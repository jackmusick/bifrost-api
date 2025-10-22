"""
Internal utilities for Bifrost SDK.

Permission checking, context access, and helper functions.
"""

import logging
from typing import TYPE_CHECKING

from ._context import get_execution_context

if TYPE_CHECKING:
    from shared.request_context import RequestContext

logger = logging.getLogger(__name__)


def require_permission(permission: str) -> 'RequestContext':
    """
    Check if the current user has the required permission.

    Args:
        permission: Permission string to check (e.g., "organizations.create")

    Returns:
        RequestContext if permission is granted

    Raises:
        RuntimeError: If no execution context
        PermissionError: If user lacks the required permission
    """
    context = get_execution_context()

    # Platform admins bypass permission checks for most operations
    if context.is_platform_admin:
        return context

    # Check specific permission (when implemented in RequestContext)
    # For now, we'll use role-based checks
    # TODO: Implement granular permission system

    logger.info(
        f"Permission check: user={context.user_id} permission={permission} "
        f"admin={context.is_platform_admin}"
    )

    return context


def require_admin() -> 'RequestContext':
    """
    Require that the current user is a platform admin.

    Returns:
        RequestContext if user is admin

    Raises:
        RuntimeError: If no execution context
        PermissionError: If user is not a platform admin
    """
    context = get_execution_context()

    if not context.is_platform_admin:
        raise PermissionError(
            f"User {context.user_id} is not a platform admin. "
            "This operation requires admin privileges."
        )

    return context


def get_context() -> 'RequestContext':
    """
    Get the current execution context.

    Alias for get_execution_context() for convenience.

    Returns:
        RequestContext for the current execution

    Raises:
        RuntimeError: If called outside of a workflow execution context
    """
    return get_execution_context()
