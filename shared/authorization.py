"""
Authorization helpers for Bifrost Integrations
Provides permission checking and form access control
"""

import logging

from shared.repositories.executions import ExecutionRepository
from shared.repositories.forms_file import FormsFileRepository
from shared.repositories.roles import RoleRepository
from shared.context import ExecutionContext

logger = logging.getLogger(__name__)


# ============================================================================
# Private Helper Functions
# ============================================================================
# Note: Most helper functions removed - repositories now handle fallback logic


# ============================================================================
# Public Authorization Functions
# ============================================================================


async def can_user_view_form(context: ExecutionContext, form_id: str) -> bool:
    """
    Check if user can view a form.

    Rules:
    - Platform admins: can view all forms (active and inactive)
    - Regular users:
        - Must be active form
        - accessLevel="authenticated" → any authenticated user
        - accessLevel="role_based" (or None) → user must have assigned role

    Args:
        context: ExecutionContext
        form_id: Form ID (UUID)

    Returns:
        True if user can view form, False otherwise
    """
    # Get form using repository (handles GLOBAL fallback automatically)
    form_repo = FormsFileRepository(context)
    form = await form_repo.get_form(form_id)

    if not form:
        return False

    # Platform admins can view all forms (including inactive)
    if context.is_platform_admin:
        return True

    # Regular users can only view active forms
    if not form.isActive:
        return False

    # Check access level (default to role_based if not set)
    access_level = form.accessLevel or "role_based"

    if access_level == "authenticated":
        # Any authenticated user can access
        return True
    elif access_level == "role_based":
        # Check role membership
        user_roles = await get_user_role_ids(context.user_id)
        form_roles = await get_form_role_ids(form_id)
        return any(role in form_roles for role in user_roles)
    # Future: handle "public" for unauthenticated access

    return False


async def can_user_execute_form(context: ExecutionContext, form_id: str) -> bool:
    """
    Check if user can execute a form.

    Same rules as can_user_view_form (if you can view it, you can execute it).

    Args:
        context: ExecutionContext
        form_id: Form ID (UUID)

    Returns:
        True if user can execute form, False otherwise
    """
    return await can_user_view_form(context, form_id)


async def get_user_visible_forms(context: ExecutionContext) -> list[dict]:
    """
    Get all forms visible to the user (filtered by permissions).

    Rules:
    - Platform admins: see all forms (active and inactive) in context.scope
    - Regular users: see active forms they have access to based on accessLevel:
        - authenticated: all active forms with this access level
        - role_based: only forms where user has an assigned role

    Args:
        context: ExecutionContext

    Returns:
        List of form entities (as dicts for backward compatibility)
    """
    form_repo = FormsFileRepository(context)

    # Platform admin sees all forms (including inactive) in their current scope (set by X-Organization-Id)
    if context.is_platform_admin:
        # Admin can see all forms (active and inactive) in their scope, including GLOBAL forms
        forms = await form_repo.list_forms(include_global=True, active_only=False)
        # Convert Form models to dicts for backward compatibility (JSON-serializable)
        return [form.model_dump(mode="json") for form in forms]

    # Regular user: Get forms with GLOBAL fallback and filter to active only
    all_forms = await form_repo.list_forms(include_global=True, active_only=True)

    # Get user's role IDs once for efficiency
    user_role_ids = await get_user_role_ids(context.user_id)

    # Filter forms by access level
    visible_forms = []
    for form in all_forms:
        access_level = form.accessLevel or "role_based"

        if access_level == "authenticated":
            # Any authenticated user can see this form
            visible_forms.append(form)
        elif access_level == "role_based":
            # Check if user has any of the roles assigned to this form
            form_role_ids = await get_form_role_ids(form.id)
            if any(role_id in form_role_ids for role_id in user_role_ids):
                visible_forms.append(form)

    # Convert Form models to dicts for backward compatibility (JSON-serializable)
    return [form.model_dump(mode="json") for form in visible_forms]


def can_user_view_execution(context: ExecutionContext, execution_entity: dict) -> bool:
    """
    Check if user can view an execution.

    Rules:
    - Platform admins: can view all executions
    - Regular users: can only view THEIR executions

    Args:
        context: ExecutionContext
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


async def get_user_executions(context: ExecutionContext, limit: int | None = None) -> list[dict]:
    """
    Get executions visible to the user.

    Rules:
    - Platform admins: all executions in context.scope
    - Regular users: only THEIR executions

    Args:
        context: ExecutionContext
        limit: Optional limit on number of executions to return

    Returns:
        List of execution entities (as dicts for backward compatibility)
    """
    exec_repo = ExecutionRepository(context)

    if context.is_platform_admin:
        # Platform admin sees all executions in scope
        executions = await exec_repo.list_executions(limit=limit or 1000)
    else:
        # Regular user sees only their executions (using optimized user index)
        executions = await exec_repo.list_executions_by_user(
            user_id=context.user_id,
            limit=limit or 50
        )

    # Convert WorkflowExecution models to dicts for backward compatibility
    return [execution.model_dump() for execution in executions]


async def get_user_role_ids(user_id: str, role_repository: RoleRepository | None = None) -> list[str]:
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

    return await role_repository.get_user_role_ids(user_id)


async def get_form_role_ids(form_id: str, role_repository: RoleRepository | None = None) -> list[str]:
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

    return await role_repository.get_form_role_ids(form_id)
