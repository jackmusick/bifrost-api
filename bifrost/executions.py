"""
Execution history SDK for Bifrost.

Provides Python API for execution history operations (list, get, delete).
"""

from typing import Any

from shared.handlers.executions_handlers import get_execution_handler, list_executions_handler
from shared.repositories.executions import ExecutionRepository

from ._internal import get_context


class executions:
    """
    Execution history operations.

    Allows workflows to query execution history and clean up old executions.
    """

    @staticmethod
    def list(
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
            >>> recent = executions.list(limit=10)
            >>> failed = executions.list(status="Failed")
            >>> workflow_execs = executions.list(workflow_name="create_customer")
        """
        import asyncio

        context = get_context()

        # Use the handler to get filtered executions
        execs, _ = asyncio.run(list_executions_handler(
            context=context,
            workflow_name=workflow_name,
            status=status,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            continuation_token=None
        ))

        return execs

    @staticmethod
    def get(execution_id: str) -> dict[str, Any]:
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
            >>> exec_details = executions.get("exec-123")
            >>> print(exec_details["status"])
            >>> print(exec_details["result"])
        """
        import asyncio

        context = get_context()

        execution, error = asyncio.run(get_execution_handler(context, execution_id))

        if error:
            if error == "NotFound":
                raise ValueError(f"Execution not found: {execution_id}")
            elif error == "Forbidden":
                raise PermissionError(f"Access denied to execution: {execution_id}")
            else:
                raise ValueError(f"Error retrieving execution: {error}")

        return execution or {}

    @staticmethod
    def delete(execution_id: str) -> None:
        """
        Delete an execution from history.

        Useful for cleaning up old or sensitive execution data.
        Platform admins can delete any execution in their scope.
        Regular users can only delete their own executions.

        Args:
            execution_id: Execution ID (UUID)

        Raises:
            ValueError: If execution not found or access denied
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import executions
            >>> executions.delete("exec-123")
        """
        import asyncio

        context = get_context()

        # Get execution to verify access
        execution, error = asyncio.run(get_execution_handler(context, execution_id))

        if error:
            if error == "NotFound":
                raise ValueError(f"Execution not found: {execution_id}")
            elif error == "Forbidden":
                raise PermissionError(f"Access denied to execution: {execution_id}")
            else:
                raise ValueError(f"Error retrieving execution: {error}")

        if not execution:
            raise ValueError(f"Execution not found: {execution_id}")

        # Delete the execution
        repo = ExecutionRepository(context)
        repo.delete_execution(execution_id, execution.get("orgId"))
