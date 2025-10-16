"""
Permissions API endpoints
- Manage user permissions for organizations
- List users and their access rights
"""

import json
import logging

import azure.functions as func

from shared.custom_types import get_context, get_route_param
from shared.decorators import require_platform_admin, with_request_context
from shared.models import (
    ErrorResponse,
    GrantPermissionsRequest,
    User,
    UserFormsResponse,
    UserRolesResponse,
)
from shared.openapi_decorators import openapi_endpoint
from shared.storage import get_table_service

logger = logging.getLogger(__name__)

# Create blueprint for permissions endpoints
bp = func.Blueprint()


@bp.function_name("permissions_list_users")
@bp.route(route="users", methods=["GET"])
@openapi_endpoint(
    path="/users",
    method="GET",
    summary="List users",
    description="List all users with optional filtering by type and organization (Platform admin only)",
    tags=["Users", "Permissions"],
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
    user_type_filter = req.params.get("type", "").lower()
    org_id_filter = req.params.get("orgId")

    logger.info(f"User {context.user_id} listing users (type={user_type_filter}, orgId={org_id_filter})")

    try:
        # Query Users table (no context needed - uses custom partitioning)
        users_service = get_table_service("Users", context)

        # Build filter based on type
        if user_type_filter == "platform":
            filter_query = "PartitionKey eq 'USER' and UserType eq 'PLATFORM'"
        elif user_type_filter == "org":
            filter_query = "PartitionKey eq 'USER' and UserType eq 'ORG'"
        else:
            filter_query = "PartitionKey eq 'USER'"

        user_entities = list(users_service.query_entities(filter=filter_query))

        # Convert to response models
        users = []
        for entity in user_entities:
            # Skip if orgId filter specified and doesn't match
            # Note: ORG users don't have a single orgId - they're assigned via permissions
            # For now, we'll skip this complex filtering
            # TODO: Filter by UserPermissions table for org-specific users

            user_model = User(
                id=entity["RowKey"],
                email=entity["Email"],
                displayName=entity["DisplayName"],
                userType=entity.get("UserType", "PLATFORM"),
                isPlatformAdmin=entity.get("IsPlatformAdmin", False),
                isActive=entity.get("IsActive", True),
                lastLogin=entity.get("LastLoginAt"),
                createdAt=entity["CreatedAt"]
            )
            users.append(user_model.model_dump(mode="json"))

        # Sort by lastLogin descending (most recent first), handle None values
        users.sort(key=lambda u: u.get("lastLogin") or "", reverse=True)

        logger.info(f"Returning {len(users)} users")

        return func.HttpResponse(
            json.dumps(users),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error listing users: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to list users"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("permissions_get_user")
@bp.route(route="users/{userId}", methods=["GET"])
@openapi_endpoint(
    path="/users/{userId}",
    method="GET",
    summary="Get user details",
    description="Get a specific user's details (Platform admin only)",
    tags=["Users", "Permissions"],
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

    logger.info(f"User {context.user_id} retrieving details for user {user_id}")

    try:
        # Get user from Users table (no context needed - uses custom partitioning)
        users_service = get_table_service("Users", context)
        try:
            user_entity = users_service.get_entity("USER", user_id)
        except Exception:
            user_entity = None

        if not user_entity:
            logger.warning(f"User not found: {user_id}")
            error = ErrorResponse(
                error="NotFound",
                message="User not found in system"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Convert to response model
        user_model = User(
            id=user_entity["RowKey"],
            email=user_entity["Email"],
            displayName=user_entity["DisplayName"],
            userType=user_entity.get("UserType", "PLATFORM"),
            isPlatformAdmin=user_entity.get("IsPlatformAdmin", False),
            isActive=user_entity.get("IsActive", True),
            lastLogin=user_entity.get("LastLogin"),
            createdAt=user_entity["CreatedAt"]
        )

        logger.info(f"Returning user details for {user_id}")

        return func.HttpResponse(
            json.dumps(user_model.model_dump(mode="json")),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error retrieving user: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to retrieve user"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("permissions_get_user_permissions")
@bp.route(route="permissions/users/{userId}", methods=["GET"])
@openapi_endpoint(
    path="/permissions/users/{userId}",
    method="GET",
    summary="Get user permissions (deprecated)",
    description="DEPRECATED: Org-specific permissions have been removed. Returns empty list for backward compatibility.",
    tags=["Permissions", "Deprecated"],
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
async def get_user_permissions(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/permissions/users/{userId}
    DEPRECATED: Org-specific permissions have been removed.
    Authorization is now platform admin only.

    Returns empty list for backward compatibility.
    """
    context = get_context(req)
    user_id = get_route_param(req, "userId")

    logger.info(f"User {context.user_id} retrieving permissions for user {user_id} (DEPRECATED endpoint)")

    # Return empty list - org permissions no longer exist
    return func.HttpResponse(
        json.dumps([]),
        status_code=200,
        mimetype="application/json"
    )


@bp.function_name("permissions_get_org_permissions")
@bp.route(route="permissions/organizations/{orgId}", methods=["GET"])
@openapi_endpoint(
    path="/permissions/organizations/{orgId}",
    method="GET",
    summary="Get organization permissions (deprecated)",
    description="DEPRECATED: Org-specific permissions have been removed. Returns empty list for backward compatibility.",
    tags=["Permissions", "Deprecated"],
    path_params={
        "orgId": {
            "description": "Organization ID",
            "schema": {"type": "string"},
            "required": True
        }
    }
)
@with_request_context
@require_platform_admin
async def get_org_permissions(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/permissions/organizations/{orgId}
    DEPRECATED: Org-specific permissions have been removed.
    Authorization is now platform admin only.

    Returns empty list for backward compatibility.
    """
    context = get_context(req)
    org_id = get_route_param(req, "orgId")

    logger.info(f"User {context.user_id} retrieving permissions for org {org_id} (DEPRECATED endpoint)")

    # Return empty list - org permissions no longer exist
    return func.HttpResponse(
        json.dumps([]),
        status_code=200,
        mimetype="application/json"
    )


@bp.function_name("permissions_grant_permissions")
@bp.route(route="permissions", methods=["POST"])
@openapi_endpoint(
    path="/permissions",
    method="POST",
    summary="Grant user permissions (deprecated)",
    description="DEPRECATED: Org-specific permissions have been removed. Use role-based access control instead.",
    tags=["Permissions", "Deprecated"],
    request_model=GrantPermissionsRequest,
    response_model=ErrorResponse
)
@with_request_context
@require_platform_admin
async def grant_permissions(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/permissions
    DEPRECATED: Org-specific permissions have been removed.
    Authorization is now platform admin only.

    Use role assignments instead (see /api/roles endpoints).
    """
    context = get_context(req)
    logger.info(f"User {context.user_id} attempting to grant permissions (DEPRECATED endpoint)")

    error = ErrorResponse(
        error="NotImplemented",
        message="Org-specific permissions are deprecated. Use role-based access control instead (see /api/roles endpoints)."
    )
    return func.HttpResponse(
        json.dumps(error.model_dump()),
        status_code=501,
        mimetype="application/json"
    )


@bp.function_name("permissions_revoke_permissions")
@bp.route(route="permissions", methods=["DELETE"])
@openapi_endpoint(
    path="/permissions",
    method="DELETE",
    summary="Revoke user permissions (deprecated)",
    description="DEPRECATED: Org-specific permissions have been removed. Use role-based access control instead.",
    tags=["Permissions", "Deprecated"],
    query_params={
        "userId": {
            "description": "User ID",
            "schema": {"type": "string"},
            "required": True
        },
        "orgId": {
            "description": "Organization ID",
            "schema": {"type": "string"},
            "required": True
        }
    },
    response_model=ErrorResponse
)
@with_request_context
@require_platform_admin
async def revoke_permissions(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/permissions?userId={userId}&orgId={orgId}
    DEPRECATED: Org-specific permissions have been removed.
    Authorization is now platform admin only.

    Use role assignments instead (see /api/roles endpoints).
    """
    context = get_context(req)
    logger.info(f"User {context.user_id} attempting to revoke permissions (DEPRECATED endpoint)")

    error = ErrorResponse(
        error="NotImplemented",
        message="Org-specific permissions are deprecated. Use role-based access control instead (see /api/roles endpoints)."
    )
    return func.HttpResponse(
        json.dumps(error.model_dump()),
        status_code=501,
        mimetype="application/json"
    )


# ==================== USER ROLES ENDPOINTS ====================


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

    logger.info(f"User {context.user_id} getting roles for user {user_id}")

    try:
        # Query Relationships table for user-role assignments
        # Row key pattern: userrole:{user_id}:{role_uuid}
        relationships_service = get_table_service("Relationships", context)
        user_role_entities = list(relationships_service.query_entities(
            filter=f"RowKey ge 'userrole:{user_id}:' and RowKey lt 'userrole:{user_id};'"
        ))

        # Extract role UUIDs from row keys
        role_ids = []
        for entity in user_role_entities:
            # RowKey format: userrole:{user_id}:{role_uuid}
            parts = entity["RowKey"].split(":", 2)
            if len(parts) == 3:
                role_ids.append(parts[2])

        logger.info(f"User {user_id} has {len(role_ids)} roles assigned")

        return func.HttpResponse(
            json.dumps({"roleIds": role_ids}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error getting user roles: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to get user roles"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


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

    logger.info(f"User {context.user_id} getting forms for user {user_id}")

    try:
        # Get user entity to check type
        users_service = get_table_service("Users", context)
        try:
            user_entity = users_service.get_entity("USER", user_id)
        except Exception:
            user_entity = None

        if not user_entity:
            error = ErrorResponse(
                error="NotFound",
                message=f"User {user_id} not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        user_type = user_entity.get("UserType", "PLATFORM")
        is_platform_admin = user_entity.get("IsPlatformAdmin", False)

        # Platform admins have access to ALL forms
        if user_type == "PLATFORM" and is_platform_admin:
            logger.info(f"User {user_id} is platform admin - has access to all forms")
            return func.HttpResponse(
                json.dumps({
                    "userType": "PLATFORM",
                    "hasAccessToAllForms": True,
                    "formIds": []  # Empty array indicates "all forms"
                }),
                status_code=200,
                mimetype="application/json"
            )

        # Regular users: Get forms based on role assignments
        # 1. Get user's roles from Relationships table
        relationships_service = get_table_service("Relationships", context)
        user_role_entities = list(relationships_service.query_entities(
            filter=f"RowKey ge 'userrole:{user_id}:' and RowKey lt 'userrole:{user_id};'"
        ))

        # Extract role UUIDs
        role_ids = []
        for entity in user_role_entities:
            parts = entity["RowKey"].split(":", 2)
            if len(parts) == 3:
                role_ids.append(parts[2])

        if not role_ids:
            logger.info(f"User {user_id} has no roles assigned")
            return func.HttpResponse(
                json.dumps({
                    "userType": user_type,
                    "hasAccessToAllForms": False,
                    "formIds": []
                }),
                status_code=200,
                mimetype="application/json"
            )

        # 2. Get forms for each role from Relationships table
        # Row key pattern: roleform:{role_uuid}:{form_uuid}
        form_ids_set = set()

        for role_id in role_ids:
            form_role_entities = list(relationships_service.query_entities(
                filter=f"RowKey ge 'roleform:{role_id}:' and RowKey lt 'roleform:{role_id};'"
            ))
            for entity in form_role_entities:
                # Extract form UUID from row key
                parts = entity["RowKey"].split(":", 2)
                if len(parts) == 3:
                    form_ids_set.add(parts[2])

        form_ids = list(form_ids_set)

        logger.info(f"User {user_id} has access to {len(form_ids)} forms via {len(role_ids)} roles")

        return func.HttpResponse(
            json.dumps({
                "userType": user_type,
                "hasAccessToAllForms": False,
                "formIds": form_ids
            }),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error getting user forms: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to get user forms"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )
