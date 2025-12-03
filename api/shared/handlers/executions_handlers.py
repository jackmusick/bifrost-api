"""
Executions Handlers

Business logic for execution history operations.
Used by both HTTP handlers and Bifrost SDK.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import desc, select


if TYPE_CHECKING:
    from shared.context import ExecutionContext
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def _get_db_session() -> "AsyncSession":
    """Get a database session for handler use."""
    from src.core.database import get_session_factory

    async_session = get_session_factory()
    return async_session()


async def list_executions_handler(
    context: "ExecutionContext",
    workflow_name: str | None = None,
    status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
    continuation_token: str | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    """
    List workflow executions with filtering.

    Args:
        context: Execution context with user info
        workflow_name: Filter by workflow name
        status: Filter by status
        start_date: Filter by start date (ISO format)
        end_date: Filter by end date (ISO format)
        limit: Maximum results
        continuation_token: Pagination token

    Returns:
        Tuple of (executions list, next continuation token)
    """
    from datetime import datetime

    from src.models import Execution as ExecutionModel

    async with await _get_db_session() as db:
        query = select(ExecutionModel)

        # Organization scoping
        if context.org_id:
            try:
                org_uuid = UUID(context.org_id)
                query = query.where(ExecutionModel.organization_id == org_uuid)
            except (ValueError, TypeError):
                pass

        # Non-admins can only see their own executions
        if not context.is_platform_admin:
            query = query.where(ExecutionModel.executed_by == context.email)

        # Filters
        if workflow_name:
            query = query.where(ExecutionModel.workflow_name == workflow_name)

        if status:
            query = query.where(ExecutionModel.status == status)

        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                query = query.where(ExecutionModel.started_at >= start_dt)
            except ValueError:
                pass

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                query = query.where(ExecutionModel.started_at <= end_dt)
            except ValueError:
                pass

        # Order by newest first
        query = query.order_by(desc(ExecutionModel.started_at))

        # Pagination
        offset = 0
        if continuation_token:
            try:
                offset = int(continuation_token)
            except ValueError:
                pass

        query = query.offset(offset).limit(limit + 1)

        result = await db.execute(query)
        executions = list(result.scalars().all())

        # Check for more results
        has_more = len(executions) > limit
        if has_more:
            executions = executions[:limit]

        next_token = str(offset + limit) if has_more else None

        # Convert to dicts
        execution_list = [_execution_to_dict(e) for e in executions]

        return execution_list, next_token


async def get_execution_handler(
    context: "ExecutionContext",
    execution_id: str,
) -> tuple[dict[str, Any] | None, str | None]:
    """
    Get execution by ID.

    Args:
        context: Execution context with user info
        execution_id: Execution ID (UUID string)

    Returns:
        Tuple of (execution dict, error code) where error code is None on success
    """
    from src.models import Execution as ExecutionModel

    try:
        exec_uuid = UUID(execution_id)
    except ValueError:
        return None, "NotFound"

    async with await _get_db_session() as db:
        result = await db.execute(
            select(ExecutionModel).where(ExecutionModel.id == exec_uuid)
        )
        execution = result.scalar_one_or_none()

        if not execution:
            return None, "NotFound"

        # Authorization check - non-admins can only see their own
        if not context.is_platform_admin and execution.executed_by != context.email:
            return None, "Forbidden"

        return _execution_to_dict(execution), None


def _execution_to_dict(execution) -> dict[str, Any]:
    """Convert SQLAlchemy execution model to dict."""
    return {
        "execution_id": str(execution.id),
        "workflow_name": execution.workflow_name,
        "org_id": str(execution.organization_id) if execution.organization_id else None,
        "form_id": str(execution.form_id) if execution.form_id else None,
        "executed_by": str(execution.executed_by),
        "executed_by_name": execution.executed_by_name or str(execution.executed_by),
        "status": execution.status,
        "input_data": execution.parameters or {},
        "result": execution.result,
        "result_type": execution.result_type,
        "error_message": execution.error_message,
        "duration_ms": execution.duration_ms,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        "logs": None,  # Fetched separately
        "variables": execution.variables,
    }
