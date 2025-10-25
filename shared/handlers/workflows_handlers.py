"""
Workflows Handlers V2 - Refactored to use unified engine
Business logic for workflow execution using shared/engine.py
"""

import base64
import json
import logging
import uuid
from datetime import datetime

import azure.functions as func

from shared.context import Caller
from shared.engine import ExecutionRequest, execute
from shared.execution_logger import get_execution_logger
from shared.models import ErrorResponse, ExecutionStatus, WorkflowExecutionResponse
from shared.registry import get_registry

logger = logging.getLogger(__name__)


async def execute_workflow_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Execute a workflow with the provided parameters - V2 using unified engine.

    Supports:
    - Named workflows from registry
    - Inline Python scripts (base64-encoded)
    - Async execution (enqueue to worker)
    - Transient execution (no DB writes, for editor)
    """
    # Pre-execution setup
    try:
        # Get context from request (injected by @with_org_context decorator)
        context = req.org_context  # type: ignore[attr-defined]
        user_id = context.user_id

        # Hot-reload: Re-discover workspace modules
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

    # Parse request body
    try:
        body = req.get_json() or {}

        if not isinstance(body, dict):
            raise ValueError("Request body must be a JSON object")

        # Extract fields
        workflow_name = body.get('workflowName') or req.route_params.get('workflowName')
        form_id = body.get('formId')
        input_data = body.get('inputData', {})
        transient = body.get('transient', False)
        code_base64 = body.get('code')
        script_name = body.get('scriptName')

        # Validate
        if not workflow_name and not code_base64:
            raise ValueError("Either 'workflowName' or 'code' must be provided")

    except (ValueError, TypeError) as e:
        logger.error(f"Failed to parse request body: {str(e)}")
        error = ErrorResponse(error="BadRequest", message=str(e))
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    # Determine execution mode
    is_script = bool(code_base64)

    if is_script:
        # Use scriptName or fallback
        workflow_name = script_name or "script"

        try:
            # Validate base64 (engine will decode it)
            base64.b64decode(code_base64).decode('utf-8')
        except Exception as e:
            error = ErrorResponse(
                error="BadRequest",
                message=f"Invalid base64 encoded code: {str(e)}"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )
    else:
        # Look up workflow from registry
        assert workflow_name is not None, "workflow_name should not be None at this point"
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

        # Check if async execution required (scripts always sync)
        if workflow_metadata.execution_mode == "async":
            from shared.async_executor import enqueue_workflow_execution

            assert workflow_name is not None
            execution_id = await enqueue_workflow_execution(
                context=context,
                workflow_name=workflow_name,
                parameters=input_data,
                form_id=form_id
            )

            return func.HttpResponse(
                json.dumps({
                    "executionId": execution_id,
                    "status": "Pending",
                    "message": "Workflow queued for async execution"
                }),
                status_code=202,
                mimetype="application/json"
            )

    # Synchronous execution path
    execution_id = str(uuid.uuid4())
    exec_logger = get_execution_logger()
    start_time = datetime.utcnow()

    try:
        # Create execution record - skip if transient
        if not transient:
            assert workflow_name is not None
            exec_logger.create_execution(
                execution_id=execution_id,
                org_id=context.org_id,
                user_id=user_id,
                user_name=context.name,
                workflow_name=workflow_name,
                input_data=input_data,
                form_id=form_id
            )

        logger.info(
            f"Starting workflow execution: {workflow_name}",
            extra={
                "execution_id": execution_id,
                "org_id": context.org_id,
                "user_id": user_id
            }
        )

        # Build execution request for engine
        request = ExecutionRequest(
            execution_id=execution_id,
            caller=Caller(
                user_id=context.user_id,
                email=context.email,
                name=context.name
            ),
            organization=context.organization,
            config=context._config,
            code=code_base64 if is_script else None,
            name=workflow_name if not is_script else None,
            parameters=input_data,
            transient=transient,
            is_platform_admin=context.is_platform_admin
        )

        # Execute via unified engine
        result = await execute(request)

        # Update execution record - skip if transient
        if not transient:
            exec_logger.update_execution(
                execution_id=execution_id,
                org_id=context.org_id,
                user_id=user_id,
                status=result.status,
                result=result.result,
                error_message=result.error_message,
                error_type=result.error_type,
                duration_ms=result.duration_ms,
                state_snapshots=result.state_snapshots,
                integration_calls=result.integration_calls,
                logs=result.logs if result.logs else None,
                variables=result.variables if result.variables else None
            )

        # Build HTTP response
        # Return logs/variables for platform admins (transient executions only show in response)
        response_logs = result.logs if context.is_platform_admin else None
        response_variables = result.variables if context.is_platform_admin else None

        end_time = datetime.utcnow()

        response = WorkflowExecutionResponse(
            executionId=execution_id,
            status=result.status,
            result=result.result if result.status == ExecutionStatus.SUCCESS else None,
            error=result.error_message,
            errorType=result.error_type,
            durationMs=result.duration_ms,
            startedAt=start_time,
            completedAt=end_time,
            logs=response_logs,
            variables=response_variables,
            isTransient=transient
        )

        return func.HttpResponse(
            json.dumps(response.model_dump(), default=str),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        # CRITICAL: Catch-all to prevent stuck executions
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.error(
            f"Unexpected error in workflow execution: {workflow_name}",
            extra={"execution_id": execution_id, "error": str(e)},
            exc_info=True
        )

        # Try to update execution record
        if not transient:
            try:
                exec_logger.update_execution(
                    execution_id=execution_id,
                    org_id=context.org_id,
                    user_id=user_id,
                    status=ExecutionStatus.FAILED,
                    error_message=f"Unexpected error: {str(e)}",
                    error_type="InternalError",
                    duration_ms=duration_ms
                )
            except Exception as update_error:
                logger.error(f"Failed to update execution record: {update_error}")

        # Return error response
        response = WorkflowExecutionResponse(
            executionId=execution_id,
            status=ExecutionStatus.FAILED,
            error=str(e),
            errorType="InternalError",
            durationMs=duration_ms,
            startedAt=start_time,
            completedAt=end_time,
            isTransient=transient
        )

        return func.HttpResponse(
            json.dumps(response.model_dump(), default=str),
            status_code=200,
            mimetype="application/json"
        )
