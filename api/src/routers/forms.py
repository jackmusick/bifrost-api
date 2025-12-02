"""
Forms Router

CRUD operations for workflow forms.
Support for org-specific and global forms.
Form execution for org users with access control.
"""

import logging
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, HTTPException, status
from sqlalchemy import select

from src.core.auth import Context, CurrentActiveUser, CurrentSuperuser
from src.core.database import DbSession
from src.core.pubsub import publish_execution_update
from src.models.orm import Form as FormORM, FormRole as FormRoleORM, UserRole as UserRoleORM
from src.models.models import FormCreate, FormUpdate, FormPublic
from src.models.schemas import WorkflowExecutionResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/forms", tags=["Forms"])


@router.get(
    "",
    response_model=list[FormPublic],
    summary="List forms",
    description="List all forms visible to the user based on their permissions",
)
async def list_forms(
    ctx: Context,
    db: DbSession,
) -> list[FormPublic]:
    """List all forms visible to the user."""
    query = select(FormORM).where(FormORM.is_active)

    # Platform admins see all forms, org users see only their org's forms
    if not ctx.user.is_superuser:
        if ctx.org_id:
            query = query.where(FormORM.organization_id == ctx.org_id)
        else:
            # User has no org - no forms visible
            return []

    query = query.order_by(FormORM.name)
    result = await db.execute(query)
    forms = result.scalars().all()

    return [FormPublic.model_validate(f) for f in forms]


@router.post(
    "",
    response_model=FormPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new form",
    description="Create a new form (Platform admin only)",
)
async def create_form(
    request: FormCreate,
    ctx: Context,
    user: CurrentSuperuser,
    db: DbSession,
) -> FormPublic:
    """Create a new form."""
    now = datetime.utcnow()

    # Convert form_schema to dict if it's a FormSchema model
    form_schema_data = request.form_schema
    if hasattr(form_schema_data, 'model_dump'):
        form_schema_data = form_schema_data.model_dump()

    form = FormORM(
        name=request.name,
        description=request.description,
        linked_workflow=request.linked_workflow,
        launch_workflow_id=request.launch_workflow_id,
        default_launch_params=request.default_launch_params,
        allowed_query_params=request.allowed_query_params,
        form_schema=form_schema_data,
        access_level=request.access_level,
        is_active=True,
        created_by=ctx.user.email,
        created_at=now,
        updated_at=now,
    )

    db.add(form)
    await db.flush()
    await db.refresh(form)

    logger.info(f"Created form {form.id}: {form.name}")
    return FormPublic.model_validate(form)


@router.get(
    "/{form_id}",
    response_model=FormPublic,
    summary="Get form by ID",
    description="Get a specific form by ID. User must have access to the form.",
)
async def get_form(
    form_id: UUID,
    ctx: Context,
    db: DbSession,
) -> FormPublic:
    """Get a specific form by ID."""
    result = await db.execute(select(FormORM).where(FormORM.id == form_id))
    form = result.scalar_one_or_none()

    if not form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form not found",
        )

    # Check access
    if not ctx.user.is_superuser:
        if form.organization_id != ctx.org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to form",
            )

    return FormPublic.model_validate(form)


@router.patch(
    "/{form_id}",
    response_model=FormPublic,
    summary="Update a form",
    description="Update an existing form (Platform admin only)",
)
async def update_form(
    form_id: UUID,
    request: FormUpdate,
    ctx: Context,
    user: CurrentSuperuser,
    db: DbSession,
) -> FormPublic:
    """Update a form."""
    result = await db.execute(select(FormORM).where(FormORM.id == form_id))
    form = result.scalar_one_or_none()

    if not form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form not found",
        )

    if request.name is not None:
        form.name = request.name
    if request.description is not None:
        form.description = request.description
    if request.linked_workflow is not None:
        form.linked_workflow = request.linked_workflow
    if request.launch_workflow_id is not None:
        form.launch_workflow_id = request.launch_workflow_id
    if request.default_launch_params is not None:
        form.default_launch_params = request.default_launch_params
    if request.allowed_query_params is not None:
        form.allowed_query_params = request.allowed_query_params
    if request.form_schema is not None:
        form_schema_data = request.form_schema
        if hasattr(form_schema_data, 'model_dump'):
            form_schema_data = form_schema_data.model_dump()
        form.form_schema = form_schema_data
    if request.is_active is not None:
        form.is_active = request.is_active
    if request.access_level is not None:
        form.access_level = request.access_level
    if request.assigned_roles is not None:
        form.assigned_roles = request.assigned_roles

    form.updated_at = datetime.utcnow()

    await db.flush()
    await db.refresh(form)

    logger.info(f"Updated form {form_id}")
    return FormPublic.model_validate(form)


# Keep PUT for backwards compatibility
@router.put(
    "/{form_id}",
    response_model=FormPublic,
    summary="Update a form",
    description="Update an existing form (Platform admin only)",
    include_in_schema=False,  # Hide from OpenAPI, use PATCH instead
)
async def update_form_put(
    form_id: UUID,
    request: FormUpdate,
    ctx: Context,
    user: CurrentSuperuser,
    db: DbSession,
) -> FormPublic:
    """Update a form (PUT - for backwards compatibility)."""
    return await update_form(form_id, request, ctx, user, db)


@router.delete(
    "/{form_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a form",
    description="Soft delete a form (Platform admin only)",
)
async def delete_form(
    form_id: UUID,
    ctx: Context,
    user: CurrentSuperuser,
    db: DbSession,
) -> None:
    """Soft delete a form."""
    result = await db.execute(select(FormORM).where(FormORM.id == form_id))
    form = result.scalar_one_or_none()

    if not form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form not found",
        )

    form.is_active = False
    form.updated_at = datetime.utcnow()

    await db.flush()
    logger.info(f"Soft deleted form {form_id}")


# =============================================================================
# Form Execution
# =============================================================================


async def _check_form_access(
    db: DbSession,
    form: FormORM,
    user_id: UUID,
    is_superuser: bool,
) -> bool:
    """
    Check if user has access to execute a form.

    Access levels:
    - 'public': Anyone can access (not recommended for production)
    - 'authenticated': Any logged-in user can access
    - 'role_based': User must be assigned to a role that has this form
    """
    # Platform admins always have access
    if is_superuser:
        return True

    access_level = form.access_level or "authenticated"

    if access_level == "public":
        return True

    if access_level == "authenticated":
        return True  # User is already authenticated to reach this point

    if access_level == "role_based":
        # Check if user has a role that is assigned to this form
        # 1. Get all roles the user has
        user_roles_query = select(UserRoleORM.role_id).where(
            UserRoleORM.user_id == user_id
        )
        user_roles_result = await db.execute(user_roles_query)
        user_role_ids = list(user_roles_result.scalars().all())

        if not user_role_ids:
            return False

        # 2. Check if any of those roles have this form assigned
        form_role_query = select(FormRoleORM).where(
            FormRoleORM.form_id == form.id,
            FormRoleORM.role_id.in_(user_role_ids),
        )
        form_role_result = await db.execute(form_role_query)
        has_access = form_role_result.scalar_one_or_none() is not None

        return has_access

    # Unknown access level - deny by default
    return False


@router.post(
    "/{form_id}/execute",
    response_model=WorkflowExecutionResponse,
    summary="Execute a form",
    description="Execute the workflow linked to a form. Requires appropriate access based on form's access_level.",
)
async def execute_form(
    form_id: UUID,
    ctx: Context,
    user: CurrentActiveUser,
    db: DbSession,
    input_data: dict = Body(default={}),
) -> WorkflowExecutionResponse:
    """
    Execute the workflow linked to a form.

    This endpoint allows org users to execute workflows through forms they have access to.
    Access control is based on the form's access_level:
    - 'authenticated': Any logged-in user can execute
    - 'role_based': User must be assigned to a role that has this form
    """
    from shared.context import ExecutionContext as SharedContext, Organization
    from shared.handlers.workflows_handlers import execute_workflow_internal
    from src.models.schemas import ExecutionStatus

    # Get the form
    result = await db.execute(select(FormORM).where(FormORM.id == form_id))
    form = result.scalar_one_or_none()

    if not form or not form.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form not found",
        )

    # Check access
    has_access = await _check_form_access(db, form, ctx.user.user_id, ctx.user.is_superuser)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this form",
        )

    # Form must have a linked workflow
    if not form.linked_workflow:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Form has no linked workflow",
        )

    # Merge default launch params with provided input
    merged_params = {**(form.default_launch_params or {}), **input_data}

    # Create organization object if org_id is set
    org = None
    if ctx.org_id:
        org = Organization(id=str(ctx.org_id), name="", is_active=True)

    # Create shared context compatible with existing handlers
    shared_ctx = SharedContext(
        user_id=str(ctx.user.user_id),
        name=ctx.user.name,
        email=ctx.user.email,
        scope=str(ctx.org_id) if ctx.org_id else "GLOBAL",
        organization=org,
        is_platform_admin=ctx.user.is_superuser,
        is_function_key=False,
        execution_id=str(uuid4()),
    )

    try:
        # Execute the linked workflow
        result_dict, status_code = await execute_workflow_internal(
            context=shared_ctx,
            workflow_name=form.linked_workflow,
            parameters=merged_params,
            form_id=str(form.id),
            transient=False,
        )

        # Convert to response model
        if status_code >= 400:
            # Error response
            raise HTTPException(
                status_code=status_code,
                detail=result_dict.get("message", "Execution failed"),
            )

        # Success or pending response
        execution_id = result_dict.get("executionId", "")
        status_str = result_dict.get("status", "Pending")

        # Map status string to enum
        status_map = {
            "Pending": ExecutionStatus.PENDING,
            "Running": ExecutionStatus.RUNNING,
            "Success": ExecutionStatus.SUCCESS,
            "Failed": ExecutionStatus.FAILED,
        }
        exec_status = status_map.get(status_str, ExecutionStatus.PENDING)

        # Publish execution update via WebSocket
        if execution_id:
            await publish_execution_update(
                execution_id=execution_id,
                status=exec_status.value,
                data={
                    "form_id": str(form.id),
                    "workflow_name": form.linked_workflow,
                },
            )

        logger.info(f"Form {form_id} executed by user {ctx.user.email}, execution_id={execution_id}")

        return WorkflowExecutionResponse(
            execution_id=execution_id,
            status=exec_status,
            result=result_dict.get("result"),
            error=result_dict.get("error"),
            error_type=result_dict.get("errorType"),
            duration_ms=result_dict.get("durationMs"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing form {form_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute form",
        )
