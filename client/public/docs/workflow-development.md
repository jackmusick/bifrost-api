# Workflow Development Guide

This comprehensive guide covers everything you need to know about developing workflows in the Bifrost Integrations platform.

## Table of Contents

- [Getting Started](#getting-started)
- [Workflow Structure](#workflow-structure)
- [Parameters and Validation](#parameters-and-validation)
- [Context API](#context-api)
- [Error Handling](#error-handling)
- [Data Providers](#data-providers)
- [Integrations](#integrations)
- [Testing](#testing)
- [Best Practices](#best-practices)
- [Advanced Patterns](#advanced-patterns)

---

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Understanding of async/await patterns
- Basic knowledge of REST APIs
- Familiarity with JSON data structures

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
   curl http://localhost:7072/api/health
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
  http://localhost:7072/api/workflows/my_first_workflow
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

- **user_management**: User creation, updates, deactivation
- **automation**: Scheduled tasks and cleanup operations
- **integration**: Data synchronization between systems
- **reporting**: Report generation and data analysis
- **administration**: System administration and maintenance
- **examples**: Sample workflows and templates

### Execution Modes

#### Synchronous (sync)
- Default mode
- Executes immediately and returns result
- Best for quick operations (<5 seconds)

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
- Runs in background
- Returns execution ID immediately
- Best for long-running operations

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
- Runs automatically on schedule
- Cannot be called manually from forms
- Best for recurring tasks

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
      http://localhost:7072/api/workflows/$workflow)
    
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

This comprehensive guide provides everything you need to develop robust, secure, and maintainable workflows in the Bifrost Integrations platform.