"""
Bifrost Integrations - Type Stubs for Workflow Development

Copy this file to your workflow workspace to get IDE autocomplete and type hints.

Usage:
    1. Copy bifrost.pyi to your workspace folder
    2. Import and use with simplified imports
    3. At runtime, the actual engine implementation is provided by the container

Example:
    from bifrost import workflow, param, OrganizationContext

    @workflow(name="my_workflow", description="...")
    @param("user_email", "string", required=True)
    async def my_workflow(context: OrganizationContext, user_email: str):
        context.log("info", f"Processing {user_email}")
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
    org_id: str
    name: str
    is_active: bool

@dataclass
class Caller:
    """User who triggered the workflow execution."""
    user_id: str
    email: str
    name: str

class OrganizationContext:
    """
    Context object passed to all workflows.

    Provides access to:
    - Organization information (id, name)
    - Execution metadata (execution_id, caller)
    - Configuration (key-value pairs with secret resolution)
    - OAuth connections (pre-authenticated credentials)
    - State tracking (checkpoints, logs, variables)
    """

    org: Organization | None
    caller: Caller
    execution_id: str

    def __init__(
        self,
        org: Organization | None,
        config: dict[str, Any],
        caller: Caller,
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

    # Caller properties
    @property
    def executed_by(self) -> str:
        """User ID who triggered this execution."""
        ...

    @property
    def executed_by_email(self) -> str:
        """Email of user who triggered this execution."""
        ...

    @property
    def executed_by_name(self) -> str:
        """Display name of user who triggered this execution."""
        ...

    # Configuration
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with automatic secret resolution.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value (with secrets resolved from Key Vault)
        """
        ...

    def has_config(self, key: str) -> bool:
        """Check if configuration key exists."""
        ...

    # OAuth connections
    async def get_oauth_connection(self, connection_name: str) -> OAuthCredentials:
        """
        Get OAuth credentials for a connection.

        Retrieves OAuth credentials from storage and Key Vault.
        Works with both org-scoped and GLOBAL contexts.

        Args:
            connection_name: Name of the OAuth connection

        Returns:
            OAuthCredentials object with access_token and metadata

        Raises:
            ValueError: If connection not found or not authorized
        """
        ...

    async def get_secret(self, key: str) -> str:
        """
        Get secret from Azure Key Vault.

        Args:
            key: Secret key

        Returns:
            Secret value

        Raises:
            KeyError: If secret not found
        """
        ...

    # State tracking
    def save_checkpoint(self, name: str, data: dict[str, Any]) -> None:
        """
        Save a state checkpoint during workflow execution.

        Useful for debugging and understanding execution flow.

        Args:
            name: Checkpoint name
            data: Checkpoint data (will be sanitized)
        """
        ...

    def set_variable(self, key: str, value: Any) -> None:
        """
        Set a workflow variable (persisted in execution record).

        Args:
            key: Variable name
            value: Variable value (will be sanitized)
        """
        ...

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a workflow variable."""
        ...

    def info(self, message: str, data: dict[str, Any] | None = None) -> None:
        """
        Log an info-level message.

        Args:
            message: Log message
            data: Optional structured data dictionary

        Examples:
            context.info("Processing user")
            context.info("User created", {"user_id": "123", "email": "user@example.com"})
        """
        ...

    def warning(self, message: str, data: dict[str, Any] | None = None) -> None:
        """
        Log a warning-level message.

        Args:
            message: Log message
            data: Optional structured data dictionary

        Examples:
            context.warning("Rate limit approaching")
            context.warning("OAuth token expired", {"expires_at": "2024-01-01"})
        """
        ...

    def error(self, message: str, data: dict[str, Any] | None = None) -> None:
        """
        Log an error-level message.

        Args:
            message: Log message
            data: Optional structured data dictionary

        Examples:
            context.error("API call failed")
            context.error("Connection timeout", {"endpoint": "/users", "timeout": 30})
        """
        ...

    def debug(self, message: str, data: dict[str, Any] | None = None) -> None:
        """
        Log a debug-level message.

        Args:
            message: Log message
            data: Optional structured data dictionary

        Examples:
            context.debug("Request details", {"headers": headers, "body": body})
        """
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
