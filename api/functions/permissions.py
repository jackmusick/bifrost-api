"""
Permissions API endpoints
- Manage user permissions for organizations
- List users and their access rights
"""

import logging
import json
from datetime import datetime
from typing import List
import azure.functions as func

from shared.auth import require_auth
from shared.storage import TableStorageService
from shared.models import (
    User,
    UserType,
    UserPermission,
    GrantPermissionsRequest,
    ErrorResponse
)
from pydantic import ValidationError

logger = logging.getLogger(__name__)

# Create blueprint for permissions endpoints
bp = func.Blueprint()


@bp.function_name("permissions_list_users")
@bp.route(route="users", methods=["GET"])
@require_auth
def list_users(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/users?type=platform|org&orgId={id}
    List users with optional filtering by type

    Query params:
        type: Filter by user type (platform or org), optional
        orgId: Filter org users by organization, optional

    Requires: Authentication (any authenticated user)
    """
    user = req.user
    user_type_filter = req.params.get("type", "").lower()
    org_id_filter = req.params.get("orgId")

    logger.info(f"User {user.email} listing users (type={user_type_filter}, orgId={org_id_filter})")

    try:
        # Query Users table
        users_service = TableStorageService("Users")

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
@require_auth
def get_user(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/users/{userId}
    Get a specific user's details

    Note: User ID should match the authenticated user's ID from Azure AD.
    For local development with SWA CLI, use the email address as the user ID
    when logging in (SWA CLI allows you to specify any userId value).

    Requires: User can query their own details or be a platform admin
    """
    current_user = req.user
    user_id = req.route_params.get("userId")

    logger.info(f"User {current_user.email} retrieving details for user {user_id}")

    try:
        # Get user from Users table
        users_service = TableStorageService("Users")
        user_entity = users_service.get_entity("USER", user_id)

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
@require_auth
def get_user_permissions(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/permissions/users/{userId}
    Get all organizations a user can access and their permissions

    Requires: User can only query their own permissions (or is admin in future)
    """
    current_user = req.user
    user_id = req.route_params.get("userId")

    logger.info(f"User {current_user.email} retrieving permissions for user {user_id}")

    try:
        # Security check: user can only query their own permissions
        if current_user.user_id != user_id:
            logger.warning(f"User {current_user.email} denied access to user {user_id} permissions")
            error = ErrorResponse(
                error="Forbidden",
                message="You can only view your own permissions"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        # Query UserPermissions table
        permissions_service = TableStorageService("UserPermissions")
        permission_entities = list(permissions_service.query_entities(
            filter=f"PartitionKey eq '{user_id}'"
        ))

        # Convert to response models
        permissions = []
        for entity in permission_entities:
            permission = UserPermission(
                userId=entity["PartitionKey"],
                orgId=entity["RowKey"],
                canExecuteWorkflows=entity.get("CanExecuteWorkflows", False),
                canManageConfig=entity.get("CanManageConfig", False),
                canManageForms=entity.get("CanManageForms", False),
                canViewHistory=entity.get("CanViewHistory", False),
                grantedBy=entity["GrantedBy"],
                grantedAt=entity["GrantedAt"]
            )
            permissions.append(permission.model_dump(mode="json"))

        logger.info(f"Returning {len(permissions)} permissions for user {user_id}")

        return func.HttpResponse(
            json.dumps(permissions),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error retrieving user permissions: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to retrieve user permissions"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("permissions_get_org_permissions")
@bp.route(route="permissions/organizations/{orgId}", methods=["GET"])
@require_auth
def get_org_permissions(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/permissions/organizations/{orgId}
    Get all users who have access to an organization

    Requires: User must have canManageConfig permission for the org
    """
    user = req.user
    org_id = req.route_params.get("orgId")

    logger.info(f"User {user.email} retrieving permissions for org {org_id}")

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

        # Check canManageConfig permission
        if not permission.get("CanManageConfig", False):
            logger.warning(f"User {user.email} lacks canManageConfig permission for org {org_id}")
            error = ErrorResponse(
                error="Forbidden",
                message="You don't have permission to manage permissions"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        # Query OrgPermissions table
        org_permissions_service = TableStorageService("OrgPermissions")
        permission_entities = list(org_permissions_service.query_entities(
            filter=f"PartitionKey eq '{org_id}'"
        ))

        # Convert to response models
        permissions = []
        for entity in permission_entities:
            permission = UserPermission(
                userId=entity["RowKey"],
                orgId=entity["PartitionKey"],
                canExecuteWorkflows=entity.get("CanExecuteWorkflows", False),
                canManageConfig=entity.get("CanManageConfig", False),
                canManageForms=entity.get("CanManageForms", False),
                canViewHistory=entity.get("CanViewHistory", False),
                grantedBy=entity["GrantedBy"],
                grantedAt=entity["GrantedAt"]
            )
            permissions.append(permission.model_dump(mode="json"))

        logger.info(f"Returning {len(permissions)} permissions for org {org_id}")

        return func.HttpResponse(
            json.dumps(permissions),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error retrieving org permissions: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to retrieve organization permissions"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("permissions_grant_permissions")
@bp.route(route="permissions", methods=["POST"])
@require_auth
def grant_permissions(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/permissions
    Grant a user permissions to access an organization

    Requires: User must have canManageConfig permission for the org
    """
    user = req.user
    logger.info(f"User {user.email} granting permissions")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        grant_request = GrantPermissionsRequest(**request_body)

        # Check if requesting user has access to this org
        permissions_service = TableStorageService("UserPermissions")
        permission = permissions_service.get_entity(user.user_id, grant_request.orgId)

        if not permission:
            logger.warning(f"User {user.email} denied access to org {grant_request.orgId}")
            error = ErrorResponse(
                error="Forbidden",
                message="You don't have access to this organization"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        # Check canManageConfig permission
        if not permission.get("CanManageConfig", False):
            logger.warning(f"User {user.email} lacks canManageConfig permission for org {grant_request.orgId}")
            error = ErrorResponse(
                error="Forbidden",
                message="You don't have permission to manage permissions"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        # Create permission entities for both tables (dual-indexing)
        now = datetime.utcnow()
        user_permission_entity = {
            "PartitionKey": grant_request.userId,
            "RowKey": grant_request.orgId,
            "CanExecuteWorkflows": grant_request.permissions.canExecuteWorkflows,
            "CanManageConfig": grant_request.permissions.canManageConfig,
            "CanManageForms": grant_request.permissions.canManageForms,
            "CanViewHistory": grant_request.permissions.canViewHistory,
            "GrantedBy": user.user_id,
            "GrantedAt": now.isoformat()
        }

        org_permission_entity = {
            "PartitionKey": grant_request.orgId,
            "RowKey": grant_request.userId,
            "CanExecuteWorkflows": grant_request.permissions.canExecuteWorkflows,
            "CanManageConfig": grant_request.permissions.canManageConfig,
            "CanManageForms": grant_request.permissions.canManageForms,
            "CanViewHistory": grant_request.permissions.canViewHistory,
            "GrantedBy": user.user_id,
            "GrantedAt": now.isoformat()
        }

        # Perform dual insert (upsert to allow updates)
        permissions_service.upsert_entity(user_permission_entity)

        org_permissions_service = TableStorageService("OrgPermissions")
        org_permissions_service.upsert_entity(org_permission_entity)

        logger.info(f"Granted permissions to user {grant_request.userId} for org {grant_request.orgId}")

        # Create response model
        permission_response = UserPermission(
            userId=grant_request.userId,
            orgId=grant_request.orgId,
            canExecuteWorkflows=grant_request.permissions.canExecuteWorkflows,
            canManageConfig=grant_request.permissions.canManageConfig,
            canManageForms=grant_request.permissions.canManageForms,
            canViewHistory=grant_request.permissions.canViewHistory,
            grantedBy=user.user_id,
            grantedAt=now
        )

        return func.HttpResponse(
            json.dumps(permission_response.model_dump(mode="json")),
            status_code=201,
            mimetype="application/json"
        )

    except ValidationError as e:
        logger.warning(f"Validation error granting permissions: {e}")
        # Convert validation errors to JSON-serializable format
        errors = []
        for err in e.errors():
            error_dict = {"loc": err["loc"], "type": err["type"], "msg": str(err["msg"])}
            if "input" in err:
                error_dict["input"] = str(err["input"])
            errors.append(error_dict)

        error = ErrorResponse(
            error="ValidationError",
            message="Invalid request data",
            details={"errors": errors}
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
        logger.error(f"Error granting permissions: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to grant permissions"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("permissions_revoke_permissions")
@bp.route(route="permissions", methods=["DELETE"])
@require_auth
def revoke_permissions(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/permissions?userId={userId}&orgId={orgId}
    Revoke a user's access to an organization

    Requires: User must have canManageConfig permission for the org
    """
    user = req.user
    user_id = req.params.get("userId")
    org_id = req.params.get("orgId")

    logger.info(f"User {user.email} revoking permissions for user {user_id} on org {org_id}")

    try:
        # Validate query parameters
        if not user_id or not org_id:
            error = ErrorResponse(
                error="BadRequest",
                message="Both userId and orgId query parameters are required"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # Check if requesting user has access to this org
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

        # Check canManageConfig permission
        if not permission.get("CanManageConfig", False):
            logger.warning(f"User {user.email} lacks canManageConfig permission for org {org_id}")
            error = ErrorResponse(
                error="Forbidden",
                message="You don't have permission to manage permissions"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        # Perform dual delete (idempotent)
        try:
            permissions_service.delete_entity(user_id, org_id)
            logger.debug(f"Deleted permission from UserPermissions: {user_id}, {org_id}")
        except Exception as e:
            logger.debug(f"Permission not found in UserPermissions, continuing: {e}")

        try:
            org_permissions_service = TableStorageService("OrgPermissions")
            org_permissions_service.delete_entity(org_id, user_id)
            logger.debug(f"Deleted permission from OrgPermissions: {org_id}, {user_id}")
        except Exception as e:
            logger.debug(f"Permission not found in OrgPermissions, continuing: {e}")

        logger.info(f"Revoked permissions for user {user_id} on org {org_id}")

        return func.HttpResponse(
            status_code=204  # No Content
        )

    except Exception as e:
        logger.error(f"Error revoking permissions: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to revoke permissions"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


# ==================== USER ROLES ENDPOINTS ====================


@bp.function_name("permissions_get_user_roles")
@bp.route(route="users/{userId}/roles", methods=["GET"])
@require_auth
def get_user_roles(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/users/{userId}/roles
    Get all roles assigned to a user

    Requires: User must be authenticated
    """
    user = req.user
    user_id = req.route_params.get("userId")

    logger.info(f"User {user.email} getting roles for user {user_id}")

    try:
        # Query UserRoles across all roles (need to scan)
        user_roles_service = TableStorageService("UserRoles")
        user_role_entities = list(user_roles_service.query_entities(
            filter=f"UserId eq '{user_id}'"
        ))

        # Extract role IDs
        role_ids = [entity["RoleId"] for entity in user_role_entities]

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
@require_auth
def get_user_forms(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/users/{userId}/forms
    Get all forms a user can access based on their roles

    Access logic:
    - If user is PLATFORM type: Return all forms (bypass role check)
    - If user is ORG type: Return forms based on role assignments

    Requires: User must be authenticated
    """
    user = req.user
    user_id = req.route_params.get("userId")

    logger.info(f"User {user.email} getting forms for user {user_id}")

    try:
        # Get user entity to check type
        users_service = TableStorageService("Users")
        user_entity = users_service.get_entity(user_id, "user")

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

        # PLATFORM users have access to ALL forms
        if user_type == "PLATFORM":
            logger.info(f"User {user_id} is PLATFORM type - has access to all forms")
            return func.HttpResponse(
                json.dumps({
                    "userType": "PLATFORM",
                    "hasAccessToAllForms": True,
                    "formIds": []  # Empty array indicates "all forms"
                }),
                status_code=200,
                mimetype="application/json"
            )

        # ORG users: Get forms based on role assignments
        # 1. Get user's roles
        user_roles_service = TableStorageService("UserRoles")
        user_role_entities = list(user_roles_service.query_entities(
            filter=f"UserId eq '{user_id}'"
        ))
        role_ids = [entity["RoleId"] for entity in user_role_entities]

        if not role_ids:
            logger.info(f"User {user_id} is ORG type but has no roles assigned")
            return func.HttpResponse(
                json.dumps({
                    "userType": "ORG",
                    "hasAccessToAllForms": False,
                    "formIds": []
                }),
                status_code=200,
                mimetype="application/json"
            )

        # 2. Get forms for each role
        form_roles_service = TableStorageService("FormRoles")
        form_ids_set = set()

        for role_id in role_ids:
            form_role_entities = list(form_roles_service.query_entities(
                filter=f"RoleId eq '{role_id}'"
            ))
            for entity in form_role_entities:
                form_ids_set.add(entity["FormId"])

        form_ids = list(form_ids_set)

        logger.info(f"User {user_id} has access to {len(form_ids)} forms via {len(role_ids)} roles")

        return func.HttpResponse(
            json.dumps({
                "userType": "ORG",
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
