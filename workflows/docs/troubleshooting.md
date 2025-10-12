# Troubleshooting Guide (T069)

Common issues and solutions for the workflow engine.

## Table of Contents

- [Import Errors](#import-errors)
- [Authentication Issues](#authentication-issues)
- [Azurite Problems](#azurite-problems)
- [Azure Functions Issues](#azure-functions-issues)
- [Workflow Execution Errors](#workflow-execution-errors)
- [GitHub Actions Failures](#github-actions-failures)
- [Performance Issues](#performance-issues)

---

## Import Errors

### Error: `ImportError: Workspace code cannot import engine module`

**Symptom**:
```
ImportError: Workspace code cannot import engine module 'engine.shared.storage'.

Workspace code can only import from the public API:
  - engine.shared.decorators (for @workflow, @param, @data_provider)
  - engine.shared.context (for OrganizationContext)
  - engine.shared.error_handling (for WorkflowException, etc.)
  - engine.shared.models (for Pydantic models)
```

**Cause**: Your workspace code is attempting to import an engine module that's not part of the public API.

**Solution**:
1. Remove the blocked import
2. Use the public API or context instead

```python
# ✗ BLOCKED
from engine.shared.storage import get_organization

# ✓ CORRECT - Use context
async def my_workflow(context: OrganizationContext):
    org_id = context.org.org_id
    org_name = context.org.name
```

**See**: `/docs/workspace-api.md` for complete public API reference

---

### Error: `ModuleNotFoundError: No module named 'engine'`

**Symptom**:
```
ModuleNotFoundError: No module named 'engine'
```

**Cause**: Import path is incorrect or you're running from wrong directory.

**Solution**:
1. Ensure you're in the `/workflows` directory
2. Check import statement uses full path:

```python
# ✓ CORRECT
from engine.shared.decorators import workflow
from engine.shared.context import OrganizationContext

# ✗ WRONG
from shared.decorators import workflow
```

---

##Authentication Issues

### Error: `403 Forbidden - No valid authentication credentials`

**Symptom**:
```json
{
  "error": "Forbidden",
  "message": "No valid authentication credentials provided..."
}
```

**Cause**: Request missing both function key and Easy Auth headers.

**Solution**: Add function key to request:

```bash
# Via header (recommended)
curl -H "x-functions-key: YOUR_KEY" ...

# Via query parameter
curl "http://localhost:7072/api/workflows/test?code=YOUR_KEY"
```

**Local Development**: Any non-empty string works as function key:
```bash
curl -H "x-functions-key: test_key" ...
```

---

### Error: Function key not working

**Symptom**: Still getting 403 even with function key header.

**Cause**: Header name incorrect or key has whitespace.

**Solution**:
1. Check header name (case-insensitive):
   - `x-functions-key` ✅
   - `X-Functions-Key` ✅
   - `X-FUNCTIONS-KEY` ✅

2. Ensure no whitespace:
```bash
# ✗ WRONG - Extra spaces
curl -H "x-functions-key:  my_key  " ...

# ✓ CORRECT
curl -H "x-functions-key: my_key" ...
```

3. Verify key is not empty:
```bash
# This will NOT work
curl -H "x-functions-key: " ...
```

---

## Azurite Problems

### Error: `EADDRINUSE: address already in use`

**Symptom**:
```
Error: listen EADDRINUSE: address already in use :::10002
```

**Cause**: Azurite already running or port 10002 in use.

**Solution**:
```bash
# Find process using port
lsof -i :10002

# Kill existing Azurite
kill -9 <PID>

# Restart Azurite
azurite --silent --location /tmp/azurite
```

---

### Error: Seed script fails with connection error

**Symptom**:
```
Failed to create table client for audit logging: ...
```

**Cause**: Azurite not running or wrong connection string.

**Solution**:
1. Verify Azurite is running:
```bash
curl http://127.0.0.1:10002/devstoreaccount1
# Should return XML response
```

2. Check connection string in `local.settings.json`:
```json
{
  "Values": {
    "TABLE_STORAGE_CONNECTION_STRING": "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
  }
}
```

3. Restart seed script:
```bash
python scripts/seed_azurite.py
```

---

### Error: Seed script slow (>5 seconds)

**Symptom**: Seed script takes longer than 5 second target.

**Cause**: Network latency or Azurite overloaded.

**Solution**:
1. Restart Azurite:
```bash
kill -9 $(lsof -t -i:10002)
azurite --silent --location /tmp/azurite
```

2. Clear Azurite data:
```bash
rm -rf /tmp/azurite/*
```

3. Run seed script again

**Note**: First run may be slower (creates tables). Subsequent runs should be <5s.

---

## Azure Functions Issues

### Error: `No job functions found`

**Symptom**:
```
No job functions found. Try making your job classes and methods public.
```

**Cause**: Not in correct directory or function_app.py missing.

**Solution**:
```bash
# Ensure you're in /workflows directory
cd /path/to/bifrost-integrations/workflows

# Verify function_app.py exists
ls -la function_app.py

# Start Functions
func start
```

---

### Error: `Worker was unable to load function`

**Symptom**:
```
Worker was unable to load function execute_workflow: ...
```

**Cause**: Python version incompatible or dependencies missing.

**Solution**:
1. Check Python version:
```bash
python --version  # Should be 3.11+
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Restart Functions:
```bash
func start
```

---

### Error: Functions starts on wrong port

**Symptom**: Functions starts on port 7072 instead of 7071.

**Cause**: Port 7071 already in use.

**Solution**:
1. Note the actual port in startup output:
```
Now listening on: http://0.0.0.0:7072
```

2. Update curl commands to use correct port:
```bash
curl http://localhost:7072/api/health
```

3. Or kill process using 7071:
```bash
lsof -i :7071
kill -9 <PID>
```

---

## Workflow Execution Errors

### Error: `404 Not Found - Workflow not found`

**Symptom**:
```json
{
  "error": "NotFound",
  "message": "Workflow 'my_workflow' not found"
}
```

**Cause**: Workflow not registered or wrong name.

**Solution**:
1. Verify workflow file exists in `/workspace/workflows/`
2. Check `@workflow` decorator is present:
```python
@workflow(name="my_workflow", description="...")
async def my_workflow(context: OrganizationContext):
    ...
```

3. Ensure file is imported (should be automatic via `import workspace.workflows`)
4. Restart Azure Functions to trigger re-discovery
5. Check workflow name matches URL:
```bash
# If decorator says name="my_workflow"
curl .../api/workflows/my_workflow

# NOT my_workflow.py or myWorkflow
```

---

### Error: `400 Bad Request - Missing required parameter`

**Symptom**:
```json
{
  "error": "BadRequest",
  "message": "Missing required parameter: email"
}
```

**Cause**: Required parameter not provided in request body.

**Solution**: Include all required parameters:
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org-active" \
  -H "x-functions-key: test" \
  -d '{"email": "user@example.com", "name": "John"}' \
  http://localhost:7072/api/workflows/my_workflow
```

**Check**: Review `@param` decorators in workflow for required fields.

---

### Error: `404 Not Found - Organization not found`

**Symptom**:
```json
{
  "error": "NotFound",
  "message": "Organization test-org-123 not found"
}
```

**Cause**: Organization doesn't exist or is inactive, or seed data not loaded.

**Solution**:
1. Run seed script:
```bash
python scripts/seed_azurite.py
```

2. Use correct org ID from seed data:
   - `test-org-active` (active organization)
   - `test-org-demo` (active organization)
   - `test-org-inactive` (will fail - inactive)

3. Verify org exists:
```python
from azure.data.tables import TableServiceClient

client = TableServiceClient.from_connection_string(CONNECTION_STRING)
table = client.get_table_client("Organizations")
orgs = list(table.query_entities("PartitionKey eq 'org'"))

for org in orgs:
    print(f"{org['RowKey']}: {org['Name']} (Active: {org['IsActive']})")
```

---

## GitHub Actions Failures

### Error: `Modifications to /engine/* are not allowed`

**Symptom**: GitHub Action fails on PR with error about engine modifications.

**Cause**: Your PR includes changes to `/engine` directory (intentional protection).

**Solution**:
1. If you're a developer: **Do not modify `/engine` code**
   - Move your changes to `/workspace` if applicable
   - Request platform team to make engine changes

2. If you're platform team: Use authorized bot account
   - `upstream-sync[bot]`
   - `github-actions[bot]`

3. Verify changes:
```bash
git diff main...HEAD --name-only | grep "^engine/"
```

4. Revert engine changes:
```bash
git restore engine/
git commit --amend
git push --force-with-lease
```

---

### Error: GitHub Action times out

**Symptom**: Action runs for >2 minutes and times out.

**Cause**: GitHub Actions has 2-minute timeout (intentionally fast failure).

**Solution**: This indicates a problem with the action setup. Contact platform team.

---

## Performance Issues

### Issue: Slow workflow execution

**Symptoms**: Workflows take longer than expected.

**Diagnosis**:
1. Check execution logs for bottlenecks
2. Review integration call timings
3. Look for synchronous operations that could be async

**Solution**:
```python
# ✗ SLOW - Sequential API calls
result1 = await api.get("/endpoint1")
result2 = await api.get("/endpoint2")

# ✓ FAST - Parallel API calls
import asyncio
result1, result2 = await asyncio.gather(
    api.get("/endpoint1"),
    api.get("/endpoint2")
)
```

---

### Issue: High memory usage

**Symptoms**: Azure Functions consuming excessive memory.

**Cause**: Large data structures, memory leaks, or unbounded loops.

**Solution**:
1. Use generators for large datasets:
```python
# ✗ BAD - Loads everything into memory
all_users = list(table.list_entities())

# ✓ GOOD - Processes iteratively
for user in table.list_entities():
    process(user)
```

2. Clear large variables after use:
```python
large_data = process_data()
result = transform(large_data)
del large_data  # Free memory
```

---

## Getting More Help

### Check Documentation

1. **Workspace API**: `/docs/workspace-api.md`
2. **Local Development**: `/docs/local-development.md`
3. **Migration Guide**: `/docs/migration-guide.md`
4. **Performance & Security**: `/docs/performance-and-security.md`

### Review Logs

1. **Azure Functions logs**: Console output from `func start`
2. **Audit logs**: Query AuditLog table in Azurite
3. **Workflow logs**: context.log() messages in execution records

### Test Locally

Always test locally before deploying:
```bash
# 1. Start Azurite
azurite --silent --location /tmp/azurite

# 2. Seed data
python scripts/seed_azurite.py

# 3. Start Functions
func start

# 4. Test workflow
./scripts/test_local_dev.sh
```

### Contact Platform Team

If issue persists:
1. Gather error messages and logs
2. Document steps to reproduce
3. Note what you've already tried
4. Create issue in repository

---

## Quick Reference

### Common Commands

```bash
# Check what's running on ports
lsof -i :7071  # Azure Functions
lsof -i :10002  # Azurite

# Kill processes
kill -9 <PID>

# Start services
azurite --silent --location /tmp/azurite
func start

# Seed data
python scripts/seed_azurite.py

# Test health
curl http://localhost:7072/api/health

# Test workflow
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org-active" \
  -H "x-functions-key: test" \
  -d '{"param": "value"}' \
  http://localhost:7072/api/workflows/WORKFLOW_NAME
```

### Environment Check

```bash
# Python version
python --version  # Should be 3.11+

# Azure Functions Core Tools
func --version  # Should be 4.x

# Azurite
azurite --version

# Dependencies
pip list | grep azure-functions
pip list | grep azure-data-tables
```

---

## Still Stuck?

**Remember**: Import restrictions and GitHub Actions protection are working as designed to keep the platform secure. If you're hitting these protections, that's usually a sign you should be working in `/workspace` or using the public API instead of modifying `/engine`.
