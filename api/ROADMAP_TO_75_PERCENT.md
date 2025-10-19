# Roadmap to 75% Coverage

**Current:** 53.71% (3,638 / 6,774 lines)
**Target:** 75.00% (5,080 / 6,774 lines)
**Need:** +1,442 lines

**Strategy:** Focus on top 15 high-impact files (offers +1,480 lines = 97.4% of target)

---

## Overview

Getting to 75% coverage requires covering **97.4% of the potential gain** from just the **top 15 files**. This is very achievable because:

1. ✅ All 15 files already have *some* coverage (12-41%)
2. ✅ All are API endpoints or services (integration tests work well)
3. ✅ Test infrastructure already exists (from Phases 1-4)
4. ✅ Patterns established (can be replicated)

---

## The Top 15 Target Files

| Priority | File | Current | Missing | Gain to 80% | Type |
|----------|------|---------|---------|-------------|------|
| 1 | `functions/oauth_api.py` | 17.7% | 382 | **289 lines** | API |
| 2 | `functions/forms.py` | 15.4% | 302 | **230 lines** | API |
| 3 | `functions/roles.py` | 27.8% | 184 | **133 lines** | API |
| 4 | `functions/secrets.py` | 20.4% | 148 | **110 lines** | API |
| 5 | `functions/org_config.py` | 25.0% | 144 | **105 lines** | API |
| 6 | `functions/permissions.py` | 33.5% | 117 | **81 lines** | API |
| 7 | `functions/workflow_keys.py` | 22.8% | 98 | **72 lines** | API |
| 8 | `functions/oauth_refresh_timer.py` | 12.7% | 89 | **68 lines** | Timer |
| 9 | `functions/workflows.py` | 19.4% | 87 | **65 lines** | API |
| 10 | `functions/organizations.py` | 31.2% | 88 | **62 lines** | API |
| 11 | `functions/openapi.py` | 16.1% | 78 | **59 lines** | Metadata |
| 12 | `services/oauth_provider.py` | 14.3% | 72 | **55 lines** | Service |
| 13 | `functions/executions.py` | 24.0% | 73 | **53 lines** | API |
| 14 | `shared/middleware.py` | 40.8% | 77 | **51 lines** | Core |
| 15 | `functions/endpoints.py` | 22.0% | 64 | **47 lines** | API |

**Total Potential:** +1,480 lines (would bring coverage to **75.55%**)

---

## Execution Strategy: 3 Phases (Parallel)

### Phase 5A: Top 5 API Endpoints (High Impact)
**Target:** +867 lines | **Timeline:** 2-3 days | **Priority:** Critical

**Files:**
1. `functions/oauth_api.py` - OAuth complete flows (+289 lines)
2. `functions/forms.py` - Form validation/execution (+230 lines)
3. `functions/roles.py` - Role assignment edge cases (+133 lines)
4. `functions/secrets.py` - Secrets encryption/access (+110 lines)
5. `functions/org_config.py` - Config validation (+105 lines)

**Approach:**
- Expand existing integration test files from Phase 4
- Add comprehensive error path testing
- Test all HTTP methods and status codes
- Cover authorization edge cases
- Test data validation thoroughly

**Test Files to Expand:**
- Expand `tests/integration/api/test_oauth_edge_cases.py`
- Expand `tests/integration/api/test_forms_edge_cases.py`
- Expand `tests/integration/api/test_roles_edge_cases.py`
- Expand `tests/integration/api/test_secrets_endpoints.py`
- Expand `tests/integration/api/test_org_config_endpoints.py`

**Estimated Tests:** ~120 new tests

---

### Phase 5B: Mid-Tier APIs + Services (Medium Impact)
**Target:** +382 lines | **Timeline:** 2 days | **Priority:** High

**Files:**
6. `functions/permissions.py` - Permission queries (+81 lines)
7. `functions/workflow_keys.py` - Key management (+72 lines)
8. `functions/oauth_refresh_timer.py` - Token refresh (+68 lines)
9. `functions/workflows.py` - Workflow execution (+65 lines)
10. `functions/organizations.py` - Org management (+62 lines)
11. `services/oauth_provider.py` - OAuth provider logic (+55 lines)

**Approach:**
- Integration tests for API endpoints
- Unit tests for service layer (oauth_provider)
- Test timer trigger function (oauth_refresh_timer)
- Cover workflow execution paths

**Test Files:**
- Expand `tests/integration/api/test_permissions_endpoints.py`
- Expand `tests/integration/api/test_workflow_keys_endpoints.py`
- Create `tests/unit/test_oauth_refresh_timer.py`
- Create `tests/integration/api/test_workflows_endpoints.py`
- Expand `tests/integration/api/test_organizations_endpoints.py` (NEW)
- Create `tests/unit/services/test_oauth_provider.py`

**Estimated Tests:** ~80 new tests

---

### Phase 5C: Supporting APIs + Infrastructure (Finishing Touches)
**Target:** +219 lines | **Timeline:** 1-2 days | **Priority:** Medium

**Files:**
12. `functions/openapi.py` - OpenAPI metadata (+59 lines)
13. `functions/executions.py` - Execution tracking (+53 lines)
14. `shared/middleware.py` - Middleware edge cases (+51 lines)
15. `functions/endpoints.py` - Generic endpoint utils (+47 lines)

**Approach:**
- Test OpenAPI spec generation
- Test execution status tracking
- Expand middleware edge case tests
- Test generic endpoint utilities

**Test Files:**
- Create `tests/unit/test_openapi.py`
- Create `tests/integration/api/test_executions_endpoints.py`
- Expand `tests/unit/test_middleware.py` (more edge cases)
- Create `tests/integration/api/test_endpoints.py`

**Estimated Tests:** ~50 new tests

---

## Parallel Execution Plan

Run all 3 phases simultaneously with 3 code-executor agents:

```
Phase 5A (Agent 1): Top 5 APIs → +867 lines
Phase 5B (Agent 2): Mid-tier APIs + Services → +382 lines
Phase 5C (Agent 3): Supporting APIs + Infrastructure → +219 lines
```

**Combined Impact:** +1,468 lines (exceeds +1,442 target by 26 lines)
**Expected Coverage:** **75.55%** (exceeds 75% target)

---

## Detailed Implementation Specs

### Phase 5A: Top 5 API Endpoints

#### 1. OAuth API Complete Flows (`functions/oauth_api.py`)
**Current:** 17.7% | **Target:** 80% | **Gain:** +289 lines

**What to Test:**
- Complete authorization flows (success + all error paths)
- Callback handling (valid codes, invalid states, expired tokens)
- Connection CRUD edge cases (concurrent updates, deletions)
- Provider-specific flows (Microsoft, Google, Custom)
- Token refresh (success, failure, expiry)
- Credential encryption/decryption paths
- State management transitions
- Error responses (400, 401, 403, 404, 500)

**Test Additions:**
- ~35 new tests in `test_oauth_edge_cases.py`
- Cover every endpoint × every error scenario
- Test authorization flow state machine
- Test concurrent operations

#### 2. Forms API Validation/Execution (`functions/forms.py`)
**Current:** 15.4% | **Target:** 80% | **Gain:** +230 lines

**What to Test:**
- Form field validation (all field types)
- Complex schema validation (nested, conditionals, dependencies)
- Form submission processing
- Workflow execution triggering
- File attachments handling
- Multi-step forms
- Form versioning and updates
- Conditional field logic
- Validation error messages

**Test Additions:**
- ~30 new tests in `test_forms_edge_cases.py`
- Test every field type thoroughly
- Test schema validation rules
- Test form execution paths

#### 3. Roles API Assignment Edge Cases (`functions/roles.py`)
**Current:** 27.8% | **Target:** 80% | **Gain:** +133 lines

**What to Test:**
- Bulk operations (add/remove many users)
- Permission inheritance
- Role hierarchies
- Assignment conflicts
- Cascade deletes
- Form-role relationships
- User-role relationships
- Permission checks at boundaries

**Test Additions:**
- ~20 new tests in `test_roles_edge_cases.py`
- Test bulk operations
- Test permission cascading
- Test relationship management

#### 4. Secrets API Encryption/Access (`functions/secrets.py`)
**Current:** 20.4% | **Target:** 80% | **Gain:** +110 lines

**What to Test:**
- Secret encryption before storage
- Access control (who can read/write)
- Secret rotation
- Bulk operations
- Secret history/versioning
- Integration with Key Vault
- Audit logging
- Error handling

**Test Additions:**
- ~18 new tests in `test_secrets_endpoints.py`
- Test encryption flow
- Test access control thoroughly
- Test audit trail

#### 5. Org Config API Validation (`functions/org_config.py`)
**Current:** 25.0% | **Target:** 80% | **Gain:** +105 lines

**What to Test:**
- Config schema validation
- Nested config structures
- Config inheritance (global vs org)
- Type validation (strings, numbers, booleans, objects)
- Default values
- Required vs optional fields
- Config updates and merges
- Integration configs

**Test Additions:**
- ~17 new tests in `test_org_config_endpoints.py`
- Test all config types
- Test validation rules
- Test inheritance

---

### Phase 5B: Mid-Tier APIs + Services

#### 6. Permissions API (`functions/permissions.py`)
**Gain:** +81 lines | **Tests:** ~15

- Query permissions by user/role/form
- Permission grant/revoke flows
- Bulk permission operations
- Permission inheritance

#### 7. Workflow Keys API (`functions/workflow_keys.py`)
**Gain:** +72 lines | **Tests:** ~12

- Key generation and validation
- Key expiration handling
- Key revocation
- Key-based auth flow

#### 8. OAuth Refresh Timer (`functions/oauth_refresh_timer.py`)
**Gain:** +68 lines | **Tests:** ~10 (unit tests)

- Timer trigger handling
- Token refresh logic
- Batch processing
- Error handling and retries

#### 9. Workflows API (`functions/workflows.py`)
**Gain:** +65 lines | **Tests:** ~15

- Workflow listing and metadata
- Workflow execution triggering
- Parameter validation
- Execution status tracking

#### 10. Organizations API (`functions/organizations.py`)
**Gain:** +62 lines | **Tests:** ~15

- Organization CRUD
- Org settings management
- User assignments
- Org deactivation

#### 11. OAuth Provider Service (`services/oauth_provider.py`)
**Gain:** +55 lines | **Tests:** ~13 (unit tests)

- Provider-specific logic
- Token exchange
- Scope management
- Provider metadata

---

### Phase 5C: Supporting APIs + Infrastructure

#### 12. OpenAPI Metadata (`functions/openapi.py`)
**Gain:** +59 lines | **Tests:** ~10

- Spec generation
- Schema documentation
- Endpoint metadata
- Model definitions

#### 13. Executions API (`functions/executions.py`)
**Gain:** +53 lines | **Tests:** ~12

- Execution tracking
- Status updates
- Result storage
- Execution history

#### 14. Middleware Edge Cases (`shared/middleware.py`)
**Gain:** +51 lines | **Tests:** ~15

- More auth scenarios
- Request transformation
- Response formatting
- Error handling middleware

#### 15. Generic Endpoints (`functions/endpoints.py`)
**Gain:** +47 lines | **Tests:** ~13

- Endpoint utilities
- Common patterns
- Shared validation
- Response formatting

---

## Success Criteria

### Coverage Targets (Each Phase)
- **Phase 5A:** +867 lines → 66.5% overall coverage
- **Phase 5B:** +382 lines → 72.1% overall coverage
- **Phase 5C:** +219 lines → **75.5% overall coverage** ✅

### Quality Metrics
- ✅ All new tests passing (0 failures)
- ✅ Each file reaches 80%+ coverage
- ✅ Fast execution (< 30 seconds total)
- ✅ Integration tests use real HTTP
- ✅ Unit tests properly mocked

### Test Totals
- **Current:** 987 tests
- **Phase 5A:** +120 tests → 1,107 tests
- **Phase 5B:** +80 tests → 1,187 tests
- **Phase 5C:** +50 tests → **1,237 tests**
- **Total Added:** +250 tests

---

## Time Estimate

**With Parallel Execution (3 agents):**
- Phase 5A: 2-3 days
- Phase 5B: 2 days
- Phase 5C: 1-2 days
- **Total Elapsed:** ~3 days (parallel)

**Sequential Execution:**
- Total: ~6-7 days

**Recommendation:** Use 3 parallel code-executor agents for 3-day completion.

---

## Running Tests After Completion

```bash
# Full suite
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=. --cov-report=term-missing --cov-report=html

# Phase 5A tests only
python -m pytest tests/integration/api/test_oauth_edge_cases.py \
    tests/integration/api/test_forms_edge_cases.py \
    tests/integration/api/test_roles_edge_cases.py \
    tests/integration/api/test_secrets_endpoints.py \
    tests/integration/api/test_org_config_endpoints.py -v

# Phase 5B tests only
python -m pytest tests/integration/api/test_permissions_endpoints.py \
    tests/integration/api/test_workflow_keys_endpoints.py \
    tests/unit/test_oauth_refresh_timer.py \
    tests/integration/api/test_workflows_endpoints.py \
    tests/integration/api/test_organizations_endpoints.py \
    tests/unit/services/test_oauth_provider.py -v

# Phase 5C tests only
python -m pytest tests/unit/test_openapi.py \
    tests/integration/api/test_executions_endpoints.py \
    tests/unit/test_middleware.py \
    tests/integration/api/test_endpoints.py -v
```

---

## After 75%: Path to 90% (Optional)

If targeting 90% coverage later:
- **Current plan gets to:** 75.5%
- **Remaining to 90%:** +980 lines
- **Estimated effort:** 2-3 weeks
- **Focus areas:**
  - Workflow execution internals
  - Advanced OAuth scenarios
  - Complex error recovery
  - Performance edge cases

---

## Recommendation

**Start with Phase 5A** to get the biggest impact first. The top 5 files alone add +867 lines (60% of target). If you need to stop early, you'll still be at ~66.5% coverage.

**Ready to create detailed specs for Phases 5A, 5B, and 5C?** We can then launch 3 parallel code-executor agents to knock this out in 3 days!
