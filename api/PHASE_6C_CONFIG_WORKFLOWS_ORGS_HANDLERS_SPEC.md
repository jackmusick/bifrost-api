# Phase 6C: Extract Config, Workflows & Organizations Handlers

## Objective
Extract business logic from `org_config.py` (572 lines), `workflow_keys.py` (451 lines), `workflows.py` (450 lines), and `organizations.py` (380 lines) into unit-testable handler functions in `shared/handlers/`.

## Files to Refactor

### 1. org_config.py → shared/handlers/org_config_handlers.py

**Current Structure:**
- 8 endpoint functions with inline business logic
- ~572 lines total

**Handlers to Extract (8 total):**
1. `get_config_handler`
2. `set_config_handler`
3. `delete_config_handler`
4. `get_integrations_handler`
5. `set_integration_handler`
6. `delete_integration_handler`
7. `validate_config_schema_handler`
8. `get_config_metadata_handler`

### 2. workflow_keys.py → shared/handlers/workflow_keys_handlers.py

**Current Structure:**
- 8 endpoint functions with inline business logic
- ~451 lines total

**Handlers to Extract (8 total):**
1. `create_workflow_key_handler`
2. `list_workflow_keys_handler`
3. `get_workflow_key_handler`
4. `delete_workflow_key_handler`
5. `rotate_workflow_key_handler`
6. `validate_workflow_key_handler`
7. `get_workflow_key_usage_handler`
8. `update_workflow_key_metadata_handler`

### 3. workflows.py → shared/handlers/workflows_handlers.py

**Current Structure:**
- 9 endpoint functions with inline business logic
- ~450 lines total

**Handlers to Extract (9 total):**
1. `create_workflow_handler`
2. `list_workflows_handler`
3. `get_workflow_handler`
4. `update_workflow_handler`
5. `delete_workflow_handler`
6. `execute_workflow_handler`
7. `get_workflow_execution_handler`
8. `list_workflow_executions_handler`
9. `cancel_workflow_execution_handler`

### 4. organizations.py → shared/handlers/organizations_handlers.py

**Current Structure:**
- 7 endpoint functions with inline business logic
- ~380 lines total

**Handlers to Extract (7 total):**
1. `create_organization_handler`
2. `list_organizations_handler`
3. `get_organization_handler`
4. `update_organization_handler`
5. `delete_organization_handler`
6. `get_organization_members_handler`
7. `update_organization_settings_handler`

## Implementation Pattern

### Step 1: Create Handler Files
```bash
touch shared/handlers/org_config_handlers.py
touch shared/handlers/workflow_keys_handlers.py
touch shared/handlers/workflows_handlers.py
touch shared/handlers/organizations_handlers.py
```

### Step 2: Extract Handler Functions

**Example - workflows.py:**

**Before:**
```python
# functions/workflows.py
@bp.route(route="workflows/{workflow_id}/execute", methods=["POST"])
@with_request_context
async def execute_workflow(req: func.HttpRequest) -> func.HttpResponse:
    context = get_context(req)
    workflow_id = get_route_param(req, "workflow_id")

    try:
        # ... 80 lines of business logic
        # Get workflow, validate, execute, handle async, etc.
        return func.HttpResponse(json.dumps(result.model_dump()), status_code=200, ...)
    except Exception as e:
        # ... error handling
```

**After:**
```python
# functions/workflows.py (~60 lines total)
from shared.handlers.workflows_handlers import execute_workflow_handler

@bp.route(route="workflows/{workflow_id}/execute", methods=["POST"])
@with_request_context
async def execute_workflow(req: func.HttpRequest) -> func.HttpResponse:
    return await execute_workflow_handler(req)

# shared/handlers/workflows_handlers.py
async def execute_workflow_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Execute workflow - unit testable business logic"""
    context = get_context(req)
    workflow_id = get_route_param(req, "workflow_id")

    try:
        # ... all 80 lines of business logic
        return func.HttpResponse(json.dumps(result.model_dump()), status_code=200, ...)
    except Exception as e:
        # ... error handling
```

### Step 3: Write Unit Tests

**Test File Structure:**
```
tests/unit/handlers/
├── test_org_config_handlers.py
├── test_workflow_keys_handlers.py
├── test_workflows_handlers.py
└── test_organizations_handlers.py
```

**Test Pattern - Org Config:**
```python
# tests/unit/handlers/test_org_config_handlers.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
import azure.functions as func
from shared.handlers.org_config_handlers import set_config_handler

@pytest.mark.asyncio
async def test_set_config_string_type():
    """Test setting string config value"""
    mock_req = Mock(spec=func.HttpRequest)
    mock_req.get_json.return_value = {
        "key": "api_endpoint",
        "value": "https://api.example.com",
        "type": "string",
        "description": "API endpoint URL"
    }

    with patch('shared.handlers.org_config_handlers.get_context') as mock_ctx:
        mock_ctx.return_value = Mock(scope="org-123", user_id="user-123")

        with patch('shared.handlers.org_config_handlers.ConfigRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.set_config_value = AsyncMock()

            response = await set_config_handler(mock_req)

            assert response.status_code == 200
            mock_repo.set_config_value.assert_called_once_with(
                key="api_endpoint",
                value="https://api.example.com",
                config_type="string",
                description="API endpoint URL"
            )

@pytest.mark.asyncio
async def test_set_config_with_validation():
    """Test config validation against schema"""
    mock_req = Mock(spec=func.HttpRequest)
    mock_req.get_json.return_value = {
        "key": "max_retries",
        "value": "5",
        "type": "number",
        "validation": {"min": 0, "max": 10}
    }

    with patch('shared.handlers.org_config_handlers.get_context') as mock_ctx:
        mock_ctx.return_value = Mock(scope="org-123")

        with patch('shared.handlers.org_config_handlers.ConfigRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.validate_config_value = AsyncMock(return_value=True)
            mock_repo.set_config_value = AsyncMock()

            response = await set_config_handler(mock_req)

            assert response.status_code == 200
            mock_repo.validate_config_value.assert_called_once()

@pytest.mark.asyncio
async def test_get_config_with_global_fallback():
    """Test org-specific config with global fallback"""
    mock_req = Mock(spec=func.HttpRequest)
    mock_req.params = {"key": "feature_flag"}

    with patch('shared.handlers.org_config_handlers.get_context') as mock_ctx:
        mock_ctx.return_value = Mock(scope="org-123")

        with patch('shared.handlers.org_config_handlers.ConfigRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            # Org-specific config not found, returns global default
            mock_repo.get_config_value = AsyncMock(return_value=Mock(
                key="feature_flag",
                value="true",
                source="GLOBAL"
            ))

            response = await get_config_handler(mock_req)

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert data["source"] == "GLOBAL"
```

**Test Pattern - Workflow Keys:**
```python
@pytest.mark.asyncio
async def test_create_workflow_key_generates_secure_key():
    """Test workflow key generation with cryptographic security"""
    mock_req = Mock(spec=func.HttpRequest)
    mock_req.get_json.return_value = {
        "workflow_id": "wf-123",
        "description": "Production key",
        "expires_at": "2025-12-31T23:59:59Z"
    }

    with patch('shared.handlers.workflow_keys_handlers.get_context') as mock_ctx:
        mock_ctx.return_value = Mock(scope="org-123", user_id="user-123")

        with patch('shared.handlers.workflow_keys_handlers.WorkflowKeysRepository') as MockRepo:
            with patch('shared.handlers.workflow_keys_handlers.secrets.token_urlsafe') as mock_token:
                mock_token.return_value = "secure-random-key-abc123"
                mock_repo = MockRepo.return_value
                mock_repo.create_workflow_key = AsyncMock(return_value=Mock(
                    key_id="key-123",
                    workflow_id="wf-123",
                    key_value="wfk_secure-random-key-abc123"
                ))

                response = await create_workflow_key_handler(mock_req)

                assert response.status_code == 201
                assert mock_token.called
                data = json.loads(response.get_body())
                assert data["key_value"].startswith("wfk_")

@pytest.mark.asyncio
async def test_rotate_workflow_key_invalidates_old():
    """Test key rotation creates new key and invalidates old"""
    mock_req = Mock(spec=func.HttpRequest)
    key_id = "key-123"

    with patch('shared.handlers.workflow_keys_handlers.get_context') as mock_ctx:
        with patch('shared.handlers.workflow_keys_handlers.get_route_param') as mock_param:
            mock_param.return_value = key_id
            mock_ctx.return_value = Mock(scope="org-123")

            with patch('shared.handlers.workflow_keys_handlers.WorkflowKeysRepository') as MockRepo:
                mock_repo = MockRepo.return_value
                old_key = Mock(key_id=key_id, workflow_id="wf-123")
                mock_repo.get_workflow_key = AsyncMock(return_value=old_key)
                mock_repo.invalidate_key = AsyncMock()
                mock_repo.create_workflow_key = AsyncMock(return_value=Mock(
                    key_id="key-456",
                    workflow_id="wf-123"
                ))

                response = await rotate_workflow_key_handler(mock_req)

                assert response.status_code == 201
                mock_repo.invalidate_key.assert_called_once_with(key_id)
                mock_repo.create_workflow_key.assert_called_once()
```

**Test Pattern - Workflows:**
```python
@pytest.mark.asyncio
async def test_execute_workflow_async_mode():
    """Test async workflow execution via queue"""
    mock_req = Mock(spec=func.HttpRequest)
    mock_req.get_json.return_value = {"input": "test-data"}

    with patch('shared.handlers.workflows_handlers.get_context') as mock_ctx:
        with patch('shared.handlers.workflows_handlers.get_route_param') as mock_param:
            mock_param.return_value = "wf-123"
            mock_ctx.return_value = Mock(scope="org-123")

            with patch('shared.handlers.workflows_handlers.WorkflowRegistry') as MockReg:
                workflow = Mock(name="test-workflow", is_async=True)
                MockReg.get_workflow.return_value = workflow

                with patch('shared.handlers.workflows_handlers.enqueue_workflow') as mock_enqueue:
                    mock_enqueue.return_value = Mock(execution_id="exec-123", status="queued")

                    response = await execute_workflow_handler(mock_req)

                    assert response.status_code == 202  # Accepted
                    mock_enqueue.assert_called_once()
                    data = json.loads(response.get_body())
                    assert data["execution_id"] == "exec-123"
                    assert data["status"] == "queued"

@pytest.mark.asyncio
async def test_execute_workflow_sync_mode():
    """Test synchronous workflow execution"""
    mock_req = Mock(spec=func.HttpRequest)
    mock_req.get_json.return_value = {"input": "test-data"}

    with patch('shared.handlers.workflows_handlers.get_context') as mock_ctx:
        with patch('shared.handlers.workflows_handlers.get_route_param') as mock_param:
            mock_param.return_value = "wf-123"
            mock_ctx.return_value = Mock(scope="org-123")

            with patch('shared.handlers.workflows_handlers.WorkflowRegistry') as MockReg:
                workflow = Mock(name="test-workflow", is_async=False, execute=AsyncMock(
                    return_value={"result": "success"}
                ))
                MockReg.get_workflow.return_value = workflow

                response = await execute_workflow_handler(mock_req)

                assert response.status_code == 200
                workflow.execute.assert_called_once()
                data = json.loads(response.get_body())
                assert data["result"] == "success"
```

**Test Pattern - Organizations:**
```python
@pytest.mark.asyncio
async def test_create_organization_with_domain():
    """Test organization creation with domain auto-assignment"""
    mock_req = Mock(spec=func.HttpRequest)
    mock_req.get_json.return_value = {
        "name": "Test Corp",
        "domain": "testcorp.com",
        "settings": {"allow_msp_management": False}
    }

    with patch('shared.handlers.organizations_handlers.get_context') as mock_ctx:
        mock_ctx.return_value = Mock(scope="GLOBAL", user_id="user-123", roles=["platform_admin"])

        with patch('shared.handlers.organizations_handlers.OrganizationsRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_domain = AsyncMock(return_value=None)  # Domain available
            mock_repo.create_organization = AsyncMock(return_value=Mock(
                organization_id="org-new",
                name="Test Corp",
                domain="testcorp.com"
            ))

            response = await create_organization_handler(mock_req)

            assert response.status_code == 201
            mock_repo.get_by_domain.assert_called_once_with("testcorp.com")
            mock_repo.create_organization.assert_called_once()

@pytest.mark.asyncio
async def test_update_organization_settings():
    """Test updating organization settings"""
    mock_req = Mock(spec=func.HttpRequest)
    mock_req.get_json.return_value = {
        "allow_msp_management": True,
        "tenant_type": "msp"
    }

    with patch('shared.handlers.organizations_handlers.get_context') as mock_ctx:
        with patch('shared.handlers.organizations_handlers.get_route_param') as mock_param:
            mock_param.return_value = "org-123"
            mock_ctx.return_value = Mock(scope="GLOBAL", roles=["platform_admin"])

            with patch('shared.handlers.organizations_handlers.OrganizationsRepository') as MockRepo:
                mock_repo = MockRepo.return_value
                mock_repo.get_organization = AsyncMock(return_value=Mock(organization_id="org-123"))
                mock_repo.update_settings = AsyncMock()

                response = await update_organization_settings_handler(mock_req)

                assert response.status_code == 200
                mock_repo.update_settings.assert_called_once()
```

## Test Coverage Targets

### Org Config Handlers Tests (~40 tests)
- `get_config_handler`: 4 tests (success, not found, global fallback, exception)
- `set_config_handler`: 6 tests (string, number, boolean, object, validation, exception)
- `delete_config_handler`: 3 tests (success, not found, cascade)
- `get_integrations_handler`: 3 tests (success, empty, filtered)
- `set_integration_handler`: 5 tests (oauth, email, sso, validation, exception)
- `delete_integration_handler`: 3 tests (success, not found, in use)
- Plus ~16 more for remaining handlers

### Workflow Keys Handlers Tests (~40 tests)
- `create_workflow_key_handler`: 5 tests (success, secure generation, expiration, validation, exception)
- `list_workflow_keys_handler`: 3 tests (success, empty, by workflow)
- `get_workflow_key_handler`: 3 tests (success, not found, masked)
- `delete_workflow_key_handler`: 3 tests (success, not found, cascade)
- `rotate_workflow_key_handler`: 5 tests (success, invalidate old, generate new, not found, exception)
- `validate_workflow_key_handler`: 4 tests (valid, invalid, expired, not found)
- Plus ~17 more for remaining handlers

### Workflows Handlers Tests (~45 tests)
- `create_workflow_handler`: 5 tests (success, validation, duplicate, permissions, exception)
- `list_workflows_handler`: 3 tests (success, empty, filtering)
- `get_workflow_handler`: 3 tests (success, not found, exception)
- `update_workflow_handler`: 5 tests (success, not found, validation, version conflict, exception)
- `delete_workflow_handler`: 4 tests (success, not found, in use, cascade)
- `execute_workflow_handler`: 6 tests (async mode, sync mode, validation, not found, queue failure, exception)
- Plus ~19 more for remaining handlers

### Organizations Handlers Tests (~35 tests)
- `create_organization_handler`: 5 tests (success, with domain, duplicate domain, validation, exception)
- `list_organizations_handler`: 3 tests (success, empty, filtering)
- `get_organization_handler`: 3 tests (success, not found, exception)
- `update_organization_handler`: 5 tests (success, not found, validation, partial, exception)
- `delete_organization_handler`: 4 tests (success, not found, has members, cascade)
- Plus ~15 more for remaining handlers

## Completion Criteria

- [ ] `shared/handlers/org_config_handlers.py` created with 8 handler functions (~520 lines)
- [ ] `shared/handlers/workflow_keys_handlers.py` created with 8 handler functions (~420 lines)
- [ ] `shared/handlers/workflows_handlers.py` created with 9 handler functions (~410 lines)
- [ ] `shared/handlers/organizations_handlers.py` created with 7 handler functions (~350 lines)
- [ ] `functions/org_config.py` refactored to thin wrappers (~70 lines)
- [ ] `functions/workflow_keys.py` refactored to thin wrappers (~65 lines)
- [ ] `functions/workflows.py` refactored to thin wrappers (~70 lines)
- [ ] `functions/organizations.py` refactored to thin wrappers (~60 lines)
- [ ] `tests/unit/handlers/test_org_config_handlers.py` with ~40 tests
- [ ] `tests/unit/handlers/test_workflow_keys_handlers.py` with ~40 tests
- [ ] `tests/unit/handlers/test_workflows_handlers.py` with ~45 tests
- [ ] `tests/unit/handlers/test_organizations_handlers.py` with ~35 tests
- [ ] All tests pass (100%)
- [ ] Type checking passes (`npx pyright shared/handlers/`)
- [ ] Linting passes (`ruff check shared/handlers/`)
- [ ] Coverage of handlers >= 80%
- [ ] Integration tests still pass (no regressions)

## Estimated Impact
- **Lines of code refactored:** ~1853
- **New test coverage:** ~160 tests, ~1600 test lines
- **Expected coverage increase:** +5-7% (handlers now measurable)
