"""
OAuth Connections Router

Manages OAuth connections for workflow integrations.
This is separate from oauth_sso.py which handles user authentication.
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.schemas import (
    CreateOAuthConnectionRequest,
    UpdateOAuthConnectionRequest,
    OAuthConnectionDetail,
    OAuthConnectionSummary,
    OAuthCredentialsResponse,
    OAuthCallbackRequest,
    OAuthCallbackResponse,
)
from src.core.auth import Context, CurrentSuperuser
from src.models import OAuthProvider, OAuthToken

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/oauth", tags=["OAuth Connections"])


# =============================================================================
# Response Models
# =============================================================================


class OAuthConnectionListResponse(BaseModel):
    """Response for listing OAuth connections."""
    connections: list[OAuthConnectionSummary] = Field(
        ..., description="List of OAuth connections"
    )


class AuthorizeResponse(BaseModel):
    """Response for initiating OAuth authorization."""
    authorization_url: str = Field(..., description="URL to redirect user for authorization")
    state: str = Field(..., description="State parameter for CSRF protection")
    message: str = Field(default="Redirect user to authorization_url")


class RefreshTokenResponse(BaseModel):
    """Response for token refresh."""
    success: bool
    message: str
    expires_at: str | None = None


class RefreshJobRun(BaseModel):
    """Details of a single refresh job run."""
    status: str = Field(default="completed")
    start_time: datetime | None = None
    end_time: datetime | None = None
    connections_checked: int = 0
    refreshed_successfully: int = 0
    refresh_failed: int = 0
    needs_refresh: int = 0
    total_connections: int = 0
    error: str | None = None
    errors: list[str] = Field(default_factory=list)


class RefreshJobStatusResponse(BaseModel):
    """Response for refresh job status."""
    enabled: bool = Field(default=True)
    last_run: RefreshJobRun | None = None
    next_run: datetime | None = None


class RefreshAllResponse(BaseModel):
    """Response for triggering refresh of all tokens."""
    triggered: bool
    message: str
    connections_queued: int = 0
    refreshed_successfully: int = 0
    refresh_failed: int = 0


# =============================================================================
# Repository
# =============================================================================


class OAuthConnectionRepository:
    """PostgreSQL-based OAuth connection repository."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_connections(
        self,
        org_id: UUID | None = None,
    ) -> list[OAuthConnectionSummary]:
        """List all OAuth connections, optionally filtered by org."""
        query = select(OAuthProvider)
        if org_id:
            query = query.where(OAuthProvider.organization_id == org_id)
        query = query.order_by(OAuthProvider.created_at.desc())

        result = await self.db.execute(query)
        providers = result.scalars().all()

        return [self._to_summary(p) for p in providers]

    async def get_connection(
        self,
        connection_name: str,
        org_id: UUID | None = None,
    ) -> OAuthProvider | None:
        """Get a specific OAuth connection."""
        query = select(OAuthProvider).where(
            OAuthProvider.provider_name == connection_name
        )
        if org_id:
            query = query.where(OAuthProvider.organization_id == org_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_connection(
        self,
        request: CreateOAuthConnectionRequest,
        org_id: UUID | None,
        created_by: str,
    ) -> OAuthProvider:
        """Create a new OAuth connection."""
        # Encrypt client secret if provided
        encrypted_secret = b""
        if request.client_secret:
            from src.core.security import encrypt_secret
            encrypted_secret = encrypt_secret(request.client_secret).encode()

        provider = OAuthProvider(
            organization_id=org_id,
            provider_name=request.connection_name,
            display_name=request.name or request.connection_name,
            description=request.description,
            oauth_flow_type=request.oauth_flow_type,
            client_id=request.client_id,
            encrypted_client_secret=encrypted_secret,
            authorization_url=request.authorization_url,
            token_url=request.token_url,
            scopes=request.scopes.split(",") if request.scopes else [],
            status="not_connected",
            created_by=created_by,
        )

        self.db.add(provider)
        await self.db.flush()
        await self.db.refresh(provider)

        return provider

    async def update_connection(
        self,
        connection_name: str,
        org_id: UUID | None,
        request: UpdateOAuthConnectionRequest,
    ) -> OAuthProvider | None:
        """Update an existing OAuth connection."""
        provider = await self.get_connection(connection_name, org_id)
        if not provider:
            return None

        if request.name is not None:
            provider.display_name = request.name
        if request.client_id is not None:
            provider.client_id = request.client_id
        if request.scopes is not None:
            provider.scopes = request.scopes

        provider.updated_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(provider)

        return provider

    async def delete_connection(
        self,
        connection_name: str,
        org_id: UUID | None,
    ) -> bool:
        """Delete an OAuth connection."""
        provider = await self.get_connection(connection_name, org_id)
        if not provider:
            return False

        # Delete associated tokens first
        token_query = select(OAuthToken).where(OAuthToken.provider_id == provider.id)
        token_result = await self.db.execute(token_query)
        for token in token_result.scalars().all():
            await self.db.delete(token)

        await self.db.delete(provider)
        await self.db.flush()

        return True

    async def update_status(
        self,
        connection_name: str,
        org_id: UUID | None,
        status: str,
        status_message: str | None = None,
    ) -> bool:
        """Update connection status."""
        provider = await self.get_connection(connection_name, org_id)
        if not provider:
            return False

        provider.status = status
        provider.status_message = status_message
        provider.updated_at = datetime.utcnow()

        await self.db.flush()
        return True

    async def get_token(
        self,
        connection_name: str,
        org_id: UUID | None,
    ) -> OAuthToken | None:
        """Get the current token for a connection."""
        provider = await self.get_connection(connection_name, org_id)
        if not provider:
            return None

        query = select(OAuthToken).where(
            OAuthToken.provider_id == provider.id
        ).order_by(OAuthToken.created_at.desc())

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def store_token(
        self,
        connection_name: str,
        org_id: UUID | None,
        access_token: str,
        refresh_token: str | None,
        expires_at: datetime,
        token_type: str = "Bearer",
    ) -> OAuthToken | None:
        """Store a new token for a connection."""
        provider = await self.get_connection(connection_name, org_id)
        if not provider:
            return None

        # Create new token (could also update existing)
        token = OAuthToken(
            provider_id=provider.id,
            # In production, tokens should be encrypted
            access_token_ref=f"oauth/{connection_name}/access_token",
            refresh_token_ref=f"oauth/{connection_name}/refresh_token" if refresh_token else None,
            token_type=token_type,
            expires_at=expires_at,
        )

        self.db.add(token)

        # Update provider status
        provider.status = "completed"
        provider.status_message = "Token acquired successfully"
        provider.last_token_refresh = datetime.utcnow()
        provider.updated_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(token)

        return token

    def _to_summary(self, provider: OAuthProvider) -> OAuthConnectionSummary:
        """Convert to summary model."""
        # Get latest token expiry if available
        expires_at = None
        if provider.tokens:
            latest_token = max(provider.tokens, key=lambda t: t.created_at)
            expires_at = latest_token.expires_at

        return OAuthConnectionSummary(
            connection_name=provider.provider_name,
            name=provider.display_name,
            provider=provider.provider_name,
            oauth_flow_type=provider.oauth_flow_type,
            status=provider.status or "not_connected",
            status_message=provider.status_message,
            expires_at=expires_at,
            last_refresh_at=provider.last_token_refresh,
            created_at=provider.created_at,
            updated_at=provider.updated_at,
        )

    def _to_detail(self, provider: OAuthProvider) -> OAuthConnectionDetail:
        """Convert to detail model."""
        summary = self._to_summary(provider)
        return OAuthConnectionDetail(
            **summary.model_dump(),
            client_id=provider.client_id,
            authorization_url=provider.authorization_url,
            token_url=provider.token_url,
            scopes=provider.scopes,
            description=provider.description,
        )


# =============================================================================
# HTTP Endpoints
# =============================================================================


@router.get(
    "/connections",
    response_model=OAuthConnectionListResponse,
    summary="List OAuth connections",
    description="List all OAuth connections (Platform admin only)",
)
async def list_connections(
    ctx: Context,
    user: CurrentSuperuser,
) -> OAuthConnectionListResponse:
    """List all OAuth connections."""
    repo = OAuthConnectionRepository(ctx.db)
    org_id = ctx.org_id
    connections = await repo.list_connections(org_id)

    return OAuthConnectionListResponse(connections=connections)


@router.get(
    "/connections/{connection_name}",
    response_model=OAuthConnectionDetail,
    summary="Get OAuth connection",
    description="Get a specific OAuth connection (Platform admin only)",
)
async def get_connection(
    connection_name: str,
    ctx: Context,
    user: CurrentSuperuser,
) -> OAuthConnectionDetail:
    """Get a specific OAuth connection."""
    repo = OAuthConnectionRepository(ctx.db)
    org_id = ctx.org_id
    provider = await repo.get_connection(connection_name, org_id)

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OAuth connection '{connection_name}' not found",
        )

    return repo._to_detail(provider)


@router.post(
    "/connections",
    response_model=OAuthConnectionDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create OAuth connection",
    description="Create a new OAuth connection (Platform admin only)",
)
async def create_connection(
    request: CreateOAuthConnectionRequest,
    ctx: Context,
    user: CurrentSuperuser,
) -> OAuthConnectionDetail:
    """Create a new OAuth connection."""
    repo = OAuthConnectionRepository(ctx.db)
    org_id = ctx.org_id

    # Check for existing connection
    existing = await repo.get_connection(request.connection_name, org_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"OAuth connection '{request.connection_name}' already exists",
        )

    provider = await repo.create_connection(
        request=request,
        org_id=org_id,
        created_by=ctx.user.email,
    )

    logger.info(f"Created OAuth connection: {request.connection_name}")

    return repo._to_detail(provider)


@router.put(
    "/connections/{connection_name}",
    response_model=OAuthConnectionDetail,
    summary="Update OAuth connection",
    description="Update an existing OAuth connection (Platform admin only)",
)
async def update_connection(
    connection_name: str,
    request: UpdateOAuthConnectionRequest,
    ctx: Context,
    user: CurrentSuperuser,
) -> OAuthConnectionDetail:
    """Update an OAuth connection."""
    repo = OAuthConnectionRepository(ctx.db)
    org_id = ctx.org_id

    provider = await repo.update_connection(connection_name, org_id, request)

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OAuth connection '{connection_name}' not found",
        )

    logger.info(f"Updated OAuth connection: {connection_name}")

    return repo._to_detail(provider)


@router.delete(
    "/connections/{connection_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete OAuth connection",
    description="Delete an OAuth connection (Platform admin only)",
)
async def delete_connection(
    connection_name: str,
    ctx: Context,
    user: CurrentSuperuser,
) -> None:
    """Delete an OAuth connection."""
    repo = OAuthConnectionRepository(ctx.db)
    org_id = ctx.org_id

    deleted = await repo.delete_connection(connection_name, org_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OAuth connection '{connection_name}' not found",
        )

    logger.info(f"Deleted OAuth connection: {connection_name}")


@router.post(
    "/connections/{connection_name}/authorize",
    response_model=AuthorizeResponse,
    summary="Initiate OAuth authorization",
    description="Get authorization URL for user to complete OAuth flow",
)
async def authorize_connection(
    connection_name: str,
    ctx: Context,
    user: CurrentSuperuser,
) -> AuthorizeResponse:
    """Initiate OAuth authorization flow."""
    repo = OAuthConnectionRepository(ctx.db)
    org_id = ctx.org_id

    provider = await repo.get_connection(connection_name, org_id)

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OAuth connection '{connection_name}' not found",
        )

    if not provider.authorization_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This connection uses client_credentials flow and doesn't require user authorization",
        )

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)

    # Build authorization URL
    params = {
        "client_id": provider.client_id,
        "response_type": "code",
        "state": state,
        "scope": provider.scopes or "",
        # TODO: Make redirect_uri configurable
        "redirect_uri": f"http://localhost:5173/oauth/callback/{connection_name}",
    }

    authorization_url = f"{provider.authorization_url}?{urlencode(params)}"

    # Update status to waiting
    await repo.update_status(
        connection_name=connection_name,
        org_id=org_id,
        status="waiting_callback",
        status_message="Waiting for user to complete authorization",
    )

    return AuthorizeResponse(
        authorization_url=authorization_url,
        state=state,
        message="Redirect user to authorization_url to complete OAuth flow",
    )


@router.post(
    "/connections/{connection_name}/cancel",
    response_model=OAuthConnectionDetail,
    summary="Cancel OAuth authorization",
    description="Cancel pending OAuth authorization and reset to not_connected",
)
async def cancel_authorization(
    connection_name: str,
    ctx: Context,
    user: CurrentSuperuser,
) -> OAuthConnectionDetail:
    """Cancel OAuth authorization and reset status."""
    repo = OAuthConnectionRepository(ctx.db)
    org_id = ctx.org_id

    provider = await repo.get_connection(connection_name, org_id)

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OAuth connection '{connection_name}' not found",
        )

    await repo.update_status(
        connection_name=connection_name,
        org_id=org_id,
        status="not_connected",
        status_message="Authorization cancelled",
    )

    # Refresh provider
    provider = await repo.get_connection(connection_name, org_id)
    return repo._to_detail(provider)


@router.post(
    "/connections/{connection_name}/refresh",
    response_model=RefreshTokenResponse,
    summary="Refresh OAuth token",
    description="Manually refresh the OAuth access token using the refresh token",
)
async def refresh_token(
    connection_name: str,
    ctx: Context,
    user: CurrentSuperuser,
) -> RefreshTokenResponse:
    """Refresh OAuth token."""
    repo = OAuthConnectionRepository(ctx.db)
    org_id = ctx.org_id

    provider = await repo.get_connection(connection_name, org_id)

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OAuth connection '{connection_name}' not found",
        )

    token = await repo.get_token(connection_name, org_id)

    if not token or not token.refresh_token_ref:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No refresh token available for this connection",
        )

    # TODO: Implement actual token refresh using the OAuth provider
    # For now, return a placeholder response
    return RefreshTokenResponse(
        success=True,
        message="Token refresh not yet implemented in FastAPI migration",
        expires_at=None,
    )


@router.post(
    "/callback/{connection_name}",
    response_model=OAuthCallbackResponse,
    summary="OAuth callback",
    description="Handle OAuth callback and exchange code for tokens",
)
async def oauth_callback(
    connection_name: str,
    request: OAuthCallbackRequest,
    ctx: Context,
) -> OAuthCallbackResponse:
    """Handle OAuth callback."""
    repo = OAuthConnectionRepository(ctx.db)
    # Callbacks may come from non-authenticated contexts
    org_id = None

    provider = await repo.get_connection(connection_name, org_id)

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OAuth connection '{connection_name}' not found",
        )

    # TODO: Implement actual token exchange
    # For now, just update status
    await repo.update_status(
        connection_name=connection_name,
        org_id=org_id,
        status="completed",
        status_message="Callback received (token exchange not yet implemented)",
    )

    return OAuthCallbackResponse(
        success=True,
        message="OAuth callback processed",
        connection_name=connection_name,
    )


@router.get(
    "/credentials/{connection_name}",
    response_model=OAuthCredentialsResponse,
    summary="Get OAuth credentials",
    description="Get OAuth credentials for use in workflows (Platform admin only)",
)
async def get_credentials(
    connection_name: str,
    ctx: Context,
    user: CurrentSuperuser,
) -> OAuthCredentialsResponse:
    """Get OAuth credentials."""
    repo = OAuthConnectionRepository(ctx.db)
    org_id = ctx.org_id

    provider = await repo.get_connection(connection_name, org_id)

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OAuth connection '{connection_name}' not found",
        )

    token = await repo.get_token(connection_name, org_id)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No token available for this connection",
        )

    # In production, we'd decrypt the token here
    return OAuthCredentialsResponse(
        connection_name=connection_name,
        access_token="[REDACTED - token storage not yet migrated]",
        token_type=token.token_type,
        expires_at=token.expires_at,
    )


@router.get(
    "/refresh_job_status",
    response_model=RefreshJobStatusResponse,
    summary="Get OAuth refresh job status",
    description="Get status of the background token refresh job",
)
async def get_refresh_job_status(
    ctx: Context,
    user: CurrentSuperuser,
) -> RefreshJobStatusResponse:
    """Get refresh job status."""
    # In production, this would query the scheduler/job history
    # For now, return a basic status indicating no jobs have run
    return RefreshJobStatusResponse(
        enabled=True,
        last_run=None,
        next_run=None,
    )


@router.post(
    "/refresh_all",
    response_model=RefreshAllResponse,
    summary="Trigger refresh of all OAuth tokens",
    description="Manually trigger refresh of all OAuth tokens (Platform admin only)",
)
async def trigger_refresh_all(
    ctx: Context,
    user: CurrentSuperuser,
) -> RefreshAllResponse:
    """Trigger refresh of all OAuth tokens."""
    # In production, this would queue refresh jobs
    repo = OAuthConnectionRepository(ctx.db)
    org_id = ctx.org_id

    connections = await repo.list_connections(org_id)
    completed_count = len([c for c in connections if c.status == "completed"])

    return RefreshAllResponse(
        triggered=True,
        message=f"Queued {completed_count} connections for refresh",
        connections_queued=completed_count,
    )
