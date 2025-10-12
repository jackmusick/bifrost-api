"""
Authentication Header Derivation
Derives X-Organization-Id and X-User-Id from Easy Auth or validates admin overrides
"""

import logging
import json
import azure.functions as func
from typing import Tuple, Optional
from shared.auth import get_authenticated_user, is_platform_admin
from shared.models import ErrorResponse
from shared.storage import TableStorageService

logger = logging.getLogger(__name__)


def get_auth_headers(req: func.HttpRequest, require_org: bool = True) -> Tuple[Optional[str], Optional[str], Optional[func.HttpResponse]]:
    """
    Get or derive X-Organization-Id and X-User-Id headers with security validation.

    Logic:
    1. If neither header provided → derive from database (user's default org)
    2. If either header provided:
       - Check if user is PlatformAdmin
       - If admin: use provided values, derive missing ones
       - If not admin: return 403 (unauthorized override attempt)
    3. Platform admins can have None org_id if require_org=False

    Args:
        req: Azure Functions HTTP request
        require_org: If False, platform admins can operate without org context (default: True)

    Returns:
        Tuple of (org_id, user_id, error_response)
        - If successful: (org_id, user_id, None) - org_id may be None if require_org=False
        - If error: (None, None, HttpResponse with error)

    Usage:
        # Require org (most endpoints)
        org_id, user_id, error = get_auth_headers(req)
        if error:
            return error

        # Optional org (list endpoints for platform admins)
        org_id, user_id, error = get_auth_headers(req, require_org=False)
        if error:
            return error
        # org_id may be None for platform admins
    """
    try:
        # Get authenticated user from Easy Auth
        user = get_authenticated_user(req)
        if not user:
            error = ErrorResponse(
                error="Unauthorized",
                message="Authentication required"
            )
            return None, None, func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=401,
                mimetype="application/json"
            )

        # Check if user is platform admin
        user_is_admin = is_platform_admin(user.user_id)

        # Check if headers are provided in request
        provided_org_id = req.headers.get("X-Organization-Id")
        provided_user_id = req.headers.get("X-User-Id")

        # Case 1: Neither header provided → derive from database or allow None for admins
        if not provided_org_id and not provided_user_id:
            # Platform admins can operate without org context if allowed
            if user_is_admin and not require_org:
                logger.info(f"PlatformAdmin {user.email} operating without org context")
                return None, user.user_id, None

            # Non-admins or admins with require_org=True: must derive from database
            logger.info(f"Deriving org and user context for {user.email} from database")
            org_id, user_id = _derive_from_database(user.user_id)

            if not org_id or not user_id:
                # If platform admin and org is optional, allow operation without org
                if user_is_admin and not require_org:
                    logger.info(f"PlatformAdmin {user.email} has no default org, operating without org context")
                    return None, user.user_id, None

                error = ErrorResponse(
                    error="NotFound",
                    message="User organization context not found. Please contact administrator."
                )
                return None, None, func.HttpResponse(
                    json.dumps(error.model_dump()),
                    status_code=404,
                    mimetype="application/json"
                )
            return org_id, user_id, None

        # Case 2: Either header provided → check if admin
        if not user_is_admin:
            # Non-admin trying to override context → 403
            logger.warning(f"Non-admin user {user.email} attempted to override auth headers")
            error = ErrorResponse(
                error="Forbidden",
                message="Only platform administrators can override organization/user context"
            )
            return None, None, func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        # Case 3: Admin with provided headers → use provided, derive missing
        logger.info(f"PlatformAdmin {user.email} overriding context: org={provided_org_id}, user={provided_user_id}")

        org_id = provided_org_id
        user_id = provided_user_id or user.user_id

        # Derive org_id if not provided (but only if required)
        if not org_id and require_org:
            derived_org_id, _ = _derive_from_database(user_id)
            org_id = derived_org_id

        # If org still missing and required, return error
        if not org_id and require_org:
            error = ErrorResponse(
                error="NotFound",
                message="Could not derive organization context"
            )
            return None, None, func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        return org_id, user_id, None

    except Exception as e:
        logger.error(f"Error deriving auth headers: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to derive authentication context"
        )
        return None, None, func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


def _derive_from_database(user_id: str) -> Tuple[Optional[str], str]:
    """
    Look up user in database and get their organization ID

    Returns:
        Tuple of (org_id, user_id)
    """
    try:
        users_table = TableStorageService("Users")

        # Query for user by user_id (which is the RowKey)
        # We need to find the entity where RowKey = user_id
        # PartitionKey in Users table is the org_id

        # Query all partitions for this user_id
        query_filter = f"RowKey eq '{user_id}'"
        entities = list(users_table.query_entities(query_filter))

        if not entities:
            logger.warning(f"User {user_id} not found in database")
            return None, user_id

        if len(entities) > 1:
            logger.warning(f"Multiple users found for {user_id}, using first")

        user_entity = entities[0]
        org_id = user_entity.get("PartitionKey")  # PartitionKey is org_id in Users table

        logger.info(f"Derived org context for user {user_id}: org={org_id}")
        return org_id, user_id

    except Exception as e:
        logger.error(f"Error looking up user in database: {str(e)}", exc_info=True)
        return None, user_id
