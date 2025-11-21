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
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
    WorkflowMetadata,
    WorkflowValidationRequest,
    WorkflowValidationResponse
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
    description="Returns metadata for all registered workflows in the system. Triggers workspace re-scan to pick up new workflows.",
    tags=["Workflows"],
    response_model=list[WorkflowMetadata]
)
@with_request_context
async def list_workflows(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/workflows
    Return metadata for all registered workflows

    Requires authentication (uses request context from SWA/EasyAuth)
    Triggers workspace re-scan to discover new workflows before returning metadata.

    Returns:
        200: List of WorkflowMetadata
        500: Internal server error
    """
    try:
        # Re-scan workspace to pick up new workflows
        from function_app import discover_workspace_modules
        logger.info("Triggering workspace re-scan before returning workflows")
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
