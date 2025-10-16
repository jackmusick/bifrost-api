"""
Organization Context
Context object passed to all workflows with org data, config, secrets, and integrations
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .config_resolver import ConfigResolver

logger = logging.getLogger(__name__)


@dataclass
class Organization:
    """Organization entity."""
    org_id: str
    name: str
    tenant_id: str | None
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
        org: Organization | None,
        config: dict[str, Any],
        caller: Caller,
        execution_id: str
    ):
        self.org = org
        self._config = config
        self.caller = caller
        self.execution_id = execution_id

        # Configuration resolver for transparent secret resolution
        self._config_resolver = ConfigResolver()

        # Integration cache
        self._integration_cache = {}

        # State tracking
        self._state_snapshots = []
        self._integration_calls = []
        self._logs = []
        self._variables = {}

    # ==================== ORG PROPERTIES ====================

    @property
    def org_id(self) -> str | None:
        """Organization ID (None for platform admins in global context)."""
        return self.org.org_id if self.org else None

    @property
    def org_name(self) -> str | None:
        """Organization display name (None for platform admins in global context)."""
        return self.org.name if self.org else None

    @property
    def tenant_id(self) -> str | None:
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
        Get organization-specific configuration value with transparent secret resolution.

        This method automatically resolves secret references from Azure Key Vault
        based on the configuration type. If the config type is 'secret_ref', it
        retrieves the actual secret value from Key Vault using org-scoped → global fallback.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value (with secret resolved if secret_ref type)

        Raises:
            KeyError: If secret reference cannot be resolved from Key Vault
        """
        # Use resolver for transparent secret handling
        if not self.org_id:
            # Platform admin context - no org-scoped resolution
            return self._config.get(key, default)

        try:
            return self._config_resolver.get_config(
                org_id=self.org_id,
                key=key,
                config_data=self._config,
                default=default
            )
        except KeyError as e:
            # Secret resolution failed - log and re-raise with context
            logger.error(
                f"Failed to get config '{key}' for org '{self.org_id}': {e}",
                extra={"execution_id": self.execution_id, "org_id": self.org_id}
            )
            raise

    def has_config(self, key: str) -> bool:
        """Check if configuration key exists."""
        return key in self._config

    # ==================== OAUTH CONNECTIONS ====================

    async def get_oauth_connection(self, connection_name: str):
        """
        Get OAuth credentials for a connection.

        Retrieves OAuth credentials from storage and Key Vault,
        resolving them to actual access tokens for workflow use.

        This method works with both org-scoped and GLOBAL contexts.
        OAuth connections follow org→GLOBAL fallback pattern.

        Example:
            # In a workflow
            creds = await context.get_oauth_connection("HaloPSA")
            headers = {"Authorization": creds.get_auth_header()}
            response = requests.get("https://api.example.com/v1/data", headers=headers)

        Args:
            connection_name: Name of the OAuth connection to retrieve

        Returns:
            OAuthCredentials object with access_token and metadata

        Raises:
            ValueError: If connection not found or not authorized
            KeyError: If credentials cannot be resolved from Key Vault
        """
        import json

        from .keyvault import KeyVaultClient
        from .models import OAuthCredentials
        from .storage import TableStorageService

        # Determine scope for OAuth connection lookup
        # For GLOBAL context (org_id=None), use "GLOBAL" as the scope
        lookup_org_id = self.org_id if self.org_id else "GLOBAL"

        logger.info(
            f"Retrieving OAuth connection: {connection_name} (scope: {lookup_org_id})",
            extra={"execution_id": self.execution_id, "lookup_scope": lookup_org_id}
        )

        # Get storage services
        oauth_table = TableStorageService("OAuthConnections")
        config_table = TableStorageService("Config")
        keyvault = KeyVaultClient()

        # Try org-specific connection first (if we have an org), then GLOBAL fallback
        connection_entity = None
        connection_scope = None

        if self.org_id:
            connection_entity = oauth_table.get_entity(self.org_id, connection_name)
            if connection_entity:
                connection_scope = self.org_id
                logger.info(f"Using org-specific OAuth connection: {connection_name}")

        # If not found in org scope (or no org), try GLOBAL
        if not connection_entity:
            connection_entity = oauth_table.get_entity("GLOBAL", connection_name)
            if connection_entity:
                connection_scope = "GLOBAL"
                logger.info(f"Using GLOBAL OAuth connection: {connection_name}")

        if not connection_entity:
            raise ValueError(
                f"OAuth connection '{connection_name}' not found for scope '{lookup_org_id}' or GLOBAL. "
                f"Create connection using the OAuth Connections page in the admin UI"
            )

        # Check connection status
        status = connection_entity.get("status", "not_connected")

        if status != "completed":
            raise ValueError(
                f"OAuth connection '{connection_name}' is not authorized (status: {status}). "
                f"Complete OAuth authorization flow using the 'Connect' button in the admin UI"
            )

        # Get OAuth response reference from connection
        oauth_response_ref = connection_entity.get("oauth_response_ref")

        if not oauth_response_ref:
            raise ValueError(
                f"OAuth connection '{connection_name}' missing oauth_response_ref"
            )

        # Get OAuth response config entry from the same scope as the connection
        oauth_response_key = f"config:{oauth_response_ref}"
        assert connection_scope is not None, "connection_scope is None"
        oauth_response_config = config_table.get_entity(connection_scope, oauth_response_key)

        if not oauth_response_config:
            raise ValueError(
                f"OAuth response config not found: {oauth_response_key} in scope {connection_scope}"
            )

        # Get Key Vault secret name from config
        keyvault_secret_name = oauth_response_config.get("Value")

        if not keyvault_secret_name:
            raise ValueError(
                "OAuth response config missing Key Vault secret name"
            )

        # Retrieve actual OAuth tokens from Key Vault
        # Note: keyvault_secret_name is already the full secret name (e.g., "GLOBAL--oauth-HaloPSA-response")
        # so we use the _client directly instead of get_secret() which expects org_id and secret_key
        try:
            assert keyvault._client is not None, "KeyVault client is None"
            secret = keyvault._client.get_secret(keyvault_secret_name)
            oauth_response_json = secret.value
            assert oauth_response_json is not None, "OAuth response JSON is None"
            oauth_response = json.loads(oauth_response_json)
        except Exception as e:
            logger.error(
                f"Failed to retrieve OAuth tokens from Key Vault: {e}",
                extra={"execution_id": self.execution_id, "secret_name": keyvault_secret_name}
            )
            raise KeyError(
                f"Failed to retrieve OAuth tokens for '{connection_name}' from Key Vault: {e}"
            ) from e

        # Parse OAuth response
        access_token = oauth_response.get("access_token")
        refresh_token = oauth_response.get("refresh_token")
        token_type = oauth_response.get("token_type", "Bearer")
        expires_at_str = oauth_response.get("expires_at")

        if not access_token:
            raise ValueError(
                f"OAuth response for '{connection_name}' missing access_token"
            )

        # Parse expiration timestamp
        if expires_at_str:
            if isinstance(expires_at_str, str):
                expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
            else:
                expires_at = expires_at_str
        else:
            # Default to current time (will be marked as expired)
            expires_at = datetime.utcnow()

        # Get scopes from connection entity
        scopes = connection_entity.get("scopes", "")

        # Create credentials object
        credentials = OAuthCredentials(
            connection_name=connection_name,
            access_token=access_token,
            token_type=token_type,
            expires_at=expires_at,
            refresh_token=refresh_token,
            scopes=scopes
        )

        # Check if expired
        if credentials.is_expired():
            logger.warning(
                f"OAuth token for '{connection_name}' is expired (expired at {expires_at})",
                extra={"execution_id": self.execution_id}
            )

        logger.info(
            f"Retrieved OAuth credentials for '{connection_name}'",
            extra={
                "execution_id": self.execution_id,
                "expires_at": expires_at.isoformat(),
                "has_refresh_token": bool(refresh_token),
                "is_expired": credentials.is_expired()
            }
        )

        # Track credential access in context
        self.info(
            f"Retrieved OAuth credentials for '{connection_name}'",
            {
                "connection_name": connection_name,
                "expires_at": expires_at.isoformat(),
                "is_expired": credentials.is_expired()
            }
        )

        return credentials

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

    def save_checkpoint(self, name: str, data: dict[str, Any]) -> None:
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

    def _log(self, level: str, message: str, data: dict[str, Any] | None = None) -> None:
        """
        Internal logging method used by info(), warning(), error(), debug().

        Args:
            level: Log level (info, warning, error, debug)
            message: Log message
            data: Optional structured data dictionary
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

    def info(self, message: str, data: dict[str, Any] | None = None) -> None:
        """
        Log an info-level message.

        Args:
            message: Log message
            data: Optional structured data dictionary

        Example:
            context.info("Processing user")
            context.info("User created", {"user_id": "123", "email": "user@example.com"})
        """
        self._log("info", message, data)

    def warning(self, message: str, data: dict[str, Any] | None = None) -> None:
        """
        Log a warning-level message.

        Args:
            message: Log message
            data: Optional structured data dictionary

        Example:
            context.warning("Rate limit approaching")
            context.warning("OAuth token expired", {"expires_at": "2024-01-01"})
        """
        self._log("warning", message, data)

    def error(self, message: str, data: dict[str, Any] | None = None) -> None:
        """
        Log an error-level message.

        Args:
            message: Log message
            data: Optional structured data dictionary

        Example:
            context.error("API call failed")
            context.error("Connection timeout", {"endpoint": "/users", "timeout": 30})
        """
        self._log("error", message, data)

    def debug(self, message: str, data: dict[str, Any] | None = None) -> None:
        """
        Log a debug-level message.

        Args:
            message: Log message
            data: Optional structured data dictionary

        Example:
            context.debug("Request details", {"headers": headers, "body": body})
        """
        self._log("debug", message, data)

    def _track_integration_call(
        self,
        integration: str,
        method: str,
        endpoint: str,
        status_code: int,
        duration_ms: int,
        error: str | None = None
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

    async def finalize_execution(self) -> dict[str, Any]:
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
