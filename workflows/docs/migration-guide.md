# Migration Guide (T064)

Guide for migrating existing workflows to the new `/engine` and `/workspace` structure.

## Table of Contents

- [Overview](#overview)
- [What Changed](#what-changed)
- [Migration Checklist](#migration-checklist)
- [Import Path Updates](#import-path-updates)
- [Breaking Changes](#breaking-changes)
- [Step-by-Step Migration](#step-by-step-migration)
- [Verification](#verification)
- [Rollback Plan](#rollback-plan)

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

- [x] ✅ System code moved to `/engine/` (automated)
- [x] ✅ Workflows moved to `/workspace/workflows/` (automated)
- [x] ✅ Import paths updated (automated)
- [x] ✅ GitHub Actions protection enabled
- [x] ✅ Import restrictions installed
- [x] ✅ Authentication system updated
- [ ] ⚠️ **Manual Step**: Review your workflow imports
- [ ] ⚠️ **Manual Step**: Test your workflows locally
- [ ] ⚠️ **Manual Step**: Update any deployment scripts

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
- `engine.shared.decorators` - @workflow, @param, @data_provider
- `engine.shared.context` - OrganizationContext, Organization, Caller
- `engine.shared.error_handling` - WorkflowException, ValidationError, etc.
- `engine.shared.models` - Pydantic models

**Blocked Imports** (will raise `ImportError`):
- `engine.shared.storage` - Use context.config instead
- `engine.shared.middleware` - Use public API
- `engine.execute` - Use public API
- Any other `engine.*` modules not in allowed list

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
- `user_id` may now be `"function_key:default"` for function key auth
- `email` may now be `"function-key@system.local"` for function key auth

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
  http://localhost:7072/api/workflows/YOUR_WORKFLOW
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

Expected: GitHub Action fails with error "Modifications to /engine/* are not allowed"

### Verify Authentication Works

```bash
# Test function key auth
curl -H "x-functions-key: test" http://localhost:7072/api/health

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
curl "http://localhost:7072/api/workflows/test?code=YOUR_KEY"
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

- [ ] All workflows execute successfully
- [ ] Import restrictions prevent engine imports
- [ ] GitHub Actions block `/engine` modifications
- [ ] Local development works (Azurite + seed + Functions)
- [ ] Authentication works (function key + Easy Auth)
- [ ] Configuration is accessible through context
- [ ] Audit logging captures function key usage
- [ ] Tests pass (if applicable)

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
- ✅ System code moved to `/engine`
- ✅ Your workflows moved to `/workspace`
- ✅ Import paths updated automatically
- ✅ Protection mechanisms enabled

**Benefits**:
- 🔒 Protected system code (can't accidentally modify)
- 🚀 Faster local development (Azurite + seed script)
- 🛡️ Enhanced security (import restrictions + audit logging)
- 📚 Clear API boundaries (public API documentation)

Migration should be straightforward for most workflows. If you encounter issues, refer to the troubleshooting section or contact the platform team.
