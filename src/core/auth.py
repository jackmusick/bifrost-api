"""
Authentication and Authorization

Provides FastAPI dependencies for authentication and authorization.
Supports JWT bearer token authentication with user context injection.
"""

import logging
from dataclasses import dataclass, field
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.config import get_settings
from src.core.database import DbSession
from src.core.security import decode_token

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class UserPrincipal:
    """
    Authenticated user principal.

    Represents an authenticated user with their identity and permissions.
    """
    user_id: UUID
    email: str
    name: str = ""
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False
    organization_id: UUID | None = None
    roles: list[str] = field(default_factory=list)

    @property
    def is_platform_admin(self) -> bool:
        """Check if user is a platform admin (superuser)."""
        return self.is_superuser

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles


@dataclass
class ExecutionContext:
    """
    Execution context for request handling.

    Contains the authenticated user, organization scope, and database session.
    """
    user: UserPrincipal
    org_id: UUID | None
    db: object  # AsyncSession, but avoid circular import

    @property
    def scope(self) -> str:
        """Get the scope string for data access (org_id or 'GLOBAL')."""
        return str(self.org_id) if self.org_id else "GLOBAL"

    @property
    def user_id(self) -> str:
        """Get user ID as string."""
        return str(self.user.user_id)

    @property
    def is_global_scope(self) -> bool:
        """Check if operating in global scope."""
        return self.org_id is None


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbSession,
) -> UserPrincipal | None:
    """
    Get the current user from JWT token (optional).

    Returns None if no token is provided or token is invalid.
    Does not raise an exception for unauthenticated requests.

    Args:
        credentials: HTTP Bearer credentials from request
        db: Database session

    Returns:
        UserPrincipal if authenticated, None otherwise
    """
    if credentials is None:
        return None

    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        return None

    # Extract user ID from token
    user_id_str = payload.get("sub")
    if not user_id_str:
        return None

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        return None

    # Import here to avoid circular imports
    from src.repositories.users import UserRepository

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if user is None or not user.is_active:
        return None

    return UserPrincipal(
        user_id=user.id,
        email=user.email,
        name=user.name or user.email.split("@")[0],
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        is_verified=user.is_verified,
        organization_id=user.organization_id,
        roles=[],  # TODO: Load roles from database
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbSession,
) -> UserPrincipal:
    """
    Get the current user from JWT token (required).

    Raises HTTPException if not authenticated.

    Args:
        credentials: HTTP Bearer credentials from request
        db: Database session

    Returns:
        UserPrincipal for authenticated user

    Raises:
        HTTPException: If not authenticated or token is invalid
    """
    settings = get_settings()

    # In development, allow bypass for unauthenticated requests
    if settings.is_development and credentials is None:
        logger.warning("Using development bypass authentication")
        # Return a dev user principal
        return UserPrincipal(
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            email=settings.dev_user_email,
            name="Dev Admin",
            is_active=True,
            is_superuser=True,
            is_verified=True,
            organization_id=None,
            roles=["admin"],
        )

    user = await get_current_user_optional(credentials, db)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    user: Annotated[UserPrincipal, Depends(get_current_user)],
) -> UserPrincipal:
    """
    Get the current active user.

    Raises HTTPException if user is inactive.

    Args:
        user: Current user from authentication

    Returns:
        UserPrincipal for active user

    Raises:
        HTTPException: If user is inactive
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return user


async def get_current_superuser(
    user: Annotated[UserPrincipal, Depends(get_current_active_user)],
) -> UserPrincipal:
    """
    Get the current superuser (platform admin).

    Raises HTTPException if user is not a superuser.

    Args:
        user: Current active user

    Returns:
        UserPrincipal for superuser

    Raises:
        HTTPException: If user is not a superuser
    """
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required"
        )
    return user


async def get_execution_context(
    request: Request,
    user: Annotated[UserPrincipal, Depends(get_current_active_user)],
    db: DbSession,
) -> ExecutionContext:
    """
    Get execution context with organization scope.

    Organization context is determined by:
    1. X-Organization-Id header (if user is superuser or member of that org)
    2. User's default organization
    3. None (global scope) for superusers without org header

    Args:
        request: FastAPI request object
        user: Current active user
        db: Database session

    Returns:
        ExecutionContext with user and organization scope

    Raises:
        HTTPException: If org access is denied
    """
    # Get org from header
    org_header = request.headers.get("X-Organization-Id")
    org_id: UUID | None = None

    if org_header:
        try:
            org_id = UUID(org_header)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-Organization-Id header"
            )

        # Verify access to organization
        if not user.is_superuser:
            # Non-superusers can only access their own org
            if user.organization_id != org_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to organization"
                )
    else:
        # No header - use user's default org (or None for superusers)
        org_id = user.organization_id

    return ExecutionContext(
        user=user,
        org_id=org_id,
        db=db,
    )


# Type aliases for dependency injection
CurrentUser = Annotated[UserPrincipal, Depends(get_current_user)]
CurrentActiveUser = Annotated[UserPrincipal, Depends(get_current_active_user)]
CurrentSuperuser = Annotated[UserPrincipal, Depends(get_current_superuser)]
Context = Annotated[ExecutionContext, Depends(get_execution_context)]


async def get_current_user_ws(websocket) -> UserPrincipal | None:
    """
    Get current user from WebSocket connection.

    Checks for token in:
    1. Query parameter: ?token=xxx
    2. Authorization header (if supported by client)

    Args:
        websocket: FastAPI WebSocket connection

    Returns:
        UserPrincipal if authenticated, None otherwise
    """
    from fastapi import WebSocket

    websocket: WebSocket = websocket
    settings = get_settings()

    # Try to get token from query params
    token = websocket.query_params.get("token")

    # Try Authorization header (some WebSocket clients support this)
    if not token:
        auth_header = websocket.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:]

    if not token:
        # Development bypass
        if settings.is_development:
            return UserPrincipal(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                email=settings.dev_user_email,
                name="Dev Admin",
                is_active=True,
                is_superuser=True,
                is_verified=True,
                organization_id=None,
                roles=["admin"],
            )
        return None

    # Decode and validate token
    payload = decode_token(token)
    if payload is None:
        return None

    user_id_str = payload.get("sub")
    if not user_id_str:
        return None

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        return None

    # Get user from database
    from src.core.database import get_session_factory
    from src.repositories.users import UserRepository

    session_factory = get_session_factory()
    async with session_factory() as db:
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)

        if user is None or not user.is_active:
            return None

        return UserPrincipal(
            user_id=user.id,
            email=user.email,
            name=user.name or user.email.split("@")[0],
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            is_verified=user.is_verified,
            organization_id=user.organization_id,
            roles=[],
        )
