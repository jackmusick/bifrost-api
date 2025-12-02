"""
Authentication and Authorization

Unified authentication system supporting:
- JWT tokens for user authentication
- API keys for service-to-service authentication
- Organization context derivation and validation
"""

import base64
import json
import logging
import os
from dataclasses import dataclass, field
from functools import wraps

import azure.functions as func

logger = logging.getLogger(__name__)


# ==================== ENVIRONMENT DETECTION ====================

def is_production() -> bool:
    """
    Check if running in production environment.

    Returns:
        True if in production, False if local development
    """
    return bool(
        os.environ.get('WEBSITE_SITE_NAME') or  # App Service
        os.environ.get('ENVIRONMENT',
                       '').lower() == 'production'
    )


# ==================== PRINCIPAL DATACLASSES ====================

@dataclass
class FunctionKeyPrincipal:
    """
    Principal for function key authentication (service-to-service).
    Provides privileged access without user context.
    """
    key_id: str
    key_name: str = "default"

    @property
    def is_function_key(self) -> bool:
        return True

    def __str__(self) -> str:
        return f"FunctionKey({self.key_name})"


@dataclass
class UserPrincipal:
    """
    Principal for user authentication via JWT token.
    Represents an authenticated end-user with identity and roles.
    """
    user_id: str
    email: str
    name: str = ""
    roles: list[str] = field(default_factory=list)
    identity_provider: str = "aad"

    @property
    def is_function_key(self) -> bool:
        return False

    def has_role(self, role: str) -> bool:
        """Check if user has specific role"""
        return role in self.roles

    def __str__(self) -> str:
        return f"User({self.email})"


# ==================== EXCEPTIONS ====================

class AuthenticationError(Exception):
    """Raised when authentication fails"""
    pass


class AuthorizationError(Exception):
    """Raised when user is authenticated but not authorized"""
    pass


# ==================== AUTHENTICATION SERVICE ====================

class AuthenticationService:
    """
    Tiered authentication with priority:
    1. Function key (x-functions-key header or ?code query param)
    2. Easy Auth (X-MS-CLIENT-PRINCIPAL header)
    3. Local dev bypass (only if not in production)
    """

    async def authenticate(self, req: func.HttpRequest) -> FunctionKeyPrincipal | UserPrincipal:
        """
        Authenticate request using tiered priority system.

        Raises:
            AuthenticationError: If no valid authentication found
        """
        # Priority 1: Function key
        principal = await self._try_function_key(req)
        if principal:
            return principal

        # Priority 2: Easy Auth user
        principal = await self._try_easy_auth(req)
        if principal:
            return principal

        # Priority 3: Local dev bypass (development only)
        if not is_production():
            logger.warning("Using local dev bypass authentication")
            return FunctionKeyPrincipal(key_id="local-dev", key_name="local-development")

        # No valid authentication
        raise AuthenticationError(
            "Authentication required. Provide x-functions-key header, ?code query param, "
            "or X-MS-CLIENT-PRINCIPAL header from Azure Easy Auth."
        )

    async def _try_function_key(self, req: func.HttpRequest) -> FunctionKeyPrincipal | None:
        """Try to authenticate with function key"""
        # Check header first
        key = req.headers.get('x-functions-key')

        # Check query param as fallback
        if not key:
            key = req.params.get('code')

        if key and key.strip():
            principal = FunctionKeyPrincipal(
                key_id=key.strip(), key_name="default")

            # Audit function key usage
            await self._audit_key_usage(req, principal)

            logger.info(
                f"Authenticated with function key: {principal.key_name}")
            return principal

        return None

    async def _try_easy_auth(self, req: func.HttpRequest) -> UserPrincipal | None:
        """Try to authenticate with JWT token (legacy support for X-MS-CLIENT-PRINCIPAL)"""
        header = req.headers.get('X-MS-CLIENT-PRINCIPAL')
        if not header:
            return None

        try:
            # Decode base64 JSON
            data = json.loads(base64.b64decode(header).decode('utf-8'))

            # Extract userId and email from principal
            user_id = data.get('userId')
            email = data.get('userDetails', '')

            if not user_id:
                if email:
                    user_id = email  # Use email as user_id for local dev
                else:
                    raise AuthenticationError(
                        "X-MS-CLIENT-PRINCIPAL missing both userId and userDetails")

            principal = UserPrincipal(
                user_id=user_id,
                email=email,
                name=email.split('@')[0] if email else user_id,
                roles=data.get('userRoles', []),
                identity_provider=data.get('identityProvider', 'aad')
            )

            return principal

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise AuthenticationError(
                f"Failed to decode Easy Auth principal: {e}") from e
        except Exception as e:
            # Catch base64 decoding errors
            raise AuthenticationError(
                f"Failed to decode Easy Auth principal: {e}") from e

    async def _audit_key_usage(self, req: func.HttpRequest, principal: FunctionKeyPrincipal) -> None:
        """Audit function key usage (fire and forget)"""
        try:
            from shared.audit import get_audit_logger

            audit_logger = get_audit_logger()
            await audit_logger.log_function_key_access(
                key_id=principal.key_id[:8] + "...",
                key_name=principal.key_name,
                org_id=req.headers.get('X-Organization-Id', 'unknown'),
                endpoint=req.url,
                method=req.method,
                remote_addr=req.headers.get('X-Forwarded-For', 'unknown'),
                user_agent=req.headers.get('User-Agent', 'unknown'),
                status_code=0,
                details=None
            )
        except Exception as e:
            logger.debug(f"Failed to audit function key usage: {e}")


# ==================== AUTHORIZATION ====================

async def is_platform_admin(user_id: str) -> bool:
    """
    Check if user is a platform admin.

    Returns:
        True if platform admin, False otherwise
    """
    from src.repositories.users import UserRepository

    try:
        user_repo = UserRepository()
        user = await user_repo.get_user(user_id)

        if user:
            return user.isPlatformAdmin and user.userType.value == "PLATFORM"

        return False
    except Exception as e:
        logger.warning(
            f"Failed to check platform admin status for {user_id}: {e}")
        return False


async def get_user_org_id(user_id: str) -> str | None:
    """
    Get user's organization ID from database.

    Returns:
        Organization ID or None if not found
    """
    from src.repositories.users import UserRepository

    try:
        user_repo = UserRepository()
        org_id = await user_repo.get_user_org_id(user_id)

        if org_id:
            logger.debug(f"User {user_id} belongs to org: {org_id}")
        else:
            logger.warning(f"User {user_id} has no org assignments")

        return org_id

    except Exception as e:
        logger.error(f"Error looking up user org: {e}")
        return None


# ==================== ORGANIZATION CONTEXT ====================

async def get_org_context(req: func.HttpRequest) -> tuple[str | None, str, func.HttpResponse | None]:
    """
    Get organization context with security enforcement.

    Rules:
    - Platform admins: Can pass X-Organization-Id to impersonate, or None for global scope
    - Regular users: org_id derived from database, cannot override

    Returns:
        (org_id, user_id, error_response)
        - org_id: Organization ID or None for global scope
        - user_id: User ID from principal
        - error_response: HttpResponse if error, None if success

    Usage:
        org_id, user_id, error = get_org_context(req)
        if error:
            return error
    """
    # Get authenticated principal from request
    principal = getattr(req, 'principal', None)
    if not principal:
        return None, "", _error_response(401, "Unauthorized", "Authentication required")

    # Function keys operate in global scope
    if isinstance(principal, FunctionKeyPrincipal):
        org_id = req.headers.get('X-Organization-Id')  # Optional
        logger.info(f"Function key auth: org={org_id or 'GLOBAL'}")
        return org_id, "function-key", None

    # User authentication
    user_id = principal.user_id
    is_admin = await is_platform_admin(user_id)
    provided_org_id = req.headers.get('X-Organization-Id')

    # Platform admin logic
    if is_admin:
        # Admin can specify org or work in global scope
        org_id = provided_org_id  # May be None
        logger.info(f"Admin {principal.email}: org={org_id or 'GLOBAL'}")
        return org_id, user_id, None

    # Regular user logic
    if provided_org_id:
        # Non-admin cannot override org context
        logger.warning(
            f"Non-admin {principal.email} attempted to set X-Organization-Id")
        return None, "", _error_response(
            403, "Forbidden",
            "Only platform administrators can override organization context"
        )

    # Derive org from database
    org_id = await get_user_org_id(user_id)
    if not org_id:
        return None, "", _error_response(
            404, "NotFound",
            "User organization not found. Contact administrator."
        )

    logger.info(f"User {principal.email}: org={org_id}")
    return org_id, user_id, None


# ==================== DECORATORS ====================

def require_auth(handler):
    """
    Decorator to require authentication for endpoints.
    Injects req.principal for use in handler.

    Usage:
        @require_auth
        async def my_handler(req: func.HttpRequest) -> func.HttpResponse:
            principal = req.principal
            # ...
    """
    @wraps(handler)
    async def wrapper(req: func.HttpRequest) -> func.HttpResponse:
        try:
            # Authenticate request
            auth_service = AuthenticationService()
            principal = await auth_service.authenticate(req)

            # Inject principal into request
            req.principal = principal  # type: ignore[attr-defined]

            # Call handler
            return await handler(req)

        except AuthenticationError as e:
            logger.warning(f"Authentication failed: {e}")
            return _error_response(403, "Forbidden", str(e))

        except Exception as e:
            logger.error(f"Unexpected auth error: {e}", exc_info=True)
            return _error_response(500, "InternalServerError", "Authentication system error")

    return wrapper


# ==================== HELPERS ====================

def get_principal(req: func.HttpRequest) -> FunctionKeyPrincipal | UserPrincipal | None:
    """Get authenticated principal from request"""
    return getattr(req, 'principal', None)


def is_function_key_auth(req: func.HttpRequest) -> bool:
    """Check if authenticated with function key"""
    return isinstance(get_principal(req), FunctionKeyPrincipal)


def is_user_auth(req: func.HttpRequest) -> bool:
    """Check if authenticated with user credentials"""
    return isinstance(get_principal(req), UserPrincipal)


def _error_response(status_code: int, error: str, message: str) -> func.HttpResponse:
    """Create standardized error response"""
    return func.HttpResponse(
        json.dumps({"error": error, "message": message}),
        status_code=status_code,
        mimetype="application/json"
    )
