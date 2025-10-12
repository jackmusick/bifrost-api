# Quickstart: Workflow Engine and User Code Separation

**Feature**: 002-i-want-to
**Date**: 2025-10-12
**Audience**: Developers writing custom workflows

## Overview

This guide helps you get started with the new `/engine` and `/workspace` folder structure, understand the security boundaries, and develop workflows locally.

## Prerequisites

- Azure Functions Core Tools 4.x installed (`func --version`)
- Python 3.11 installed
- Azurite storage emulator installed
- Git configured for this repository
- (Optional) Static Web Apps CLI for auth testing (`npm install -g @azure/static-web-apps-cli`)

## Quick Setup (5 Minutes)

### 1. Fork or Clone Repository

```bash
# If you haven't already, fork the canonical workflows repository
gh repo fork msp-workflows/workflows --clone

# Or clone your existing fork
git clone https://github.com/YOUR-ORG/workflows.git
cd workflows
```

### 2. Install Dependencies

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 3. Start Azurite

```bash
# In a separate terminal
azurite --silent --location ./azurite-data --debug ./azurite-debug.log
```

### 4. Seed Test Data

```bash
# Populate Azurite with test organizations, users, config
python scripts/seed_azurite.py

# Expected output:
# ✓ Created 2 organizations
# ✓ Created 3 users (1 PlatformAdmin, 2 OrgUsers)
# ✓ Created 5 config entries
# Seed complete in 2.3s
```

### 5. Start Azure Functions

```bash
# Start the Functions runtime
func start

# Expected output:
# Azure Functions Core Tools
# Import restrictions installed for workspace paths: ['/app/workspace']
# Discovered 2 workflows from workspace
# ...
# Http Functions:
#     execute_workflow: [POST] http://localhost:7071/api/workflows/{workflowName}
```

### 6. Test Your First Workflow

```bash
# Test with function key (bypass auth)
curl -X POST http://localhost:7071/api/workflows/user-onboarding \
  -H "x-functions-key: dev-key" \
  -H "X-Organization-Id: test-org-1" \
  -H "X-User-Id: jack@gocovi.com" \
  -H "Content-Type: application/json" \
  -d '{"userName": "test.user", "email": "test@example.com"}'

# Expected response:
# {
#   "executionId": "abc-123",
#   "status": "Success",
#   "result": {"user_id": "test.user", "message": "User onboarded"},
#   "durationMs": 234
# }
```

✅ **You're ready to develop!**

## Repository Structure

```
workflows/
├── engine/               # ⚠️ DO NOT MODIFY - Protected system code
│   ├── shared/           # Core engine modules
│   │   ├── context.py    # Organization context
│   │   ├── decorators.py # @workflow, @data_provider
│   │   ├── auth.py       # Authentication service
│   │   └── import_restrictions.py  # Import blocker
│   ├── execute.py        # Workflow execution endpoint
│   └── function_app.py   # Azure Functions app
│
├── workspace/            # ✅ YOUR CODE GOES HERE
│   ├── workflows/        # Your custom workflows
│   │   └── my_workflow.py
│   └── data_providers/   # Your custom data providers
│       └── my_provider.py
│
├── tests/                # Test suite
├── scripts/              # Utility scripts
│   └── seed_azurite.py   # Test data seeding
└── .github/workflows/
    └── protect-engine.yml  # Blocks /engine modifications
```

## Creating Your First Workflow

### 1. Create Workflow File

```bash
# Create new workflow in workspace
touch workspace/workflows/send_welcome_email.py
```

### 2. Write Workflow Code

```python
# workspace/workflows/send_welcome_email.py

from shared.decorators import workflow
from shared.context import OrganizationContext

@workflow(
    name="send-welcome-email",
    description="Send welcome email to new user",
    category="Onboarding",
    parameters=[
        {"name": "user_email", "type": "string", "required": True},
        {"name": "user_name", "type": "string", "required": True}
    ]
)
async def send_welcome_email(context: OrganizationContext, user_email: str, user_name: str):
    """
    Send personalized welcome email to newly onboarded user.

    Args:
        context: Organization context (injected automatically)
        user_email: User's email address
        user_name: User's display name

    Returns:
        Dict with email status
    """
    # Access org configuration
    smtp_server = context.get_config('smtp_server', 'smtp.example.com')

    # Log workflow progress
    context.log('info', f"Sending welcome email to {user_email}")

    # Save checkpoint for debugging
    context.save_checkpoint('email_prepared', {
        'recipient': user_email,
        'smtp_server': smtp_server
    })

    # TODO: Implement email sending logic
    # For now, return success
    return {
        'status': 'sent',
        'recipient': user_email,
        'message': f"Welcome email sent to {user_name}"
    }
```

### 3. Test Locally

```bash
# Restart Functions runtime to discover new workflow
^C  # Stop current func start
func start

# Expected output should show:
# Discovered 3 workflows from workspace

# Test your workflow
curl -X POST http://localhost:7071/api/workflows/send-welcome-email \
  -H "x-functions-key: dev-key" \
  -H "X-Organization-Id: test-org-1" \
  -H "X-User-Id: jack@gocovi.com" \
  -H "Content-Type: application/json" \
  -d '{"user_email": "john@example.com", "user_name": "John Doe"}'
```

### 4. Debug with Breakpoints

```python
# In VS Code, set breakpoint in your workflow
# Press F5 or Run > Start Debugging
# Make curl request
# Debugger will pause at your breakpoint
```

## Allowed Imports

### ✅ Safe Imports (Whitelisted)

```python
# Shared modules (public API)
from shared.decorators import workflow, data_provider
from shared.context import OrganizationContext
from shared.error_handling import WorkflowException, ValidationError
from shared.models import WorkflowParameter

# Standard library
import json, datetime, uuid, logging

# Third-party packages
import aiohttp, pydantic

# Other workspace modules
from workspace.data_providers.my_provider import get_data
```

### ❌ Blocked Imports (Will Raise ImportError)

```python
# ❌ Engine internals - BLOCKED
from engine.shared.storage import get_table_storage_service
from engine.execute import execute_workflow
from shared.storage import TableStorageService  # Blocked (not in whitelist)

# Error message:
# ImportError: Workspace code cannot import engine module 'engine.shared.storage'.
# Use only the public API exported through 'shared.decorators', 'shared.context',
# 'shared.error_handling', and 'shared.models'.
```

## Authentication Methods

### Method 1: Function Key (Local Development)

```bash
# Simplest for local testing - bypasses authentication
curl -H "x-functions-key: dev-key" \
     -H "X-Organization-Id: test-org-1" \
     -H "X-User-Id: jack@gocovi.com" \
     http://localhost:7071/api/workflows/my-workflow
```

**Use when**:
- Local development and testing
- CI/CD pipelines
- System integrations
- Administrative operations

### Method 2: Azure Easy Auth (Production-Like)

```bash
# Start with SWA CLI for full auth emulation
swa start --api-location ./workflows --app-location ./client

# Login via browser
open http://localhost:4280/.auth/login/aad

# Make authenticated request (SWA CLI injects X-MS-CLIENT-PRINCIPAL)
curl -b cookies.txt \
     -H "X-Organization-Id: test-org-1" \
     http://localhost:4280/api/workflows/my-workflow
```

**Use when**:
- Testing production authentication flow locally
- Validating user permissions
- Testing org membership checks

## Common Tasks

### Access Organization Configuration

```python
@workflow(name="config-example")
async def use_config(context: OrganizationContext):
    # Get org-specific config (falls back to global)
    api_key = context.get_config('external_api_key')

    # Check if config exists
    if context.has_config('optional_setting'):
        setting = context.get_config('optional_setting')

    # Get with default
    timeout = context.get_config('api_timeout', default=30)
```

### Access Secrets (Planned)

```python
@workflow(name="secret-example")
async def use_secrets(context: OrganizationContext):
    # Get secret from Key Vault (scoped to org)
    api_secret = await context.get_secret('msgraph_client_secret')
```

### Log Workflow Events

```python
@workflow(name="logging-example")
async def use_logging(context: OrganizationContext):
    # Log info message
    context.log('info', "Processing started")

    # Log warning with data
    context.log('warning', "Retrying operation", {
        'attempt': 2,
        'max_retries': 3
    })

    # Log error
    context.log('error', "Operation failed", {
        'error_code': 'TIMEOUT',
        'duration_ms': 5000
    })

    # Logs appear in:
    # - Application Insights
    # - Execution record (WorkflowExecutions table)
```

### Save State Checkpoints

```python
@workflow(name="checkpoint-example")
async def use_checkpoints(context: OrganizationContext, items: list):
    for i, item in enumerate(items):
        # Save checkpoint before processing each item
        context.save_checkpoint(f"item_{i}", {
            'item_id': item['id'],
            'processed': i,
            'total': len(items)
        })

        # Process item...

    # Checkpoints saved in execution record for debugging
```

### Handle Errors

```python
from shared.error_handling import ValidationError, WorkflowException

@workflow(name="error-handling")
async def handle_errors(context: OrganizationContext, email: str):
    # Validate input
    if not '@' in email:
        raise ValidationError(
            message="Invalid email format",
            details={'email': email, 'expected_format': 'user@domain.com'}
        )

    try:
        # Call external API
        result = await call_external_api()
    except aiohttp.ClientError as e:
        # Wrap in WorkflowException for better logging
        raise WorkflowException(
            message=f"External API failed: {str(e)}",
            error_type="IntegrationError",
            details={'api': 'external-service', 'status': 'timeout'}
        )
```

## Testing Your Workflow

### Unit Test (Optional)

```python
# tests/unit/test_my_workflow.py
import pytest
from workspace.workflows.send_welcome_email import send_welcome_email
from shared.context import OrganizationContext, Organization, Caller

@pytest.mark.asyncio
async def test_send_welcome_email():
    # Create mock context
    org = Organization(
        org_id="test-org",
        name="Test Org",
        tenant_id=None,
        is_active=True
    )
    caller = Caller(
        user_id="test-user",
        email="test@example.com",
        name="Test User"
    )
    context = OrganizationContext(
        org=org,
        config={'smtp_server': 'smtp.test.com'},
        caller=caller,
        execution_id="test-123"
    )

    # Execute workflow
    result = await send_welcome_email(
        context,
        user_email="john@example.com",
        user_name="John Doe"
    )

    # Assert result
    assert result['status'] == 'sent'
    assert result['recipient'] == "john@example.com"
```

### Integration Test

```python
# tests/integration/test_send_welcome_email_integration.py
import pytest
import aiohttp

@pytest.mark.asyncio
async def test_send_welcome_email_endpoint():
    # Start Functions runtime (in test fixture)

    async with aiohttp.ClientSession() as session:
        response = await session.post(
            'http://localhost:7071/api/workflows/send-welcome-email',
            headers={
                'x-functions-key': 'test-key',
                'X-Organization-Id': 'test-org-1',
                'X-User-Id': 'test@example.com',
                'Content-Type': 'application/json'
            },
            json={
                'user_email': 'john@example.com',
                'user_name': 'John Doe'
            }
        )

        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'Success'
        assert 'executionId' in data
```

### Run Tests

```bash
# Run all tests
pytest tests/

# Run only integration tests
pytest tests/integration/

# Run with verbose output
pytest -v tests/

# Run with coverage
pytest --cov=workspace tests/
```

## Committing Your Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/send-welcome-email
```

### 2. Add Your Workspace Code

```bash
# Only add workspace files
git add workspace/workflows/send_welcome_email.py
git add tests/integration/test_send_welcome_email_integration.py

# ⚠️ DO NOT add engine files
# GitHub Action will block if you try!
```

### 3. Commit and Push

```bash
git commit -m "feat: add send welcome email workflow"
git push origin feature/send-welcome-email
```

### 4. Create Pull Request

```bash
# Create PR
gh pr create --title "Add send welcome email workflow" \
             --body "Implements welcome email workflow for user onboarding"

# GitHub Action will validate:
# ✅ No changes to /engine/*
# ✅ All tests pass
# ✅ Linting passes
```

## Troubleshooting

### Problem: ImportError when importing engine module

**Error**:
```
ImportError: Workspace code cannot import engine module 'engine.shared.storage'
```

**Solution**: You're trying to import internal engine code. Use the public API instead:

```python
# ❌ Don't do this
from engine.shared.storage import get_table_storage_service

# ✅ Do this instead
# Access storage through context object
@workflow(name="example")
async def my_workflow(context: OrganizationContext):
    # Context provides safe access to org data
    config = context.get_config('my_key')
```

### Problem: GitHub Action blocks my commit

**Error**:
```
::error::Modifications to /engine/* are not allowed from developer commits
```

**Solution**: You accidentally modified engine code. Revert those changes:

```bash
# Check what you changed
git status

# Revert engine changes
git checkout engine/shared/storage.py

# Or reset entire engine directory
git checkout -- engine/
```

### Problem: 403 Forbidden when calling workflow

**Error**:
```
{"error": "Unauthorized", "message": "Authentication required"}
```

**Solution**: Provide authentication:

```bash
# Add function key header
curl -H "x-functions-key: dev-key" ...

# Or use SWA CLI for user auth
swa start
# Login at http://localhost:4280/.auth/login/aad
```

### Problem: Organization not found

**Error**:
```
{"error": "NotFound", "message": "Organization test-org-1 not found"}
```

**Solution**: Seed Azurite with test data:

```bash
# Re-run seed script
python scripts/seed_azurite.py

# Verify organizations created
# (Inspect Azurite with Azure Storage Explorer)
```

### Problem: Workflow not discovered

**Symptom**: Workflow doesn't appear in `func start` output

**Solutions**:
1. Ensure `@workflow` decorator is present
2. Restart Functions runtime
3. Check file is in `workspace/workflows/` directory
4. Check for syntax errors (`python -m py_compile workspace/workflows/my_workflow.py`)

## Next Steps

- **Read the spec**: [spec.md](./spec.md) - Full feature specification
- **Explore contracts**: [contracts/README.md](./contracts/README.md) - API contracts
- **See data model**: [data-model.md](./data-model.md) - Data entities
- **Check research**: [research.md](./research.md) - Technical decisions

## Getting Help

- **Documentation**: `/docs/` directory in repository
- **Code examples**: See existing workflows in `workspace/workflows/`
- **Issues**: Create GitHub issue with `question` label
- **Team**: Ping #workflows channel in Slack

## Summary

You now know how to:
- ✅ Set up local development environment
- ✅ Create custom workflows in `/workspace`
- ✅ Use allowed imports (avoid blocked ones)
- ✅ Test workflows locally with function keys
- ✅ Commit and push without triggering GitHub Action errors
- ✅ Debug and troubleshoot common issues

Happy workflow building! 🚀
