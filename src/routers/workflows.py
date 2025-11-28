"""
Workflows Router

Handles workflow discovery, execution, and validation.
API-compatible with the existing Azure Functions implementation.

Note: This router bridges to existing business logic in shared/ for workflow
discovery and execution since that logic is tightly coupled to file system
scanning and Python execution runtime.
"""

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import ValidationError

# Import existing Pydantic models for API compatibility
from shared.models import (
    FileScanRequest,
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
    WorkflowMetadata,
    WorkflowValidationRequest,
    WorkflowValidationResponse,
    WorkspaceScanRequest,
    WorkspaceScanResponse,
)

from src.core.auth import Context, CurrentActiveUser, CurrentSuperuser
from src.core.database import DbSession
from src.core.pubsub import publish_execution_update

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflows", tags=["Workflows"])


# =============================================================================
# Helper Functions
# =============================================================================


def _convert_workflow_metadata_to_model(workflow_meta) -> WorkflowMetadata:
    """Convert internal workflow metadata to Pydantic model."""
    # Import here to avoid circular imports at module load time
    from shared.handlers.discovery_handlers import convert_workflow_metadata_to_model
    return convert_workflow_metadata_to_model(workflow_meta)


# =============================================================================
# HTTP Endpoints
# =============================================================================


@router.get(
    "",
    response_model=list[WorkflowMetadata],
    summary="List all workflows",
    description="Returns metadata for all registered workflows in the system",
)
async def list_workflows(
    user: CurrentActiveUser,
    reload_file: str | None = Query(None, description="Optional file path to reload"),
) -> list[WorkflowMetadata]:
    """List all registered workflows."""
    # Import shared discovery module
    from shared.discovery import scan_all_workflows

    try:
        workflows = []
        for w in scan_all_workflows():
            try:
                workflow_model = _convert_workflow_metadata_to_model(w)
                workflows.append(workflow_model)
            except Exception as e:
                logger.error(f"Failed to convert workflow '{w.name}': {e}")

        logger.info(f"Returning {len(workflows)} workflows")
        return workflows

    except Exception as e:
        logger.error(f"Error retrieving workflows: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workflows",
        )


@router.post(
    "/execute",
    response_model=WorkflowExecutionResponse,
    summary="Execute a workflow or script",
    description="Execute a workflow by name or inline Python code (Platform admin only)",
)
async def execute_workflow(
    request: WorkflowExecutionRequest,
    ctx: Context,
    user: CurrentSuperuser,  # Platform admin only
) -> WorkflowExecutionResponse:
    """Execute a workflow or script with the provided parameters."""
    # Import shared execution handler
    from shared.handlers.workflows_logic import execute_workflow_logic, execute_code_logic
    from shared.models import ExecutionStatus

    try:
        # Build context for execution
        from shared.context import ExecutionContext as SharedContext

        # Create shared context compatible with existing handlers
        shared_ctx = SharedContext(
            user_id=str(ctx.user.user_id),
            name=ctx.user.name,
            email=ctx.user.email,
            is_platform_admin=ctx.user.is_superuser,
            org_id=str(ctx.org_id) if ctx.org_id else None,
        )

        if request.code:
            # Execute inline code
            result = await execute_code_logic(
                context=shared_ctx,
                code=request.code,
                script_name=request.scriptName or "inline_script",
                input_data=request.inputData,
                transient=request.transient,
            )
        else:
            # Execute named workflow
            if not request.workflowName:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Either workflowName or code must be provided",
                )

            result = await execute_workflow_logic(
                context=shared_ctx,
                workflow_name=request.workflowName,
                input_data=request.inputData,
                form_id=request.formId,
                transient=request.transient,
            )

        # Publish execution update via WebSocket
        if not request.transient and result.executionId:
            await publish_execution_update(
                execution_id=result.executionId,
                status=result.status.value,
                data={
                    "result": result.result,
                    "error": result.error,
                    "durationMs": result.durationMs,
                },
            )

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error executing workflow: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute workflow",
        )


@router.post(
    "/validate",
    response_model=WorkflowValidationResponse,
    summary="Validate a workflow file",
    description="Validate a workflow file for syntax errors and decorator issues",
)
async def validate_workflow(
    request: WorkflowValidationRequest,
    user: CurrentActiveUser,
) -> WorkflowValidationResponse:
    """Validate a workflow file for errors."""
    from shared.handlers.workflows_handlers import validate_workflow_file

    try:
        result = await validate_workflow_file(
            path=request.path,
            content=request.content,
        )

        logger.info(f"Validation result for {request.path}: valid={result.valid}, issues={len(result.issues)}")
        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error validating workflow: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate workflow",
        )


@router.post(
    "/scan",
    response_model=WorkspaceScanResponse,
    summary="Scan workspace for SDK usage issues",
    description="Scans all Python files for SDK usage issues",
)
async def scan_workspace(
    ctx: Context,
    user: CurrentSuperuser,
) -> WorkspaceScanResponse:
    """Scan entire workspace for SDK dependencies and issues."""
    from shared.discovery import scan_all_forms
    from shared.services.sdk_usage_scanner import SDKUsageScanner
    from shared.context import ExecutionContext as SharedContext

    try:
        workspace_path = os.environ.get("BIFROST_WORKSPACE_LOCATION", "/mounts/workspace")

        # Create shared context
        shared_ctx = SharedContext(
            user_id=str(ctx.user.user_id),
            name=ctx.user.name,
            email=ctx.user.email,
            is_platform_admin=ctx.user.is_superuser,
            org_id=str(ctx.org_id) if ctx.org_id else None,
        )

        # Scan for SDK usage issues
        scanner = SDKUsageScanner(workspace_path)
        file_usages = scanner.scan_workspace()
        scanned_count = len(file_usages)
        sdk_issues = await scanner.validate_workspace(shared_ctx)

        # Scan for forms
        forms = scan_all_forms()
        form_count = len(forms)

        response = WorkspaceScanResponse(
            issues=sdk_issues,
            scanned_files=scanned_count,
            form_issues=[],
            scanned_forms=form_count,
            valid_forms=form_count,
        )

        logger.info(
            f"Workspace scan complete: {scanned_count} files/{len(sdk_issues)} SDK issues, "
            f"{form_count} forms scanned"
        )

        return response

    except Exception as e:
        logger.error(f"Error scanning workspace: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to scan workspace",
        )


@router.post(
    "/scan/file",
    response_model=WorkspaceScanResponse,
    summary="Scan a single file for SDK usage issues",
    description="Scans a single Python file for config/secrets/oauth calls",
)
async def scan_file(
    request: FileScanRequest,
    ctx: Context,
    user: CurrentSuperuser,
) -> WorkspaceScanResponse:
    """Scan a single file for SDK dependencies."""
    from shared.services.sdk_usage_scanner import SDKUsageScanner
    from shared.context import ExecutionContext as SharedContext

    try:
        workspace_path = os.environ.get("BIFROST_WORKSPACE_LOCATION", "/mounts/workspace")

        # Create shared context
        shared_ctx = SharedContext(
            user_id=str(ctx.user.user_id),
            name=ctx.user.name,
            email=ctx.user.email,
            is_platform_admin=ctx.user.is_superuser,
            org_id=str(ctx.org_id) if ctx.org_id else None,
        )

        scanner = SDKUsageScanner(workspace_path)
        issues = await scanner.validate_file(
            file_path=request.file_path,
            context=shared_ctx,
            content=request.content,
        )

        response = WorkspaceScanResponse(
            issues=issues,
            scanned_files=1,
        )

        logger.info(f"File scan complete: {request.file_path}, {len(issues)} issues")
        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error scanning file: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to scan file",
        )
