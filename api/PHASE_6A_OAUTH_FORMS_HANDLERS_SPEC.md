# Phase 6A: Extract OAuth & Forms Handlers

## Objective
Extract business logic from `oauth_api.py` (1463 lines) and `forms.py` (1034 lines) into unit-testable handler functions in `shared/handlers/`.

## Files to Refactor

### 1. oauth_api.py → shared/handlers/oauth_handlers.py

**Current Structure:**
- 19 endpoint functions with inline business logic
- ~1463 lines total
- All logic embedded in Azure Functions route handlers

**Target Structure:**
```python
# functions/oauth_api.py (after - ~200 lines)
from shared.handlers.oauth_handlers import (
    create_oauth_connection_handler,
    list_oauth_connections_handler,
    # ... all other handlers
)

@bp.route(route="oauth/connections", methods=["POST"])
@with_request_context
@require_platform_admin
async def create_oauth_connection(req: func.HttpRequest) -> func.HttpResponse:
    """Thin wrapper - just routing"""
    return await create_oauth_connection_handler(req)
```

```python
# shared/handlers/oauth_handlers.py (new - ~1300 lines)
async def create_oauth_connection_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Business logic for creating OAuth connection
    Unit testable - all dependencies can be mocked
    """
    context = get_context(req)
    org_id = context.scope

    try:
        request_body = req.get_json()
        create_request = CreateOAuthConnectionRequest(**request_body)
        oauth_service = OAuthStorageService()
        # ... all business logic here
        return func.HttpResponse(json.dumps(detail.model_dump(mode="json")),
                                status_code=201, mimetype="application/json")
    except ValidationError as e:
        # ... error handling
```

**Handlers to Extract (19 total):**
1. `create_oauth_connection_handler`
2. `list_oauth_connections_handler`
3. `get_oauth_connection_handler`
4. `update_oauth_connection_handler`
5. `delete_oauth_connection_handler`
6. `authorize_oauth_connection_handler`
7. `cancel_oauth_authorization_handler`
8. `oauth_callback_handler`
9. `get_oauth_credentials_handler`
10. `refresh_oauth_credentials_handler`
11. `get_refresh_job_status_handler`
12. `list_oauth_providers_handler`
13. `get_oauth_provider_handler`
14. `test_oauth_connection_handler`
15. `get_oauth_connection_status_handler`
16. `revoke_oauth_credentials_handler`
17. `get_oauth_scopes_handler`
18. `validate_oauth_config_handler`
19. `get_oauth_metadata_handler`

### 2. forms.py → shared/handlers/forms_handlers.py

**Current Structure:**
- 11 endpoint functions with inline business logic
- ~1034 lines total

**Handlers to Extract (11 total):**
1. `create_form_handler`
2. `list_forms_handler`
3. `get_form_handler`
4. `update_form_handler`
5. `delete_form_handler`
6. `form_startup_handler`
7. `form_execute_handler`
8. `upload_file_handler`
9. `get_form_schema_handler`
10. `validate_form_data_handler`
11. `get_form_submissions_handler`

## Implementation Steps

### Step 1: Create Handler Files
1. Create `shared/handlers/oauth_handlers.py`
2. Create `shared/handlers/forms_handlers.py`

### Step 2: Extract OAuth Handlers
For each endpoint in `oauth_api.py`:
1. Copy the entire function body (excluding decorators) to new handler function
2. Keep the async signature if it's async
3. Preserve all imports needed by the handler
4. Update the original function to call the handler:
   ```python
   async def create_oauth_connection(req: func.HttpRequest) -> func.HttpResponse:
       return await create_oauth_connection_handler(req)
   ```

### Step 3: Extract Forms Handlers
Same process for `forms.py`

### Step 4: Write Unit Tests

**Test File Structure:**
```
tests/unit/handlers/
├── conftest.py              # Shared fixtures
├── test_oauth_handlers.py   # OAuth handler tests
└── test_forms_handlers.py   # Forms handler tests
```

**Test Pattern for Async Handlers:**
```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from shared.handlers.oauth_handlers import create_oauth_connection_handler
import azure.functions as func

@pytest.mark.asyncio
async def test_create_oauth_connection_success():
    # Create mock request
    mock_req = Mock(spec=func.HttpRequest)
    mock_req.get_json.return_value = {
        "connection_name": "test-conn",
        "oauth_provider": "microsoft",
        "client_id": "test-client",
        "client_secret": "test-secret",
        "scopes": ["openid"]
    }

    # Mock context
    with patch('shared.handlers.oauth_handlers.get_context') as mock_ctx:
        mock_ctx.return_value = Mock(
            scope="org-123",
            email="admin@test.com",
            user_id="user-123"
        )

        # Mock OAuthStorageService
        with patch('shared.handlers.oauth_handlers.OAuthStorageService') as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.get_connection = AsyncMock(return_value=None)
            mock_svc.create_connection = AsyncMock(return_value=Mock(
                connection_id="conn-123",
                connection_name="test-conn",
                to_detail=lambda: Mock(model_dump=lambda mode: {
                    "connection_id": "conn-123",
                    "connection_name": "test-conn"
                })
            ))

            # Execute handler
            response = await create_oauth_connection_handler(mock_req)

            # Assertions
            assert response.status_code == 201
            assert response.mimetype == "application/json"
            mock_svc.create_connection.assert_called_once()

@pytest.mark.asyncio
async def test_create_oauth_connection_duplicate():
    """Test duplicate connection name handling"""
    mock_req = Mock(spec=func.HttpRequest)
    mock_req.get_json.return_value = {"connection_name": "existing", ...}

    with patch('shared.handlers.oauth_handlers.get_context') as mock_ctx:
        mock_ctx.return_value = Mock(scope="org-123", email="admin@test.com")

        with patch('shared.handlers.oauth_handlers.OAuthStorageService') as MockSvc:
            mock_svc = MockSvc.return_value
            # Simulate existing connection
            mock_svc.get_connection = AsyncMock(return_value=Mock(connection_name="existing"))

            response = await create_oauth_connection_handler(mock_req)

            assert response.status_code == 409
            # Should NOT attempt to create
            mock_svc.create_connection.assert_not_called()
```

**Test Coverage Requirements:**
- Test happy path for each handler
- Test validation errors (ValidationError, ValueError)
- Test business logic errors (duplicate names, not found, etc.)
- Test permission checks (if applicable)
- Test async service calls with AsyncMock
- Aim for 80%+ coverage of each handler file

**Fixtures Needed (conftest.py):**
```python
import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_http_request():
    """Mock Azure Functions HttpRequest"""
    def _make_request(json_data=None, params=None, headers=None):
        req = Mock(spec=func.HttpRequest)
        req.get_json.return_value = json_data or {}
        req.params = params or {}
        req.headers = headers or {}
        return req
    return _make_request

@pytest.fixture
def mock_request_context():
    """Mock RequestContext"""
    return Mock(
        scope="org-test",
        email="user@test.com",
        user_id="user-123",
        roles=["platform_admin"]
    )
```

## Test Coverage Targets

### OAuth Handlers Tests (~95 tests)
- `create_oauth_connection_handler`: 5 tests (success, duplicate, validation, json error, exception)
- `list_oauth_connections_handler`: 3 tests (success, empty, pagination)
- `get_oauth_connection_handler`: 3 tests (success, not found, exception)
- `update_oauth_connection_handler`: 5 tests (success, not found, validation, partial update, exception)
- `delete_oauth_connection_handler`: 3 tests (success, not found, idempotent)
- `authorize_oauth_connection_handler`: 6 tests (success, not found, already connected, state generation, PKCE, rate limit)
- `cancel_oauth_authorization_handler`: 3 tests (success, not found, no pending state)
- `oauth_callback_handler`: 8 tests (success, invalid state, expired state, missing code, provider error, state reuse, redirect, token exchange)
- `get_oauth_credentials_handler`: 4 tests (success, not found, not connected, masked)
- `refresh_oauth_credentials_handler`: 5 tests (success, not connected, expired token, provider error, status update)
- `get_refresh_job_status_handler`: 3 tests (success, not found, job status)
- `list_oauth_providers_handler`: 2 tests (success, empty)
- `get_oauth_provider_handler`: 2 tests (success, not found)
- `test_oauth_connection_handler`: 4 tests (success, not connected, test failure, credentials missing)
- Plus ~40 more for remaining handlers

### Forms Handlers Tests (~55 tests)
- `create_form_handler`: 5 tests (success, validation, duplicate, complex schema, exception)
- `list_forms_handler`: 3 tests (success, empty, filtering)
- `get_form_handler`: 3 tests (success, not found, exception)
- `update_form_handler`: 5 tests (success, not found, validation, version conflict, exception)
- `delete_form_handler`: 3 tests (success, not found, with submissions)
- `form_startup_handler`: 4 tests (success, not found, no workflow, GET method)
- `form_execute_handler`: 6 tests (success, not found, no workflow, validation, large payload, exception)
- `upload_file_handler`: 5 tests (success, missing fields, large file, invalid type, exception)
- Plus ~20 more for remaining handlers

## Completion Criteria

- [ ] `shared/handlers/oauth_handlers.py` created with 19 handler functions
- [ ] `shared/handlers/forms_handlers.py` created with 11 handler functions
- [ ] `functions/oauth_api.py` refactored to thin wrappers (~200 lines)
- [ ] `functions/forms.py` refactored to thin wrappers (~150 lines)
- [ ] `tests/unit/handlers/test_oauth_handlers.py` with ~95 tests
- [ ] `tests/unit/handlers/test_forms_handlers.py` with ~55 tests
- [ ] All tests pass (100%)
- [ ] Type checking passes (`npx pyright shared/handlers/`)
- [ ] Linting passes (`ruff check shared/handlers/`)
- [ ] Coverage of handlers >= 80%
- [ ] Integration tests still pass (no regressions)

## Estimated Impact
- **Lines of code refactored:** ~2500
- **New test coverage:** ~150 tests, ~1500 test lines
- **Expected coverage increase:** +8-10% (handlers now measurable)
