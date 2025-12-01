"""
Audit Logging System for Privileged Operations

Provides structured audit logging to PostgreSQL for:
- Function key authentication usage
- Cross-organization access by PlatformAdmins
- Import violation attempts

All audit logs are stored in the audit_logs table with date-based partitioning
for efficient time-range queries.
"""

import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)

# Singleton instance
_audit_logger_instance: Optional['AuditLogger'] = None


class AuditLogger:
    """
    Structured audit logging to PostgreSQL.

    All audit events are written to the audit_logs table with:
    - event_type: Type of audit event
    - timestamp: When the event occurred
    - Additional event-specific fields stored in JSONB
    """

    def __init__(self):
        """Initialize audit logger."""
        self._enabled = True

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

        try:
            from src.core.database import get_session_factory
            from src.models import AuditLog

            session_factory = get_session_factory()

            async with session_factory() as db:
                audit_entry = AuditLog(
                    event_type="function_key_access",
                    key_id=key_id,
                    key_name=key_name,
                    org_id=org_id,
                    endpoint=endpoint,
                    method=method,
                    remote_addr=remote_addr,
                    user_agent=user_agent,
                    status_code=status_code,
                    details=details,
                )
                db.add(audit_entry)
                await db.commit()
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

        try:
            from src.core.database import get_session_factory
            from src.models import AuditLog

            session_factory = get_session_factory()

            async with session_factory() as db:
                audit_entry = AuditLog(
                    event_type="cross_org_access",
                    user_id=user_id,
                    target_org_id=target_org_id,
                    endpoint=endpoint,
                    method=method,
                    remote_addr=remote_addr,
                    status_code=status_code,
                    details=details,
                )
                db.add(audit_entry)
                await db.commit()
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

        Args:
            blocked_module: Module name that was blocked
            workspace_file: Source file that attempted import
            stack_trace: Python stack trace (file:line format)
        """
        if not self._enabled:
            logger.debug("Audit logging disabled, skipping engine_violation_attempt event")
            return

        try:
            from src.core.database import get_session_factory
            from src.models import AuditLog

            session_factory = get_session_factory()

            async with session_factory() as db:
                audit_entry = AuditLog(
                    event_type="engine_violation_attempt",
                    details={
                        "blocked_module": blocked_module,
                        "workspace_file": workspace_file,
                        "stack_trace": stack_trace,
                    },
                )
                db.add(audit_entry)
                await db.commit()
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
