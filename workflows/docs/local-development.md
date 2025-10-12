# Local Development Setup (T059)

Complete guide for setting up and testing workflows locally using Azurite and Azure Functions Core Tools.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Authentication](#authentication)
- [Testing Workflows](#testing-workflows)
- [Troubleshooting](#troubleshooting)

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
- `azure-functions` - Azure Functions runtime
- `azure-data-tables` - Table Storage SDK
- `pydantic` - Data validation
- `pytest`, `pytest-asyncio` - Testing

---

## Quick Start

For the fastest path to a working local environment:

```bash
# 1. Start Azurite (in a separate terminal)
azurite --silent --location /tmp/azurite

# 2. Seed test data
python scripts/seed_azurite.py

# 3. Start Azure Functions (in a separate terminal)
func start

# 4. Test health endpoint
curl http://localhost:7072/api/health

# 5. Execute a workflow
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org-active" \
  -H "x-functions-key: test_local_key_12345" \
  -d '{"param": "value"}' \
  http://localhost:7072/api/workflows/YOUR_WORKFLOW_NAME
```

**Execution time target**: ~5 seconds from seed to ready

---

## Detailed Setup

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
- `test-org-active` - Active test organization
- `test-org-demo` - Demo organization (active)
- `test-org-inactive` - Inactive test organization

**Users** (5 test users):
- `admin@platform.local` - PlatformAdmin
- `user1@testorg.local` - OrgUser (test-org-active)
- `user2@testorg.local` - OrgUser (test-org-active)
- `admin@demo.local` - OrgAdmin (test-org-demo)
- `user@inactive.local` - OrgUser (test-org-inactive)

**Configuration** (10+ entries):
- Global config: platform settings, feature flags
- Org-specific config: API endpoints, integrations, rate limits

**Features:**
- ✓ Idempotent (can run multiple times safely)
- ✓ <5s execution time
- ✓ Clear console output with status

### Step 3: Configure Environment

Ensure `local.settings.json` exists with Azurite connection:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "TABLE_STORAGE_CONNECTION_STRING": "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
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
    execute_workflow: [POST] http://localhost:7072/api/workflows/{workflowName}
    health: [GET] http://localhost:7072/api/health
    ...
```

**Port**: Default is `7071`, but may be `7072` if `7071` is in use.

### Step 5: Verify Setup

Run the automated test script:

```bash
./scripts/test_local_dev.sh
```

This verifies:
- [x] Azurite is running
- [x] Seed data populated
- [x] Azure Functions responding
- [x] Health endpoint works
- [x] Authentication functioning

---

## Authentication

The workflow engine supports **tiered authentication** with the following priority order:

### 1. Function Key (Highest Priority)

Provides privileged access without user context. Ideal for local development and system integrations.

**Via Header:**
```bash
curl -H "x-functions-key: your_key_here" ...
```

**Via Query Parameter:**
```bash
curl "http://localhost:7072/api/workflows/test?code=your_key_here"
```

**Security:**
- All function key usage is audited to `AuditLog` table
- Bypasses user authentication but still validates organization

**Local Development Example:**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org-active" \
  -H "x-functions-key: test_local_key_12345" \
  -d '{"test": "data"}' \
  http://localhost:7072/api/workflows/YOUR_WORKFLOW
```

### 2. Easy Auth (Fallback)

Used in production when deployed to Azure with Easy Auth enabled.

Azure injects `X-MS-CLIENT-PRINCIPAL` header containing:
```json
{
  "userId": "user-id-from-aad",
  "userDetails": "user@domain.com",
  "identityProvider": "aad",
  "userRoles": ["OrgUser", "OrgAdmin"]
}
```

This header is Base64-encoded by Azure and automatically decoded by the auth service.

### 3. No Authentication → 403 Forbidden

If neither function key nor Easy Auth is present, requests are rejected with:

```json
{
  "error": "Forbidden",
  "message": "No valid authentication credentials provided..."
}
```

### Authentication Flow Diagram

```
Request arrives
    ↓
Check x-functions-key header
    ↓ (not found)
Check ?code=KEY query param
    ↓ (not found)
Check X-MS-CLIENT-PRINCIPAL header
    ↓ (not found)
Return 403 Forbidden
```

---

## Testing Workflows

### Creating a Test Workflow

Create a workflow in `/workspace/workflows/`:

```python
# /workspace/workflows/test_workflow.py
from engine.shared.decorators import workflow, param
from engine.shared.context import OrganizationContext

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

### Executing the Workflow

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org-active" \
  -H "x-functions-key: test_local_key_12345" \
  -d '{"message": "Hello, World!"}' \
  http://localhost:7072/api/workflows/test_workflow
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
    "caller": "function-key@system.local"
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
  -H "X-Organization-Id: test-org-active" \
  -H "x-functions-key: key123" \
  -d '{"message": "test"}' \
  http://localhost:7072/api/workflows/test_workflow

# Inactive org (should fail with 404)
curl -X POST \
  -H "X-Organization-Id: test-org-inactive" \
  -H "x-functions-key: key123" \
  -d '{"message": "test"}' \
  http://localhost:7072/api/workflows/test_workflow
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

### Authentication fails (403 Forbidden)

**Error:** `No valid authentication credentials provided`

**Solution:** Add function key header
```bash
curl -H "x-functions-key: any_key_for_local" ...
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

**Solution:** Use public API only
```python
# ✗ WRONG - Blocks internal imports
from engine.shared.storage import get_organization

# ✓ CORRECT - Use public API
from engine.shared.decorators import workflow, param
from engine.shared.context import OrganizationContext
from engine.shared.error_handling import WorkflowException
```

Allowed imports for workspace code:
- `engine.shared.decorators` - @workflow, @param, @data_provider
- `engine.shared.context` - OrganizationContext
- `engine.shared.error_handling` - WorkflowException, ValidationError, etc.
- `engine.shared.models` - Pydantic models

### Port conflicts

**Error:** Azure Functions starts on different port

**Solution:** Check actual port in startup output
```
Now listening on: http://0.0.0.0:7072  # Note: Port 7072, not 7071
```

Update curl commands to use the correct port.

---

## Additional Resources

- **Workspace API Documentation**: `/docs/workspace-api.md`
- **Migration Guide**: `/docs/migration-guide.md`
- **GitHub Actions Protection**: `/.github/workflows/protect-engine.yml`
- **Seed Script Source**: `/scripts/seed_azurite.py`
- **Test Script Source**: `/scripts/test_local_dev.sh`

---

## Summary Checklist

Before starting development, ensure:

- [ ] Azurite is running on port 10002
- [ ] Seed script has populated test data
- [ ] Azure Functions is running and showing endpoints
- [ ] Health endpoint responds: `curl http://localhost:7072/api/health`
- [ ] Test workflow executes successfully
- [ ] Function key authentication works

**Ready to develop!** 🚀

Create workflows in `/workspace/workflows/` and test immediately with function key auth.
