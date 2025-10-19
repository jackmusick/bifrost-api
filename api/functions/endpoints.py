"""
Workflow Endpoints API
Exposes registered workflows as HTTP endpoints with API key authentication
"""

import json
import logging
from datetime import datetime

import azure.functions as func

from shared.error_handling import WorkflowError
from shared.execution_logger import get_execution_logger
from shared.middleware import has_workflow_key
from shared.models import ErrorResponse, ExecutionStatus
from shared.openapi_decorators import openapi_endpoint
from shared.registry import get_registry
from shared.workflow_endpoint_utils import (
    coerce_parameter_types,
    record_workflow_execution_result,
    separate_workflow_params,
)

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

        # Hot-reload: Re-discover workspace modules on every request
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

    # Get workflow from registry
    registry = get_registry()
    workflow_metadata = registry.get_workflow(workflow_name)

    if not workflow_metadata:
        logger.warning(f"Workflow not found: {workflow_name}")
        error = ErrorResponse(
            error="NotFound",
            message=f"Workflow '{workflow_name}' not found"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=404,
            mimetype="application/json"
        )

    # Check if endpoint is enabled
    if not workflow_metadata.endpoint_enabled:
        logger.warning(f"Workflow endpoint not enabled: {workflow_name}")
        return func.HttpResponse(
            json.dumps({
                "error": "NotFound",
                "message": f"Workflow endpoint '{workflow_name}' is not enabled"
            }),
            status_code=404,
            mimetype="application/json"
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
        return func.HttpResponse(
            json.dumps({
                "error": "MethodNotAllowed",
                "message": f"HTTP method {http_method} not allowed for this endpoint. Allowed methods: {', '.join(allowed_methods)}"
            }),
            status_code=405,
            mimetype="application/json"
        )

    # Parse input data from query params + body
    try:
        # Get query params as dict
        query_params = dict(req.params)

        # Get body (if present)
        try:
            body = req.get_json() or {}
        except Exception:
            body = {}

        # Merge: body takes precedence
        input_data = {**query_params, **body}

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

    # Get workflow function
    workflow_func = workflow_metadata.function

    # Generate execution ID
    execution_id = str(__import__('uuid').uuid4())

    # Create execution logger
    exec_logger = get_execution_logger()

    # Record execution start
    start_time = datetime.utcnow()

    try:
        # Create execution record (status=RUNNING)
        await exec_logger.create_execution(
            execution_id=execution_id,
            org_id=context.org_id,
            user_id=context.caller.user_id,
            user_name=context.caller.name,
            workflow_name=workflow_name,
            input_data=input_data,
            form_id=None  # Endpoints don't have form context
        )

        logger.info(
            f"Starting workflow endpoint execution: {workflow_name}",
            extra={
                "execution_id": execution_id,
                "org_id": context.org_id,
                "user_id": context.caller.user_id,
                "workflow_name": workflow_name,
                "http_method": http_method
            }
        )

        # Apply type coercion to input data
        param_metadata = {param.name: param for param in workflow_metadata.parameters}
        coerced_data = coerce_parameter_types(input_data, param_metadata)

        # Separate workflow parameters from extra variables
        workflow_params, extra_variables = separate_workflow_params(coerced_data, workflow_metadata)

        # Inject extra variables into context
        for key, value in extra_variables.items():
            context.set_variable(key, value)

        # Call the workflow function with context as first parameter
        result = await workflow_func(context, **workflow_params)

        # Record successful execution
        response = await record_workflow_execution_result(
            exec_logger=exec_logger,
            execution_id=execution_id,
            context=context,
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

        return func.HttpResponse(
            json.dumps(response.model_dump(mode='json')),
            status_code=200,
            mimetype="application/json"
        )

    except WorkflowError as e:
        # Expected workflow error - log as warning
        response = await record_workflow_execution_result(
            exec_logger=exec_logger,
            execution_id=execution_id,
            context=context,
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

        return func.HttpResponse(
            json.dumps(response.model_dump(mode='json')),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        # Unexpected error - log with full traceback
        response = await record_workflow_execution_result(
            exec_logger=exec_logger,
            execution_id=execution_id,
            context=context,
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

        return func.HttpResponse(
            json.dumps(response.model_dump(mode='json')),
            status_code=200,
            mimetype="application/json"
        )
