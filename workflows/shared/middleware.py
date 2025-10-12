"""
Middleware Decorators
Request middleware for authentication, context loading, and permissions
"""

import functools
import json
import logging
from typing import Callable
import azure.functions as func

from .context import OrganizationContext, Organization, Caller

logger = logging.getLogger(__name__)


def with_org_context(handler: Callable) -> Callable:
    """
    Decorator to load OrganizationContext from request headers.

    Extracts X-Organization-Id header, loads organization and config from
    Table Storage, and creates OrganizationContext object to pass to handler.

    Usage:
        @bp.route(route="workflows/{name}", methods=["POST"])
        @with_org_context
        async def execute_workflow(req: func.HttpRequest, context: OrganizationContext):
            # context is automatically loaded and injected
            pass

    Returns:
        400 Bad Request: If X-Organization-Id header missing
        404 Not Found: If organization doesn't exist or is inactive
        500 Internal Server Error: If context loading fails
    """
    @functools.wraps(handler)
    async def wrapper(req: func.HttpRequest) -> func.HttpResponse:
        # Extract organization ID from header
        org_id = req.headers.get('X-Organization-Id')

        if not org_id:
            logger.warning("Missing X-Organization-Id header in request")
            return func.HttpResponse(
                json.dumps({
                    "error": "BadRequest",
                    "message": "Missing required header: X-Organization-Id"
                }),
                status_code=400,
                mimetype="application/json"
            )

        try:
            # Load organization context
            context = load_organization_context(org_id, req)

            logger.info(
                f"Organization context loaded for {context.org_name} ({org_id})",
                extra={"org_id": org_id}
            )

            # Inject context into request object
            req.context = context

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


def load_organization_context(
    org_id: str,
    req: func.HttpRequest
) -> OrganizationContext:
    """
    Load OrganizationContext from Table Storage.

    Args:
        org_id: Organization ID
        req: HTTP request (for extracting caller info)

    Returns:
        OrganizationContext object

    Raises:
        OrganizationNotFoundError: If org doesn't exist or is inactive
    """
    from .storage import get_organization, get_org_config

    # Load organization from Organizations table
    org_entity = get_organization(org_id)

    if not org_entity:
        raise OrganizationNotFoundError(f"Organization {org_id} not found")

    if not org_entity.get('IsActive', False):
        raise OrganizationNotFoundError(f"Organization {org_id} is inactive")

    # Create Organization object
    org = Organization(
        org_id=org_entity['RowKey'],
        name=org_entity['Name'],
        tenant_id=org_entity.get('TenantId'),
        is_active=org_entity['IsActive']
    )

    # Load organization config (all config for this org)
    config_entities = get_org_config(org_id)
    config = {}

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

    # Extract caller from request
    # TODO: Extract from JWT token when auth is implemented
    # For now, use a placeholder
    caller = Caller(
        user_id="system",  # Will be from JWT
        email="system@platform.local",
        name="System User"
    )

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
