# Workspace API Reference (T063)

Complete reference for the public API available to workspace workflow code.

## Table of Contents

- [Overview](#overview)
- [Allowed Imports](#allowed-imports)
- [Decorators](#decorators)
- [Context](#context)
- [Error Handling](#error-handling)
- [Models](#models)
- [Best Practices](#best-practices)

---

## Overview

Workspace workflows have access to a **carefully curated public API** that provides all necessary functionality while maintaining security boundaries.

### Import Restrictions

Workspace code can **ONLY** import from these modules:

```python
from engine.shared.decorators import ...  # Workflow registration
from engine.shared.context import ...     # Organization context
from engine.shared.error_handling import ...  # Exception types
from engine.shared.models import ...      # Pydantic models
```

**Attempting to import any other `engine.*` modules will result in an `ImportError`.**

---

## Allowed Imports

### 1. `engine.shared.decorators`

Decorators for registering workflows, parameters, and data providers.

```python
from engine.shared.decorators import workflow, param, data_provider
```

### 2. `engine.shared.context`

Organization context and caller information.

```python
from engine.shared.context import OrganizationContext, Organization, Caller
```

### 3. `engine.shared.error_handling`

Exception types for structured error reporting.

```python
from engine.shared.error_handling import (
    WorkflowException,
    ValidationError,
    IntegrationError,
    TimeoutError
)
```

### 4. `engine.shared.models`

Pydantic models for type-safe data structures.

```python
from engine.shared.models import (
    WorkflowExecutionResponse,
    ExecutionStatus,
    ErrorResponse
)
```

---

## Decorators

### `@workflow`

Register a function as an executable workflow.

**Signature:**
```python
@workflow(
    name: str,
    description: str,
    category: str = "General",
    requires_org: bool = True
)
```

**Parameters:**
- `name` (str): Unique workflow identifier (used in API calls)
- `description` (str): Human-readable description
- `category` (str, optional): Workflow category for UI grouping
- `requires_org` (bool, optional): Whether org context is required (default: True)

**Example:**
```python
@workflow(
    name="create_user",
    description="Create a new user in the system",
    category="User Management"
)
async def create_user(context: OrganizationContext, ...):
    ...
```

**Requirements:**
- Function must be `async`
- First parameter must be `OrganizationContext` (if `requires_org=True`)
- Must return JSON-serializable data (dict, list, str, int, etc.)

---

### `@param`

Define a workflow parameter with validation.

**Signature:**
```python
@param(
    name: str,
    param_type: type,
    description: str,
    required: bool = True,
    default: Any = None,
    validation: dict = None
)
```

**Parameters:**
- `name` (str): Parameter name (must match function argument)
- `param_type` (type): Python type (`str`, `int`, `bool`, `dict`, `list`)
- `description` (str): Parameter description for UI/docs
- `required` (bool, optional): Whether parameter is required
- `default` (Any, optional): Default value if not provided
- `validation` (dict, optional): Validation rules (e.g., `{"min": 1, "max": 100}`)

**Example:**
```python
@workflow(name="send_email", description="Send email notification")
@param("recipient", str, "Email recipient address", required=True)
@param("subject", str, "Email subject line", required=True)
@param("body", str, "Email body content", required=True)
@param("cc", list, "CC recipients", required=False, default=[])
async def send_email(
    context: OrganizationContext,
    recipient: str,
    subject: str,
    body: str,
    cc: list
):
    ...
```

**Validation Rules:**
- `min`, `max`: For numeric types
- `min_length`, `max_length`: For strings and lists
- `pattern`: Regex pattern for strings
- `enum`: List of allowed values

---

### `@data_provider`

Register a data provider for dynamic option lists.

**Signature:**
```python
@data_provider(
    name: str,
    description: str
)
```

**Example:**
```python
@data_provider(
    name="list_organizations",
    description="List all organizations"
)
async def list_organizations(context: OrganizationContext):
    return [
        {"value": "org-1", "label": "Organization 1"},
        {"value": "org-2", "label": "Organization 2"}
    ]
```

**Requirements:**
- Must return list of `{"value": str, "label": str}` dicts
- Used for dynamic dropdowns in UI

---

## Context

### `OrganizationContext`

Provides access to organization data, configuration, and execution utilities.

**Attributes:**
```python
class OrganizationContext:
    org: Organization           # Organization info
    config: Dict[str, Any]     # Org configuration
    caller: Caller             # Who triggered the workflow
    execution_id: str          # Unique execution ID
```

**Methods:**

#### `log(level: str, message: str, data: dict = None) -> None`

Log a message for this execution with structured data.

```python
context.log("info", "Processing user data", {"user_id": "123", "action": "create"})
context.log("warning", "Rate limit approaching", {"remaining": 10, "reset_time": "2024-01-01T12:00:00Z"})
context.log("error", "API call failed", {"error": "Connection timeout", "endpoint": "/users"})
```

**Log Levels**: `"info"`, `"warning"`, `"error"`, `"debug"`

#### `set_variable(key: str, value: Any) -> None`

Store a variable for later retrieval (persisted for execution duration).

```python
context.set_variable("user_count", 42)
context.set_variable("api_response", {"status": "success"})
context.set_variable("processing_stage", "validation")
```

#### `get_variable(key: str, default: Any = None) -> Any`

Retrieve a stored variable.

```python
user_count = context.get_variable("user_count", default=0)
processing_stage = context.get_variable("processing_stage", "unknown")
```

#### `save_checkpoint(name: str, data: dict = None) -> None`

Save workflow checkpoint for debugging and recovery.

```python
context.save_checkpoint("user_validation", {
    "email": "user@example.com",
    "is_valid": True,
    "timestamp": "2024-01-01T12:00:00Z"
})

context.save_checkpoint("api_call_complete", {
    "endpoint": "/users",
    "status_code": 201,
    "response_id": "user-123"
})
```

#### `get_config(key: str, default: Any = None) -> Any`

Get organization configuration value with automatic secret resolution.

```python
# Regular config
api_url = context.get_config("api_url", "https://default.api.com")
timeout = context.get_config("request_timeout", 30)

# Secret resolution (automatically fetches from Key Vault)
api_key = context.get_config("api_key")  # Fetches from Key Vault if secret_ref
db_password = context.get_config("database_password")
```

#### `has_config(key: str) -> bool`

Check if configuration key exists.

```python
if context.has_config("feature_flag_new_ui"):
    # Use new UI feature
    pass

if not context.has_config("api_endpoint"):
    raise ConfigurationError("API endpoint not configured")
```

#### `get_secret(secret_name: str) -> Awaitable[str]`

Get secret directly from Key Vault (org-scoped: {org_id}--{secret_name}).

```python
# Secrets are automatically scoped to organization
api_key = await context.get_secret("my_api_key")
db_connection_string = await context.get_secret("database_connection")
oauth_client_secret = await context.get_secret("oauth_client_secret")
```

#### `get_oauth_connection(provider_name: str) -> Awaitable[OAuthCredentials]`

Get pre-authenticated OAuth credentials for external services.

```python
# Get OAuth credentials for HaloPSA
halo_creds = await context.get_oauth_connection("HaloPSA")
headers = {"Authorization": halo_creds.get_auth_header()}

# Check if token needs refresh
if halo_creds.is_expired():
    context.log("warning", "OAuth token expired, will refresh")

# Use in API calls
async with aiohttp.ClientSession() as session:
    async with session.get("https://api.halopsa.com/tickets", headers=headers) as response:
        data = await response.json()
```

#### `get_integration(integration_name: str) -> IntegrationClient`

Get pre-authenticated integration client.

```python
# Microsoft Graph integration
graph = context.get_integration("msgraph")
users = await graph.get_users()
user_details = await graph.get_user("user@example.com")

# HaloPSA integration
halo = context.get_integration("halopsa")
tickets = await halo.get_tickets()
client = await halo.get_client("client-123")

# Custom integrations (if configured)
custom_api = context.get_integration("custom_api")
data = await custom_api.get_data("/endpoint")
```

---

### `Organization`

Organization information.

**Attributes:**
```python
class Organization:
    org_id: str        # Organization ID
    name: str          # Organization name
    tenant_id: str     # Azure AD tenant ID (optional)
    is_active: bool    # Whether org is active
```

---

### `Caller`

Information about who triggered the workflow.

**Attributes:**
```python
class Caller:
    user_id: str       # User ID (or "function_key:name" for function key auth)
    email: str         # User email
    name: str          # User display name
```

**Example Usage:**
```python
async def my_workflow(context: OrganizationContext):
    if context.caller.email == "admin@example.com":
        context.log("Admin user detected")

    # Access org info
    context.log(f"Running for org: {context.org.name}")

    # Access config
    api_endpoint = context.config.get("api_endpoint")
```

---

## Error Handling

Structured exceptions for workflow errors.

### `WorkflowException`

Base exception for all workflow errors.

**Signature:**
```python
WorkflowException(
    message: str,
    error_type: str = "WorkflowError",
    details: dict = None
)
```

**Example:**
```python
raise WorkflowException(
    message="User not found",
    error_type="NotFoundError",
    details={"user_id": "12345"}
)
```

---

### `ValidationError`

Input validation failures (returns HTTP 400).

**Example:**
```python
from engine.shared.error_handling import ValidationError

if not email.endswith("@example.com"):
    raise ValidationError(
        message="Invalid email domain",
        details={"email": email, "required_domain": "@example.com"}
    )
```

---

### `IntegrationError`

External API call failures (returns HTTP 500).

**Example:**
```python
from engine.shared.error_handling import IntegrationError

try:
    response = await api_client.get("/users")
except Exception as e:
    raise IntegrationError(
        message=f"Failed to fetch users from API: {str(e)}",
        details={"service": "UserAPI", "error": str(e)}
    )
```

---

### `TimeoutError`

Operation timeout (returns HTTP 500).

**Example:**
```python
from engine.shared.error_handling import TimeoutError
import asyncio

try:
    result = await asyncio.wait_for(long_operation(), timeout=30.0)
except asyncio.TimeoutError:
    raise TimeoutError(
        message="Operation timed out after 30 seconds",
        details={"operation": "long_operation", "timeout_seconds": 30}
    )
```

---

## Models

Pydantic models for type-safe data structures.

### `WorkflowExecutionResponse`

Response model for workflow executions (automatically generated by engine).

```python
class WorkflowExecutionResponse(BaseModel):
    executionId: str
    status: ExecutionStatus
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    errorType: Optional[str]
    details: Optional[Dict[str, Any]]
    durationMs: int
    startedAt: datetime
    completedAt: datetime
```

### `ExecutionStatus`

Workflow execution status enum.

```python
class ExecutionStatus(str, Enum):
    SUCCESS = "Success"
    RUNNING = "Running"
    FAILED = "Failed"
```

---

## Best Practices

### 1. **Always Use Type Hints**

```python
# ✓ GOOD
async def create_user(
    context: OrganizationContext,
    email: str,
    name: str
) -> dict:
    return {"user_id": "123", "email": email}

# ✗ BAD
async def create_user(context, email, name):
    return {"user_id": "123", "email": email}
```

### 2. **Log Important Steps**

```python
context.log("Starting user creation")
context.log(f"Creating user: {email}")
context.log("User created successfully")
```

### 3. **Use Structured Error Handling**

```python
# ✓ GOOD
if not email:
    raise ValidationError(
        message="Email is required",
        details={"field": "email"}
    )

# ✗ BAD
if not email:
    raise Exception("Email is required")
```

### 4. **Save State for Complex Workflows**

```python
context.save_state({"step": "validation", "records": 100})
# ... do work ...
context.save_state({"step": "processing", "records": 100})
# ... do work ...
context.save_state({"step": "complete", "records": 100})
```

### 5. **Log Integration Calls**

```python
start_time = time.time()
response = await api_client.get("/users")
duration_ms = int((time.time() - start_time) * 1000)

context.log_integration_call(
    service="UserAPI",
    endpoint="/users",
    method="GET",
    status_code=response.status,
    duration_ms=duration_ms
)
```

### 6. **Return JSON-Serializable Data**

```python
# ✓ GOOD
return {
    "user_id": "123",
    "created_at": datetime.now().isoformat(),
    "success": True
}

# ✗ BAD - datetime not JSON-serializable
return {
    "created_at": datetime.now()  # Will fail!
}
```

### 7. **Don't Import Engine Internals**

```python
# ✓ GOOD
from engine.shared.decorators import workflow
from engine.shared.context import OrganizationContext

# ✗ BAD - Will raise ImportError
from engine.shared.storage import get_organization
from engine.execute import execute_workflow
```

---

## Complete Example

```python
"""
Example workflow demonstrating best practices
"""

from engine.shared.decorators import workflow, param
from engine.shared.context import OrganizationContext
from engine.shared.error_handling import ValidationError, IntegrationError
import aiohttp


@workflow(
    name="create_user",
    description="Create a new user in external system",
    category="User Management"
)
@param("email", str, "User email address", required=True)
@param("name", str, "User full name", required=True)
@param("role", str, "User role", required=False, default="OrgUser")
async def create_user(
    context: OrganizationContext,
    email: str,
    name: str,
    role: str
) -> dict:
    """
    Create a new user in the external user management system.

    Args:
        context: Organization context
        email: User email address
        name: User full name
        role: User role (default: OrgUser)

    Returns:
        dict: Created user information

    Raises:
        ValidationError: If input validation fails
        IntegrationError: If API call fails
    """
    context.log(f"Creating user: {email}")

    # Validate input
    if not email.endswith(f"@{context.org.name}.com"):
        raise ValidationError(
            message=f"Email must be from {context.org.name}.com domain",
            details={"email": email, "org": context.org.name}
        )

    # Save initial state
    context.save_state({
        "step": "validation_complete",
        "email": email,
        "role": role
    })

    # Get API endpoint from org config
    api_endpoint = context.config.get("api_endpoint")
    if not api_endpoint:
        raise ValidationError(
            message="API endpoint not configured for organization",
            details={"org_id": context.org.org_id}
        )

    # Call external API
    context.log("Calling user creation API")

    try:
        import time
        start_time = time.time()

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_endpoint}/users",
                json={"email": email, "name": name, "role": role}
            ) as response:
                duration_ms = int((time.time() - start_time) * 1000)

                # Log integration call
                context.log_integration_call(
                    service="UserAPI",
                    endpoint="/users",
                    method="POST",
                    status_code=response.status,
                    duration_ms=duration_ms
                )

                if response.status != 201:
                    raise IntegrationError(
                        message=f"User creation failed with status {response.status}",
                        details={"status_code": response.status}
                    )

                user_data = await response.json()

        context.save_state({"step": "api_call_complete", "user_id": user_data["id"]})
        context.log(f"User created successfully: {user_data['id']}")

        return {
            "user_id": user_data["id"],
            "email": email,
            "name": name,
            "role": role,
            "created_by": context.caller.email,
            "org_id": context.org.org_id
        }

    except aiohttp.ClientError as e:
        raise IntegrationError(
            message=f"Failed to connect to user API: {str(e)}",
            details={"error": str(e), "api_endpoint": api_endpoint}
        )
```

---

## Additional Resources

- **Local Development Guide**: `/docs/local-development.md`
- **Migration Guide**: `/docs/migration-guide.md`
- **Troubleshooting**: `/docs/troubleshooting.md`

---

## Getting Help

If you encounter import errors or need functionality not available in the public API:

1. **Check this documentation** - Ensure you're using allowed imports
2. **Review examples** - See `/workspace/examples/` for working code
3. **Read error messages** - Import errors include guidance on allowed imports
4. **Contact the platform team** - Request API additions if needed

**Remember**: The import restrictions exist for security and stability. All necessary functionality is available through the public API.
