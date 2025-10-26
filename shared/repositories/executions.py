"""
Execution Repository
Manages workflow executions with display-optimized indexes

Indexes maintained:
1. Primary: execution:{reverse_ts}_{uuid} (Entities table)
2. User index: userexec:{user_id}:{execution_id} (Relationships table) - with display fields
3. Workflow index: workflowexec:{workflow_name}:{org_id}:{execution_id} (Relationships table) - with display fields
4. Form index: formexec:{form_id}:{execution_id} (Relationships table) - with display fields
5. Status index: status:{status}:{execution_id} (Relationships table) - for cleanup queries
"""

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, cast

from shared.models import ExecutionStatus, WorkflowExecution
from shared.async_storage import AsyncTableStorageService

from .base import BaseRepository

if TYPE_CHECKING:
    from shared.context import ExecutionContext

logger = logging.getLogger(__name__)


class ExecutionRepository(BaseRepository):
    """
    Repository for workflow executions

    Manages execution records with automatic index maintenance for:
    - User-based queries ("my executions")
    - Workflow-based queries ("all executions of WorkflowX")
    - Form-based queries ("all submissions of FormY")

    All indexes include display fields (WorkflowName, Status, StartedAt, etc.)
    to avoid secondary fetches when rendering tables.
    """

    def __init__(self, context: 'ExecutionContext | None' = None):
        super().__init__("Entities", context)
        self.relationships_service = AsyncTableStorageService("Relationships")

    async def create_execution(
        self,
        execution_id: str,
        org_id: str | None,
        user_id: str,
        user_name: str,
        workflow_name: str,
        input_data: dict,
        form_id: str | None = None
    ) -> WorkflowExecution:
        """
        Create execution with ALL indexes atomically

        Writes to:
        1. Entities table (primary record with full data)
        2. Relationships table (user index with display fields)
        3. Relationships table (workflow index with display fields)
        4. Relationships table (form index with display fields, if form_id provided)

        Args:
            execution_id: Unique execution ID (UUID)
            org_id: Organization ID or None for GLOBAL
            user_id: User ID who executed the workflow
            user_name: Display name of user
            workflow_name: Name of workflow being executed
            input_data: Input parameters dict
            form_id: Optional form ID if triggered from form

        Returns:
            WorkflowExecution model

        Raises:
            Exception: If any index creation fails
        """
        now = datetime.utcnow()
        reverse_ts = self._reverse_timestamp(now)
        partition_key = org_id or "GLOBAL"

        # 1. Primary execution record (Entities table) - FULL data
        execution_entity = {
            "PartitionKey": partition_key,
            "RowKey": f"execution:{reverse_ts}_{execution_id}",
            "ExecutionId": execution_id,
            "WorkflowName": workflow_name,
            "FormId": form_id,
            "ExecutedBy": user_id,
            "ExecutedByName": user_name,
            "Status": ExecutionStatus.RUNNING.value,
            "InputData": json.dumps(input_data),
            "StartedAt": now.isoformat(),
            "CompletedAt": None,
            "DurationMs": None,
            "Result": None,
            "ResultInBlob": False,
            "ErrorMessage": None,
        }

        # 2. User index - with DISPLAY fields for table view
        user_index_entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"userexec:{user_id}:{execution_id}",
            "ExecutionId": execution_id,
            "OrganizationId": org_id,
            # Display fields (avoid second fetch for table view)
            "WorkflowName": workflow_name,
            "FormId": form_id,
            "Status": ExecutionStatus.RUNNING.value,
            "StartedAt": now.isoformat(),
            "CompletedAt": None,
            "DurationMs": None,
            "ErrorMessage": None,
            "ExecutedByName": user_name,
        }

        # 3. Workflow index - with DISPLAY fields
        workflow_index_entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"workflowexec:{workflow_name}:{partition_key}:{execution_id}",
            "ExecutionId": execution_id,
            "OrganizationId": org_id,
            # Display fields
            "ExecutedBy": user_id,
            "ExecutedByName": user_name,
            "FormId": form_id,
            "Status": ExecutionStatus.RUNNING.value,
            "StartedAt": now.isoformat(),
            "CompletedAt": None,
            "DurationMs": None,
            "ErrorMessage": None,
        }

        # 4. Form index - with DISPLAY fields (only if form_id provided)
        form_index_entity = None
        if form_id:
            form_index_entity = {
                "PartitionKey": "GLOBAL",
                "RowKey": f"formexec:{form_id}:{execution_id}",
                "ExecutionId": execution_id,
                "OrganizationId": org_id,
                # Display fields
                "WorkflowName": workflow_name,
                "ExecutedBy": user_id,
                "ExecutedByName": user_name,
                "Status": ExecutionStatus.RUNNING.value,
                "StartedAt": now.isoformat(),
                "CompletedAt": None,
                "DurationMs": None,
                "ErrorMessage": None,
            }

        # 5. Status index - for cleanup queries (Pending/Running only)
        status_index_entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"status:{ExecutionStatus.RUNNING.value}:{execution_id}",
            "ExecutionId": execution_id,
            "OrganizationId": org_id,
            # Display fields for cleanup UI
            "WorkflowName": workflow_name,
            "ExecutedBy": user_id,
            "ExecutedByName": user_name,
            "Status": ExecutionStatus.RUNNING.value,
            "StartedAt": now.isoformat(),
            "UpdatedAt": now.isoformat(),
        }

        # Write all atomically (best effort)
        try:
            # Primary record
            await self.insert(execution_entity)

            # Indexes (in order of importance)
            await self.relationships_service.insert_entity(user_index_entity)
            await self.relationships_service.insert_entity(workflow_index_entity)
            await self.relationships_service.insert_entity(status_index_entity)

            if form_index_entity:
                await self.relationships_service.insert_entity(form_index_entity)

            index_count = 4 if form_id else 3
            logger.info(
                f"Created execution {execution_id} with {index_count} indexes "
                f"(workflow={workflow_name}, user={user_id}, form={form_id})"
            )

            return self._entity_to_model(execution_entity)

        except Exception as e:
            logger.error(
                f"Failed to create execution {execution_id} with indexes: {e}",
                exc_info=True
            )
            # TODO: Add cleanup/rollback logic
            raise

    async def update_execution(
        self,
        execution_id: str,
        org_id: str | None,
        user_id: str,
        status: ExecutionStatus,
        result: dict | str | None = None,
        error_message: str | None = None,
        duration_ms: int | None = None,
        result_in_blob: bool = False
    ) -> WorkflowExecution:
        """
        Update execution and ALL indexes with completion data

        Updates display fields in indexes so table views show current status
        without secondary fetches.

        Args:
            execution_id: Execution ID
            org_id: Organization ID
            user_id: User ID (for index lookup)
            status: New execution status
            result: Execution result (dict or string)
            error_message: Error message if failed
            duration_ms: Duration in milliseconds
            result_in_blob: Whether result is stored in blob storage

        Returns:
            Updated WorkflowExecution model
        """
        now = datetime.utcnow()
        partition_key = org_id or "GLOBAL"

        # Find primary execution record
        exec_filter = f"PartitionKey eq '{partition_key}' and ExecutionId eq '{execution_id}'"
        results = await self.query(exec_filter)

        if not results:
            raise ValueError(f"Execution {execution_id} not found in partition {partition_key}")

        execution_entity = results[0]

        # Extract metadata for index updates
        workflow_name = execution_entity.get("WorkflowName")
        form_id = execution_entity.get("FormId")
        old_status = execution_entity.get("Status", "")  # Capture BEFORE updating

        # Update primary record
        execution_entity["Status"] = status.value

        # Only set CompletedAt for terminal statuses (not Pending/Running)
        if status not in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
            execution_entity["CompletedAt"] = now.isoformat()
            execution_entity["DurationMs"] = duration_ms

        execution_entity["ErrorMessage"] = error_message
        execution_entity["ResultInBlob"] = result_in_blob

        if result and not result_in_blob:
            execution_entity["Result"] = json.dumps(result) if isinstance(result, dict) else result

        await self.update(execution_entity)

        # Update user index (so "my executions" table shows correct status!)
        try:
            user_index = await self.relationships_service.get_entity(
                "GLOBAL",
                f"userexec:{user_id}:{execution_id}"
            )
            if user_index:
                user_index["Status"] = status.value
                # Only set CompletedAt for terminal statuses
                if status not in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
                    user_index["CompletedAt"] = now.isoformat()
                    user_index["DurationMs"] = duration_ms
                user_index["ErrorMessage"] = error_message
                await self.relationships_service.update_entity(user_index)
        except Exception as e:
            logger.warning(f"Failed to update user index for {execution_id}: {e}")

        # Update workflow index
        try:
            workflow_index = await self.relationships_service.get_entity(
                "GLOBAL",
                f"workflowexec:{workflow_name}:{partition_key}:{execution_id}"
            )
            if workflow_index:
                workflow_index["Status"] = status.value
                # Only set CompletedAt for terminal statuses
                if status not in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
                    workflow_index["CompletedAt"] = now.isoformat()
                    workflow_index["DurationMs"] = duration_ms
                workflow_index["ErrorMessage"] = error_message
                await self.relationships_service.update_entity(workflow_index)
        except Exception as e:
            logger.warning(f"Failed to update workflow index for {execution_id}: {e}")

        # Update form index (if exists)
        if form_id:
            try:
                form_index = await self.relationships_service.get_entity(
                    "GLOBAL",
                    f"formexec:{form_id}:{execution_id}"
                )
                if form_index:
                    form_index["Status"] = status.value
                    # Only set CompletedAt for terminal statuses
                    if status not in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
                        form_index["CompletedAt"] = now.isoformat()
                        form_index["DurationMs"] = duration_ms
                    form_index["ErrorMessage"] = error_message
                    await self.relationships_service.update_entity(form_index)
            except Exception as e:
                logger.warning(f"Failed to update form index for {execution_id}: {e}")

        # Update status index - delete old status, create new if Pending/Running
        try:
            # Delete old status index if it was Pending or Running
            if old_status in [ExecutionStatus.PENDING.value, ExecutionStatus.RUNNING.value]:
                try:
                    await self.relationships_service.delete_entity(
                        "GLOBAL",
                        f"status:{old_status}:{execution_id}"
                    )
                except Exception:
                    pass  # Might not exist, that's okay

            # Create new status index only for Pending/Running
            if status in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
                status_index = {
                    "PartitionKey": "GLOBAL",
                    "RowKey": f"status:{status.value}:{execution_id}",
                    "ExecutionId": execution_id,
                    "OrganizationId": org_id,
                    "WorkflowName": workflow_name,
                    "ExecutedBy": user_id,
                    "ExecutedByName": execution_entity.get("ExecutedByName", ""),
                    "Status": status.value,
                    "StartedAt": execution_entity.get("StartedAt"),
                    "UpdatedAt": now.isoformat(),
                }
                await self.relationships_service.insert_entity(status_index)
        except Exception as e:
            logger.warning(f"Failed to update status index for {execution_id}: {e}")

        logger.info(
            f"Updated execution {execution_id} to status {status.value} "
            f"(duration={duration_ms}ms, indexes updated)"
        )

        return self._entity_to_model(execution_entity)

    async def get_execution(self, execution_id: str, org_id: str | None = None) -> WorkflowExecution | None:
        """
        Get full execution by ID

        Args:
            execution_id: Execution ID
            org_id: Organization ID (optional, will search GLOBAL if not provided)

        Returns:
            WorkflowExecution model or None if not found
        """
        partition_key = org_id or "GLOBAL"

        # Query by ExecutionId field
        exec_filter = f"PartitionKey eq '{partition_key}' and ExecutionId eq '{execution_id}'"
        results = await self.query(exec_filter)

        if not results:
            # Try GLOBAL if org_id was provided and failed
            if org_id:
                exec_filter = f"PartitionKey eq 'GLOBAL' and ExecutionId eq '{execution_id}'"
                results = await self.query(exec_filter)

        if results:
            return self._entity_to_model(results[0])

        return None

    async def list_executions_by_user(
        self,
        user_id: str,
        limit: int = 50
    ) -> list[WorkflowExecution]:
        """
        List executions for a specific user (optimized for table view)

        DEPRECATED: Use list_executions_by_user_paged() for better performance.

        Uses user index with display fields - NO secondary fetch needed!

        Args:
            user_id: User ID
            limit: Maximum number of results

        Returns:
            List of WorkflowExecution models with display fields populated
        """
        filter_query = (
            f"PartitionKey eq 'GLOBAL' and "
            f"RowKey ge 'userexec:{user_id}:' and "
            f"RowKey lt 'userexec:{user_id}~'"
        )

        # Use paginated query
        index_entities, _ = await self.relationships_service.query_entities_paged(
            filter=filter_query,
            results_per_page=limit
        )

        executions = []
        for entity in index_entities:
            # Parse datetime fields
            started_at = cast(datetime, self._parse_datetime(entity.get("StartedAt"), datetime.utcnow()))
            completed_at = self._parse_datetime(entity.get("CompletedAt"), None)

            # Parse status enum
            status_str = entity.get("Status", "Pending")
            status = ExecutionStatus(status_str) if status_str else ExecutionStatus.PENDING

            # Convert index entity directly to model (has display fields!)
            executions.append(WorkflowExecution(
                executionId=cast(str, entity.get("ExecutionId", "")),
                workflowName=cast(str, entity.get("WorkflowName", "")),
                orgId=entity.get("OrganizationId"),
                formId=entity.get("FormId"),
                status=status,
                executedBy=user_id,
                executedByName=cast(str, entity.get("ExecutedByName", user_id)),
                startedAt=started_at,
                completedAt=completed_at,
                durationMs=entity.get("DurationMs"),
                errorMessage=entity.get("ErrorMessage"),
                # Large fields NOT in index (null for table view)
                inputData={},
                result=None,
                resultType=None,
                logs=None
            ))

        logger.info(f"Found {len(executions)} executions for user {user_id}")
        return executions

    async def list_executions_by_user_paged(
        self,
        user_id: str,
        results_per_page: int = 50,
        continuation_token: dict | str | None = None
    ) -> tuple[list[WorkflowExecution], dict | str | None]:
        """
        List executions for a specific user with proper pagination.

        Uses user index with display fields - NO secondary fetch needed!

        Args:
            user_id: User ID
            results_per_page: Number of results per page (default 50, max 1000)
            continuation_token: Token from previous page (None for first page)

        Returns:
            Tuple of (list of WorkflowExecution models, next continuation token)
        """
        filter_query = (
            f"PartitionKey eq 'GLOBAL' and "
            f"RowKey ge 'userexec:{user_id}:' and "
            f"RowKey lt 'userexec:{user_id}~'"
        )

        # Query with pagination
        index_entities, next_token = await self.relationships_service.query_entities_paged(
            filter=filter_query,
            results_per_page=results_per_page,
            continuation_token=continuation_token
        )

        executions = []
        for entity in index_entities:
            # Parse datetime fields
            started_at = cast(datetime, self._parse_datetime(entity.get("StartedAt"), datetime.utcnow()))
            completed_at = self._parse_datetime(entity.get("CompletedAt"), None)

            # Parse status enum
            status_str = entity.get("Status", "Pending")
            status = ExecutionStatus(status_str) if status_str else ExecutionStatus.PENDING

            # Convert index entity directly to model (has display fields!)
            executions.append(WorkflowExecution(
                executionId=cast(str, entity.get("ExecutionId", "")),
                workflowName=cast(str, entity.get("WorkflowName", "")),
                orgId=entity.get("OrganizationId"),
                formId=entity.get("FormId"),
                status=status,
                executedBy=user_id,
                executedByName=cast(str, entity.get("ExecutedByName", user_id)),
                startedAt=started_at,
                completedAt=completed_at,
                durationMs=entity.get("DurationMs"),
                errorMessage=entity.get("ErrorMessage"),
                # Large fields NOT in index (null for table view)
                inputData={},
                result=None,
                resultType=None,
                logs=None
            ))

        logger.info(f"Found {len(executions)} executions for user {user_id} (paginated)")
        return executions, next_token

    async def list_executions_by_workflow(
        self,
        workflow_name: str,
        org_id: str | None = None,
        limit: int = 100
    ) -> list[WorkflowExecution]:
        """
        List executions for a specific workflow (optimized for table view)

        Uses workflow index with display fields - NO secondary fetch needed!

        Args:
            workflow_name: Workflow name
            org_id: Organization ID (None = GLOBAL)
            limit: Maximum number of results

        Returns:
            List of WorkflowExecution models with display fields populated
        """
        scope = org_id or "GLOBAL"

        filter_query = (
            f"PartitionKey eq 'GLOBAL' and "
            f"RowKey ge 'workflowexec:{workflow_name}:{scope}:' and "
            f"RowKey lt 'workflowexec:{workflow_name}:{scope}~'"
        )

        index_entities = await self.relationships_service.query_entities(filter_query)

        executions = []
        for entity in index_entities[:limit]:
            # Parse datetime fields
            started_at = cast(datetime, self._parse_datetime(entity.get("StartedAt"), datetime.utcnow()))
            completed_at = self._parse_datetime(entity.get("CompletedAt"), None)

            # Parse status enum
            status_str = entity.get("Status", "Pending")
            status = ExecutionStatus(status_str) if status_str else ExecutionStatus.PENDING

            executions.append(WorkflowExecution(
                executionId=cast(str, entity.get("ExecutionId", "")),
                workflowName=workflow_name,
                orgId=entity.get("OrganizationId"),
                formId=entity.get("FormId"),
                status=status,
                executedBy=cast(str, entity.get("ExecutedBy", "")),
                executedByName=cast(str, entity.get("ExecutedByName", "")),
                startedAt=started_at,
                completedAt=completed_at,
                durationMs=entity.get("DurationMs"),
                errorMessage=entity.get("ErrorMessage"),
                # Large fields NOT in index
                inputData={},
                result=None,
                resultType=None,
                logs=None
            ))

        logger.info(f"Found {len(executions)} executions for workflow {workflow_name}")
        return executions

    async def list_executions_by_form(
        self,
        form_id: str,
        limit: int = 100
    ) -> list[WorkflowExecution]:
        """
        List executions for a specific form (optimized for table view)

        Uses form index with display fields - NO secondary fetch needed!

        Args:
            form_id: Form ID
            limit: Maximum number of results

        Returns:
            List of WorkflowExecution models with display fields populated
        """
        filter_query = (
            f"PartitionKey eq 'GLOBAL' and "
            f"RowKey ge 'formexec:{form_id}:' and "
            f"RowKey lt 'formexec:{form_id}~'"
        )

        index_entities = await self.relationships_service.query_entities(filter_query)

        executions = []
        for entity in index_entities[:limit]:
            # Parse datetime fields
            started_at = cast(datetime, self._parse_datetime(entity.get("StartedAt"), datetime.utcnow()))
            completed_at = self._parse_datetime(entity.get("CompletedAt"), None)

            # Parse status enum
            status_str = entity.get("Status", "Pending")
            status = ExecutionStatus(status_str) if status_str else ExecutionStatus.PENDING

            executions.append(WorkflowExecution(
                executionId=cast(str, entity.get("ExecutionId", "")),
                workflowName=cast(str, entity.get("WorkflowName", "")),
                orgId=entity.get("OrganizationId"),
                formId=form_id,
                status=status,
                executedBy=cast(str, entity.get("ExecutedBy", "")),
                executedByName=cast(str, entity.get("ExecutedByName", "")),
                startedAt=started_at,
                completedAt=completed_at,
                durationMs=entity.get("DurationMs"),
                errorMessage=entity.get("ErrorMessage"),
                # Large fields NOT in index
                inputData={},
                result=None,
                resultType=None,
                logs=None
            ))

        logger.info(f"Found {len(executions)} executions for form {form_id}")
        return executions

    async def list_executions_for_org(
        self,
        org_id: str,
        limit: int = 100
    ) -> list[dict]:
        """
        List ALL executions for an organization (admin view)

        Returns raw entities for flexibility in filtering/sorting.

        Args:
            org_id: Organization ID
            limit: Maximum number of results

        Returns:
            List of execution entities (raw dicts)
        """
        filter_query = (
            f"PartitionKey eq '{org_id}' and "
            f"RowKey ge 'execution:' and RowKey lt 'execution;'"
        )

        entities = await self.query(filter_query)
        return entities[:limit]

    async def list_executions(self,
                        org_id: str | None = None,
                        limit: int = 50
    ) -> list[WorkflowExecution]:
        """
        List workflow executions across entire platform or within an organization.

        DEPRECATED: Use list_executions_paged() for better performance.
        This method loads all results into memory before limiting.

        Args:
            org_id: Optional organization ID to scope executions
            limit: Maximum number of results (default 50)

        Returns:
            List of WorkflowExecution models
        """
        partition_key = org_id or "GLOBAL"

        filter_query = (
            f"PartitionKey eq '{partition_key}' and "
            f"RowKey ge 'execution:' and RowKey lt 'execution;'"
        )

        # Use paginated query for better performance
        entities, _ = await self.query_paged(filter_query, results_per_page=limit)

        # Convert to model
        executions = []
        for entity in entities:
            execution = self._entity_to_model(entity)
            executions.append(execution)

        return executions

    async def list_executions_paged(
        self,
        org_id: str | None = None,
        results_per_page: int = 50,
        continuation_token: dict | str | None = None
    ) -> tuple[list[WorkflowExecution], dict | str | None]:
        """
        List workflow executions with proper pagination.

        Args:
            org_id: Optional organization ID to scope executions
            results_per_page: Number of results per page (default 50, max 1000)
            continuation_token: Token from previous page (None for first page)

        Returns:
            Tuple of (list of WorkflowExecution models, next continuation token)
        """
        partition_key = org_id or "GLOBAL"

        filter_query = (
            f"PartitionKey eq '{partition_key}' and "
            f"RowKey ge 'execution:' and RowKey lt 'execution;'"
        )

        # Query with pagination
        entities, next_token = await self.query_paged(
            filter_query,
            results_per_page=results_per_page,
            continuation_token=continuation_token
        )

        # Convert to models
        executions = [self._entity_to_model(entity) for entity in entities]

        return executions, next_token

    async def get_stuck_executions(
        self,
        pending_timeout_minutes: int = 10,
        running_timeout_minutes: int = 30
    ) -> list[WorkflowExecution]:
        """
        Get executions stuck in Pending or Running status.

        Uses status index in Relationships table for efficient queries.
        Only queries Pending and Running status indexes (no full table scan).

        Args:
            pending_timeout_minutes: Timeout for Pending status (default: 10)
            running_timeout_minutes: Timeout for Running status (default: 30)

        Returns:
            List of stuck executions with display fields populated
        """
        now = datetime.utcnow()
        stuck_executions: list[WorkflowExecution] = []

        # Query status indexes for Pending and Running executions
        for status_value, timeout_minutes in [
            (ExecutionStatus.PENDING.value, pending_timeout_minutes),
            (ExecutionStatus.RUNNING.value, running_timeout_minutes)
        ]:
            # Query status index using range query
            filter_query = (
                f"PartitionKey eq 'GLOBAL' and "
                f"RowKey ge 'status:{status_value}:' and "
                f"RowKey lt 'status:{status_value}~'"
            )

            try:
                status_entities = await self.relationships_service.query_entities(filter_query)

                for entity in status_entities:
                    try:
                        # Use StartedAt to determine age (more accurate than UpdatedAt)
                        # This catches executions that never progressed from initial creation
                        started_at_str = entity.get("StartedAt")
                        if not started_at_str:
                            # Fallback to UpdatedAt if StartedAt is missing (shouldn't happen)
                            started_at_str = entity.get("UpdatedAt")
                            if not started_at_str:
                                continue

                        # Parse timestamp (with non-None default, should never be None)
                        started_at = self._parse_datetime(started_at_str, now)
                        if started_at is None:
                            continue  # Skip if parsing failed
                        age_minutes = (now - started_at).total_seconds() / 60

                        # Check if stuck based on timeout
                        if age_minutes > timeout_minutes:
                            # Build WorkflowExecution from index fields (use already-parsed started_at)
                            execution_started_at = started_at

                            execution = WorkflowExecution(
                                executionId=cast(str, entity.get("ExecutionId", "")),
                                workflowName=cast(str, entity.get("WorkflowName", "")),
                                orgId=entity.get("OrganizationId"),
                                formId=None,  # Not in status index
                                status=ExecutionStatus(status_value),
                                executedBy=cast(str, entity.get("ExecutedBy", "")),
                                executedByName=cast(str, entity.get("ExecutedByName", "")),
                                startedAt=execution_started_at,
                                completedAt=None,
                                durationMs=None,
                                errorMessage=None,
                                # Large fields NOT in index
                                inputData={},
                                result=None,
                                resultType=None,
                                logs=None
                            )
                            stuck_executions.append(execution)

                    except Exception as e:
                        logger.warning(
                            f"Error parsing status index entity: {e}",
                            extra={
                                "error": str(e),
                                "execution_id": entity.get("ExecutionId"),
                            }
                        )
                        continue

            except Exception as e:
                logger.error(
                    f"Error querying status index for {status_value}: {e}",
                    exc_info=True
                )

        logger.info(f"Found {len(stuck_executions)} stuck executions")
        return stuck_executions

    def _reverse_timestamp(self, dt: datetime) -> str:
        """
        Create reverse timestamp for sorting executions newest-first

        Args:
            dt: Datetime to convert

        Returns:
            Reverse timestamp string (9999999999999 - timestamp_ms)
        """
        timestamp_ms = int(dt.timestamp() * 1000)
        reverse = 9999999999999 - timestamp_ms
        return str(reverse)

    def _entity_to_model(self, entity: dict) -> WorkflowExecution:
        """
        Convert entity dict to WorkflowExecution model

        Args:
            entity: Entity dictionary from table storage

        Returns:
            WorkflowExecution model
        """
        # Parse InputData from JSON string
        input_data = entity.get("InputData")
        if input_data and isinstance(input_data, str):
            try:
                input_data = json.loads(input_data)
            except json.JSONDecodeError:
                input_data = {}
        elif not input_data:
            input_data = {}

        # Parse Result if inline (not in blob)
        result = None
        result_type = None
        if not entity.get("ResultInBlob") and entity.get("Result"):
            result_str = entity.get("Result")
            if isinstance(result_str, str):
                try:
                    result = json.loads(result_str)
                    result_type = "json"
                except json.JSONDecodeError:
                    result = result_str
                    # Check for HTML (trim whitespace before checking)
                    trimmed = result_str.strip()
                    result_type = "html" if (trimmed.startswith("<") and ">" in trimmed) else "text"
            else:
                result = result_str
                result_type = "json"

        # Parse datetime fields
        started_at = cast(datetime, self._parse_datetime(entity.get("StartedAt"), datetime.utcnow()))
        completed_at = self._parse_datetime(entity.get("CompletedAt"), None)

        # Parse status enum
        status_str = entity.get("Status", "Pending")
        status = ExecutionStatus(status_str) if status_str else ExecutionStatus.PENDING

        # Parse durationMs (can be int, str, or None from Table Storage)
        duration_ms = entity.get("DurationMs")
        if duration_ms is not None and isinstance(duration_ms, str):
            try:
                duration_ms = int(duration_ms)
            except (ValueError, TypeError):
                duration_ms = None

        return WorkflowExecution(
            executionId=cast(str, entity.get("ExecutionId", "")),
            workflowName=cast(str, entity.get("WorkflowName", "")),
            orgId=entity.get("PartitionKey"),
            formId=entity.get("FormId"),
            executedBy=cast(str, entity.get("ExecutedBy", "")),
            executedByName=cast(str, entity.get("ExecutedByName", "")),
            status=status,
            inputData=input_data,
            result=result,
            resultType=result_type,
            errorMessage=entity.get("ErrorMessage"),
            durationMs=duration_ms,
            startedAt=started_at,
            completedAt=completed_at,
            logs=None  # Logs fetched separately from blob storage
        )
