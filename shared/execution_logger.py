"""
Execution Logger
Logs workflow execution details using ExecutionRepository
Large data (logs, results, snapshots) stored in Blob Storage to avoid size limits
"""

import json
import logging
from typing import Any, TYPE_CHECKING

from shared.blob_storage import get_blob_service
from shared.models import ExecutionStatus
from shared.repositories.executions import ExecutionRepository

if TYPE_CHECKING:
    from shared.webpubsub_broadcaster import WebPubSubBroadcaster

logger = logging.getLogger(__name__)

# Size threshold for storing data in blob vs table (1KB)
BLOB_THRESHOLD_BYTES = 1024


class ExecutionLogger:
    """
    Logger for workflow executions.

    Uses ExecutionRepository for all database operations with automatic index management.
    """

    def __init__(self, context=None):
        self.repository = ExecutionRepository(context)
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
        Create execution record with automatic index management.

        Repository handles:
        - Primary record in Entities table
        - User index for "my executions" queries
        - Workflow index for "executions by workflow" queries
        - Form index for "executions from form" queries

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
        # Delegate to repository (handles all indexes automatically!)
        execution_model = await self.repository.create_execution(
            execution_id=execution_id,
            org_id=org_id,
            user_id=user_id,
            user_name=user_name,
            workflow_name=workflow_name,
            input_data=input_data,
            form_id=form_id
        )

        logger.info(
            f"Created execution {execution_id} via repository with all indexes",
            extra={"execution_id": execution_id, "org_id": org_id, "workflow": workflow_name}
        )

        # Broadcast new execution to history page (if enabled)
        if webpubsub_broadcaster:
            scope = org_id or "GLOBAL"
            await webpubsub_broadcaster.broadcast_execution_to_history(
                execution_id=execution_id,
                workflow_name=workflow_name,
                status=execution_model.status.value,  # Use actual DB status (RUNNING)
                executed_by=user_id,
                executed_by_name=user_name,
                scope=scope,
                started_at=execution_model.startedAt
            )

        # Return as dict for compatibility with existing code
        return execution_model.model_dump()

    async def update_execution(
        self,
        execution_id: str,
        org_id: str | None,
        user_id: str,
        status: ExecutionStatus,
        result: dict[str, Any] | str | None = None,
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
        Update execution record with results and automatic index updates.

        Large data (logs, results, snapshots) automatically stored in blob storage.
        Repository updates ALL indexes (user, workflow, form) with display fields.

        Args:
            execution_id: Execution ID
            org_id: Organization ID (None for GLOBAL scope)
            user_id: User ID
            status: Execution status
            result: Workflow result (dict or str - if success)
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
        # Handle result storage (blob for large, table for small)
        result_in_blob = False
        if result is not None:
            result_json = json.dumps(result) if isinstance(result, dict) else result
            result_size = len(result_json.encode('utf-8'))

            if result_size > BLOB_THRESHOLD_BYTES:
                # Store in blob storage
                await self.blob_service.upload_result(execution_id, result)
                result_in_blob = True
                result = None  # Don't store inline
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

        # Delegate to repository (handles primary record + ALL indexes!)
        execution_model = await self.repository.update_execution(
            execution_id=execution_id,
            org_id=org_id,
            user_id=user_id,
            status=status,
            result=result,
            error_message=error_message,
            duration_ms=duration_ms,
            result_in_blob=result_in_blob
        )

        logger.info(
            f"Updated execution {execution_id} via repository (status={status.value}, all indexes updated)",
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
            # Broadcast completion status ONLY (logs already streamed in real-time)
            # Logs are persisted in ExecutionLogs table and available via HTTP API
            # Client can fetch logs from /api/executions/{id}/logs if needed
            await webpubsub_broadcaster.broadcast_execution_update(
                execution_id=execution_id,
                status=status.value,
                executed_by=user_id,
                scope=scope,
                latest_logs=None,  # Don't re-send logs (already streamed + in Table Storage)
                is_complete=is_complete
            )

            # Broadcast to history page for ALL status changes (PENDING → RUNNING → completion)
            await webpubsub_broadcaster.broadcast_execution_to_history(
                execution_id=execution_id,
                workflow_name=execution_model.workflowName,
                status=status.value,
                executed_by=user_id,
                executed_by_name=execution_model.executedByName,
                scope=scope,
                started_at=execution_model.startedAt,
                completed_at=execution_model.completedAt,
                duration_ms=duration_ms
            )

        # Return as dict for compatibility
        return execution_model.model_dump()


# Singleton instance
_execution_logger = None


def get_execution_logger() -> ExecutionLogger:
    """Get singleton ExecutionLogger instance."""
    global _execution_logger
    if _execution_logger is None:
        _execution_logger = ExecutionLogger()
    return _execution_logger
