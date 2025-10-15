"""
Middleware Decorators
Request middleware for authentication, context loading, and permissions
"""

import functools
import json
import logging
from typing import Callable, Optional
import azure.functions as func

from .context import OrganizationContext, Organization, Caller

logger = logging.getLogger(__name__)


def with_org_context(handler: Callable) -> Callable:
    """
    Decorator to load OrganizationContext from request headers.

    Extracts X-Organization-Id header (optional for platform admins), loads
    organization and config from Table Storage, and creates OrganizationContext
    object to pass to handler.

    For platform admins without org context, creates a "global" context with no
    organization but with caller information.

    Usage:
        @bp.route(route="workflows/{name}", methods=["POST"])
        @with_org_context
        async def execute_workflow(req: func.HttpRequest, context: OrganizationContext):
            # context is automatically loaded and injected
            # context.org may be None for platform admins
            pass

    Returns:
        404 Not Found: If organization doesn't exist or is inactive
        500 Internal Server Error: If context loading fails
    """
    @functools.wraps(handler)
    async def wrapper(req: func.HttpRequest) -> func.HttpResponse:
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
                    extra={"user": context.caller.email}
                )

            # Inject context into request object
            # Use req.org_context instead of req.context to allow coexistence
            # with @with_request_context decorator
            req.org_context = context

            # Call handler
            return await handler(req)

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
    org_id: Optional[str],
    req: func.HttpRequest
) -> OrganizationContext:
    """
    Load OrganizationContext from Table Storage.

    T037: Organization validation is enforced when org_id is provided.
    T055-T056: Uses AuthenticationService to extract caller from authenticated principal.

    If org_id is None, creates a "global" context for platform admins with no
    organization but with caller information.

    Args:
        org_id: Organization ID (optional - None for platform admins)
        req: HTTP request (for authentication and caller extraction)

    Returns:
        OrganizationContext object

    Raises:
        OrganizationNotFoundError: If org_id provided but org doesn't exist or is inactive
        AuthenticationError: If authentication fails
    """
    from .storage import get_organization, get_org_config

    org = None
    config = {}

    # Load organization and config
    if org_id:
        # T037: Validate organization exists and is active
        org_entity = get_organization(org_id)

        if not org_entity:
            raise OrganizationNotFoundError(f"Organization {org_id} not found")

        if not org_entity.get('IsActive', False):
            raise OrganizationNotFoundError(f"Organization {org_id} is inactive")

        # Create Organization object
        # RowKey is in format "org:{uuid}", extract the UUID
        org_uuid = org_entity['RowKey'].split(':', 1)[1]
        org = Organization(
            org_id=org_uuid,
            name=org_entity['Name'],
            tenant_id=org_entity.get('TenantId'),
            is_active=org_entity['IsActive']
        )

        # Load organization config (all config for this org)
        config_entities = get_org_config(org_id)

        for entity in config_entities:
            # RowKey format: "config:{key}"
            key = entity['RowKey'].replace('config:', '', 1)
            value = entity.get('Value')

            # Parse JSON if type is json
            if entity.get('Type') == 'json':
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON config: {key}")

            config[key] = value
    else:
        # Load GLOBAL configs for platform admin context
        logger.info("Loading GLOBAL configs for platform admin context")
        config_entities = get_org_config("GLOBAL")

        for entity in config_entities:
            # RowKey format: "config:{key}"
            key = entity['RowKey'].replace('config:', '', 1)
            value = entity.get('Value')

            # Parse JSON if type is json
            if entity.get('Type') == 'json':
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON config: {key}")

            config[key] = value

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

    # Create and return context
    context = OrganizationContext(
        org=org,
        config=config,
        caller=caller,
        execution_id=execution_id
    )

    return context


class OrganizationNotFoundError(Exception):
    """Raised when organization is not found or inactive."""
    pass
