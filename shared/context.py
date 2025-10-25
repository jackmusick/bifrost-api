"""
Organization Context
Context object passed to all workflows with org data, config, secrets, and integrations

Execution Context - Unified context for all requests, workflows, and scripts

This replaces both ExecutionContext and ExecutionContext with a single,
unified context that works everywhere:
- HTTP endpoint handlers
- Workflows and data providers
- Scripts
- Bifrost SDK
- Repository queries
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .config_resolver import ConfigResolver

logger = logging.getLogger(__name__)


@dataclass
class Organization:
    """Organization entity."""
    id: str
    name: str
    is_active: bool = True

    @property
    def org_id(self) -> str:
        """Backwards compatibility: alias for id"""
        return self.id


@dataclass
class Caller:
    """User who triggered the execution."""
    user_id: str
    email: str
    name: str


@dataclass
class ExecutionContext:
    """
    Unified execution context for all code execution.

    Provides:
    - User identity (user_id, email, name)
    - Scope (GLOBAL or organization ID)
    - Authorization (is_platform_admin, is_function_key)
    - Configuration and secrets
    - Workflow state tracking (logs, variables, checkpoints)

    Used everywhere:
    - HTTP handlers receive this from middleware
    - Workflows receive this as first parameter
    - Scripts have this available as `context`
    - Bifrost SDK accesses this via ContextVar
    - Repositories use this for scoped queries
    """

    # ==================== IDENTITY ====================
    user_id: str
    email: str
    name: str

    # ==================== SCOPE ====================
    scope: str  # "GLOBAL" or organization ID
    organization: Organization | None  # None for GLOBAL scope

    # ==================== AUTHORIZATION ====================
    is_platform_admin: bool
    is_function_key: bool

    # ==================== EXECUTION ====================
    execution_id: str

    # ==================== WORKFLOW STATE (private) ====================
    _config: dict[str, Any] = field(default_factory=dict)
    _config_resolver: ConfigResolver = field(default_factory=ConfigResolver)
    _integration_cache: dict = field(default_factory=dict)
    _state_snapshots: list = field(default_factory=list)
    _integration_calls: list = field(default_factory=list)

    # ==================== COMPUTED PROPERTIES ====================

    @property
    def org_id(self) -> str | None:
        """Organization ID (None for GLOBAL scope)"""
        return self.organization.id if self.organization else None

    @property
    def org_name(self) -> str | None:
        """Organization name (None for GLOBAL scope)"""
        return self.organization.name if self.organization else None

    @property
    def is_global_scope(self) -> bool:
        """True if executing in GLOBAL scope (no organization)"""
        return self.scope == "GLOBAL"

    @property
    def executed_by(self) -> str:
        """Backwards compatibility: alias for user_id"""
        return self.user_id

    @property
    def executed_by_email(self) -> str:
        """Backwards compatibility: alias for email"""
        return self.email

    @property
    def executed_by_name(self) -> str:
        """Backwards compatibility: alias for name"""
        return self.name

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
        # GLOBAL scope - no org-scoped resolution
        if self.is_global_scope:
            return self._config.get(key, default)

        try:
            return self._config_resolver.get_config(
                org_id=self.scope,
                key=key,
                config_data=self._config,
                default=default
            )
        except KeyError as e:
            # Secret resolution failed - log and re-raise with context
            logger.error(
                f"Failed to get config '{key}' for scope '{self.scope}': {e}",
                extra={"execution_id": self.execution_id, "scope": self.scope}
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

        logger.info(
            f"Retrieving OAuth connection: {connection_name} (scope: {self.scope})",
            extra={"execution_id": self.execution_id, "scope": self.scope}
        )

        # Use OAuthStorageService to get connection metadata
        from shared.services.oauth_storage_service import OAuthStorageService

        oauth_service = OAuthStorageService()
        keyvault = KeyVaultClient()
        config_table = TableStorageService("Config")

        # Get connection with org→GLOBAL fallback
        connection = await oauth_service.get_connection(self.scope, connection_name)

        if not connection:
            raise ValueError(
                f"OAuth connection '{connection_name}' not found for scope '{self.scope}' or GLOBAL. "
                f"Create connection using the OAuth Connections page in the admin UI"
            )

        # Check connection status
        if connection.status != "completed":
            raise ValueError(
                f"OAuth connection '{connection_name}' is not authorized (status: {connection.status}). "
                f"Complete OAuth authorization flow using the 'Connect' button in the admin UI"
            )

        # Get OAuth response reference
        oauth_response_ref = connection.oauth_response_ref

        if not oauth_response_ref:
            raise ValueError(
                f"OAuth connection '{connection_name}' missing oauth_response_ref"
            )

        # Get OAuth response config entry from the connection's org scope
        oauth_response_key = f"config:{oauth_response_ref}"
        connection_scope = connection.org_id
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

        # Get scopes from connection object
        scopes = connection.scopes or ""

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
        raise NotImplementedError("Key Vault integration not yet implemented")

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
            Dict with state_snapshots and integration_calls
        """
        return {
            "state_snapshots": self._state_snapshots,
            "integration_calls": self._integration_calls,
        }
