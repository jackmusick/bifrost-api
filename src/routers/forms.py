"""
Forms Router

CRUD operations for workflow forms.
Support for org-specific and global forms.
API-compatible with the existing Azure Functions implementation.
"""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

# Import existing Pydantic models for API compatibility
from shared.models import (
    CreateFormRequest,
    DataProviderRequest,
    DataProviderResponse,
    Form,
    FormExecuteRequest,
    FormStartupResponse,
    RoleFormsResponse,
    UpdateFormRequest,
    WorkflowExecutionResponse,
)

from src.core.auth import Context, CurrentActiveUser, CurrentSuperuser
from src.core.database import DbSession
from src.core.pubsub import publish_execution_update

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/forms", tags=["Forms"])


# =============================================================================
# HTTP Endpoints
# =============================================================================


@router.get(
    "",
    response_model=list[Form],
    summary="List forms",
    description="List all forms visible to the user based on their permissions",
)
async def list_forms(
    ctx: Context,
) -> list[Form]:
    """List all forms visible to the user."""
    from shared.handlers.forms_handlers import list_forms_handler
    from shared.context import ExecutionContext as SharedContext

    try:
        # Create shared context
        shared_ctx = SharedContext(
            user_id=str(ctx.user.user_id),
            name=ctx.user.name,
            email=ctx.user.email,
            is_platform_admin=ctx.user.is_superuser,
            org_id=str(ctx.org_id) if ctx.org_id else None,
        )

        # Create mock request for handler compatibility
        class MockRequest:
            context = shared_ctx

        result, status_code = await list_forms_handler(MockRequest(), shared_ctx)

        if status_code != 200:
            raise HTTPException(status_code=status_code, detail=result.get("message", "Error"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing forms: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list forms",
        )


@router.post(
    "",
    response_model=Form,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new form",
    description="Create a new form (Platform admin only)",
)
async def create_form(
    request: CreateFormRequest,
    ctx: Context,
    user: CurrentSuperuser,
) -> Form:
    """Create a new form."""
    from shared.handlers.forms_handlers import create_form_handler
    from shared.context import ExecutionContext as SharedContext

    try:
        shared_ctx = SharedContext(
            user_id=str(ctx.user.user_id),
            name=ctx.user.name,
            email=ctx.user.email,
            is_platform_admin=ctx.user.is_superuser,
            org_id=str(ctx.org_id) if ctx.org_id else None,
        )

        result, status_code = await create_form_handler(
            request.model_dump(mode="json"),
            shared_ctx,
        )

        if status_code == 201:
            return Form(**result) if isinstance(result, dict) else result
        else:
            raise HTTPException(status_code=status_code, detail=result.get("message", "Error"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating form: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create form",
        )


@router.get(
    "/{form_id}",
    response_model=Form,
    summary="Get form by ID",
    description="Get a specific form by ID. User must have access to the form.",
)
async def get_form(
    form_id: UUID,
    ctx: Context,
) -> Form:
    """Get a specific form by ID."""
    from shared.handlers.forms_handlers import get_form_handler
    from shared.context import ExecutionContext as SharedContext

    try:
        shared_ctx = SharedContext(
            user_id=str(ctx.user.user_id),
            name=ctx.user.name,
            email=ctx.user.email,
            is_platform_admin=ctx.user.is_superuser,
            org_id=str(ctx.org_id) if ctx.org_id else None,
        )

        result, status_code = await get_form_handler(str(form_id), shared_ctx)

        if status_code == 200:
            return Form(**result) if isinstance(result, dict) else result
        elif status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Form not found",
            )
        elif status_code == 403:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to form",
            )
        else:
            raise HTTPException(status_code=status_code, detail=result.get("message", "Error"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting form: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get form",
        )


@router.put(
    "/{form_id}",
    response_model=Form,
    summary="Update a form",
    description="Update an existing form (Platform admin only)",
)
async def update_form(
    form_id: UUID,
    request: UpdateFormRequest,
    ctx: Context,
    user: CurrentSuperuser,
) -> Form:
    """Update a form."""
    from shared.handlers.forms_handlers import update_form_handler
    from shared.context import ExecutionContext as SharedContext

    try:
        shared_ctx = SharedContext(
            user_id=str(ctx.user.user_id),
            name=ctx.user.name,
            email=ctx.user.email,
            is_platform_admin=ctx.user.is_superuser,
            org_id=str(ctx.org_id) if ctx.org_id else None,
        )

        result, status_code = await update_form_handler(
            str(form_id),
            request.model_dump(mode="json", exclude_unset=True),
            shared_ctx,
        )

        if status_code == 200:
            return Form(**result) if isinstance(result, dict) else result
        elif status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Form not found",
            )
        else:
            raise HTTPException(status_code=status_code, detail=result.get("message", "Error"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating form: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update form",
        )


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
) -> None:
    """Soft delete a form."""
    from shared.handlers.forms_handlers import delete_form_handler
    from shared.context import ExecutionContext as SharedContext

    try:
        shared_ctx = SharedContext(
            user_id=str(ctx.user.user_id),
            name=ctx.user.name,
            email=ctx.user.email,
            is_platform_admin=ctx.user.is_superuser,
            org_id=str(ctx.org_id) if ctx.org_id else None,
        )

        result, status_code = await delete_form_handler(str(form_id), shared_ctx)

        if status_code == 204:
            return
        elif status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Form not found",
            )
        else:
            raise HTTPException(status_code=status_code, detail=result.get("message", "Error"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting form: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete form",
        )


@router.post(
    "/{form_id}/startup",
    response_model=FormStartupResponse,
    summary="Execute form's launch workflow",
    description="Execute the form's launch workflow to populate initial form context",
)
@router.get(
    "/{form_id}/startup",
    response_model=FormStartupResponse,
    summary="Execute form's launch workflow",
    description="Execute the form's launch workflow to populate initial form context",
)
async def execute_form_startup(
    form_id: UUID,
    ctx: Context,
    request: Request,
    body: FormExecuteRequest | None = None,
) -> FormStartupResponse:
    """Execute form's launch workflow."""
    from shared.handlers.forms_handlers import execute_form_startup_handler
    from shared.context import ExecutionContext as SharedContext

    try:
        shared_ctx = SharedContext(
            user_id=str(ctx.user.user_id),
            name=ctx.user.name,
            email=ctx.user.email,
            is_platform_admin=ctx.user.is_superuser,
            org_id=str(ctx.org_id) if ctx.org_id else None,
        )

        # Create mock request for handler compatibility
        class MockRequest:
            context = shared_ctx
            org_context = shared_ctx
            params = dict(request.query_params)
            method = request.method

            def get_json(self):
                return body.model_dump() if body else {}

            def get_body(self):
                return b"" if body is None else b"{}"

        mock_req = MockRequest()

        result, status_code = await execute_form_startup_handler(
            str(form_id),
            mock_req,
            shared_ctx,
            shared_ctx,
        )

        if status_code == 200:
            return FormStartupResponse(**result) if isinstance(result, dict) else result
        elif status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Form not found",
            )
        elif status_code == 403:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to form",
            )
        else:
            raise HTTPException(status_code=status_code, detail=str(result))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing form startup: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute form startup",
        )


@router.post(
    "/{form_id}/execute",
    response_model=WorkflowExecutionResponse,
    summary="Execute a form",
    description="Execute a form and run the linked workflow",
)
async def execute_form(
    form_id: UUID,
    request: FormExecuteRequest,
    ctx: Context,
) -> WorkflowExecutionResponse:
    """Execute a form and run linked workflow."""
    from shared.handlers.forms_handlers import execute_form_handler
    from shared.context import ExecutionContext as SharedContext

    try:
        shared_ctx = SharedContext(
            user_id=str(ctx.user.user_id),
            name=ctx.user.name,
            email=ctx.user.email,
            is_platform_admin=ctx.user.is_superuser,
            org_id=str(ctx.org_id) if ctx.org_id else None,
        )

        result, status_code = await execute_form_handler(
            str(form_id),
            request.model_dump(mode="json"),
            shared_ctx,
            shared_ctx,
        )

        if status_code == 200:
            # Publish execution update
            if result.get("executionId"):
                await publish_execution_update(
                    execution_id=result["executionId"],
                    status=result.get("status", "Running"),
                )
            return WorkflowExecutionResponse(**result)
        elif status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Form not found",
            )
        elif status_code == 403:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to form",
            )
        else:
            raise HTTPException(status_code=status_code, detail=str(result))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing form: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute form",
        )


@router.get(
    "/{form_id}/roles",
    response_model=RoleFormsResponse,
    summary="Get roles assigned to a form",
    description="Get all roles that have access to this form (Platform admin only)",
)
async def get_form_roles(
    form_id: UUID,
    ctx: Context,
    user: CurrentSuperuser,
) -> RoleFormsResponse:
    """Get roles assigned to form."""
    from shared.handlers.forms_handlers import get_form_roles_handler
    from shared.context import ExecutionContext as SharedContext

    try:
        shared_ctx = SharedContext(
            user_id=str(ctx.user.user_id),
            name=ctx.user.name,
            email=ctx.user.email,
            is_platform_admin=ctx.user.is_superuser,
            org_id=str(ctx.org_id) if ctx.org_id else None,
        )

        result, status_code = await get_form_roles_handler(str(form_id), shared_ctx)

        if status_code == 200:
            return RoleFormsResponse(**result) if isinstance(result, dict) else result
        elif status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Form not found",
            )
        else:
            raise HTTPException(status_code=status_code, detail=str(result))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting form roles: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get form roles",
        )


@router.post(
    "/{form_id}/data-providers/{provider_name}",
    response_model=DataProviderResponse,
    summary="Execute a data provider in the context of a form",
    description="Execute a data provider to retrieve options for form fields",
)
async def execute_form_data_provider(
    form_id: UUID,
    provider_name: str,
    request: DataProviderRequest,
    ctx: Context,
) -> DataProviderResponse:
    """Execute data provider for form."""
    from shared.handlers.forms_handlers import execute_form_data_provider_handler
    from shared.context import ExecutionContext as SharedContext

    try:
        shared_ctx = SharedContext(
            user_id=str(ctx.user.user_id),
            name=ctx.user.name,
            email=ctx.user.email,
            is_platform_admin=ctx.user.is_superuser,
            org_id=str(ctx.org_id) if ctx.org_id else None,
        )

        result, status_code = await execute_form_data_provider_handler(
            form_id=str(form_id),
            provider_name=provider_name,
            request_context=shared_ctx,
            workflow_context=shared_ctx,
            no_cache=request.noCache if hasattr(request, "noCache") else False,
            inputs=request.inputs if hasattr(request, "inputs") else None,
        )

        if status_code == 200:
            return DataProviderResponse(**result) if isinstance(result, dict) else result
        elif status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Form or data provider not found",
            )
        elif status_code == 403:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to form",
            )
        else:
            raise HTTPException(status_code=status_code, detail=str(result))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing data provider: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute data provider",
        )
