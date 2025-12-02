"""
Forms Router

CRUD operations for workflow forms.
Support for org-specific and global forms.
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from src.core.auth import Context, CurrentSuperuser
from src.core.database import DbSession
from src.models.orm import Form as FormORM
from src.models.models import FormCreate, FormUpdate, FormPublic

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
