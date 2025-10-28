"""
Workflow Endpoints API
Exposes registered workflows as HTTP endpoints with API key authentication

Thin HTTP handler layer that delegates to shared/handlers/endpoints_handlers.py
"""

import json
import logging

import azure.functions as func

from shared.handlers.endpoints_handlers import (
    execute_workflow_endpoint_handler,
    parse_input_data,
)
from shared.middleware import has_workflow_key
from shared.models import ErrorResponse
from shared.openapi_decorators import openapi_endpoint

logger = logging.getLogger(__name__)

# Create blueprint for workflow endpoints
bp = func.Blueprint()


@bp.route(route="endpoints/{workflowName}", methods=["GET", "POST", "PUT", "DELETE"])
@bp.function_name("execute_workflow_endpoint")
@openapi_endpoint(
    path="/endpoints/{workflowName}",
    method="POST",
    summary="Execute a workflow via HTTP endpoint",
    description="Execute a workflow as an HTTP endpoint using API key authentication",
    tags=["Workflow Endpoints"],
    path_params={
        "workflowName": {
            "description": "Name of the workflow to execute",
            "schema": {"type": "string"},
            "required": True
        }
    }
)
@has_workflow_key
async def execute_workflow_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Execute a workflow via HTTP endpoint using API key authentication.

    Supports GET, POST, PUT, DELETE methods. The allowed methods are determined
    by the workflow's endpoint configuration.

    Authentication:
        - Uses API key from Authorization: Bearer header
        - Can use workflow-specific keys or global keys
        - If workflow has DisableGlobalKey=True, only workflow-specific keys work

    Input parameters:
        - Query parameters (for all methods)
        - JSON body (for POST, PUT)
        - Body parameters take precedence over query parameters with same name

    Response:
        200: Workflow executed successfully
        {
            "executionId": "uuid",
            "status": "Success" | "Failed" | "CompletedWithErrors",
            "result": {...},
            "error": "error message",  // If failed
            "durationMs": 1234,
            "startedAt": "ISO8601",
            "completedAt": "ISO8601"
        }

        400: Bad request (invalid JSON, validation errors)
        401: Unauthorized (invalid or missing API key)
        404: Workflow endpoint not enabled
        405: HTTP method not allowed for this workflow
        500: Server error
    """
    try:
        # Get context from request (injected by @has_workflow_key decorator)
        context = req.org_context  # type: ignore[attr-defined]

        workflow_name = req.route_params.get('workflowName')
        assert workflow_name is not None, "workflowName is required"

        # Get HTTP method
        http_method = req.method.upper()

        # Hot-reload: Re-discover workspace modules (force_reload=True by default)
        from function_app import discover_workspace_modules
        discover_workspace_modules()

    except Exception as e:
        logger.error(f"Pre-execution error: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalError",
            message=f"Failed to initialize workflow execution: {str(e)}"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )

    # Parse input data from query params + body
    try:
        input_data = parse_input_data(req)
    except Exception as e:
        logger.error(f"Failed to parse input data: {str(e)}")
        error = ErrorResponse(
            error="BadRequest",
            message="Invalid input data"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    # Delegate to handler
    response, status_code = await execute_workflow_endpoint_handler(
        context=context,
        workflow_name=workflow_name,
        http_method=http_method,
        input_data=input_data
    )

    return response
