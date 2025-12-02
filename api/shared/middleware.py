"""
Middleware Decorators
Request middleware for authentication, context loading, and permissions
"""

import functools
import json
import logging
from collections.abc import Callable

import azure.functions as func

from .context import Organization, ExecutionContext, Caller

logger = logging.getLogger(__name__)


async def load_config_for_partition(partition_key: str) -> dict:
    """
    Load configuration values for a given partition (org ID or GLOBAL).

    Extracts config entities from database and parses JSON values.

    Args:
        partition_key: Partition to load config from (org ID or "GLOBAL")

    Returns:
        Dictionary of config key-value pairs
    """
    from .storage import get_org_config_async

    config = {}
    config_entities = await get_org_config_async(partition_key)

    for entity in config_entities:
        # RowKey format: "config:{key}"
        key = entity['RowKey'].replace('config:', '', 1)
        value = entity.get('Value')

        # Parse JSON if type is json
        if entity.get('Type') == 'json':
            try:
                assert value is not None, "Value cannot be None for JSON parsing"
                value = json.loads(value)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON config: {key}")

        config[key] = value

    return config


def with_org_context(handler: Callable) -> Callable:
    """
    Decorator to load ExecutionContext from request headers.

    Extracts X-Organization-Id header (optional for platform admins), loads
    organization and config from Table Storage, and creates ExecutionContext
    object to pass to handler.

    For platform admins without org context, creates a "global" context with no
    organization but with caller information.

    Usage:
        @bp.route(route="workflows/{name}", methods=["POST"])
        @with_org_context
        async def execute_workflow(req: func.HttpRequest, context: ExecutionContext):
            # context is automatically loaded and injected
            # context.org may be None for platform admins
            pass

    Returns:
        404 Not Found: If organization doesn't exist or is inactive
        500 Internal Server Error: If context loading fails
    """
    @functools.wraps(handler)
    async def wrapper(req: func.HttpRequest, **kwargs) -> func.HttpResponse:
        # Extract organization ID from header (optional)
        org_id = req.headers.get('X-Organization-Id')

        try:
            # Load organization context (or global context if no org_id)
            context = await load_organization_context(org_id, req)

            if org_id:
                logger.info(
                    f"Organization context loaded for {context.org_name} ({org_id})",
                    extra={"org_id": org_id}
                )
            else:
                logger.info(
                    "Global context loaded (no organization)",
                    extra={"user": context.email}
                )

            # Inject context into request object
            # Use req.org_context instead of req.context to allow coexistence
            # with @with_request_context decorator
            req.org_context = context  # type: ignore[attr-defined]

            # Call handler with additional bindings (e.g., SignalR output binding)
            return await handler(req, **kwargs)

        except OrganizationNotFoundError as e:
            logger.warning(f"Organization not found: {org_id}")
            return func.HttpResponse(
                json.dumps({
                    "error": "NotFound",
                    "message": str(e)
                }),
                status_code=404,
                mimetype="application/json"
            )

        except Exception as e:
            logger.error(
                f"Failed to load organization context: {str(e)}",
                exc_info=True,
                extra={"org_id": org_id}
            )
            return func.HttpResponse(
                json.dumps({
                    "error": "InternalServerError",
                    "message": "Failed to load organization context"
                }),
                status_code=500,
                mimetype="application/json"
            )

    return wrapper


async def load_organization_context(
    org_id: str | None,
    req: func.HttpRequest
) -> ExecutionContext:
    """
    Load ExecutionContext from database.

    T037: Organization validation is enforced when org_id is provided.
    T055-T056: Uses AuthenticationService to extract caller from authenticated principal.

    If org_id is None, creates a "global" context for platform admins with no
    organization but with caller information.

    Args:
        org_id: Organization ID (optional - None for platform admins)
        req: HTTP request (for authentication and caller extraction)

    Returns: ExecutionContext object

    Raises:
        OrganizationNotFoundError: If org_id provided but org doesn't exist or is inactive
        AuthenticationError: If authentication fails
    """
    from .storage import get_organization_async

    org = None
    config = {}

    # Load organization and config
    if org_id:
        # T037: Validate organization exists and is active
        org_entity = await get_organization_async(org_id)

        if not org_entity:
            raise OrganizationNotFoundError(f"Organization {org_id} not found")

        if not org_entity.get('IsActive', False):
            raise OrganizationNotFoundError(f"Organization {org_id} is inactive")

        # Create Organization object
        # RowKey is in format "org:{uuid}", extract the UUID
        org_uuid = org_entity['RowKey'].split(':', 1)[1]
        org = Organization(
            id=org_uuid,
            name=org_entity['Name'],
            is_active=org_entity['IsActive']
        )

        # Load organization config (all config for this org)
        config = await load_config_for_partition(org_id)
    else:
        # Load GLOBAL configs for platform admin context
        logger.info("Loading GLOBAL configs for platform admin context")
        config = await load_config_for_partition("GLOBAL")

    # T056: Extract caller from authenticated principal
    # Use authentication service to get principal, then create Caller
    from shared.auth import AuthenticationService, FunctionKeyPrincipal, UserPrincipal

    auth_service = AuthenticationService()

    try:
        principal = await auth_service.authenticate(req)

        # Create Caller based on principal type
        if isinstance(principal, FunctionKeyPrincipal):
            # Function key authentication
            # Check if Management API provided X-User-Id header (for proxied requests)
            provided_user_id = req.headers.get('X-User-Id')
            if provided_user_id:
                # Use provided user context from Management API
                caller = Caller(
                    user_id=provided_user_id,
                    email=provided_user_id,  # Management API doesn't send email, use user_id
                    name=provided_user_id
                )
            else:
                # Direct function key call - system caller
                caller = Caller(
                    user_id=f"function_key:{principal.key_name}",
                    email="function-key@system.local",
                    name=f"Function Key ({principal.key_name})"
                )
        elif isinstance(principal, UserPrincipal):
            # User authentication - real user caller
            caller = Caller(
                user_id=principal.user_id,
                email=principal.email,
                name=principal.name or principal.email
            )

            # If org_id not provided and user is not platform admin, look up user's org
            if not org_id and 'PlatformAdmin' not in principal.roles:
                logger.info(f"No org_id provided for non-admin user {principal.email}, looking up from database")

                # Import here to avoid circular dependency
                from shared.user_lookup import get_user_organization

                user_org_id = await get_user_organization(principal.email)

                if user_org_id:
                    org_id = user_org_id
                    logger.info(f"Found org {org_id} for user {principal.email}")

                    # Re-load organization and config now that we have org_id
                    # T037: Validate organization exists and is active
                    org_entity = await get_organization_async(org_id)

                    if not org_entity:
                        raise OrganizationNotFoundError(f"Organization {org_id} not found")

                    if not org_entity.get('IsActive', False):
                        raise OrganizationNotFoundError(f"Organization {org_id} is inactive")

                    # Create Organization object
                    # RowKey is in format "org:{uuid}", extract the UUID
                    org_uuid = org_entity['RowKey'].split(':', 1)[1]
                    org = Organization(
                        id=org_uuid,
                        name=org_entity['Name'],
                        is_active=org_entity['IsActive']
                    )

                    # Load organization config (all config for this org)
                    config = await load_config_for_partition(org_id)
                else:
                    # User has no org assignment
                    raise OrganizationNotFoundError(
                        f"User {principal.email} has no organization assignment. "
                        "Contact your administrator to assign you to an organization."
                    )
        else:
            # Fallback (should not happen)
            caller = Caller(
                user_id="unknown",
                email="unknown@system.local",
                name="Unknown User"
            )

    except Exception as auth_error:
        # If authentication fails, let it bubble up as 403
        logger.warning(f"Authentication failed in middleware: {auth_error}")
        raise

    # Generate execution ID (will be used when logging execution)
    import uuid
    execution_id = str(uuid.uuid4())

    # Determine if user is platform admin
    is_platform_admin = isinstance(principal, FunctionKeyPrincipal) or (
        isinstance(principal, UserPrincipal) and 'PlatformAdmin' in principal.roles
    )

    # Determine is_function_key
    is_function_key = isinstance(principal, FunctionKeyPrincipal)

    # Determine scope (explicit "GLOBAL" or org ID)
    scope = "GLOBAL" if org_id is None else org_id

    # Create and return context
    context = ExecutionContext(
        # User identity
        user_id=caller.user_id,
        email=caller.email,
        name=caller.name,
        # Scope
        scope=scope,
        organization=org,
        # Authorization
        is_platform_admin=is_platform_admin,
        is_function_key=is_function_key,
        # Execution
        execution_id=execution_id,
        # Config (as keyword arg for dataclass field)
        _config=config
    )

    return context


class OrganizationNotFoundError(Exception):
    """Raised when organization is not found or inactive."""
    pass


def has_workflow_key(handler: Callable) -> Callable:
    """
    Decorator to allow workflow execution via API key, user authentication, or public access.

    Checks workflow metadata to determine authentication requirements:
    - If public_endpoint=True: Allow unauthenticated access with minimal context
    - If API key in Authorization header: Validate and create API key context
    - Otherwise: Fall back to standard user authentication via @with_org_context

    Usage:
        @bp.route(route="workflows/{workflowName}/execute", methods=["POST"])
        @has_workflow_key
        async def execute_workflow(req: func.HttpRequest):
            # Accessible via API key, authenticated user, OR public (if enabled)
            context = req.org_context
            pass

    Authorization header format:
        Authorization: Bearer wk_abc123def456...

    Returns:
        401 Unauthorized: If API key is invalid or revoked (for non-public endpoints)
        Otherwise passes through to @with_org_context decorator
    """
    @functools.wraps(handler)
    async def wrapper(req: func.HttpRequest) -> func.HttpResponse:
        # Check if this is a public endpoint (webhook)
        # Get workflow name from route params
        workflow_id = req.route_params.get('workflowName')

        if workflow_id:
            # Check workflow metadata to see if it's public
            from shared.discovery import load_workflow
            result = load_workflow(workflow_id)
            workflow_metadata = result[1] if result else None

            if workflow_metadata and workflow_metadata.public_endpoint:
                # Public endpoint - create minimal anonymous context
                logger.info(
                    f"Public endpoint access for workflow: {workflow_id}",
                    extra={"workflow_id": workflow_id}
                )

                # Create anonymous caller for public endpoints
                anonymous_caller = Caller(
                    user_id="public:anonymous",
                    email="public@system.local",
                    name="Public Access (Webhook)"
                )

                # Load GLOBAL config
                config = await load_config_for_partition("GLOBAL")

                public_context = ExecutionContext(
                    user_id=anonymous_caller.user_id,
                    email=anonymous_caller.email,
                    name=anonymous_caller.name,
                    scope="GLOBAL",
                    organization=None,
                    is_platform_admin=False,
                    is_function_key=False,
                    execution_id=str(__import__('uuid').uuid4()),
                    _config=config
                )

                # Inject context into request
                req.org_context = public_context  # type: ignore[attr-defined]

                # Call handler directly (skip auth)
                return await handler(req)

        # Not a public endpoint - proceed with authentication
        # Check for API key in Authorization header
        auth_header = req.headers.get('Authorization', '')

        if auth_header.startswith('Bearer '):
            api_key = auth_header[7:]  # Remove 'Bearer ' prefix

            # Validate API key
            from shared.workflow_keys import validate_workflow_key
            import os

            connection_str = os.environ.get("AzureWebJobsStorage", "UseDevelopmentStorage=true")

            # Extract workflow ID from route params if present
            workflow_id = req.route_params.get('workflowName')

            try:
                is_valid, key_id = await validate_workflow_key(connection_str, api_key, workflow_id)

                if is_valid:
                    # Create global scope context for API key access
                    # API key users get GLOBAL scope to access all workflows
                    logger.info(
                        f"Valid API key authentication for workflow: {workflow_id or 'global'}",
                        extra={"workflow_id": workflow_id, "key_id": key_id}
                    )

                    # Create minimal global context for API key access
                    # No organization, but with API key caller
                    # Use key_id in the caller name for logging purposes
                    api_caller = Caller(
                        user_id=f"api_key:{key_id}" if key_id else "api_key:unknown",
                        email="api-key@system.local",
                        name=f"API Key ({key_id})" if key_id else "API Key"
                    )

                    # Load GLOBAL config for platform admin context
                    config = await load_config_for_partition("GLOBAL")

                    api_context = ExecutionContext(
                        user_id=api_caller.user_id,
                        email=api_caller.email,
                        name=api_caller.name,
                        scope="GLOBAL",
                        organization=None,
                        is_platform_admin=True,
                        is_function_key=True,
                        execution_id=str(__import__('uuid').uuid4()),
                        _config=config
                    )

                    # Inject context into request
                    req.org_context = api_context  # type: ignore[attr-defined]

                    # Call handler directly (skip org context decorator)
                    return await handler(req)
                else:
                    logger.warning(
                        f"Invalid or revoked API key attempted for workflow: {workflow_id}",
                        extra={"workflow_id": workflow_id}
                    )
                    return func.HttpResponse(
                        json.dumps({
                            "error": "Unauthorized",
                            "message": "Invalid or revoked API key"
                        }),
                        status_code=401,
                        mimetype="application/json"
                    )
            except Exception as e:
                logger.error(
                    f"API key validation failed: {str(e)}",
                    exc_info=True,
                    extra={"workflow_id": workflow_id}
                )
                return func.HttpResponse(
                    json.dumps({
                        "error": "Unauthorized",
                        "message": "API key validation failed"
                    }),
                    status_code=401,
                    mimetype="application/json"
                )

        # No API key provided, fall back to standard authentication
        # Apply @with_org_context decorator
        return await with_org_context(handler)(req)

    return wrapper
