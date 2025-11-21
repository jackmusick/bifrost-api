"""
Workflow Execution API
Handles execution of registered workflows with org context

Business logic extracted to shared/handlers/workflows_handlers.py
"""

import json
import logging

import azure.functions as func

from shared.decorators import require_platform_admin, with_request_context
from shared.handlers.discovery_handlers import convert_registry_workflow_to_model
from shared.handlers.workflows_handlers import execute_workflow_handler, validate_workflow_file
from shared.middleware import with_org_context
from shared.models import (
    FileScanRequest,
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
    WorkflowMetadata,
    WorkflowValidationRequest,
    WorkflowValidationResponse,
    WorkspaceScanResponse,
)
from shared.openapi_decorators import openapi_endpoint
from shared.registry import get_registry

logger = logging.getLogger(__name__)

# Create blueprint for workflow execution endpoints
bp = func.Blueprint()


@bp.route(route="workflows", methods=["GET"])
@bp.function_name("list_workflows")
@openapi_endpoint(
    path="/workflows",
    method="GET",
    summary="List all workflows",
    description="Returns metadata for all registered workflows in the system. Supports full re-scan or incremental reload of a single file via ?reload_file query parameter.",
    tags=["Workflows"],
    response_model=list[WorkflowMetadata],
    query_params={
        "reload_file": {
            "description": "Optional relative workspace path to a single file to reload (incremental discovery). If provided, only that file is reloaded.",
            "schema": {"type": "string"},
            "required": False
        }
    }
)
@with_request_context
async def list_workflows(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/workflows
    Return metadata for all registered workflows

    Query Parameters:
        reload_file: Optional relative path to a single file to reload (e.g., "features/my_workflow.py")
                    If provided, only that file is reloaded. Otherwise, full workspace scan occurs.

    Requires authentication (uses request context from SWA/EasyAuth)
    Triggers workspace re-scan (full or incremental) to discover workflows before returning metadata.

    Returns:
        200: List of WorkflowMetadata
        400: Invalid reload_file path
        500: Internal server error
    """
    try:
        reload_file = req.params.get('reload_file')

        if reload_file:
            # Incremental reload: just reload the specified file
            from pathlib import Path
            from function_app import reload_single_module, get_workspace_paths
            import os

            logger.info(f"Triggering incremental reload for file: {reload_file}")

            # Find the absolute path
            workspace_roots = get_workspace_paths()
            workspace_location = os.environ.get("BIFROST_WORKSPACE_LOCATION")
            if workspace_location:
                workspace_roots.insert(0, workspace_location)

            abs_path = None
            for root in workspace_roots:
                candidate = Path(root) / reload_file
                if candidate.exists():
                    abs_path = candidate
                    break

            if abs_path is None:
                error_response = {
                    "error": "FileNotFound",
                    "message": f"File not found: {reload_file}"
                }
                return func.HttpResponse(
                    json.dumps(error_response),
                    status_code=400,
                    mimetype="application/json"
                )

            # Remove workflow(s) from registry if they exist with this file path
            registry = get_registry()
            abs_path_str = str(abs_path)
            removed_workflows = registry.remove_workflows_by_file_path(abs_path_str)
            if removed_workflows:
                logger.info(f"Removed {len(removed_workflows)} workflow(s) before reload: {', '.join(removed_workflows)}")

            # Reload the file (this will re-register if valid)
            try:
                reload_single_module(abs_path)
                logger.info(f"Successfully reloaded file: {reload_file}")
            except Exception as e:
                logger.warning(f"Failed to reload file {reload_file}: {e}")
                # Continue - file might have syntax errors, registry will reflect removal
        else:
            # Full workspace re-scan
            from function_app import discover_workspace_modules
            logger.info("Triggering full workspace re-scan before returning workflows")
            discover_workspace_modules()

        # Get all workflows from registry
        registry = get_registry()
        workflows = []

        for w in registry.get_all_workflows():
            try:
                workflow_model = convert_registry_workflow_to_model(w)
                workflows.append(workflow_model)
            except Exception as e:
                logger.error(
                    f"Failed to convert workflow '{w.name}': {e}",
                    exc_info=True
                )

        logger.info(f"Returning {len(workflows)} workflows")

        return func.HttpResponse(
            json.dumps([w.model_dump(mode="json", by_alias=True, exclude_none=True) for w in workflows]),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error retrieving workflows: {str(e)}", exc_info=True)

        error_response = {
            "error": "InternalServerError",
            "message": "Failed to retrieve workflows"
        }

        return func.HttpResponse(
            json.dumps(error_response),
            status_code=500,
            mimetype="application/json"
        )


@bp.route(route="workflows/execute", methods=["POST"])
@bp.function_name("execute_workflow")
@openapi_endpoint(
    path="/workflows/execute",
    method="POST",
    summary="Execute a workflow or script",
    description="Execute a workflow by name or inline Python code (Platform admin only)",
    tags=["Workflows"],
    request_model=WorkflowExecutionRequest,
    response_model=WorkflowExecutionResponse,
)
@with_request_context
@with_org_context
@require_platform_admin
async def execute_workflow(req: func.HttpRequest) -> func.HttpResponse:
    """Execute a workflow or script with the provided parameters"""
    return await execute_workflow_handler(req)


@bp.route(route="workflows/validate", methods=["POST"])
@bp.function_name("validate_workflow")
@openapi_endpoint(
    path="/workflows/validate",
    method="POST",
    summary="Validate a workflow file",
    description="Validate a workflow file for syntax errors, decorator issues, and Pydantic validation problems",
    tags=["Workflows"],
    request_model=WorkflowValidationRequest,
    response_model=WorkflowValidationResponse,
)
@with_request_context
async def validate_workflow(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/workflows/validate
    Validate a workflow file for errors

    Request Body:
        {
            "path": "relative/path/to/workflow.py",
            "content": "optional file content to validate"
        }

    Returns:
        200: WorkflowValidationResponse with validation results
        400: Invalid request
        500: Internal server error
    """
    try:
        # Parse request body
        body = req.get_json()
        validation_request = WorkflowValidationRequest(**body)

        # Perform validation
        result = await validate_workflow_file(
            path=validation_request.path,
            content=validation_request.content
        )

        logger.info(f"Validation result for {validation_request.path}: valid={result.valid}, issues={len(result.issues)}")

        return func.HttpResponse(
            json.dumps(result.model_dump(mode="json", by_alias=True, exclude_none=True)),
            status_code=200,
            mimetype="application/json"
        )

    except ValueError as e:
        logger.error(f"Invalid request body: {e}", exc_info=True)
        error_response = {
            "error": "InvalidRequest",
            "message": f"Invalid request body: {str(e)}"
        }
        return func.HttpResponse(
            json.dumps(error_response),
            status_code=400,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error validating workflow: {str(e)}", exc_info=True)
        error_response = {
            "error": "InternalServerError",
            "message": "Failed to validate workflow"
        }
        return func.HttpResponse(
            json.dumps(error_response),
            status_code=500,
            mimetype="application/json"
        )


@bp.route(route="workflows/scan", methods=["POST"])
@bp.function_name("scan_workspace")
@openapi_endpoint(
    path="/workflows/scan",
    method="POST",
    summary="Scan workspace for SDK usage issues",
    description="Scans all Python files in workspace for config.get(), secrets.get(), and oauth.get_token() calls and validates against stored data",
    tags=["Workflows"],
    response_model=WorkspaceScanResponse,
)
@with_request_context
@with_org_context
async def scan_workspace(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/workflows/scan
    Scan entire workspace for missing SDK dependencies

    Returns:
        200: WorkspaceScanResponse with issues found
        500: Internal server error
    """
    import os
    from shared.services.sdk_usage_scanner import SDKUsageScanner

    try:
        context = req.org_context  # type: ignore[attr-defined]
        workspace_path = os.environ.get('BIFROST_WORKSPACE_LOCATION', '/mounts/workspace')

        scanner = SDKUsageScanner(workspace_path)

        # Get count of Python files that will be scanned
        file_usages = scanner.scan_workspace()
        scanned_count = len(file_usages)

        # Validate against stored data
        issues = await scanner.validate_workspace(context)

        response = WorkspaceScanResponse(
            issues=issues,
            scanned_files=scanned_count
        )

        logger.info(f"Workspace scan complete: {scanned_count} files, {len(issues)} issues")

        return func.HttpResponse(
            json.dumps(response.model_dump(mode="json", by_alias=True, exclude_none=True)),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error scanning workspace: {str(e)}", exc_info=True)
        error_response = {
            "error": "InternalServerError",
            "message": "Failed to scan workspace"
        }
        return func.HttpResponse(
            json.dumps(error_response),
            status_code=500,
            mimetype="application/json"
        )


@bp.route(route="workflows/scan/file", methods=["POST"])
@bp.function_name("scan_file")
@openapi_endpoint(
    path="/workflows/scan/file",
    method="POST",
    summary="Scan a single file for SDK usage issues",
    description="Scans a single Python file for config.get(), secrets.get(), and oauth.get_token() calls and validates against stored data",
    tags=["Workflows"],
    request_model=FileScanRequest,
    response_model=WorkspaceScanResponse,
)
@with_request_context
@with_org_context
async def scan_file(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/workflows/scan/file
    Scan a single file for missing SDK dependencies

    Request Body:
        {
            "file_path": "relative/path/to/file.py",
            "content": "optional file content (if not provided, reads from disk)"
        }

    Returns:
        200: WorkspaceScanResponse with issues found
        400: Invalid request
        500: Internal server error
    """
    import os
    from shared.services.sdk_usage_scanner import SDKUsageScanner

    try:
        body = req.get_json()
        scan_request = FileScanRequest(**body)

        context = req.org_context  # type: ignore[attr-defined]
        workspace_path = os.environ.get('BIFROST_WORKSPACE_LOCATION', '/mounts/workspace')

        scanner = SDKUsageScanner(workspace_path)
        issues = await scanner.validate_file(
            file_path=scan_request.file_path,
            context=context,
            content=scan_request.content
        )

        response = WorkspaceScanResponse(
            issues=issues,
            scanned_files=1
        )

        logger.info(f"File scan complete: {scan_request.file_path}, {len(issues)} issues")

        return func.HttpResponse(
            json.dumps(response.model_dump(mode="json", by_alias=True, exclude_none=True)),
            status_code=200,
            mimetype="application/json"
        )

    except ValueError as e:
        logger.error(f"Invalid request body: {e}", exc_info=True)
        error_response = {
            "error": "InvalidRequest",
            "message": f"Invalid request body: {str(e)}"
        }
        return func.HttpResponse(
            json.dumps(error_response),
            status_code=400,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error scanning file: {str(e)}", exc_info=True)
        error_response = {
            "error": "InternalServerError",
            "message": "Failed to scan file"
        }
        return func.HttpResponse(
            json.dumps(error_response),
            status_code=500,
            mimetype="application/json"
        )
