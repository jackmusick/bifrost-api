"""
Workflow Executions API endpoints

Provides access to workflow execution history with filtering capabilities.
"""

import json
import logging
import azure.functions as func
from typing import Optional, List
from datetime import datetime

from shared.decorators import with_request_context
from shared.authorization import can_user_view_execution, get_user_executions
from shared.storage import get_table_service
from shared.models import WorkflowExecution, ExecutionStatus

logger = logging.getLogger(__name__)

# Create blueprint for executions endpoints
bp = func.Blueprint()


@bp.function_name("executions_list")
@bp.route(route="executions", methods=["GET"])
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
        context = req.context

        # Get query parameters
        workflow_name = req.params.get('workflowName')
        status = req.params.get('status')
        limit = int(req.params.get('limit', '50'))

        # Cap limit at 1000 to prevent abuse
        limit = min(limit, 1000)

        # Use authorization helper to get executions user can view
        executions_list = get_user_executions(context, limit=limit)

        # Apply additional filters if specified
        if workflow_name:
            executions_list = [e for e in executions_list if e.get('WorkflowName') == workflow_name]

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
            executions_list = [e for e in executions_list if e.get('Status') == backend_status]

        # Apply limit
        executions_list = executions_list[:limit]

        # Convert to response format (match WorkflowExecution Pydantic model)
        executions = []
        for entity in executions_list:
            # Helper to convert datetime field to ISO string
            def to_iso(value):
                if value is None:
                    return None
                if isinstance(value, str):
                    return value  # Already a string
                return value.isoformat()  # Convert datetime to string

            # Extract execution ID from RowKey "execution:reverse_ts_uuid"
            row_key_parts = entity['RowKey'].split(':', 1)
            if len(row_key_parts) > 1:
                execution_id = entity.get('ExecutionId', row_key_parts[1])
            else:
                execution_id = entity.get('ExecutionId')

            execution = {
                'executionId': execution_id,
                'workflowName': entity.get('WorkflowName'),
                'orgId': entity.get('PartitionKey'),  # Include org scope for UI display
                'status': _map_status_to_frontend(entity.get('Status')),
                'errorMessage': entity.get('ErrorMessage'),
                'executedBy': entity.get('ExecutedBy'),
                'startedAt': to_iso(entity.get('StartedAt')),
                'completedAt': to_iso(entity.get('CompletedAt')),
                'formId': entity.get('FormId'),
                'durationMs': entity.get('DurationMs')
            }
            executions.append(execution)

        logger.info(f"Returning {len(executions)} executions for user {context.user_id}")

        # Build response
        response_data = {
            'executions': executions
        }

        return func.HttpResponse(
            json.dumps(response_data),
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
@with_request_context
async def get_execution(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/executions/{executionId}

    Returns: Single workflow execution details (with authorization check)
    - Platform admins: Can view any execution in their scope
    - Regular users: Can only view THEIR executions
    """
    try:
        context = req.context

        # Get execution ID from route
        execution_id = req.route_params.get('executionId')

        # Query Entities table for execution
        entities_service = get_table_service('Entities', context)

        # Find the execution by ExecutionId field (stored in entity)
        filter_query = f"ExecutionId eq '{execution_id}'"
        entities = list(entities_service.query_entities(filter_query))

        if not entities:
            return func.HttpResponse(
                json.dumps({
                    'error': 'NotFound',
                    'message': f'Execution {execution_id} not found'
                }),
                status_code=404,
                mimetype='application/json'
            )

        entity = entities[0]

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

        # Helper to convert datetime field to ISO string
        def to_iso(value):
            if value is None:
                return None
            if isinstance(value, str):
                return value  # Already a string
            return value.isoformat()  # Convert datetime to string

        # Convert to response format (match WorkflowExecution Pydantic model + logs)
        execution = {
            'executionId': entity.get('ExecutionId'),
            'workflowName': entity.get('WorkflowName'),
            'orgId': entity.get('PartitionKey'),  # Include org scope for UI display
            'status': _map_status_to_frontend(entity.get('Status')),
            'inputData': json.loads(entity.get('InputData', '{}')),
            'result': json.loads(entity.get('Result')) if entity.get('Result') else None,
            'errorMessage': entity.get('ErrorMessage'),
            'executedBy': entity.get('ExecutedBy'),
            'startedAt': to_iso(entity.get('StartedAt')),
            'completedAt': to_iso(entity.get('CompletedAt')),
            'formId': entity.get('FormId'),
            'durationMs': entity.get('DurationMs'),
            'logs': json.loads(entity.get('Logs')) if entity.get('Logs') else []
        }

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
