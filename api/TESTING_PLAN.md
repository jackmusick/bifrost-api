# Comprehensive Testing Plan to 90% Coverage

## Current State
- **Coverage: 38.63%** (2656/6876 lines)
- **Total Tests: 542** (118 contract, 73 integration, 351 unit)
- **Missing: 4220 lines**
- **Target: 90% = 6188 lines covered**
- **Need: +3532 lines coverage**

## Problem Analysis

### Why Coverage is Low Despite 542 Tests

1. **118 Contract Tests (22% of tests) = Low Value**
   - Test Pydantic model validation (Pydantic already does this)
   - Example: Testing that `WorkflowMetadata.executionMode = "async"` works
   - These tests cover ~500 lines of model definitions but don't test business logic
   - **Recommendation: Keep only tests for complex validation, remove simple field tests**
   - **Potential savings: Remove ~80-90 contract tests**

2. **Large API Endpoints Barely Tested**
   - `functions/oauth_api.py`: 464 lines, only 17.7% covered (382 lines missing)
   - `functions/forms.py`: 357 lines, only 15.4% covered (302 lines missing)
   - `functions/roles.py`: 255 lines, only 27.8% covered (184 lines missing)
   - **These are HTTP handlers that need integration tests**

3. **Infrastructure Code Untested**
   - OAuth services: 8-15% coverage
   - File services: 0% coverage (but likely not critical business logic)
   - Repositories: 12-27% coverage

## Strategic Testing Plan (90% Target)

### Phase 1: HIGH-IMPACT API ENDPOINTS (2 weeks)
**Target: +2000 lines | Effort: High | Value: Critical**

Create integration tests for main API endpoints using real HTTP:

#### Priority 1: OAuth & Auth (Week 1)
- `functions/oauth_api.py` (+300 lines)
  - Test OAuth connection flow
  - Test callback handling
  - Test refresh token logic
  - Test error scenarios

#### Priority 2: Forms & Workflows (Week 2)
- `functions/forms.py` (+240 lines)
  - Test form CRUD operations
  - Test field validation
  - Test file uploads
  - Test form submission with workflow launch

- `functions/roles.py` (+140 lines)
  - Test role assignment/revocation
  - Test permission checks
  - Test inheritance

- `functions/permissions.py` (+90 lines)
  - Test permission validation
  - Test cross-org access denial

**Integration Test Pattern:**
```python
# Use func start + requests library
def test_oauth_flow_complete():
    # Start OAuth connection
    response = requests.post(
        "http://localhost:7071/api/oauth/connect",
        json={"provider": "microsoft", "org_id": "test-org"}
    )
    assert response.status_code == 200

    # Follow redirect, simulate OAuth callback
    # Verify connection stored
    # Test refresh flow
```

### Phase 2: REPOSITORIES & DATA ACCESS (1 week)
**Target: +800 lines | Effort: Medium | Value: High**

Unit tests for repository classes with mocked storage:

#### Priority Files
- `shared/repositories/forms.py` (+120 lines)
- `shared/repositories/roles.py` (+95 lines)
- `shared/repositories/organizations.py` (+50 lines)
- `shared/repositories/config.py` (+48 lines)
- `shared/repositories/users.py` (+40 lines)
- `shared/repositories/executions.py` (+60 lines)

**Unit Test Pattern:**
```python
@pytest.fixture
def mock_table_service():
    with patch('shared.repositories.base.TableStorageService') as mock:
        yield mock

def test_forms_repository_create(mock_table_service):
    repo = FormsRepository()
    form_data = {"name": "test", "org_id": "org-123"}

    result = repo.create_form(form_data)

    mock_table_service.return_value.insert_entity.assert_called_once()
    assert result.name == "test"
```

### Phase 3: SERVICES & UTILITIES (1 week)
**Target: +600 lines | Effort: Medium | Value: Medium**

#### Priority Services
- `services/oauth_storage_service.py` (+165 lines)
  - Test connection storage/retrieval
  - Test token encryption/decryption
  - Test refresh logic

- `shared/blob_storage.py` (+107 lines)
  - Test file upload/download
  - Test large file handling
  - Test error scenarios

- `shared/keyvault.py` (+98 lines)
  - Test secret storage/retrieval (mock Key Vault)
  - Test encryption
  - Test access control

**Skip Low-Value Services:**
- `services/temp_file_service.py` - File utilities, low business value
- `services/zip_service.py` - Zip utilities, low business value
- `services/workspace_service.py` - Workspace management, low risk

### Phase 4: FILL COVERAGE GAPS (3-5 days)
**Target: +500 lines | Effort: Low | Value: Medium**

Improve existing tests to hit edge cases:

- Error handling paths in well-tested modules
- Validation edge cases
- Exception scenarios
- Boundary conditions

**Files to target:**
- `shared/middleware.py` (+60 lines to 80%)
- `shared/auth.py` (+55 lines to 85%)
- `shared/context.py` (+60 lines to 80%)
- `shared/models.py` (+50 lines to 95%)

### Phase 5: CLEANUP CONTRACT TESTS (1 day)
**Target: Remove ~90 tests | Effort: Low | Value: Cleaner codebase**

**Remove simple Pydantic validation tests:**

Examples to DELETE:
```python
def test_workflow_metadata_with_async_flag(self):
    """Pydantic already validates this"""
    metadata = WorkflowMetadata(
        name="long_running_workflow",
        description="Long running workflow",
        executionMode="async"
    )
    assert metadata.executionMode == "async"  # No value

def test_workflow_key_with_all_fields(self):
    """Just testing Pydantic field assignment"""
    key = WorkflowKey(
        id="key-123",
        org_id="org-456",
        name="Test Key",
        # ... all fields
    )
    assert key.name == "Test Key"  # Pydantic already does this
```

**Keep complex validation tests:**
```python
def test_datetime_field_with_validation(self):
    """Tests custom validation logic"""
    with pytest.raises(ValidationError):
        FormField(type="datetime", validation={"min": "invalid"})
```

**Estimated savings:** Remove 80-90 tests (15-16% of test suite)

## Exclusions from Coverage

Add to `.coveragerc`:

```ini
[run]
omit =
    # Development scripts (not production code)
    clear_data.py
    seed_data.py
    analyze_coverage.py

    # Test files
    tests/*

    # Workspace examples (user code, not platform code)
    workspace/examples/*
```

After exclusions, effective coverage = ~41-42% (better baseline)

## Summary Table

| Phase | Target Lines | Effort | Timeline | Priority |
|-------|-------------|--------|----------|----------|
| Phase 1: API Endpoints | +2000 | High | 2 weeks | Critical |
| Phase 2: Repositories | +800 | Medium | 1 week | High |
| Phase 3: Services | +600 | Medium | 1 week | Medium |
| Phase 4: Fill Gaps | +500 | Low | 3-5 days | Medium |
| **TOTAL** | **+3900** | | **4-5 weeks** | |
| **Contract Cleanup** | Remove 90 tests | Low | 1 day | Cleanup |

**Projected Coverage: ~94%** (6556/6876 lines)

## Immediate Next Steps

1. **Today:**
   - Create `.coveragerc` to exclude dev scripts
   - Re-run coverage to get clean baseline

2. **This Week:**
   - Start Phase 1: OAuth integration tests
   - Set up testing infrastructure (Docker, Azurite, etc.) ✅ (DONE)

3. **Document Testing Patterns:**
   - Integration test template
   - Repository unit test template
   - Mocking strategy guide

## ROI Analysis

**Effort vs Value:**

| Category | Effort | Lines | ROI | Recommendation |
|----------|--------|-------|-----|----------------|
| API Integration Tests | High | 2000 | ⭐⭐⭐⭐⭐ | DO FIRST |
| Repository Unit Tests | Medium | 800 | ⭐⭐⭐⭐ | DO SECOND |
| Service Tests | Medium | 600 | ⭐⭐⭐ | DO THIRD |
| Gap Filling | Low | 500 | ⭐⭐⭐ | DO FOURTH |
| Contract Test Cleanup | Low | -90 tests | ⭐⭐⭐⭐ | DO ANYTIME |
| File Service Tests | Medium | 200 | ⭐ | SKIP |

**Files to SKIP Testing (Low Business Value):**
- `services/temp_file_service.py` (69 lines) - Basic file operations
- `services/zip_service.py` (57 lines) - Zip utilities
- `services/workspace_service.py` (82 lines) - File management
- `workspace/examples/*` - User-provided code

**Total skippable: ~200 lines**

## Key Principles

1. **Test Business Logic, Not Frameworks**
   - Don't test that Pydantic validates fields
   - Don't test that Azure Functions routes work
   - Test YOUR business rules and workflows

2. **Integration > Unit for APIs**
   - API endpoints need integration tests (real HTTP)
   - Business logic needs unit tests (mocked dependencies)
   - Models need contract tests only for complex validation

3. **Focus on High-Risk, High-Value Code**
   - OAuth flows (security critical)
   - Permission checks (security critical)
   - Workflow execution (core business value)
   - Data access (data integrity)

4. **Acceptable Coverage by Layer**
   - API Endpoints (functions/): Target 80%
   - Business Logic (shared/): Target 90%
   - Repositories: Target 85%
   - Models: Target 95%
   - Services: Target 70% (lower priority)
   - Dev Scripts: 0% (excluded)

## Maintenance Strategy

**After reaching 90%:**

1. **Enforce coverage in CI/CD:**
   ```yaml
   - name: Test with coverage
     run: pytest --cov --cov-fail-under=90
   ```

2. **New code must maintain coverage:**
   - PRs cannot decrease coverage
   - New endpoints need integration tests
   - New repositories need unit tests

3. **Quarterly review:**
   - Identify new coverage gaps
   - Remove obsolete tests
   - Update testing strategy
