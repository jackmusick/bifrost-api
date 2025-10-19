"""
Workflow Executions API endpoints

Provides access to workflow execution history with filtering capabilities.
"""

import json
import logging

import azure.functions as func

from shared.decorators import with_request_context
from shared.handlers.executions_handlers import get_execution_handler, list_executions_handler
from shared.models import WorkflowExecution
from shared.openapi_decorators import openapi_endpoint

logger = logging.getLogger(__name__)

# Create blueprint for executions endpoints
bp = func.Blueprint()


@bp.function_name("executions_list")
@bp.route(route="executions", methods=["GET"])
@openapi_endpoint(
    path="/executions",
    method="GET",
    summary="List workflow executions",
    description="List workflow executions with filtering. Platform admins see all executions in their org scope. Regular users see only their own executions.",
    tags=["Executions"],
    response_model=list[WorkflowExecution],
    query_params={
        "workflowName": {
            "description": "Filter by workflow name",
            "schema": {"type": "string"},
            "required": False
        },
        "status": {
            "description": "Filter by execution status",
            "schema": {"type": "string", "enum": ["Pending", "Running", "Success", "Failed", "CompletedWithErrors"]},
            "required": False
        },
        "limit": {
            "description": "Maximum number of results (default: 50, max: 1000)",
            "schema": {"type": "integer", "minimum": 1, "maximum": 1000},
            "required": False
        }
    }
)
@with_request_context
async def list_executions(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/executions

    Query parameters:
    - workflowName: Filter by workflow name (optional)
    - status: Filter by status (optional)
    - limit: Max results (optional, default 50, max 1000)

    Returns: List of workflow executions (filtered by user permissions)
    - Platform admins: All executions in their org scope
    - Regular users: Only THEIR executions
    """
    try:
        context = req.context  # type: ignore[attr-defined]

        # Get query parameters
        workflow_name = req.params.get('workflowName')
        status = req.params.get('status')
        limit = int(req.params.get('limit', '50'))

        # Call handler to list executions
        executions = await list_executions_handler(context, workflow_name, status, limit)

        return func.HttpResponse(
            json.dumps(executions),
            status_code=200,
            mimetype='application/json'
        )

    except Exception as e:
        logger.error(f"Error listing executions: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'error': 'InternalServerError',
                'message': str(e)
            }),
            status_code=500,
            mimetype='application/json'
        )


@bp.function_name("executions_get")
@bp.route(route="executions/{executionId}", methods=["GET"])
@openapi_endpoint(
    path="/executions/{executionId}",
    method="GET",
    summary="Get execution details",
    description="Get detailed information about a specific execution. Platform admins can view any execution in their scope. Regular users can only view their own executions.",
    tags=["Executions"],
    response_model=WorkflowExecution,
    path_params={
        "executionId": {
            "description": "Execution ID (UUID)",
            "schema": {"type": "string", "format": "uuid"}
        }
    }
)
@with_request_context
async def get_execution(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/executions/{executionId}

    Returns: Single workflow execution details (with authorization check)
    - Platform admins: Can view any execution in their scope
    - Regular users: Can only view THEIR executions
    """
    try:
        context = req.context  # type: ignore[attr-defined]

        # Get execution ID from route
        execution_id = req.route_params.get('executionId')

        # Call handler to get execution
        execution, error = await get_execution_handler(context, execution_id or "")

        # Map error codes to HTTP responses
        if error == "BadRequest":
            return func.HttpResponse(
                json.dumps({
                    'error': 'BadRequest',
                    'message': 'Execution ID is required'
                }),
                status_code=400,
                mimetype='application/json'
            )
        elif error == "NotFound":
            return func.HttpResponse(
                json.dumps({
                    'error': 'NotFound',
                    'message': f'Execution {execution_id} not found'
                }),
                status_code=404,
                mimetype='application/json'
            )
        elif error == "Forbidden":
            return func.HttpResponse(
                json.dumps({
                    'error': 'Forbidden',
                    'message': 'You do not have permission to view this execution'
                }),
                status_code=403,
                mimetype='application/json'
            )

        return func.HttpResponse(
            json.dumps(execution),
            status_code=200,
            mimetype='application/json'
        )

    except Exception as e:
        logger.error(f"Error getting execution: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'error': 'InternalServerError',
                'message': str(e)
            }),
            status_code=500,
            mimetype='application/json'
        )
