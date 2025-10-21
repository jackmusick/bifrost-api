"""
Roles API endpoints
- Manage roles for organization users
- Assign users to roles (UserRoles)
- Assign forms to roles (FormRoles)
"""

import logging

import azure.functions as func

from shared.decorators import require_platform_admin, with_request_context
from shared.models import (
    Role,
    RoleFormsResponse,
    RoleUsersResponse,
)
from shared.openapi_decorators import openapi_endpoint
from shared.handlers.roles_handlers import (
    assign_forms_to_role_handler,
    assign_users_to_role_handler,
    create_role_handler,
    delete_role_handler,
    get_role_forms_handler,
    get_role_users_handler,
    list_roles_handler,
    remove_form_from_role_handler,
    remove_user_from_role_handler,
    update_role_handler,
)

logger = logging.getLogger(__name__)

# Create blueprint for roles endpoints
bp = func.Blueprint()


@bp.function_name("roles_list_roles")
@bp.route(route="roles", methods=["GET"])
@openapi_endpoint(
    path="/roles",
    method="GET",
    summary="List all roles",
    description="Get all roles (Platform admin only)",
    tags=["Roles"],
    response_model=list[Role]
)
@with_request_context
@require_platform_admin
async def list_roles(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/roles
    List all roles

    Platform admin only endpoint
    """
    return await list_roles_handler(req)


@bp.function_name("roles_create_role")
@bp.route(route="roles", methods=["POST"])
@openapi_endpoint(
    path="/roles",
    method="POST",
    summary="Create a role",
    description="Create a new role (Platform admin only)",
    tags=["Roles"],
    request_model=Role,
    response_model=Role
)
@with_request_context
@require_platform_admin
async def create_role(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/roles
    Create a new role

    Platform admin only endpoint
    """
    return await create_role_handler(req)


@bp.function_name("roles_update_role")
@bp.route(route="roles/{roleId}", methods=["PUT"])
@openapi_endpoint(
    path="/roles/{roleId}",
    method="PUT",
    summary="Update a role",
    description="Update a role (Platform admin only)",
    tags=["Roles"],
    request_model=Role,
    response_model=Role,
    path_params={
        "roleId": {
            "description": "Role ID (UUID)",
            "schema": {"type": "string", "format": "uuid"}
        }
    }
)
@with_request_context
@require_platform_admin
async def update_role(req: func.HttpRequest) -> func.HttpResponse:
    """
    PUT /api/roles/{roleId}
    Update a role

    Platform admin only endpoint
    """
    role_id = req.route_params.get("roleId")
    assert role_id is not None, "roleId is required"
    return await update_role_handler(req, role_id)


@bp.function_name("roles_delete_role")
@bp.route(route="roles/{roleId}", methods=["DELETE"])
@openapi_endpoint(
    path="/roles/{roleId}",
    method="DELETE",
    summary="Delete a role",
    description="Soft delete a role (set IsActive=False) (Platform admin only)",
    tags=["Roles"],
    path_params={
        "roleId": {
            "description": "Role ID (UUID)",
            "schema": {"type": "string", "format": "uuid"}
        }
    }
)
@with_request_context
@require_platform_admin
async def delete_role(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/roles/{roleId}
    Soft delete a role (set IsActive=False)

    Platform admin only endpoint
    """
    role_id = req.route_params.get("roleId")
    assert role_id is not None, "roleId is required"
    return await delete_role_handler(req, role_id)


@bp.function_name("roles_get_role_users")
@bp.route(route="roles/{roleId}/users", methods=["GET"])
@openapi_endpoint(
    path="/roles/{roleId}/users",
    method="GET",
    summary="Get role users",
    description="Get all users assigned to a role (Platform admin only)",
    tags=["Roles"],
    response_model=RoleUsersResponse,
    path_params={
        "roleId": {
            "description": "Role ID (UUID)",
            "schema": {"type": "string", "format": "uuid"}
        }
    }
)
@with_request_context
@require_platform_admin
async def get_role_users(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/roles/{roleId}/users
    Get all users assigned to a role

    Platform admin only endpoint
    """
    role_id = req.route_params.get("roleId")
    assert role_id is not None, "roleId is required"
    return await get_role_users_handler(req, role_id)


@bp.function_name("roles_assign_users_to_role")
@bp.route(route="roles/{roleId}/users", methods=["POST"])
@openapi_endpoint(
    path="/roles/{roleId}/users",
    method="POST",
    summary="Assign users to role",
    description="Assign users to a role (batch operation) (Platform admin only)",
    tags=["Roles"],
    request_model=Role,
    path_params={
        "roleId": {
            "description": "Role ID (UUID)",
            "schema": {"type": "string", "format": "uuid"}
        }
    }
)
@with_request_context
@require_platform_admin
async def assign_users_to_role(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/roles/{roleId}/users
    Assign users to a role (batch operation)

    Platform admin only endpoint
    """
    role_id = req.route_params.get("roleId")
    assert role_id is not None, "roleId is required"
    return await assign_users_to_role_handler(req, role_id)


@bp.function_name("roles_remove_user_from_role")
@bp.route(route="roles/{roleId}/users/{userId}", methods=["DELETE"])
@openapi_endpoint(
    path="/roles/{roleId}/users/{userId}",
    method="DELETE",
    summary="Remove user from role",
    description="Remove a user from a role (Platform admin only)",
    tags=["Roles"],
    path_params={
        "roleId": {
            "description": "Role ID (UUID)",
            "schema": {"type": "string", "format": "uuid"}
        },
        "userId": {
            "description": "User ID",
            "schema": {"type": "string"}
        }
    }
)
@with_request_context
@require_platform_admin
async def remove_user_from_role(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/roles/{roleId}/users/{userId}
    Remove a user from a role

    Platform admin only endpoint
    """
    role_id = req.route_params.get("roleId")
    user_id = req.route_params.get("userId")
    return await remove_user_from_role_handler(req, role_id or "", user_id or "")


@bp.function_name("roles_get_role_forms")
@bp.route(route="roles/{roleId}/forms", methods=["GET"])
@openapi_endpoint(
    path="/roles/{roleId}/forms",
    method="GET",
    summary="Get role forms",
    description="Get all forms assigned to a role (Platform admin only)",
    tags=["Roles"],
    response_model=RoleFormsResponse,
    path_params={
        "roleId": {
            "description": "Role ID (UUID)",
            "schema": {"type": "string", "format": "uuid"}
        }
    }
)
@with_request_context
@require_platform_admin
async def get_role_forms(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/roles/{roleId}/forms
    Get all forms assigned to a role

    Platform admin only endpoint
    """
    role_id = req.route_params.get("roleId")
    assert role_id is not None, "roleId is required"
    return await get_role_forms_handler(req, role_id)


@bp.function_name("roles_assign_forms_to_role")
@bp.route(route="roles/{roleId}/forms", methods=["POST"])
@openapi_endpoint(
    path="/roles/{roleId}/forms",
    method="POST",
    summary="Assign forms to role",
    description="Assign forms to a role (batch operation) (Platform admin only)",
    tags=["Roles"],
    request_model=Role,
    path_params={
        "roleId": {
            "description": "Role ID (UUID)",
            "schema": {"type": "string", "format": "uuid"}
        }
    }
)
@with_request_context
@require_platform_admin
async def assign_forms_to_role(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/roles/{roleId}/forms
    Assign forms to a role (batch operation)

    Platform admin only endpoint
    """
    role_id = req.route_params.get("roleId")
    assert role_id is not None, "roleId is required"
    return await assign_forms_to_role_handler(req, role_id)


@bp.function_name("roles_remove_form_from_role")
@bp.route(route="roles/{roleId}/forms/{formId}", methods=["DELETE"])
@openapi_endpoint(
    path="/roles/{roleId}/forms/{formId}",
    method="DELETE",
    summary="Remove form from role",
    description="Remove a form from a role (Platform admin only)",
    tags=["Roles"],
    path_params={
        "roleId": {
            "description": "Role ID (UUID)",
            "schema": {"type": "string", "format": "uuid"}
        },
        "formId": {
            "description": "Form ID (UUID)",
            "schema": {"type": "string", "format": "uuid"}
        }
    }
)
@with_request_context
@require_platform_admin
async def remove_form_from_role(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/roles/{roleId}/forms/{formId}
    Remove a form from a role

    Platform admin only endpoint
    """
    role_id = req.route_params.get("roleId")
    form_id = req.route_params.get("formId")
    return await remove_form_from_role_handler(req, role_id or "", form_id or "")
