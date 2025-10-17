"""
Authorization helpers for Bifrost Integrations
Provides permission checking and form access control
"""

import logging

from shared.repositories.executions import ExecutionRepository
from shared.repositories.forms import FormRepository
from shared.repositories.roles import RoleRepository
from shared.request_context import RequestContext

logger = logging.getLogger(__name__)


# ============================================================================
# Private Helper Functions
# ============================================================================
# Note: Most helper functions removed - repositories now handle fallback logic


# ============================================================================
# Public Authorization Functions
# ============================================================================


def can_user_view_form(context: RequestContext, form_id: str) -> bool:
    """
    Check if user can view a form.

    Rules:
    - Platform admins: can view all forms
    - Regular users: can view all active forms (global forms + their org's forms)

    Args:
        context: RequestContext
        form_id: Form ID (UUID)

    Returns:
        True if user can view form, False otherwise
    """
    # Platform admins can view all forms
    if context.is_platform_admin:
        return True

    # Get form using repository (handles GLOBAL fallback automatically)
    form_repo = FormRepository(context)
    form = form_repo.get_form(form_id)

    if not form:
        return False

    # Check if form is active
    if not form.isActive:
        return False

    # If we got the form, user can view it (repository handles scope checking)
    return True


def can_user_execute_form(context: RequestContext, form_id: str) -> bool:
    """
    Check if user can execute a form.

    Same rules as can_user_view_form (if you can view it, you can execute it).

    Args:
        context: RequestContext
        form_id: Form ID (UUID)

    Returns:
        True if user can execute form, False otherwise
    """
    return can_user_view_form(context, form_id)


def get_user_visible_forms(context: RequestContext) -> list[dict]:
    """
    Get all forms visible to the user (filtered by permissions).

    Rules:
    - Platform admins: see all forms in context.scope (controlled by X-Organization-Id header)
    - Regular users: see all active GLOBAL forms + all active forms in their org

    Args:
        context: RequestContext

    Returns:
        List of form entities (as dicts for backward compatibility)
    """
    form_repo = FormRepository(context)

    # Platform admin sees all forms in their current scope (set by X-Organization-Id)
    if context.is_platform_admin:
        # Admin can see all forms (including inactive) in their scope
        forms = form_repo.list_forms(include_global=False, active_only=False)
        # Convert Form models to dicts for backward compatibility (JSON-serializable)
        return [form.model_dump(mode="json") for form in forms]

    # Regular user: Get forms with GLOBAL fallback and filter to active only
    forms = form_repo.list_forms(include_global=True, active_only=True)

    # Convert Form models to dicts for backward compatibility (JSON-serializable)
    return [form.model_dump(mode="json") for form in forms]


def can_user_view_execution(context: RequestContext, execution_entity: dict) -> bool:
    """
    Check if user can view an execution.

    Rules:
    - Platform admins: can view all executions
    - Regular users: can only view THEIR executions

    Args:
        context: RequestContext
        execution_entity: Execution entity dictionary

    Returns:
        True if user can view execution, False otherwise
    """
    # Platform admins can view all
    if context.is_platform_admin:
        return True

    # Regular users can only view their own executions
    # ExecutedBy stores user_id (not email)
    executed_by = execution_entity.get("ExecutedBy")
    return executed_by == context.user_id


def get_user_executions(context: RequestContext, limit: int | None = None) -> list[dict]:
    """
    Get executions visible to the user.

    Rules:
    - Platform admins: all executions in context.scope
    - Regular users: only THEIR executions

    Args:
        context: RequestContext
        limit: Optional limit on number of executions to return

    Returns:
        List of execution entities (as dicts for backward compatibility)
    """
    exec_repo = ExecutionRepository(context)

    if context.is_platform_admin:
        # Platform admin sees all executions in scope
        executions = exec_repo.list_executions(limit=limit or 1000)
    else:
        # Regular user sees only their executions (using optimized user index)
        executions = exec_repo.list_executions_by_user(
            user_id=context.user_id,
            limit=limit or 50
        )

    # Convert WorkflowExecution models to dicts for backward compatibility
    return [execution.model_dump() for execution in executions]


def get_user_role_ids(user_id: str, role_repository: RoleRepository | None = None) -> list[str]:
    """
    Get all role IDs (UUIDs) assigned to a user.

    Args:
        user_id: User ID
        role_repository: Optional RoleRepository instance (for backward compatibility)

    Returns:
        List of role UUIDs
    """
    if role_repository is None:
        role_repository = RoleRepository()

    return role_repository.get_user_role_ids(user_id)


def get_form_role_ids(form_id: str, role_repository: RoleRepository | None = None) -> list[str]:
    """
    Get all role IDs (UUIDs) that can access a form.

    Args:
        form_id: Form ID (UUID)
        role_repository: Optional RoleRepository instance (for backward compatibility)

    Returns:
        List of role UUIDs
    """
    if role_repository is None:
        role_repository = RoleRepository()

    return role_repository.get_form_role_ids(form_id)
