"""
Organizations API endpoints
CRUD operations for client organizations

Business logic extracted to shared/handlers/organizations_handlers.py
"""

import azure.functions as func

from shared.decorators import require_platform_admin, with_request_context
from shared.handlers.organizations_handlers import (
    create_organization_handler,
    delete_organization_handler,
    get_organization_handler,
    list_organizations_handler,
    update_organization_handler,
)
from shared.models import (
    CreateOrganizationRequest,
    Organization,
    UpdateOrganizationRequest,
)
from shared.openapi_decorators import openapi_endpoint

# Create blueprint for organizations endpoints
bp = func.Blueprint()


@bp.function_name("orgs_list_organizations")
@bp.route(route="organizations", methods=["GET"])
@openapi_endpoint(
    path="/organizations",
    method="GET",
    summary="List all organizations",
    description="Get all organizations (Platform admin only)",
    tags=["Organizations"],
    response_model=list[Organization]
)
@with_request_context
@require_platform_admin
async def list_organizations(req: func.HttpRequest) -> func.HttpResponse:
    """List all organizations"""
    return await list_organizations_handler(req)


@bp.function_name("orgs_create_organization")
@bp.route(route="organizations", methods=["POST"])
@openapi_endpoint(
    path="/organizations",
    method="POST",
    summary="Create a new organization",
    description="Create a new client organization (Platform admin only)",
    tags=["Organizations"],
    request_model=CreateOrganizationRequest,
    response_model=Organization
)
@with_request_context
@require_platform_admin
async def create_organization(req: func.HttpRequest) -> func.HttpResponse:
    """Create a new client organization"""
    return await create_organization_handler(req)


@bp.function_name("orgs_get_organization")
@bp.route(route="organizations/{orgId}", methods=["GET"])
@openapi_endpoint(
    path="/organizations/{orgId}",
    method="GET",
    summary="Get organization by ID",
    description="Get a specific organization by ID (Platform admin only)",
    tags=["Organizations"],
    response_model=Organization,
    path_params={
        "orgId": {
            "description": "Organization ID (UUID)",
            "schema": {"type": "string", "format": "uuid"}
        }
    }
)
@with_request_context
@require_platform_admin
async def get_organization(req: func.HttpRequest) -> func.HttpResponse:
    """Get a specific organization by ID"""
    return await get_organization_handler(req)


@bp.function_name("orgs_update_organization")
@bp.route(route="organizations/{orgId}", methods=["PATCH"])
@openapi_endpoint(
    path="/organizations/{orgId}",
    method="PATCH",
    summary="Update an organization",
    description="Update an existing organization (Platform admin only)",
    tags=["Organizations"],
    request_model=UpdateOrganizationRequest,
    response_model=Organization,
    path_params={
        "orgId": {
            "description": "Organization ID (UUID)",
            "schema": {"type": "string", "format": "uuid"}
        }
    }
)
@with_request_context
@require_platform_admin
async def update_organization(req: func.HttpRequest) -> func.HttpResponse:
    """Update an organization"""
    return await update_organization_handler(req)


@bp.function_name("orgs_delete_organization")
@bp.route(route="organizations/{orgId}", methods=["DELETE"])
@openapi_endpoint(
    path="/organizations/{orgId}",
    method="DELETE",
    summary="Delete an organization",
    description="Soft delete an organization (sets IsActive=False, Platform admin only)",
    tags=["Organizations"],
    path_params={
        "orgId": {
            "description": "Organization ID (UUID)",
            "schema": {"type": "string", "format": "uuid"}
        }
    }
)
@with_request_context
@require_platform_admin
async def delete_organization(req: func.HttpRequest) -> func.HttpResponse:
    """Soft delete an organization"""
    return await delete_organization_handler(req)
