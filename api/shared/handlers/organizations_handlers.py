"""
Organizations Handlers
Business logic for organization management
Extracted from functions/organizations.py for unit testability
"""

import json
import logging

import azure.functions as func
from pydantic import ValidationError

from shared.models import (
    CreateOrganizationRequest,
    ErrorResponse,
    UpdateOrganizationRequest,
)
from shared.repositories.organizations import OrganizationRepository

logger = logging.getLogger(__name__)


async def list_organizations_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/organizations
    List all organizations

    - Platform Admins: See all organizations
    - Organization Users: Access denied (403)
    """
    context = req.context  # type: ignore[attr-defined]
    logger.info(f"User {context.user_id} listing organizations")

    try:
        # Platform admin - get ALL organizations using repository
        org_repo = OrganizationRepository()
        orgs = org_repo.list_organizations(active_only=True)

        # Convert to JSON
        organizations = [org.model_dump(mode="json") for org in orgs]

        # Sort by name
        organizations.sort(key=lambda o: o["name"])

        logger.info(f"Returning {len(organizations)} organizations for platform admin {context.user_id}")

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
    Create a new client organization
    """
    context = req.context  # type: ignore[attr-defined]
    logger.info(f"User {context.user_id} creating organization")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        create_request = CreateOrganizationRequest(**request_body)

        # Create organization using repository
        org_repo = OrganizationRepository()
        org = org_repo.create_organization(
            org_request=create_request,
            created_by=context.user_id
        )

        logger.info(f"Created organization {org.id}: {org.name}")

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
    Get a specific organization by ID

    Platform admin only endpoint
    """
    context = req.context  # type: ignore[attr-defined]
    org_id = req.route_params.get("orgId")

    assert org_id is not None, "orgId is required"

    logger.info(f"User {context.user_id} retrieving organization {org_id}")

    try:
        # Get organization using repository
        org_repo = OrganizationRepository()
        org = org_repo.get_organization(org_id)

        if not org:
            logger.warning(f"Organization {org_id} not found")
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
    Update an organization

    Platform admin only endpoint
    """
    context = req.context  # type: ignore[attr-defined]
    org_id = req.route_params.get("orgId")

    assert org_id is not None, "orgId is required"

    logger.info(f"User {context.user_id} updating organization {org_id}")

    try:
        # Parse and validate update request
        request_body = req.get_json()
        update_request = UpdateOrganizationRequest(**request_body)

        # Update organization using repository
        org_repo = OrganizationRepository()
        org = org_repo.update_organization(org_id, update_request)

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

        logger.info(f"Updated organization {org_id}")

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
    Soft delete an organization (sets IsActive=False)

    Platform admin only endpoint
    """
    context = req.context  # type: ignore[attr-defined]
    org_id = req.route_params.get("orgId")

    assert org_id is not None, "orgId is required"

    logger.info(f"User {context.user_id} deleting organization {org_id}")

    try:
        # Soft delete organization using repository
        org_repo = OrganizationRepository()
        success = org_repo.delete_organization(org_id)

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

        logger.info(f"Soft deleted organization {org_id}")

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
