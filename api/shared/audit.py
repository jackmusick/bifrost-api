"""
Audit Logging System for Privileged Operations

Provides structured audit logging to Azure Table Storage for:
- Function key authentication usage
- Cross-organization access by PlatformAdmins
- Import violation attempts

All audit logs are stored in the AuditLog table with date-based partitioning
for efficient time-range queries and 90-day retention.
"""

import json
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Singleton instance
_audit_logger_instance: Optional['AuditLogger'] = None


class AuditLogger:
    """
    Structured audit logging to Azure Table Storage.

    All audit events are written to the AuditLog table with:
    - PartitionKey: Date in YYYY-MM-DD format (for time-range queries)
    - RowKey: Reverse timestamp + UUID (for chronological sorting)
    - EventType: Type of audit event
    - Additional event-specific fields
    """

    def __init__(self, connection_string: str | None = None):
        """
        Initialize audit logger with Table Storage connection.

        Args:
            connection_string: Azure Storage connection string.
                              Defaults to AzureWebJobsStorage env var.
        """
        self.connection_string = connection_string or os.environ.get(
            "AzureWebJobsStorage"
        )

        if not self.connection_string:
            logger.warning(
                "AzureWebJobsStorage not set - audit logging disabled"
            )
            self._enabled = False
        else:
            self._enabled = True

        self._table_client = None

    def _get_table_client(self):
        """Lazy-load table client"""
        if not self._enabled:
            return None

        if self._table_client is None:
            try:
                from azure.data.tables import TableServiceClient

                assert self.connection_string is not None, "Connection string is None"
                service_client = TableServiceClient.from_connection_string(
                    self.connection_string
                )
                self._table_client = service_client.get_table_client("AuditLog")
            except Exception as e:
                logger.error(f"Failed to create table client for audit logging: {e}")
                self._enabled = False
                return None

        return self._table_client

    async def log_function_key_access(
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
        Log function key authentication usage.

        Creates entry in AuditLog table with EventType='function_key_access'.

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
        await self._log_event(
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

    async def log_cross_org_access(
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
        Log PlatformAdmin cross-organization access.

        Creates entry in AuditLog table with EventType='cross_org_access'.

        Args:
            user_id: Admin user ID
            target_org_id: Organization being accessed
            endpoint: API endpoint path
            method: HTTP method
            remote_addr: Client IP address
            status_code: HTTP response status
            details: Additional context (reason, support ticket, etc.)
        """
        await self._log_event(
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

    async def log_import_violation_attempt(
        self,
        blocked_module: str,
        workspace_file: str,
        stack_trace: list[str] | None = None
    ) -> None:
        """
        Log attempted workspace→engine import violation.

        Creates entry in AuditLog table with EventType='engine_violation_attempt'.

        Args:
            blocked_module: Module name that was blocked
            workspace_file: Source file that attempted import
            stack_trace: Python stack trace (file:line format)
        """
        await self._log_event(
            event_type="engine_violation_attempt",
            data={
                "BlockedModule": blocked_module,
                "WorkspaceFile": workspace_file,
                "Details": json.dumps({
                    "stack_trace": stack_trace or []
                })
            }
        )

    async def _log_event(
        self,
        event_type: str,
        data: dict[str, Any]
    ) -> None:
        """
        Internal method to log audit event to Table Storage.

        Args:
            event_type: Type of audit event
            data: Event-specific data fields
        """
        if not self._enabled:
            logger.debug(f"Audit logging disabled, skipping {event_type} event")
            return

        table_client = self._get_table_client()
        if not table_client:
            return

        try:
            # Create entity
            now = datetime.now(UTC)
            entity = self._create_entity(event_type, now, data)

            # Insert into table (fire and forget - synchronous SDK)
            table_client.create_entity(entity)

            logger.info(
                f"Audit event logged: {event_type}",
                extra={'event_type': event_type, 'partition_key': entity['PartitionKey']}
            )

        except Exception as e:
            logger.error(
                f"Failed to log audit event {event_type}: {e}",
                exc_info=True
            )

    def _create_entity(
        self,
        event_type: str,
        timestamp: datetime,
        data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Create AuditLog table entity.

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


def get_audit_logger() -> AuditLogger:
    """
    Get singleton AuditLogger instance.

    Returns:
        Shared AuditLogger instance
    """
    global _audit_logger_instance

    if _audit_logger_instance is None:
        _audit_logger_instance = AuditLogger()

    return _audit_logger_instance
