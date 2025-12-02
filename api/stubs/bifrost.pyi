"""
Bifrost Integrations - Type Stubs for Workflow Development

Copy this file to your workflow workspace to get IDE autocomplete and type hints.

Usage:
    1. Copy bifrost.pyi to your workspace folder
    2. Import and use with simplified imports
    3. At runtime, the actual engine implementation is provided by the container

Example (with explicit context parameter):
    from bifrost import workflow, param, ExecutionContext

    @workflow(name="my_workflow", description="...")
    @param("user_email", "string", required=True)
    async def my_workflow(context: ExecutionContext, user_email: str):
        # Direct access to context properties
        org_id = context.org_id
        user = context.email
        return {"success": True}

Example (without context parameter - SDK only):
    from bifrost import workflow, param, config

    @workflow(name="simple_workflow", description="...")
    @param("api_key", "string", required=True)
    async def simple_workflow(api_key: str):
        # Only using SDK functions - no direct context access needed
        endpoint = await config.get("api_endpoint")
        return {"endpoint": endpoint}
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Literal

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
    Context object for workflow execution.

    The context parameter is OPTIONAL in workflow signatures:
    - Include it when you need direct access to org_id, user_id, email, etc.
    - Omit it when only using SDK functions (config, secrets, files, etc.)

    SDK functions (config.get(), secrets.get(), files.read()) can access
    the context implicitly via ContextVar, so they work without the parameter.

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
    execution_mode: str | None = None,  # Auto: "sync" if endpoint_enabled else "async"
    timeout_seconds: int = 300,
    max_duration_seconds: int = 300,
    retry_policy: dict[str, Any] | None = None,
    schedule: str | None = None,
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
        execution_mode: "sync", "async", or None (auto-select based on endpoint_enabled)
        timeout_seconds: Max execution time
        expose_in_forms: Whether workflow can be triggered from forms
        required_permission: Permission required to execute

    Example (with context parameter):
        @workflow(
            name="create_user",
            description="Create a new user in Microsoft 365",
            category="User Management"
        )
        @param("email", "string", required=True)
        @param("first_name", "string", required=True)
        @param("last_name", "string", required=True)
        async def create_user(context: ExecutionContext, email: str, first_name: str, last_name: str):
            # Direct access to context properties
            org_id = context.org_id
            user = context.email
            pass

    Example (without context parameter):
        @workflow(
            name="simple_task",
            description="Simple task using only SDK functions",
            category="Utilities"
        )
        @param("task_name", "string", required=True)
        async def simple_task(task_name: str):
            # SDK functions work without explicit context parameter
            api_key = await secrets.get("api_key")
            endpoint = await config.get("api_endpoint")
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

@dataclass
class Role:
    """Role entity for organization users."""
    id: str
    name: str
    description: str | None
    isActive: bool
    createdBy: str
    createdAt: datetime
    updatedAt: datetime

@dataclass
class Form:
    """Form entity."""
    id: str
    orgId: str
    name: str
    description: str | None
    linkedWorkflow: str
    formSchema: dict[str, Any]
    isActive: bool
    isGlobal: bool
    accessLevel: str | None
    createdBy: str
    createdAt: datetime
    updatedAt: datetime

# ==================== ERRORS ====================

class UserError(Exception):
    """
    Exception that displays its message to end users.

    Use this for validation errors, business logic failures, or any error
    that users should see and understand.
    """
    ...

class WorkflowError(Exception):
    """Base class for workflow-related errors."""
    ...

class ValidationError(WorkflowError):
    """Raised when workflow input validation fails."""
    ...

class IntegrationError(WorkflowError):
    """Raised when integration with external service fails."""
    ...

class ConfigurationError(WorkflowError):
    """Raised when workflow configuration is invalid."""
    ...

# ==================== SDK MODULES ====================

class config:
    """
    Configuration management SDK.

    Provides access to organization-scoped configuration with automatic
    secret resolution.

    Example:
        from bifrost import config

        # Get config value
        api_key = await config.get("api_key")

        # Get with default
        timeout = await config.get("timeout", default=30)

        # List all config for current org
        org_config = await config.list(org_id="org-123")

        # Platform admin: list all orgs' config
        all_configs = await config.list()
    """
    @staticmethod
    async def get(key: str, org_id: str | None = None, default: Any = None) -> Any:
        """
        Get configuration value with automatic secret resolution.

        Args:
            key: Configuration key
            org_id: Organization ID (defaults to current org from context)
            default: Default value if key not found

        Returns:
            Configuration value (with secret resolved if secret_ref type)

        Raises:
            RuntimeError: If no execution context available
        """
        ...

    @staticmethod
    async def set(key: str, value: Any, org_id: str | None = None) -> None:
        """
        Set configuration value.

        Args:
            key: Configuration key
            value: Configuration value (must be JSON-serializable)
            org_id: Organization ID (defaults to current org from context)

        Raises:
            RuntimeError: If no execution context
            ValueError: If value is not JSON-serializable
        """
        ...

    @staticmethod
    async def list(org_id: str | None = None) -> dict[str, Any] | dict[str, dict[str, Any]]:
        """
        List configuration key-value pairs.

        Behavior depends on context and parameters:
        - If org_id is specified: Returns config for that specific org
        - If org_id is None and user is platform admin: Returns all configs across all orgs
        - If org_id is None and user is not admin: Returns config for current org

        Args:
            org_id: Organization ID (optional, defaults to all orgs for admins)

        Returns:
            - Single org: dict[str, Any] - Configuration key-value pairs
            - All orgs (admin): dict[str, dict[str, Any]] - Mapping of org_id to config dict

        Raises:
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    async def delete(key: str, org_id: str | None = None) -> bool:
        """
        Delete configuration value.

        Args:
            key: Configuration key
            org_id: Organization ID (defaults to current org from context)

        Returns:
            bool: True if deleted, False if not found

        Raises:
            RuntimeError: If no execution context
        """
        ...

class secrets:
    """
    Secret management SDK.

    Provides access to encrypted secrets stored in PostgreSQL.

    Example:
        from bifrost import secrets

        # Get secret
        api_key = await secrets.get("stripe_api_key")

        # Set secret
        await secrets.set("stripe_api_key", "sk_live_xxxxx")

        # List secret keys (not values)
        keys = await secrets.list()

        # Delete secret
        await secrets.delete("old_api_key")
    """
    @staticmethod
    async def get(key: str) -> str | None:
        """
        Get decrypted secret value.

        Args:
            key: Secret key name

        Returns:
            str | None: Decrypted secret value, or None if not found

        Raises:
            RuntimeError: If no execution context available
        """
        ...

    @staticmethod
    async def set(key: str, value: str) -> None:
        """
        Set encrypted secret value.

        Requires: Permission to manage secrets (typically admin)

        Args:
            key: Secret key name
            value: Secret value (will be encrypted)

        Raises:
            PermissionError: If user lacks permission
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    async def list(org_id: str | None = None) -> list[str]:
        """
        List all secret keys (NOT values - keys only for security).

        Args:
            org_id: Organization ID to filter by (optional)

        Returns:
            list[str]: List of secret keys

        Raises:
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    async def delete(key: str) -> bool:
        """
        Delete secret.

        Requires: Permission to manage secrets (typically admin)

        Args:
            key: Secret key name

        Returns:
            bool: True if deleted, False if not found

        Raises:
            PermissionError: If user lacks permission
            RuntimeError: If no execution context
        """
        ...

class oauth:
    """
    OAuth token management SDK.

    Provides access to OAuth connections and tokens stored in PostgreSQL.

    Example:
        from bifrost import oauth

        # Get OAuth connection (includes tokens and credentials)
        conn = await oauth.get("microsoft")
        if conn:
            access_token = conn["access_token"]
            # For cross-tenant operations, also available:
            # conn["client_id"], conn["client_secret"], conn["refresh_token"]

        # List configured providers
        providers = await oauth.list_providers()

        # Delete a connection (admin only)
        await oauth.delete_token("microsoft")

        # Refresh a token
        new_token = await oauth.refresh_token("microsoft")
    """
    @staticmethod
    async def get(provider: str, org_id: str | None = None) -> dict[str, Any] | None:
        """
        Get OAuth connection configuration for a provider.

        Returns the full OAuth configuration including credentials needed for
        custom token operations (e.g., cross-tenant exchanges).

        Args:
            provider: OAuth provider/connection name (e.g., "microsoft", "partner_center")
            org_id: Organization ID (defaults to current org from context)

        Returns:
            dict | None: OAuth connection config with keys:
                - connection_name: str
                - client_id: str
                - client_secret: str | None (if configured)
                - authorization_url: str | None
                - token_url: str
                - scopes: str
                - refresh_token: str | None (if available)
                - access_token: str | None (if available)
                - expires_at: str | None (ISO format, if available)
            Returns None if connection not found.

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

class files:
    """
    Local filesystem operations SDK.

    Provides safe file access within workspace/files/ and temp directories.
    All paths are sandboxed to prevent access outside allowed directories.

    Location Options:
    - "temp": Temporary files (cleared periodically, for execution-scoped data)
    - "workspace": Persistent workspace files (survives across executions)

    Example:
        from bifrost import files

        # Read a file
        content = files.read("data/customers.csv")

        # Write to temp (execution-scoped)
        files.write("temp-data.txt", "content", location="temp")

        # Write to workspace (persistent)
        files.write("exports/report.csv", data)

        # Check if file exists
        if files.exists("data/input.csv"):
            data = files.read("data/input.csv")
    """
    @staticmethod
    def read(path: str, location: Literal["temp", "workspace"] = "workspace") -> str:
        """
        Read a text file.

        Args:
            path: File path (relative or absolute)
            location: Storage location ("temp" or "workspace", default: "workspace")

        Returns:
            str: File contents

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If path is outside allowed directories
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    def read_bytes(path: str, location: Literal["temp", "workspace"] = "workspace") -> bytes:
        """
        Read a binary file.

        Args:
            path: File path (relative or absolute)
            location: Storage location ("temp" or "workspace", default: "workspace")

        Returns:
            bytes: File contents

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If path is outside allowed directories
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    def write(path: str, content: str, location: Literal["temp", "workspace"] = "workspace") -> None:
        """
        Write text to a file.

        Args:
            path: File path (relative or absolute)
            content: Text content to write
            location: Storage location ("temp" or "workspace", default: "workspace")

        Raises:
            ValueError: If path is outside allowed directories
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    def write_bytes(path: str, content: bytes, location: Literal["temp", "workspace"] = "workspace") -> None:
        """
        Write binary data to a file.

        Args:
            path: File path (relative or absolute)
            content: Binary content to write
            location: Storage location ("temp" or "workspace", default: "workspace")

        Raises:
            ValueError: If path is outside allowed directories
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    def list(directory: str = "", location: Literal["temp", "workspace"] = "workspace") -> list[str]:
        """
        List files in a directory.

        Args:
            directory: Directory path (relative, default: root)
            location: Storage location ("temp" or "workspace", default: "workspace")

        Returns:
            list[str]: List of file and directory names

        Raises:
            FileNotFoundError: If directory doesn't exist
            ValueError: If path is outside allowed directories
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    def delete(path: str, location: Literal["temp", "workspace"] = "workspace") -> None:
        """
        Delete a file or directory.

        Args:
            path: File or directory path (relative or absolute)
            location: Storage location ("temp" or "workspace", default: "workspace")

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If path is outside allowed directories
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    def exists(path: str, location: Literal["temp", "workspace"] = "workspace") -> bool:
        """
        Check if a file or directory exists.

        Args:
            path: File or directory path (relative or absolute)
            location: Storage location ("temp" or "workspace", default: "workspace")

        Returns:
            bool: True if path exists

        Raises:
            ValueError: If path is outside allowed directories
            RuntimeError: If no execution context
        """
        ...

class organizations:
    """
    Organization management SDK.

    Provides CRUD operations for organizations.
    Most operations require platform admin privileges.

    Example:
        from bifrost import organizations

        # List all organizations (admin only)
        orgs = await organizations.list()

        # Get specific organization
        org = await organizations.get("org-123")

        # Create new organization (admin only)
        new_org = await organizations.create("Acme Corp", domain="acme.com")
    """
    @staticmethod
    async def create(name: str, domain: str | None = None, is_active: bool = True) -> Organization:
        """
        Create a new organization.

        Requires: Platform admin privileges

        Args:
            name: Organization name
            domain: Organization domain (optional)
            is_active: Whether the organization is active (default: True)

        Returns:
            Organization: Created organization object

        Raises:
            PermissionError: If user is not platform admin
            ValueError: If validation fails
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    async def get(org_id: str) -> Organization:
        """
        Get organization by ID.

        Args:
            org_id: Organization ID

        Returns:
            Organization: Organization object

        Raises:
            ValueError: If organization not found
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    async def list() -> list[Organization]:
        """
        List all organizations.

        Requires: Platform admin privileges

        Returns:
            list[Organization]: List of organization objects

        Raises:
            PermissionError: If user is not platform admin
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    async def update(org_id: str, **updates: Any) -> Organization:
        """
        Update an organization.

        Requires: Platform admin privileges

        Args:
            org_id: Organization ID
            **updates: Fields to update (name, domain, isActive)

        Returns:
            Organization: Updated organization object

        Raises:
            PermissionError: If user is not platform admin
            ValueError: If organization not found or validation fails
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    async def delete(org_id: str) -> bool:
        """
        Delete an organization.

        Requires: Platform admin privileges

        Args:
            org_id: Organization ID

        Returns:
            bool: True if organization was deleted

        Raises:
            PermissionError: If user is not platform admin
            ValueError: If organization not found
            RuntimeError: If no execution context
        """
        ...

class roles:
    """
    Role and permission management SDK.

    Provides CRUD operations for roles and user/form assignments.

    Example:
        from bifrost import roles

        # List all roles
        all_roles = await roles.list()

        # Create a new role
        role = await roles.create(
            "Customer Manager",
            description="Can manage customer data",
            permissions=["customers.read", "customers.write"]
        )

        # Assign users to role
        await roles.assign_users("role-123", ["user-1", "user-2"])
    """
    @staticmethod
    async def create(name: str, description: str = "", permissions: list[str] | None = None) -> Role:
        """
        Create a new role.

        Requires: Platform admin or organization admin privileges

        Args:
            name: Role name
            description: Role description (optional)
            permissions: List of permission strings (optional)

        Returns:
            Role: Created role object

        Raises:
            PermissionError: If user lacks permission
            ValueError: If validation fails
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    async def get(role_id: str) -> Role:
        """
        Get role by ID.

        Args:
            role_id: Role ID

        Returns:
            Role: Role object

        Raises:
            ValueError: If role not found
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    async def list() -> list[Role]:
        """
        List all roles in the current organization.

        Returns:
            list[Role]: List of role objects

        Raises:
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    async def update(role_id: str, **updates: Any) -> Role:
        """
        Update a role.

        Requires: Platform admin or organization admin privileges

        Args:
            role_id: Role ID
            **updates: Fields to update (name, description, permissions)

        Returns:
            Role: Updated role object

        Raises:
            PermissionError: If user lacks permission
            ValueError: If role not found or validation fails
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    async def delete(role_id: str) -> None:
        """
        Delete a role.

        Requires: Platform admin or organization admin privileges

        Args:
            role_id: Role ID

        Raises:
            PermissionError: If user lacks permission
            ValueError: If role not found
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    async def list_users(role_id: str) -> list[str]:
        """
        List all user IDs assigned to a role.

        Args:
            role_id: Role ID

        Returns:
            list[str]: List of user IDs

        Raises:
            ValueError: If role not found
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    async def list_forms(role_id: str) -> list[str]:
        """
        List all form IDs assigned to a role.

        Args:
            role_id: Role ID

        Returns:
            list[str]: List of form IDs

        Raises:
            ValueError: If role not found
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    async def assign_users(role_id: str, user_ids: list[str]) -> None:
        """
        Assign users to a role.

        Requires: Platform admin or organization admin privileges

        Args:
            role_id: Role ID
            user_ids: List of user IDs to assign

        Raises:
            PermissionError: If user lacks permission
            ValueError: If role or users not found
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    async def assign_forms(role_id: str, form_ids: list[str]) -> None:
        """
        Assign forms to a role.

        Requires: Platform admin or organization admin privileges

        Args:
            role_id: Role ID
            form_ids: List of form IDs to assign

        Raises:
            PermissionError: If user lacks permission
            ValueError: If role or forms not found
            RuntimeError: If no execution context
        """
        ...

class forms:
    """
    Form management SDK.

    Provides read-only access to form definitions.

    Example:
        from bifrost import forms

        # List all forms
        all_forms = await forms.list()

        # Get specific form
        form = await forms.get("form-123")
        print(form.name)
    """
    @staticmethod
    async def list() -> list[Form]:
        """
        List all forms available to the current user.

        Returns:
            list[Form]: List of form objects

        Raises:
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    async def get(form_id: str) -> Form:
        """
        Get a form definition by ID.

        Args:
            form_id: Form ID

        Returns:
            Form: Form object

        Raises:
            ValueError: If form not found
            RuntimeError: If no execution context
        """
        ...

class executions:
    """
    Execution history operations SDK.

    Provides access to workflow execution history.

    Example:
        from bifrost import executions

        # List recent executions
        recent = await executions.list(limit=10)

        # List failed executions
        failed = await executions.list(status="Failed")

        # Get specific execution
        exec_details = await executions.get("exec-123")
    """
    @staticmethod
    async def list(
        workflow_name: str | None = None,
        status: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """
        List workflow executions with filtering.

        Platform admins see all executions in their scope.
        Regular users see only their own executions.

        Args:
            workflow_name: Filter by workflow name (optional)
            status: Filter by status (optional)
            start_date: Filter by start date in ISO format (optional)
            end_date: Filter by end date in ISO format (optional)
            limit: Maximum number of results (default: 50, max: 1000)

        Returns:
            list[dict]: List of execution dictionaries

        Raises:
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    async def get(execution_id: str) -> dict[str, Any]:
        """
        Get execution details by ID.

        Platform admins can view any execution in their scope.
        Regular users can only view their own executions.

        Args:
            execution_id: Execution ID (UUID)

        Returns:
            dict: Execution details

        Raises:
            ValueError: If execution not found or access denied
            RuntimeError: If no execution context
        """
        ...

class workflows:
    """
    Workflow execution SDK.

    Allows workflows to trigger other workflows and query execution status.

    Example:
        from bifrost import workflows

        # Execute another workflow
        result = workflows.execute("process_order", {"order_id": "12345"})

        # List all workflows
        wf_list = workflows.list()

        # Get execution details
        execution = workflows.get("exec-123")
    """
    @staticmethod
    def execute(workflow_name: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Execute another workflow programmatically.

        Args:
            workflow_name: Name of workflow to execute
            parameters: Workflow parameters (optional)

        Returns:
            dict: Execution result

        Raises:
            ValueError: If workflow not found
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    def list() -> list[dict[str, Any]]:
        """
        List all available workflows.

        Returns:
            list[dict]: List of workflow metadata

        Raises:
            RuntimeError: If no execution context
        """
        ...

    @staticmethod
    def get(execution_id: str) -> dict[str, Any]:
        """
        Get execution details for a workflow.

        Args:
            execution_id: Execution ID

        Returns:
            dict: Execution details including status, result, logs

        Raises:
            ValueError: If execution not found
            RuntimeError: If no execution context
        """
        ...
