"""
Workflow Executions API endpoints

Provides access to workflow execution history with filtering capabilities.
"""

import json
import logging
import azure.functions as func
from typing import Optional, List
from datetime import datetime

from shared.auth import require_auth
from shared.storage import TableStorageService
from shared.models import WorkflowExecution, ExecutionStatus
from shared.auth_headers import get_scope_context

logger = logging.getLogger(__name__)

# Create blueprint for executions endpoints
bp = func.Blueprint()


@bp.function_name("executions_list")
@bp.route(route="executions", methods=["GET"])
@require_auth
def list_executions(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/executions

    Headers:
    - X-Organization-Id: Organization ID (optional, defaults to GLOBAL for admins)

    Query parameters:
    - workflowName: Filter by workflow name (optional)
    - status: Filter by status (optional)
    - limit: Max results (optional, default 50, max 1000)
    - continuationToken: Pagination token (optional)
    - showAll: If "true", platform admins see executions across ALL orgs (optional, admin-only)

    Returns: List of workflow executions with optional continuation token
    """
    try:
        # Get scope context - platform admins can have org_id=None for GLOBAL scope
        org_id, user_id, error = get_scope_context(req)
        if error:
            return error

        # Get query parameters
        workflow_name = req.params.get('workflowName')
        status = req.params.get('status')
        limit = int(req.params.get('limit', '50'))
        continuation_token = req.params.get('continuationToken')
        show_all = req.params.get('showAll', '').lower() == 'true'

        # Cap limit at 1000 to prevent abuse
        limit = min(limit, 1000)

        # Check if user is platform admin for showAll functionality
        from shared.auth import get_authenticated_user, is_platform_admin
        user = get_authenticated_user(req)
        user_is_admin = is_platform_admin(user.user_id) if user else False

        # Security: Only platform admins can use showAll
        if show_all and not user_is_admin:
            return func.HttpResponse(
                json.dumps({
                    'error': 'Forbidden',
                    'message': 'Only platform administrators can view executions across all organizations'
                }),
                status_code=403,
                mimetype='application/json'
            )

        # Query WorkflowExecutions table
        executions_service = TableStorageService('WorkflowExecutions')

        # Build filter query
        filter_parts = []

        # Partition filtering: showAll admins query across all partitions
        if show_all and user_is_admin:
            # No PartitionKey filter - query all orgs
            logger.info(f"PlatformAdmin {user.user_id} querying executions across ALL organizations")
        else:
            # Standard scoped query - use "GLOBAL" partition for None org_id
            partition_key = org_id or "GLOBAL"
            filter_parts.append(f"PartitionKey eq '{partition_key}'")
            logger.info(f"User {user.user_id} querying executions for partition: {partition_key}")

        if workflow_name:
            filter_parts.append(f"WorkflowName eq '{workflow_name}'")

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
            filter_parts.append(f"Status eq '{backend_status}'")

        filter_query = ' and '.join(filter_parts) if filter_parts else None

        # Use projection to only fetch needed fields (skip large JSON blobs)
        # Include PartitionKey to show org scope in UI
        select_fields = [
            'PartitionKey', 'ExecutionId', 'WorkflowName', 'Status', 'ExecutedBy',
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
            # Helper to convert datetime field to ISO string
            def to_iso(value):
                if value is None:
                    return None
                if isinstance(value, str):
                    return value  # Already a string
                return value.isoformat()  # Convert datetime to string

            execution = {
                'executionId': entity.get('ExecutionId'),
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

    Headers:
    - X-Organization-Id: Organization ID (optional, defaults to GLOBAL)

    Returns: Single workflow execution details
    """
    try:
        # Get scope context - platform admins can have org_id=None for GLOBAL scope
        org_id, user_id, error = get_scope_context(req)
        if error:
            return error

        # Get execution ID from route
        execution_id = req.route_params.get('executionId')

        # TODO: Validate user has permission to view org executions

        # Query WorkflowExecutions table
        executions_service = TableStorageService('WorkflowExecutions')

        # Find the execution by ExecutionId - use "GLOBAL" partition for None org_id
        partition_key = org_id or "GLOBAL"
        filter_query = f"PartitionKey eq '{partition_key}' and ExecutionId eq '{execution_id}'"
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
