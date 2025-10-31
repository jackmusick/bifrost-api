"""
Bifrost Integrations - Type Stubs for Workflow Development

Copy this file to your workflow workspace to get IDE autocomplete and type hints.

Usage:
    1. Copy bifrost.pyi to your workspace folder
    2. Import and use with simplified imports
    3. At runtime, the actual engine implementation is provided by the container

Example:
    from bifrost import workflow, param, ExecutionContext

    @workflow(name="my_workflow", description="...")
    @param("user_email", "string", required=True)
    async def my_workflow(context: ExecutionContext, user_email: str):
        context.info(f"Processing {user_email}")
        return {"success": True}
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

# ==================== CONTEXT ====================

@dataclass
class Organization:
    """Organization entity."""
    id: str
    name: str
    is_active: bool

@dataclass
class Caller:
    """User who triggered the workflow execution."""
    user_id: str
    email: str
    name: str

class ExecutionContext:
    """
    Context object passed to all workflows.

    Provides access to:
    - Organization information (id, name)
    - User information (user_id, email, name)
    - Execution metadata (execution_id, scope)
    - Configuration (key-value pairs with secret resolution)
    - OAuth connections (pre-authenticated credentials)
    - State tracking (checkpoints, logs, variables)
    """

    # Core properties
    user_id: str
    email: str
    name: str
    scope: str
    organization: Organization | None
    is_platform_admin: bool
    is_function_key: bool
    execution_id: str

    def __init__(
        self,
        user_id: str,
        email: str,
        name: str,
        scope: str,
        organization: Organization | None,
        is_platform_admin: bool,
        is_function_key: bool,
        execution_id: str
    ) -> None: ...

    # Organization properties
    @property
    def org_id(self) -> str | None:
        """Organization ID (None for platform admins in global context)."""
        ...

    @property
    def org_name(self) -> str | None:
        """Organization display name (None for platform admins)."""
        ...

    # Backwards compatibility properties
    @property
    def executed_by(self) -> str:
        """User ID who triggered this execution (alias for user_id)."""
        ...

    @property
    def executed_by_email(self) -> str:
        """Email of user who triggered this execution (alias for email)."""
        ...

    @property
    def executed_by_name(self) -> str:
        """Display name of user who triggered this execution (alias for name)."""
        ...

    @property
    def is_global_scope(self) -> bool:
        """True if executing in GLOBAL scope (no organization)."""
        ...

    async def finalize_execution(self) -> dict[str, Any]:
        """Get final execution state for persistence."""
        ...

# ==================== DECORATORS ====================

def workflow(
    name: str,
    description: str,
    category: str = "General",
    tags: list[str] | None = None,
    execution_mode: str = "sync",
    timeout_seconds: int = 300,
    max_duration_seconds: int = 300,
    retry_policy: dict[str, Any] | None = None,
    schedule: str | None = None,
    requires_org: bool = True,
    expose_in_forms: bool = True,
    requires_approval: bool = False,
    required_permission: str = "canExecuteWorkflows"
) -> Callable:
    """
    Decorator to register a workflow function.

    Args:
        name: Workflow name (URL-friendly, lowercase-with-dashes)
        description: User-friendly description
        category: Category for grouping (default: "General")
        tags: Optional tags for filtering
        execution_mode: "sync" or "async"
        timeout_seconds: Max execution time
        requires_org: Whether workflow requires org context
        expose_in_forms: Whether workflow can be triggered from forms
        required_permission: Permission required to execute

    Example:
        @workflow(
            name="create_user",
            description="Create a new user in Microsoft 365",
            category="User Management"
        )
        @param("email", "string", required=True)
        @param("first_name", "string", required=True)
        @param("last_name", "string", required=True)
        async def create_user(context: OrganizationContext, email: str, first_name: str, last_name: str):
            # Workflow implementation
            pass
    """
    ...

def param(
    name: str,
    type: str,
    label: str | None = None,
    required: bool = False,
    validation: dict[str, Any] | None = None,
    data_provider: str | None = None,
    default_value: Any = None,
    help_text: str | None = None
) -> Callable:
    """
    Decorator to define a workflow parameter.

    Args:
        name: Parameter name (must match function argument)
        type: Parameter type ("string", "number", "boolean", "select", etc.)
        label: Display label (defaults to name)
        required: Whether parameter is required
        validation: Validation rules (pattern, min, max)
        data_provider: Name of data provider for dynamic options
        default_value: Default value if not provided
        help_text: Help text for UI

    Example:
        @param("department", "select", data_provider="departments", required=True)
        @param("notify_manager", "boolean", default_value=True)
    """
    ...

def data_provider(
    name: str,
    description: str,
    category: str = "General",
    cache_ttl_seconds: int = 300
) -> Callable:
    """
    Decorator to register a data provider for dynamic form options.

    Args:
        name: Data provider name
        description: Description of what data it provides
        category: Category for grouping
        cache_ttl_seconds: How long to cache results

    Example:
        @data_provider(
            name="departments",
            description="List of departments from HaloPSA"
        )
        async def get_departments(context: OrganizationContext) -> List[Dict[str, str]]:
            return [
                {"value": "it", "label": "IT"},
                {"value": "hr", "label": "HR"}
            ]
    """
    ...

# ==================== MODELS ====================

class ExecutionStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "Pending"
    RUNNING = "Running"
    SUCCESS = "Success"
    COMPLETED_WITH_ERRORS = "CompletedWithErrors"
    FAILED = "Failed"

class ConfigType(str, Enum):
    """Configuration value types."""
    STRING = "string"
    SECRET_REF = "secret_ref"
    JSON = "json"

class FormFieldType(str, Enum):
    """Form field types."""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    DATE = "date"
    DATETIME = "datetime"

class IntegrationType(str, Enum):
    """Integration provider types."""
    MSGRAPH = "msgraph"
    HALOPSA = "halopsa"
    OAUTH = "oauth"

class OAuthCredentials:
    """OAuth credentials for API access."""
    connection_name: str
    access_token: str
    token_type: str
    expires_at: datetime
    refresh_token: str | None
    scopes: str

    def __init__(
        self,
        connection_name: str,
        access_token: str,
        token_type: str,
        expires_at: datetime,
        refresh_token: str | None = None,
        scopes: str = ""
    ) -> None: ...

    def is_expired(self) -> bool:
        """Check if access token is expired."""
        ...

    def get_auth_header(self) -> str:
        """Get Authorization header value (e.g., 'Bearer token...')."""
        ...

# ==================== SDK MODULES ====================

class config:
    """
    Configuration management SDK.

    Provides access to organization-scoped configuration with automatic
    secret resolution from Azure Key Vault.

    Example:
        from bifrost import config

        # Get config value
        api_key = config.get("api_key")

        # Get with default
        timeout = config.get("timeout", default=30)

        # Check if exists
        if config.has("api_key"):
            ...
    """
    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """
        Get configuration value with automatic secret resolution.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value (with secret resolved if secret_ref type)

        Raises:
            KeyError: If secret reference cannot be resolved
            RuntimeError: If no execution context available
        """
        ...

    @staticmethod
    def has(key: str) -> bool:
        """
        Check if configuration key exists.

        Args:
            key: Configuration key

        Returns:
            True if key exists, False otherwise
        """
        ...

class secrets:
    """
    Secret management SDK.

    Provides access to Azure Key Vault secrets scoped to organization.

    Example:
        from bifrost import secrets

        # Get secret
        api_key = await secrets.get("api_key")
    """
    @staticmethod
    async def get(key: str) -> str:
        """
        Get secret from Azure Key Vault.

        Args:
            key: Secret key

        Returns:
            Secret value

        Raises:
            KeyError: If secret not found
            RuntimeError: If no execution context available
        """
        ...

class executions:
    """Execution history operations SDK."""
    ...

class files:
    """Local filesystem operations SDK."""
    ...

class forms:
    """Form management SDK."""
    ...

class organizations:
    """Organization management SDK."""
    ...

class roles:
    """Role and permission management SDK."""
    ...

class storage:
    """Cloud storage operations SDK (Azure Blob Storage)."""
    ...

class workflows:
    """Workflow execution SDK."""
    ...

class oauth:
    """
    OAuth token management SDK.

    Provides access to OAuth tokens with automatic resolution from Azure Key Vault.

    Example:
        from bifrost import oauth

        # Get token
        token = await oauth.get_token("microsoft")
        if token:
            access_token = token["access_token"]
            # Use the token for API calls

        # List configured providers
        providers = await oauth.list_providers()

        # Set a token (admin only)
        await oauth.set_token("microsoft", {
            "access_token": "ya29.xxx",
            "refresh_token": "1//xxx",
            "expires_at": 1234567890,
            "token_type": "Bearer"
        })

        # Delete a token (admin only)
        await oauth.delete_token("microsoft")

        # Refresh a token
        new_token = await oauth.refresh_token("microsoft")
    """
    @staticmethod
    async def get_token(provider: str, org_id: str | None = None) -> dict[str, Any] | None:
        """
        Get OAuth token for a provider.

        Args:
            provider: OAuth provider name (e.g., "microsoft", "google")
            org_id: Organization ID (defaults to current org from context)

        Returns:
            dict | None: OAuth token data (access_token, refresh_token, expires_at, etc.)
                        or None if not found

        Raises:
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    async def set_token(
        provider: str,
        token_data: dict[str, Any],
        org_id: str | None = None
    ) -> None:
        """
        Set OAuth token for a provider.

        Requires: Permission to manage OAuth tokens (typically admin)

        Args:
            provider: OAuth provider name (e.g., "microsoft", "google")
            token_data: OAuth token data (access_token, refresh_token, expires_at, etc.)
            org_id: Organization ID (defaults to current org from context)

        Raises:
            PermissionError: If user lacks permission
            RuntimeError: If no execution context
            ValueError: If token_data is invalid
        """
        ...

    @staticmethod
    async def list_providers(org_id: str | None = None) -> list[str]:
        """
        List all OAuth providers with stored tokens.

        Args:
            org_id: Organization ID (defaults to current org from context)

        Returns:
            list[str]: List of provider names

        Raises:
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    async def delete_token(provider: str, org_id: str | None = None) -> bool:
        """
        Delete OAuth token for a provider.

        Requires: Permission to manage OAuth tokens (typically admin)

        Args:
            provider: OAuth provider name (e.g., "microsoft", "google")
            org_id: Organization ID (defaults to current org from context)

        Returns:
            bool: True if deleted, False if not found

        Raises:
            PermissionError: If user lacks permission
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    async def refresh_token(provider: str, org_id: str | None = None) -> dict[str, Any]:
        """
        Refresh OAuth token for a provider.

        Args:
            provider: OAuth provider name (e.g., "microsoft", "google")
            org_id: Organization ID (defaults to current org from context)

        Returns:
            dict: New OAuth token data

        Raises:
            RuntimeError: If no execution context or refresh fails
            ValueError: If provider not found or refresh token invalid
        """
        ...
