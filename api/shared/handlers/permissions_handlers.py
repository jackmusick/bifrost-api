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
    ErrorResponse,
    User,
)
from shared.request_context import RequestContext
from shared.storage import get_table_service

logger = logging.getLogger(__name__)


async def list_users_handler(
    context: RequestContext,
    user_type_filter: str = "",
    org_id_filter: Optional[str] = None
) -> func.HttpResponse:
    """
    List users with optional filtering by type and organization.

    Args:
        context: Request context with auth info
        user_type_filter: Filter by user type ('platform' or 'org')
        org_id_filter: Filter org users by organization ID

    Returns:
        HttpResponse with list of users
    """
    logger.info(
        f"User {context.user_id} listing users (type={user_type_filter}, "
        f"orgId={org_id_filter})"
    )

    try:
        # Query Entities table for users
        entities_service = get_table_service("Entities", context)

        # Build filter based on type
        user_type_filter_lower = user_type_filter.lower()
        if user_type_filter_lower == "platform":
            filter_query = (
                "PartitionKey eq 'GLOBAL' and RowKey ge 'user:' and RowKey lt 'user;' "
                "and UserType eq 'PLATFORM'"
            )
        elif user_type_filter_lower == "org":
            filter_query = (
                "PartitionKey eq 'GLOBAL' and RowKey ge 'user:' and RowKey lt 'user;' "
                "and UserType eq 'ORG'"
            )
        else:
            filter_query = "PartitionKey eq 'GLOBAL' and RowKey ge 'user:' and RowKey lt 'user;'"

        user_entities = list(entities_service.query_entities(filter=filter_query))

        # Convert to response models
        users = []
        for entity in user_entities:
            # Skip if orgId filter specified and doesn't match
            # Note: ORG users don't have a single orgId - they're assigned via permissions
            # For now, we'll skip this complex filtering
            # TODO: Filter by UserPermissions table for org-specific users

            user_model = User(
                id=entity["RowKey"].split(":", 1)[1],  # Extract email from "user:email"
                email=entity["Email"],
                displayName=entity["DisplayName"],
                userType=entity.get("UserType", "PLATFORM"),
                isPlatformAdmin=entity.get("IsPlatformAdmin", False),
                isActive=entity.get("IsActive", True),
                lastLogin=entity.get("LastLogin"),  # Use LastLogin instead of LastLoginAt
                createdAt=entity["CreatedAt"],
                entraUserId=entity.get("EntraUserId"),
                lastEntraIdSync=entity.get("LastEntraIdSync")
            )
            users.append(user_model)

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
    context: RequestContext,
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
        entities_service = get_table_service("Entities", context)
        try:
            user_entity = entities_service.get_entity("GLOBAL", f"user:{user_id}")
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
    context: RequestContext,
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
    context: RequestContext,
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
    context: RequestContext
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
    context: RequestContext,
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
    context: RequestContext,
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


async def get_user_forms_handler(
    context: RequestContext,
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
        entities_service = get_table_service("Entities", context)
        try:
            user_entity = entities_service.get_entity("GLOBAL", f"user:{user_id}")
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
