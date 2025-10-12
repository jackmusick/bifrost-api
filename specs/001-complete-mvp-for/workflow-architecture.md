# Workflow Architecture: Advanced Features

**Date**: 2025-10-10
**Status**: Design Complete
**Purpose**: Document advanced workflow features including error handling, scheduling, state management, and execution modes

---

## Overview

The workflow engine supports three execution modes, comprehensive error handling, cron scheduling, webhooks, state tracking, and full execution observability.

---

## 1. Execution Modes

### Synchronous (Default)
- Frontend waits for response
- Max 30 seconds (HTTP timeout)
- Returns result immediately
- Use for: Quick operations (<30s)

```python
@workflow(
    name="user_onboarding",
    execution_mode="sync",
    timeout_seconds=30
)
async def onboard_user(context, email, first_name):
    # Quick user creation
    return {"user_id": "..."}
```

**Client Flow:**
```
POST /workflows/user_onboarding
→ waits for response (max 30s)
← {"status": "Success", "result": {...}}
```

### Asynchronous (Queued)
- Returns execution ID immediately (202 Accepted)
- Workflow runs in background via Azure Queue Storage
- Client polls for status
- Use for: Long-running operations (>30s)

```python
@workflow(
    name="long_migration",
    execution_mode="async",
    timeout_seconds=600,  # 10 minutes
    max_duration_seconds=600
)
async def migrate_mailboxes(context, user_ids):
    # Long-running migration
    for user_id in user_ids:
        # ... migrate each mailbox
        context.save_checkpoint(f"migrated_user_{user_id}", {...})

    return {"migrated_count": len(user_ids)}
```

**Client Flow:**
```
POST /workflows/long_migration
← {"executionId": "exec-123", "status": "Queued", "pollUrl": "/executions/exec-123"}

GET /executions/exec-123
← {"status": "Running", "progress": 45}

GET /executions/exec-123
← {"status": "Success", "result": {...}}
```

### Scheduled (Cron)
- Triggered by timer (every minute check)
- Runs for all orgs with workflow enabled
- No input parameters
- Use for: Automated maintenance, audits, reports

```python
@workflow(
    name="daily_license_audit",
    execution_mode="scheduled",
    schedule="0 9 * * *",  # Every day at 9 AM UTC
    expose_in_forms=False,  # Can't be called from forms
    timeout_seconds=600
)
async def audit_licenses(context):
    """Runs automatically for all orgs at 9 AM."""
    graph = context.get_integration('msgraph')
    skus = await graph.get_subscribed_skus()

    # Calculate unused licenses
    unused = [...]

    context.log("info", f"Found {len(unused)} unused licenses")

    return {"unused_licenses": unused}
```

**Schedule Formats:**
```
"0 9 * * *"      → Every day at 9:00 AM
"*/15 * * * *"   → Every 15 minutes
"0 0 * * 1"      → Every Monday at midnight
"0 9 * * 1-5"    → Weekdays at 9 AM
"0 0 1 * *"      → First day of month at midnight
```

---

## 2. Error Handling

### Standard Error Types

All workflow exceptions inherit from `WorkflowException` and produce standardized error responses:

```python
from shared.error_handling import (
    ValidationError,
    IntegrationError,
    TimeoutError,
    ConfigurationError,
    PermissionError
)

@workflow(name="create_user", ...)
async def create_user(context, email, first_name, last_name):
    # Validate input
    if not email or '@' not in email:
        raise ValidationError("Invalid email address", field="email")

    # Check config
    if not context.has_config('msgraph_client_id'):
        raise ConfigurationError(
            "Microsoft Graph not configured",
            config_key="msgraph_client_id"
        )

    # Call external API
    try:
        graph = context.get_integration('msgraph')
        user = await graph.create_user(email, first_name, last_name)
    except Exception as e:
        raise IntegrationError(
            integration="msgraph",
            message=f"Failed to create user: {str(e)}",
            status_code=getattr(e, 'status_code', None)
        )

    return {"user_id": user['id']}
```

### Error Response Format

**ValidationError (400 Bad Request):**
```json
{
  "executionId": "exec-123",
  "status": "Failed",
  "error": "ValidationError",
  "message": "Invalid email address",
  "details": {
    "field": "email"
  }
}
```

**IntegrationError (500 Internal Server Error):**
```json
{
  "executionId": "exec-123",
  "status": "Failed",
  "error": "IntegrationError",
  "message": "Failed to create user: 401 Unauthorized",
  "details": {
    "integration": "msgraph",
    "status_code": 401
  }
}
```

**TimeoutError (500):**
```json
{
  "executionId": "exec-123",
  "status": "Failed",
  "error": "TimeoutError",
  "message": "Workflow exceeded timeout of 300 seconds",
  "details": {
    "timeout_seconds": 300
  }
}
```

**Unexpected Error (500):**
```json
{
  "executionId": "exec-123",
  "status": "Failed",
  "error": "InternalServerError",
  "message": "An unexpected error occurred during workflow execution",
  "details": {}
}
```
*Note: Internal error details are logged but NOT exposed to client for security*

### Webhook Error Handling

Webhooks return generic 400 errors to external systems:

```json
{
  "error": "BadRequest",
  "message": "Failed to process webhook"
}
```

Full error details are logged internally but not exposed.

---

## 3. State Tracking & Observability

### Checkpoints

Save state snapshots during execution for debugging and resumability:

```python
@workflow(name="complex_onboarding", ...)
async def onboard_user(context, email, first_name, last_name, department):
    # Checkpoint 1: User creation
    context.save_checkpoint("create_user_start", {
        "email": email,
        "first_name": first_name,
        "last_name": last_name
    })

    graph = context.get_integration('msgraph')
    user = await graph.create_user(email, first_name, last_name)

    context.set_variable("user_id", user['id'])
    context.save_checkpoint("user_created", {
        "user_id": user['id']
    })

    # Checkpoint 2: Group assignment
    context.log("info", f"Assigning to department: {department}")
    group_id = await graph.get_group_by_name(f"{department}-Users")
    await graph.add_user_to_group(user['id'], group_id)

    context.set_variable("group_id", group_id)
    context.save_checkpoint("group_assigned", {"group_id": group_id})

    return {
        "user_id": user['id'],
        "checkpoints_completed": 3
    }
```

### Logging

Structured logging within workflows:

```python
context.log("info", "Starting user provisioning", {
    "email": email,
    "department": department
})

context.log("warning", "Failed to assign to default group", {
    "group_name": "Default-Users",
    "error": str(e)
})

context.log("error", "Critical failure in license assignment", {
    "license_sku": sku_id,
    "user_id": user_id
})
```

### Variables

Persist workflow state across execution:

```python
context.set_variable("users_processed", 0)
context.set_variable("errors_encountered", [])

for user in users:
    try:
        # Process user
        count = context.get_variable("users_processed", 0)
        context.set_variable("users_processed", count + 1)
    except Exception as e:
        errors = context.get_variable("errors_encountered", [])
        errors.append({"user": user, "error": str(e)})
        context.set_variable("errors_encountered", errors)
```

### Integration Call Tracking

All integration client calls are automatically tracked:

```python
# Automatic tracking in integration clients
graph = context.get_integration('msgraph')
await graph.create_user(...)  # Automatically logged

# Tracking includes:
# - Timestamp
# - Integration name (msgraph, halopsa, etc.)
# - HTTP method and endpoint
# - Status code
# - Duration in milliseconds
# - Success/failure
# - Error message (if failed)
```

### Execution Record

Complete execution record stored in WorkflowExecutions table:

```json
{
  "ExecutionId": "exec-abc-123",
  "WorkflowName": "complex_onboarding",
  "Status": "Success",
  "StartedAt": "2025-10-10T14:30:00Z",
  "CompletedAt": "2025-10-10T14:30:15Z",
  "DurationMs": 15234,

  "InputData": "{\"email\":\"john@acme.com\", ...}",
  "Result": "{\"user_id\":\"user-123\", ...}",

  "StateSnapshots": [
    {
      "timestamp": "2025-10-10T14:30:01Z",
      "name": "create_user_start",
      "data": {"email": "john@acme.com", "first_name": "John"}
    },
    {
      "timestamp": "2025-10-10T14:30:05Z",
      "name": "user_created",
      "data": {"user_id": "user-123"}
    },
    {
      "timestamp": "2025-10-10T14:30:10Z",
      "name": "group_assigned",
      "data": {"group_id": "group-456"}
    }
  ],

  "IntegrationCalls": [
    {
      "timestamp": "2025-10-10T14:30:02Z",
      "integration": "msgraph",
      "method": "POST",
      "endpoint": "/v1.0/users",
      "status_code": 201,
      "duration_ms": 2345,
      "success": true
    },
    {
      "timestamp": "2025-10-10T14:30:08Z",
      "integration": "msgraph",
      "method": "POST",
      "endpoint": "/v1.0/groups/{id}/members",
      "status_code": 204,
      "duration_ms": 1234,
      "success": true
    }
  ],

  "Logs": [
    {
      "timestamp": "2025-10-10T14:30:00Z",
      "level": "info",
      "message": "Starting user provisioning",
      "data": {"email": "john@acme.com", "department": "Sales"}
    },
    {
      "timestamp": "2025-10-10T14:30:07Z",
      "level": "info",
      "message": "Assigning to department: Sales"
    }
  ],

  "Variables": {
    "user_id": "user-123",
    "group_id": "group-456"
  }
}
```

**Data Sanitization:**
- Secrets, passwords, tokens, keys are REDACTED
- Long strings truncated to 1000 characters
- Arrays limited to 100 items
- Total execution record size managed to fit Table Storage limits

---

## 4. Webhooks

### Enabling Webhooks

```python
@workflow(
    name="process_ticket_update",
    description="Handle HaloPSA ticket webhooks",
    webhook_enabled=True,
    webhook_secret_required=True,
    expose_in_forms=False,  # Webhooks only
    execution_mode="async"  # Always async for webhooks
)
async def process_ticket_webhook(context, ticket_id, status, notes):
    context.log("info", f"Processing ticket update: {ticket_id}")

    # Workflow logic
    return {"processed": True}
```

### Webhook URL

```
POST https://your-functions.azurewebsites.net/webhooks/{orgId}/{workflowName}
Headers:
  X-Webhook-Secret: <secret>
Body:
  {
    "ticket_id": "123",
    "status": "closed",
    "notes": "Resolved by technician"
  }
```

### Webhook Response

```json
{
  "executionId": "exec-456",
  "status": "Queued",
  "message": "Webhook received and queued for processing"
}
```

**Status Code:** 202 Accepted (always async)

---

## 5. Context API

### Organization Properties

```python
# Direct org information
context.org_id           # "org-abc-123"
context.org_name         # "Acme Corp"
context.tenant_id        # "tenant-456-789" (M365 tenant)

# Execution metadata
context.execution_id     # "exec-xyz-999"
context.executed_by      # "user-123" (User ID)
context.executed_by_email  # "john@msp.com"
context.executed_by_name   # "John Doe"
```

### Configuration (Key-Value)

```python
# Get org-specific config
default_location = context.get_config('default_office_location', 'Remote')
halo_client_id = context.get_config('halo_client_id')

# Check if config exists
if context.has_config('enable_auto_licensing'):
    # ...
```

### Secrets (Azure Key Vault)

```python
# Get secret (org-scoped)
api_key = await context.get_secret('halopsa_api_key')
client_secret = await context.get_secret('msgraph_client_secret')

# Secrets are stored as: {org_id}--{key}
# Example: "org-abc-123--halopsa_api_key"
```

### Pre-Authenticated Integrations

```python
# Microsoft Graph
graph = context.get_integration('msgraph')
user = await graph.create_user(...)
await graph.assign_license(...)

# HaloPSA
halo = context.get_integration('halopsa')
ticket = await halo.create_ticket(...)

# Integrations are:
# - Automatically authenticated
# - Cached for request duration
# - Call tracking enabled automatically
```

---

## 6. Forms → Workflows

### Form Access Control

```python
@workflow(
    name="user_onboarding",
    expose_in_forms=True,      # ✅ Can be called from forms
    requires_approval=False
)

@workflow(
    name="delete_organization",
    expose_in_forms=True,
    requires_approval=True      # ⚠️ Requires approval
)

@workflow(
    name="internal_sync",
    expose_in_forms=False       # ❌ Internal only (API/scheduled)
)
```

### Form Submission Flow

```typescript
// Frontend form submission
async function submitForm(formId: string, formData: Record<string, any>) {
  const form = await apiClient.get(`/forms/${formId}`);

  // Execute linked workflow
  const response = await workflowClient.executeWorkflow(
    form.LinkedWorkflow,
    orgId,
    formData
  );

  // Handle sync vs async
  if (response.status === 202) {
    // Async - poll for status
    pollExecutionStatus(response.executionId);
  } else {
    // Sync - show result
    showResult(response.result);
  }
}
```

### Backend Form Endpoint

```python
@bp.route(route="forms/{formId}/submit", methods=["POST"])
async def submit_form(req, context):
    form = await storage.get_form(context.org_id, form_id)
    form_data = req.get_json()

    # Get linked workflow
    workflow = registry.get_workflow(form.LinkedWorkflow)

    # Check if workflow allows form access
    if not workflow.expose_in_forms:
        return func.HttpResponse("Forbidden", status_code=403)

    # Execute workflow (respects execution_mode)
    return await execute_workflow_internal(
        workflow,
        context,
        parameters=form_data,
        triggered_by_form=form_id
    )
```

---

## 7. Complete @workflow Decorator Reference

```python
@workflow(
    # === IDENTITY ===
    name="workflow_name",              # Required: Unique identifier (snake_case)
    description="Description here",     # Required: Human-readable description
    category="user_management",         # Optional: Category (default: "General")
    tags=["m365", "user"],             # Optional: Tags for filtering

    # === EXECUTION ===
    execution_mode="sync",              # "sync" | "async" | "scheduled"
    timeout_seconds=300,                # Max execution time (default: 300)
    max_duration_seconds=300,           # Hard limit (default: 300)

    # === RETRY ===
    retry_policy={                      # Optional: Retry configuration
        "max_attempts": 3,
        "backoff_multiplier": 2
    },

    # === SCHEDULING ===
    schedule="0 9 * * *",               # Optional: Cron expression

    # === ACCESS CONTROL ===
    requires_org=True,                  # Requires org context? (default: True)
    expose_in_forms=True,               # Can be called from forms? (default: True)
    requires_approval=False,            # Requires approval? (default: False)
    required_permission="canExecuteWorkflows",  # Permission required

    # === WEBHOOKS ===
    webhook_enabled=False,              # Can be triggered via webhook?
    webhook_secret_required=True        # Webhook requires secret?
)
async def my_workflow(context, ...):
    pass
```

---

## 8. Integration Client Development

### Creating New Integrations

```python
# shared/integrations/connectwise.py
from shared.integrations.base import BaseIntegration
from shared.error_handling import IntegrationError

class ConnectWiseIntegration(BaseIntegration):
    integration_name = "connectwise"  # Auto-registered

    async def authenticate(self) -> str:
        """Implement CW-specific auth."""
        company_id = self.get_config('cw_company_id')
        public_key = self.get_config('cw_public_key')
        private_key = await self.get_secret('cw_private_key')

        # CW auth logic
        # ...

        return access_token

    async def create_ticket(self, summary: str, description: str):
        """Standard method."""
        started_at = datetime.utcnow()
        endpoint = "/v2022_1/service/tickets"

        try:
            token = await self.authenticate()
            response = await self.http_client.post(
                f"{self.api_url}{endpoint}",
                headers={"Authorization": f"Bearer {token}"},
                json={"summary": summary, "description": description}
            )

            # Track successful call
            duration_ms = int((datetime.utcnow() - started_at).total_seconds() * 1000)
            self.context._track_integration_call(
                integration="connectwise",
                method="POST",
                endpoint=endpoint,
                status_code=response.status_code,
                duration_ms=duration_ms,
                error=None
            )

            return response.json()

        except Exception as e:
            # Track failed call
            duration_ms = int((datetime.utcnow() - started_at).total_seconds() * 1000)
            self.context._track_integration_call(
                integration="connectwise",
                method="POST",
                endpoint=endpoint,
                status_code=getattr(e, 'status_code', 500),
                duration_ms=duration_ms,
                error=str(e)
            )

            raise IntegrationError(
                integration="connectwise",
                message=f"Failed to create ticket: {str(e)}",
                status_code=getattr(e, 'status_code', None)
            )
```

### Using Integrations in Workflows

```python
@workflow(name="create_cw_ticket", ...)
async def create_ticket(context, summary, description):
    # Get pre-authenticated client
    cw = context.get_integration('connectwise')

    # Use it immediately - already authenticated
    ticket = await cw.create_ticket(summary, description)

    return {"ticket_id": ticket['id'], "ticket_url": ticket['url']}
```

---

## 9. Testing Patterns

### Testing Workflows with Mock Context

```python
# tests/unit/test_workflows.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from workflows.user_onboarding import onboard_user

@pytest.mark.asyncio
async def test_onboard_user_success():
    # Mock context
    context = MagicMock()
    context.org_id = "org-123"
    context.org_name = "Test Org"
    context.get_config = MagicMock(return_value="default_value")

    # Mock integration
    mock_graph = AsyncMock()
    mock_graph.create_user = AsyncMock(return_value={"id": "user-456"})
    context.get_integration = MagicMock(return_value=mock_graph)

    # Execute workflow
    result = await onboard_user(
        context,
        email="test@example.com",
        first_name="Test",
        last_name="User"
    )

    # Assert
    assert result["success"] is True
    assert result["user_id"] == "user-456"
    mock_graph.create_user.assert_called_once()
```

---

## Summary

The workflow engine provides enterprise-grade features:

✅ **Three execution modes** (sync, async, scheduled)
✅ **Comprehensive error handling** with standardized error types
✅ **Cron scheduling** with per-org enablement
✅ **Webhook support** with secret validation
✅ **Complete observability** (checkpoints, logs, variables, integration tracking)
✅ **Secure context API** (org data, config, secrets, pre-auth integrations)
✅ **Form integration** with access control
✅ **Extensible integration framework** for adding new services

All features are production-ready and follow Azure best practices.
