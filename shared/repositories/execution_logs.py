"""
Execution Logs Repository
Stores real-time execution logs in Table Storage for reliable retrieval
"""

import os
import uuid
from datetime import datetime
from typing import Any

from azure.data.tables import TableClient
from shared.async_storage import AsyncTableStorageService


class ExecutionLogsRepository:
    """
    Repository for execution logs.

    Partition Strategy: ExecutionId (allows fast retrieval of all logs for an execution)
    Row Key Strategy: ISO timestamp + sequence (ensures chronological ordering)

    Each log entry has a unique ExecutionLogId for client-side deduplication.

    Uses dual clients:
    - Synchronous TableClient for append_log() (real-time, immediate writes)
    - Async AsyncTableStorageService for read operations (efficient async queries)
    """

    def __init__(self):
        # Async client for read operations
        self.table_service = AsyncTableStorageService("ExecutionLogs")

        # Synchronous client for real-time log writes
        connection_string = os.environ.get("AzureWebJobsStorage")
        if not connection_string:
            raise ValueError("AzureWebJobsStorage environment variable not set")
        self.sync_table_client = TableClient.from_connection_string(
            conn_str=connection_string,
            table_name="ExecutionLogs"
        )

        # Ensure table exists
        try:
            self.sync_table_client.create_table()
        except Exception:
            pass  # Table already exists

        self._sequence_counters: dict[str, int] = {}  # In-memory sequence tracking

    async def close(self):
        """Close the underlying table service clients."""
        await self.table_service.close()
        self.sync_table_client.close()

    def append_log(
        self,
        execution_id: str,
        level: str,
        message: str,
        source: str = "workflow"
    ) -> dict[str, Any]:
        """
        Append a log entry for an execution (synchronous, immediate write).

        This method uses synchronous Table Storage client to ensure logs are
        written immediately for real-time streaming. Called from logging.Handler.emit()
        which must be synchronous.

        Each log gets a unique ExecutionLogId for client deduplication.

        Args:
            execution_id: Execution ID
            level: Log level (INFO, WARNING, ERROR, DEBUG)
            message: Log message
            source: Log source (workflow, script, system)

        Returns:
            Created log entity with ExecutionLogId
        """
        now = datetime.utcnow()
        timestamp_iso = now.isoformat() + "Z"

        # Generate sequence number for this execution (handles same-millisecond logs)
        sequence = self._get_next_sequence(execution_id, timestamp_iso)

        # Row key format: timestamp + sequence (zero-padded for sorting)
        # Example: "2025-01-28T19:11:04.123456Z-0001"
        row_key = f"{timestamp_iso}-{sequence:04d}"

        log_id = str(uuid.uuid4())

        entity = {
            "PartitionKey": execution_id,
            "RowKey": row_key,
            "ExecutionLogId": log_id,
            "Timestamp": timestamp_iso,
            "Level": level.upper(),
            "Message": message,
            "Source": source,
            "CreatedAt": timestamp_iso
        }

        # Synchronous write for immediate persistence (real-time streaming)
        self.sync_table_client.upsert_entity(entity)
        return entity

    def _get_next_sequence(self, execution_id: str, timestamp: str) -> int:
        """
        Generate sequence number for logs in same millisecond.

        This prevents RowKey collisions when multiple logs occur in same millisecond.
        """
        key = f"{execution_id}:{timestamp}"
        if key not in self._sequence_counters:
            self._sequence_counters[key] = 0
        self._sequence_counters[key] += 1
        return self._sequence_counters[key]

    async def get_logs(
        self,
        execution_id: str,
        since_timestamp: str | None = None,
        limit: int = 1000
    ) -> list[dict[str, Any]]:
        """
        Get logs for an execution.

        Args:
            execution_id: Execution ID
            since_timestamp: Only fetch logs after this timestamp (ISO format)
            limit: Maximum number of logs to return

        Returns:
            List of log entries (sorted by timestamp ascending)
        """
        if since_timestamp:
            # Query range: RowKey > since_timestamp
            # Since RowKey format is "timestamp-sequence", we can compare directly
            query = f"PartitionKey eq '{execution_id}' and RowKey gt '{since_timestamp}'"
        else:
            # Get all logs for execution
            query = f"PartitionKey eq '{execution_id}'"

        results = await self.table_service.query_entities(query)

        # Already sorted by RowKey (timestamp + sequence)
        # Limit results
        return results[:limit]

    async def get_latest_logs(
        self,
        execution_id: str,
        count: int = 50
    ) -> list[dict[str, Any]]:
        """
        Get the latest N logs for an execution.

        Args:
            execution_id: Execution ID
            count: Number of latest logs to return

        Returns:
            List of latest log entries (sorted by timestamp descending)
        """
        query = f"PartitionKey eq '{execution_id}'"
        results = await self.table_service.query_entities(query)

        # Return last N logs (already sorted by RowKey ascending)
        return results[-count:] if len(results) > count else results

    async def count_logs(self, execution_id: str) -> int:
        """
        Count total logs for an execution.

        Args:
            execution_id: Execution ID

        Returns:
            Total number of logs
        """
        query = f"PartitionKey eq '{execution_id}'"
        results = await self.table_service.query_entities(query)
        return len(results)


# Singleton
_execution_logs_repo: ExecutionLogsRepository | None = None


def get_execution_logs_repository() -> ExecutionLogsRepository:
    """Get singleton ExecutionLogsRepository instance."""
    global _execution_logs_repo
    if _execution_logs_repo is None:
        _execution_logs_repo = ExecutionLogsRepository()
    return _execution_logs_repo
