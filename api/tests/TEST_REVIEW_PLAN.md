# Test Review Plan: Fixing 110 Remaining Test Failures

**Date Created:** 2025-10-14
**Current Status:** 357 passing (73%), 110 failing (22%), 0 errors
**Total Tests:** 490 tests

---

## Executive Summary

After cleaning up infrastructure tests and fixing import path issues, we have **110 legitimate test failures** remaining. These failures are due to **schema changes and API refactoring**, not infrastructure problems. All tests now execute successfully (0 errors) - they just have incorrect expectations.

**Your mission:** Review and fix these 110 failing tests to match our current schema and business logic.

---

## Our Testing Philosophy

### ✅ What We TEST (High Value)

1. **Business Logic**
   - Authorization rules (who can access what)
   - Permission checking (platform admin vs org user)
   - Data scoping (GLOBAL vs org-scoped)
   - Workflow execution logic
   - Form access control

2. **API Contracts**
   - Response schemas (Pydantic models)
   - Required vs optional fields
   - Data type validation
   - Error response formats

3. **End-to-End Workflows**
   - Full user journeys
   - Multi-step operations
   - Cross-component integration

4. **Security Boundaries**
   - Cross-org isolation
   - Role-based access
   - Sensitive data masking

### ❌ What We DON'T Test (Low Value)

1. **Infrastructure Wrappers** - Already removed:
   - Azure SDK clients (Key Vault, Table Storage)
   - Logging infrastructure
   - Authentication service plumbing
   - Config parsing utilities
   - Test fixtures themselves

2. **External Dependencies**
   - Azure services behavior
   - Third-party library internals
   - HTTP client behavior

3. **Implementation Details**
   - Internal helper functions
   - Private methods
   - Data transformation steps (unless business-critical)

---

## Test Organization Structure

```
tests/
├── contract/                    # API response schema tests (196 tests)
│   ├── test_forms_contract.py
│   ├── test_oauth_api_contract.py
│   ├── test_org_config_contract.py
│   ├── test_organizations_contract.py
│   ├── test_permissions_contract.py
│   ├── test_roles_contract.py
│   └── test_secrets_contract.py
│
├── engine/
│   ├── contract/                # Engine contract tests (76 tests)
│   │   ├── test_data_provider_contract.py
│   │   ├── test_execution_contract.py
│   │   ├── test_github_action_protection.py
│   │   ├── test_import_restriction.py
│   │   ├── test_tiered_authentication.py
│   │   └── test_type_stubs.py
│   │
│   ├── integration/             # Component integration tests (69 tests)
│   │   ├── test_auth_flow.py
│   │   ├── test_auto_discovery.py
│   │   ├── test_cross_org_isolation.py
│   │   ├── test_developer_workflow.py
│   │   ├── test_metadata_endpoint.py
│   │   ├── test_seed_data.py
│   │   ├── test_workflow_execution.py
│   │   └── test_workspace_execution.py
│   │
│   └── unit/                    # Core business logic (35 tests)
│       ├── test_decorators.py
│       └── test_registry.py
│
├── integration_e2e/             # End-to-end tests (92 tests)
│   ├── test_config_e2e.py
│   ├── test_forms_e2e.py
│   ├── test_oauth_e2e.py
│   ├── test_organizations_e2e.py
│   ├── test_roles_permissions_e2e.py
│   ├── test_security_e2e.py
│   └── test_workflow_execution_e2e.py
│
├── test_authorization.py        # Business logic tests (10 tests)
└── test_request_context.py      # Business logic tests (14 tests) ✅ ALL PASSING
```

---

## Current Schema & Data Models

### Key Schema Changes (Why Tests Are Failing)

1. **Users Table Structure**
   ```python
   # NEW SCHEMA:
   {
       "PartitionKey": "user@example.com",
       "RowKey": "user",  # Always "user" (not email)
       "Email": "user@example.com",
       "Name": "User Name",
       "IsPlatformAdmin": bool,
       "UserType": "PLATFORM" | "ORG"  # NEW FIELD
   }
   ```

2. **Relationships Table Structure**
   ```python
   # User-to-org assignments
   {
       "PartitionKey": "GLOBAL",
       "RowKey": "userperm:{user_email}:{org_id}",
       # Other permission fields...
   }
   ```

3. **Configuration Values**
   ```python
   # Config entries now have structured format:
   {
       "key_name": {
           "value": "actual_value",
           "type": "string" | "int" | "bool" | "json" | "secret_ref"
       }
   }
   ```

4. **Authentication Headers**
   - Function Key: `x-functions-key` header or `?code` param
   - EasyAuth: `X-MS-CLIENT-PRINCIPAL` (base64-encoded JSON)
   - Org Context: `X-Organization-Id` header (platform admins only)

---

## How to Fix Failing Tests

### Step 1: Understand the Test Category

**Contract Tests** (`tests/contract/`, `tests/engine/contract/`)
- **Purpose:** Validate API response schemas match Pydantic models
- **Common Fixes:**
  - Update expected field names
  - Add/remove required fields
  - Fix data types
  - Update enum values

**Integration Tests** (`tests/engine/integration/`)
- **Purpose:** Test multiple components working together
- **Common Fixes:**
  - Update test data to match schema
  - Fix mock fixtures
  - Update expected behavior

**E2E Tests** (`tests/integration_e2e/`)
- **Purpose:** Full user journey testing
- **Common Fixes:**
  - Update API call payloads
  - Fix expected response structures
  - Update test data setup
  - Fix assertions on response fields

### Step 2: Run Individual Test to See Failure

```bash
# Run single failing test with verbose output
python -m pytest tests/path/to/test_file.py::TestClass::test_name -v --tb=short

# Run all tests in a file
python -m pytest tests/path/to/test_file.py -v

# Run tests in a directory
python -m pytest tests/contract/ -v
```

### Step 3: Categorize the Failure Type

**Type A: Schema Mismatch** (Most Common)
```python
# Example: Field name changed
# OLD: entity["OrgId"]
# NEW: entity["org_id"]

# Example: New required field
# OLD: {"name": "Test Org"}
# NEW: {"name": "Test Org", "tenant_id": "abc-123"}
```

**Type B: Business Logic Change**
```python
# Example: Permission rules changed
# OLD: Regular users can create forms
# NEW: Only platform admins can create forms
```

**Type C: Test Data Outdated**
```python
# Example: Mock data doesn't match current structure
# OLD: Mock returns flat dict
# NEW: Mock should return nested structure
```

**Type D: API Endpoint Change**
```python
# Example: Endpoint path or method changed
# OLD: GET /api/config/{key}
# NEW: GET /api/config?key={key}
```

### Step 4: Apply the Fix

**For Schema Mismatches:**
1. Read the actual model in `shared/models.py`
2. Update test expectations to match
3. Update test data/fixtures to match

**For Business Logic Changes:**
1. Verify the new behavior is intentional
2. Update test assertions
3. If behavior is wrong, fix the code (not the test)

**For Test Data Issues:**
1. Update fixtures in `tests/conftest.py`
2. Fix mock return values
3. Ensure test data follows current schema

### Step 5: Verify the Fix

```bash
# Run the specific test
python -m pytest tests/path/to/test_file.py::TestClass::test_name -v

# If it passes, run the whole file
python -m pytest tests/path/to/test_file.py -v

# Finally, run the full suite
npm test
```

---

## Common Patterns & Examples

### Pattern 1: Fixing User Schema in Tests

**Before:**
```python
mock_user = {
    "PartitionKey": "user@example.com",
    "RowKey": "user@example.com",  # ❌ WRONG
    "IsPlatformAdmin": True,
    "OrgId": "org-123"  # ❌ WRONG - not stored here
}
```

**After:**
```python
mock_user = {
    "PartitionKey": "user@example.com",
    "RowKey": "user",  # ✅ Always "user"
    "Email": "user@example.com",
    "Name": "User Name",
    "IsPlatformAdmin": True,
    "UserType": "PLATFORM"  # ✅ NEW FIELD
}

# Org assignment goes in Relationships table:
mock_relationship = {
    "PartitionKey": "GLOBAL",
    "RowKey": "userperm:user@example.com:org-123"
}
```

### Pattern 2: Fixing Config Tests

**Before:**
```python
# Test expects flat value
assert config_value == "some-value"
```

**After:**
```python
# Config now has structured format
assert config_entry["value"] == "some-value"
assert config_entry["type"] == "string"
```

### Pattern 3: Fixing Auth Headers in E2E Tests

**Before:**
```python
headers = {
    "Authorization": "Bearer token123",  # ❌ OLD
    "X-Organization-Id": "org-123"
}
```

**After:**
```python
# For function key auth:
headers = {
    "x-functions-key": "test-key",
    "X-Organization-Id": "org-123"  # Optional
}

# For EasyAuth:
import base64, json
principal = {"userId": "user@example.com", "userDetails": "user@example.com"}
principal_header = base64.b64encode(json.dumps(principal).encode()).decode()
headers = {
    "X-MS-CLIENT-PRINCIPAL": principal_header,
    "X-Organization-Id": "org-123"  # Only for platform admins
}
```

### Pattern 4: Fixing Response Assertions

**Before:**
```python
response = client.get("/api/forms")
assert "forms" in response.json()
assert response.json()["forms"][0]["name"] == "Test Form"
```

**After - Check actual model first:**
```python
# 1. Read shared/models.py to see actual FormResponse structure
# 2. Update assertions to match:
response = client.get("/api/forms")
data = response.json()
assert "items" in data  # Maybe changed from "forms" to "items"
assert data["items"][0]["form_name"] == "Test Form"  # Maybe "name" -> "form_name"
```

---

## Prioritization Strategy

### High Priority (Fix First) 🔴

**E2E Tests** - These represent real user workflows
- `tests/integration_e2e/test_security_e2e.py` - Critical security tests
- `tests/integration_e2e/test_roles_permissions_e2e.py` - Core RBAC
- `tests/integration_e2e/test_organizations_e2e.py` - Multi-tenancy

**Business Logic Tests** - Core functionality
- `tests/test_authorization.py` - Permission checking

### Medium Priority (Fix Second) 🟡

**Contract Tests** - API stability
- `tests/contract/` - All API contract tests
- Ensure backward compatibility
- Document breaking changes

**Engine Integration** - Component interactions
- `tests/engine/integration/test_auth_flow.py`
- `tests/engine/integration/test_cross_org_isolation.py`

### Lower Priority (Fix Last) 🟢

**Engine Contracts** - Internal contracts
- `tests/engine/contract/` - Can be adjusted if internal APIs change

**Remaining Integration** - Nice-to-have coverage
- `tests/engine/integration/test_metadata_endpoint.py`
- `tests/engine/integration/test_auto_discovery.py`

---

## Tools & Commands Reference

### Run Tests by Category

```bash
# All E2E tests
python -m pytest tests/integration_e2e/ -v

# All contract tests
python -m pytest tests/contract/ -v

# All engine tests
python -m pytest tests/engine/ -v

# Only failing tests
python -m pytest --lf -v

# Stop on first failure
python -m pytest -x -v

# Run specific test class
python -m pytest tests/integration_e2e/test_security_e2e.py::TestCrossOrgIsolation -v
```

### Get Test Failure Summary

```bash
# Short summary
npm test 2>&1 | grep FAILED | head -20

# Full output with details
python -m pytest tests/integration_e2e/ -v --tb=short 2>&1 | tee test_output.txt
```

### Check Test Coverage

```bash
# Run with coverage (if installed)
python -m pytest tests/ --cov=. --cov-report=html

# See which code paths are tested
open htmlcov/index.html
```

---

## Key Files to Reference

### Models & Schemas
- `shared/models.py` - Pydantic models for all entities
- `shared/custom_types.py` - Custom type definitions
- `shared/storage.py` - Table structure documentation

### Test Fixtures
- `tests/conftest.py` - Shared fixtures for all tests
- `tests/engine/conftest.py` - Engine-specific fixtures
- `tests/helpers/mock_auth.py` - Auth mocking utilities
- `tests/helpers/mock_requests.py` - Request mocking utilities

### Core Business Logic
- `shared/request_context.py` - Auth & context handling ✅ (tests all passing)
- `shared/authorization.py` - Permission checking
- `functions/` - All API endpoints

---

## Success Criteria

### Definition of Done

A test is **fixed** when:
1. ✅ It passes consistently
2. ✅ It tests the current behavior (not old behavior)
3. ✅ Test data matches current schema
4. ✅ Assertions are meaningful and correct
5. ✅ No deprecated fields or APIs referenced

### What Good Looks Like

After fixing all 110 tests:
- **Pass rate:** 90%+ (some tests may be legitimately removed)
- **Error count:** 0 (already achieved!)
- **Test execution time:** <5 seconds
- **No flaky tests:** All tests deterministic

---

## Common Pitfalls to Avoid

### ❌ Don't Do This

1. **Commenting out failing assertions**
   ```python
   # assert response.status_code == 200  # ❌ NO!
   ```

2. **Making tests too permissive**
   ```python
   assert response.status_code in [200, 201, 204, 400, 403]  # ❌ TOO BROAD!
   ```

3. **Ignoring test failures without investigation**
   ```python
   @pytest.mark.skip("broken")  # ❌ WHY IS IT BROKEN?
   ```

4. **Testing implementation details**
   ```python
   assert mock_table.query_entities.call_count == 2  # ❌ FRAGILE
   ```

5. **Duplicating E2E coverage in unit tests**
   - If E2E test covers it, unit test may not be needed

### ✅ Do This Instead

1. **Understand the failure, then fix it**
   ```python
   # Read error, check model, update assertion
   assert response.status_code == 200
   assert response.json()["items"] == expected_items
   ```

2. **Be specific and intentional**
   ```python
   assert response.status_code == 201  # Created
   assert "form_id" in response.json()
   ```

3. **Document why tests are skipped (if necessary)**
   ```python
   @pytest.mark.skip("Waiting for OAuth service deployment")
   def test_oauth_flow():
       ...
   ```

4. **Test behavior, not implementation**
   ```python
   # Good: Test the outcome
   forms = get_user_visible_forms(user_id)
   assert len(forms) == 2
   ```

---

## Tracking Progress

### Create a Checklist

As you fix tests, track your progress:

```markdown
## E2E Tests (Priority 1)
- [ ] test_config_e2e.py (15 failures)
- [ ] test_forms_e2e.py (10 failures)
- [ ] test_oauth_e2e.py (12 failures)
- [ ] test_organizations_e2e.py (9 failures)
- [ ] test_roles_permissions_e2e.py (15 failures)
- [ ] test_security_e2e.py (17 failures)
- [ ] test_workflow_execution_e2e.py (2 failures)

## Business Logic (Priority 2)
- [ ] test_authorization.py (1 failure)

## Contract Tests (Priority 3)
- [ ] test_forms_contract.py
- [ ] test_oauth_api_contract.py
- [ ] test_org_config_contract.py
...
```

### After Each File

Run the full suite to ensure you didn't break anything:
```bash
npm test 2>&1 | tail -1
```

Target: See the failure count drop from 110 → 100 → 90 → ...

---

## Questions to Ask While Reviewing

For each failing test, ask:

1. **Is this test still relevant?**
   - Does it test current functionality?
   - Or was the feature removed/changed?

2. **Is the test in the right category?**
   - Should it be E2E instead of unit?
   - Is it duplicating coverage?

3. **What changed?**
   - Schema field name?
   - Business rule?
   - API endpoint?
   - Data type?

4. **Is the new behavior correct?**
   - If yes: Fix the test
   - If no: Fix the code, not the test

5. **Can this test be deleted?**
   - Is it redundant with E2E coverage?
   - Is it testing infrastructure we removed?

---

## Final Notes

### Philosophy
- **Tests should document behavior** - They're living documentation
- **Fail-fast is good** - Better to catch bugs in tests than production
- **Don't chase 100% coverage** - Focus on high-value tests
- **E2E tests are your safety net** - Keep them working first

### When in Doubt
1. Read the actual model in `shared/models.py`
2. Check the actual endpoint in `functions/`
3. Run the test and read the error carefully
4. Ask: "What does this test actually verify?"
5. Update the test to match current reality

### Remember
- You've already eliminated all infrastructure noise (0 errors!)
- All 110 failures are legitimate expectation mismatches
- The code works - the tests just need to catch up
- Take it one file at a time
- Run tests frequently to catch regressions

---

**Good luck! You've got this. 💪**

The test suite is in much better shape than when we started. Now it's just about aligning expectations with your refactored schema.
