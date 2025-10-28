"""
System Logger
Logs platform-level events (not workflow executions) to Table Storage

Events like:
- Module discovery failures
- Organization/user CRUD operations
- Configuration changes
- Secret management
- Form updates
- OAuth token refreshes
- System errors and warnings
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from azure.data.tables import TableServiceClient

logger = logging.getLogger(__name__)

# Event categories
EventCategory = Literal[
    "discovery",      # Workflow/module discovery
    "organization",   # Organization CRUD
    "user",          # User management
    "role",          # Role management
    "config",        # Configuration changes
    "secret",        # Secret management
    "form",          # Form CRUD
    "oauth",         # OAuth token management
    "execution",     # Execution-related events (cleanup, etc.)
    "system",        # General system events
    "error"          # System errors
]

# Event severity levels
EventLevel = Literal["info", "warning", "error", "critical"]


class SystemLogger:
    """
    Logger for platform-level system events.

    Stores events in Table Storage with structure:
    - PartitionKey: Event category (e.g., "discovery", "organization")
    - RowKey: timestamp_eventId (for chronological ordering)
    - Timestamp: ISO timestamp
    - Level: info/warning/error/critical
    - Message: Human-readable event description
    - ExecutedBy: User ID or "System"
    - ExecutedByName: Display name or "System"
    - Details: JSON blob with event-specific data

    Usage:
        system_logger = SystemLogger()

        # Log discovery failure
        await system_logger.log(
            category="discovery",
            level="error",
            message="Failed to import workspace.my_workflow",
            executed_by="System",
            details={"error": "ImportError: ...", "file": "/path/to/workflow.py"}
        )

        # Log organization creation
        await system_logger.log(
            category="organization",
            level="info",
            message="Created organization 'Acme Corp'",
            executed_by="jack@example.com",
            executed_by_name="Jack Smith",
            details={"org_id": "abc-123", "domain": "acme.com"}
        )
    """

    def __init__(self, connection_string: str | None = None):
        """
        Initialize system logger.

        Args:
            connection_string: Azure Storage connection string (defaults to env var)
        """
        import os
        self.connection_string = connection_string or os.environ.get(
            "AzureWebJobsStorage",
            "UseDevelopmentStorage=true"
        )
        self.table_name = "SystemLogs"

        # Ensure table exists
        try:
            table_service = TableServiceClient.from_connection_string(self.connection_string)
            table_service.create_table_if_not_exists(self.table_name)
            logger.debug(f"System logs table '{self.table_name}' ready")
        except Exception as e:
            logger.warning(f"Failed to initialize system logs table: {e}")

    def _reverse_timestamp(self, dt: datetime) -> str:
        """
        Create reverse timestamp for sorting logs newest-first.
        Same pattern as ExecutionRepository.

        Args:
            dt: Datetime to convert

        Returns:
            Reverse timestamp string (9999999999999 - timestamp_ms)
        """
        timestamp_ms = int(dt.timestamp() * 1000)
        reverse = 9999999999999 - timestamp_ms
        return str(reverse)

    async def log(
        self,
        category: EventCategory,
        level: EventLevel,
        message: str,
        executed_by: str = "System",
        executed_by_name: str | None = None,
        details: dict[str, Any] | None = None
    ) -> str:
        """
        Log a system event.

        Args:
            category: Event category (discovery, organization, user, etc.)
            level: Severity level (info, warning, error, critical)
            message: Human-readable event description
            executed_by: User ID or "System" (default: "System")
            executed_by_name: Display name (default: same as executed_by)
            details: Additional event-specific data as dict

        Returns:
            Event ID (UUID)
        """
        event_id = str(uuid4())
        timestamp = datetime.now(timezone.utc)

        # Use executed_by as name if not provided
        if executed_by_name is None:
            executed_by_name = executed_by

        # Create entity with reverse timestamp for newest-first ordering
        reverse_ts = self._reverse_timestamp(timestamp)
        entity = {
            "PartitionKey": category,
            "RowKey": f"{reverse_ts}_{event_id}",  # Reverse chronological ordering (newest first)
            "EventId": event_id,
            "TimestampISO": timestamp.isoformat(),  # Store ISO timestamp for parsing
            "Level": level,
            "Message": message,
            "ExecutedBy": executed_by,
            "ExecutedByName": executed_by_name,
            "Details": json.dumps(details) if details else None
        }

        try:
            table_service = TableServiceClient.from_connection_string(self.connection_string)
            table_client = table_service.get_table_client(self.table_name)
            table_client.create_entity(entity)

            logger.debug(
                f"System event logged: [{level.upper()}] {category} - {message}",
                extra={"event_id": event_id, "category": category, "executed_by": executed_by}
            )

        except Exception as e:
            # Don't fail the operation if logging fails
            logger.error(
                f"Failed to log system event: {e}",
                extra={"category": category, "event_message": message},
                exc_info=True
            )

        return event_id

    async def log_discovery_failure(
        self,
        module_name: str,
        file_path: str,
        error: str
    ) -> str:
        """
        Convenience method for logging module discovery failures.

        Args:
            module_name: Module name that failed to import
            file_path: Path to the file
            error: Error message

        Returns:
            Event ID
        """
        return await self.log(
            category="discovery",
            level="error",
            message=f"Failed to import {module_name}",
            details={
                "module_name": module_name,
                "file_path": file_path,
                "error": error
            }
        )

    async def log_organization_event(
        self,
        action: Literal["create", "update", "delete"],
        org_id: str,
        org_name: str,
        executed_by: str,
        executed_by_name: str,
        details: dict[str, Any] | None = None
    ) -> str:
        """
        Convenience method for logging organization events.

        Args:
            action: create/update/delete
            org_id: Organization ID
            org_name: Organization name
            executed_by: User ID
            executed_by_name: Display name
            details: Additional details

        Returns:
            Event ID
        """
        action_past = {"create": "Created", "update": "Updated", "delete": "Deleted"}[action]

        event_details = {"org_id": org_id, "org_name": org_name}
        if details:
            event_details.update(details)

        return await self.log(
            category="organization",
            level="info",
            message=f"{action_past} organization '{org_name}'",
            executed_by=executed_by,
            executed_by_name=executed_by_name,
            details=event_details
        )

    async def log_config_event(
        self,
        action: Literal["set", "delete"],
        scope: str,
        key: str,
        executed_by: str,
        executed_by_name: str,
        config_type: str | None = None
    ) -> str:
        """
        Convenience method for logging configuration changes.

        Args:
            action: set/delete
            scope: Organization ID or "GLOBAL"
            key: Config key
            executed_by: User ID
            executed_by_name: Display name
            config_type: Type of config value

        Returns:
            Event ID
        """
        action_past = {"set": "Set", "delete": "Deleted"}[action]

        return await self.log(
            category="config",
            level="info",
            message=f"{action_past} config '{key}' in {scope}",
            executed_by=executed_by,
            executed_by_name=executed_by_name,
            details={"scope": scope, "key": key, "type": config_type}
        )

    async def log_secret_event(
        self,
        action: Literal["set", "delete"],
        scope: str,
        key: str,
        executed_by: str,
        executed_by_name: str
    ) -> str:
        """
        Convenience method for logging secret management events.

        Args:
            action: set/delete
            scope: Organization ID or "GLOBAL"
            key: Secret key
            executed_by: User ID
            executed_by_name: Display name

        Returns:
            Event ID
        """
        action_past = {"set": "Set", "delete": "Deleted"}[action]

        return await self.log(
            category="secret",
            level="info",
            message=f"{action_past} secret '{key}' in {scope}",
            executed_by=executed_by,
            executed_by_name=executed_by_name,
            details={"scope": scope, "key": key}
        )

    async def log_form_event(
        self,
        action: Literal["create", "update", "delete"],
        form_id: str,
        form_name: str,
        scope: str,
        executed_by: str,
        executed_by_name: str
    ) -> str:
        """
        Convenience method for logging form events.

        Args:
            action: create/update/delete
            form_id: Form ID
            form_name: Form name
            scope: Organization ID or "GLOBAL"
            executed_by: User ID
            executed_by_name: Display name

        Returns:
            Event ID
        """
        action_past = {"create": "Created", "update": "Updated", "delete": "Deleted"}[action]

        return await self.log(
            category="form",
            level="info",
            message=f"{action_past} form '{form_name}' in {scope}",
            executed_by=executed_by,
            executed_by_name=executed_by_name,
            details={"form_id": form_id, "form_name": form_name, "scope": scope}
        )

    async def log_user_event(
        self,
        action: Literal["create", "update", "delete"],
        user_id: str,
        user_email: str,
        executed_by: str,
        executed_by_name: str,
        details: dict[str, Any] | None = None
    ) -> str:
        """
        Convenience method for logging user management events.

        Args:
            action: create/update/delete
            user_id: User ID
            user_email: User email
            executed_by: User ID who performed the action
            executed_by_name: Display name
            details: Additional details (user_type, is_admin, org_id, etc.)

        Returns:
            Event ID
        """
        action_past = {"create": "Created", "update": "Updated", "delete": "Deleted"}[action]

        event_details = {"user_id": user_id, "user_email": user_email}
        if details:
            event_details.update(details)

        return await self.log(
            category="user",
            level="info",
            message=f"{action_past} user '{user_email}'",
            executed_by=executed_by,
            executed_by_name=executed_by_name,
            details=event_details
        )

    async def log_role_event(
        self,
        action: Literal["create", "update", "delete", "assign_users", "remove_user", "assign_forms", "remove_form"],
        role_id: str,
        role_name: str,
        executed_by: str,
        executed_by_name: str,
        scope: str | None = None,
        details: dict[str, Any] | None = None
    ) -> str:
        """
        Convenience method for logging role management events.

        Args:
            action: create/update/delete/assign_users/remove_user/assign_forms/remove_form
            role_id: Role ID
            role_name: Role name
            executed_by: User ID
            executed_by_name: Display name
            scope: Organization ID or "GLOBAL"
            details: Additional details (permissions, user_ids, form_ids, etc.)

        Returns:
            Event ID
        """
        action_messages = {
            "create": f"Created role '{role_name}'",
            "update": f"Updated role '{role_name}'",
            "delete": f"Deleted role '{role_name}'",
            "assign_users": f"Assigned users to role '{role_name}'",
            "remove_user": f"Removed user from role '{role_name}'",
            "assign_forms": f"Assigned forms to role '{role_name}'",
            "remove_form": f"Removed form from role '{role_name}'"
        }

        event_details = {"role_id": role_id, "role_name": role_name}
        if scope:
            event_details["scope"] = scope
        if details:
            event_details.update(details)

        return await self.log(
            category="role",
            level="info",
            message=action_messages[action],
            executed_by=executed_by,
            executed_by_name=executed_by_name,
            details=event_details
        )


# Singleton instance
_system_logger = None


def get_system_logger() -> SystemLogger:
    """Get singleton SystemLogger instance."""
    global _system_logger
    if _system_logger is None:
        _system_logger = SystemLogger()
    return _system_logger
