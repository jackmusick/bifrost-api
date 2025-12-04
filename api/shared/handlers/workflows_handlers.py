"""
Workflows Handlers V2 - Refactored to use unified engine
Business logic for workflow execution using shared/engine.py

Note: HTTP handlers have been removed - see FastAPI routers in src/routers/
"""

import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from shared.context import Caller
from shared.discovery import get_workflow
from shared.engine import ExecutionRequest, execute
from shared.models import ErrorResponse, ExecutionStatus

# Lazy imports to avoid unnecessary dependencies for validation-only use cases
if TYPE_CHECKING:
    pass

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

    # Determine if async execution is required
    execution_mode = "async"  # Default for scripts

    # Variables to hold loaded workflow data
    workflow_func = None
    workflow_metadata = None

    if not is_script:
        # Dynamically load workflow (always fresh import)
        try:
            result = get_workflow(workflow_name)
            if not result:
                logger.warning(f"Workflow not found: {workflow_name}")
                return {
                    "error": "NotFound",
                    "message": f"Workflow '{workflow_name}' not found"
                }, 404

            workflow_func, workflow_metadata = result
            logger.debug(f"Loaded workflow fresh: {workflow_name}")
        except Exception as e:
            # Load failed (likely syntax error)
            logger.error(f"Failed to load workflow {workflow_name}: {e}", exc_info=True)
            error_response = ErrorResponse(
                error="WorkflowLoadError",
                message=f"Failed to load workflow '{workflow_name}': {str(e)}"
            )
            return error_response.model_dump(), 500

        # Get execution mode from workflow metadata
        execution_mode = workflow_metadata.execution_mode

    # Queue for async execution if required
    if execution_mode == "async":
        from shared.async_executor import enqueue_workflow_execution

        execution_id = await enqueue_workflow_execution(
            context=context,
            workflow_name=workflow_name,
            parameters=parameters,
            form_id=form_id,
            code_base64=code_base64  # Pass script code if present
        )

        return {
            "executionId": execution_id,
            "status": "Pending",
            "message": "Workflow queued for async execution" if not is_script else "Script queued for async execution"
        }, 202

    # Synchronous execution path
    execution_id = str(uuid.uuid4())

    # Runtime imports to avoid unnecessary dependencies at module load
    from shared.execution_logger import get_execution_logger
    from shared.webpubsub_broadcaster import WebPubSubBroadcaster

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
            func=workflow_func if not is_script else None,
            code=code_base64 if is_script else None,
            name=workflow_name,
            tags=["workflow"] if not is_script else [],
            timeout_seconds=workflow_metadata.timeout_seconds if workflow_metadata else 1800,
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


# Note: HTTP handlers are implemented in FastAPI routers.
# See src/routers/workflows.py for the HTTP endpoint implementation.


async def validate_workflow_file(path: str, content: str | None = None):
    """
    Validate a workflow file for syntax errors, decorator issues, and Pydantic validation.

    Args:
        path: Relative workspace path to the workflow file
        content: Optional file content (if not provided, reads from disk)

    Returns:
        WorkflowValidationResponse with validation results
    """
    from pathlib import Path
    import tempfile
    import os
    import re
    from pydantic import ValidationError
    from shared.models import WorkflowValidationResponse, ValidationIssue
    from shared.handlers.discovery_handlers import convert_workflow_metadata_to_model
    from shared.discovery import import_module_fresh, WorkflowMetadata
    from shared.decorators import VALID_PARAM_TYPES

    issues = []
    valid = True
    metadata = None

    # Determine the absolute file path
    workspace_roots = ["/home", "/platform", "/workspace"]
    workspace_location = os.environ.get("BIFROST_WORKSPACE_LOCATION")
    if workspace_location:
        workspace_roots.insert(0, workspace_location)

    abs_path = None
    for root in workspace_roots:
        candidate = Path(root) / path
        if candidate.exists():
            abs_path = candidate
            break

    # If content provided, use temporary file; otherwise use actual file
    if content is not None:
        # Create a temporary file with the content
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
        try:
            temp_file.write(content)
            temp_file.close()
            file_to_validate = Path(temp_file.name)
            file_content = content
        except Exception as e:
            issues.append(ValidationIssue(
                line=None,
                message=f"Failed to write temporary file: {str(e)}",
                severity="error"
            ))
            return WorkflowValidationResponse(valid=False, issues=issues, metadata=None)
    else:
        if abs_path is None or not abs_path.exists():
            issues.append(ValidationIssue(
                line=None,
                message=f"File not found: {path}",
                severity="error"
            ))
            return WorkflowValidationResponse(valid=False, issues=issues, metadata=None)
        file_to_validate = abs_path
        file_content = abs_path.read_text()

    try:
        # Step 1: Check for Python syntax errors
        try:
            compile(file_content, str(file_to_validate), 'exec')
        except SyntaxError as e:
            issues.append(ValidationIssue(
                line=e.lineno,
                message=f"Syntax error: {e.msg}",
                severity="error"
            ))
            valid = False
            return WorkflowValidationResponse(valid=valid, issues=issues, metadata=None)

        # Step 2: Check for import errors by attempting to load the module
        try:
            module = import_module_fresh(file_to_validate)
        except Exception as e:
            # Import error - could be missing dependencies or runtime errors
            issues.append(ValidationIssue(
                line=None,
                message=f"Import error: {str(e)}",
                severity="error"
            ))
            valid = False
            return WorkflowValidationResponse(valid=valid, issues=issues, metadata=None)

        # Step 3: Check if @workflow decorator was found by scanning module
        discovered_workflows: list[WorkflowMetadata] = []
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if callable(attr) and hasattr(attr, '_workflow_metadata'):
                metadata_obj = attr._workflow_metadata
                if isinstance(metadata_obj, WorkflowMetadata):
                    discovered_workflows.append(metadata_obj)

        if not discovered_workflows:
            issues.append(ValidationIssue(
                line=None,
                message="No @workflow decorator found. Functions must use @workflow(...) to be discoverable.",
                severity="error"
            ))
            valid = False
            return WorkflowValidationResponse(valid=valid, issues=issues, metadata=None)

        # Use the first matching workflow for validation
        # (most files will have just one workflow, but we support multiple)
        workflow_metadata = discovered_workflows[0]

        # Step 4: Validate workflow name pattern
        name_pattern = r"^[a-z0-9_]+$"
        if not re.match(name_pattern, workflow_metadata.name):
            issues.append(ValidationIssue(
                line=None,
                message=f"Invalid workflow name '{workflow_metadata.name}'. Name must be lowercase snake_case (only letters, numbers, underscores).",
                severity="error"
            ))
            valid = False

        # Step 5: Validate required fields
        if not workflow_metadata.description or len(workflow_metadata.description.strip()) == 0:
            issues.append(ValidationIssue(
                line=None,
                message="Workflow description is required and cannot be empty.",
                severity="error"
            ))
            valid = False

        # Step 6: Validate execution mode
        if workflow_metadata.execution_mode not in ["sync", "async"]:
            issues.append(ValidationIssue(
                line=None,
                message=f"Invalid execution mode '{workflow_metadata.execution_mode}'. Must be 'sync' or 'async'.",
                severity="error"
            ))
            valid = False

        # Step 7: Validate timeout
        if workflow_metadata.timeout_seconds is not None:
            if workflow_metadata.timeout_seconds < 1 or workflow_metadata.timeout_seconds > 7200:
                issues.append(ValidationIssue(
                    line=None,
                    message=f"Invalid timeout {workflow_metadata.timeout_seconds}s. Must be between 1 and 7200 seconds.",
                    severity="error"
                ))
                valid = False

        # Step 8: Validate parameter types
        if workflow_metadata.parameters:
            for param in workflow_metadata.parameters:
                if param.type not in VALID_PARAM_TYPES:
                    issues.append(ValidationIssue(
                        line=None,
                        message=f"Invalid parameter type '{param.type}' for parameter '{param.name}'. Must be one of: {', '.join(VALID_PARAM_TYPES)}",
                        severity="error"
                    ))
                    valid = False

        # Step 9: Validate Pydantic model conversion (this is what discovery endpoint does)
        try:
            metadata = convert_workflow_metadata_to_model(workflow_metadata)
        except ValidationError as e:
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                issues.append(ValidationIssue(
                    line=None,
                    message=f"Validation error in field '{field}': {error['msg']}",
                    severity="error"
                ))
            valid = False

        # Step 10: Warnings for best practices
        if workflow_metadata.category == "General":
            issues.append(ValidationIssue(
                line=None,
                message="Consider specifying a category other than 'General' for better organization.",
                severity="warning"
            ))

        if not workflow_metadata.tags or len(workflow_metadata.tags) == 0:
            issues.append(ValidationIssue(
                line=None,
                message="Consider adding tags to make your workflow more discoverable.",
                severity="warning"
            ))

    finally:
        # Clean up temporary file if created
        if content is not None:
            try:
                os.unlink(temp_file.name)
            except Exception:
                pass

    return WorkflowValidationResponse(valid=valid, issues=issues, metadata=metadata)
