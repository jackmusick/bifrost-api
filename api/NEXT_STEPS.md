# Next Steps - Action Plan

## Immediate Actions

### 1. ✅ Mark All API Integration Test Files
Add `pytestmark = pytest.mark.requires_api` to these files:

- ✅ `tests/integration/api/test_oauth_endpoints.py` (DONE)
- `tests/integration/api/test_oauth_edge_cases.py`
- `tests/integration/api/test_forms_endpoints.py`
- `tests/integration/api/test_secrets_endpoints.py`
- `tests/integration/api/test_endpoints.py`
- `tests/integration/api/test_permissions_endpoints.py`
- `tests/integration/api/test_roles_endpoints.py`
- `tests/integration/api/test_workflow_keys_endpoints.py`
- `tests/integration/api/test_workflows_endpoints.py`
- `tests/integration/api/test_executions_endpoints.py`
- `tests/integration/api/test_organizations_endpoints.py`
- `tests/integration/api/test_org_config_endpoints.py`
- `tests/integration/api/test_roles_edge_cases.py`
- `tests/integration/api/test_forms_edge_cases.py`

**Pattern to add**:
```python
"""
Module docstring...

REQUIRES: Azure Functions API running (func start --port 7071)
"""

import pytest
# ... other imports ...

pytestmark = pytest.mark.requires_api  # Mark all tests in this file
```

### 2. 🔴 Regenerate Frontend Types

**Prerequisites**: Azure Functions API must be running

```bash
# Terminal 1: Start API
cd api
func start --port 7071

# Wait for: "Worker process started and initialized"

# Terminal 2: Generate types
cd client
npm run generate:types
```

**Expected changes**:
- `optionGenerators` → `dataProviders` in metadata types
- New fields in `WorkflowParameter`: `label`, `helpText`, `defaultValue`, `validation`

### 3. 🔴 Fix Frontend Type Errors

After regeneration, check for TypeScript errors:
```bash
cd client
npm run tsc
```

**Likely fixes needed**:
- Update any references to `optionGenerators` → `dataProviders`
- Handle new optional fields in `WorkflowParameter`

### 4. 🔴 Fix Remaining 8 API Tests

**Test Failures**:
1. **Routing Issues** (404s) - OAuth callback, delete endpoints
2. **Auth Issues** (401 vs 400) - Forms invalid JSON
3. **Timeouts** - Secrets endpoints

**Debug approach**:
```bash
# Terminal 1: Start API with verbose logging
cd api
func start --port 7071 --verbose

# Terminal 2: Run failing tests one at a time
pytest tests/integration/api/test_oauth_endpoints.py::TestOAuthConnectionManagement::test_delete_oauth_connection_idempotent -vv

# Check routing, middleware, auth issues
```

## Test Running Reference

### Fast Feedback (Development)
```bash
# Run without API (~50 seconds, 1631 tests)
pytest tests/ -m "not requires_api"
```

### Full Validation (CI/CD)
```bash
# Terminal 1: API
cd api && func start --port 7071

# Terminal 2: All tests
pytest tests/
```

### Specific Test Types
```bash
# Unit tests only
pytest tests/unit/ -v

# Integration (no API)
pytest tests/integration/engine/ -v

# API integration only
pytest tests/ -m requires_api -v

# Specific file
pytest tests/unit/handlers/test_oauth_handlers.py -v
```

## Files Changed Today

### Test Fixes
- `tests/unit/handlers/test_oauth_handlers.py` - Status code fixes
- `tests/integration/engine/test_metadata_endpoint.py` - Field rename
- `tests/unit/handlers/test_discovery_handlers.py` - dataProviders rename

### Model Changes
- `shared/models.py` - WorkflowParameter fields, MetadataResponse rename
- `shared/handlers/discovery_handlers.py` - Field mapping
- `functions/discovery.py` - Logging update

### Configuration
- `pytest.ini` - Added `requires_api` marker
- `tests/integration/api/test_oauth_endpoints.py` - Added marker (example)

### Documentation
- `TESTING.md` - Comprehensive testing guide
- `TEST_SUMMARY.md` - Migration summary
- `NEXT_STEPS.md` - This file

## Success Criteria

- ✅ 1,631 tests passing without API
- ⏳ All 1,640 tests passing with API
- ⏳ Frontend types regenerated
- ⏳ Frontend TypeScript compiles
- ⏳ No test failures in CI/CD

## Timeline

**Today**:
1. ✅ Fixed 6 test failures
2. ✅ Added test markers
3. ✅ Created documentation
4. Mark remaining API test files (~15 files)
5. Regenerate frontend types
6. Fix frontend type errors

**Tomorrow**:
1. Debug remaining 8 API test failures
2. Verify CI/CD pipeline
3. Update team documentation

## Quick Commands

```bash
# Run fast tests
pytest -m "not requires_api"

# Run API tests (with func start running)
pytest -m requires_api

# Run specific test
pytest tests/unit/handlers/test_oauth_handlers.py::test_list_oauth_connections_success -v

# Check test markers
pytest --markers

# Coverage report
pytest --cov=functions --cov=shared --cov-report=html
```
