# Workflow Development Guide

This comprehensive guide covers everything you need to know about developing workflows in the Bifrost Integrations platform.

## Table of Contents

-   [Getting Started](#getting-started)
-   [Workflow Structure](#workflow-structure)
-   [Parameters and Validation](#parameters-and-validation)
-   [Context API](#context-api)
-   [Error Handling](#error-handling)
-   [Data Providers](#data-providers)
-   [Integrations](#integrations)
-   [Testing](#testing)
-   [Best Practices](#best-practices)
-   [Advanced Patterns](#advanced-patterns)
-   [HTTP Endpoints](#http-endpoints)
    -   [Exposing Workflows as Endpoints](#exposing-workflows-as-endpoints)
    -   [Endpoint Configuration](#endpoint-configuration)
    -   [Calling HTTP Endpoints](#calling-http-endpoints)
    -   [API Key Management](#api-key-management)
    -   [OpenAPI Documentation](#openapi-documentation)
    -   [Webhook Integration Examples](#webhook-integration-examples)
    -   [REST API Patterns](#rest-api-patterns)
    -   [Public Endpoints (Webhooks)](#public-endpoints-webhooks)
    -   [Best Practices for HTTP Endpoints](#best-practices-for-http-endpoints)

---

## Getting Started

### Prerequisites

-   Python 3.11 or higher
-   Understanding of async/await patterns
-   Basic knowledge of REST APIs
-   Familiarity with JSON data structures

### Development Environment Setup

1. **Clone and Setup**

    ```bash
    git clone https://github.com/your-org/bifrost-integrations.git
    cd bifrost-integrations/workflows
    pip install -r requirements.txt
    ```

2. **Start Local Development**

    ```bash
    # Start Azurite (local storage)
    azurite --silent --location /tmp/azurite

    # Seed test data
    python scripts/seed_azurite.py

    # Start Azure Functions
    func start
    ```

3. **Verify Setup**
    ```bash
    curl http://localhost:7071/api/health
    # Should return: {"status": "healthy"}
    ```

### Your First Workflow

Create `/workspace/workflows/examples/my_first_workflow.py`:

```python
from engine.shared.decorators import workflow, param
from engine.shared.context import OrganizationContext

@workflow(
    name="my_first_workflow",
    description="A simple example workflow",
    category="examples"
)
@param("message", "string", "Message to process", required=True)
async def my_first_workflow(context: OrganizationContext, message: str):
    """
    Process a simple message and return a response.
    """
    context.log("info", f"Processing message: {message}")

    result = {
        "original": message,
        "processed": message.upper(),
        "length": len(message),
        "timestamp": context.execution_id
    }

    context.save_checkpoint("processing_complete", result)
    return result
```

Test your workflow:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org-active" \
  -H "x-functions-key: test" \
  -d '{"message": "Hello World"}' \
  http://localhost:7071/api/workflows/my_first_workflow
```

---

## Workflow Structure

### Basic Workflow Anatomy

Every workflow follows this structure:

```python
# 1. Imports
from engine.shared.decorators import workflow, param
from engine.shared.context import OrganizationContext
from engine.shared.error_handling import WorkflowException

# 2. Workflow Decorator
@workflow(
    name="workflow_name",           # Unique identifier
    description="Human readable description",
    category="user_management",     # UI category
    execution_mode="sync",          # sync, async, scheduled
    timeout_seconds=300,           # Max execution time
    schedule="0 9 * * *",          # Cron schedule (if scheduled)
    expose_in_forms=True,          # Can be called from forms
    requires_org=True,             # Requires organization context
    tags=["m365", "automation"]    # Optional tags
)

# 3. Parameter Decorators
@param("param1", "string", "Parameter description", required=True)
@param("param2", "int", "Number parameter", default_value=42)
@param("param3", "bool", "Boolean parameter", default_value=False)

# 4. Function Definition
async def workflow_name(
    context: OrganizationContext,  # Always first parameter
    param1: str,                   # Match parameter names
    param2: int = 42,
    param3: bool = False
) -> dict:                        # Return type hint
    """
    Detailed description of what this workflow does.

    Args:
        context: Organization context with access to org data
        param1: Description of parameter 1
        param2: Description of parameter 2
        param3: Description of parameter 3

    Returns:
        dict: Description of return value

    Raises:
        WorkflowException: When something goes wrong
    """
    # 5. Implementation
    context.log("info", "Starting workflow execution")

    try:
        # Your logic here
        result = process_data(param1, param2, param3)

        context.log("info", "Workflow completed successfully")
        return {"success": True, "result": result}

    except Exception as e:
        context.log("error", f"Workflow failed: {str(e)}")
        raise WorkflowException(f"Processing failed: {str(e)}")
```

### Workflow Categories

Organize your workflows into these standard categories:

-   **user_management**: User creation, updates, deactivation
-   **automation**: Scheduled tasks and cleanup operations
-   **integration**: Data synchronization between systems
-   **reporting**: Report generation and data analysis
-   **administration**: System administration and maintenance
-   **examples**: Sample workflows and templates

### Execution Modes

#### Synchronous (sync)

-   Default mode
-   Executes immediately and returns result
-   Best for quick operations (<5 seconds)

```python
@workflow(
    name="quick_task",
    execution_mode="sync",
    timeout_seconds=30
)
async def quick_task(context):
    # Fast operation
    return {"status": "completed"}
```

#### Asynchronous (async)

-   Runs in background
-   Returns execution ID immediately
-   Best for long-running operations

```python
@workflow(
    name="bulk_operation",
    execution_mode="async",
    timeout_seconds=1800  # 30 minutes
)
async def bulk_operation(context, data):
    # Long-running operation
    for item in data:
        await process_item(item)
        context.set_variable("processed", len(processed_items))

    return {"processed": len(data)}
```

#### Scheduled (scheduled)

-   Runs automatically on schedule
-   Cannot be called manually from forms
-   Best for recurring tasks

```python
@workflow(
    name="daily_cleanup",
    execution_mode="scheduled",
    schedule="0 2 * * *",  # Daily at 2 AM UTC
    expose_in_forms=False
)
async def daily_cleanup(context):
    # Automated cleanup
    await cleanup_old_data()
    return {"cleaned_items": 42}
```

---

## Parameters and Validation

### Parameter Types

Supported parameter types:

```python
# String parameters
@param("name", "string", "Full name", required=True,
       validation={"min_length": 1, "max_length": 100})

# Integer parameters
@param("age", "int", "User age",
       validation={"min": 18, "max": 120})

# Boolean parameters
@param("is_active", "bool", "Account status", default_value=True)

# Email parameters (with validation)
@param("email", "email", "Email address", required=True)

# JSON parameters
@param("metadata", "json", "Additional metadata",
       default_value={})

# List parameters
@param("tags", "list", "List of tags",
       default_value=[])

# Float parameters
@param("price", "float", "Item price",
       validation={"min": 0.0})
```

### Validation Rules

#### String Validation

```python
@param("username", "string", "Username", required=True,
       validation={
           "min_length": 3,
           "max_length": 50,
           "pattern": r"^[a-zA-Z0-9_]+$"  # Alphanumeric and underscore
       })
```

#### Number Validation

```python
@param("quantity", "int", "Order quantity", required=True,
       validation={
           "min": 1,
           "max": 1000
       })

@param("percentage", "float", "Percentage",
       validation={
           "min": 0.0,
           "max": 100.0
       })
```

#### Enum Validation

```python
@param("status", "string", "Order status", required=True,
       validation={
           "enum": ["pending", "processing", "completed", "cancelled"]
       })
```

#### Custom Validation

For complex validation, handle it in the workflow:

```python
@workflow(name="complex_validation")
@param("email", "email", "Email address", required=True)
@param("domain", "string", "Email domain", required=True)
async def complex_validation(context, email, domain):
    # Custom validation logic
    if not email.endswith(f"@{domain}"):
        raise ValidationError(
            "Email domain does not match specified domain",
            field="email",
            details={"email": email, "expected_domain": domain}
        )

    # Continue processing
    return {"validated": True}
```

### Dynamic Parameters with Data Providers

Use data providers for dynamic dropdown options:

```python
@param("department", "string", "Department", required=True,
       data_provider="get_departments")

@param("license_type", "string", "License type",
       data_provider="get_available_licenses")

@param("manager", "string", "Manager",
       data_provider="get_managers")
```

---

## Context API

The `OrganizationContext` provides access to all platform services.

### Organization Information

```python
async def workflow_example(context: OrganizationContext):
    # Basic organization info
    org_id = context.org_id
    org_name = context.org_name
    tenant_id = context.tenant_id

    context.log("info", f"Running for org: {org_name} ({org_id})")
```

### Configuration Management

```python
async def config_example(context: OrganizationContext):
    # Get configuration values
    api_url = context.get_config("api_url", "https://default.api.com")
    timeout = context.get_config("request_timeout", 30)

    # Check if configuration exists
    if context.has_config("feature_flag"):
        # Use feature
        pass

    # Configuration with secret resolution
    api_key = context.get_config("api_key")  # Automatically fetched from Key Vault

    return {
        "api_url": api_url,
        "timeout": timeout,
        "has_feature": context.has_config("feature_flag")
    }
```

### Secret Management

```python
async def secret_example(context: OrganizationContext):
    # Get secrets directly from Key Vault
    # Secrets are org-scoped: {org_id}--{secret_name}

    api_key = await context.get_secret("my_api_key")
    db_password = await context.get_secret("database_password")
    oauth_secret = await context.get_secret("oauth_client_secret")

    # Use secrets securely
    headers = {"Authorization": f"Bearer {api_key}"}

    return {"secret_accessed": True}
```

### OAuth Connections

```python
async def oauth_example(context: OrganizationContext):
    # Get pre-authenticated OAuth credentials
    halo_creds = await context.get_oauth_connection("HaloPSA")

    # Check token status
    if halo_creds.is_expired():
        context.log("warning", "OAuth token expired, will refresh")

    # Get authorization header
    headers = {"Authorization": halo_creds.get_auth_header()}

    # Use in API calls
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.halopsa.com/tickets", headers=headers) as response:
            tickets = await response.json()

    return {"tickets_count": len(tickets)}
```

### Integration Clients

```python
async def integration_example(context: OrganizationContext):
    # Microsoft Graph integration
    graph = context.get_integration("msgraph")

    # Get users
    users = await graph.get_users()

    # Create user
    new_user = await graph.create_user(
        email="user@example.com",
        name="John Doe"
    )

    # HaloPSA integration
    halo = context.get_integration("halopsa")
    tickets = await halo.get_tickets()

    return {
        "users_count": len(users),
        "created_user": new_user["id"],
        "tickets_count": len(tickets)
    }
```

### Logging and Monitoring

```python
async def logging_example(context: OrganizationContext):
    # Structured logging with data
    context.log("info", "Starting user processing", {
        "user_count": 100,
        "processing_type": "bulk"
    })

    context.log("warning", "Rate limit approaching", {
        "remaining_requests": 10,
        "reset_time": "2024-01-01T12:00:00Z"
    })

    context.log("error", "API call failed", {
        "endpoint": "/users",
        "error_code": 500,
        "error_message": "Internal server error"
    })
```

### Checkpoints and State Management

```python
async def checkpoint_example(context: OrganizationContext):
    # Save checkpoints for debugging and recovery
    context.save_checkpoint("validation_start", {
        "step": "validation",
        "records_to_process": 1000
    })

    # Process data
    processed = 0
    for item in data:
        await process_item(item)
        processed += 1

        # Save progress every 100 items
        if processed % 100 == 0:
            context.save_checkpoint(f"batch_{processed}", {
                "processed": processed,
                "current_item": item["id"]
            })

    # Workflow variables (persisted for execution duration)
    context.set_variable("total_processed", processed)
    context.set_variable("processing_complete", True)

    # Retrieve variables
    total = context.get_variable("total_processed", 0)
    is_complete = context.get_variable("processing_complete", False)

    return {"processed": total, "complete": is_complete}
```

---

## Error Handling

### Structured Exception Types

```python
from engine.shared.error_handling import (
    ValidationError, IntegrationError, TimeoutError,
    ConfigurationError, PermissionError, WorkflowException
)

async def error_handling_example(context: OrganizationContext, email: str):
    # Input validation
    if not email or "@" not in email:
        raise ValidationError(
            "Invalid email address format",
            field="email",
            details={"provided_value": email}
        )

    # Configuration validation
    if not context.has_config("api_endpoint"):
        raise ConfigurationError(
            "API endpoint not configured",
            config_key="api_endpoint"
        )

    # Permission check
    if not context.caller.email.endswith("@admin.com"):
        raise PermissionError(
            "Administrator access required",
            required_role="admin",
            current_user=context.caller.email
        )

    # Integration error handling
    try:
        graph = context.get_integration("msgraph")
        user = await graph.get_user(email)
    except Exception as e:
        raise IntegrationError(
            integration="msgraph",
            message=f"Failed to retrieve user: {str(e)}",
            status_code=getattr(e, 'status_code', None),
            details={"email": email}
        )

    return {"user": user}
```

### Timeout Handling

```python
async def timeout_example(context: OrganizationContext):
    import asyncio

    try:
        # Operation with timeout
        result = await asyncio.wait_for(
            long_running_operation(),
            timeout=30.0
        )
        return result

    except asyncio.TimeoutError:
        raise TimeoutError(
            "Operation timed out after 30 seconds",
            timeout_seconds=30,
            operation="long_running_operation"
        )
```

### Custom Exception Types

```python
from engine.shared.error_handling import WorkflowException

class BusinessLogicError(WorkflowException):
    """Custom exception for business logic errors"""

    def __init__(self, message: str, business_rule: str, details: dict = None):
        super().__init__(
            message=message,
            error_type="BusinessLogicError",
            details=details or {}
        )
        self.business_rule = business_rule

async def custom_error_example(context: OrganizationContext, user_type: str):
    if user_type == "premium":
        # Check premium user limits
        premium_count = context.get_variable("premium_users", 0)
        if premium_count >= 100:
            raise BusinessLogicError(
                "Premium user limit exceeded",
                business_rule="MAX_PREMIUM_USERS",
                details={"current": premium_count, "limit": 100}
            )

    return {"user_type": user_type}
```

---

## Data Providers

Data providers supply dynamic options for form fields.

### Creating Data Providers

```python
# /workspace/data_providers/organization_data.py
from engine.shared.decorators import data_provider
from engine.shared.context import OrganizationContext

@data_provider(
    name="get_departments",
    description="Get list of departments for the organization",
    category="organization",
    cache_ttl_seconds=300  # Cache for 5 minutes
)
async def get_departments(context: OrganizationContext):
    """Return department options for form dropdown."""

    # Get from organization configuration
    departments_config = context.get_config("departments", "")

    if departments_config:
        departments = [dept.strip() for dept in departments_config.split(",")]
    else:
        # Default departments
        departments = ["IT", "HR", "Finance", "Sales", "Marketing"]

    return [
        {"label": dept, "value": dept.lower().replace(" ", "_")}
        for dept in departments
    ]

@data_provider(
    name="get_m365_licenses",
    description="Get available Microsoft 365 licenses",
    category="m365"
)
async def get_m365_licenses(context: OrganizationContext):
    """Return available M365 licenses from Microsoft Graph."""
    try:
        graph = context.get_integration("msgraph")
        skus = await graph.get_subscribed_skus()

        licenses = []
        for sku in skus.value:
            available = sku.prepaid_units.enabled - sku.consumed_units
            if available > 0:
                licenses.append({
                    "label": f"{sku.sku_part_number} ({available} available)",
                    "value": sku.sku_id,
                    "metadata": {
                        "available": available,
                        "price": sku.prepaid_units.enabled
                    }
                })

        return licenses

    except Exception as e:
        context.log("error", "Failed to get M365 licenses", {"error": str(e)})
        return []

@data_provider(
    name="get_users",
    description="Get list of users for selection",
    category="organization"
)
async def get_users(context: OrganizationContext):
    """Return list of active users."""
    try:
        graph = context.get_integration("msgraph")
        users = await graph.get_users(filter="accountEnabled eq true")

        return [
            {
                "label": f"{user['displayName']} ({user['userPrincipalName']})",
                "value": user["id"],
                "metadata": {
                    "email": user["userPrincipalName"],
                    "department": user.get("department", "Unknown")
                }
            }
            for user in users.value
        ]

    except Exception as e:
        context.log("error", "Failed to get users", {"error": str(e)})
        return []
```

### Using Data Providers in Workflows

```python
@workflow(name="assign_license")
@param("user", "string", "User to assign license to",
       data_provider="get_users")
@param("license", "string", "License to assign",
       data_provider="get_m365_licenses")
@param("department", "string", "Department",
       data_provider="get_departments")
async def assign_license(context, user, license, department):
    """Assign Microsoft 365 license to user."""

    graph = context.get_integration("msgraph")

    # Assign license
    result = await graph.assign_license(user, license)

    # Update user department
    await graph.update_user(user, {"department": department})

    return {
        "user": user,
        "license": license,
        "department": department,
        "assignment_id": result["id"]
    }
```

---

## Integrations

### Microsoft Graph Integration

```python
async def msgraph_example(context: OrganizationContext):
    graph = context.get_integration("msgraph")

    # User management
    users = await graph.get_users()
    user = await graph.get_user("user@example.com")
    new_user = await graph.create_user(
        email="newuser@example.com",
        name="New User",
        department="IT"
    )

    # Group management
    groups = await graph.get_groups()
    await graph.add_user_to_group(user["id"], "group-id")

    # License management
    licenses = await graph.get_subscribed_skus()
    await graph.assign_license(user["id"], "license-sku-id")

    # Security and compliance
    sign_ins = await graph.get_sign_ins()
    security_alerts = await graph.get_security_alerts()

    return {
        "users_count": len(users),
        "created_user": new_user["id"],
        "licenses_count": len(licenses)
    }
```

### HaloPSA Integration

```python
async def halopsa_example(context: OrganizationContext):
    halo = context.get_integration("halopsa")

    # Client management
    clients = await halo.get_clients()
    client = await halo.get_client("client-id")
    new_client = await halo.create_client(
        name="New Client",
        email="contact@client.com",
        phone="555-0123"
    )

    # Ticket management
    tickets = await halo.get_tickets()
    ticket = await halo.get_ticket("ticket-id")
    new_ticket = await halo.create_ticket(
        client_id="client-id",
        title="Support Request",
        description="User needs help with login",
        priority="medium"
    )

    # Time tracking
    time_entries = await halo.get_time_entries()
    await halo.create_time_entry(
        ticket_id="ticket-id",
        user_id="user-id",
        hours=2.5,
        description="Troubleshooting login issue"
    )

    return {
        "clients_count": len(clients),
        "tickets_count": len(tickets),
        "created_ticket": new_ticket["id"]
    }
```

### Custom API Integration

```python
# /workspace/integrations/custom_api.py
from engine.shared.integrations.base import BaseIntegration
from engine.shared.error_handling import IntegrationError
import aiohttp

class CustomAPIIntegration(BaseIntegration):
    integration_name = "custom_api"

    async def authenticate(self):
        """Authenticate to custom API."""
        api_key = await self.get_secret("custom_api_key")
        base_url = self.get_config("custom_api_url")

        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}

        return api_key

    async def get_data(self, endpoint: str):
        """Get data from API endpoint."""
        started_at = datetime.utcnow()
        url = f"{self.base_url}{endpoint}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    data = await response.json()

                    # Track successful call
                    duration_ms = int((datetime.utcnow() - started_at).total_seconds() * 1000)
                    self.context._track_integration_call(
                        integration="custom_api",
                        method="GET",
                        endpoint=endpoint,
                        status_code=response.status,
                        duration_ms=duration_ms
                    )

                    return data

        except Exception as e:
            # Track failed call
            duration_ms = int((datetime.utcnow() - started_at).total_seconds() * 1000)
            self.context._track_integration_call(
                integration="custom_api",
                method="GET",
                endpoint=endpoint,
                status_code=500,
                duration_ms=duration_ms,
                error=str(e)
            )

            raise IntegrationError(
                integration="custom_api",
                message=f"API call failed: {str(e)}"
            )

# Register the integration
from engine.shared.integrations.base import register_integration
register_integration("custom_api", CustomAPIIntegration)

# Use in workflow
async def custom_api_example(context: OrganizationContext):
    api = context.get_integration("custom_api")
    data = await api.get_data("/users")
    return {"users": data}
```

---

## Testing

### Unit Testing with Mock Context

```python
# /workspace/tests/test_user_workflows.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from workspace.workflows.user_management.create_user import create_user

@pytest.mark.asyncio
async def test_create_user_success():
    # Mock context
    context = MagicMock()
    context.org_id = "test-org"
    context.org_name = "Test Organization"
    context.get_config = MagicMock(return_value="test_value")
    context.log = MagicMock()
    context.save_checkpoint = MagicMock()

    # Mock integration
    mock_graph = AsyncMock()
    mock_graph.create_user = AsyncMock(return_value={
        "id": "user-123",
        "email": "test@example.com",
        "displayName": "Test User"
    })
    context.get_integration = MagicMock(return_value=mock_graph)

    # Execute workflow
    result = await create_user(
        context,
        email="test@example.com",
        name="Test User",
        department="IT"
    )

    # Assert
    assert result["success"] is True
    assert result["user_id"] == "user-123"
    mock_graph.create_user.assert_called_once_with(
        email="test@example.com",
        name="Test User",
        department="IT"
    )
    context.log.assert_called()

@pytest.mark.asyncio
async def test_create_user_validation_error():
    context = MagicMock()

    # Test invalid email
    with pytest.raises(ValidationError):
        await create_user(
            context,
            email="invalid-email",
            name="Test User",
            department="IT"
        )
```

### Integration Testing

```python
# /workspace/tests/test_integrations.py
import pytest
import aiohttp
from workspace.integrations.custom_api import CustomAPIIntegration

@pytest.mark.asyncio
async def test_custom_api_integration():
    # Mock context
    context = MagicMock()
    context.get_secret = AsyncMock(return_value="test-api-key")
    context.get_config = MagicMock(return_value="https://api.example.com")
    context._track_integration_call = MagicMock()

    # Create integration
    integration = CustomAPIIntegration(context)

    # Mock HTTP response
    with aioresponses() as m:
        m.get(
            "https://api.example.com/users",
            payload={"users": [{"id": 1, "name": "Test User"}]}
        )

        # Test API call
        result = await integration.get_data("/users")

        assert result["users"][0]["name"] == "Test User"
        context._track_integration_call.assert_called_once()
```

### Local Development Testing

```bash
#!/bin/bash
# /workspace/scripts/test_workflows.sh

echo "Starting workflow tests..."

# Start services
azurite --silent --location /tmp/azurite &
AZURITE_PID=$!
sleep 2

python scripts/seed_azurite.py
func start &
FUNCTIONS_PID=$!
sleep 5

# Test workflows
workflows=(
    "create_user"
    "assign_license"
    "generate_report"
)

for workflow in "${workflows[@]}"; do
    echo "Testing $workflow..."

    response=$(curl -s -w "%{http_code}" -X POST \
      -H "Content-Type: application/json" \
      -H "X-Organization-Id: test-org-active" \
      -H "x-functions-key: test" \
      -d '{"email": "test@example.com"}' \
      http://localhost:7071/api/workflows/$workflow)

    http_code="${response: -3}"
    if [ "$http_code" != "200" ]; then
        echo "❌ $workflow failed with HTTP $http_code"
        exit 1
    else
        echo "✅ $workflow passed"
    fi
done

# Cleanup
kill $AZURITE_PID $FUNCTIONS_PID
echo "All tests passed!"
```

---

## Best Practices

### 1. Workflow Design

**Single Responsibility**

```python
# ✅ Good - Focused on one task
@workflow(name="create_user")
async def create_user(context, email, name):
    # Only creates user
    pass

# ✅ Good - Separate workflow for additional tasks
@workflow(name="assign_license")
async def assign_license(context, user_id, license_sku):
    # Only assigns license
    pass

# ❌ Bad - Doing too much
@workflow(name="onboard_user")
async def onboard_user(context, email, name, department, license, groups):
    # Creates user, assigns license, adds to groups, sends email...
    pass
```

**Descriptive Names and Categories**

```python
# ✅ Good
@workflow(
    name="create_m365_user",
    description="Create new user in Microsoft 365",
    category="user_management"
)

# ❌ Bad
@workflow(
    name="proc1",
    description="Does stuff",
    category="misc"
)
```

### 2. Error Handling

**Specific Exception Types**

```python
# ✅ Good
if not email.endswith("@company.com"):
    raise ValidationError(
        "Email must use company domain",
        field="email",
        details={"required_domain": "@company.com"}
    )

# ❌ Bad
if not email.endswith("@company.com"):
    raise Exception("Wrong email")
```

**Log Before Raising**

```python
# ✅ Good
try:
    result = await api_call()
except Exception as e:
    context.log("error", "API call failed", {
        "endpoint": "/users",
        "error": str(e)
    })
    raise IntegrationError("API call failed", details={"error": str(e)})

# ❌ Bad
try:
    result = await api_call()
except Exception as e:
    raise IntegrationError("API call failed")
```

### 3. Performance

**Use Async for I/O**

```python
# ✅ Good - Parallel API calls
import asyncio
users, groups = await asyncio.gather(
    graph.get_users(),
    graph.get_groups()
)

# ❌ Bad - Sequential API calls
users = await graph.get_users()
groups = await graph.get_groups()
```

**Process Large Datasets Efficiently**

```python
# ✅ Good - Stream processing
async def process_users(context):
    async for user in graph.get_users_stream():
        await process_user(user)

# ❌ Bad - Load everything into memory
async def process_users(context):
    users = await graph.get_users()  # Could be thousands
    for user in users:
        await process_user(user)
```

### 4. Security

**Never Log Sensitive Data**

```python
# ✅ Good
context.log("info", "API call successful", {
    "endpoint": "/users",
    "user_count": len(users)
})

# ❌ Bad - Logging sensitive data
context.log("info", "API call successful", {
    "endpoint": "/users",
    "api_key": api_key,  # Don't log this!
    "users": users  # Don't log PII!
})
```

**Use Context for Secrets**

```python
# ✅ Good
api_key = await context.get_secret("api_key")

# ❌ Bad - Hardcoded secrets
api_key = "sk-1234567890abcdef"
```

### 5. Maintainability

**Add Clear Docstrings**

```python
@workflow(name="complex_workflow")
async def complex_workflow(context, data):
    """
    Process complex data with multiple validation steps.

    This workflow validates input data, transforms it according to business rules,
    and stores the results in the database. It includes comprehensive error
    handling and progress tracking.

    Args:
        context: Organization context
        data: Dictionary containing user data with keys:
            - email (str): User email address
            - name (str): Full name
            - department (str): Department code

    Returns:
        dict: Processing results with keys:
            - success (bool): Whether processing succeeded
            - user_id (str): Created user ID (if successful)
            - errors (list): List of validation errors (if any)

    Raises:
        ValidationError: If input data is invalid
        IntegrationError: If external API calls fail
    """
```

**Use Type Hints**

```python
# ✅ Good
async def process_user(
    context: OrganizationContext,
    user_data: dict[str, Any]
) -> dict[str, Any]:
    return {"processed": True}

# ❌ Bad
async def process_user(context, user_data):
    return {"processed": True}
```

---

## Advanced Patterns

### 1. Workflow Composition

```python
# Base workflow for common functionality
@workflow(name="base_user_operation")
async def base_user_operation(context, user_email):
    """Common user validation and setup."""

    # Validate email format
    if not user_email or "@" not in user_email:
        raise ValidationError("Invalid email format", field="user_email")

    # Check if user exists
    graph = context.get_integration("msgraph")
    existing_user = await graph.get_user(user_email)

    if existing_user:
        raise ValidationError("User already exists", field="user_email")

    return {"validated_email": user_email}

# Compose with base workflow
@workflow(name="create_and_setup_user")
async def create_and_setup_user(context, user_email, name, department):
    """Create user and perform initial setup."""

    # Use base workflow for validation
    validation_result = await context.execute_workflow(
        "base_user_operation",
        {"user_email": user_email}
    )

    # Create user
    graph = context.get_integration("msgraph")
    user = await graph.create_user(user_email, name, department)

    # Additional setup
    await context.execute_workflow("assign_default_groups", {
        "user_id": user["id"],
        "department": department
    })

    return {"user_id": user["id"], "setup_complete": True}
```

### 2. Conditional Execution

```python
@workflow(name="conditional_processing")
async def conditional_processing(context, data, processing_type):
    """Process data differently based on type."""

    if processing_type == "bulk":
        # Bulk processing logic
        results = []
        for item in data:
            result = await process_single_item(item)
            results.append(result)

        return {"processed": len(results), "results": results}

    elif processing_type == "stream":
        # Stream processing logic
        processed_count = 0
        async for item in stream_data(data):
            await process_single_item(item)
            processed_count += 1

            # Save progress
            if processed_count % 100 == 0:
                context.save_checkpoint("stream_progress", {
                    "processed": processed_count
                })

        return {"processed": processed_count}

    else:
        raise ValidationError(
            "Invalid processing type",
            field="processing_type",
            details={"valid_types": ["bulk", "stream"]}
        )
```

### 3. Retry and Resilience

```python
import asyncio
from engine.shared.error_handling import IntegrationError

async def resilient_api_call(context, api_func, max_retries=3, backoff_factor=2):
    """Execute API call with retry logic."""

    for attempt in range(max_retries + 1):
        try:
            return await api_func()

        except IntegrationError as e:
            if attempt == max_retries:
                # Final attempt failed
                context.log("error", f"API call failed after {max_retries + 1} attempts", {
                    "error": str(e),
                    "attempts": attempt + 1
                })
                raise

            # Calculate backoff delay
            delay = backoff_factor ** attempt
            context.log("warning", f"API call failed, retrying in {delay}s", {
                "attempt": attempt + 1,
                "error": str(e)
            })

            await asyncio.sleep(delay)

@workflow(name="resilient_user_creation")
async def resilient_user_creation(context, email, name):
    """Create user with retry logic."""

    graph = context.get_integration("msgraph")

    async def create_user():
        return await graph.create_user(email, name)

    user = await resilient_api_call(context, create_user)
    return {"user_id": user["id"]}
```

### 4. Batch Processing

```python
@workflow(
    name="bulk_user_import",
    execution_mode="async",
    timeout_seconds=1800  # 30 minutes
)
async def bulk_user_import(context, users_data):
    """Import multiple users with progress tracking."""

    total_users = len(users_data)
    context.set_variable("total_users", total_users)
    context.set_variable("processed_users", 0)
    context.set_variable("failed_users", [])

    results = {
        "successful": [],
        "failed": [],
        "summary": {}
    }

    # Process in batches to avoid overwhelming APIs
    batch_size = 10
    for i in range(0, total_users, batch_size):
        batch = users_data[i:i + batch_size]

        context.log("info", f"Processing batch {i//batch_size + 1}", {
            "batch_size": len(batch),
            "batch_start": i,
            "total_users": total_users
        })

        # Process batch in parallel
        batch_tasks = [
            process_single_user(context, user_data)
            for user_data in batch
        ]

        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

        # Process results
        for j, result in enumerate(batch_results):
            user_index = i + j

            if isinstance(result, Exception):
                # Handle failure
                failed_list = context.get_variable("failed_users", [])
                failed_list.append({
                    "index": user_index,
                    "data": batch[j],
                    "error": str(result)
                })
                context.set_variable("failed_users", failed_list)

                results["failed"].append({
                    "index": user_index,
                    "error": str(result)
                })
            else:
                # Handle success
                processed_count = context.get_variable("processed_users", 0)
                context.set_variable("processed_users", processed_count + 1)

                results["successful"].append(result)

        # Save checkpoint after each batch
        context.save_checkpoint(f"batch_{i//batch_size + 1}_complete", {
            "processed": context.get_variable("processed_users"),
            "failed": len(context.get_variable("failed_users", [])),
            "progress": (i + len(batch)) / total_users * 100
        })

    # Generate summary
    results["summary"] = {
        "total": total_users,
        "successful": len(results["successful"]),
        "failed": len(results["failed"]),
        "success_rate": len(results["successful"]) / total_users * 100
    }

    context.log("info", "Bulk import completed", results["summary"])
    return results
```

---

## HTTP Endpoints

Workflows can be exposed as HTTP endpoints for webhook integration, external automation, and third-party tool integration. This feature transforms workflows into REST API endpoints with full HTTP method support, API key authentication, and automatic OpenAPI documentation.

### Exposing Workflows as Endpoints

Enable HTTP endpoint access using the `endpoint_enabled` parameter in the `@workflow` decorator:

```python
@workflow(
    name="process_webhook",
    description="Process incoming webhook data",
    category="integration",
    endpoint_enabled=True,                    # Enable HTTP endpoint
    allowed_methods=["GET", "POST"],          # Allowed HTTP methods
    disable_global_key=False                  # Use global API key (default)
)
@param("event_type", "string", "Event type", required=True)
@param("payload", "json", "Event payload", required=False)
async def process_webhook(context, event_type, payload=None):
    """
    Process webhook events from external systems.

    This workflow is exposed as an HTTP endpoint at:
    POST /api/endpoints/process_webhook
    """
    context.log("info", f"Processing {event_type} event")

    # Process the webhook payload
    result = await process_event(event_type, payload)

    return {"success": True, "result": result}
```

### Endpoint Configuration

#### `endpoint_enabled` (bool)
When `True`, exposes the workflow at `/api/endpoints/{workflow_name}`. When `False` (default), the workflow can only be executed through the UI or the `/api/workflows/{workflow_name}/execute` endpoint.

#### `allowed_methods` (list[str])
Specifies which HTTP methods are permitted. Supported methods:
- `GET` - Retrieve or query data
- `POST` - Create or process data (default)
- `PUT` - Update or replace data
- `DELETE` - Remove or deactivate data

```python
# Example: Read-only endpoint
@workflow(
    name="get_status",
    endpoint_enabled=True,
    allowed_methods=["GET"]  # Only allow GET requests
)
async def get_status(context):
    return {"status": "operational", "version": "1.0.0"}

# Example: Full CRUD endpoint
@workflow(
    name="manage_resource",
    endpoint_enabled=True,
    allowed_methods=["GET", "POST", "PUT", "DELETE"]
)
async def manage_resource(context, resource_id, action, data=None):
    # Handle different methods in workflow logic
    return {"action": action, "resource_id": resource_id}
```

#### `disable_global_key` (bool)
Controls API key authentication behavior:
- `False` (default) - Both global API keys and workflow-specific keys work
- `True` - Only workflow-specific API keys are accepted (global keys rejected)

```python
# Example: Require dedicated API key
@workflow(
    name="sensitive_operation",
    endpoint_enabled=True,
    allowed_methods=["POST"],
    disable_global_key=True  # Require workflow-specific key
)
async def sensitive_operation(context, data):
    """
    This workflow requires a dedicated API key.
    Global platform API keys will be rejected.
    """
    return {"processed": True}
```

### Calling HTTP Endpoints

#### Endpoint URL Pattern
Enabled workflows are accessible at:
```
{method} https://your-app.azurestaticapps.net/api/endpoints/{workflow_name}
```

#### Authentication
All endpoint calls require API key authentication via:
1. **Header** (recommended): `x-functions-key: your-api-key`
2. **Query parameter**: `?code=your-api-key`

Create API keys in the platform UI under Workflows → API Keys.

#### Input Parameters

**Query Parameters** and **JSON Body** are both supported. If both are provided, **JSON body takes precedence**.

**Example with Query Parameters (GET):**
```bash
curl -X GET \
  -H "x-functions-key: your-api-key" \
  "https://your-app.azurestaticapps.net/api/endpoints/get_user?email=user@example.com"
```

**Example with JSON Body (POST):**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "x-functions-key: your-api-key" \
  -d '{
    "email": "user@example.com",
    "name": "John Doe",
    "department": "IT"
  }' \
  https://your-app.azurestaticapps.net/api/endpoints/create_user
```

**Example with Both (Body takes precedence):**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "x-functions-key: your-api-key" \
  -d '{"email": "override@example.com"}' \
  "https://your-app.azurestaticapps.net/api/endpoints/process?email=fallback@example.com"

# Result: email="override@example.com" (from body, not query string)
```

#### HTTP Status Codes

Endpoints return standard HTTP status codes:
- `200 OK` - Workflow executed successfully (even if workflow returned `success: false`)
- `400 Bad Request` - Invalid input or missing required parameters
- `404 Not Found` - Endpoint not enabled or workflow doesn't exist
- `405 Method Not Allowed` - HTTP method not in `allowed_methods`
- `401 Unauthorized` - Invalid or missing API key
- `500 Internal Server Error` - Pre-execution infrastructure error

**Important**: Workflow execution errors return `200` with `status: "Failed"` in the response body. This distinguishes workflow-level failures from infrastructure errors.

#### Response Format

All endpoint responses follow the standard workflow execution response format:

```json
{
  "executionId": "uuid",
  "status": "Success" | "Failed" | "CompletedWithErrors",
  "result": { ... },              // Present on success
  "error": "error message",        // Present on failure
  "errorType": "ErrorType",        // Present on failure
  "details": { ... },              // Present on failure with details
  "durationMs": 1234,
  "startedAt": "2024-01-15T10:30:00Z",
  "completedAt": "2024-01-15T10:30:01Z"
}
```

### API Key Management

#### Global API Keys
Platform-wide keys that work for all workflows (unless `disable_global_key=True`). Created in the UI under Platform Settings → API Keys.

#### Workflow-Specific API Keys
Scoped to a single workflow. Created in the UI under Workflows → {workflow_name} → API Keys.

**Key Priority**:
1. If workflow has `disable_global_key=True`, **only** workflow-specific keys work
2. Otherwise, workflow-specific keys are tried first, then global keys

```python
# Example: Opt out of global keys for sensitive workflow
@workflow(
    name="financial_report",
    endpoint_enabled=True,
    allowed_methods=["POST"],
    disable_global_key=True  # Only dedicated keys work
)
async def financial_report(context, month, year):
    """
    Generate financial reports.
    Requires dedicated API key for auditing purposes.
    """
    return {"report": generate_report(month, year)}
```

### OpenAPI Documentation

Enabled endpoints automatically appear in the OpenAPI specification at:
```
GET /api/openapi.json
```

The OpenAPI spec includes:
- Endpoint paths and methods
- Required and optional parameters
- Parameter types and validation rules
- Request/response schemas
- Authentication requirements

Access the Swagger UI documentation at:
```
https://your-app.azurestaticapps.net/api/swagger
```

### Webhook Integration Examples

#### GitHub Webhook
```python
@workflow(
    name="github_webhook",
    description="Process GitHub webhook events",
    endpoint_enabled=True,
    allowed_methods=["POST"],
    requires_org=False  # Public webhook, no org context
)
@param("action", "string", "Webhook action", required=True)
@param("repository", "json", "Repository data", required=True)
@param("sender", "json", "Sender data", required=True)
async def github_webhook(context, action, repository, sender):
    """
    Handle GitHub webhook events.

    Endpoint: POST /api/endpoints/github_webhook
    Configure in GitHub: Repo Settings → Webhooks → Add webhook
    Payload URL: https://your-app.azurestaticapps.net/api/endpoints/github_webhook?code=YOUR_API_KEY
    """
    context.log("info", f"GitHub {action} event", {
        "repo": repository.get("name"),
        "sender": sender.get("login")
    })

    if action == "opened":
        # Handle PR opened
        await notify_team(repository, sender)
    elif action == "closed":
        # Handle PR closed
        await update_tracking(repository)

    return {"processed": True, "action": action}
```

#### Stripe Webhook
```python
@workflow(
    name="stripe_webhook",
    description="Process Stripe payment events",
    endpoint_enabled=True,
    allowed_methods=["POST"],
    disable_global_key=True  # Require dedicated key for security
)
@param("type", "string", "Event type", required=True)
@param("data", "json", "Event data", required=True)
async def stripe_webhook(context, type, data):
    """
    Handle Stripe webhook events.

    Endpoint: POST /api/endpoints/stripe_webhook
    Configure in Stripe Dashboard → Webhooks → Add endpoint
    """
    context.log("info", f"Stripe event: {type}")

    if type == "payment_intent.succeeded":
        await process_successful_payment(data)
    elif type == "payment_intent.failed":
        await handle_failed_payment(data)

    return {"received": True}
```

#### Zapier Integration
```python
@workflow(
    name="zapier_trigger",
    description="Trigger for Zapier integration",
    endpoint_enabled=True,
    allowed_methods=["GET", "POST"]
)
@param("trigger_type", "string", "Trigger type", required=True)
@param("data", "json", "Trigger data", required=False)
async def zapier_trigger(context, trigger_type, data=None):
    """
    Zapier trigger endpoint.

    GET: Verify connection
    POST: Process trigger
    """
    if context.request.method == "GET":
        # Zapier connection test
        return {"status": "connected"}

    # Process Zapier trigger
    result = await process_trigger(trigger_type, data)
    return {"result": result}
```

### REST API Patterns

#### Resource Management
```python
@workflow(
    name="manage_tickets",
    endpoint_enabled=True,
    allowed_methods=["GET", "POST", "PUT", "DELETE"]
)
@param("ticket_id", "string", "Ticket ID", required=False)
@param("action", "string", "Action", required=False)
@param("data", "json", "Ticket data", required=False)
async def manage_tickets(context, ticket_id=None, action=None, data=None):
    """
    RESTful ticket management endpoint.

    GET /api/endpoints/manage_tickets?ticket_id=123 - Get ticket
    POST /api/endpoints/manage_tickets - Create ticket
    PUT /api/endpoints/manage_tickets?ticket_id=123 - Update ticket
    DELETE /api/endpoints/manage_tickets?ticket_id=123 - Delete ticket
    """
    method = context.request.method

    if method == "GET":
        return await get_ticket(ticket_id)
    elif method == "POST":
        return await create_ticket(data)
    elif method == "PUT":
        return await update_ticket(ticket_id, data)
    elif method == "DELETE":
        return await delete_ticket(ticket_id)
```

### Public Endpoints (Webhooks)

For workflows that need to accept unauthenticated requests from external systems (like webhooks from third-party services), you can use the `public_endpoint` parameter.

#### Enabling Public Endpoints

```python
@workflow(
    name="webhook_example",
    description="Public webhook endpoint for external integrations",
    category="webhooks",
    tags=["webhook", "public", "example"],
    requires_org=False,          # No organization context required
    endpoint_enabled=True,        # Enable HTTP endpoint
    allowed_methods=["POST"],     # Accept POST requests
    public_endpoint=True          # No authentication required
)
@param("event_type", type="string", label="Event Type", required=True)
@param("payload", type="json", label="Payload", required=False)
async def webhook_example(context, event_type: str, payload: dict = None):
    """
    Public webhook endpoint that accepts events from external systems.

    This workflow is exposed as a PUBLIC HTTP endpoint at:
    - POST /api/endpoints/webhook_example

    No authentication is required. External systems can POST directly.
    """
    context.info(f"Received webhook event: {event_type}")

    # Process the payload
    result = {
        "status": "received",
        "event_type": event_type,
        "received_at": datetime.utcnow().isoformat(),
        "caller": context.caller.name,  # Will be "Public Access (Webhook)"
        "has_payload": payload is not None
    }

    if payload:
        context.info(f"Payload keys: {list(payload.keys())}")
        result["payload_keys"] = list(payload.keys())

    # Save checkpoint for audit trail
    context.save_checkpoint("webhook_received", {
        "event_type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "payload_size": len(str(payload)) if payload else 0
    })

    return result
```

#### Public Endpoint Configuration

When `public_endpoint=True` is set:

- **No Authentication Required**: The endpoint can be called without any API key
- **Anonymous Caller**: `context.caller.name` will be "Public Access (Webhook)"
- **UI Indicators**: The workflow shows an orange warning badge in the UI
- **No API Key Management**: Public endpoints are excluded from API key creation dialogs
- **Security Implications**: The endpoint is completely open to the internet

#### Calling Public Endpoints

**No authentication headers needed:**

```bash
curl -X POST "https://your-app.azurestaticapps.net/api/endpoints/webhook_example" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "order.created",
    "payload": {
      "order_id": "12345",
      "total": 99.99
    }
  }'
```

Compare this to authenticated endpoints which require:

```bash
curl -X POST "https://your-app.azurestaticapps.net/api/endpoints/authenticated_workflow" \
  -H "Content-Type: application/json" \
  -H "x-functions-key: YOUR_API_KEY" \
  -d '{"data": "value"}'
```

#### Security Considerations for Public Endpoints

Since public endpoints accept unauthenticated requests, you should implement additional security measures in your workflow code:

```python
@workflow(
    name="secure_webhook",
    public_endpoint=True,
    endpoint_enabled=True,
    allowed_methods=["POST"]
)
@param("signature", "string", "Webhook signature", required=True)
@param("payload", "json", "Event data", required=True)
async def secure_webhook(context, signature: str, payload: dict):
    """
    Public webhook with signature validation.
    """
    # 1. Verify webhook signature
    secret = await context.get_secret("webhook_secret")
    expected_signature = hmac.new(
        secret.encode(),
        json.dumps(payload).encode(),
        hashlib.sha256
    ).hexdigest()

    if signature != expected_signature:
        context.log("error", "Invalid webhook signature", {
            "received": signature[:8] + "...",
            "expected": expected_signature[:8] + "..."
        })
        raise PermissionError("Invalid webhook signature")

    # 2. Validate payload structure
    required_fields = ["event_type", "timestamp", "data"]
    missing = [f for f in required_fields if f not in payload]
    if missing:
        raise ValidationError(f"Missing required fields: {missing}")

    # 3. Check timestamp to prevent replay attacks
    event_time = datetime.fromisoformat(payload["timestamp"])
    age_seconds = (datetime.utcnow() - event_time).total_seconds()
    if age_seconds > 300:  # 5 minutes
        raise ValidationError("Webhook event too old (replay attack?)")

    # 4. Rate limiting (implement in your infrastructure)
    # Consider using Azure API Management or similar

    # 5. Log all access for security auditing
    context.log("info", "Valid webhook received", {
        "event_type": payload.get("event_type"),
        "timestamp": payload.get("timestamp"),
        "source_ip": context.request.headers.get("X-Forwarded-For")
    })

    # Process the validated webhook
    return await process_webhook_event(payload)
```

#### Best Practices for Public Webhooks

```python
# ✅ Good - Validate webhook signatures
@workflow(public_endpoint=True)
async def validated_webhook(context, signature, payload):
    verify_signature(signature, payload)
    return process_payload(payload)

# ✅ Good - Log all webhook activity
@workflow(public_endpoint=True)
async def logged_webhook(context, data):
    context.log("info", "Webhook received", {
        "source_ip": context.request.headers.get("X-Forwarded-For"),
        "user_agent": context.request.headers.get("User-Agent")
    })
    return process_data(data)

# ✅ Good - Validate payload structure
@workflow(public_endpoint=True)
@param("event_type", "string", required=True)
@param("data", "json", required=True)
async def validated_structure(context, event_type, data):
    if event_type not in ["created", "updated", "deleted"]:
        raise ValidationError("Invalid event_type")
    return process_event(event_type, data)

# ❌ Bad - No validation, no logging
@workflow(public_endpoint=True)
async def unsafe_webhook(context, data):
    # Blindly process any data without validation
    return process_data(data)

# ❌ Bad - Using public_endpoint for internal workflows
@workflow(public_endpoint=True)
async def internal_workflow(context, sensitive_data):
    # This should require authentication!
    return process_sensitive_data(sensitive_data)
```

#### When to Use Public Endpoints

**✅ Good Use Cases:**
- External webhook integrations (GitHub, Stripe, etc.)
- Public API endpoints for mobile apps
- Third-party system notifications
- IoT device data collection
- Public form submissions

**❌ Bad Use Cases:**
- Internal business workflows
- Workflows handling sensitive data without validation
- Administrative operations
- User account management
- Financial transactions without verification

#### Monitoring and Security

```python
@workflow(
    name="monitored_webhook",
    public_endpoint=True,
    endpoint_enabled=True,
    allowed_methods=["POST"]
)
@param("event", "json", required=True)
async def monitored_webhook(context, event):
    """
    Public webhook with comprehensive monitoring.
    """
    start_time = datetime.utcnow()

    try:
        # Track request metadata
        metadata = {
            "source_ip": context.request.headers.get("X-Forwarded-For"),
            "user_agent": context.request.headers.get("User-Agent"),
            "content_length": len(json.dumps(event)),
            "timestamp": start_time.isoformat()
        }

        context.log("info", "Webhook request received", metadata)

        # Validate and process
        result = await process_webhook(event)

        # Track success metrics
        duration = (datetime.utcnow() - start_time).total_seconds()
        context.log("info", "Webhook processed successfully", {
            "duration_seconds": duration,
            **metadata
        })

        return result

    except Exception as e:
        # Track failure metrics
        context.log("error", "Webhook processing failed", {
            "error": str(e),
            "error_type": type(e).__name__,
            **metadata
        })
        raise
```

### Best Practices for HTTP Endpoints

#### 1. **Security**
```python
# ✅ Good - Dedicated key for sensitive operations
@workflow(
    name="delete_data",
    endpoint_enabled=True,
    allowed_methods=["DELETE"],
    disable_global_key=True  # Require dedicated key
)

# ✅ Good - Validate input thoroughly
async def process_webhook(context, data):
    if not data or "required_field" not in data:
        raise ValidationError("Missing required field")

    # Additional validation
    if not is_valid_signature(context.request.headers):
        raise PermissionError("Invalid signature")
```

#### 2. **Method Selection**
```python
# ✅ Good - Use appropriate HTTP methods
@workflow(endpoint_enabled=True, allowed_methods=["GET"])
async def get_status():  # Read-only operation
    pass

@workflow(endpoint_enabled=True, allowed_methods=["POST"])
async def create_resource():  # Create operation
    pass

# ❌ Bad - Allowing all methods for simple operation
@workflow(endpoint_enabled=True, allowed_methods=["GET", "POST", "PUT", "DELETE"])
async def get_status():  # Only needs GET
    pass
```

#### 3. **Parameter Handling**
```python
# ✅ Good - Support both query params and body
@workflow(endpoint_enabled=True, allowed_methods=["GET", "POST"])
@param("email", "email", "User email", required=True)
async def lookup_user(context, email):
    # Works with both:
    # GET /api/endpoints/lookup_user?email=user@example.com
    # POST /api/endpoints/lookup_user {"email": "user@example.com"}
    pass
```

#### 4. **Error Handling**
```python
# ✅ Good - Return structured errors
async def process_data(context, data):
    try:
        result = await process(data)
        return {"success": True, "result": result}
    except Exception as e:
        # Workflow error (returns 200 with status: "Failed")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
```

#### 5. **Documentation**
```python
# ✅ Good - Clear docstring with endpoint details
@workflow(
    name="process_order",
    description="Process customer orders from e-commerce platform",
    endpoint_enabled=True,
    allowed_methods=["POST"]
)
async def process_order(context, order_id, items, customer):
    """
    Process e-commerce orders.

    Endpoint: POST /api/endpoints/process_order
    Authentication: API key required (x-functions-key header)

    Example:
        curl -X POST \\
          -H "x-functions-key: YOUR_KEY" \\
          -H "Content-Type: application/json" \\
          -d '{"order_id": "123", "items": [...], "customer": {...}}' \\
          https://app.azurestaticapps.net/api/endpoints/process_order

    Returns:
        {
            "success": true,
            "order_id": "123",
            "status": "processed",
            "tracking_number": "TRACK123"
        }
    """
    # Implementation
    pass
```

---

This comprehensive guide provides everything you need to develop robust, secure, and maintainable workflows in the Bifrost Integrations platform.
