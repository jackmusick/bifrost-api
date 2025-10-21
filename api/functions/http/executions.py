"""
Workflow Executions API endpoints

Provides access to workflow execution history with filtering capabilities.
"""

import json
import logging
from datetime import datetime

import azure.functions as func

from shared.decorators import with_request_context
from shared.handlers.executions_handlers import get_execution_handler, list_executions_handler
from shared.models import WorkflowExecution
from shared.openapi_decorators import openapi_endpoint

logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

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
            "description": "Maximum number of results (default: 25, max: 1000)",
            "schema": {"type": "integer", "minimum": 1, "maximum": 1000},
            "required": False
        },
        "continuationToken": {
            "description": "Continuation token from previous page for pagination",
            "schema": {"type": "string"},
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
    - limit: Max results (optional, default 25, max 1000)

    Returns: List of workflow executions (filtered by user permissions)
    - Platform admins: All executions in their org scope
    - Regular users: Only THEIR executions
    """
    try:
        context = req.context  # type: ignore[attr-defined]

        # Get query parameters
        workflow_name = req.params.get('workflowName')
        status = req.params.get('status')
        limit = int(req.params.get('limit', '25'))
        continuation_token = req.params.get('continuationToken')

        # Call handler to list executions (now returns continuation token)
        executions, next_token = await list_executions_handler(
            context, workflow_name, status, limit, continuation_token
        )

        # Return paginated response
        response = {
            'executions': executions,
            'continuationToken': next_token,
            'hasMore': next_token is not None
        }

        return func.HttpResponse(
            json.dumps(response, cls=DateTimeEncoder),
            status_code=200,
            mimetype='application/json'
        )

    except Exception as e:
        # Avoid logging exception details that might have None values causing sanitizer issues
        error_type = type(e).__name__
        error_msg = str(e) if e else "Unknown error"
        logger.error(
            f"Error listing executions: {error_type}",
            extra={"error_type": error_type, "has_message": bool(error_msg)}
        )
        return func.HttpResponse(
            json.dumps({
                'error': 'InternalServerError',
                'message': error_msg
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
            json.dumps(execution, cls=DateTimeEncoder),
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
