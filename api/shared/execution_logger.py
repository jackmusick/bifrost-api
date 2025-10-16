"""
Execution Logger
Logs workflow execution details to Table Storage with dual-indexing
"""

import json
import logging
from datetime import datetime
from typing import Any

from shared.models import ExecutionStatus
from shared.storage import get_table_storage_service

logger = logging.getLogger(__name__)


class ExecutionLogger:
    """
    Logger for workflow executions.

    Uses consolidated table structure:
    - Entities table: Stores full execution records (partitioned by org_id or GLOBAL)
    - Relationships table: Stores user→execution index for fast lookup
    """

    def __init__(self):
        self.entities = get_table_storage_service("Entities")
        self.relationships = get_table_storage_service("Relationships")

    async def create_execution(
        self,
        execution_id: str,
        org_id: str | None,
        user_id: str,
        workflow_name: str,
        input_data: dict[str, Any],
        form_id: str | None = None
    ) -> dict[str, Any]:
        """
        Create execution record in Entities and user index in Relationships.

        Args:
            execution_id: Unique execution ID (UUID)
            org_id: Organization ID (None for GLOBAL scope)
            user_id: User ID who executed
            workflow_name: Name of workflow
            input_data: Input parameters
            form_id: Optional form ID if triggered by form

        Returns:
            Created execution entity
        """
        started_at = datetime.utcnow()
        reverse_ts = self._get_reverse_timestamp(started_at)

        # Use "GLOBAL" partition for None org_id (platform admin in global scope)
        partition_key = org_id or "GLOBAL"

        # Create entity for Entities table (full execution record)
        execution_entity = {
            "PartitionKey": partition_key,
            "RowKey": f"execution:{reverse_ts}_{execution_id}",
            "ExecutionId": execution_id,
            "WorkflowName": workflow_name,
            "FormId": form_id,
            "ExecutedBy": user_id,
            "Status": ExecutionStatus.RUNNING.value,
            "InputData": json.dumps(input_data),
            "Result": None,
            "ErrorMessage": None,
            "ErrorType": None,
            "ErrorDetails": None,
            "DurationMs": None,
            "StartedAt": started_at.isoformat(),
            "CompletedAt": None,
            "StateSnapshots": None,
            "IntegrationCalls": None,
            "Logs": None,
            "Variables": None
        }

        # Create dual index in Relationships table (user→execution lookup)
        user_exec_relationship = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"userexec:{user_id}:{execution_id}",
            "ExecutionId": execution_id,
            "UserId": user_id,
            "OrgId": org_id or "GLOBAL",
            "WorkflowName": workflow_name,
            "Status": ExecutionStatus.RUNNING.value,
            "StartedAt": started_at.isoformat()
        }

        # Insert into both tables (dual-indexing)
        try:
            self.entities.insert_entity(execution_entity)
            logger.info(
                f"Created execution record in Entities: {execution_id}",
                extra={"execution_id": execution_id, "org_id": org_id}
            )

            self.relationships.insert_entity(user_exec_relationship)
            logger.info(
                f"Created execution index in Relationships: {execution_id}",
                extra={"execution_id": execution_id, "user_id": user_id}
            )

            return execution_entity

        except Exception as e:
            logger.error(
                f"Failed to create execution record: {str(e)}",
                extra={"execution_id": execution_id},
                exc_info=True
            )
            raise

    async def update_execution(
        self,
        execution_id: str,
        org_id: str | None,
        user_id: str,
        status: ExecutionStatus,
        result: dict[str, Any] | None = None,
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
        Update execution record with results.

        Args:
            execution_id: Execution ID
            org_id: Organization ID (None for GLOBAL scope)
            user_id: User ID
            status: Execution status
            result: Workflow result (if success)
            error_message: Error message (if failed)
            error_type: Error type (if failed)
            error_details: Error details (if failed)
            duration_ms: Duration in milliseconds
            state_snapshots: State checkpoints
            integration_calls: Integration call tracking
            logs: Workflow logs
            variables: Workflow variables

        Returns:
            Updated execution entity
        """
        completed_at = datetime.utcnow()

        # Use "GLOBAL" partition for None org_id
        partition_key = org_id or "GLOBAL"

        # Get existing entity to get RowKey (need reverse timestamp)
        existing = await self._get_execution(org_id, execution_id)
        if not existing:
            raise ValueError(f"Execution {execution_id} not found")

        row_key = existing['RowKey']

        # Update Entities table (full execution record)
        execution_update = {
            "PartitionKey": partition_key,
            "RowKey": row_key,
            "Status": status.value,
            "CompletedAt": completed_at.isoformat(),
            "DurationMs": duration_ms
        }

        if result is not None:
            execution_update["Result"] = json.dumps(result)

        if error_message:
            execution_update["ErrorMessage"] = error_message
            execution_update["ErrorType"] = error_type
            if error_details:
                execution_update["ErrorDetails"] = json.dumps(error_details)

        # Add state tracking data
        if state_snapshots:
            execution_update["StateSnapshots"] = json.dumps(state_snapshots)
        if integration_calls:
            execution_update["IntegrationCalls"] = json.dumps(integration_calls)
        if logs:
            execution_update["Logs"] = json.dumps(logs)
        if variables:
            execution_update["Variables"] = json.dumps(variables)

        # Update Relationships table (user index)
        user_exec_update = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"userexec:{user_id}:{execution_id}",
            "Status": status.value
        }

        try:
            self.entities.update_entity(execution_update, mode="merge")
            logger.info(
                f"Updated execution in Entities: {execution_id} (status={status.value})",
                extra={"execution_id": execution_id, "status": status.value}
            )

            self.relationships.update_entity(user_exec_update, mode="merge")
            logger.info(
                f"Updated execution index in Relationships: {execution_id} (status={status.value})",
                extra={"execution_id": execution_id, "status": status.value}
            )

            return execution_update

        except Exception as e:
            logger.error(
                f"Failed to update execution record: {str(e)}",
                extra={"execution_id": execution_id},
                exc_info=True
            )
            raise

    async def _get_execution(self, org_id: str | None, execution_id: str) -> dict[str, Any] | None:
        """
        Get execution entity by org_id and execution_id.

        Note: We need to query because RowKey includes reverse timestamp.

        Args:
            org_id: Organization ID (None for GLOBAL scope)
            execution_id: Execution ID
        """
        # Use "GLOBAL" partition for None org_id
        partition_key = org_id or "GLOBAL"

        # Query Entities for this execution
        filter_str = f"PartitionKey eq '{partition_key}' and ExecutionId eq '{execution_id}'"
        results = list(self.entities.query_entities(filter=filter_str))

        if results:
            return results[0]
        return None

    def _get_reverse_timestamp(self, dt: datetime) -> int:
        """
        Calculate reverse timestamp for descending order in Table Storage.

        Formula: 9999999999999 - timestamp_in_milliseconds

        This ensures newest records appear first when querying by partition key.
        """
        timestamp_ms = int(dt.timestamp() * 1000)
        return 9999999999999 - timestamp_ms


# Singleton instance
_execution_logger = None


def get_execution_logger() -> ExecutionLogger:
    """Get singleton ExecutionLogger instance."""
    global _execution_logger
    if _execution_logger is None:
        _execution_logger = ExecutionLogger()
    return _execution_logger
