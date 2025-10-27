"""
Permissions API handlers
Business logic for user permissions and roles
"""

import json
import logging
from datetime import datetime
from typing import Optional

import azure.functions as func

from shared.models import (
    CreateUserRequest,
    ErrorResponse,
    UpdateUserRequest,
    User,
    UserType,
)
from shared.context import ExecutionContext
from shared.async_storage import get_async_table_service
from shared.repositories.users import UserRepository
from shared.repositories.organizations import OrganizationRepository

logger = logging.getLogger(__name__)


async def list_users_handler(
    context: ExecutionContext,
    user_type_filter: str = "",
    org_id_filter: Optional[str] = None
) -> func.HttpResponse:
    """
    List users with optional filtering based on scope.

    Scope-based filtering (from X-Organization-Id header in context.scope):
    - GLOBAL scope: Returns all users (platform admins and org users)
    - Organization scope: Returns only org users for that organization

    Args:
        context: Request context with auth info and scope
        user_type_filter: Deprecated - use context.scope instead
        org_id_filter: Deprecated - use context.scope instead

    Returns:
        HttpResponse with list of users
    """
    logger.info(
        f"User {context.user_id} listing users (scope={context.scope})"
    )

    try:
        # Query Entities table for users
        entities_service = get_async_table_service("Entities", context)

        # Build filter based on scope (from X-Organization-Id header)
        if not hasattr(context, 'scope') or context.scope == "GLOBAL":
            # Global scope (or no scope): return all users
            filter_query = "PartitionKey eq 'GLOBAL' and RowKey ge 'user:' and RowKey lt 'user;'"
        else:
            # Organization scope: return only org users for this organization
            filter_query = (
                "PartitionKey eq 'GLOBAL' and RowKey ge 'user:' and RowKey lt 'user;' "
                "and UserType eq 'ORG'"
            )

        user_entities = await entities_service.query_entities(filter=filter_query)

        # For organization scope, get list of users assigned to this org
        org_user_emails = set()
        if hasattr(context, 'scope') and context.scope != "GLOBAL":
            # Query org-to-user relationships to find users in this org
            relationships_service = get_async_table_service("Relationships", context)
            org_perm_filter = (
                f"PartitionKey eq 'GLOBAL' and "
                f"RowKey ge 'orgperm:{context.scope}:' and "
                f"RowKey lt 'orgperm:{context.scope}~'"
            )
            org_relationships = await relationships_service.query_entities(filter=org_perm_filter)
            for rel in org_relationships:
                # Extract user email from "orgperm:orgId:userEmail"
                parts = rel["RowKey"].split(":", 2)
                if len(parts) == 3:
                    user_email = parts[2]
                    org_user_emails.add(user_email)

        # Convert to response models
        users = []
        for entity in user_entities:
            try:
                user_email = entity["Email"]

                # For organization scope, only include users assigned to this org
                if hasattr(context, 'scope') and context.scope != "GLOBAL" and user_email not in org_user_emails:
                    continue

                user_model = User(
                    id=entity["RowKey"].split(":", 1)[1],  # Extract email from "user:email"
                    email=user_email,
                    displayName=entity["DisplayName"],
                    userType=entity.get("UserType", "PLATFORM"),
                    isPlatformAdmin=entity.get("IsPlatformAdmin", False),
                    isActive=entity.get("IsActive", True),
                    lastLogin=entity.get("LastLogin"),
                    createdAt=entity["CreatedAt"],
                    entraUserId=entity.get("EntraUserId"),
                    lastEntraIdSync=entity.get("LastEntraIdSync")
                )
                users.append(user_model)
            except Exception as e:
                logger.warning(f"Failed to convert user entity to model: {str(e)}", exc_info=True)
                continue

        # Sort by lastLogin descending (most recent first), handle None values
        users.sort(key=lambda u: u.lastLogin or datetime.min, reverse=True)

        logger.info(f"Returning {len(users)} users")

        return func.HttpResponse(
            json.dumps([u.model_dump(mode="json") for u in users]),
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


async def get_user_handler(
    context: ExecutionContext,
    user_id: str
) -> func.HttpResponse:
    """
    Get a specific user's details.

    Args:
        context: Request context with auth info
        user_id: User ID to retrieve

    Returns:
        HttpResponse with user details
    """
    logger.info(f"User {context.user_id} retrieving details for user {user_id}")

    try:
        # Get user from Entities table
        entities_service = get_async_table_service("Entities", context)
        try:
            user_entity = await entities_service.get_entity("GLOBAL", f"user:{user_id}")
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
            id=user_id,  # Using user_id directly instead of RowKey
            email=user_entity["Email"],
            displayName=user_entity["DisplayName"],
            userType=user_entity.get("UserType", "PLATFORM"),
            isPlatformAdmin=user_entity.get("IsPlatformAdmin", False),
            isActive=user_entity.get("IsActive", True),
            lastLogin=user_entity.get("LastLogin"),
            createdAt=user_entity["CreatedAt"],
            entraUserId=user_entity.get("EntraUserId"),
            lastEntraIdSync=user_entity.get("LastEntraIdSync")
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


async def get_user_permissions_handler(
    context: ExecutionContext,
    user_id: str
) -> func.HttpResponse:
    """
    Get user permissions (deprecated endpoint).

    DEPRECATED: Org-specific permissions have been removed.
    Authorization is now platform admin only.
    Returns empty list for backward compatibility.

    Args:
        context: Request context with auth info
        user_id: User ID

    Returns:
        HttpResponse with empty list
    """
    logger.info(
        f"User {context.user_id} retrieving permissions for user {user_id} "
        "(DEPRECATED endpoint)"
    )

    # Return empty list - org permissions no longer exist
    return func.HttpResponse(
        json.dumps([]),
        status_code=200,
        mimetype="application/json"
    )


async def get_org_permissions_handler(
    context: ExecutionContext,
    org_id: str
) -> func.HttpResponse:
    """
    Get organization permissions (deprecated endpoint).

    DEPRECATED: Org-specific permissions have been removed.
    Authorization is now platform admin only.
    Returns empty list for backward compatibility.

    Args:
        context: Request context with auth info
        org_id: Organization ID

    Returns:
        HttpResponse with empty list
    """
    logger.info(
        f"User {context.user_id} retrieving permissions for org {org_id} "
        "(DEPRECATED endpoint)"
    )

    # Return empty list - org permissions no longer exist
    return func.HttpResponse(
        json.dumps([]),
        status_code=200,
        mimetype="application/json"
    )


async def grant_permissions_handler(
    context: ExecutionContext
) -> func.HttpResponse:
    """
    Grant user permissions (deprecated endpoint).

    DEPRECATED: Org-specific permissions have been removed.
    Use role-based access control instead.

    Args:
        context: Request context with auth info

    Returns:
        HttpResponse with error message
    """
    logger.info(
        f"User {context.user_id} attempting to grant permissions "
        "(DEPRECATED endpoint)"
    )

    error = ErrorResponse(
        error="NotImplemented",
        message="Org-specific permissions are deprecated. Use role-based access control instead (see /api/roles endpoints)."
    )
    return func.HttpResponse(
        json.dumps(error.model_dump()),
        status_code=501,
        mimetype="application/json"
    )


async def revoke_permissions_handler(
    context: ExecutionContext,
    user_id: str,
    org_id: str
) -> func.HttpResponse:
    """
    Revoke user permissions (deprecated endpoint).

    DEPRECATED: Org-specific permissions have been removed.
    Use role-based access control instead.

    Args:
        context: Request context with auth info
        user_id: User ID
        org_id: Organization ID

    Returns:
        HttpResponse with error message
    """
    logger.info(
        f"User {context.user_id} attempting to revoke permissions "
        "(DEPRECATED endpoint)"
    )

    error = ErrorResponse(
        error="NotImplemented",
        message="Org-specific permissions are deprecated. Use role-based access control instead (see /api/roles endpoints)."
    )
    return func.HttpResponse(
        json.dumps(error.model_dump()),
        status_code=501,
        mimetype="application/json"
    )


async def get_user_roles_handler(
    context: ExecutionContext,
    user_id: str
) -> func.HttpResponse:
    """
    Get all roles assigned to a user.

    Args:
        context: Request context with auth info
        user_id: User ID to get roles for

    Returns:
        HttpResponse with UserRolesResponse containing list of role IDs
    """
    logger.info(f"User {context.user_id} getting roles for user {user_id}")

    try:
        # Query Relationships table for user-role assignments
        # Row key pattern: userrole:{user_id}:{role_uuid}
        relationships_service = get_async_table_service("Relationships", context)
        user_role_entities = await relationships_service.query_entities(
            filter=f"RowKey ge 'userrole:{user_id}:' and RowKey lt 'userrole:{user_id};'"
        )

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


async def get_user_forms_handler(
    context: ExecutionContext,
    user_id: str
) -> func.HttpResponse:
    """
    Get all forms a user can access based on their roles.

    Access logic:
    - Platform admins: Return all forms (hasAccessToAllForms=True)
    - Regular users: Return forms based on role assignments

    Args:
        context: Request context with auth info
        user_id: User ID to get forms for

    Returns:
        HttpResponse with UserFormsResponse
    """
    logger.info(f"User {context.user_id} getting forms for user {user_id}")

    try:
        # Get user entity to check type
        entities_service = get_async_table_service("Entities", context)
        try:
            user_entity = await entities_service.get_entity("GLOBAL", f"user:{user_id}")
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
        relationships_service = get_async_table_service("Relationships", context)
        user_role_entities = await relationships_service.query_entities(
            filter=f"RowKey ge 'userrole:{user_id}:' and RowKey lt 'userrole:{user_id};'"
        )

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
            form_role_entities = await relationships_service.query_entities(
                filter=f"RowKey ge 'roleform:{role_id}:' and RowKey lt 'roleform:{role_id};'"
            )
            for entity in form_role_entities:
                # Extract form UUID from row key
                parts = entity["RowKey"].split(":", 2)
                if len(parts) == 3:
                    form_ids_set.add(parts[2])

        form_ids = list(form_ids_set)

        logger.info(
            f"User {user_id} has access to {len(form_ids)} forms "
            f"via {len(role_ids)} roles"
        )

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


async def create_user_handler(
    context: ExecutionContext,
    req: func.HttpRequest
) -> func.HttpResponse:
    """
    Create a new user proactively (before first login).

    Business Rules:
    - isPlatformAdmin=true → User is PLATFORM type (global access)
    - isPlatformAdmin=false → User is ORG type, orgId is REQUIRED

    Args:
        context: Request context with auth info
        req: HTTP request with CreateUserRequest body

    Returns:
        HttpResponse with created User model
    """
    logger.info(f"Platform admin {context.user_id} creating new user")

    try:
        # Parse and validate request body
        try:
            body = req.get_json()
            create_request = CreateUserRequest(**body)
        except ValueError as e:
            logger.warning(f"Invalid create user request: {e}")
            error = ErrorResponse(
                error="ValidationError",
                message=str(e)
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # Check if user already exists
        user_repo = UserRepository(context)
        existing_user = await user_repo.get_user(create_request.email)

        if existing_user:
            logger.warning(f"User already exists: {create_request.email}")
            error = ErrorResponse(
                error="Conflict",
                message=f"User with email {create_request.email} already exists"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=409,
                mimetype="application/json"
            )

        # Validate organization exists if orgId provided
        if create_request.orgId:
            org_repo = OrganizationRepository(context)
            org = await org_repo.get_by_id("GLOBAL", f"org:{create_request.orgId}")
            if not org:
                logger.warning(f"Organization not found: {create_request.orgId}")
                error = ErrorResponse(
                    error="NotFound",
                    message=f"Organization {create_request.orgId} not found"
                )
                return func.HttpResponse(
                    json.dumps(error.model_dump()),
                    status_code=404,
                    mimetype="application/json"
                )

        # Determine user type based on isPlatformAdmin
        user_type = UserType.PLATFORM if create_request.isPlatformAdmin else UserType.ORG

        # Create user
        new_user = await user_repo.create_user(
            email=create_request.email,
            display_name=create_request.displayName,
            user_type=user_type,
            is_platform_admin=create_request.isPlatformAdmin
        )

        # Assign to organization if ORG user
        if user_type == UserType.ORG and create_request.orgId:
            await user_repo.assign_user_to_org(
                email=create_request.email,
                org_id=create_request.orgId,
                assigned_by=context.user_id
            )

        logger.info(
            f"Created user {create_request.email} "
            f"(type={user_type}, admin={create_request.isPlatformAdmin})"
        )

        return func.HttpResponse(
            json.dumps(new_user.model_dump(mode="json")),
            status_code=201,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error creating user: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to create user"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


async def update_user_handler(
    context: ExecutionContext,
    user_id: str,
    req: func.HttpRequest
) -> func.HttpResponse:
    """
    Update user properties including role transitions.

    Business Rules:
    - Promoting to Platform Admin: Removes org assignments
    - Demoting to Org User: Requires orgId, creates org assignment

    Args:
        context: Request context with auth info
        user_id: User ID (email) to update
        req: HTTP request with UpdateUserRequest body

    Returns:
        HttpResponse with updated User model
    """
    logger.info(f"Platform admin {context.user_id} updating user {user_id}")

    try:
        # Parse and validate request body
        try:
            body = req.get_json()
            update_request = UpdateUserRequest(**body)
        except ValueError as e:
            logger.warning(f"Invalid update user request: {e}")
            error = ErrorResponse(
                error="ValidationError",
                message=str(e)
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # Check if user exists
        user_repo = UserRepository(context)
        existing_user = await user_repo.get_user(user_id)

        if not existing_user:
            logger.warning(f"User not found: {user_id}")
            error = ErrorResponse(
                error="NotFound",
                message=f"User {user_id} not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Prevent users from changing their own role or active status
        # They can only change their display name
        if context.user_id == user_id:
            if update_request.isPlatformAdmin is not None or update_request.isActive is not None:
                logger.warning(f"User {context.user_id} attempted to change their own role/status")
                error = ErrorResponse(
                    error="Forbidden",
                    message="You cannot change your own role or active status"
                )
                return func.HttpResponse(
                    json.dumps(error.model_dump()),
                    status_code=403,
                    mimetype="application/json"
                )

        # Validate organization exists if orgId provided
        if update_request.orgId:
            org_repo = OrganizationRepository(context)
            org = await org_repo.get_by_id("GLOBAL", f"org:{update_request.orgId}")
            if not org:
                logger.warning(f"Organization not found: {update_request.orgId}")
                error = ErrorResponse(
                    error="NotFound",
                    message=f"Organization {update_request.orgId} not found"
                )
                return func.HttpResponse(
                    json.dumps(error.model_dump()),
                    status_code=404,
                    mimetype="application/json"
                )

        # Update user
        updated_user = await user_repo.update_user(
            email=user_id,
            display_name=update_request.displayName,
            is_active=update_request.isActive,
            is_platform_admin=update_request.isPlatformAdmin,
            org_id=update_request.orgId,
            updated_by=context.user_id
        )

        if not updated_user:
            logger.error(f"Failed to update user: {user_id}")
            error = ErrorResponse(
                error="InternalServerError",
                message="Failed to update user"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=500,
                mimetype="application/json"
            )

        logger.info(f"Updated user {user_id}")

        return func.HttpResponse(
            json.dumps(updated_user.model_dump(mode="json")),
            status_code=200,
            mimetype="application/json"
        )

    except ValueError as e:
        # Handle validation errors from repository (e.g., missing orgId)
        logger.warning(f"Validation error updating user: {e}")
        error = ErrorResponse(
            error="ValidationError",
            message=str(e)
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to update user"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


async def delete_user_handler(
    context: ExecutionContext,
    user_id: str
) -> func.HttpResponse:
    """
    Delete a user from the system.

    Business Rules:
    - Users cannot delete themselves
    - Only Platform Admins can delete users

    Args:
        context: Request context with auth info
        user_id: User ID (email) to delete

    Returns:
        HttpResponse with 204 No Content on success
    """
    logger.info(f"Platform admin {context.user_id} attempting to delete user {user_id}")

    # Prevent users from deleting themselves
    if context.user_id == user_id:
        logger.warning(f"User {context.user_id} attempted to delete themselves")
        error = ErrorResponse(
            error="Forbidden",
            message="You cannot delete your own user account"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=403,
            mimetype="application/json"
        )

    try:
        user_repo = UserRepository(context)

        # Check if user exists
        existing_user = await user_repo.get_user(user_id)
        if not existing_user:
            logger.warning(f"User not found: {user_id}")
            error = ErrorResponse(
                error="NotFound",
                message=f"User {user_id} not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Delete the user entity
        await user_repo.delete("GLOBAL", f"user:{user_id}")

        # Clean up org assignments if exists
        org_id = await user_repo.get_user_org_id(user_id)
        if org_id:
            await user_repo.remove_user_from_org(user_id, org_id)

        logger.info(f"Deleted user {user_id}")

        return func.HttpResponse(
            status_code=204
        )

    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to delete user"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )
