"""
Audit Repository
Manages audit log entries with date-based partitioning
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from .base import BaseRepository

logger = logging.getLogger(__name__)


class AuditRepository(BaseRepository):
    """
    Repository for audit log entries

    Audit logs are stored in AuditLog table with:
    - PartitionKey: Date in YYYY-MM-DD format (for time-range queries)
    - RowKey: Reverse timestamp + UUID (for chronological sorting)
    - EventType: Type of audit event
    - Event-specific fields
    """

    def __init__(self):
        """Initialize audit repository without context (uses GLOBAL table)"""
        super().__init__("AuditLog", context=None)

    def log_event(self, event_type: str, data: dict[str, Any]) -> None:
        """
        Log an audit event to table storage

        Args:
            event_type: Type of audit event
            data: Event-specific data fields

        Raises:
            Exception: If logging fails
        """
        now = datetime.now(UTC)
        entity = self._create_entity(event_type, now, data)

        try:
            self.insert(entity)
            logger.info(
                f"Audit event logged: {event_type}",
                extra={'event_type': event_type, 'partition_key': entity['PartitionKey']}
            )
        except Exception as e:
            logger.error(
                f"Failed to log audit event {event_type}: {e}",
                exc_info=True
            )
            raise

    def log_function_key_access(
        self,
        key_id: str,
        key_name: str,
        org_id: str,
        endpoint: str,
        method: str,
        remote_addr: str,
        user_agent: str,
        status_code: int,
        details: dict[str, Any] | None = None
    ) -> None:
        """
        Log function key authentication usage

        Args:
            key_id: Function key identifier
            key_name: Friendly key name
            org_id: Target organization ID
            endpoint: API endpoint path
            method: HTTP method
            remote_addr: Client IP address
            user_agent: Client user agent string
            status_code: HTTP response status
            details: Additional context (JSON-serializable)
        """
        self.log_event(
            event_type="function_key_access",
            data={
                "KeyId": key_id,
                "KeyName": key_name,
                "OrgId": org_id,
                "Endpoint": endpoint,
                "Method": method,
                "RemoteAddr": remote_addr,
                "UserAgent": user_agent,
                "StatusCode": status_code,
                "Details": json.dumps(details) if details else None
            }
        )

    def log_cross_org_access(
        self,
        user_id: str,
        target_org_id: str,
        endpoint: str,
        method: str,
        remote_addr: str,
        status_code: int,
        details: dict[str, Any] | None = None
    ) -> None:
        """
        Log PlatformAdmin cross-organization access

        Args:
            user_id: Admin user ID
            target_org_id: Organization being accessed
            endpoint: API endpoint path
            method: HTTP method
            remote_addr: Client IP address
            status_code: HTTP response status
            details: Additional context (reason, support ticket, etc.)
        """
        self.log_event(
            event_type="cross_org_access",
            data={
                "UserId": user_id,
                "OrgId": target_org_id,
                "Endpoint": endpoint,
                "Method": method,
                "RemoteAddr": remote_addr,
                "StatusCode": status_code,
                "Details": json.dumps(details) if details else None
            }
        )

    def log_import_violation_attempt(
        self,
        blocked_module: str,
        workspace_file: str,
        stack_trace: list[str] | None = None
    ) -> None:
        """
        Log attempted workspace→engine import violation

        Args:
            blocked_module: Module name that was blocked
            workspace_file: Source file that attempted import
            stack_trace: Python stack trace (file:line format)
        """
        self.log_event(
            event_type="engine_violation_attempt",
            data={
                "BlockedModule": blocked_module,
                "WorkspaceFile": workspace_file,
                "Details": json.dumps({
                    "stack_trace": stack_trace or []
                })
            }
        )

    def query_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        event_type: str | None = None
    ) -> list[dict]:
        """
        Query audit logs by date range

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            event_type: Optional filter by event type

        Returns:
            List of audit log entities
        """
        # Build list of partition keys (dates) to query
        current = start_date.date()
        end = end_date.date()

        results = []
        while current <= end:
            partition_key = current.strftime("%Y-%m-%d")

            # Build filter
            filter_query = f"PartitionKey eq '{partition_key}'"
            if event_type:
                filter_query += f" and EventType eq '{event_type}'"

            # Query this partition
            results.extend(list(self.query(filter_query)))

            # Move to next day
            from datetime import timedelta
            current += timedelta(days=1)

        logger.info(
            f"Found {len(results)} audit log entries from {start_date.date()} to {end_date.date()}"
        )
        return results

    def _create_entity(
        self,
        event_type: str,
        timestamp: datetime,
        data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Create AuditLog table entity

        Args:
            event_type: Type of audit event
            timestamp: Event timestamp (UTC)
            data: Event-specific data

        Returns:
            Dictionary representing table entity
        """
        # PartitionKey: Date in YYYY-MM-DD format
        partition_key = timestamp.strftime("%Y-%m-%d")

        # RowKey: Reverse timestamp + UUID for chronological sorting
        # Reverse timestamp ensures newest first when querying partition
        max_ticks = 9999999999999  # Max value for sorting
        ticks = int(timestamp.timestamp() * 1000)  # milliseconds
        reverse_ticks = max_ticks - ticks
        row_key = f"{reverse_ticks}_{uuid.uuid4().hex}"

        # Build entity
        entity = {
            "PartitionKey": partition_key,
            "RowKey": row_key,
            "EventType": event_type,
            "Timestamp": timestamp.isoformat(),
            **data  # Merge event-specific fields
        }

        return entity
