# AI Agent Usage Guide

This guide helps AI agents assist developers in creating custom workflows, integrations, and automation within the Bifrost Integrations platform.

## Table of Contents

- [AI Agent Capabilities](#ai-agent-capabilities)
- [Getting Started](#getting-started)
- [Workflow Development Patterns](#workflow-development-patterns)
- [Common Tasks](#common-tasks)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## AI Agent Capabilities

### What AI Agents Can Do

✅ **Create Workflows**: Generate complete workflow implementations  
✅ **Write Data Providers**: Create dynamic form option providers  
✅ **Develop Integrations**: Build custom API integration clients  
✅ **Generate Tests**: Create unit and integration tests  
✅ **Optimize Performance**: Suggest performance improvements  
✅ **Debug Issues**: Help troubleshoot workflow problems  
✅ **Document Code**: Generate comprehensive documentation

### What AI Agents Cannot Do

❌ **Modify Engine Code**: Cannot access `/engine` directory (security restriction)  
❌ **Access Production Data**: Cannot access real organization data  
❌ **Execute Workflows**: Cannot directly run workflows (can provide test commands)  
❌ **Manage Secrets**: Cannot access real Key Vault secrets

---

## Getting Started

### Essential Rules for AI Agents

#### 1. Code Location Rule

**⚠️ CRITICAL**: ALL workflow and user code MUST be written **ONLY** in the `/workspace/` directory.

```
✅ ALLOWED: /workspace/workflows/user_management/create_user.py
✅ ALLOWED: /workspace/data_providers/get_departments.py
✅ ALLOWED: /workspace/integrations/custom_api.py

❌ FORBIDDEN: /engine/shared/storage.py
❌ FORBIDDEN: /engine/functions/execute.py
❌ FORBIDDEN: /engine/admin/metadata.py
```

#### 2. Import Restrictions

Workspace code can ONLY import from these modules:

```python
# ✅ ALLOWED - Public API
from engine.shared.decorators import workflow, param, data_provider
from engine.shared.context import OrganizationContext
from engine.shared.error_handling import (
    WorkflowException, ValidationError, IntegrationError
)
from engine.shared.models import (
    WorkflowMetadata, DataProviderMetadata, OAuthCredentials
)

# ❌ FORBIDDEN - Internal engine modules
from engine.shared.storage import TableStorageService
from engine.shared.auth import AuthService
from engine.functions.execute import execute_workflow_internal
```

#### 3. File Structure Requirements

Always follow the recommended folder structure:

```
/workspace/
├── workflows/
│   └── category/
│       └── workflow_name/
│           ├── workflow.py
│           ├── diagram.mmd
│           ├── lib/
│           │   └── __init__.py
│           └── tests/
│               └── __init__.py
├── data_providers/
├── integrations/
└── utils/
```

---

## Workflow Development Patterns

### Pattern 1: Basic User Management Workflow

```python
# Request: "Create a workflow to add a new user to Microsoft 365"

# AI Agent Response:
from engine.shared.decorators import workflow, param
from engine.shared.context import OrganizationContext
from engine.shared.error_handling import ValidationError, IntegrationError

@workflow(
    name="create_m365_user",
    description="Create a new user in Microsoft 365",
    category="user_management",
    tags=["m365", "user-management"]
)
@param("email", "email", "User email address", required=True)
@param("name", "string", "User full name", required=True,
       validation={"min_length": 1, "max_length": 100})
@param("department", "string", "Department",
       data_provider="get_departments")
@param("license_sku", "string", "License SKU",
       data_provider="get_available_licenses")
async def create_m365_user(
    context: OrganizationContext,
    email: str,
    name: str,
    department: str,
    license_sku: str
):
    """
    Create a new user in Microsoft 365 with license assignment.

    Args:
        context: Organization context
        email: User email address
        name: User full name
        department: Department name
        license_sku: Microsoft 365 license SKU

    Returns:
        dict: Created user information
    """
    context.log("info", f"Creating M365 user: {email}", {
        "name": name,
        "department": department,
        "license_sku": license_sku
    })

    # Validate email domain
    if not email.endswith(f"@{context.org.tenant_id}.mail.onmicrosoft.com"):
        raise ValidationError(
            "Email must use organization domain",
            field="email",
            details={"expected_domain": context.org.tenant_id}
        )

    try:
        # Get Microsoft Graph integration
        graph = context.get_integration("msgraph")

        # Create user
        context.save_checkpoint("creating_user", {"email": email})
        user = await graph.create_user(
            email=email,
            display_name=name,
            department=department
        )

        # Assign license
        context.save_checkpoint("assigning_license", {
            "user_id": user["id"],
            "license_sku": license_sku
        })
        await graph.assign_license(user["id"], license_sku)

        # Add to department group
        department_group = await get_department_group(graph, department)
        if department_group:
            await graph.add_user_to_group(user["id"], department_group["id"])

        context.log("info", "User created successfully", {
            "user_id": user["id"],
            "email": email
        })

        return {
            "success": True,
            "user_id": user["id"],
            "email": email,
            "name": name,
            "department": department,
            "license_sku": license_sku
        }

    except Exception as e:
        context.log("error", "Failed to create user", {"error": str(e)})
        raise IntegrationError(
            integration="msgraph",
            message=f"Failed to create user: {str(e)}",
            details={"email": email}
        )

async def get_department_group(graph, department):
    """Get Microsoft 365 group for department."""
    groups = await graph.get_groups(f"displayName eq '{department}'")
    return groups.value[0] if groups.value else None
```

### Pattern 2: Data Provider for Dynamic Options

```python
# Request: "Create a data provider for available Microsoft 365 licenses"

# AI Agent Response:
from engine.shared.decorators import data_provider
from engine.shared.context import OrganizationContext

@data_provider(
    name="get_available_licenses",
    description="Get available Microsoft 365 licenses for assignment",
    category="m365",
    cache_ttl_seconds=300  # Cache for 5 minutes
)
async def get_available_licenses(context: OrganizationContext):
    """
    Return available Microsoft 365 licenses from organization subscription.

    Returns:
        list: Available license options with metadata
    """
    try:
        graph = context.get_integration("msgraph")
        skus = await graph.get_subscribed_skus()

        available_licenses = []
        for sku in skus.value:
            available_units = sku.prepaid_units.enabled - sku.consumed_units

            if available_units > 0:
                available_licenses.append({
                    "label": f"{sku.sku_part_number} ({available_units} available)",
                    "value": sku.sku_id,
                    "metadata": {
                        "sku_part_number": sku.sku_part_number,
                        "available": available_units,
                        "total": sku.prepaid_units.enabled,
                        "consumed": sku.consumed_units
                    }
                })

        context.log("info", f"Found {len(available_licenses)} available licenses")

        return available_licenses

    except Exception as e:
        context.log("error", "Failed to get available licenses", {"error": str(e)})
        return []
```

### Pattern 3: Integration with External API

```python
# Request: "Create an integration with a custom REST API for user management"

# AI Agent Response:
# /workspace/integrations/user_management_api.py
from engine.shared.integrations.base import BaseIntegration
from engine.shared.error_handling import IntegrationError
from engine.shared.context import OrganizationContext
import aiohttp
from datetime import datetime
from typing import Dict, Any, List

class UserManagementAPIIntegration(BaseIntegration):
    """Integration with custom user management REST API."""

    integration_name = "user_management_api"

    async def authenticate(self):
        """Authenticate to the user management API."""
        api_key = await self.get_secret("user_management_api_key")
        base_url = self.get_config("user_management_api_url", "https://api.example.com")

        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Bifrost-Integrations/1.0"
        }

        # Test authentication
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/health",
                    headers=self.headers
                ) as response:
                    if response.status != 200:
                        raise IntegrationError(
                            integration="user_management_api",
                            message="API authentication failed",
                            status_code=response.status
                        )
        except Exception as e:
            raise IntegrationError(
                integration="user_management_api",
                message=f"Failed to authenticate: {str(e)}"
            )

        return api_key

    async def create_user(self, email: str, name: str, department: str) -> Dict[str, Any]:
        """Create a new user in the external system."""
        started_at = datetime.utcnow()
        url = f"{self.base_url}/users"

        payload = {
            "email": email,
            "name": name,
            "department": department,
            "created_at": datetime.utcnow().isoformat()
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=self.headers) as response:
                    duration_ms = int((datetime.utcnow() - started_at).total_seconds() * 1000)

                    if response.status == 201:
                        user_data = await response.json()

                        # Track successful call
                        self.context._track_integration_call(
                            integration="user_management_api",
                            method="POST",
                            endpoint="/users",
                            status_code=response.status,
                            duration_ms=duration_ms
                        )

                        self.context.log("info", "User created in external system", {
                            "user_id": user_data.get("id"),
                            "email": email
                        })

                        return user_data
                    else:
                        error_text = await response.text()

                        # Track failed call
                        self.context._track_integration_call(
                            integration="user_management_api",
                            method="POST",
                            endpoint="/users",
                            status_code=response.status,
                            duration_ms=duration_ms,
                            error=error_text
                        )

                        raise IntegrationError(
                            integration="user_management_api",
                            message=f"Failed to create user: {error_text}",
                            status_code=response.status,
                            details={"email": email, "response": error_text}
                        )

        except aiohttp.ClientError as e:
            duration_ms = int((datetime.utcnow() - started_at).total_seconds() * 1000)

            # Track network error
            self.context._track_integration_call(
                integration="user_management_api",
                method="POST",
                endpoint="/users",
                status_code=500,
                duration_ms=duration_ms,
                error=str(e)
            )

            raise IntegrationError(
                integration="user_management_api",
                message=f"Network error: {str(e)}",
                details={"email": email}
            )

    async def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get user details from external system."""
        started_at = datetime.utcnow()
        url = f"{self.base_url}/users/{user_id}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    duration_ms = int((datetime.utcnow() - started_at).total_seconds() * 1000)

                    if response.status == 200:
                        user_data = await response.json()

                        self.context._track_integration_call(
                            integration="user_management_api",
                            method="GET",
                            endpoint=f"/users/{user_id}",
                            status_code=response.status,
                            duration_ms=duration_ms
                        )

                        return user_data
                    else:
                        error_text = await response.text()

                        self.context._track_integration_call(
                            integration="user_management_api",
                            method="GET",
                            endpoint=f"/users/{user_id}",
                            status_code=response.status,
                            duration_ms=duration_ms,
                            error=error_text
                        )

                        raise IntegrationError(
                            integration="user_management_api",
                            message=f"User not found: {error_text}",
                            status_code=response.status,
                            details={"user_id": user_id}
                        )

        except aiohttp.ClientError as e:
            duration_ms = int((datetime.utcnow() - started_at).total_seconds() * 1000)

            self.context._track_integration_call(
                integration="user_management_api",
                method="GET",
                endpoint=f"/users/{user_id}",
                status_code=500,
                duration_ms=duration_ms,
                error=str(e)
            )

            raise IntegrationError(
                integration="user_management_api",
                message=f"Network error: {str(e)}",
                details={"user_id": user_id}
            )

# Register the integration
from engine.shared.integrations.base import register_integration
register_integration("user_management_api", UserManagementAPIIntegration)
```

### Pattern 4: Scheduled Workflow for Automation

```python
# Request: "Create a scheduled workflow to audit user licenses weekly"

# AI Agent Response:
@workflow(
    name="weekly_license_audit",
    description="Weekly audit of Microsoft 365 license usage",
    category="automation",
    execution_mode="scheduled",
    schedule="0 9 * * 1",  # Every Monday at 9 AM UTC
    expose_in_forms=False,  # Cannot be called manually
    timeout_seconds=600,    # 10 minutes max
    tags=["audit", "licenses", "scheduled"]
)
async def weekly_license_audit(context: OrganizationContext):
    """
    Perform weekly audit of Microsoft 365 license usage.

    This workflow runs automatically every Monday morning to:
    1. Check current license utilization
    2. Identify unused or over-allocated licenses
    3. Generate audit report
    4. Send notification to administrators
    """
    context.log("info", "Starting weekly license audit")

    try:
        # Get Microsoft Graph integration
        graph = context.get_integration("msgraph")

        # Get all subscribed SKUs
        context.save_checkpoint("getting_licenses", {})
        skus = await graph.get_subscribed_skus()

        audit_results = {
            "audit_date": datetime.utcnow().isoformat(),
            "total_skus": len(skus.value),
            "licenses": [],
            "summary": {
                "total_licenses": 0,
                "used_licenses": 0,
                "available_licenses": 0,
                "utilization_rate": 0.0
            },
            "recommendations": []
        }

        # Analyze each license SKU
        for sku in skus.value:
            enabled = sku.prepaid_units.enabled
            consumed = sku.consumed_units
            available = enabled - consumed
            utilization_rate = (consumed / enabled * 100) if enabled > 0 else 0

            license_info = {
                "sku_part_number": sku.sku_part_number,
                "sku_id": sku.sku_id,
                "enabled": enabled,
                "consumed": consumed,
                "available": available,
                "utilization_rate": round(utilization_rate, 2)
            }

            audit_results["licenses"].append(license_info)
            audit_results["summary"]["total_licenses"] += enabled
            audit_results["summary"]["used_licenses"] += consumed
            audit_results["summary"]["available_licenses"] += available

            # Generate recommendations
            if utilization_rate < 50:
                audit_results["recommendations"].append({
                    "type": "underutilized",
                    "sku": sku.sku_part_number,
                    "message": f"License {sku.sku_part_number} is only {utilization_rate:.1f}% utilized",
                    "action": "Consider reducing license count"
                })
            elif utilization_rate > 95:
                audit_results["recommendations"].append({
                    "type": "overutilized",
                    "sku": sku.sku_part_number,
                    "message": f"License {sku.sku_part_number} is {utilization_rate:.1f}% utilized",
                    "action": "Consider purchasing additional licenses"
                })

        # Calculate overall utilization
        total = audit_results["summary"]["total_licenses"]
        used = audit_results["summary"]["used_licenses"]
        audit_results["summary"]["utilization_rate"] = round((used / total * 100) if total > 0 else 0, 2)

        # Save checkpoint
        context.save_checkpoint("audit_complete", {
            "licenses_analyzed": len(audit_results["licenses"]),
            "recommendations": len(audit_results["recommendations"])
        })

        # Send audit report
        admin_email = context.get_config("admin_email")
        if admin_email:
            await send_audit_report(context, admin_email, audit_results)

        context.log("info", "License audit completed", {
            "licenses_analyzed": len(audit_results["licenses"]),
            "utilization_rate": audit_results["summary"]["utilization_rate"],
            "recommendations": len(audit_results["recommendations"])
        })

        return audit_results

    except Exception as e:
        context.log("error", "License audit failed", {"error": str(e)})
        raise WorkflowException(f"License audit failed: {str(e)}")

async def send_audit_report(context, admin_email, audit_results):
    """Send audit report via email."""
    # This would integrate with an email service
    context.log("info", "Audit report sent", {
        "recipient": admin_email,
        "utilization_rate": audit_results["summary"]["utilization_rate"]
    })
```

---

## Common Tasks

### Task 1: Creating a User Management Workflow

**User Request**: "I need a workflow to create users in both Microsoft 365 and our internal system"

**AI Agent Response**:

```python
# /workspace/workflows/user_management/create_user_sync/workflow.py
from engine.shared.decorators import workflow, param
from engine.shared.context import OrganizationContext
from engine.shared.error_handling import ValidationError, IntegrationError

@workflow(
    name="create_user_sync",
    description="Create user in both Microsoft 365 and internal system",
    category="user_management",
    tags=["m365", "sync", "user-management"]
)
@param("email", "email", "User email address", required=True)
@param("name", "string", "User full name", required=True)
@param("department", "string", "Department", data_provider="get_departments")
@param("license_sku", "string", "M365 License", data_provider="get_available_licenses")
async def create_user_sync(
    context: OrganizationContext,
    email: str,
    name: str,
    department: str,
    license_sku: str
):
    """
    Create user in Microsoft 365 and synchronize with internal system.
    """
    context.log("info", f"Creating synchronized user: {email}")

    try:
        # Create in Microsoft 365 first
        graph = context.get_integration("msgraph")
        m365_user = await graph.create_user(email, name, department)
        await graph.assign_license(m365_user["id"], license_sku)

        context.save_checkpoint("m365_user_created", {
            "user_id": m365_user["id"],
            "email": email
        })

        # Create in internal system
        internal_api = context.get_integration("user_management_api")
        internal_user = await internal_api.create_user(email, name, department)

        context.save_checkpoint("internal_user_created", {
            "user_id": internal_user["id"],
            "email": email
        })

        # Store mapping for future synchronization
        await store_user_mapping(context, m365_user["id"], internal_user["id"])

        return {
            "success": True,
            "m365_user_id": m365_user["id"],
            "internal_user_id": internal_user["id"],
            "email": email,
            "name": name
        }

    except Exception as e:
        context.log("error", "User synchronization failed", {"error": str(e)})
        raise IntegrationError(
            message="Failed to create synchronized user",
            details={"email": email, "error": str(e)}
        )

async def store_user_mapping(context, m365_id, internal_id):
    """Store user ID mapping for synchronization."""
    # This would store the mapping in a database or table
    context.log("info", "User mapping stored", {
        "m365_id": m365_id,
        "internal_id": internal_id
    })
```

### Task 2: Creating a Data Provider

**User Request**: "I need a data provider that shows all active users for selection"

**AI Agent Response**:

```python
# /workspace/data_providers/get_active_users.py
from engine.shared.decorators import data_provider
from engine.shared.context import OrganizationContext

@data_provider(
    name="get_active_users",
    description="Get list of active users for selection",
    category="organization",
    cache_ttl_seconds=600  # Cache for 10 minutes
)
async def get_active_users(context: OrganizationContext):
    """
    Return active users from Microsoft 365 for form selection.

    Returns:
        list: Active users with display names and emails
    """
    try:
        graph = context.get_integration("msgraph")

        # Get only enabled users
        users = await graph.get_users(
            filter="accountEnabled eq true",
            select=["id", "displayName", "userPrincipalName", "department", "jobTitle"]
        )

        active_users = []
        for user in users.value:
            display_name = user.get("displayName", "Unknown")
            email = user.get("userPrincipalName", "")
            department = user.get("department", "No Department")

            active_users.append({
                "label": f"{display_name} ({email}) - {department}",
                "value": user["id"],
                "metadata": {
                    "email": email,
                    "display_name": display_name,
                    "department": department,
                    "job_title": user.get("jobTitle", "")
                }
            })

        # Sort by display name
        active_users.sort(key=lambda x: x["metadata"]["display_name"])

        context.log("info", f"Retrieved {len(active_users)} active users")

        return active_users

    except Exception as e:
        context.log("error", "Failed to get active users", {"error": str(e)})
        return []
```

### Task 3: Creating Integration Tests

**User Request**: "Write tests for the user creation workflow"

**AI Agent Response**:

```python
# /workspace/tests/test_user_workflows.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from workspace.workflows.user_management.create_user_sync import create_user_sync

@pytest.mark.asyncio
async def test_create_user_sync_success():
    """Test successful user synchronization."""

    # Mock context
    context = MagicMock()
    context.org_id = "test-org"
    context.org_name = "Test Organization"
    context.get_config = MagicMock(return_value="test_value")
    context.log = MagicMock()
    context.save_checkpoint = MagicMock()

    # Mock Microsoft Graph integration
    mock_graph = AsyncMock()
    mock_graph.create_user = AsyncMock(return_value={
        "id": "m365-user-123",
        "displayName": "Test User",
        "userPrincipalName": "test@example.com"
    })
    mock_graph.assign_license = AsyncMock(return_value={"success": True})

    # Mock internal API integration
    mock_internal_api = AsyncMock()
    mock_internal_api.create_user = AsyncMock(return_value={
        "id": "internal-user-456",
        "email": "test@example.com",
        "name": "Test User"
    })

    # Set up integration mocks
    def get_integration_mock(name):
        if name == "msgraph":
            return mock_graph
        elif name == "user_management_api":
            return mock_internal_api
        else:
            raise ValueError(f"Unknown integration: {name}")

    context.get_integration = MagicMock(side_effect=get_integration_mock)

    # Execute workflow
    result = await create_user_sync(
        context,
        email="test@example.com",
        name="Test User",
        department="IT",
        license_sku="ENTERPRISEPACK"
    )

    # Assertions
    assert result["success"] is True
    assert result["m365_user_id"] == "m365-user-123"
    assert result["internal_user_id"] == "internal-user-456"
    assert result["email"] == "test@example.com"

    # Verify integration calls
    mock_graph.create_user.assert_called_once_with(
        "test@example.com", "Test User", "IT"
    )
    mock_graph.assign_license.assert_called_once_with(
        "m365-user-123", "ENTERPRISEPACK"
    )
    mock_internal_api.create_user.assert_called_once_with(
        "test@example.com", "Test User", "IT"
    )

    # Verify logging
    context.log.assert_called()
    context.save_checkpoint.assert_called()

@pytest.mark.asyncio
async def test_create_user_sync_graph_failure():
    """Test handling of Microsoft Graph failure."""

    context = MagicMock()
    context.log = MagicMock()
    context.save_checkpoint = MagicMock()

    # Mock Graph failure
    mock_graph = AsyncMock()
    mock_graph.create_user.side_effect = Exception("Graph API error")

    context.get_integration = MagicMock(return_value=mock_graph)

    # Execute and expect failure
    with pytest.raises(IntegrationError) as exc_info:
        await create_user_sync(
            context,
            email="test@example.com",
            name="Test User",
            department="IT",
            license_sku="ENTERPRISEPACK"
        )

    assert "Failed to create synchronized user" in str(exc_info.value)
    context.log.assert_called()

@pytest.mark.asyncio
async def test_create_user_sync_validation_error():
    """Test input validation."""

    context = MagicMock()

    # Test invalid email
    with pytest.raises(ValidationError):
        await create_user_sync(
            context,
            email="invalid-email",  # Invalid format
            name="Test User",
            department="IT",
            license_sku="ENTERPRISEPACK"
        )
```

---

## Best Practices

### 1. Code Organization

**Follow Folder Structure**

```
/workspace/workflows/user_management/
├── create_user/
│   ├── workflow.py
│   ├── diagram.mmd
│   ├── lib/
│   │   ├── __init__.py
│   │   ├── helpers.py
│   │   └── validators.py
│   └── tests/
│       ├── __init__.py
│       └── test_workflow.py
```

**Use Descriptive Names**

```python
# ✅ Good
@workflow(name="create_m365_user_with_license")
async def create_m365_user_with_license(...):

# ❌ Bad
@workflow(name="user_proc1")
async def user_proc1(...):
```

### 2. Error Handling

**Use Specific Exceptions**

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
    raise Exception("Wrong email domain")
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
    raise IntegrationError("API call failed")

# ❌ Bad
try:
    result = await api_call()
except Exception as e:
    raise IntegrationError("API call failed")
```

### 3. Performance

**Use Async for Parallel Operations**

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

**Process Large Datasets in Batches**

```python
# ✅ Good - Batch processing
batch_size = 50
for i in range(0, len(users), batch_size):
    batch = users[i:i + batch_size]
    await process_batch(batch)

# ❌ Bad - Process all at once
await process_all_users(users)  # Could timeout
```

### 4. Security

**Never Log Sensitive Data**

```python
# ✅ Good
context.log("info", "User created successfully", {
    "user_id": user["id"],
    "email_domain": email.split("@")[1]  # Only domain
})

# ❌ Bad - Logging PII
context.log("info", "User created", {
    "user_id": user["id"],
    "email": email,  # PII!
    "api_key": api_key  # Secret!
})
```

**Use Context for Secrets**

```python
# ✅ Good
api_key = await context.get_secret("api_key")

# ❌ Bad - Hardcoded secrets
api_key = "sk-1234567890abcdef"
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: Import Errors

**Problem**: `ImportError: Workspace code cannot import engine module`

**Solution**: Only import from allowed modules:

```python
# ✅ Allowed
from engine.shared.decorators import workflow
from engine.shared.context import OrganizationContext

# ❌ Blocked
from engine.shared.storage import get_organization
```

#### Issue 2: Workflow Not Found

**Problem**: 404 when executing workflow

**Solution**: Ensure workflow is in correct location and has decorator:

```python
# File must be: /workspace/workflows/category/name/workflow.py
@workflow(name="workflow_name")  # Required decorator
async def workflow_name(...):
```

#### Issue 3: Integration Not Available

**Problem**: `Integration 'xyz' not found`

**Solution**: Register integration properly:

```python
# In integration file
from engine.shared.integrations.base import register_integration
register_integration("integration_name", IntegrationClass)
```

#### Issue 4: Tests Failing

**Problem**: Mock objects not working correctly

**Solution**: Use proper mocking patterns:

```python
# ✅ Good
context.get_integration = MagicMock(side_effect=lambda name: mock_graph)

# ❌ Bad
context.get_integration.return_value = mock_graph  # Won't work with multiple calls
```

### Debugging Tips

1. **Use Checkpoints**: Add checkpoints to track progress
2. **Enable Debug Logging**: Use context.log() extensively
3. **Test Locally**: Always test with local development environment
4. **Check Error Messages**: Read full error details for clues
5. **Verify Configuration**: Ensure all required config values exist

This guide helps AI agents provide effective assistance while maintaining security and best practices in the Bifrost Integrations platform.
