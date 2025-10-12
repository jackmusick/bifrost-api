"""
Organizations API endpoints
CRUD operations for client organizations
"""

import logging
import json
import uuid
from datetime import datetime
from typing import List
import azure.functions as func

from shared.auth import require_auth, get_org_id
from shared.storage import TableStorageService
from shared.models import (
    Organization,
    CreateOrganizationRequest,
    UpdateOrganizationRequest,
    ErrorResponse
)
from pydantic import ValidationError

logger = logging.getLogger(__name__)

# Create blueprint for organizations endpoints
bp = func.Blueprint()


@bp.function_name("orgs_list_organizations")
@bp.route(route="organizations", methods=["GET"])
@require_auth
def list_organizations(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/organizations
    List all organizations

    - Platform Admins: See all organizations
    - Organization Users: Access denied (403)
    """
    from shared.auth import is_platform_admin

    user = req.user
    logger.info(f"User {user.email} listing organizations")

    try:
        # Check if user is platform admin
        if not is_platform_admin(user.user_id):
            logger.warning(f"User {user.email} is not a platform admin - denied org list access")
            error = ErrorResponse(
                error="Forbidden",
                message="Only platform administrators can list organizations"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        # Platform admin - get ALL organizations
        orgs_service = TableStorageService("Organizations")
        org_entities = list(orgs_service.query_entities(
            filter="PartitionKey eq 'ORG' and IsActive eq true"
        ))

        organizations = []
        for org_entity in org_entities:
            org = Organization(
                id=org_entity["RowKey"],
                name=org_entity["Name"],
                tenantId=org_entity.get("TenantId"),
                isActive=org_entity.get("IsActive", True),
                createdAt=org_entity["CreatedAt"],
                createdBy=org_entity["CreatedBy"],
                updatedAt=org_entity["UpdatedAt"]
            )
            organizations.append(org.model_dump(mode="json"))

        # Sort by name
        organizations.sort(key=lambda o: o["name"])

        logger.info(f"Returning {len(organizations)} organizations for platform admin {user.email}")

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


@bp.function_name("orgs_create_organization")
@bp.route(route="organizations", methods=["POST"])
@require_auth
def create_organization(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/organizations
    Create a new client organization
    """
    user = req.user
    logger.info(f"User {user.email} creating organization")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        create_request = CreateOrganizationRequest(**request_body)

        # Generate new organization ID
        org_id = f"org-{uuid.uuid4()}"
        now = datetime.utcnow()

        # Create entity for Table Storage
        entity = {
            "PartitionKey": "ORG",
            "RowKey": org_id,
            "Name": create_request.name,
            "TenantId": create_request.tenantId,
            "IsActive": True,
            "CreatedAt": now.isoformat(),
            "CreatedBy": user.user_id,
            "UpdatedAt": now.isoformat()
        }

        # Insert into Organizations table
        orgs_service = TableStorageService("Organizations")
        orgs_service.insert_entity(entity)

        logger.info(f"Created organization {org_id}: {create_request.name}")

        # Create response model
        org = Organization(
            id=org_id,
            name=create_request.name,
            tenantId=create_request.tenantId,
            isActive=True,
            createdAt=now,
            createdBy=user.user_id,
            updatedAt=now
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


@bp.function_name("orgs_get_organization")
@bp.route(route="organizations/{orgId}", methods=["GET"])
@require_auth
def get_organization(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/organizations/{orgId}
    Get a specific organization by ID
    """
    user = req.user
    org_id = req.route_params.get("orgId")

    logger.info(f"User {user.email} retrieving organization {org_id}")

    try:
        # Check if user has access to this org
        permissions_service = TableStorageService("UserPermissions")
        permission = permissions_service.get_entity(user.user_id, org_id)

        if not permission:
            logger.warning(f"User {user.email} denied access to org {org_id}")
            error = ErrorResponse(
                error="Forbidden",
                message="You don't have access to this organization"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        # Get organization
        orgs_service = TableStorageService("Organizations")
        org_entity = orgs_service.get_entity("ORG", org_id)

        if not org_entity:
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

        # Create response model
        org = Organization(
            id=org_entity["RowKey"],
            name=org_entity["Name"],
            tenantId=org_entity.get("TenantId"),
            isActive=org_entity.get("IsActive", True),
            createdAt=org_entity["CreatedAt"],
            createdBy=org_entity["CreatedBy"],
            updatedAt=org_entity["UpdatedAt"]
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


@bp.function_name("orgs_update_organization")
@bp.route(route="organizations/{orgId}", methods=["PATCH"])
@require_auth
def update_organization(req: func.HttpRequest) -> func.HttpResponse:
    """
    PATCH /api/organizations/{orgId}
    Update an organization
    """
    user = req.user
    org_id = req.route_params.get("orgId")

    logger.info(f"User {user.email} updating organization {org_id}")

    try:
        # Check if user has canManageConfig permission
        permissions_service = TableStorageService("UserPermissions")
        permission = permissions_service.get_entity(user.user_id, org_id)

        if not permission:
            error = ErrorResponse(
                error="Forbidden",
                message="You don't have access to this organization"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        if not permission.get("CanManageConfig", False):
            error = ErrorResponse(
                error="Forbidden",
                message="You don't have permission to manage this organization"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        # Get existing organization
        orgs_service = TableStorageService("Organizations")
        org_entity = orgs_service.get_entity("ORG", org_id)

        if not org_entity:
            error = ErrorResponse(
                error="NotFound",
                message="Organization not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Parse and validate update request
        request_body = req.get_json()
        update_request = UpdateOrganizationRequest(**request_body)

        # Update fields if provided
        if update_request.name is not None:
            org_entity["Name"] = update_request.name

        if update_request.tenantId is not None:
            org_entity["TenantId"] = update_request.tenantId

        if update_request.isActive is not None:
            org_entity["IsActive"] = update_request.isActive

        org_entity["UpdatedAt"] = datetime.utcnow().isoformat()

        # Update in table storage
        orgs_service.update_entity(org_entity)

        logger.info(f"Updated organization {org_id}")

        # Create response model
        org = Organization(
            id=org_entity["RowKey"],
            name=org_entity["Name"],
            tenantId=org_entity.get("TenantId"),
            isActive=org_entity.get("IsActive", True),
            createdAt=org_entity["CreatedAt"],
            createdBy=org_entity["CreatedBy"],
            updatedAt=org_entity["UpdatedAt"]
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


@bp.function_name("orgs_delete_organization")
@bp.route(route="organizations/{orgId}", methods=["DELETE"])
@require_auth
def delete_organization(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/organizations/{orgId}
    Soft delete an organization (sets IsActive=False)
    """
    user = req.user
    org_id = req.route_params.get("orgId")

    logger.info(f"User {user.email} deleting organization {org_id}")

    try:
        # Check if user has canManageConfig permission
        permissions_service = TableStorageService("UserPermissions")
        permission = permissions_service.get_entity(user.user_id, org_id)

        if not permission:
            error = ErrorResponse(
                error="Forbidden",
                message="You don't have access to this organization"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        if not permission.get("CanManageConfig", False):
            error = ErrorResponse(
                error="Forbidden",
                message="You don't have permission to manage this organization"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        # Get existing organization
        orgs_service = TableStorageService("Organizations")
        org_entity = orgs_service.get_entity("ORG", org_id)

        if not org_entity:
            error = ErrorResponse(
                error="NotFound",
                message="Organization not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Soft delete - set IsActive to False
        org_entity["IsActive"] = False
        org_entity["UpdatedAt"] = datetime.utcnow().isoformat()

        orgs_service.update_entity(org_entity)

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
