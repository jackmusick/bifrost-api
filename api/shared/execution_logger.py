"""
Execution Logger
Logs workflow execution details using ExecutionRepository
Large data (logs, results, snapshots) stored in Blob Storage to avoid size limits
"""

import json
import logging
from typing import Any

from shared.blob_storage import get_blob_service
from shared.models import ExecutionStatus
from shared.repositories.executions import ExecutionRepository

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

    def create_execution(
        self,
        execution_id: str,
        org_id: str | None,
        user_id: str,
        user_name: str,
        workflow_name: str,
        input_data: dict[str, Any],
        form_id: str | None = None
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
        execution_model = self.repository.create_execution(
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

        # Return as dict for compatibility with existing code
        return execution_model.model_dump()

    def update_execution(
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
        state_snapshots: list | None = None,
        integration_calls: list | None = None,
        logs: list | None = None,
        variables: dict[str, Any] | None = None
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
            state_snapshots: State checkpoints
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
                self.blob_service.upload_result(execution_id, result)
                result_in_blob = True
                result = None  # Don't store inline
                logger.info(
                    f"Stored large result in blob storage ({result_size} bytes)",
                    extra={"execution_id": execution_id}
                )

        # Store large data in blob storage
        if logs:
            self.blob_service.upload_logs(execution_id, logs)
            logger.info(
                f"Stored logs in blob storage ({len(logs)} entries)",
                extra={"execution_id": execution_id}
            )

        if state_snapshots:
            self.blob_service.upload_snapshot(execution_id, state_snapshots)
            logger.info(
                "Stored snapshots in blob storage",
                extra={"execution_id": execution_id}
            )

        # Delegate to repository (handles primary record + ALL indexes!)
        execution_model = self.repository.update_execution(
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
