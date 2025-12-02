"""
Workflows Business Logic

Reusable functions for workflow operations (used by both HTTP handlers and Bifrost SDK).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from shared.discovery import scan_all_workflows

if TYPE_CHECKING:
    from shared.context import ExecutionContext

logger = logging.getLogger(__name__)


def list_workflows_logic(context: 'ExecutionContext') -> list[dict[str, Any]]:
    """
    List all available workflows (business logic).

    Args:
        context: Request context with user info

    Returns:
        list[dict]: List of workflow metadata dictionaries
    """
    logger.info(f"User {context.user_id} listing workflows")

    # Dynamically scan all workflows (always fresh)
    workflows = scan_all_workflows()

    # Convert to dicts for serialization
    workflow_list = [
        {
            "name": wf.name,
            "description": wf.description,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type,
                    "required": p.required,
                    "description": p.help_text
                }
                for p in wf.parameters
            ],
            "executionMode": wf.execution_mode,
            "endpointEnabled": wf.endpoint_enabled
        }
        for wf in workflows
    ]

    logger.info(f"Returning {len(workflow_list)} workflows for user {context.user_id}")

    return workflow_list


async def get_workflow_status_logic(context: 'ExecutionContext', execution_id: str) -> dict[str, Any] | None:
    """
    Get workflow execution status (business logic).

    Args:
        context: Request context with user info
        execution_id: Execution ID

    Returns:
        dict | None: Execution status dictionary or None if not found
    """
    from shared.handlers.executions_handlers import get_execution_handler

    logger.info(f"User {context.user_id} getting status for execution {execution_id}")

    # Reuse executions logic
    execution, error = await get_execution_handler(context, execution_id)

    if error or not execution:
        logger.warning(f"Execution {execution_id} not found or error: {error}")
        return None

    return execution


async def execute_workflow_logic(
    context: 'ExecutionContext',
    workflow_name: str,
    input_data: dict[str, Any] | None = None,
    form_id: str | None = None,
    transient: bool = False,
):
    """
    Execute a named workflow (business logic).

    Args:
        context: Execution context with user/org info
        workflow_name: Name of workflow to execute
        input_data: Input parameters for the workflow
        form_id: Optional form ID if triggered by form
        transient: If True, don't persist execution record

    Returns:
        WorkflowExecutionResponse with execution results
    """
    from shared.handlers.workflows_handlers import execute_workflow_internal
    from src.models.schemas import WorkflowExecutionResponse, ExecutionStatus

    logger.info(f"User {context.user_id} executing workflow: {workflow_name}")

    response_dict, status_code = await execute_workflow_internal(
        context=context,
        workflow_name=workflow_name,
        parameters=input_data or {},
        form_id=form_id,
        transient=transient,
    )

    # Convert response dict to WorkflowExecutionResponse
    if status_code == 404:
        raise ValueError(f"Workflow '{workflow_name}' not found")
    elif status_code == 500 and "error" in response_dict:
        raise RuntimeError(response_dict.get("message", response_dict.get("error")))

    # Map response to WorkflowExecutionResponse
    return WorkflowExecutionResponse(
        execution_id=response_dict.get("executionId"),
        status=ExecutionStatus(response_dict.get("status", "Pending")),
        result=response_dict.get("result"),
        error=response_dict.get("error"),
        duration_ms=response_dict.get("durationMs"),
    )


async def execute_code_logic(
    context: 'ExecutionContext',
    code: str,
    script_name: str = "inline_script",
    input_data: dict[str, Any] | None = None,
    transient: bool = False,
):
    """
    Execute inline code/script (business logic).

    Args:
        context: Execution context with user/org info
        code: Python code to execute
        script_name: Name for the script execution
        input_data: Input parameters for the script
        transient: If True, don't persist execution record

    Returns:
        WorkflowExecutionResponse with execution results
    """
    import base64
    from shared.handlers.workflows_handlers import execute_workflow_internal
    from src.models.schemas import WorkflowExecutionResponse, ExecutionStatus

    logger.info(f"User {context.user_id} executing inline script: {script_name}")

    # Encode code to base64
    code_base64 = base64.b64encode(code.encode()).decode()

    response_dict, status_code = await execute_workflow_internal(
        context=context,
        workflow_name=script_name,
        parameters=input_data or {},
        transient=transient,
        code_base64=code_base64,
    )

    # Map response to WorkflowExecutionResponse
    return WorkflowExecutionResponse(
        execution_id=response_dict.get("executionId"),
        status=ExecutionStatus(response_dict.get("status", "Pending")),
        result=response_dict.get("result"),
        error=response_dict.get("error"),
        duration_ms=response_dict.get("durationMs"),
    )
