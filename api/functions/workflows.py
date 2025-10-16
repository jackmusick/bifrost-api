"""
Workflow Execution API
Handles execution of registered workflows with org context
"""

import json
import logging
import uuid
from datetime import datetime

import azure.functions as func

from shared.error_handling import ValidationError, WorkflowError
from shared.execution_logger import get_execution_logger
from shared.middleware import with_org_context
from shared.models import ErrorResponse, ExecutionStatus, WorkflowExecutionRequest, WorkflowExecutionResponse
from shared.openapi_decorators import openapi_endpoint
from shared.registry import get_registry

logger = logging.getLogger(__name__)

# Create blueprint for workflow execution endpoints
bp = func.Blueprint()


@bp.route(route="workflows/{workflowName}/execute", methods=["POST"])
@openapi_endpoint(
    path="/workflows/{workflowName}/execute",
    method="POST",
    summary="Execute a workflow",
    description="Execute a workflow with the provided parameters",
    tags=["Workflows"],
    request_model=WorkflowExecutionRequest,
    response_model=WorkflowExecutionResponse,
    path_params={
        "workflowName": {
            "description": "Name of the workflow to execute",
            "schema": {"type": "string"},
            "required": True
        }
    }
)
@with_org_context
async def execute_workflow(req: func.HttpRequest) -> func.HttpResponse:
    """
    Execute a workflow with the provided parameters.

    T057: Authentication handled by @with_org_context decorator using AuthenticationService.

    Can be called with tiered authentication:
    1. Function key (x-functions-key header or ?code=xxx) - HIGHEST PRIORITY
    2. Easy Auth (X-MS-CLIENT-PRINCIPAL header from Azure AD) - FALLBACK
    3. None → 403 Forbidden

    Headers:
        X-Organization-Id: Organization ID (optional - omit for global/platform admin context)
        x-functions-key: Function key for privileged access (optional)
        X-MS-CLIENT-PRINCIPAL: Easy Auth principal (optional, set by Azure)
        X-User-Id: DEPRECATED - User info now extracted from authentication principal

    Body (WorkflowExecutionRequest):
        {
            "inputData": {
                "param1": "value1",
                "param2": "value2"
            },
            "formId": "optional-form-id"  // Optional: reference to form that triggered execution
        }

        If workflow has no parameters, body can be omitted or inputData can be empty dict.

    Response (WorkflowExecutionResponse):
        200: {
            "executionId": "uuid",
            "status": "Success" | "Failed",
            "result": { ... },           // Present on success
            "error": "error message",     // Present on failure
            "errorType": "ErrorType",     // Present on failure
            "details": { ... },           // Present on failure with details
            "durationMs": 1234,
            "startedAt": "ISO8601",
            "completedAt": "ISO8601"
        }
        400: Validation error
        404: Workflow not found
        500: Execution error
    """
    # Get context from request (injected by @with_org_context decorator)
    context = req.org_context  # type: ignore[attr-defined]

    workflow_name = req.route_params.get('workflowName')
    assert workflow_name is not None, "workflowName is required"

    # T057: Extract user_id from context.caller (set by authentication service)
    user_id = context.caller.user_id  # Now comes from authenticated principal

    # Hot-reload: Re-discover workspace modules on every request
    # This allows adding/modifying workflows without restarting
    from function_app import discover_workspace_modules
    discover_workspace_modules()

    # Parse request body (WorkflowExecutionRequest) - optional, defaults to empty inputData
    try:
        body = req.get_json()

        # If no body provided, default to empty dict
        if body is None:
            body = {}

        if not isinstance(body, dict):
            raise ValueError("Request body must be a JSON object")

        # Extract form_id and inputData from request body
        form_id = body.get('formId')
        input_data = body.get('inputData', {})

        # If input_data is not provided, treat empty body as empty parameters
        if not input_data and not form_id:
            input_data = {}
    except ValueError as e:
        logger.error(f"Failed to parse request body: {str(e)}")
        error = ErrorResponse(
            error="BadRequest",
            message="Invalid JSON body"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Failed to parse request body: {str(e)}")
        error = ErrorResponse(
            error="BadRequest",
            message="Invalid JSON body"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
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

    # Get workflow function
    workflow_func = workflow_metadata.function

    # TODO: Check permissions (requires_permission from metadata)
    # For now, we assume @with_org_context has validated org access (or function key for direct calls)

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
            user_id=user_id,
            workflow_name=workflow_name,
            input_data=input_data,
            form_id=form_id
        )

        logger.info(
            f"Starting workflow execution: {workflow_name}",
            extra={
                "execution_id": execution_id,
                "org_id": context.org_id,
                "user_id": user_id,
                "workflow_name": workflow_name
            }
        )

        # Separate workflow parameters from extra data
        # Get defined parameters from workflow metadata
        defined_params = {param.name for param in workflow_metadata.parameters}

        # Split input_data into workflow params and extra variables
        workflow_params = {}
        extra_variables = {}

        for key, value in input_data.items():
            if key in defined_params:
                workflow_params[key] = value
            else:
                extra_variables[key] = value

        # Inject extra variables into context so workflows can access them
        # This allows passing additional data that isn't in the function signature
        for key, value in extra_variables.items():
            context.set_variable(key, value)

        logger.info(
            f"Injected {len(extra_variables)} extra variables into context",
            extra={
                "execution_id": execution_id,
                "extra_variables": list(extra_variables.keys())
            }
        )

        # Execute workflow with only defined parameters
        # Note: Workflow functions are async and receive (context, **params)
        result = await workflow_func(context, **workflow_params)

        # Calculate duration
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Determine execution status based on result
        # If result is a dict with success=false, mark as COMPLETED_WITH_ERRORS
        # This is like PowerShell's Write-Error (non-terminating error)
        execution_status = ExecutionStatus.SUCCESS
        error_message = None

        if isinstance(result, dict) and result.get('success') is False:
            execution_status = ExecutionStatus.COMPLETED_WITH_ERRORS
            error_message = result.get(
                'error', 'Workflow completed with errors')
            logger.warning(
                f"Workflow completed with errors: {workflow_name} - {error_message}",
                extra={
                    "execution_id": execution_id,
                    "duration_ms": duration_ms
                }
            )
        else:
            logger.info(
                f"Workflow execution completed successfully: {workflow_name}",
                extra={
                    "execution_id": execution_id,
                    "duration_ms": duration_ms
                }
            )

        # Update execution record
        await exec_logger.update_execution(
            execution_id=execution_id,
            org_id=context.org_id,
            user_id=user_id,
            status=execution_status,
            result=result,
            error_message=error_message,
            duration_ms=duration_ms,
            state_snapshots=context._state_snapshots,
            integration_calls=context._integration_calls,
            logs=context._logs,
            variables=context._variables
        )

        # Build success response
        response = WorkflowExecutionResponse(
            executionId=execution_id,
            status=execution_status,
            result=result,
            durationMs=duration_ms,
            startedAt=start_time,
            completedAt=end_time
        )

        return func.HttpResponse(
            json.dumps(response.model_dump(), default=str),
            status_code=200,
            mimetype="application/json"
        )

    except WorkflowError as e:
        # Handle known workflow errors
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.error(
            f"Workflow execution failed: {workflow_name} - {e.error_type}: {e.message}",
            extra={
                "execution_id": execution_id,
                "error_type": e.error_type,
                "details": e.details
            },
            exc_info=True
        )

        # Update execution record (status=FAILED)
        await exec_logger.update_execution(
            execution_id=execution_id,
            org_id=context.org_id,
            user_id=user_id,
            status=ExecutionStatus.FAILED,
            error_message=e.message,
            error_type=e.error_type,
            error_details=e.details,
            duration_ms=duration_ms,
            state_snapshots=context._state_snapshots,
            integration_calls=context._integration_calls,
            logs=context._logs,
            variables=context._variables
        )

        # Build error response
        response = WorkflowExecutionResponse(
            executionId=execution_id,
            status=ExecutionStatus.FAILED,
            error=e.message,
            errorType=e.error_type,
            details=e.details,
            durationMs=duration_ms,
            startedAt=start_time,
            completedAt=end_time
        )

        # Return 400 for validation errors, 500 for others
        status_code = 400 if isinstance(e, ValidationError) else 500

        return func.HttpResponse(
            json.dumps(response.model_dump(), default=str),
            status_code=status_code,
            mimetype="application/json"
        )

    except Exception as e:
        # Handle unexpected errors
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.error(
            f"Unexpected error in workflow execution: {workflow_name}",
            extra={
                "execution_id": execution_id,
                "error": str(e)
            },
            exc_info=True
        )

        # Update execution record (status=FAILED)
        await exec_logger.update_execution(
            execution_id=execution_id,
            org_id=context.org_id,
            user_id=user_id,
            status=ExecutionStatus.FAILED,
            error_message=f"Internal error: {str(e)}",
            error_type="InternalError",
            error_details={"exception": type(e).__name__},
            duration_ms=duration_ms,
            state_snapshots=context._state_snapshots,
            integration_calls=context._integration_calls,
            logs=context._logs,
            variables=context._variables
        )

        # Build error response
        response = WorkflowExecutionResponse(
            executionId=execution_id,
            status=ExecutionStatus.FAILED,
            error=f"Internal error: {str(e)}",
            errorType="InternalError",
            durationMs=duration_ms,
            startedAt=start_time,
            completedAt=end_time
        )

        return func.HttpResponse(
            json.dumps(response.model_dump(), default=str),
            status_code=500,
            mimetype="application/json"
        )
