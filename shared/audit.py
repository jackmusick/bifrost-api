"""
Audit Logging System for Privileged Operations

Provides structured audit logging to Azure Table Storage for:
- Function key authentication usage
- Cross-organization access by PlatformAdmins
- Import violation attempts

All audit logs are stored in the AuditLog table with date-based partitioning
for efficient time-range queries and 90-day retention.
"""

import logging
import os
from typing import Any, Optional

from shared.repositories.audit import AuditRepository

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

        self._repository = None

    def _get_repository(self) -> AuditRepository | None:
        """Lazy-load audit repository"""
        if not self._enabled:
            return None

        if self._repository is None:
            try:
                self._repository = AuditRepository()
            except Exception as e:
                logger.error(f"Failed to create audit repository: {e}")
                self._enabled = False
                return None

        return self._repository

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
        if not self._enabled:
            logger.debug("Audit logging disabled, skipping function_key_access event")
            return

        repository = self._get_repository()
        if not repository:
            return

        try:
            await repository.log_function_key_access(
                key_id=key_id,
                key_name=key_name,
                org_id=org_id,
                endpoint=endpoint,
                method=method,
                remote_addr=remote_addr,
                user_agent=user_agent,
                status_code=status_code,
                details=details
            )
        except Exception as e:
            logger.error(
                f"Failed to log function_key_access event: {e}",
                exc_info=True
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
        if not self._enabled:
            logger.debug("Audit logging disabled, skipping cross_org_access event")
            return

        repository = self._get_repository()
        if not repository:
            return

        try:
            await repository.log_cross_org_access(
                user_id=user_id,
                target_org_id=target_org_id,
                endpoint=endpoint,
                method=method,
                remote_addr=remote_addr,
                status_code=status_code,
                details=details
            )
        except Exception as e:
            logger.error(
                f"Failed to log cross_org_access event: {e}",
                exc_info=True
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
        if not self._enabled:
            logger.debug("Audit logging disabled, skipping engine_violation_attempt event")
            return

        repository = self._get_repository()
        if not repository:
            return

        try:
            await repository.log_import_violation_attempt(
                blocked_module=blocked_module,
                workspace_file=workspace_file,
                stack_trace=stack_trace
            )
        except Exception as e:
            logger.error(
                f"Failed to log engine_violation_attempt event: {e}",
                exc_info=True
            )


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
