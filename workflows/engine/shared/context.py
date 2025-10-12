"""
Organization Context
Context object passed to all workflows with org data, config, secrets, and integrations
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class Organization:
    """Organization entity."""
    org_id: str
    name: str
    tenant_id: Optional[str]
    is_active: bool


@dataclass
class Caller:
    """User who triggered the execution."""
    user_id: str
    email: str
    name: str


class OrganizationContext:
    """
    Context object passed to all workflows.

    Provides access to:
    - Organization information (id, name, tenant_id)
    - Execution metadata (execution_id, caller)
    - Configuration (key-value pairs)
    - Secrets (from Key Vault)
    - Pre-authenticated integration clients
    - State tracking (checkpoints, logs, variables)
    """

    def __init__(
        self,
        org: Optional[Organization],
        config: Dict[str, Any],
        caller: Caller,
        execution_id: str
    ):
        self.org = org
        self._config = config
        self.caller = caller
        self.execution_id = execution_id

        # Integration cache
        self._integration_cache = {}

        # State tracking
        self._state_snapshots = []
        self._integration_calls = []
        self._logs = []
        self._variables = {}

    # ==================== ORG PROPERTIES ====================

    @property
    def org_id(self) -> Optional[str]:
        """Organization ID (None for platform admins in global context)."""
        return self.org.org_id if self.org else None

    @property
    def org_name(self) -> Optional[str]:
        """Organization display name (None for platform admins in global context)."""
        return self.org.name if self.org else None

    @property
    def tenant_id(self) -> Optional[str]:
        """Microsoft 365 tenant ID (if linked)."""
        return self.org.tenant_id if self.org else None

    # ==================== EXECUTION METADATA ====================

    @property
    def executed_by(self) -> str:
        """User ID who triggered this execution."""
        return self.caller.user_id

    @property
    def executed_by_email(self) -> str:
        """Email of user who triggered this execution."""
        return self.caller.email

    @property
    def executed_by_name(self) -> str:
        """Display name of user who triggered this execution."""
        return self.caller.name

    # ==================== CONFIGURATION ====================

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get organization-specific configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)

    def has_config(self, key: str) -> bool:
        """Check if configuration key exists."""
        return key in self._config

    # ==================== SECRETS ====================

    async def get_secret(self, key: str) -> str:
        """
        Get secret from Azure Key Vault.

        Secrets are scoped to organization: {org_id}--{key}

        Args:
            key: Secret key (e.g., "msgraph_client_secret")

        Returns:
            Secret value

        Raises:
            KeyError: If secret not found
        """
        # TODO: Implement Key Vault integration
        # For now, raise NotImplementedError
        raise NotImplementedError("Key Vault integration not yet implemented")

    # ==================== INTEGRATIONS ====================

    def get_integration(self, name: str):
        """
        Get pre-authenticated integration client.

        For MVP, this raises NotImplementedError. Integration clients
        will be added when needed (Microsoft Graph, HaloPSA, etc.)

        Args:
            name: Integration name

        Returns:
            Pre-authenticated integration client

        Raises:
            NotImplementedError: Integration not yet implemented
        """
        # Check cache
        if name in self._integration_cache:
            return self._integration_cache[name]

        # For MVP, raise NotImplementedError
        # Will be implemented when needed:
        # if name == "msgraph":
        #     from shared.integrations.msgraph import MicrosoftGraphIntegration
        #     client = MicrosoftGraphIntegration(self)
        # elif name == "halopsa":
        #     from shared.integrations.halopsa import HaloPSAIntegration
        #     client = HaloPSAIntegration(self)
        # else:
        #     raise ValueError(f"Unknown integration: {name}")

        raise NotImplementedError(
            f"Integration '{name}' not yet implemented. "
            f"Add integration client to shared/integrations/{name}.py"
        )

    # ==================== STATE TRACKING ====================

    def save_checkpoint(self, name: str, data: Dict[str, Any]) -> None:
        """
        Save a state checkpoint during workflow execution.

        Useful for:
        - Debugging failed workflows
        - Understanding execution flow
        - Resuming long-running workflows

        Args:
            name: Checkpoint name
            data: Checkpoint data (will be sanitized)
        """
        checkpoint = {
            "timestamp": datetime.utcnow().isoformat(),
            "name": name,
            "data": self._sanitize_data(data)
        }
        self._state_snapshots.append(checkpoint)

        logger.info(
            f"Checkpoint saved: {name}",
            extra={"execution_id": self.execution_id, "checkpoint": checkpoint}
        )

    def set_variable(self, key: str, value: Any) -> None:
        """
        Set a workflow variable (persisted in execution record).

        Args:
            key: Variable name
            value: Variable value (will be sanitized)
        """
        self._variables[key] = self._sanitize_data(value)

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a workflow variable."""
        return self._variables.get(key, default)

    def log(self, level: str, message: str, data: Dict[str, Any] = None) -> None:
        """
        Log a message from the workflow.

        Logs are persisted in the execution record.

        Args:
            level: "info" | "warning" | "error"
            message: Log message
            data: Additional structured data
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "data": self._sanitize_data(data) if data else {}
        }
        self._logs.append(log_entry)

        # Also log to Azure Functions logger
        logger_method = getattr(logging, level, logging.info)
        logger_method(
            message,
            extra={"execution_id": self.execution_id, **log_entry.get("data", {})}
        )

    def _track_integration_call(
        self,
        integration: str,
        method: str,
        endpoint: str,
        status_code: int,
        duration_ms: int,
        error: str = None
    ) -> None:
        """
        Track external integration call.

        Called automatically by integration clients.
        """
        call_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "integration": integration,
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "error": error,
            "success": status_code < 400 and not error
        }
        self._integration_calls.append(call_record)

    def _sanitize_data(self, data: Any) -> Any:
        """
        Remove sensitive data before persisting.

        - Removes keys containing 'secret', 'password', 'token', 'key'
        - Truncates long strings
        - Limits list/array sizes
        """
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                # Skip sensitive keys
                if any(s in key.lower() for s in ['secret', 'password', 'token', 'key', 'credential']):
                    sanitized[key] = "***REDACTED***"
                else:
                    sanitized[key] = self._sanitize_data(value)
            return sanitized

        elif isinstance(data, list):
            # Limit list size to 100 items
            return [self._sanitize_data(item) for item in data[:100]]

        elif isinstance(data, str):
            # Truncate long strings to 1000 characters
            return data[:1000] if len(data) > 1000 else data

        else:
            return data

    async def finalize_execution(self) -> Dict[str, Any]:
        """
        Get final execution state for persistence.

        Called automatically at end of execution.

        Returns:
            Dict with state_snapshots, integration_calls, logs, variables
        """
        return {
            "state_snapshots": self._state_snapshots,
            "integration_calls": self._integration_calls,
            "logs": self._logs,
            "variables": self._variables
        }
