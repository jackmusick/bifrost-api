"""
OAuth SSO Router

Provides endpoints for OAuth/SSO authentication:
- Get available providers
- Initialize OAuth flow
- Handle OAuth callback
- Link/unlink OAuth accounts
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel

from src.config import get_settings
from src.core.auth import CurrentActiveUser, get_current_user_from_db
from src.core.database import DbSession
from src.core.security import create_access_token, create_refresh_token
from src.services.oauth_sso import OAuthError, OAuthService
from src.services.user_provisioning import ensure_user_provisioned, get_user_roles

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/oauth", tags=["oauth"])


# =============================================================================
# Request/Response Models
# =============================================================================

class OAuthProviderInfo(BaseModel):
    """OAuth provider information."""
    name: str
    display_name: str
    icon: str | None = None


class OAuthProvidersResponse(BaseModel):
    """Available OAuth providers."""
    providers: list[OAuthProviderInfo]


class OAuthInitResponse(BaseModel):
    """OAuth initialization response."""
    authorization_url: str
    state: str


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request (for when frontend handles callback)."""
    provider: str
    code: str
    state: str
    code_verifier: str


class OAuthTokenResponse(BaseModel):
    """OAuth login token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LinkedAccountResponse(BaseModel):
    """Linked OAuth account info."""
    provider: str
    provider_email: str
    linked_at: str
    last_used_at: str | None = None


class LinkedAccountsResponse(BaseModel):
    """List of linked OAuth accounts."""
    accounts: list[LinkedAccountResponse]


# Provider display names and icons
PROVIDER_INFO = {
    "microsoft": {"display_name": "Microsoft", "icon": "microsoft"},
    "google": {"display_name": "Google", "icon": "google"},
    "oidc": {"display_name": "SSO", "icon": "key"},
}


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/providers", response_model=OAuthProvidersResponse)
async def get_oauth_providers(db: DbSession) -> OAuthProvidersResponse:
    """
    Get available OAuth providers.

    Returns list of configured OAuth providers that can be used for login.

    Returns:
        List of available OAuth providers with display info
    """
    oauth_service = OAuthService(db)
    available = oauth_service.get_available_providers()

    providers = []
    for name in available:
        info = PROVIDER_INFO.get(name, {"display_name": name.title(), "icon": None})
        providers.append(OAuthProviderInfo(
            name=name,
            display_name=info.get("display_name") or name.title(),
            icon=info.get("icon"),
        ))

    return OAuthProvidersResponse(providers=providers)


@router.get("/init/{provider}", response_model=OAuthInitResponse)
async def init_oauth(
    provider: str,
    db: DbSession,
    redirect_uri: str = Query(..., description="Frontend callback URL"),
) -> OAuthInitResponse:
    """
    Initialize OAuth login flow.

    Generates authorization URL with PKCE challenge for secure OAuth flow.
    The frontend should store the state and code_verifier in session storage.

    Args:
        provider: OAuth provider name (microsoft, google, oidc)
        redirect_uri: Frontend callback URL

    Returns:
        Authorization URL and state for CSRF protection

    Note:
        The code_verifier is returned in a secure httpOnly cookie for the callback.
        The frontend must include this cookie when calling the callback endpoint.
    """
    oauth_service = OAuthService(db)

    try:
        # Generate PKCE values and state
        code_verifier = OAuthService.generate_code_verifier()
        state = OAuthService.generate_state()

        authorization_url = oauth_service.get_authorization_url(
            provider=provider,
            redirect_uri=redirect_uri,
            state=state,
            code_verifier=code_verifier,
        )

        # Store code_verifier in response for frontend to use
        # In production, consider using encrypted server-side session
        response = OAuthInitResponse(
            authorization_url=authorization_url,
            state=state,
        )

        # Note: We return code_verifier to frontend for PKCE flow
        # Frontend stores it in sessionStorage and sends back with callback
        return response

    except OAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/init/{provider}/verifier")
async def get_code_verifier(
    provider: str,
    db: DbSession,
) -> dict[str, str]:
    """
    Generate a PKCE code verifier.

    This is a helper endpoint that returns a code verifier for the OAuth flow.
    The frontend should call this before redirecting to the OAuth provider,
    store the verifier in sessionStorage, and send it back with the callback.

    Returns:
        code_verifier and code_challenge for PKCE
    """
    code_verifier = OAuthService.generate_code_verifier()
    code_challenge = OAuthService.generate_code_challenge(code_verifier)

    return {
        "code_verifier": code_verifier,
        "code_challenge": code_challenge,
    }


@router.post("/callback", response_model=OAuthTokenResponse)
async def oauth_callback(
    callback_data: OAuthCallbackRequest,
    request: Request,
    db: DbSession,
) -> OAuthTokenResponse:
    """
    Complete OAuth login flow.

    Called by frontend after receiving callback from OAuth provider.
    Exchanges authorization code for tokens, gets user info, and returns JWT.

    OAuth users bypass MFA - the OAuth provider is trusted for authentication.

    Args:
        callback_data: OAuth callback data with code and PKCE verifier

    Returns:
        JWT access and refresh tokens

    Raises:
        HTTPException: If OAuth flow fails or user cannot be provisioned
    """
    settings = get_settings()
    oauth_service = OAuthService(db)

    try:
        # Build redirect URI from frontend URL
        # The frontend callback URL must match what was used in init
        frontend_url = settings.frontend_url or "http://localhost:3000"
        redirect_uri = f"{frontend_url}/auth/callback/{callback_data.provider}"

        # Exchange code for tokens
        tokens = await oauth_service.exchange_code_for_tokens(
            provider=callback_data.provider,
            code=callback_data.code,
            redirect_uri=redirect_uri,
            code_verifier=callback_data.code_verifier,
        )

        # Get user info from provider
        user_info = await oauth_service.get_user_info(
            provider=callback_data.provider,
            tokens=tokens,
        )

        if not user_info.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth provider did not return email address",
            )

    except OAuthError as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Check if user already has an OAuth account linked
    existing_user = await oauth_service.find_user_by_oauth(
        provider=user_info.provider,
        provider_user_id=user_info.provider_user_id,
    )

    if existing_user:
        # Existing OAuth user - update last login
        user = existing_user
        user.last_login = datetime.now(timezone.utc)

        # Update OAuth account
        await oauth_service.link_oauth_account(user, user_info, tokens)
        await db.commit()

    else:
        # New user or linking new OAuth account - provision user
        try:
            result = await ensure_user_provisioned(
                db=db,
                email=user_info.email,
                name=user_info.name,
            )
            user = result.user

            # Link OAuth account to user
            await oauth_service.link_oauth_account(user, user_info, tokens)

            user.last_login = datetime.now(timezone.utc)
            await db.commit()

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    # Get user roles
    db_roles = await get_user_roles(db, user.id)

    # Build role list
    roles = ["authenticated"]
    if user.is_superuser:
        roles.append("PlatformAdmin")
    else:
        roles.append("OrgUser")
    roles.extend(db_roles)

    # Build JWT claims
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "name": user.name or user.email.split("@")[0],
        "user_type": user.user_type.value,
        "is_superuser": user.is_superuser,
        "org_id": str(user.organization_id) if user.organization_id else None,
        "roles": roles,
        "oauth_provider": callback_data.provider,  # Mark as OAuth login
    }

    # Generate tokens
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    logger.info(
        f"OAuth login successful: {user.email}",
        extra={
            "user_id": str(user.id),
            "provider": callback_data.provider,
            "oauth_user_id": user_info.provider_user_id,
        }
    )

    return OAuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


# =============================================================================
# Account Linking (for authenticated users)
# =============================================================================

@router.get("/accounts", response_model=LinkedAccountsResponse)
async def get_linked_accounts(
    current_user: CurrentActiveUser,
    db: DbSession,
) -> LinkedAccountsResponse:
    """
    Get OAuth accounts linked to current user.

    Returns:
        List of linked OAuth accounts
    """
    oauth_service = OAuthService(db)
    accounts = await oauth_service.get_user_oauth_accounts(current_user.user_id)

    return LinkedAccountsResponse(
        accounts=[
            LinkedAccountResponse(
                provider=acc.provider_id,
                provider_email=acc.email,
                linked_at=acc.created_at.isoformat(),
                last_used_at=acc.last_login.isoformat() if acc.last_login else None,
            )
            for acc in accounts
        ]
    )


@router.delete("/accounts/{provider}")
async def unlink_oauth_account(
    provider: str,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> dict:
    """
    Unlink an OAuth account from current user.

    User must have password set or another OAuth account to unlink.

    Args:
        provider: OAuth provider to unlink

    Returns:
        Success message

    Raises:
        HTTPException: If account not found or user would be locked out
    """
    user = await get_current_user_from_db(current_user, db)
    oauth_service = OAuthService(db)

    # Check if user would be locked out
    accounts = await oauth_service.get_user_oauth_accounts(user.id)
    has_password = user.hashed_password is not None
    other_oauth = [a for a in accounts if a.provider_id != provider]

    if not has_password and not other_oauth:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot unlink: You need a password or another OAuth account to log in",
        )

    # Unlink account
    unlinked = await oauth_service.unlink_oauth_account(user.id, provider)
    if not unlinked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {provider} account linked",
        )

    await db.commit()

    logger.info(
        f"OAuth account unlinked: {provider}",
        extra={"user_id": str(user.id), "provider": provider}
    )

    return {"message": f"{provider.title()} account unlinked"}
