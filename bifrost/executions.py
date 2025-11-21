"""
Execution history SDK for Bifrost.

Provides Python API for execution history operations (list, get).

All methods are async and must be called with await.
"""

from typing import Any

from shared.handlers.executions_handlers import get_execution_handler, list_executions_handler

from ._internal import get_context


class executions:
    """
    Execution history operations.

    Allows workflows to query execution history.

    All methods are async and must be awaited.
    """

    @staticmethod
    async def list(
        workflow_name: str | None = None,
        status: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """
        List workflow executions with filtering.

        Platform admins see all executions in their scope.
        Regular users see only their own executions.

        Args:
            workflow_name: Filter by workflow name (optional)
            status: Filter by status (optional)
            start_date: Filter by start date in ISO format (optional)
            end_date: Filter by end date in ISO format (optional)
            limit: Maximum number of results (default: 50, max: 1000)

        Returns:
            list[dict]: List of execution dictionaries

        Raises:
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import executions
            >>> recent = await executions.list(limit=10)
            >>> failed = await executions.list(status="Failed")
            >>> workflow_execs = await executions.list(workflow_name="create_customer")
        """
        context = get_context()

        # Use the handler to get filtered executions
        execs, _ = await list_executions_handler(
            context=context,
            workflow_name=workflow_name,
            status=status,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            continuation_token=None
        )

        return execs

    @staticmethod
    async def get(execution_id: str) -> dict[str, Any]:
        """
        Get execution details by ID.

        Platform admins can view any execution in their scope.
        Regular users can only view their own executions.

        Args:
            execution_id: Execution ID (UUID)

        Returns:
            dict: Execution details

        Raises:
            ValueError: If execution not found or access denied
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import executions
            >>> exec_details = await executions.get("exec-123")
            >>> print(exec_details["status"])
            >>> print(exec_details["result"])
        """
        context = get_context()

        execution, error = await get_execution_handler(context, execution_id)

        if error:
            if error == "NotFound":
                raise ValueError(f"Execution not found: {execution_id}")
            elif error == "Forbidden":
                raise PermissionError(f"Access denied to execution: {execution_id}")
            else:
                raise ValueError(f"Error retrieving execution: {error}")

        return execution or {}

