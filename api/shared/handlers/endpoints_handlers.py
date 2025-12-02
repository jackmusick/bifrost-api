"""
Endpoints Handlers
Business logic for workflow endpoint execution
Extracted from HTTP handlers for unit testability
"""

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import azure.functions as func

from shared.async_executor import enqueue_workflow_execution
from shared.context import ExecutionContext
from shared.discovery import load_workflow, WorkflowMetadata
from shared.error_handling import WorkflowError
from shared.execution_logger import get_execution_logger
from shared.models import ErrorResponse, ExecutionStatus
from shared.workflow_endpoint_utils import (
    coerce_parameter_types,
    record_workflow_execution_result,
    separate_workflow_params,
)

logger = logging.getLogger(__name__)


async def execute_workflow_endpoint_handler(
    context: ExecutionContext,
    workflow_name: str,
    http_method: str,
    input_data: dict[str, Any],
) -> tuple["func.HttpResponse", int]:
    """
    Execute a workflow via HTTP endpoint.

    This is the core business logic for workflow endpoint execution, extracted
    from the HTTP handler for unit testability. It handles:
    1. Workflow lookup and validation
    2. HTTP method validation
    3. Async vs sync execution dispatch
    4. Execution logging and error handling

    Args:
        context: Organization context with auth info
        workflow_name: Name of workflow to execute
        http_method: HTTP method (GET, POST, PUT, DELETE)
        input_data: Merged query parameters and body

    Returns:
        tuple of (HttpResponse, status_code)
    """
    # Dynamically load workflow (always fresh)
    try:
        result = load_workflow(workflow_name)
        if not result:
            logger.warning(f"Workflow not found: {workflow_name}")
            error = ErrorResponse(
                error="NotFound",
                message=f"Workflow '{workflow_name}' not found"
            )
            return (
                func.HttpResponse(
                    json.dumps(error.model_dump()),
                    status_code=404,
                    mimetype="application/json"
                ),
                404
            )
        workflow_func, workflow_metadata = result
    except Exception as e:
        # Load failed (likely syntax error)
        logger.error(f"Failed to load workflow {workflow_name}: {e}", exc_info=True)
        error = ErrorResponse(
            error="WorkflowLoadError",
            message=f"Failed to load workflow '{workflow_name}': {str(e)}"
        )
        return (
            func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=500,
                mimetype="application/json"
            ),
            500
        )

    # Check if endpoint is enabled
    if not workflow_metadata.endpoint_enabled:
        logger.warning(f"Workflow endpoint not enabled: {workflow_name}")
        return (
            func.HttpResponse(
                json.dumps({
                    "error": "NotFound",
                    "message": f"Workflow endpoint '{workflow_name}' is not enabled"
                }),
                status_code=404,
                mimetype="application/json"
            ),
            404
        )

    # Check if HTTP method is allowed
    allowed_methods = workflow_metadata.allowed_methods or ['POST']
    if http_method not in allowed_methods:
        logger.warning(
            f"Method not allowed for workflow endpoint: {workflow_name}",
            extra={
                "workflow_name": workflow_name,
                "method": http_method,
                "allowed_methods": allowed_methods
            }
        )
        return (
            func.HttpResponse(
                json.dumps({
                    "error": "MethodNotAllowed",
                    "message": f"HTTP method {http_method} not allowed for this endpoint. Allowed methods: {', '.join(allowed_methods)}"
                }),
                status_code=405,
                mimetype="application/json"
            ),
            405
        )

    # Check if workflow should execute asynchronously
    if workflow_metadata.execution_mode == "async":
        return await _execute_async(
            context=context,
            workflow_name=workflow_name,
            input_data=input_data
        )

    # Execute synchronously
    return await _execute_sync(
        context=context,
        workflow_name=workflow_name,
        http_method=http_method,
        input_data=input_data,
        workflow_func=workflow_func,
        workflow_metadata=workflow_metadata
    )


async def _execute_async(
    context: ExecutionContext,
    workflow_name: str,
    input_data: dict[str, Any],
) -> tuple["func.HttpResponse", int]:
    """
    Execute workflow asynchronously via queue.

    Args:
        context: Organization context
        workflow_name: Workflow name
        input_data: Input parameters

    Returns:
        tuple of (HttpResponse with execution ID, 202 status)
    """
    # Enqueue for async execution
    # Cast ExecutionContext to match ExecutionContext interface
    # Both have org_id, user_id, name, and email attributes
    execution_id = await enqueue_workflow_execution(
        context=context,  # type: ignore[arg-type]
        workflow_name=workflow_name,
        parameters=input_data,
        form_id=None  # Endpoints don't have form context
    )

    # Return immediately with execution ID and PENDING status (202 Accepted)
    response = func.HttpResponse(
        json.dumps({
            "executionId": execution_id,
            "status": "Pending",
            "message": "Workflow queued for async execution"
        }),
        status_code=202,  # 202 Accepted
        mimetype="application/json"
    )
    return (response, 202)


async def _execute_sync(
    context: ExecutionContext,
    workflow_name: str,
    http_method: str,
    input_data: dict[str, Any],
    workflow_func: Any,
    workflow_metadata: WorkflowMetadata,
) -> tuple["func.HttpResponse", int]:
    """
    Execute workflow synchronously.

    Args:
        context: Organization context
        workflow_name: Workflow name
        http_method: HTTP method (for logging)
        input_data: Input parameters
        workflow_func: The workflow function to execute
        workflow_metadata: Workflow metadata

    Returns:
        tuple of (HttpResponse with execution result, status_code)
    """
    import uuid

    # Generate execution ID
    execution_id = str(uuid.uuid4())

    # Create execution logger
    exec_logger = get_execution_logger()

    # Record execution start
    start_time = datetime.utcnow()

    try:
        # Create execution record (status=RUNNING)
        await exec_logger.create_execution(
            execution_id=execution_id,
            org_id=context.org_id,
            user_id=context.user_id,
            user_name=context.name,
            workflow_name=workflow_name,
            input_data=input_data,
            form_id=None  # Endpoints don't have form context
        )

        logger.info(
            f"Starting workflow endpoint execution: {workflow_name}",
            extra={
                "execution_id": execution_id,
                "org_id": context.org_id,
                "user_id": context.user_id,
                "workflow_name": workflow_name,
                "http_method": http_method
            }
        )

        # Apply type coercion to input data
        param_metadata = {param.name: param for param in workflow_metadata.parameters}
        coerced_data = coerce_parameter_types(input_data, param_metadata)

        # Separate workflow parameters from extra variables
        workflow_params, extra_variables = separate_workflow_params(coerced_data, workflow_metadata)

        # Extra variables are no longer injected into context
        # They will be ignored for endpoint executions (only workflow params are used)

        # Call the workflow function with context as first parameter
        result = await workflow_func(context, **workflow_params)

        # Record successful execution
        response = await record_workflow_execution_result(
            exec_logger=exec_logger,
            execution_id=execution_id,
            context=context,  # type: ignore[arg-type]
            status=ExecutionStatus.SUCCESS,
            start_time=start_time,
            result=result
        )

        logger.info(
            f"Workflow endpoint execution completed: {workflow_name}",
            extra={
                "execution_id": execution_id,
                "status": "Success",
                "duration_ms": response.durationMs
            }
        )

        return (
            func.HttpResponse(
                json.dumps(response.model_dump(mode='json')),
                status_code=200,
                mimetype="application/json"
            ),
            200
        )

    except WorkflowError as e:
        # Expected workflow error - log as warning
        response = await record_workflow_execution_result(
            exec_logger=exec_logger,
            execution_id=execution_id,
            context=context,  # type: ignore[arg-type]
            status=ExecutionStatus.FAILED,
            start_time=start_time,
            error=e
        )

        logger.warning(
            f"Workflow endpoint execution failed: {workflow_name}",
            extra={
                "execution_id": execution_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": response.durationMs
            }
        )

        return (
            func.HttpResponse(
                json.dumps(response.model_dump(mode='json')),
                status_code=200,
                mimetype="application/json"
            ),
            200
        )

    except Exception as e:
        # Unexpected error - log with full traceback
        response = await record_workflow_execution_result(
            exec_logger=exec_logger,
            execution_id=execution_id,
            context=context,  # type: ignore[arg-type]
            status=ExecutionStatus.FAILED,
            start_time=start_time,
            error=e
        )

        logger.error(
            f"Workflow endpoint execution error: {workflow_name}",
            extra={
                "execution_id": execution_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": response.durationMs
            },
            exc_info=True
        )

        return (
            func.HttpResponse(
                json.dumps(response.model_dump(mode='json')),
                status_code=200,
                mimetype="application/json"
            ),
            200
        )


def parse_input_data(req: "func.HttpRequest") -> dict[str, Any]:
    """
    Parse input data from query parameters and JSON body.

    Query parameters + body are merged with body taking precedence.

    Args:
        req: HTTP request

    Returns:
        Merged dict of input data

    Raises:
        ValueError: If input data cannot be parsed
    """
    # Get query params as dict
    query_params = dict(req.params)

    # Get body (if present)
    try:
        body = req.get_json() or {}
    except Exception as e:
        logger.error(f"Failed to parse JSON body: {str(e)}")
        raise ValueError("Invalid JSON body") from e

    # Merge: body takes precedence
    return {**query_params, **body}
