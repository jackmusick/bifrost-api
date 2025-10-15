# Migration Guide (T064)

Guide for migrating existing workflows to the new `/engine` and `/workspace` structure.

## Table of Contents

-   [Overview](#overview)
-   [What Changed](#what-changed)
-   [Migration Checklist](#migration-checklist)
-   [Import Path Updates](#import-path-updates)
-   [Breaking Changes](#breaking-changes)
-   [Step-by-Step Migration](#step-by-step-migration)
-   [Verification](#verification)
-   [Rollback Plan](#rollback-plan)

---

## Overview

The workflow engine has been restructured to separate system code (`/engine`) from user code (`/workspace`) with enhanced security and development experience.

**Timeline**: This migration was completed in Phase 2 (Foundational) of Feature 002.

**Status**: ✅ **All existing workflows have been migrated automatically**

---

## What Changed

### Directory Structure

**Before:**

```
/workflows/
├── admin/              # Admin functions
├── data_providers/     # Built-in data providers
├── functions/          # Azure Function endpoints
├── shared/             # Shared utilities
├── workflows/          # Custom workflows (YOUR CODE)
├── execute.py          # Execution logic
└── function_app.py     # Function app entry
```

**After:**

```
/workflows/
├── engine/             # Protected system code (DO NOT MODIFY)
│   ├── admin/
│   ├── data_providers/
│   ├── functions/
│   ├── shared/
│   └── execute.py
├── workspace/          # Developer code (YOUR WORKFLOWS)
│   └── workflows/
├── function_app.py
└── host.json
```

### Key Changes

1. **System Code → `/engine`**: All platform code moved to protected directory
2. **User Code → `/workspace`**: Your workflows moved to workspace directory
3. **Import Restrictions**: Workspace code can only import from public API
4. **GitHub Actions Protection**: Prevents accidental `/engine` modifications
5. **Authentication**: Tiered auth system (function key → Easy Auth → 403)

---

## Migration Checklist

-   [x] ✅ System code moved to `/engine/` (automated)
-   [x] ✅ Workflows moved to `/workspace/workflows/` (automated)
-   [x] ✅ Import paths updated (automated)
-   [x] ✅ GitHub Actions protection enabled
-   [x] ✅ Import restrictions installed
-   [x] ✅ Authentication system updated
-   [ ] ⚠️ **Manual Step**: Review your workflow imports
-   [ ] ⚠️ **Manual Step**: Test your workflows locally
-   [ ] ⚠️ **Manual Step**: Update any deployment scripts

---

## Import Path Updates

### Automated Changes (Already Done)

The following import changes were applied automatically:

**Engine Code:**

```python
# Before
from shared.context import OrganizationContext
from shared.decorators import workflow
from shared.storage import get_organization

# After
from engine.shared.context import OrganizationContext
from engine.shared.decorators import workflow
from engine.shared.storage import get_organization
```

**Workspace Code:**

```python
# Before (in /workflows/workflows/)
from shared.decorators import workflow
from shared.context import OrganizationContext

# After (in /workspace/workflows/)
from engine.shared.decorators import workflow
from engine.shared.context import OrganizationContext
```

### Required Manual Changes

**If you have custom imports in your workflows**, update them:

```python
# ✗ OLD - Will fail with ImportError
from shared.decorators import workflow
from shared.context import OrganizationContext

# ✓ NEW - Correct import paths
from engine.shared.decorators import workflow, param
from engine.shared.context import OrganizationContext
from engine.shared.error_handling import ValidationError
```

---

## Breaking Changes

### 1. Import Restrictions (IMPORTANT!)

**What Changed**: Workspace code can NO LONGER import engine internals.

**Allowed Imports**:

-   `engine.shared.decorators` - @workflow, @param, @data_provider
-   `engine.shared.context` - OrganizationContext, Organization, Caller
-   `engine.shared.error_handling` - WorkflowException, ValidationError, etc.
-   `engine.shared.models` - Pydantic models

**Blocked Imports** (will raise `ImportError`):

-   `engine.shared.storage` - Use context.config instead
-   `engine.shared.middleware` - Use public API
-   `engine.execute` - Use public API
-   Any other `engine.*` modules not in allowed list

**Migration Path**:

```python
# ✗ BEFORE - Direct storage access
from engine.shared.storage import get_organization

org = get_organization("org-123")

# ✓ AFTER - Use context
async def my_workflow(context: OrganizationContext):
    org_id = context.org.org_id  # From context
    org_name = context.org.name  # From context
```

### 2. Authentication Changes

**What Changed**: User ID now extracted from authenticated principal (not X-User-Id header).

**Impact**: If you reference `context.caller`:

-   `user_id` may now be `"function_key:default"` for function key auth
-   `email` may now be `"function-key@system.local"` for function key auth

**Migration Path**:

```python
# ✗ BEFORE - Assumed always real user
if context.caller.email == "admin@example.com":
    # Special admin logic

# ✓ AFTER - Check auth type
from engine.shared.auth import is_function_key_auth

if not is_function_key_auth(req) and context.caller.email == "admin@example.com":
    # Special admin logic for real users only
```

### 3. Configuration Access

**What Changed**: Config now loaded through context (no direct storage access).

**Migration Path**:

```python
# ✗ BEFORE
from engine.shared.storage import get_org_config
config = get_org_config("org-123")

# ✓ AFTER
async def my_workflow(context: OrganizationContext):
    config = context.config  # Already loaded!
    api_endpoint = config.get("api_endpoint")
```

---

## Step-by-Step Migration

### Step 1: Pull Latest Changes

```bash
git pull origin main
```

### Step 2: Review Workflow Files

Check your workflows in `/workspace/workflows/`:

```bash
ls -la /workspace/workflows/
```

### Step 3: Update Imports (If Needed)

Search for old import patterns:

```bash
grep -r "from shared\." workspace/workflows/
grep -r "from engine.shared.storage" workspace/workflows/
```

Update any matches to use public API imports.

### Step 4: Test Locally

```bash
# Start Azurite
azurite --silent --location /tmp/azurite

# Seed test data
python scripts/seed_azurite.py

# Start Functions
func start

# Test your workflow
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org-active" \
  -H "x-functions-key: test_key" \
  -d '{"param": "value"}' \
  http://localhost:7071/api/workflows/YOUR_WORKFLOW
```

### Step 5: Run Tests (If You Have Them)

```bash
pytest tests/
```

### Step 6: Commit Changes (If Any)

```bash
git add workspace/workflows/
git commit -m "Update workflow imports for new structure"
git push
```

---

## Verification

### Verify Import Restrictions Work

Create a test file to verify restrictions are active:

```bash
# Create test workflow with blocked import
cat > workspace/workflows/test_blocked_import.py <<'EOF'
from engine.shared.decorators import workflow
from engine.shared.context import OrganizationContext
from engine.shared.storage import get_organization  # BLOCKED!

@workflow(name="test", description="Test")
async def test(context: OrganizationContext):
    return {}
EOF

# Try to start Functions - should fail with ImportError
func start
```

Expected error:

```
ImportError: Workspace code cannot import engine module 'engine.shared.storage'.

Workspace code can only import from the public API:
  - engine.shared.decorators (for @workflow, @param, @data_provider)
  - engine.shared.context (for OrganizationContext)
  - engine.shared.error_handling (for WorkflowException, etc.)
  - engine.shared.models (for Pydantic models)
```

If you see this error, import restrictions are working! ✅

Remove the test file:

```bash
rm workspace/workflows/test_blocked_import.py
```

### Verify GitHub Actions Protection

Try to modify engine code:

```bash
# Attempt to modify engine file (on a branch)
git checkout -b test-protection
echo "# test" >> engine/shared/storage.py
git add engine/shared/storage.py
git commit -m "Test protection"
git push origin test-protection

# Create PR - GitHub Actions should block it
```

Expected: GitHub Action fails with error "Modifications to /engine/\* are not allowed"

### Verify Authentication Works

```bash
# Test function key auth
curl -H "x-functions-key: test" http://localhost:7071/api/health

# Should return health status (not 403)
```

---

## Rollback Plan

If you encounter issues, the old structure is preserved in `/workflows-backup/`:

```bash
# View backup
ls -la /workflows-backup/

# Restore from backup (if needed)
cp -r /workflows-backup/* /workflows/

# Restore git state
git restore .
```

**Note**: Backup was created in Phase 1 (T001) and is safe to delete after successful migration.

---

## Common Migration Issues

### Issue 1: Import Errors

**Symptom**: `ImportError: Workspace code cannot import engine module`

**Solution**: Update imports to use public API:

```python
# Remove blocked import
# from engine.shared.storage import get_organization

# Use context instead
async def workflow(context: OrganizationContext):
    org_id = context.org.org_id
```

### Issue 2: Function Key Auth Not Working

**Symptom**: Getting 403 Forbidden with function key

**Solution**: Ensure key is in header or query param:

```bash
# Header (recommended)
curl -H "x-functions-key: YOUR_KEY" ...

# Query param (alternative)
curl "http://localhost:7071/api/workflows/test?code=YOUR_KEY"
```

### Issue 3: Workflows Not Discovered

**Symptom**: Workflow returns 404 Not Found

**Solution**: Ensure workflow file is in `/workspace/workflows/` and has `@workflow` decorator:

```bash
# Check file location
ls -la workspace/workflows/

# Restart Functions to trigger discovery
func start
```

### Issue 4: Configuration Not Available

**Symptom**: `KeyError` when accessing config

**Solution**: Use `.get()` with default:

```python
# ✗ BAD - May raise KeyError
api_endpoint = context.config["api_endpoint"]

# ✓ GOOD - Safe with default
api_endpoint = context.config.get("api_endpoint", "https://default.api.com")
```

---

## Post-Migration Validation

After migration, verify the following:

-   [ ] All workflows execute successfully
-   [ ] Import restrictions prevent engine imports
-   [ ] GitHub Actions block `/engine` modifications
-   [ ] Local development works (Azurite + seed + Functions)
-   [ ] Authentication works (function key + Easy Auth)
-   [ ] Configuration is accessible through context
-   [ ] Audit logging captures function key usage
-   [ ] Tests pass (if applicable)
-   [ ] Key Vault integration works for secrets
-   [ ] OAuth connections are properly configured
-   [ ] Data providers are discoverable
-   [ ] Form validation works correctly
-   [ ] Performance benchmarks are met

---

## Advanced Migration Scenarios

### Migrating Complex Workflows with External Dependencies

For workflows that import external libraries or have complex dependencies:

```python
# ✗ BEFORE - Direct imports that may need updating
import requests
import pandas as pd
from engine.shared.storage import get_organization

@workflow(name="complex_workflow")
async def complex_workflow(context):
    org = get_organization(context.org_id)
    data = requests.get(org.config["api_url"]).json()
    df = pd.DataFrame(data)
    return df.to_dict()

# ✓ AFTER - Use context and async patterns
import aiohttp
import pandas as pd

@workflow(name="complex_workflow")
async def complex_workflow(context: OrganizationContext):
    api_url = context.get_config("api_url")

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as response:
            data = await response.json()

    df = pd.DataFrame(data)
    return df.to_dict()
```

### Migrating Workflows with Custom Integrations

For workflows that use custom integration clients:

```python
# ✗ BEFORE - Direct integration instantiation
from integrations.custom_api import CustomAPIClient

@workflow(name="custom_integration")
async def custom_integration(context):
    client = CustomAPIClient(api_key="hardcoded-key")
    return client.get_data()

# ✓ AFTER - Use integration registry
@workflow(name="custom_integration")
async def custom_integration(context: OrganizationContext):
    # Get registered integration
    client = context.get_integration("custom_api")
    return await client.get_data()
```

### Migrating Scheduled Workflows

For workflows that run on schedules:

```python
# ✗ BEFORE - May need schedule configuration
@workflow(name="daily_report")
async def daily_report(context):
    # Generate daily report
    pass

# ✓ AFTER - Explicit schedule configuration
@workflow(
    name="daily_report",
    description="Generate daily organization report",
    execution_mode="scheduled",
    schedule="0 8 * * *",  # Daily at 8 AM UTC
    timeout_seconds=600,
    expose_in_forms=False
)
async def daily_report(context: OrganizationContext):
    context.log("info", "Starting daily report generation")

    # Generate report
    report_data = await generate_report(context)

    context.save_checkpoint("report_complete", {
        "report_id": report_data["id"],
        "generated_at": datetime.now().isoformat()
    })

    return report_data
```

---

## Migration Testing Strategy

### 1. Unit Testing

Test individual workflow functions with mocked context:

```python
# tests/test_migration.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from workspace.workflows.my_workflow import my_workflow

@pytest.mark.asyncio
async def test_my_workflow_migration():
    # Mock context with new structure
    context = MagicMock()
    context.org.org_id = "test-org-active"
    context.org.name = "Test Organization"
    context.get_config = MagicMock(return_value="test_value")
    context.log = MagicMock()
    context.save_checkpoint = MagicMock()

    # Test workflow execution
    result = await my_workflow(context, "test@example.com")

    # Verify results
    assert result["success"] is True
    context.log.assert_called()
```

### 2. Integration Testing

Test full workflow execution with local environment:

```bash
#!/bin/bash
# scripts/test_migration.sh

echo "Starting migration tests..."

# Start services
azurite --silent --location /tmp/azurite &
AZURITE_PID=$!
sleep 2

python scripts/seed_azurite.py
func start &
FUNCTIONS_PID=$!
sleep 5

# Test each workflow
workflows=("create_user" "update_user" "delete_user" "generate_report")

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
echo "All migration tests passed!"
```

### 3. Performance Testing

Verify performance benchmarks are maintained:

```python
# tests/test_performance.py
import time
import asyncio
import aiohttp

async def test_workflow_performance():
    """Test that workflows meet performance targets"""

    # Test import restriction overhead
    start = time.time()
    from engine.shared.decorators import workflow
    import_time = (time.time() - start) * 1000

    assert import_time < 50, f"Import time {import_time}ms exceeds 50ms target"

    # Test workflow execution time
    start = time.time()

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:7071/api/workflows/simple_test",
            headers={
                "Content-Type": "application/json",
                "X-Organization-Id": "test-org-active",
                "x-functions-key": "test"
            },
            json={"param": "value"}
        ) as response:
            result = await response.json()

    execution_time = (time.time() - start) * 1000
    assert execution_time < 5000, f"Execution time {execution_time}ms exceeds 5s target"

    print("✅ Performance tests passed")
```

---

## Rollback and Recovery Procedures

### Emergency Rollback

If critical issues are discovered post-migration:

```bash
# 1. Stop all services
pkill -f "func start"
pkill -f "azurite"

# 2. Restore from backup
cp -r /workflows-backup/* /workflows/

# 3. Restore git state
git checkout main
git reset --hard HEAD~1  # Remove migration commit

# 4. Restart services
azurite --silent --location /tmp/azurite &
func start &

# 5. Verify rollback
curl http://localhost:7071/api/health
```

### Partial Rollback

If only specific workflows have issues:

```bash
# 1. Identify problematic workflows
grep -r "ImportError" workspace/workflows/

# 2. Temporarily disable problematic workflows
mv workspace/workflows/problematic_workflow.py workspace/workflows/problematic_workflow.py.disabled

# 3. Restart Functions
func start

# 4. Fix issues and re-enable
mv workspace/workflows/problematic_workflow.py.disabled workspace/workflows/problematic_workflow.py
```

---

## Migration Monitoring

### Health Checks

Implement health checks to monitor migration success:

```python
# scripts/migration_health_check.py
import asyncio
import aiohttp
from datetime import datetime

async def check_migration_health():
    """Comprehensive health check after migration"""

    health_status = {
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }

    # Check 1: API Health
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:7071/api/health") as response:
                if response.status == 200:
                    health_status["checks"]["api_health"] = "✅ PASS"
                else:
                    health_status["checks"]["api_health"] = f"❌ FAIL - HTTP {response.status}"
    except Exception as e:
        health_status["checks"]["api_health"] = f"❌ FAIL - {str(e)}"

    # Check 2: Import Restrictions
    try:
        # Test that blocked imports are rejected
        result = subprocess.run([
            "python", "-c",
            "from engine.shared.storage import get_organization"
        ], capture_output=True, text=True, cwd="/workflows")

        if result.returncode != 0 and "ImportError" in result.stderr:
            health_status["checks"]["import_restrictions"] = "✅ PASS"
        else:
            health_status["checks"]["import_restrictions"] = "❌ FAIL - Imports not restricted"
    except Exception as e:
        health_status["checks"]["import_restrictions"] = f"❌ FAIL - {str(e)}"

    # Check 3: Workflow Discovery
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:7071/api/workflows") as response:
                if response.status == 200:
                    workflows = await response.json()
                    if len(workflows) > 0:
                        health_status["checks"]["workflow_discovery"] = f"✅ PASS - {len(workflows)} workflows"
                    else:
                        health_status["checks"]["workflow_discovery"] = "❌ FAIL - No workflows found"
                else:
                    health_status["checks"]["workflow_discovery"] = f"❌ FAIL - HTTP {response.status}"
    except Exception as e:
        health_status["checks"]["workflow_discovery"] = f"❌ FAIL - {str(e)}"

    return health_status

# Run health check
if __name__ == "__main__":
    health = asyncio.run(check_migration_health())
    print("Migration Health Check Results:")
    for check, status in health["checks"].items():
        print(f"  {check}: {status}")
```

---

## Getting Help

**If you encounter migration issues:**

1. **Check documentation**:

    - Workspace API: `/docs/workspace-api.md`
    - Local Development: `/docs/local-development.md`
    - Troubleshooting: `/docs/troubleshooting.md`

2. **Review error messages**: Import errors include specific guidance

3. **Test locally**: Use Azurite to test before deploying

4. **Contact platform team**: For complex migration issues

---

## Summary

**What You Need to Do**:

1. ✅ Pull latest code (system migration already done)
2. ⚠️ Update any custom imports in your workflows
3. ⚠️ Test workflows locally
4. ⚠️ Update deployment scripts (if any)

**What's Already Done**:

-   ✅ System code moved to `/engine`
-   ✅ Your workflows moved to `/workspace`
-   ✅ Import paths updated automatically
-   ✅ Protection mechanisms enabled

**Benefits**:

-   🔒 Protected system code (can't accidentally modify)
-   🚀 Faster local development (Azurite + seed script)
-   🛡️ Enhanced security (import restrictions + audit logging)
-   📚 Clear API boundaries (public API documentation)

Migration should be straightforward for most workflows. If you encounter issues, refer to the troubleshooting section or contact the platform team.
