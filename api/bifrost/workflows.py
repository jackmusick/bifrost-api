"""
Workflows SDK for Bifrost.

Provides Python API for workflow operations (list, get status).

All methods are async and must be awaited.
"""

from __future__ import annotations

from typing import Any

from shared.handlers.workflows_logic import list_workflows_logic

from ._internal import get_context
from .executions import executions


class workflows:
    """
    Workflow operations.

    Allows workflows to query available workflows and execution status.

    All methods are async - await is required.
    """

    @staticmethod
    async def list() -> list[dict[str, Any]]:
        """
        List all available workflows.

        Returns:
            list[dict]: List of workflow metadata

        Raises:
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import workflows
            >>> wf_list = await workflows.list()
            >>> for wf in wf_list:
            ...     print(f"{wf['name']}: {wf['description']}")
        """
        context = get_context()

        return list_workflows_logic(context)

    @staticmethod
    async def get(execution_id: str) -> dict[str, Any]:
        """
        Get execution details for a workflow.

        Args:
            execution_id: Execution ID

        Returns:
            dict: Execution details including status, result, logs

        Raises:
            ValueError: If execution not found
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import workflows
            >>> execution = await workflows.get("exec-123")
            >>> print(execution["status"])
        """
        # Use the async executions SDK
        return await executions.get(execution_id)
