"""
Consumer Helper Functions

Shared utilities for RabbitMQ consumers that need to interact
with the database and other services.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update

from src.core.database import get_session_factory
from src.models.database import Execution as ExecutionModel

logger = logging.getLogger(__name__)


async def get_execution_status(execution_id: str, org_id: str | None) -> str | None:
    """
    Get the current status of an execution.

    Args:
        execution_id: Execution ID
        org_id: Organization ID (for scoping)

    Returns:
        Status string or None if not found
    """
    session_factory = get_session_factory()
    async with session_factory() as db:
        result = await db.execute(
            select(ExecutionModel.status).where(ExecutionModel.id == UUID(execution_id))
        )
        status = result.scalar_one_or_none()
        return status


async def update_execution(
    execution_id: str,
    org_id: str | None,
    user_id: str,
    status: Any,  # ExecutionStatus enum
    result: Any = None,
    error_message: str | None = None,
    error_type: str | None = None,
    duration_ms: int | None = None,
    logs: list[dict] | None = None,
    variables: dict | None = None,
) -> None:
    """
    Update an execution record.

    Args:
        execution_id: Execution ID
        org_id: Organization ID
        user_id: User who initiated the execution
        status: New status
        result: Execution result
        error_message: Error message if failed
        error_type: Error type if failed
        duration_ms: Execution duration in milliseconds
        logs: Execution logs
        variables: Runtime variables
    """
    session_factory = get_session_factory()
    async with session_factory() as db:
        # Get status value if it's an enum
        status_value = status.value if hasattr(status, "value") else status

        # Build update values
        update_values = {
            "status": status_value,
            "updated_at": datetime.utcnow(),
        }

        if result is not None:
            update_values["result"] = result
            update_values["result_type"] = type(result).__name__

        if error_message is not None:
            update_values["error_message"] = error_message

        if error_type is not None:
            update_values["error_type"] = error_type

        if duration_ms is not None:
            update_values["duration_ms"] = duration_ms
            update_values["completed_at"] = datetime.utcnow()

        if logs is not None:
            update_values["logs"] = logs

        if variables is not None:
            update_values["variables"] = variables

        # Execute update
        await db.execute(
            update(ExecutionModel)
            .where(ExecutionModel.id == UUID(execution_id))
            .values(**update_values)
        )
        await db.commit()

        logger.debug(f"Updated execution {execution_id} to status {status_value}")
