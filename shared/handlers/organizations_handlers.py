"""
Organizations Handlers
Business logic for organization management
Extracted from functions/organizations.py for unit testability
"""

import json
import logging
from typing import TYPE_CHECKING

import azure.functions as func
from pydantic import ValidationError

from shared.models import (
    CreateOrganizationRequest,
    ErrorResponse,
    Organization,
    UpdateOrganizationRequest,
)
from shared.repositories.organizations import OrganizationRepository

if TYPE_CHECKING:
    from shared.context import ExecutionContext

logger = logging.getLogger(__name__)


# ==================== BUSINESS LOGIC FUNCTIONS ====================
# These functions contain the core business logic and can be called by both
# HTTP handlers and the Bifrost SDK


async def list_organizations_logic(context: 'ExecutionContext') -> list[Organization]:
    """
    List all organizations (business logic).

    Args:
        context: Request context with user info

    Returns:
        list[Organization]: List of organization objects
    """
    logger.info(f"User {context.user_id} listing organizations")

    org_repo = OrganizationRepository()
    orgs = await org_repo.list_organizations(active_only=True)

    # Sort by name
    orgs.sort(key=lambda o: o.name)

    logger.info(f"Returning {len(orgs)} organizations for user {context.user_id}")

    return orgs


async def create_organization_logic(
    context: 'ExecutionContext',
    name: str,
    domain: str | None = None,
    is_active: bool = True
) -> Organization:
    """
    Create a new organization (business logic).

    Args:
        context: Request context with user info
        name: Organization name
        domain: Organization domain (optional)
        is_active: Whether organization is active (default: True)

    Returns:
        Organization: Created organization object
    """
    logger.info(f"User {context.user_id} creating organization: {name}")

    create_request = CreateOrganizationRequest(
        name=name,
        domain=domain
    )

    org_repo = OrganizationRepository()
    org = await org_repo.create_organization(
        org_request=create_request,
        created_by=context.user_id
    )

    logger.info(f"Created organization {org.id}: {org.name}")

    return org


async def get_organization_logic(context: 'ExecutionContext', org_id: str) -> Organization | None:
    """
    Get organization by ID (business logic).

    Args:
        context: Request context with user info
        org_id: Organization ID

    Returns:
        Organization | None: Organization object or None if not found
    """
    logger.info(f"User {context.user_id} retrieving organization {org_id}")

    org_repo = OrganizationRepository()
    org = await org_repo.get_organization(org_id)

    if not org:
        logger.warning(f"Organization {org_id} not found")

    return org


async def update_organization_logic(
    context: 'ExecutionContext',
    org_id: str,
    **updates
) -> Organization | None:
    """
    Update organization (business logic).

    Args:
        context: Request context with user info
        org_id: Organization ID
        **updates: Fields to update (name, domain, isActive)

    Returns:
        Organization | None: Updated organization object or None if not found
    """
    logger.info(f"User {context.user_id} updating organization {org_id}")

    update_request = UpdateOrganizationRequest(**updates)

    org_repo = OrganizationRepository()
    org = await org_repo.update_organization(org_id, update_request)

    if org:
        logger.info(f"Updated organization {org_id}")
    else:
        logger.warning(f"Organization {org_id} not found for update")

    return org


async def delete_organization_logic(context: 'ExecutionContext', org_id: str) -> bool:
    """
    Soft delete organization (business logic).

    Args:
        context: Request context with user info
        org_id: Organization ID

    Returns:
        bool: True if deleted, False if not found
    """
    logger.info(f"User {context.user_id} deleting organization {org_id}")

    org_repo = OrganizationRepository()
    success = await org_repo.delete_organization(org_id)

    if success:
        logger.info(f"Soft deleted organization {org_id}")
    else:
        logger.warning(f"Organization {org_id} not found for deletion")

    return success


# ==================== HTTP HANDLERS ====================
# These functions handle HTTP-specific concerns (parsing requests, returning responses)
# and delegate to the business logic functions above


async def list_organizations_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/organizations
    List all organizations (HTTP handler)
    """
    context = req.context  # type: ignore[attr-defined]

    try:
        # Call business logic
        orgs = await list_organizations_logic(context)

        # Convert to JSON
        organizations = [org.model_dump(mode="json") for org in orgs]

        return func.HttpResponse(
            json.dumps(organizations),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error listing organizations: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to list organizations"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


async def create_organization_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/organizations
    Create a new client organization (HTTP handler)
    """
    context = req.context  # type: ignore[attr-defined]

    try:
        # Parse and validate request body
        request_body = req.get_json()
        create_request = CreateOrganizationRequest(**request_body)

        # Call business logic
        org = await create_organization_logic(
            context=context,
            **create_request.model_dump()
        )

        return func.HttpResponse(
            json.dumps(org.model_dump(mode="json")),
            status_code=201,
            mimetype="application/json"
        )

    except ValidationError as e:
        logger.warning(f"Validation error creating organization: {e}")
        error = ErrorResponse(
            error="ValidationError",
            message="Invalid request data",
            details={"errors": e.errors()}
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    except ValueError as e:
        logger.error(f"Error parsing request: {str(e)}")
        error = ErrorResponse(
            error="BadRequest",
            message="Invalid JSON in request body"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error creating organization: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to create organization"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


async def get_organization_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/organizations/{orgId}
    Get a specific organization by ID (HTTP handler)
    """
    context = req.context  # type: ignore[attr-defined]
    org_id = req.route_params.get("orgId")

    assert org_id is not None, "orgId is required"

    try:
        # Call business logic
        org = await get_organization_logic(context, org_id)

        if not org:
            error = ErrorResponse(
                error="NotFound",
                message="Organization not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        return func.HttpResponse(
            json.dumps(org.model_dump(mode="json")),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error retrieving organization: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to retrieve organization"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


async def update_organization_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    PATCH /api/organizations/{orgId}
    Update an organization (HTTP handler)
    """
    context = req.context  # type: ignore[attr-defined]
    org_id = req.route_params.get("orgId")

    assert org_id is not None, "orgId is required"

    try:
        # Parse and validate update request
        request_body = req.get_json()
        update_request = UpdateOrganizationRequest(**request_body)

        # Call business logic
        org = await update_organization_logic(
            context=context,
            org_id=org_id,
            **update_request.model_dump(exclude_unset=True)
        )

        if not org:
            error = ErrorResponse(
                error="NotFound",
                message="Organization not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        return func.HttpResponse(
            json.dumps(org.model_dump(mode="json")),
            status_code=200,
            mimetype="application/json"
        )

    except ValidationError as e:
        logger.warning(f"Validation error updating organization: {e}")
        error = ErrorResponse(
            error="ValidationError",
            message="Invalid request data",
            details={"errors": e.errors()}
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error updating organization: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to update organization"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


async def delete_organization_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/organizations/{orgId}
    Soft delete an organization (HTTP handler)
    """
    context = req.context  # type: ignore[attr-defined]
    org_id = req.route_params.get("orgId")

    assert org_id is not None, "orgId is required"

    try:
        # Call business logic
        success = await delete_organization_logic(context, org_id)

        if not success:
            error = ErrorResponse(
                error="NotFound",
                message="Organization not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        return func.HttpResponse(
            status_code=204  # No Content
        )

    except Exception as e:
        logger.error(f"Error deleting organization: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to delete organization"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )
