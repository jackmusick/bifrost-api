"""
Workflow Executions API endpoints

Provides access to workflow execution history with filtering capabilities.
"""

import json
import logging

import azure.functions as func

from shared.authorization import can_user_view_execution, get_user_executions
from shared.blob_storage import get_blob_service
from shared.decorators import with_request_context
from shared.models import WorkflowExecution
from shared.openapi_decorators import openapi_endpoint
from shared.repositories.executions import ExecutionRepository

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

        # Cap limit at 1000 to prevent abuse
        limit = min(limit, 1000)

        # Use authorization helper to get executions user can view
        executions_list = get_user_executions(context, limit=limit)

        # Apply additional filters if specified
        # Note: executions_list contains WorkflowExecution model dicts (camelCase fields)
        if workflow_name:
            executions_list = [e for e in executions_list if e.get('workflowName') == workflow_name]

        if status:
            # Map frontend status to backend status
            status_map = {
                'pending': 'Pending',
                'running': 'Running',
                'completed': 'Success',
                'completedwitherrors': 'CompletedWithErrors',
                'failed': 'Failed'
            }
            backend_status = status_map.get(status.lower(), status)
            executions_list = [e for e in executions_list if e.get('status') == backend_status]

        # Apply limit
        executions_list = executions_list[:limit]

        # Convert to response format (match WorkflowExecution Pydantic model)
        # Note: executions_list contains WorkflowExecution model dicts from get_user_executions()
        executions = []
        for model_dict in executions_list:
            # Helper to convert datetime field to ISO string
            def to_iso(value):
                if value is None:
                    return None
                if isinstance(value, str):
                    return value  # Already a string
                return value.isoformat()  # Convert datetime to string

            # Use model fields directly (model_dump output)
            execution = {
                'executionId': model_dict.get('executionId'),
                'workflowName': model_dict.get('workflowName'),
                'orgId': model_dict.get('orgId'),  # Already included in model
                'status': _map_status_to_frontend(model_dict.get('status') or ''),
                'errorMessage': model_dict.get('errorMessage'),
                'executedBy': model_dict.get('executedBy'),
                'executedByName': model_dict.get('executedByName', model_dict.get('executedBy')),  # Fallback to ID if name not set
                'startedAt': to_iso(model_dict.get('startedAt')),
                'completedAt': to_iso(model_dict.get('completedAt')),
                'formId': model_dict.get('formId'),
                'durationMs': model_dict.get('durationMs')
            }
            executions.append(execution)

        logger.info(f"Returning {len(executions)} executions for user {context.user_id}")

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

        # Validate execution_id is not None
        if not execution_id:
            return func.HttpResponse(
                json.dumps({
                    'error': 'BadRequest',
                    'message': 'Execution ID is required'
                }),
                status_code=400,
                mimetype='application/json'
            )

        # Get execution using repository
        exec_repo = ExecutionRepository(context)
        execution_model = exec_repo.get_execution(execution_id)

        if not execution_model:
            return func.HttpResponse(
                json.dumps({
                    'error': 'NotFound',
                    'message': f'Execution {execution_id} not found'
                }),
                status_code=404,
                mimetype='application/json'
            )

        # Convert to entity dict for authorization check (for backward compatibility)
        entity = execution_model.model_dump()

        # Check if user has permission to view this execution
        if not can_user_view_execution(context, entity):
            logger.warning(f"User {context.user_id} denied access to execution {execution_id}")
            return func.HttpResponse(
                json.dumps({
                    'error': 'Forbidden',
                    'message': 'You do not have permission to view this execution'
                }),
                status_code=403,
                mimetype='application/json'
            )

        # Fetch logs from blob storage
        blob_service = get_blob_service()
        execution_id_str = execution_id if execution_id else ""
        logs = blob_service.get_logs(execution_id_str)

        # Fetch result (from blob if no inline result, otherwise use inline)
        result = None
        result_type = None

        if execution_model.result:
            # Result is inline
            result = execution_model.result
            result_type = _determine_result_type(result)
        else:
            # Try to fetch from blob storage (result may be there if it was large)
            # This handles both the ResultInBlob flag and cases where result is just missing
            blob_result = blob_service.get_result(execution_id_str)
            if blob_result is not None:
                result = blob_result
                result_type = _determine_result_type(result)

        # Build response from model (with additional blob data)
        # Use mode='json' to serialize datetime objects to ISO strings
        execution = execution_model.model_dump(mode='json')
        execution['logs'] = logs
        execution['result'] = result
        execution['resultType'] = result_type

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


def _map_status_to_frontend(backend_status: str) -> str:
    """Map backend status to frontend status format (keep as-is for consistency with Pydantic)"""
    # Return as-is since Pydantic models use capitalized values
    # No mapping needed - keep backend format
    return backend_status


def _determine_result_type(result) -> str | None:
    """
    Determine result type for frontend rendering

    Args:
        result: Result data (dict or str)

    Returns:
        'json', 'html', 'text', or None
    """
    if result is None:
        return None

    if isinstance(result, dict):
        return 'json'

    if isinstance(result, str):
        # Check if it looks like HTML
        trimmed = result.strip()
        if trimmed.startswith('<') and '>' in trimmed:
            return 'html'
        return 'text'

    # Default to json for other types
    return 'json'
