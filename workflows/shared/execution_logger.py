"""
Execution Logger
Logs workflow execution details to Table Storage with dual-indexing
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from shared.storage import get_table_storage_service
from shared.models import ExecutionStatus

logger = logging.getLogger(__name__)


class ExecutionLogger:
    """
    Logger for workflow executions.
    
    Handles dual-indexed storage:
    - WorkflowExecutions table (partitioned by org_id)
    - UserExecutions table (partitioned by user_id)
    """

    def __init__(self):
        self.workflow_executions = get_table_storage_service("WorkflowExecutions")
        self.user_executions = get_table_storage_service("UserExecutions")

    async def create_execution(
        self,
        execution_id: str,
        org_id: str,
        user_id: str,
        workflow_name: str,
        input_data: Dict[str, Any],
        form_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create execution record in both tables.

        Args:
            execution_id: Unique execution ID (UUID)
            org_id: Organization ID
            user_id: User ID who executed
            workflow_name: Name of workflow
            input_data: Input parameters
            form_id: Optional form ID if triggered by form

        Returns:
            Created execution entity
        """
        started_at = datetime.utcnow()
        reverse_ts = self._get_reverse_timestamp(started_at)
        
        # Create entity for WorkflowExecutions (by org)
        workflow_exec_entity = {
            "PartitionKey": org_id,
            "RowKey": f"{reverse_ts}_{execution_id}",
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

        # Create entity for UserExecutions (by user)
        user_exec_entity = {
            "PartitionKey": user_id,
            "RowKey": f"{reverse_ts}_{execution_id}",
            "ExecutionId": execution_id,
            "OrgId": org_id,
            "WorkflowName": workflow_name,
            "Status": ExecutionStatus.RUNNING.value,
            "StartedAt": started_at.isoformat()
        }

        # Insert into both tables (dual-indexing)
        try:
            self.workflow_executions.insert_entity(workflow_exec_entity)
            logger.info(
                f"Created execution record in WorkflowExecutions: {execution_id}",
                extra={"execution_id": execution_id, "org_id": org_id}
            )

            self.user_executions.insert_entity(user_exec_entity)
            logger.info(
                f"Created execution record in UserExecutions: {execution_id}",
                extra={"execution_id": execution_id, "user_id": user_id}
            )

            return workflow_exec_entity

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
        org_id: str,
        user_id: str,
        status: ExecutionStatus,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        state_snapshots: Optional[list] = None,
        integration_calls: Optional[list] = None,
        logs: Optional[list] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update execution record with results.

        Args:
            execution_id: Execution ID
            org_id: Organization ID
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
        
        # Get existing entity to get RowKey (need reverse timestamp)
        existing = await self._get_execution(org_id, execution_id)
        if not existing:
            raise ValueError(f"Execution {execution_id} not found")
        
        row_key = existing['RowKey']

        # Update WorkflowExecutions
        workflow_exec_update = {
            "PartitionKey": org_id,
            "RowKey": row_key,
            "Status": status.value,
            "CompletedAt": completed_at.isoformat(),
            "DurationMs": duration_ms
        }

        if result is not None:
            workflow_exec_update["Result"] = json.dumps(result)
        
        if error_message:
            workflow_exec_update["ErrorMessage"] = error_message
            workflow_exec_update["ErrorType"] = error_type
            if error_details:
                workflow_exec_update["ErrorDetails"] = json.dumps(error_details)

        # Add state tracking data
        if state_snapshots:
            workflow_exec_update["StateSnapshots"] = json.dumps(state_snapshots)
        if integration_calls:
            workflow_exec_update["IntegrationCalls"] = json.dumps(integration_calls)
        if logs:
            workflow_exec_update["Logs"] = json.dumps(logs)
        if variables:
            workflow_exec_update["Variables"] = json.dumps(variables)

        # Update UserExecutions
        user_exec_update = {
            "PartitionKey": user_id,
            "RowKey": row_key,
            "Status": status.value
        }

        try:
            self.workflow_executions.update_entity(workflow_exec_update, mode="merge")
            logger.info(
                f"Updated execution in WorkflowExecutions: {execution_id} (status={status.value})",
                extra={"execution_id": execution_id, "status": status.value}
            )

            self.user_executions.update_entity(user_exec_update, mode="merge")
            logger.info(
                f"Updated execution in UserExecutions: {execution_id} (status={status.value})",
                extra={"execution_id": execution_id, "status": status.value}
            )

            return workflow_exec_update

        except Exception as e:
            logger.error(
                f"Failed to update execution record: {str(e)}",
                extra={"execution_id": execution_id},
                exc_info=True
            )
            raise

    async def _get_execution(self, org_id: str, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get execution entity by org_id and execution_id.
        
        Note: We need to query because RowKey includes reverse timestamp.
        """
        # Query WorkflowExecutions for this execution
        filter_str = f"PartitionKey eq '{org_id}' and ExecutionId eq '{execution_id}'"
        results = list(self.workflow_executions.query_entities(filter=filter_str))
        
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
