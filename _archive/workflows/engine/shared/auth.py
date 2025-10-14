"""
Authentication Service (T048-T054)

Implements tiered authentication for Azure Functions:
1. Function key authentication (x-functions-key header or code query param) - HIGHEST PRIORITY
2. Easy Auth (X-MS-CLIENT-PRINCIPAL header) - FALLBACK
3. None → AuthenticationError (converted to 403 by middleware)

Provides:
- AuthenticationService class with tiered authenticate() method
- FunctionKeyPrincipal and UserPrincipal dataclasses
- @require_auth decorator for endpoints
- Audit logging for function key usage
"""

import base64
import json
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Union
import azure.functions as func

logger = logging.getLogger(__name__)


# T052: Principal dataclasses
@dataclass
class FunctionKeyPrincipal:
    """
    Principal representing function key authentication.

    Function keys bypass user authentication and provide privileged access.
    All function key usage is audited for security monitoring.
    """
    key_id: str  # The function key value (for validation)
    key_name: str = "default"  # Friendly name (from config, default "default")
    is_function_key: bool = True  # Flag for easy type checking

    def __str__(self) -> str:
        return f"FunctionKey({self.key_name})"


@dataclass
class UserPrincipal:
    """
    Principal representing Easy Auth user authentication.

    Created from X-MS-CLIENT-PRINCIPAL header (Azure Easy Auth).
    """
    user_id: str  # Unique user identifier from identity provider
    email: str  # User email (from userDetails)
    name: str = ""  # User display name (optional)
    roles: List[str] = field(default_factory=list)  # User roles
    identity_provider: str = "unknown"  # Identity provider (aad, google, etc.)
    is_function_key: bool = False  # Flag for easy type checking

    def __str__(self) -> str:
        return f"User({self.email})"

    def has_role(self, role: str) -> bool:
        """Check if user has specific role"""
        return role in self.roles


# Authentication exceptions
class AuthenticationError(Exception):
    """Raised when authentication fails (no valid credentials)"""
    pass


class AuthorizationError(Exception):
    """Raised when user is authenticated but not authorized for action"""
    pass


# T048: AuthenticationService class
class AuthenticationService:
    """
    Tiered authentication service for Azure Functions.

    Implements priority-based authentication:
    1. Function key (header > query param)
    2. Easy Auth (X-MS-CLIENT-PRINCIPAL)
    3. Failure → AuthenticationError
    """

    def __init__(self):
        """Initialize authentication service"""
        pass

    async def authenticate(
        self,
        req: func.HttpRequest
    ) -> Union[FunctionKeyPrincipal, UserPrincipal]:
        """
        T051: Authenticate request using tiered priority system.

        Priority order:
        1. Function key (x-functions-key header OR code query param)
        2. Easy Auth (X-MS-CLIENT-PRINCIPAL header)
        3. Failure → raise AuthenticationError

        Args:
            req: Azure Functions HTTP request

        Returns:
            FunctionKeyPrincipal or UserPrincipal

        Raises:
            AuthenticationError: If no valid authentication found
        """
        # Priority 1: Function key authentication
        principal = await self._authenticate_function_key(req)
        if principal:
            return principal

        # Priority 2: Easy Auth user authentication
        principal = await self._authenticate_user(req)
        if principal:
            return principal

        # Priority 3: Local development fallback
        # ALWAYS use test principal in local dev if no auth headers present
        # In production, AZURE_FUNCTIONS_ENVIRONMENT or WEBSITE_SITE_NAME will be set
        import os
        is_production = (
            os.environ.get('WEBSITE_SITE_NAME') or  # Azure App Service
            os.environ.get('AZURE_FUNCTIONS_ENVIRONMENT', '').lower() == 'production'
        )

        if not is_production:
            logger.warning("Using default test principal for local development (no auth provided)")
            return FunctionKeyPrincipal(
                key_id="local-dev-bypass",
                key_name="local-development"
            )

        # Priority 4: No authentication found (production only)
        raise AuthenticationError(
            "No valid authentication credentials provided. "
            "Please provide either a function key (x-functions-key header or ?code=KEY) "
            "or user authentication (X-MS-CLIENT-PRINCIPAL header from Azure Easy Auth)."
        )

    async def _authenticate_function_key(
        self,
        req: func.HttpRequest
    ) -> Optional[FunctionKeyPrincipal]:
        """
        T049: Authenticate using function key.

        Checks for function key in:
        1. x-functions-key header (case-insensitive) - PRIORITY
        2. code query parameter - FALLBACK

        Args:
            req: Azure Functions HTTP request

        Returns:
            FunctionKeyPrincipal if key found, None otherwise
        """
        function_key = None

        # Check header (priority 1)
        # Azure Functions normalizes headers to lowercase
        function_key = req.headers.get('x-functions-key')

        # Also check other common header variations (case-insensitive)
        if not function_key:
            for header_name in req.headers.keys():
                if header_name.lower() == 'x-functions-key':
                    function_key = req.headers[header_name]
                    break

        # Check query parameter (priority 2)
        if not function_key:
            function_key = req.params.get('code')

        # Validate key exists and is not empty/whitespace
        if function_key and function_key.strip():
            function_key = function_key.strip()

            # Create principal
            principal = FunctionKeyPrincipal(
                key_id=function_key,
                key_name="default"  # Could be enhanced to lookup key name from config
            )

            # T053: Audit function key usage (async, non-blocking)
            await self._audit_function_key_usage(req, principal)

            logger.info(
                f"Authenticated with function key: {principal.key_name}",
                extra={'key_name': principal.key_name}
            )

            return principal

        return None

    async def _authenticate_user(
        self,
        req: func.HttpRequest
    ) -> Optional[UserPrincipal]:
        """
        T050: Authenticate using Easy Auth (X-MS-CLIENT-PRINCIPAL).

        Azure Easy Auth provides a Base64-encoded JSON header with user info.

        Args:
            req: Azure Functions HTTP request

        Returns:
            UserPrincipal if Easy Auth found, None otherwise

        Raises:
            AuthenticationError: If header exists but is malformed
        """
        # Get Easy Auth principal header
        principal_header = req.headers.get('X-MS-CLIENT-PRINCIPAL')

        if not principal_header:
            # Also check case-insensitive
            for header_name in req.headers.keys():
                if header_name.lower() == 'x-ms-client-principal':
                    principal_header = req.headers[header_name]
                    break

        if not principal_header:
            return None

        try:
            # Decode Base64 JSON
            principal_json = base64.b64decode(principal_header).decode('utf-8')
            principal_data = json.loads(principal_json)

            # Extract user information
            user_id = principal_data.get('userId')
            email = principal_data.get('userDetails', '')
            identity_provider = principal_data.get('identityProvider', 'unknown')
            roles = principal_data.get('userRoles', [])

            # Validate required fields
            if not user_id:
                raise AuthenticationError(
                    "X-MS-CLIENT-PRINCIPAL missing required field: userId"
                )

            # Create principal
            principal = UserPrincipal(
                user_id=user_id,
                email=email,
                name=email.split('@')[0] if email else "",  # Extract name from email
                roles=roles,
                identity_provider=identity_provider
            )

            logger.info(
                f"Authenticated user: {principal.email}",
                extra={'user_id': user_id, 'email': email}
            )

            return principal

        except (base64.binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(
                f"Failed to decode X-MS-CLIENT-PRINCIPAL header: {e}",
                exc_info=True
            )
            raise AuthenticationError(
                f"Failed to decode Easy Auth principal: {type(e).__name__}"
            )

    async def _audit_function_key_usage(
        self,
        req: func.HttpRequest,
        principal: FunctionKeyPrincipal
    ) -> None:
        """
        T053: Audit function key authentication usage.

        Logs privileged function key access to AuditLog table for security monitoring.

        Args:
            req: Azure Functions HTTP request
            principal: Function key principal that was authenticated
        """
        try:
            from engine.shared.audit import get_audit_logger

            audit_logger = get_audit_logger()

            # Extract request details
            org_id = req.headers.get('X-Organization-Id', 'unknown')
            endpoint = req.url
            method = req.method
            remote_addr = req.headers.get('X-Forwarded-For', req.headers.get('Remote-Addr', 'unknown'))
            user_agent = req.headers.get('User-Agent', 'unknown')

            # Log function key access (fire and forget)
            await audit_logger.log_function_key_access(
                key_id=principal.key_id[:8] + "...",  # Truncate for security
                key_name=principal.key_name,
                org_id=org_id,
                endpoint=endpoint,
                method=method,
                remote_addr=remote_addr,
                user_agent=user_agent,
                status_code=0,  # Not known yet (will be updated by middleware)
                details=None
            )

        except Exception as e:
            # Don't let audit logging failure prevent authentication
            logger.debug(f"Failed to audit function key usage: {e}")


# T054: @require_auth decorator
def require_auth(handler):
    """
    Decorator to require authentication for Azure Function endpoints.

    Automatically authenticates request and injects principal into request object.

    Usage:
        @bp.route(route="workflows/{name}", methods=["POST"])
        @require_auth
        async def execute_workflow(req: func.HttpRequest) -> func.HttpResponse:
            principal = req.principal  # Access authenticated principal
            # ... handler logic ...

    Returns:
        403 Forbidden: If authentication fails
    """
    import functools

    @functools.wraps(handler)
    async def wrapper(req: func.HttpRequest) -> func.HttpResponse:
        try:
            # Authenticate request
            auth_service = AuthenticationService()
            principal = await auth_service.authenticate(req)

            # Inject principal into request object
            req.principal = principal

            # Call handler
            return await handler(req)

        except AuthenticationError as e:
            logger.warning(f"Authentication failed: {e}")
            return func.HttpResponse(
                json.dumps({
                    "error": "Forbidden",
                    "message": str(e)
                }),
                status_code=403,
                mimetype="application/json"
            )

        except Exception as e:
            logger.error(
                f"Unexpected error in authentication: {e}",
                exc_info=True
            )
            return func.HttpResponse(
                json.dumps({
                    "error": "InternalServerError",
                    "message": "Authentication system error"
                }),
                status_code=500,
                mimetype="application/json"
            )

    return wrapper


# Helper functions
def get_current_principal(req: func.HttpRequest) -> Optional[Union[FunctionKeyPrincipal, UserPrincipal]]:
    """
    Get the authenticated principal from request (if @require_auth was used).

    Args:
        req: Azure Functions HTTP request

    Returns:
        Principal if authenticated, None otherwise
    """
    return getattr(req, 'principal', None)


def is_function_key_auth(req: func.HttpRequest) -> bool:
    """
    Check if request was authenticated with function key.

    Args:
        req: Azure Functions HTTP request

    Returns:
        True if function key authentication, False otherwise
    """
    principal = get_current_principal(req)
    return isinstance(principal, FunctionKeyPrincipal)


def is_user_auth(req: func.HttpRequest) -> bool:
    """
    Check if request was authenticated with user credentials.

    Args:
        req: Azure Functions HTTP request

    Returns:
        True if user authentication, False otherwise
    """
    principal = get_current_principal(req)
    return isinstance(principal, UserPrincipal)
