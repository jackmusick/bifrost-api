"""
Workflows Business Logic

Reusable functions for workflow operations (used by both HTTP handlers and Bifrost SDK).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from shared.registry import get_registry

if TYPE_CHECKING:
    from shared.request_context import RequestContext

logger = logging.getLogger(__name__)


def list_workflows_logic(context: 'RequestContext') -> list[dict[str, Any]]:
    """
    List all available workflows (business logic).

    Args:
        context: Request context with user info

    Returns:
        list[dict]: List of workflow metadata dictionaries
    """
    logger.info(f"User {context.user_id} listing workflows")

    registry = get_registry()
    workflows = registry.list_workflows()

    # Convert to dicts for serialization
    workflow_list = [
        {
            "name": wf.name,
            "description": wf.description,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type_hint,
                    "required": p.required,
                    "description": p.description
                }
                for p in wf.parameters
            ],
            "executionMode": wf.execution_mode,
            "requiresPermission": wf.requires_permission
        }
        for wf in workflows
    ]

    logger.info(f"Returning {len(workflow_list)} workflows for user {context.user_id}")

    return workflow_list


def get_workflow_status_logic(context: 'RequestContext', execution_id: str) -> dict[str, Any] | None:
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
    execution, error = get_execution_handler(context, execution_id)

    if error or not execution:
        logger.warning(f"Execution {execution_id} not found or error: {error}")
        return None

    return execution
