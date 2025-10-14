"""
Authorization helpers for Bifrost Integrations
Provides permission checking and form access control
"""

import logging
from typing import List, Optional
from shared.request_context import RequestContext
from shared.storage import TableStorageService

logger = logging.getLogger(__name__)


def can_user_view_form(context: RequestContext, form_id: str) -> bool:
    """
    Check if user can view a form.

    Rules:
    - Platform admins: can view all forms
    - Regular users: can view public forms OR forms assigned to their role

    Args:
        context: RequestContext
        form_id: Form ID (UUID)

    Returns:
        True if user can view form, False otherwise
    """
    # Platform admins can view all forms
    if context.is_platform_admin:
        return True

    # Get form - regular users need to check BOTH GLOBAL and their org
    from shared.request_context import RequestContext as RC

    form_entity = None

    # Try GLOBAL first
    try:
        global_context = RC(
            user_id=context.user_id,
            email=context.email,
            name=context.name,
            org_id=None,  # GLOBAL
            is_platform_admin=False,
            is_function_key=False
        )
        global_entities_service = TableStorageService("Entities", context=global_context)
        form_entity = global_entities_service.get_entity("GLOBAL", f"form:{form_id}")
    except Exception:
        # Form not in GLOBAL, try user's org
        pass

    # If not found in GLOBAL, try user's org
    if not form_entity and context.org_id:
        try:
            org_entities_service = TableStorageService("Entities", context=context)
            form_entity = org_entities_service.get_entity(context.org_id, f"form:{form_id}")
        except Exception as e:
            logger.error(f"Error fetching form {form_id}: {e}")
            return False

    if not form_entity:
        return False

    # Public forms - anyone can view
    if form_entity.get("IsPublic"):
        return True

    # Check if user has a role that grants access
    relationships_service = TableStorageService("Relationships")

    # Get user's roles
    user_role_entities = list(relationships_service.query_entities(
        f"PartitionKey eq 'GLOBAL' and RowKey ge 'userrole:{context.user_id}:' and RowKey lt 'userrole:{context.user_id};'"
    ))

    # Extract role UUIDs from row keys: "userrole:user_id:role_uuid"
    role_ids = [entity['RowKey'].split(':', 2)[2] for entity in user_role_entities]

    # Check if any role grants access to this form
    for role_id in role_ids:
        form_role_entities = list(relationships_service.query_entities(
            f"PartitionKey eq 'GLOBAL' and RowKey eq 'formrole:{form_id}:{role_id}'"
        ))
        if form_role_entities:
            return True

    return False


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


def get_user_visible_forms(context: RequestContext) -> List[dict]:
    """
    Get all forms visible to the user (filtered by permissions).

    Rules:
    - Platform admins: see all forms in context.scope (controlled by X-Organization-Id header)
    - Regular users: see GLOBAL forms + their org's forms (based on role assignments)
      - Public forms are always visible
      - Private forms require role assignment

    Args:
        context: RequestContext

    Returns:
        List of form entities user can view
    """
    from shared.request_context import RequestContext as RC

    # Platform admin sees all forms in their current scope (set by X-Organization-Id)
    if context.is_platform_admin:
        entities_service = TableStorageService("Entities", context=context)
        all_forms = list(entities_service.query_entities(
            f"PartitionKey eq '{context.scope}' and RowKey ge 'form:' and RowKey lt 'form;'"
        ))
        return all_forms

    # Regular user: Query BOTH GLOBAL and their org's forms
    all_forms = []

    # Query GLOBAL forms
    global_context = RC(
        user_id=context.user_id,
        email=context.email,
        name=context.name,
        org_id=None,  # GLOBAL
        is_platform_admin=False,
        is_function_key=False
    )
    global_entities_service = TableStorageService("Entities", context=global_context)
    global_forms = list(global_entities_service.query_entities(
        f"PartitionKey eq 'GLOBAL' and RowKey ge 'form:' and RowKey lt 'form;'"
    ))
    all_forms.extend(global_forms)

    # Query user's org forms (if they have an org)
    if context.org_id:
        org_entities_service = TableStorageService("Entities", context=context)
        org_forms = list(org_entities_service.query_entities(
            f"PartitionKey eq '{context.org_id}' and RowKey ge 'form:' and RowKey lt 'form;'"
        ))
        all_forms.extend(org_forms)

    # Get user's roles
    relationships_service = TableStorageService("Relationships")
    user_role_entities = list(relationships_service.query_entities(
        f"PartitionKey eq 'GLOBAL' and RowKey ge 'userrole:{context.user_id}:' and RowKey lt 'userrole:{context.user_id};'"
    ))

    # Extract role UUIDs
    user_role_ids = {entity['RowKey'].split(':', 2)[2] for entity in user_role_entities}

    # Filter forms by permissions (track form IDs to avoid duplicates)
    visible_forms = []
    seen_form_ids = set()

    for form_entity in all_forms:
        # Extract form UUID from row key "form:uuid"
        form_id = form_entity['RowKey'].split(':', 1)[1]

        # Skip if we've already added this form
        if form_id in seen_form_ids:
            continue

        # Public forms always visible
        if form_entity.get("IsPublic"):
            visible_forms.append(form_entity)
            seen_form_ids.add(form_id)
            continue

        # Check if user has assigned role for this form
        form_role_entities = list(relationships_service.query_entities(
            f"PartitionKey eq 'GLOBAL' and RowKey ge 'formrole:{form_id}:' and RowKey lt 'formrole:{form_id};'"
        ))

        # Extract role UUIDs from form roles
        form_role_ids = {entity['RowKey'].split(':', 2)[2] for entity in form_role_entities}

        # If user has any role that grants access, include form
        if user_role_ids & form_role_ids:  # Set intersection
            visible_forms.append(form_entity)
            seen_form_ids.add(form_id)

    return visible_forms


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
    executed_by = execution_entity.get("ExecutedBy")
    return executed_by == context.user_id


def get_user_executions(context: RequestContext, limit: Optional[int] = None) -> List[dict]:
    """
    Get executions visible to the user.

    Rules:
    - Platform admins: all executions in context.scope
    - Regular users: only THEIR executions

    Args:
        context: RequestContext
        limit: Optional limit on number of executions to return

    Returns:
        List of execution entities
    """
    if context.is_platform_admin:
        # Platform admin sees all executions in scope
        entities_service = TableStorageService("Entities", context=context)
        executions = list(entities_service.query_entities(
            f"PartitionKey eq '{context.scope}' and RowKey ge 'execution:' and RowKey lt 'execution;'"
        ))
    else:
        # Regular user sees only their executions (from dual index)
        relationships_service = TableStorageService("Relationships")
        user_exec_entities = list(relationships_service.query_entities(
            f"PartitionKey eq 'GLOBAL' and RowKey ge 'userexec:{context.user_id}:' and RowKey lt 'userexec:{context.user_id};'"
        ))

        # Extract execution IDs and fetch full entities
        exec_ids = [entity.get("ExecutionId") for entity in user_exec_entities]

        entities_service = TableStorageService("Entities", context=context)
        executions = []
        for exec_id in exec_ids:
            # Query by ExecutionId field (within user's org partition)
            exec_entities = list(entities_service.query_entities(
                f"PartitionKey eq '{context.org_id}' and ExecutionId eq '{exec_id}'"
            ))
            if exec_entities:
                executions.append(exec_entities[0])

    # Apply limit if specified
    if limit:
        executions = executions[:limit]

    return executions


def get_user_role_ids(user_id: str, relationships_service: TableStorageService) -> List[str]:
    """
    Get all role IDs (UUIDs) assigned to a user.

    Args:
        user_id: User ID
        relationships_service: TableStorageService for Relationships table

    Returns:
        List of role UUIDs
    """
    user_role_entities = list(relationships_service.query_entities(
        f"PartitionKey eq 'GLOBAL' and RowKey ge 'userrole:{user_id}:' and RowKey lt 'userrole:{user_id};'"
    ))

    # Extract role UUIDs from row keys: "userrole:user_id:role_uuid"
    role_ids = [entity['RowKey'].split(':', 2)[2] for entity in user_role_entities]
    return role_ids


def get_form_role_ids(form_id: str, relationships_service: TableStorageService) -> List[str]:
    """
    Get all role IDs (UUIDs) that can access a form.

    Args:
        form_id: Form ID (UUID)
        relationships_service: TableStorageService for Relationships table

    Returns:
        List of role UUIDs
    """
    form_role_entities = list(relationships_service.query_entities(
        f"PartitionKey eq 'GLOBAL' and RowKey ge 'formrole:{form_id}:' and RowKey lt 'formrole:{form_id};'"
    ))

    # Extract role UUIDs from row keys: "formrole:form_uuid:role_uuid"
    role_ids = [entity['RowKey'].split(':', 2)[2] for entity in form_role_entities]
    return role_ids
