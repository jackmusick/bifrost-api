"""
Authentication Router

Provides endpoints for user authentication:
- Login (JWT token generation with user provisioning)
- Token refresh
- Current user info

Key Features:
- First user login auto-promotes to PlatformAdmin
- Subsequent users auto-join organizations by email domain
- JWT tokens include user_type, org_id, and roles
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from src.config import get_settings
from src.core.auth import CurrentActiveUser, UserPrincipal
from src.core.database import DbSession
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from src.repositories.users import UserRepository
from src.services.user_provisioning import ensure_user_provisioned, get_user_roles

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# =============================================================================
# Request/Response Models
# =============================================================================

class Token(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Token refresh request model."""
    refresh_token: str


class UserResponse(BaseModel):
    """User response model."""
    id: str
    email: str
    name: str
    is_active: bool
    is_superuser: bool
    is_verified: bool
    user_type: str
    organization_id: str | None
    roles: list[str] = []


class UserCreate(BaseModel):
    """User creation request model."""
    email: EmailStr
    password: str
    name: str | None = None


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: DbSession = None,
) -> Token:
    """
    Login with email and password.

    Performs user provisioning on each login:
    - First user in system becomes PlatformAdmin
    - Subsequent users are matched to organizations by email domain
    - JWT tokens include user_type, org_id, and roles for authorization

    Args:
        form_data: OAuth2 password form with username (email) and password
        db: Database session

    Returns:
        Access and refresh tokens with user claims

    Raises:
        HTTPException: If credentials are invalid or provisioning fails
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(form_data.username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account does not have password authentication enabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    # Get user roles from database
    db_roles = await get_user_roles(db, user.id)

    # Build role list (include type-based roles + database roles)
    roles = ["authenticated"]
    if user.is_superuser:
        roles.append("PlatformAdmin")
    else:
        roles.append("OrgUser")
    roles.extend(db_roles)

    # Build JWT claims with user info
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "name": user.name or user.email.split("@")[0],
        "user_type": user.user_type.value,
        "is_superuser": user.is_superuser,
        "org_id": str(user.organization_id) if user.organization_id else None,
        "roles": roles,
    }

    # Generate tokens
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    logger.info(
        f"User logged in: {user.email}",
        extra={
            "user_id": str(user.id),
            "user_type": user.user_type.value,
            "is_superuser": user.is_superuser,
            "org_id": str(user.organization_id) if user.organization_id else None,
        }
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh,
    db: DbSession = None,
) -> Token:
    """
    Refresh access token using refresh token.

    Fetches fresh user data and roles from database to ensure
    the new token has up-to-date claims.

    Args:
        token_data: Refresh token
        db: Database session

    Returns:
        New access and refresh tokens with updated claims

    Raises:
        HTTPException: If refresh token is invalid
    """
    payload = decode_token(token_data.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify user still exists and is active
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(UUID(user_id))

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get fresh user roles from database
    db_roles = await get_user_roles(db, user.id)

    # Build role list
    roles = ["authenticated"]
    if user.is_superuser:
        roles.append("PlatformAdmin")
    else:
        roles.append("OrgUser")
    roles.extend(db_roles)

    # Build JWT claims with fresh user info
    new_token_data = {
        "sub": str(user.id),
        "email": user.email,
        "name": user.name or user.email.split("@")[0],
        "user_type": user.user_type.value,
        "is_superuser": user.is_superuser,
        "org_id": str(user.organization_id) if user.organization_id else None,
        "roles": roles,
    }

    # Generate new tokens
    access_token = create_access_token(data=new_token_data)
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentActiveUser,
) -> UserResponse:
    """
    Get current authenticated user information.

    Returns user info including type, organization, and roles from the JWT token.

    Args:
        current_user: Current authenticated user (from JWT)

    Returns:
        User information with roles
    """
    return UserResponse(
        id=str(current_user.user_id),
        email=current_user.email,
        name=current_user.name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        is_verified=current_user.is_verified,
        user_type=current_user.user_type,
        organization_id=str(current_user.organization_id) if current_user.organization_id else None,
        roles=current_user.roles,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: DbSession = None,
) -> UserResponse:
    """
    Register a new user with auto-provisioning.

    Uses the same provisioning logic as login:
    - First user becomes PlatformAdmin
    - Subsequent users are matched to organizations by email domain

    Note: In production, this should be restricted or require admin approval.

    Args:
        user_data: User registration data
        db: Database session

    Returns:
        Created user information with roles

    Raises:
        HTTPException: If email already exists or provisioning fails
    """
    settings = get_settings()

    # Only allow registration in development mode
    if not settings.is_development:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User registration is disabled",
        )

    user_repo = UserRepository(db)

    # Check if email already exists
    existing_user = await user_repo.get_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Use provisioning logic to determine user type and org assignment
    try:
        result = await ensure_user_provisioned(
            db=db,
            email=user_data.email,
            name=user_data.name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Set password for the provisioned user
    user = result.user
    user.hashed_password = get_password_hash(user_data.password)
    await db.commit()

    logger.info(
        f"User registered: {user.email}",
        extra={
            "user_id": str(user.id),
            "user_type": result.user_type.value,
            "was_created": result.was_created,
        }
    )

    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name or "",
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        is_verified=user.is_verified,
        user_type=result.user_type.value,
        organization_id=str(user.organization_id) if user.organization_id else None,
        roles=result.roles,
    )


class OAuthLoginRequest(BaseModel):
    """OAuth/SSO login request model."""
    email: EmailStr
    name: str | None = None
    provider: str = "oauth"  # e.g., "azure", "google", "github"


@router.post("/oauth/login", response_model=Token)
async def oauth_login(
    login_data: OAuthLoginRequest,
    db: DbSession = None,
) -> Token:
    """
    Login via OAuth/SSO provider.

    This endpoint is called after the frontend completes OAuth authentication.
    It provisions the user (if new) and returns JWT tokens.

    Auto-Provisioning Rules:
    - First user in system becomes PlatformAdmin
    - Subsequent users are matched to organizations by email domain
    - Users without matching org domain are rejected

    Args:
        login_data: OAuth login data with verified email from provider
        db: Database session

    Returns:
        Access and refresh tokens with user claims

    Raises:
        HTTPException: If provisioning fails (no matching org)
    """
    try:
        result = await ensure_user_provisioned(
            db=db,
            email=login_data.email,
            name=login_data.name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

    user = result.user

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    # Get user roles from database
    db_roles = await get_user_roles(db, user.id)

    # Build role list
    roles = result.roles.copy()
    roles.extend(db_roles)

    # Build JWT claims with user info
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "name": user.name or user.email.split("@")[0],
        "user_type": result.user_type.value,
        "is_superuser": result.is_platform_admin,
        "org_id": str(result.organization_id) if result.organization_id else None,
        "roles": roles,
    }

    # Generate tokens
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    logger.info(
        f"OAuth login: {user.email}",
        extra={
            "user_id": str(user.id),
            "user_type": result.user_type.value,
            "provider": login_data.provider,
            "was_created": result.was_created,
        }
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )
