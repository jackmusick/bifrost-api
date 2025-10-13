# Developer Quickstart Guide

**Feature**: Bifrost Integrations MVP
**Last Updated**: 2025-10-10
**Target Audience**: Python/React developers onboarding to the platform

## Overview

This guide will get you up and running with local development for the Bifrost Integrations in under 30 minutes. You'll learn how to:

-   Set up local Azure storage emulation with Azurite
-   Run the Management API and Workflow Engine locally
-   Create your first workflow with decorators
-   Create data providers for dynamic form fields
-   Debug workflows with native Python tooling (VSCode/PyCharm)
-   Test the React frontend against local backends

## Prerequisites

Before starting, ensure you have:

-   **Python 3.11** installed (required for Azure Functions v2)
-   **Node.js 18+** and npm/yarn
-   **Azure Functions Core Tools v4** (`npm install -g azure-functions-core-tools@4`)
-   **Azurite** for local Azure Storage emulation (`npm install -g azurite`)
-   **Git** for cloning repositories
-   **VSCode** or **PyCharm** (recommended for debugging)
-   **Azure CLI** (optional - for deployment only)

## Quick Start (5 Minutes)

### 1. Start Azurite (Local Azure Storage)

Open a terminal and start Azurite:

```bash
azurite --silent --location ~/azurite --debug ~/azurite/debug.log
```

Azurite will start with:

-   **Blob Storage**: `http://127.0.0.1:10000`
-   **Queue Storage**: `http://127.0.0.1:10001`
-   **Table Storage**: `http://127.0.0.1:10002`

Leave this running in the background.

### 2. Clone and Set Up Management API

```bash
# Clone the Management API repository
git clone https://github.com/your-org/msp-automation-api.git
cd msp-automation-api

# Create Python virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy local settings template
cp local.settings.json.example local.settings.json

# Start the Management API
func start --port 7071
```

The Management API will start on `http://localhost:7071`.

### 3. Clone and Set Up Workflow Engine

Open a **new terminal**:

```bash
# Clone the Workflow Engine repository
git clone https://github.com/your-org/msp-automation-workflows.git
cd msp-automation-workflows

# Create Python virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy local settings template
cp local.settings.json.example local.settings.json

# Start the Workflow Engine
func start --port 7072
```

The Workflow Engine will start on `http://localhost:7072`.

### 4. Clone and Set Up React Client

Open a **new terminal**:

```bash
# Clone the client repository
git clone https://github.com/your-org/msp-automation-platform.git
cd msp-automation-platform/client

# Install dependencies
npm install

# Copy environment template
cp .env.local.example .env.local

# Start the React dev server
npm start
```

The React app will start on `http://localhost:3000`.

### 5. Verify Everything Works

1. Open `http://localhost:3000` in your browser
2. You should see the login screen (Azure AD auth will be mocked in local development)
3. Check terminal outputs - all three services should be running without errors

🎉 **You're ready to develop!**

## Creating Your First Workflow

Workflows are Python functions decorated with `@workflow` that automatically register with the platform.

### Example: User Onboarding Workflow

Create a new file: `workflow-engine/workflows/user_onboarding.py`

```python
from shared.decorators import workflow, param
from shared.context import OrganizationContext

@workflow(
    name="user_onboarding",
    description="Onboard new M365 user with license assignment",
    category="user_management",
    tags=["m365", "user"]
)
@param("first_name", type="string", label="First Name", required=True)
@param("last_name", type="string", label="Last Name", required=True)
@param("email", type="email", label="Email Address", required=True,
       validation={"pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"})
@param("license", type="string", label="License Type", required=True,
       data_provider="get_available_licenses")
async def onboard_user(
    context: OrganizationContext,
    first_name: str,
    last_name: str,
    email: str,
    license: str
):
    """
    Onboard a new Microsoft 365 user with the specified license.

    This workflow:
    1. Creates the user in Azure AD via Microsoft Graph
    2. Assigns the specified license
    3. Sends welcome email
    4. Returns user details
    """

    # Get pre-authenticated Microsoft Graph client from context
    graph = context.get_integration('msgraph')

    # Create the user
    user_data = {
        "accountEnabled": True,
        "displayName": f"{first_name} {last_name}",
        "mailNickname": email.split('@')[0],
        "userPrincipalName": email,
        "passwordProfile": {
            "forceChangePasswordNextSignIn": True,
            "password": context.generate_password()  # Helper method
        }
    }

    try:
        user = await graph.users.create(user_data)

        # Assign license
        await graph.users[user.id].assign_license(
            add_licenses=[{"skuId": license}],
            remove_licenses=[]
        )

        return {
            "success": True,
            "userId": user.id,
            "upn": user.userPrincipalName,
            "message": f"User {first_name} {last_name} created successfully"
        }

    except Exception as e:
        # Workflow exceptions are automatically logged to WorkflowExecutions table
        raise WorkflowException(f"Failed to create user: {str(e)}")
```

### Workflow Auto-Discovery

The workflow is automatically discovered when the Workflow Engine starts! No manual registration needed.

**How it works**:

1. The `function_app.py` imports all modules from `workflows/` directory
2. The `@workflow` decorator registers the function in the metadata registry
3. The `/admin/metadata` endpoint exposes the workflow definition
4. The Management UI fetches metadata to build dynamic forms

### Testing Your Workflow

**Option 1: REST API (cURL)**

```bash
curl -X POST http://localhost:7072/workflows/user_onboarding \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: your-test-org-id" \
  -d '{
    "parameters": {
      "first_name": "John",
      "last_name": "Doe",
      "email": "john.doe@example.com",
      "license": "SPE_E5"
    }
  }'
```

**Option 2: React UI**

1. Navigate to Forms page
2. Click "Create Form"
3. Select "user_onboarding" workflow
4. The form fields are auto-generated from `@param` decorators!
5. Fill out and submit

**Option 3: Python Test (Recommended)**

Create `tests/integration/test_user_onboarding.py`:

```python
import pytest
from workflows.user_onboarding import onboard_user
from shared.context import OrganizationContext
from tests.fixtures import mock_context

@pytest.mark.asyncio
async def test_onboard_user_success(mock_context):
    """Test successful user onboarding"""
    result = await onboard_user(
        context=mock_context,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        license="SPE_E5"
    )

    assert result["success"] is True
    assert "userId" in result
    assert result["upn"] == "john.doe@example.com"
```

Run tests with:

```bash
pytest tests/integration/test_user_onboarding.py -v
```

## Creating Data Providers

Data providers supply dynamic options for form fields (similar to Rewst's option generators).

### Example: Available Licenses Data Provider

Create `workflow-engine/data_providers/get_available_licenses.py`:

```python
from shared.decorators import data_provider
from shared.context import OrganizationContext

@data_provider(
    name="get_available_licenses",
    description="Returns available M365 licenses for the organization",
    category="m365",
    cache_ttl_seconds=300  # Cache for 5 minutes
)
async def get_available_licenses(context: OrganizationContext):
    """
    Fetches available Microsoft 365 licenses from Graph API.

    Returns only licenses where consumedUnits < prepaidUnits (licenses available).
    """

    graph = context.get_integration('msgraph')

    # Get all subscribed SKUs for the tenant
    skus = await graph.subscribed_skus.get()

    # Filter to available licenses only
    options = []
    for sku in skus.value:
        available = sku.prepaid_units.enabled - sku.consumed_units

        if available > 0:
            options.append({
                "label": f"{sku.sku_part_number} ({available} available)",
                "value": sku.sku_id,
                "metadata": {
                    "skuPartNumber": sku.sku_part_number,
                    "available": available,
                    "total": sku.prepaid_units.enabled
                }
            })

    return options
```

### Data Provider Auto-Discovery

Like workflows, data providers are automatically discovered and exposed via `/admin/metadata`.

### Using Data Providers in Workflows

Reference a data provider in your `@param` decorator:

```python
@param("license", type="string", label="License Type",
       required=True, data_provider="get_available_licenses")
```

When the form is rendered, the UI will:

1. Call `GET /data-providers/get_available_licenses`
2. Populate the dropdown with returned options
3. Cache the response for 5 minutes (per `cache_ttl_seconds`)

## Debugging Workflows (Native Python Tooling)

One of the platform's key features is **code-first debugging** - you can use VSCode, PyCharm, or any Python debugger.

### VSCode Debug Configuration

Add to `.vscode/launch.json` in the Workflow Engine repo:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Attach to Python Functions",
            "type": "python",
            "request": "attach",
            "port": 9091,
            "preLaunchTask": "func: host start"
        },
        {
            "name": "Debug Workflow (Pytest)",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": [
                "tests/integration/test_user_onboarding.py::test_onboard_user_success",
                "-v",
                "-s"
            ],
            "console": "integratedTerminal",
            "justMyCode": false
        }
    ]
}
```

### Debugging Steps

1. **Set Breakpoints**: Click in the gutter next to any line in your workflow
2. **Start Debugging**: Press F5 or select "Debug Workflow (Pytest)"
3. **Step Through Code**: Use F10 (step over), F11 (step into), F5 (continue)
4. **Inspect Variables**: Hover over variables or use the Variables pane
5. **Evaluate Expressions**: Use the Debug Console

### PyCharm Debug Configuration

1. **Run > Edit Configurations**
2. **Add New Configuration > Python**
3. **Script path**: Select pytest executable from `.venv/bin/pytest`
4. **Parameters**: `tests/integration/test_user_onboarding.py -v`
5. **Working directory**: Select workflow-engine root
6. **Python interpreter**: Select `.venv/bin/python3.11`

## Understanding Organization Context

The `OrganizationContext` object is automatically injected into every workflow and data provider.

### What's in the Context?

```python
class OrganizationContext:
    org_id: str                    # Organization UUID
    org_name: str                  # Organization name
    tenant_id: str | None          # Microsoft 365 tenant ID (GDAP)

    def get_config(self, key: str) -> Any:
        """Get organization configuration value"""

    def get_secret(self, key: str) -> str:
        """Get organization secret from Key Vault"""

    def get_integration(self, name: str) -> BaseIntegration:
        """Get pre-authenticated integration client"""

    def generate_password(self) -> str:
        """Generate secure random password"""

    async def log(self, level: str, message: str, data: dict = None):
        """Write to execution log (stored in Blob Storage)"""
```

### Using Configuration

Organization-specific config is stored in the `OrgConfig` table:

```python
async def my_workflow(context: OrganizationContext):
    # Get config value (automatically scoped to this organization)
    default_location = context.get_config("default_office_location")

    # Get secret (fetched from Azure Key Vault)
    api_key = context.get_secret("halopsa_api_key")
```

### Pre-Authenticated Integrations

The platform provides pre-authenticated clients for common integrations:

```python
async def my_workflow(context: OrganizationContext):
    # Microsoft Graph (uses org's GDAP credentials)
    graph = context.get_integration('msgraph')
    users = await graph.users.get()

    # HaloPSA (uses org's API key from Key Vault)
    halo = context.get_integration('halopsa')
    tickets = await halo.get_tickets(status="open")
```

**Available Integrations**:

-   `msgraph`: Microsoft Graph API (M365, Azure AD)
-   `halopsa`: HaloPSA ticketing system
-   `datto`: Datto RMM/PSA
-   Custom integrations can be added in `shared/integrations/`

## Project Structure Navigation

### Workflow Engine Structure

```
workflow-engine/
├── workflows/              # Your workflow functions go here
│   ├── user_onboarding.py
│   └── __init__.py         # Auto-discovery imports
│
├── data_providers/         # Your data provider functions go here
│   ├── get_available_licenses.py
│   └── __init__.py         # Auto-discovery imports
│
├── shared/                 # Shared utilities
│   ├── decorators.py       # @workflow, @data_provider, @param
│   ├── context.py          # OrganizationContext class
│   ├── registry.py         # Metadata registry
│   ├── storage.py          # Table Storage helpers
│   ├── integrations/       # Pre-authenticated clients
│   │   ├── msgraph.py
│   │   ├── halopsa.py
│   │   └── base.py
│   └── error_handling.py
│
├── admin/                  # Admin endpoints
│   └── metadata.py         # GET /admin/metadata
│
├── tests/
│   ├── contract/           # API contract tests
│   ├── integration/        # Integration tests
│   └── fixtures.py         # Test fixtures (mock_context, etc.)
│
├── function_app.py         # Entry point
├── requirements.txt
└── host.json
```

### Management API Structure

```
management-api/
├── functions/              # HTTP-triggered endpoints
│   ├── organizations.py    # CRUD for organizations
│   ├── org_config.py       # Org configuration k/v
│   ├── permissions.py      # User permissions
│   ├── forms.py            # Form CRUD
│   └── executions.py       # Execution history
│
├── shared/                 # Shared utilities
│   ├── storage.py          # TableStorageService
│   ├── auth.py             # Token validation
│   ├── models.py           # Pydantic models
│   └── middleware.py       # Decorators
│
├── tests/
│   ├── contract/           # API contract tests
│   └── integration/        # Integration tests
│
└── function_app.py
```

### Client (React) Structure

```
client/
├── src/
│   ├── components/
│   │   ├── common/         # Reusable components
│   │   ├── organizations/  # Org management UI
│   │   ├── forms/          # Form builder & renderer
│   │   ├── workflows/      # Workflow list & execution
│   │   └── executions/     # Execution history
│   │
│   ├── services/
│   │   ├── apiClient.ts    # Management API wrapper
│   │   ├── workflowClient.ts # Workflow Engine wrapper
│   │   └── authService.ts  # Azure AD MSAL
│   │
│   ├── types/              # TypeScript interfaces
│   ├── pages/              # Route components
│   └── hooks/              # Custom React hooks
│
└── tests/
```

## Common Development Workflows

### Adding a New Workflow

1. Create new file in `workflows/` directory
2. Import decorators: `from shared.decorators import workflow, param`
3. Define function with decorators
4. Implement business logic using `context`
5. Add integration test in `tests/integration/`
6. Run tests: `pytest tests/integration/test_my_workflow.py`
7. Restart `func start` to auto-discover
8. Verify in UI: Forms > Create Form > Select your workflow

### Adding a New Data Provider

1. Create new file in `data_providers/` directory
2. Import decorator: `from shared.decorators import data_provider`
3. Return array of `{"label": "...", "value": "..."}` objects
4. Reference in workflow with `@param(..., data_provider="your_provider_name")`
5. Restart `func start` to auto-discover

### Adding a New Integration

1. Create new file in `shared/integrations/` (e.g., `connectwise.py`)
2. Extend `BaseIntegration` class
3. Implement authentication logic
4. Add to context loader in `shared/context.py`
5. Use in workflows: `context.get_integration('connectwise')`

### Debugging Table Storage Queries

Use **Azure Storage Explorer** (GUI) or **Azure Storage Browser** extension for VSCode:

1. Connect to local Azurite endpoint: `http://127.0.0.1:10002`
2. Browse tables: Organizations, UserPermissions, Forms, etc.
3. View entities by PartitionKey (OrgId)
4. Manually insert test data for development

## Environment Variables

### Workflow Engine (`local.settings.json`)

```json
{
    "IsEncrypted": false,
    "Values": {
        "AzureWebJobsStorage": "UseDevelopmentStorage=true",
        "FUNCTIONS_WORKER_RUNTIME": "python",
        "AzureWebJobsStorage": "UseDevelopmentStorage=true",
        "BLOB_STORAGE_CONNECTION_STRING": "UseDevelopmentStorage=true",
        "KEY_VAULT_URL": "https://your-keyvault.vault.azure.net/",
        "AZURE_CLIENT_ID": "your-app-registration-client-id",
        "AZURE_TENANT_ID": "your-tenant-id"
    }
}
```

### Management API (`local.settings.json`)

Same as Workflow Engine - both share the same Azure resources.

### React Client (`.env.local`)

```env
REACT_APP_MANAGEMENT_API_URL=http://localhost:7071
REACT_APP_WORKFLOW_API_URL=http://localhost:7072
REACT_APP_AZURE_CLIENT_ID=your-app-registration-client-id
REACT_APP_AZURE_TENANT_ID=your-tenant-id
REACT_APP_AZURE_REDIRECT_URI=http://localhost:3000
```

## Testing Strategy

### Test Pyramid

```
       /\
      /E2E\          <- Few end-to-end tests (Playwright)
     /------\
    / Integ  \       <- Integration tests (workflows with mocked integrations)
   /----------\
  /  Contract  \     <- API contract tests (request/response validation)
 /--------------\
/     Unit       \   <- Unit tests (decorators, context, helpers)
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=workflows --cov=data_providers --cov=shared

# Run specific test file
pytest tests/integration/test_user_onboarding.py

# Run specific test
pytest tests/integration/test_user_onboarding.py::test_onboard_user_success

# Run with verbose output
pytest -v -s
```

### Contract Testing

Contract tests validate API request/response shapes:

```python
# tests/contract/test_workflow_execution_contract.py
import pytest
from pydantic import ValidationError
from shared.models import WorkflowExecutionRequest, WorkflowExecutionResponse

def test_workflow_execution_request_valid():
    """Valid request passes validation"""
    req = WorkflowExecutionRequest(
        parameters={"first_name": "John", "last_name": "Doe"},
        metadata={"executedBy": "user@example.com"}
    )
    assert req.parameters["first_name"] == "John"

def test_workflow_execution_request_invalid():
    """Invalid request fails validation"""
    with pytest.raises(ValidationError):
        WorkflowExecutionRequest(
            parameters="not-a-dict"  # Should be dict
        )
```

## Troubleshooting

### Azurite Connection Issues

**Problem**: `ConnectionRefusedError: [Errno 61] Connection refused`

**Solution**:

-   Ensure Azurite is running: `ps aux | grep azurite`
-   Check port 10002 is not in use: `lsof -i :10002`
-   Restart Azurite: `pkill azurite && azurite --silent`

### Workflow Not Auto-Discovered

**Problem**: New workflow doesn't appear in `/admin/metadata`

**Solution**:

-   Ensure workflow file is in `workflows/` directory
-   Check `workflows/__init__.py` imports the module
-   Restart Azure Functions: Stop `func start` and restart
-   Check function logs for import errors

### Integration Authentication Fails

**Problem**: `AuthenticationError: Failed to authenticate with Microsoft Graph`

**Solution**:

-   Check `AZURE_CLIENT_ID` and `AZURE_TENANT_ID` in `local.settings.json`
-   Verify Azure AD app registration has correct API permissions
-   Check organization has `tenantId` set in Organizations table
-   Use `az login` to authenticate locally

### Table Storage Schema Errors

**Problem**: `TypeError: Object of type datetime is not JSON serializable`

**Solution**:

-   Use `datetime.isoformat()` when storing dates
-   Use `datetime.fromisoformat()` when reading dates
-   The `TableStorageService` helper handles this automatically

## Next Steps

Now that you're set up:

1. **Explore Example Workflows**: Check `workflows/examples/` for more patterns
2. **Read API Contracts**: See `specs/001-complete-mvp-for/contracts/` for full API specs
3. **Review Data Model**: See `specs/001-complete-mvp-for/data-model.md` for Table Storage schema
4. **Join the Team**: Check `CONTRIBUTING.md` for contribution guidelines
5. **Deploy to Azure**: See `docs/deployment.md` when ready for production

## Resources

-   **Architecture Docs**: `specs/001-complete-mvp-for/plan.md`
-   **API Contracts**: `specs/001-complete-mvp-for/contracts/`
-   **Data Model**: `specs/001-complete-mvp-for/data-model.md`
-   **Constitution**: `.specify/memory/constitution.md`
-   **Azure Functions Docs**: https://learn.microsoft.com/en-us/azure/azure-functions/
-   **Azure Table Storage Docs**: https://learn.microsoft.com/en-us/azure/storage/tables/
-   **Microsoft Graph API**: https://learn.microsoft.com/en-us/graph/

## Getting Help

-   **GitHub Issues**: https://github.com/your-org/msp-automation-platform/issues
-   **Team Chat**: Slack #msp-automation-dev
-   **Documentation**: `docs/` directory in each repository

---

**Welcome to the team! Happy coding! 🚀**
