"""
Request Context - Unified context extraction for all endpoints

Provides a single, consistent way to extract:
- User identity (from EasyAuth)
- Organization scope (from header or database)
- Platform admin status
- Execution context for workflows

This replaces the scattered authentication/authorization logic across
auth.py, auth_headers.py, and middleware.py.
"""

import base64
import json
import logging
from dataclasses import dataclass

import azure.functions as func

logger = logging.getLogger(__name__)


@dataclass
class RequestContext:
    """
    Unified request context for all endpoints.

    Contains everything needed to execute workflows and queries:
    - user_id: User identifier (from EasyAuth or "system" for function keys)
    - email: User email (from EasyAuth or "system@local" for function keys)
    - name: User display name
    - org_id: Organization ID (None = GLOBAL scope)
    - is_platform_admin: Whether user is platform admin
    - is_function_key: Whether authenticated via function key (not a user)

    Usage:
        context = get_request_context(req)
        if context.is_platform_admin:
            # Allow admin operations

        # Use org_id for queries
        partition_key = context.org_id or "GLOBAL"
    """
    user_id: str
    email: str
    name: str
    org_id: str | None
    is_platform_admin: bool
    is_function_key: bool

    @property
    def scope(self) -> str:
        """Get partition key for database queries"""
        return self.org_id or "GLOBAL"


def get_request_context(req: func.HttpRequest) -> RequestContext:
    """
    Extract unified request context from Azure Functions request.

    This is THE canonical function for determining execution context.

    Authentication Priority:
    1. Function key (x-functions-key header or ?code param)
       - Sets is_function_key=True
       - User is "system"
       - org_id from X-Organization-Id header (optional)

    2. Easy Auth (X-MS-CLIENT-PRINCIPAL from SWA)
       - Sets is_function_key=False
       - User from principal
       - org_id derived from user's org in database
       - Platform admins can override org_id via X-Organization-Id header

    Scoping Rules:
    - Platform admins: Can set X-Organization-Id or leave None for GLOBAL
    - Regular users: org_id derived from database, cannot override
    - Function keys: Can set X-Organization-Id or leave None for GLOBAL

    Args:
        req: Azure Functions HTTP request

    Returns:
        RequestContext with user, org, and permissions

    Raises:
        ValueError: If user not found in database or lacks org context
    """
    # Check if function key authentication
    # Azure Functions already validated the key if auth_level=FUNCTION
    # We just need to detect if it was used
    function_key = req.headers.get('x-functions-key') or req.params.get('code')

    if function_key:
        # Function key authentication - system caller
        org_id = req.headers.get('X-Organization-Id')  # Optional

        logger.info(f"Function key authentication: scope={org_id or 'GLOBAL'}")

        return RequestContext(
            user_id="system",
            email="system@local",
            name="System (Function Key)",
            org_id=org_id,
            is_platform_admin=True,  # Function keys have admin privileges
            is_function_key=True
        )

    # Try Easy Auth (X-MS-CLIENT-PRINCIPAL from SWA)
    principal_header = req.headers.get('X-MS-CLIENT-PRINCIPAL')

    if not principal_header:
        # No authentication found
        # This should only happen if auth_level=ANONYMOUS
        # For local dev, we allow it and treat as GLOBAL system user
        logger.warning("No authentication found, treating as local dev system user")

        return RequestContext(
            user_id="local-dev",
            email="local-dev@system.local",
            name="Local Development",
            org_id=None,  # GLOBAL scope
            is_platform_admin=True,
            is_function_key=True
        )

    # Parse Easy Auth principal
    try:
        principal_json = base64.b64decode(principal_header).decode('utf-8')
        principal_data = json.loads(principal_json)

        user_id = principal_data.get('userId')
        email = principal_data.get('userDetails', '')
        name = email.split('@')[0] if email else user_id
        user_roles = principal_data.get('userRoles', [])

        if not user_id:
            raise ValueError("X-MS-CLIENT-PRINCIPAL missing userId")

        logger.info(f"Easy Auth user: {email}, roles: {user_roles}")

    except Exception as e:
        logger.error(f"Failed to parse Easy Auth principal: {e}")
        raise ValueError(f"Invalid authentication: {e}") from e

    # Check if user is platform admin (role set by GetRoles endpoint)
    is_admin = 'PlatformAdmin' in user_roles

    # Determine org_id based on user role and headers
    provided_org_id = req.headers.get('X-Organization-Id')

    if is_admin:
        # Platform admin can specify org or work in GLOBAL scope
        org_id = provided_org_id  # May be None for GLOBAL

        if org_id:
            logger.info(f"Platform admin {email} in org scope: {org_id}")
        else:
            logger.info(f"Platform admin {email} in GLOBAL scope")

        return RequestContext(
            user_id=user_id,
            email=email,
            name=name,
            org_id=org_id,
            is_platform_admin=True,
            is_function_key=False
        )

    # Regular user - must derive org from database
    if provided_org_id:
        # Non-admin cannot override org context
        logger.warning(f"Non-admin user {email} attempted to set X-Organization-Id")
        raise PermissionError("Only platform administrators can override organization context")

    # Look up user's org in database
    org_id = _get_user_org_id(email)

    if not org_id:
        # User exists but has no org assignment
        # Try auto-provisioning by domain before failing
        logger.info(f"User {email} has no org assignment, attempting auto-provisioning")

        try:
            from shared.user_provisioning import ensure_user_provisioned

            result = ensure_user_provisioned(email)

            if result.was_created:
                logger.info(f"Auto-provisioned user {email} to org {result.org_id}")

            org_id = result.org_id

            if not org_id:
                # Still no org after provisioning attempt
                raise ValueError(f"User {email} has no organization assignment. Contact administrator.")

        except Exception as e:
            logger.error(f"Auto-provisioning failed for {email}: {e}")
            raise ValueError(f"User {email} has no organization assignment. Contact administrator.") from e

    logger.info(f"User {email} in org scope: {org_id}")

    return RequestContext(
        user_id=user_id,
        email=email,
        name=name,
        org_id=org_id,
        is_platform_admin=False,
        is_function_key=False
    )


def _get_user_org_id(email: str) -> str | None:
    """
    Look up user's organization ID from database.

    Queries the Relationships table for user-to-org permissions.
    Structure: PK="GLOBAL", RK="userperm:{user_email}:{org_id}"
    """
    from shared.storage import TableStorageService

    try:
        relationships_table = TableStorageService("Relationships")
        # Query for user permissions
        # Use string comparison: 'userperm:email:' to 'userperm:email~' (~ is after : in ASCII)
        query_filter = f"PartitionKey eq 'GLOBAL' and RowKey ge 'userperm:{email}:' and RowKey lt 'userperm:{email}~'"
        entities = list(relationships_table.query_entities(query_filter))

        if not entities:
            logger.warning(f"User {email} has no org assignments")
            return None

        if len(entities) > 1:
            logger.warning(f"Multiple org assignments for {email}, using first")

        # Extract org_id from RowKey "userperm:{email}:{org_id}"
        row_key = entities[0].get("RowKey")
        assert row_key is not None, "RowKey is None"
        parts = row_key.split(":", 2)
        if len(parts) >= 3:
            org_id = parts[2]
            logger.debug(f"User {email} belongs to org: {org_id}")
            return org_id

        return None

    except Exception as e:
        logger.error(f"Error looking up user org: {e}")
        return None
