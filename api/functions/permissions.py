"""
Users API endpoints
- List and manage users
- View user roles and forms
"""

import logging

import azure.functions as func

from shared.custom_types import get_context, get_route_param
from shared.decorators import require_platform_admin, with_request_context
from shared.handlers.permissions_handlers import (
    get_user_forms_handler,
    get_user_handler,
    get_user_roles_handler,
    list_users_handler,
)
from shared.models import (
    User,
    UserFormsResponse,
    UserRolesResponse,
)
from shared.openapi_decorators import openapi_endpoint

logger = logging.getLogger(__name__)

# Create blueprint for user endpoints
bp = func.Blueprint()


@bp.function_name("permissions_list_users")
@bp.route(route="users", methods=["GET"])
@openapi_endpoint(
    path="/users",
    method="GET",
    summary="List users",
    description="List all users with optional filtering by type and organization (Platform admin only)",
    tags=["Users"],
    response_model=list[User],
    query_params={
        "type": {
            "description": "Filter by user type: 'platform' or 'org'",
            "schema": {"type": "string", "enum": ["platform", "org"]},
            "required": False
        },
        "orgId": {
            "description": "Filter org users by organization ID",
            "schema": {"type": "string", "format": "uuid"},
            "required": False
        }
    }
)
@with_request_context
@require_platform_admin
async def list_users(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/users?type=platform|org&orgId={id}
    List users with optional filtering by type

    Query params:
        type: Filter by user type (platform or org), optional
        orgId: Filter org users by organization, optional

    Platform admin only endpoint
    """
    context = get_context(req)
    user_type_filter = req.params.get("type", "")
    org_id_filter = req.params.get("orgId")

    return await list_users_handler(context, user_type_filter, org_id_filter)


@bp.function_name("permissions_get_user")
@bp.route(route="users/{userId}", methods=["GET"])
@openapi_endpoint(
    path="/users/{userId}",
    method="GET",
    summary="Get user details",
    description="Get a specific user's details (Platform admin only)",
    tags=["Users"],
    path_params={
        "userId": {
            "description": "User ID",
            "schema": {"type": "string"},
            "required": True
        }
    },
    response_model=User
)
@with_request_context
@require_platform_admin
async def get_user(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/users/{userId}
    Get a specific user's details

    Note: User ID should match the authenticated user's ID from Azure AD.
    For local development with SWA CLI, use the email address as the user ID
    when logging in (SWA CLI allows you to specify any userId value).

    Platform admin only endpoint
    """
    context = get_context(req)
    user_id = get_route_param(req, "userId")

    return await get_user_handler(context, user_id)


@bp.function_name("permissions_get_user_roles")
@bp.route(route="users/{userId}/roles", methods=["GET"])
@openapi_endpoint(
    path="/users/{userId}/roles",
    method="GET",
    summary="Get user roles",
    description="Get all roles assigned to a user (Platform admin only)",
    tags=["Users", "Roles"],
    response_model=UserRolesResponse,
    path_params={
        "userId": {
            "description": "User ID",
            "schema": {"type": "string"},
            "required": True
        }
    }
)
@with_request_context
@require_platform_admin
async def get_user_roles(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/users/{userId}/roles
    Get all roles assigned to a user

    Platform admin only endpoint
    """
    context = get_context(req)
    user_id = get_route_param(req, "userId")

    return await get_user_roles_handler(context, user_id)


@bp.function_name("permissions_get_user_forms")
@bp.route(route="users/{userId}/forms", methods=["GET"])
@openapi_endpoint(
    path="/users/{userId}/forms",
    method="GET",
    summary="Get user forms",
    description="Get all forms a user can access based on their roles (Platform admin only)",
    tags=["Users", "Forms"],
    response_model=UserFormsResponse,
    path_params={
        "userId": {
            "description": "User ID",
            "schema": {"type": "string"},
            "required": True
        }
    }
)
@with_request_context
@require_platform_admin
async def get_user_forms(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/users/{userId}/forms
    Get all forms a user can access based on their roles

    Access logic:
    - Platform admins: Return all forms
    - Regular users: Return forms based on role assignments

    Platform admin only endpoint
    """
    context = get_context(req)
    user_id = get_route_param(req, "userId")

    return await get_user_forms_handler(context, user_id)
