"""
Executions Handlers
Business logic for execution queries and filtering
Extracted from functions/executions.py for unit testability
"""

import logging
from typing import Any

from shared.authorization import can_user_view_execution, get_user_executions
from shared.blob_storage import get_blob_service
from shared.repositories.executions import ExecutionRepository
from shared.request_context import RequestContext

logger = logging.getLogger(__name__)


# ============================================================================
# Status Mapping
# ============================================================================


def map_frontend_status_to_backend(frontend_status: str) -> str:
    """
    Map frontend status filter to backend execution status.

    Args:
        frontend_status: Frontend status string (lowercase)

    Returns:
        Backend status string (capitalized)
    """
    status_map = {
        'pending': 'Pending',
        'running': 'Running',
        'completed': 'Success',
        'completedwitherrors': 'CompletedWithErrors',
        'failed': 'Failed'
    }
    return status_map.get(frontend_status.lower(), frontend_status)


def map_status_to_frontend(backend_status: str) -> str:
    """
    Map backend status to frontend status format (keep as-is for consistency).

    Args:
        backend_status: Backend status string

    Returns:
        Frontend status string (unchanged - Pydantic models use capitalized values)
    """
    # Return as-is since Pydantic models use capitalized values
    # No mapping needed - keep backend format
    return backend_status


def determine_result_type(result: Any) -> str | None:
    """
    Determine result type for frontend rendering.

    Args:
        result: Result data (dict, str, or None)

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


# ============================================================================
# Private Helper Functions
# ============================================================================


def _to_iso_string(value: Any) -> str | None:
    """
    Convert datetime or string to ISO format string.

    Args:
        value: Datetime, string, or None

    Returns:
        ISO-formatted string or None
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value  # Already a string
    return value.isoformat()  # Convert datetime to string


def _format_execution_response(model_dict: dict) -> dict:
    """
    Format execution model dict to API response format.

    Handles field mapping and datetime serialization.

    Args:
        model_dict: Execution model dict (with camelCase fields from model_dump)

    Returns:
        Formatted execution dict for API response
    """
    # Ensure critical fields have safe defaults
    status = model_dict.get('status')
    if status is None:
        status = 'Unknown'

    return {
        'executionId': model_dict.get('executionId') or '',
        'workflowName': model_dict.get('workflowName') or 'Unknown',
        'orgId': model_dict.get('orgId'),
        'status': map_status_to_frontend(status),
        'errorMessage': model_dict.get('errorMessage'),
        'executedBy': model_dict.get('executedBy') or '',
        'executedByName': model_dict.get('executedByName') or model_dict.get('executedBy') or 'Unknown',
        'startedAt': _to_iso_string(model_dict.get('startedAt')),
        'completedAt': _to_iso_string(model_dict.get('completedAt')),
        'formId': model_dict.get('formId'),
        'durationMs': model_dict.get('durationMs')
    }


# ============================================================================
# Public Handler Functions
# ============================================================================


def filter_executions_by_workflow(executions: list[dict], workflow_name: str | None) -> list[dict]:
    """
    Filter executions by workflow name.

    Args:
        executions: List of execution dicts
        workflow_name: Workflow name to filter by (or None for no filter)

    Returns:
        Filtered list of execution dicts
    """
    if not workflow_name:
        return executions
    return [e for e in executions if e.get('workflowName') == workflow_name]


def filter_executions_by_status(executions: list[dict], status: str | None) -> list[dict]:
    """
    Filter executions by status.

    Args:
        executions: List of execution dicts
        status: Status to filter by (or None for no filter)

    Returns:
        Filtered list of execution dicts
    """
    if not status:
        return executions

    backend_status = map_frontend_status_to_backend(status)
    return [e for e in executions if e.get('status') == backend_status]


def apply_limit(executions: list[dict], limit: int) -> list[dict]:
    """
    Apply limit to executions list.

    Args:
        executions: List of execution dicts
        limit: Maximum number of executions to return

    Returns:
        Limited list of execution dicts
    """
    return executions[:limit]


async def list_executions_handler(
    context: RequestContext,
    workflow_name: str | None = None,
    status: str | None = None,
    limit: int = 50,
    continuation_token: str | None = None
) -> tuple[list[dict], str | None]:
    """
    List workflow executions with filtering, authorization, and pagination.

    Rules:
    - Platform admins: see all executions in their scope
    - Regular users: see only their own executions

    Args:
        context: RequestContext
        workflow_name: Optional filter by workflow name
        status: Optional filter by status
        limit: Maximum number of results (default 50, max 1000)
        continuation_token: Opaque continuation token from previous page

    Returns:
        Tuple of (list of formatted execution dicts, next continuation token)

    Raises:
        Exception: Any errors during execution retrieval
    """
    import base64
    import json

    # Cap limit at 1000 to prevent abuse
    limit = min(limit, 1000)

    # Decode continuation token if provided
    decoded_token = None
    if continuation_token:
        try:
            decoded_token = json.loads(base64.b64decode(continuation_token).decode('utf-8'))
        except Exception:
            logger.warning(f"Invalid continuation token provided, ignoring")
            decoded_token = None

    # Get repository
    execution_repo = ExecutionRepository(context)

    # Platform admins see all in scope, regular users see only theirs
    if context.is_platform_admin:
        executions, next_token = execution_repo.list_executions_paged(
            org_id=context.scope,
            results_per_page=limit,
            continuation_token=decoded_token
        )
    else:
        executions, next_token = execution_repo.list_executions_by_user_paged(
            user_id=context.user_id,
            results_per_page=limit,
            continuation_token=decoded_token
        )

    # Convert to dicts
    executions_list = [e.model_dump(mode="json") for e in executions]

    # Apply filters (TODO: Push filters down to query level for better performance)
    executions_list = filter_executions_by_workflow(executions_list, workflow_name)
    executions_list = filter_executions_by_status(executions_list, status)

    # Format for response
    formatted = [_format_execution_response(e) for e in executions_list]

    # Encode next token for client
    encoded_token = None
    if next_token:
        encoded_token = base64.b64encode(json.dumps(next_token).encode('utf-8')).decode('utf-8')

    logger.info(f"Returning {len(formatted)} executions for user {context.user_id}, has_more={next_token is not None}")
    return formatted, encoded_token


async def get_execution_handler(
    context: RequestContext,
    execution_id: str
) -> tuple[dict | None, str | None]:
    """
    Get execution details with authorization and blob data.

    Rules:
    - Platform admins: can view any execution in their scope
    - Regular users: can only view their own executions

    Args:
        context: RequestContext
        execution_id: Execution ID (UUID)

    Returns:
        Tuple of (execution_dict, error_message)
        - If successful: (execution_dict, None)
        - If execution not found: (None, "NotFound")
        - If permission denied: (None, "Forbidden")
        - If invalid ID: (None, "BadRequest")

    Raises:
        Exception: Any errors during execution retrieval (caller should handle)
    """
    if not execution_id:
        return None, "BadRequest"

    # Get execution using repository
    exec_repo = ExecutionRepository(context)
    execution_model = exec_repo.get_execution(execution_id)

    if not execution_model:
        return None, "NotFound"

    # Convert to entity dict for authorization check
    entity = execution_model.model_dump()

    # Check if user has permission to view this execution
    if not can_user_view_execution(context, entity):
        logger.warning(f"User {context.user_id} denied access to execution {execution_id}")
        return None, "Forbidden"

    # Fetch logs from blob storage
    blob_service = get_blob_service()
    logs = blob_service.get_logs(execution_id)

    # Fetch result (from blob if no inline result, otherwise use inline)
    result = None
    result_type = None

    if execution_model.result:
        # Result is inline
        result = execution_model.result
        result_type = determine_result_type(result)
    else:
        # Try to fetch from blob storage (result may be there if it was large)
        blob_result = blob_service.get_result(execution_id)
        if blob_result is not None:
            result = blob_result
            result_type = determine_result_type(result)

    # Build response from model (with additional blob data)
    # Use mode='json' to serialize datetime objects to ISO strings
    execution = execution_model.model_dump(mode='json')
    execution['logs'] = logs
    execution['result'] = result
    execution['resultType'] = result_type

    return execution, None
