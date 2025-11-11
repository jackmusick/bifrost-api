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
from shared.errors import UserError
from shared.execution_logger import get_execution_logger
from shared.models import ErrorResponse, ExecutionStatus
from shared.registry import get_registry
from shared.webpubsub_broadcaster import WebPubSubBroadcaster

logger = logging.getLogger(__name__)


async def execute_workflow_internal(
    context,
    workflow_name: str,
    parameters: dict,
    form_id: str | None = None,
    transient: bool = False,
    code_base64: str | None = None
) -> tuple[dict, int]:
    """
    Internal workflow execution logic shared by forms and workflow execute endpoint.

    Args:
        context: ExecutionContext with org scope and user info
        workflow_name: Name of workflow to execute
        parameters: Workflow parameters
        form_id: Optional form ID if triggered by form
        transient: If True, don't write to database
        code_base64: Optional base64-encoded inline script

    Returns:
        tuple of (response_dict, status_code)
    """
    user_id = context.user_id

    # Determine execution mode
    is_script = bool(code_base64)

    if is_script:
        # Scripts always execute synchronously
        pass
    else:
        # Look up workflow from registry
        registry = get_registry()
        workflow_metadata = registry.get_workflow(workflow_name)

        if not workflow_metadata:
            logger.warning(f"Workflow not found: {workflow_name}")
            return {
                "error": "NotFound",
                "message": f"Workflow '{workflow_name}' not found"
            }, 404

        # Check if async execution required
        if workflow_metadata.execution_mode == "async":
            from shared.async_executor import enqueue_workflow_execution

            execution_id = await enqueue_workflow_execution(
                context=context,
                workflow_name=workflow_name,
                parameters=parameters,
                form_id=form_id
            )

            return {
                "executionId": execution_id,
                "status": "Pending",
                "message": "Workflow queued for async execution"
            }, 202

    # Synchronous execution path
    execution_id = str(uuid.uuid4())
    exec_logger = get_execution_logger()
    start_time = datetime.utcnow()

    # Initialize Web PubSub broadcaster for real-time updates
    broadcaster = WebPubSubBroadcaster()

    try:
        # Create execution record - skip if transient
        if not transient:
            await exec_logger.create_execution(
                execution_id=execution_id,
                org_id=context.org_id,
                user_id=user_id,
                user_name=context.name,
                workflow_name=workflow_name,
                input_data=parameters,
                form_id=form_id,
                webpubsub_broadcaster=broadcaster
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
            parameters=parameters,
            transient=transient,
            is_platform_admin=context.is_platform_admin,
            broadcaster=broadcaster
        )

        # Execute via unified engine
        result = await execute(request)

        # Update execution record - skip if transient
        if not transient:
            await exec_logger.update_execution(
                execution_id=execution_id,
                org_id=context.org_id,
                user_id=user_id,
                status=result.status,
                result=result.result,
                error_message=result.error_message,
                error_type=result.error_type,
                duration_ms=result.duration_ms,
                integration_calls=result.integration_calls,
                logs=result.logs if result.logs else None,
                variables=result.variables if result.variables else None,
                webpubsub_broadcaster=broadcaster
            )

        # Build response
        end_time = datetime.utcnow()

        response_dict = {
            "executionId": execution_id,
            "status": result.status.value,
            "durationMs": result.duration_ms,
            "startedAt": start_time.isoformat(),
            "completedAt": end_time.isoformat(),
            "isTransient": transient
        }

        if result.status == ExecutionStatus.SUCCESS:
            response_dict["result"] = result.result
        elif result.error_message:
            # Filter error details based on user role and error type
            if context.is_platform_admin:
                # Admins see full technical details
                response_dict["error"] = result.error_message
                response_dict["errorType"] = result.error_type
            else:
                # Regular users: Check if it's a UserError (show message) or generic error (hide details)
                # We need to check the error_type to determine if it was a UserError
                if result.error_type == "UserError":
                    response_dict["error"] = result.error_message
                else:
                    response_dict["error"] = "An error occurred during execution"

        # Include logs/variables for platform admins
        if context.is_platform_admin:
            if result.logs:
                response_dict["logs"] = result.logs
            if result.variables:
                response_dict["variables"] = result.variables
        else:
            # Regular users: Filter logs to exclude DEBUG and TRACEBACK levels
            if result.logs:
                filtered_logs = [
                    log for log in result.logs
                    if log.get('level') not in ['debug', 'traceback']
                ]
                response_dict["logs"] = filtered_logs

        return response_dict, 200

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
                await exec_logger.update_execution(
                    execution_id=execution_id,
                    org_id=context.org_id,
                    user_id=user_id,
                    status=ExecutionStatus.FAILED,
                    error_message=f"Unexpected error: {str(e)}",
                    error_type="InternalError",
                    duration_ms=duration_ms
                )
            except Exception as update_error:
                logger.error(
                    f"Failed to update execution record: {update_error}")

        # Return error response
        return {
            "executionId": execution_id,
            "status": "Failed",
            "error": str(e),
            "errorType": "InternalError",
            "durationMs": duration_ms,
            "startedAt": start_time.isoformat(),
            "completedAt": end_time.isoformat(),
            "isTransient": transient
        }, 200


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
        workflow_name = body.get(
            'workflowName') or req.route_params.get('workflowName')
        form_id = body.get('formId')
        input_data = body.get('inputData', {})
        transient = body.get('transient', False)
        code_base64 = body.get('code')
        script_name = body.get('scriptName')

        # Validate
        if not workflow_name and not code_base64:
            raise ValueError(
                "Either 'workflowName' or 'code' must be provided")

        # For scripts, use scriptName or fallback
        if code_base64:
            workflow_name = script_name or "script"
            # Validate base64
            try:
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

        # At this point, workflow_name must be set (either from body/route params or defaulted to "script")
        assert workflow_name is not None, "workflow_name should be set"

    except (ValueError, TypeError) as e:
        logger.error(f"Failed to parse request body: {str(e)}")
        error = ErrorResponse(error="BadRequest", message=str(e))
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    # Delegate to internal execution logic
    response_dict, status_code = await execute_workflow_internal(
        context=context,
        workflow_name=workflow_name,
        parameters=input_data,
        form_id=form_id,
        transient=transient,
        code_base64=code_base64
    )

    return func.HttpResponse(
        json.dumps(response_dict, default=str),
        status_code=status_code,
        mimetype="application/json"
    )
