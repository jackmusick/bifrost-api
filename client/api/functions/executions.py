"""
Workflow Executions API endpoints

Provides access to workflow execution history with filtering capabilities.
"""

import json
import azure.functions as func
from typing import Optional, List
from datetime import datetime

from shared.auth import require_auth
from shared.storage import TableStorageService
from shared.models import WorkflowExecution, ExecutionStatus

# Create blueprint for executions endpoints
bp = func.Blueprint()


@bp.function_name("executions_list")
@bp.route(route="executions", methods=["GET"])
@require_auth
def list_executions(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/executions

    Query parameters:
    - orgId: Filter by organization (required)
    - workflowName: Filter by workflow name (optional)
    - status: Filter by status (optional)
    - limit: Max results (optional, default 50, max 1000)
    - continuationToken: Pagination token (optional)

    Returns: List of workflow executions with optional continuation token
    """
    try:
        # Get user from auth middleware
        user = req.user

        # Get query parameters
        org_id = req.params.get('orgId')
        workflow_name = req.params.get('workflowName')
        status = req.params.get('status')
        limit = int(req.params.get('limit', '50'))
        continuation_token = req.params.get('continuationToken')

        # Cap limit at 1000 to prevent abuse
        limit = min(limit, 1000)

        if not org_id:
            return func.HttpResponse(
                json.dumps({
                    'error': 'BadRequest',
                    'message': 'orgId query parameter is required'
                }),
                status_code=400,
                mimetype='application/json'
            )

        # TODO: Validate user has permission to view org executions
        # For now, allow all authenticated users

        # Query WorkflowExecutions table
        executions_service = TableStorageService('WorkflowExecutions')

        # Build filter query
        filter_parts = [f"PartitionKey eq '{org_id}'"]

        if workflow_name:
            filter_parts.append(f"WorkflowName eq '{workflow_name}'")

        if status:
            # Map frontend status to backend status
            status_map = {
                'pending': 'Pending',
                'running': 'Running',
                'completed': 'Success',
                'failed': 'Failed'
            }
            backend_status = status_map.get(status.lower(), status)
            filter_parts.append(f"Status eq '{backend_status}'")

        filter_query = ' and '.join(filter_parts)

        # Use projection to only fetch needed fields (skip large JSON blobs)
        select_fields = [
            'ExecutionId', 'WorkflowName', 'Status', 'ExecutedBy',
            'StartedAt', 'CompletedAt', 'FormId', 'DurationMs', 'ErrorMessage'
        ]

        # Query with server-side pagination
        query_result = executions_service.table_client.query_entities(
            query_filter=filter_query,
            select=select_fields,
            results_per_page=limit
        )

        # Get the first page
        page_iterator = query_result.by_page(continuation_token=continuation_token)
        page = next(page_iterator)

        # Convert to response format (match WorkflowExecution Pydantic model)
        executions = []
        for entity in page:
            execution = {
                'executionId': entity.get('ExecutionId'),
                'workflowName': entity.get('WorkflowName'),
                'status': _map_status_to_frontend(entity.get('Status')),
                'errorMessage': entity.get('ErrorMessage'),
                'executedBy': entity.get('ExecutedBy'),
                'startedAt': entity.get('StartedAt').isoformat() if entity.get('StartedAt') else None,
                'completedAt': entity.get('CompletedAt').isoformat() if entity.get('CompletedAt') else None,
                'formId': entity.get('FormId'),
                'durationMs': entity.get('DurationMs')
            }
            executions.append(execution)

        # Get continuation token for next page
        next_token = page_iterator.continuation_token

        # Build response with pagination info
        response_data = {
            'executions': executions,
            'continuationToken': next_token
        }

        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            mimetype='application/json'
        )

    except Exception as e:
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
@require_auth
def get_execution(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/executions/{executionId}

    Query parameters:
    - orgId: Organization ID (required)

    Returns: Single workflow execution details
    """
    try:
        # Get user from auth middleware
        user = req.user

        # Get execution ID from route
        execution_id = req.route_params.get('executionId')

        # Get org ID from query params
        org_id = req.params.get('orgId')

        if not org_id:
            return func.HttpResponse(
                json.dumps({
                    'error': 'BadRequest',
                    'message': 'orgId query parameter is required'
                }),
                status_code=400,
                mimetype='application/json'
            )

        # TODO: Validate user has permission to view org executions

        # Query WorkflowExecutions table
        executions_service = TableStorageService('WorkflowExecutions')

        # Find the execution by ExecutionId (need to scan since it's not in PartitionKey/RowKey directly)
        filter_query = f"PartitionKey eq '{org_id}' and ExecutionId eq '{execution_id}'"
        entities = list(executions_service.query_entities(filter_query))

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

        # Convert to response format (match WorkflowExecution Pydantic model + logs)
        execution = {
            'executionId': entity.get('ExecutionId'),
            'workflowName': entity.get('WorkflowName'),
            'status': _map_status_to_frontend(entity.get('Status')),
            'inputData': json.loads(entity.get('InputData', '{}')),
            'result': json.loads(entity.get('Result')) if entity.get('Result') else None,
            'errorMessage': entity.get('ErrorMessage'),
            'executedBy': entity.get('ExecutedBy'),
            'startedAt': entity.get('StartedAt').isoformat() if entity.get('StartedAt') else None,
            'completedAt': entity.get('CompletedAt').isoformat() if entity.get('CompletedAt') else None,
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
