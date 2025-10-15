# Local Development Setup (T059)

Complete guide for setting up and testing workflows locally using Azurite and Azure Functions Core Tools.

## Table of Contents

-   [Prerequisites](#prerequisites)
-   [Quick Start](#quick-start)
-   [Detailed Setup](#detailed-setup)
-   [Authentication](#authentication)
-   [Testing Workflows](#testing-workflows)
-   [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you begin, ensure you have the following installed:

### Required Tools

1. **Python 3.11+**

    ```bash
    python --version  # Should be 3.11 or higher
    ```

2. **Azure Functions Core Tools v4**

    ```bash
    func --version  # Should be 4.x
    ```

    Install: https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local

3. **Azurite** (Azure Storage Emulator)

    ```bash
    npm install -g azurite
    ```

    Or use Docker:

    ```bash
    docker run -p 10000:10000 -p 10001:10001 -p 10002:10002 \
        mcr.microsoft.com/azure-storage/azurite
    ```

### Python Dependencies

Install from requirements.txt:

```bash
pip install -r requirements.txt
```

Required packages:

-   `azure-functions` - Azure Functions runtime
-   `azure-data-tables` - Table Storage SDK
-   `pydantic` - Data validation
-   `pytest`, `pytest-asyncio` - Testing

---

## Quick Start

For the fastest path to a working local environment:

```bash
# 0. Authenticate to Azure (if using Key Vault secrets)
python scripts/authenticate_azure.py

# 1. Start Azurite (in a separate terminal)
azurite --silent --location /tmp/azurite

# 2. Seed test data
python scripts/seed_azurite.py

# 3. Start Azure Functions (in a separate terminal)
func start

# 4. Test health endpoint
curl http://localhost:7071/api/health

# 5. Execute a workflow (using Easy Auth header)
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org-active" \
  -d '{"param": "value"}' \
  http://localhost:7071/api/workflows/YOUR_WORKFLOW_NAME
```

**Execution time target**: ~5 seconds from seed to ready (plus one-time Azure auth)

---

## Detailed Setup

### Step 0: Authenticate to Azure (For Key Vault Secrets)

**⚠️ Important**: If your workflows use `context.get_config()` with secret references (type: `secret_ref`), you MUST authenticate to Azure BEFORE starting your development environment.

This step is required for workflows that access secrets from Azure Key Vault.

```bash
python scripts/authenticate_azure.py
```

**What this script does:**

1. Auto-detects your Key Vault URL from `local.settings.json` or prompts you to enter it
2. Authenticates you to Azure interactively (may open browser)
3. Tests your Key Vault permissions (list, get)
4. Caches credentials for subsequent use

**Output example:**

```
✓ Found Key Vault URL in local.settings.json: https://my-vault.vault.azure.net/
✓ Azure credential created successfully
✓ Successfully listed secrets
  Found 3 secret(s) in Key Vault
✅ Azure Authentication Complete
```

**When to run:**

-   First time setup
-   When your Azure CLI credentials expire
-   When switching Azure accounts
-   Before starting development if using secrets

**When to skip:**

-   Your workflows don't use secrets
-   You're using environment variable fallback (see Key Vault quickstart)

**Configuration:**
Add Key Vault URL to `local.settings.json`:

```json
{
    "Values": {
        "AZURE_KEY_VAULT_URL": "https://your-vault.vault.azure.net/"
    }
}
```

See: `specs/003-use-azure-key/quickstart.md` for detailed Key Vault setup

---

### Step 1: Start Azurite

Azurite emulates Azure Table Storage locally.

**Option A: npm/CLI** (Recommended)

```bash
azurite --silent --location /tmp/azurite --debug /tmp/azurite/debug.log
```

**Option B: Docker**

```bash
docker run -d -p 10002:10002 \
  -v /tmp/azurite:/data \
  mcr.microsoft.com/azure-storage/azurite \
  azurite-table --tableHost 0.0.0.0
```

Verify Azurite is running:

```bash
curl http://127.0.0.1:10002/devstoreaccount1
```

**Connection String** (automatically used by seed script):

```
DefaultEndpointsProtocol=http;
AccountName=devstoreaccount1;
AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;
TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;
```

### Step 2: Seed Test Data

The seed script populates Azurite with test organizations, users, and configuration.

```bash
python scripts/seed_azurite.py
```

**What gets seeded:**

**Organizations** (3 test orgs):

-   `test-org-active` - Active test organization
-   `test-org-demo` - Demo organization (active)
-   `test-org-inactive` - Inactive test organization

**Users** (5 test users):

-   `admin@platform.local` - PlatformAdmin
-   `user1@testorg.local` - OrgUser (test-org-active)
-   `user2@testorg.local` - OrgUser (test-org-active)
-   `admin@demo.local` - OrgAdmin (test-org-demo)
-   `user@inactive.local` - OrgUser (test-org-inactive)

**Configuration** (10+ entries):

-   Global config: platform settings, feature flags
-   Org-specific config: API endpoints, integrations, rate limits

**Features:**

-   ✓ Idempotent (can run multiple times safely)
-   ✓ <5s execution time
-   ✓ Clear console output with status

### Step 3: Configure Environment

Ensure `local.settings.json` exists with Azurite connection:

```json
{
    "IsEncrypted": false,
    "Values": {
        "AzureWebJobsStorage": "UseDevelopmentStorage=true",
        "FUNCTIONS_WORKER_RUNTIME": "python",
        "AzureWebJobsStorage": "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
    }
}
```

### Step 4: Start Azure Functions

Start the Functions host:

```bash
func start
```

You should see:

```
Azure Functions Core Tools
...
Functions:
    execute_workflow: [POST] http://localhost:7071/api/workflows/{workflowName}
    health: [GET] http://localhost:7071/api/health
    ...
```

**Port**: Default is `7071`, but may be `7071` if `7071` is in use.

### Step 5: Verify Setup

Run the automated test script:

```bash
./scripts/test_local_dev.sh
```

This verifies:

-   [x] Azurite is running
-   [x] Seed data populated
-   [x] Azure Functions responding
-   [x] Health endpoint works
-   [x] Authentication functioning

---

## Authentication

### Local Development Authentication

**Note**: For local development, workflows run in an **unauthenticated mode** for testing purposes. The Functions host bypasses Easy Auth locally.

In production, Azure Static Web Apps provides Easy Auth with Azure AD. The `X-MS-CLIENT-PRINCIPAL` header is automatically injected:

```json
{
    "userId": "user-id-from-aad",
    "userDetails": "user@domain.com",
    "identityProvider": "aad",
    "userRoles": ["OrgUser", "OrgAdmin"]
}
```

This header is Base64-encoded by Azure and automatically decoded by the auth service in production.

### Azure Key Vault Authentication

For accessing secrets via `context.get_config()`, you must authenticate to Azure:

```bash
python scripts/authenticate_azure.py
```

This uses `DefaultAzureCredential` which:

-   Uses Azure CLI credentials (`az login`) locally
-   Uses Managed Identity in production
-   Caches credentials for the session

**See Step 0 above for detailed instructions**

---

## Testing Workflows

### Where to Write Code

**⚠️ IMPORTANT**: All workflow code MUST be written in the `/workspace/` directory ONLY. Never modify files in `/engine/` as they contain system infrastructure code.

**Directory Structure**:

```
/workspace/
├── workflows/          # Your workflow implementations
│   ├── my_workflow.py
│   └── another_workflow.py
└── examples/           # Reference examples and templates
    ├── hello_world.py
    └── error_handling.py
```

**Allowed Imports**: Workspace code uses the **bifrost module** for platform functionality:

```python
# ✅ ALLOWED - Public API via bifrost module
from bifrost import workflow, param, data_provider, OrganizationContext
from engine.shared.error_handling import (
    WorkflowException, ValidationError, IntegrationError, TimeoutError
)

# ❌ FORBIDDEN - Internal engine modules
from engine.shared.storage import TableStorageService  # Will be blocked!
from engine.shared.auth import AuthService  # Will be blocked!
```

### Creating a Test Workflow

Create a workflow in `/workspace/workflows/`:

```python
# /workspace/workflows/test_workflow.py
from bifrost import workflow, param, OrganizationContext

@workflow(
    name="test_workflow",
    description="Test workflow for local development",
    category="Testing"
)
@param("message", str, "Message to echo back", required=True)
async def test_workflow(context: OrganizationContext, message: str):
    """Simple test workflow that echoes a message"""
    context.log(f"Received message: {message}")

    return {
        "echo": message,
        "org_id": context.org_id,
        "org_name": context.org_name,
        "caller": context.caller.email
    }
```

### Context and Available Functions

The `context` object provides access to all platform capabilities:

```python
async def my_workflow(context: OrganizationContext, param1: str):
    # === ORGANIZATION INFORMATION ===
    org_id = context.org_id           # Organization ID
    org_name = context.org_name       # Organization display name
    tenant_id = context.tenant_id     # Microsoft 365 tenant ID (if linked)

    # === EXECUTION METADATA ===
    execution_id = context.execution_id
    caller_email = context.executed_by_email
    caller_name = context.executed_by_name

    # === CONFIGURATION (with secret resolution) ===
    # Automatically resolves secret_ref types from Key Vault
    api_url = context.get_config("api_url", "https://default.com")
    api_key = context.get_config("api_key")  # Will fetch from Key Vault if secret_ref
    has_config = context.has_config("optional_setting")

    # === SECRETS (direct Key Vault access) ===
    # Secrets are org-scoped: {org_id}--{secret_name}
    secret_value = await context.get_secret("my_secret")

    # === OAUTH CONNECTIONS ===
    # Get pre-authenticated OAuth credentials
    oauth_creds = await context.get_oauth_connection("HaloPSA")
    headers = {"Authorization": oauth_creds.get_auth_header()}

    # === INTEGRATIONS ===
    # Get pre-authenticated integration clients
    # graph = context.get_integration("msgraph")  # When implemented
    # halo = context.get_integration("halopsa")  # When implemented

    # === STATE TRACKING ===
    context.save_checkpoint("step1", {"progress": "started"})
    context.set_variable("user_count", 42)
    count = context.get_variable("user_count", 0)

    # === LOGGING ===
    context.log("Processing started")  # Simple form (info level)
    context.log("info", "Processing started", data={"param1": param1})  # Explicit level
    context.log("warning", "Non-critical issue detected")
    context.log("error", "Something went wrong", data={"error": "details"})
```

### Installing and Using Modules

**External Dependencies**: Add to `requirements.txt`:

```bash
pip install requests
pip install pandas
```

**Using External Libraries**:

```python
from bifrost import workflow, OrganizationContext
import requests
import pandas as pd

@workflow(name="api_call_workflow")
async def call_external_api(context: OrganizationContext):
    # Use external libraries normally
    response = requests.get("https://api.example.com/data")
    data = response.json()

    # Process with pandas
    df = pd.DataFrame(data)
    return {"count": len(df)}
```

**Local Development Modules**: Create utility modules in `/workspace/`:

```python
# /workspace/utils.py
def format_phone_number(phone: str) -> str:
    """Utility function for formatting phone numbers"""
    return phone.replace("-", " ").strip()

# /workspace/workflows/my_workflow.py
from bifrost import workflow, OrganizationContext
from ..utils import format_phone_number  # Relative import

@workflow(name="format_phone")
async def format_phone(context: OrganizationContext, phone: str):
    formatted = format_phone_number(phone)
    return {"formatted_phone": formatted}
```

### Testing and Breakpoint Debugging

**1. Run Azure Functions in Debug Mode**:

```bash
# Start with debugging enabled
func start --debug
```

**2. Set Breakpoints in Your Code**:

```python
# /workspace/workflows/debug_workflow.py
from bifrost import workflow, OrganizationContext
import pdb  # Python debugger

@workflow(name="debug_workflow")
async def debug_workflow(context: OrganizationContext, data: str):
    context.log("Starting debug workflow")

    # Set breakpoint - execution will pause here
    pdb.set_trace()

    # You can inspect variables here
    result = process_data(data)  # Step into this function

    context.log("Processed data", {"result": result})
    return {"result": result}
```

**3. VS Code Debugging Setup**:
Create `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Azure Functions",
            "type": "python",
            "request": "attach",
            "port": 9091,
            "host": "localhost",
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "."
                }
            ]
        }
    ]
}
```

**4. Debug Workflow Execution**:

```bash
# Terminal 1: Start Functions with debug
func start --debug --port 9091

# Terminal 2: Execute workflow
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org-active" \
  -d '{"data": "test"}' \
  http://localhost:7071/api/workflows/debug_workflow
```

**5. Common Debugging Commands**:

```python
# In pdb console (when breakpoint hits):
p context.org_id          # Print organization ID
p data                    # Print variable value
l                        # List code around current line
n                        # Next line
s                        # Step into function
c                        # Continue execution
```

### Azure Key Vault Local Development

**Interactive Authentication**:

```bash
# Authenticate to Azure for Key Vault access
python scripts/authenticate_azure.py
```

**Specifying Your Key Vault**:
Add to `local.settings.json`:

```json
{
    "Values": {
        "AZURE_KEY_VAULT_URL": "https://your-key-vault-name.vault.azure.net/"
    }
}
```

**Creating/Updating Secrets**:

```bash
# Create secret in Azure CLI
az keyvault secret set --vault-name your-vault-name \
  --name "GLOBAL--shared-api-key" \
  --value "your-secret-value"

# Create org-specific secret
az keyvault secret set --vault-name your-vault-name \
  --name "org-123--client-secret" \
  --value "org-specific-secret"
```

**Remembering to Update in Both Places**:

1. **Azure Key Vault** (persistent storage):

    ```bash
    az keyvault secret set --vault-name your-vault \
      --name "GLOBAL--my-secret" --value "new-value"
    ```

2. **Local Configuration** (for development):
    ```python
    # In your workflow, use context.get_config() with secret_ref
    api_key = context.get_config("my_api_key")  # Automatically resolves from Key Vault
    ```

**Secret Naming Convention**:

-   Global secrets: `GLOBAL--{secret-name}`
-   Org-specific secrets: `{org-id}--{secret-name}`

**Testing Secret Access**:

```python
from bifrost import workflow, OrganizationContext

@workflow(name="test_secrets")
async def test_secrets(context: OrganizationContext):
    try:
        # Test global secret
        global_secret = await context.get_secret("shared_api_key")
        context.log("Got global secret", {"length": len(global_secret)})

        # Test org-specific secret
        org_secret = await context.get_secret("client_secret")
        context.log("Got org secret", {"length": len(org_secret)})

        return {"success": True}
    except Exception as e:
        context.log("error", "Secret access failed", {"error": str(e)})
        return {"success": False, "error": str(e)}
```

**Key Vault Permissions**:

```bash
# Grant yourself Key Vault access
az keyvault set-policy --name your-vault-name \
  --upn your-email@domain.com \
  --secret-permissions get list set delete
```

### Executing the Workflow

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org-active" \
  -d '{"message": "Hello, World!"}' \
  http://localhost:7071/api/workflows/test_workflow
```

**Expected Response:**

```json
{
    "executionId": "uuid-here",
    "status": "Success",
    "result": {
        "echo": "Hello, World!",
        "org_id": "test-org-active",
        "org_name": "Active Test Organization",
        "caller": "local-dev@system.local"
    },
    "durationMs": 123,
    "startedAt": "2025-01-15T10:30:00Z",
    "completedAt": "2025-01-15T10:30:00Z"
}
```

### Testing with Different Organizations

```bash
# Active org (should succeed)
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org-active" \
  -d '{"message": "test"}' \
  http://localhost:7071/api/workflows/test_workflow

# Inactive org (should fail with 404)
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org-inactive" \
  -d '{"message": "test"}' \
  http://localhost:7071/api/workflows/test_workflow
```

### Viewing Execution Logs

Logs are written to `AuditLog` table in Azurite. Use Azure Storage Explorer or query programmatically:

```python
from azure.data.tables import TableServiceClient

connection_string = "..."  # Azurite connection string
client = TableServiceClient.from_connection_string(connection_string)
table = client.get_table_client("AuditLog")

# Query today's audit events
from datetime import datetime
today = datetime.now().strftime("%Y-%m-%d")
events = table.query_entities(f"PartitionKey eq '{today}'")

for event in events:
    print(f"{event['EventType']}: {event.get('Details', '')}")
```

---

## Troubleshooting

### Azurite not starting

**Error:** `EADDRINUSE: address already in use`

**Solution:** Kill existing Azurite process

```bash
lsof -i :10002  # Find process using port 10002
kill -9 <PID>
```

### Seed script fails

**Error:** `Failed to create table client`

**Solution:** Verify Azurite is running

```bash
curl http://127.0.0.1:10002/devstoreaccount1
```

### Azure Functions not starting

**Error:** `No job functions found`

**Solution:** Ensure you're in the correct directory

```bash
cd /path/to/bifrost-integrations/workflows
func start
```

**Error:** `Worker was unable to load function`

**Solution:** Check Python version and dependencies

```bash
python --version  # Must be 3.11+
pip install -r requirements.txt
```

### Key Vault authentication fails

**Error:** `Failed to create Azure credential` or `Permission denied (403)`

**Solution:** Authenticate to Azure

```bash
python scripts/authenticate_azure.py
```

If already authenticated but getting 403:

```bash
# Grant yourself Key Vault permissions
az keyvault set-policy --name <vault-name> \
  --upn <your-email> \
  --secret-permissions get list
```

### Workflow not found (404)

**Error:** `Workflow 'my_workflow' not found`

**Solution:** Verify workflow is decorated and imported

1. Check workflow file has `@workflow` decorator
2. Ensure file is in `/workspace/workflows/`
3. Check `function_app.py` imports `workspace.workflows`
4. Restart Azure Functions to trigger discovery

### Import errors in workspace code

**Error:** `Workspace code cannot import engine module`

**Solution:** Use bifrost module for public API

```python
# ✗ WRONG - Blocks internal imports
from engine.shared.storage import get_organization

# ✓ CORRECT - Use bifrost module
from bifrost import workflow, param, OrganizationContext
from engine.shared.error_handling import WorkflowException
```

Allowed imports for workspace code:

-   `bifrost` - All public platform functionality (workflow, param, OrganizationContext, etc.)
-   `engine.shared.error_handling` - WorkflowException, ValidationError, IntegrationError, TimeoutError

### Port conflicts

**Error:** Azure Functions starts on different port

**Solution:** Check actual port in startup output

```
Now listening on: http://0.0.0.0:7071  # Note: Port 7071, not 7071
```

Update curl commands to use the correct port.

---

## Additional Resources

-   **Workspace API Documentation**: `/docs/workspace-api.md`
-   **Migration Guide**: `/docs/migration-guide.md`
-   **GitHub Actions Protection**: `/.github/workflows/protect-engine.yml`
-   **Seed Script Source**: `/scripts/seed_azurite.py`
-   **Test Script Source**: `/scripts/test_local_dev.sh`

---

## Summary Checklist

Before starting development, ensure:

-   [ ] Azure authenticated (if using secrets): `python scripts/authenticate_azure.py`
-   [ ] Azurite is running on port 10002
-   [ ] Seed script has populated test data
-   [ ] Azure Functions is running and showing endpoints
-   [ ] Health endpoint responds: `curl http://localhost:7071/api/health`
-   [ ] Test workflow executes successfully

**Ready to develop!** 🚀

Create workflows in `/workspace/workflows/` and test immediately.
