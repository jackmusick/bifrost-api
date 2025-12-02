"""
Execution Logger
Logs workflow execution details using ExecutionLogRepository (PostgreSQL)
Large data (logs, results, snapshots) stored in Blob Storage to avoid size limits
"""

import json
import logging
from datetime import datetime
from typing import Any, TYPE_CHECKING
from uuid import UUID

from shared.blob_storage import get_blob_service
from src.models.schemas import ExecutionStatus

if TYPE_CHECKING:
    from shared.webpubsub_broadcaster import WebPubSubBroadcaster

logger = logging.getLogger(__name__)

# Size threshold for storing data in blob vs table (1KB)
BLOB_THRESHOLD_BYTES = 1024


class ExecutionLogger:
    """
    Logger for workflow executions.

    Uses PostgreSQL repositories for all database operations.
    """

    def __init__(self, context=None):
        self.blob_service = get_blob_service()
        self.context = context

    async def create_execution(
        self,
        execution_id: str,
        org_id: str | None,
        user_id: str,
        user_name: str,
        workflow_name: str,
        input_data: dict[str, Any],
        form_id: str | None = None,
        webpubsub_broadcaster: 'WebPubSubBroadcaster | None' = None
    ) -> dict[str, Any]:
        """
        Create execution record.

        Args:
            execution_id: Unique execution ID (UUID)
            org_id: Organization ID (None for GLOBAL scope)
            user_id: User ID who executed
            user_name: Display name of user who executed
            workflow_name: Name of workflow
            input_data: Input parameters
            form_id: Optional form ID if triggered by form

        Returns:
            Created execution entity (as dict for compatibility)
        """
        from sqlalchemy import select
        from src.core.database import get_session_factory
        from src.models import Execution
        from src.models.enums import ExecutionStatus as ExecutionStatusEnum

        session_factory = get_session_factory()
        exec_uuid = UUID(execution_id)
        org_uuid = UUID(org_id) if org_id and org_id != "GLOBAL" else None
        form_uuid = UUID(form_id) if form_id else None
        user_uuid = UUID(user_id) if user_id else None

        async with session_factory() as db:
            execution = Execution(
                id=exec_uuid,
                organization_id=org_uuid,
                workflow_name=workflow_name,
                status=ExecutionStatusEnum.RUNNING,
                executed_by=user_uuid,
                executed_by_name=user_name,
                parameters=input_data,  # ORM uses 'parameters', not 'input_data'
                form_id=form_uuid,
                started_at=datetime.utcnow(),
            )
            db.add(execution)
            await db.commit()
            await db.refresh(execution)

            logger.info(
                f"Created execution {execution_id} with all indexes",
                extra={"execution_id": execution_id, "org_id": org_id, "workflow": workflow_name}
            )

            # Broadcast new execution to history page (if enabled)
            if webpubsub_broadcaster:
                scope = org_id or "GLOBAL"
                await webpubsub_broadcaster.broadcast_execution_to_history(
                    execution_id=execution_id,
                    workflow_name=workflow_name,
                    status=execution.status.value,
                    executed_by=user_id,
                    executed_by_name=user_name,
                    scope=scope,
                    started_at=execution.started_at
                )

            # Return as dict for compatibility with existing code
            return {
                "id": str(execution.id),
                "workflowName": execution.workflow_name,
                "status": execution.status.value,
                "executedBy": str(execution.executed_by) if execution.executed_by else None,
                "executedByName": execution.executed_by_name,
                "startedAt": execution.started_at.isoformat() if execution.started_at else None,
                "completedAt": execution.completed_at.isoformat() if execution.completed_at else None,
                "inputData": execution.parameters,  # ORM uses 'parameters'
                "result": execution.result,
                "errorMessage": execution.error_message,
                "durationMs": execution.duration_ms,
                "orgId": str(execution.organization_id) if execution.organization_id else None,
                "formId": str(execution.form_id) if execution.form_id else None,
            }

    async def update_execution(
        self,
        execution_id: str,
        org_id: str | None,
        user_id: str,
        status: ExecutionStatus,
        result: dict[str, Any] | list[Any] | str | None = None,
        error_message: str | None = None,
        error_type: str | None = None,
        error_details: dict[str, Any] | None = None,
        duration_ms: int | None = None,
        integration_calls: list | None = None,
        logs: list | None = None,
        variables: dict[str, Any] | None = None,
        webpubsub_broadcaster: 'WebPubSubBroadcaster | None' = None
    ) -> dict[str, Any]:
        """
        Update execution record with results.

        Large data (logs, results, snapshots) automatically stored in blob storage.

        Args:
            execution_id: Execution ID
            org_id: Organization ID (None for GLOBAL scope)
            user_id: User ID
            status: Execution status
            result: Workflow result (dict, list, or str - if success)
            error_message: Error message (if failed)
            error_type: Error type (if failed)
            error_details: Error details (if failed)
            duration_ms: Duration in milliseconds
            integration_calls: Integration call tracking
            logs: Workflow logs
            variables: Workflow variables

        Returns:
            Updated execution entity (as dict)
        """
        from sqlalchemy import select
        from src.core.database import get_session_factory
        from src.models import Execution
        from src.models.enums import ExecutionStatus as ExecutionStatusEnum

        # Handle result storage (blob for large, table for small)
        result_in_blob = False
        stored_result = result
        if result is not None:
            # Convert result to JSON string if it's not already a string
            result_json = result if isinstance(result, str) else json.dumps(result)
            result_size = len(result_json.encode('utf-8'))

            if result_size > BLOB_THRESHOLD_BYTES:
                # Store in blob storage
                await self.blob_service.upload_result(execution_id, result)
                result_in_blob = True
                stored_result = None  # Don't store inline
                logger.info(
                    f"Stored large result in blob storage ({result_size} bytes)",
                    extra={"execution_id": execution_id}
                )

        # Store large data in blob storage
        if logs:
            await self.blob_service.upload_logs(execution_id, logs)
            logger.info(
                f"Stored logs in blob storage ({len(logs)} entries)",
                extra={"execution_id": execution_id}
            )

        if variables:
            await self.blob_service.upload_variables(execution_id, variables)
            logger.info(
                f"Stored variables in blob storage ({len(variables)} variables)",
                extra={"execution_id": execution_id}
            )

        session_factory = get_session_factory()
        exec_uuid = UUID(execution_id)

        # Map status to enum
        status_enum = ExecutionStatusEnum(status.value)

        async with session_factory() as db:
            result_query = await db.execute(
                select(Execution).where(Execution.id == exec_uuid)
            )
            execution = result_query.scalar_one_or_none()

            if not execution:
                raise ValueError(f"Execution not found: {execution_id}")

            execution.status = status_enum
            execution.result = stored_result
            execution.error_message = error_message
            execution.duration_ms = duration_ms
            execution.result_in_blob = result_in_blob
            if status in [ExecutionStatus.SUCCESS, ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT, ExecutionStatus.COMPLETED_WITH_ERRORS]:
                execution.completed_at = datetime.utcnow()

            await db.commit()
            await db.refresh(execution)

            logger.info(
                f"Updated execution {execution_id} (status={status.value})",
                extra={"execution_id": execution_id, "status": status.value}
            )

            # Broadcast execution update via Web PubSub (if enabled)
            if webpubsub_broadcaster:
                scope = org_id or "GLOBAL"
                is_complete = status in [
                    ExecutionStatus.SUCCESS,
                    ExecutionStatus.FAILED,
                    ExecutionStatus.TIMEOUT,
                    ExecutionStatus.COMPLETED_WITH_ERRORS
                ]
                await webpubsub_broadcaster.broadcast_execution_update(
                    execution_id=execution_id,
                    status=status.value,
                    executed_by=user_id,
                    scope=scope,
                    latest_logs=None,
                    is_complete=is_complete
                )

                # Broadcast to history page
                await webpubsub_broadcaster.broadcast_execution_to_history(
                    execution_id=execution_id,
                    workflow_name=execution.workflow_name,
                    status=status.value,
                    executed_by=user_id,
                    executed_by_name=execution.executed_by_name,
                    scope=scope,
                    started_at=execution.started_at,
                    completed_at=execution.completed_at,
                    duration_ms=duration_ms
                )

            # Return as dict for compatibility
            return {
                "id": str(execution.id),
                "workflowName": execution.workflow_name,
                "status": execution.status.value,
                "executedBy": str(execution.executed_by) if execution.executed_by else None,
                "executedByName": execution.executed_by_name,
                "startedAt": execution.started_at.isoformat() if execution.started_at else None,
                "completedAt": execution.completed_at.isoformat() if execution.completed_at else None,
                "inputData": execution.parameters,  # ORM uses 'parameters'
                "result": execution.result,
                "errorMessage": execution.error_message,
                "durationMs": execution.duration_ms,
                "orgId": str(execution.organization_id) if execution.organization_id else None,
                "formId": str(execution.form_id) if execution.form_id else None,
            }


# Singleton instance
_execution_logger = None


def get_execution_logger() -> ExecutionLogger:
    """Get singleton ExecutionLogger instance."""
    global _execution_logger
    if _execution_logger is None:
        _execution_logger = ExecutionLogger()
    return _execution_logger
