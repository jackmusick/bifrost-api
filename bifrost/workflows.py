"""
Workflows SDK for Bifrost.

Provides Python API for workflow operations (list, execute, get status).
"""

from __future__ import annotations

from typing import Any

from shared.handlers.workflows_logic import get_workflow_status_logic, list_workflows_logic

from ._internal import get_context


class workflows:
    """
    Workflow operations.

    Allows workflows to trigger other workflows and query execution status.
    """

    @staticmethod
    def execute(workflow_name: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Execute another workflow programmatically.

        Args:
            workflow_name: Name of workflow to execute
            parameters: Workflow parameters (optional)

        Returns:
            dict: Execution result

        Raises:
            ValueError: If workflow not found
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import workflows
            >>> result = workflows.execute("process_order", {"order_id": "12345"})
        """
        import asyncio

        from shared.discovery import load_workflow

        context = get_context()

        # Dynamically load workflow (always fresh)
        load_result = load_workflow(workflow_name)

        if not load_result:
            raise ValueError(f"Workflow not found: {workflow_name}")

        # Execute workflow function directly (avoids HTTP overhead)
        workflow_func, _ = load_result

        # Execute workflow synchronously (workflows are async)
        result = asyncio.run(workflow_func(context, **(parameters or {})))

        return result

    @staticmethod
    def list() -> list[dict[str, Any]]:
        """
        List all available workflows.

        Returns:
            list[dict]: List of workflow metadata

        Raises:
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import workflows
            >>> wf_list = workflows.list()
            >>> for wf in wf_list:
            ...     print(f"{wf['name']}: {wf['description']}")
        """
        context = get_context()

        return list_workflows_logic(context)

    @staticmethod
    def get(execution_id: str) -> dict[str, Any]:
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
            >>> execution = workflows.get("exec-123")
            >>> print(execution["status"])
        """
        context = get_context()

        execution = get_workflow_status_logic(context, execution_id)

        if not execution:
            raise ValueError(f"Execution not found: {execution_id}")

        return execution
