# Phase 6A Implementation Plan: Extract OAuth & Forms Handlers

## Overview
Refactor ~2500 lines of business logic from `oauth_api.py` (1463 lines) and `forms.py` (1034 lines) into unit-testable handler functions. This plan details exactly which functions to extract and how to structure the handlers.

## Part 1: OAuth Handlers Extraction

### Target: `shared/handlers/oauth_handlers.py` (~1300 lines)

#### Handler Functions (11 total - smaller than spec due to code analysis)

1. **create_oauth_connection_handler(req: HttpRequest) -> HttpResponse**
   - Lines: 59-137 in oauth_api.py
   - Logic: Validate request, check duplicate, call oauth_service.create_connection(), return detail
   - Test cases: success, duplicate conflict (409), validation error (400), JSON parse error, exception

2. **list_oauth_connections_handler(req: HttpRequest) -> HttpResponse**
   - Lines: 160-193 in oauth_api.py
   - Logic: Call oauth_service.list_connections(), convert to summaries, return list
   - Test cases: success with multiple, empty list, exception

3. **get_oauth_connection_handler(req: HttpRequest) -> HttpResponse**
   - Lines: 224-266 in oauth_api.py
   - Logic: Get connection_name from route, call oauth_service.get_connection(), return detail or 404
   - Test cases: success, not found (404), exception

4. **update_oauth_connection_handler(req: HttpRequest) -> HttpResponse**
   - Lines: 298-376 in oauth_api.py
   - Logic: Parse request, call oauth_service.update_connection(), return detail or 404
   - Test cases: success, not found (404), validation error (400), JSON error, exception

5. **delete_oauth_connection_handler(req: HttpRequest) -> HttpResponse**
   - Lines: 408-441 in oauth_api.py
   - Logic: Call oauth_service.delete_connection(), return 204 (idempotent)
   - Test cases: success, not found (idempotent), exception

6. **authorize_oauth_connection_handler(req: HttpRequest) -> HttpResponse**
   - Lines: 475-568 in oauth_api.py
   - Logic: Get connection, validate not client_credentials, generate state, build auth URL, update status to waiting_callback, return authorization_url
   - Test cases: success, not found (404), client_credentials error (400), exception

7. **cancel_oauth_authorization_handler(req: HttpRequest) -> HttpResponse**
   - Lines: 600-649 in oauth_api.py
   - Logic: Get connection, reset to not_connected status, return 204
   - Test cases: success, not found (404), exception

8. **refresh_oauth_token_handler(req: HttpRequest) -> HttpResponse**
   - Lines: 679-916 in oauth_api.py
   - Logic: Get connection, validate completed status, retrieve tokens from KeyVault, call oauth_provider.refresh_access_token(), store new tokens, update status
   - Test cases: success, not found (404), not connected (400), KeyVault unavailable (503), no refresh token (400), refresh failed (400), exception

9. **oauth_callback_handler(req: HttpRequest) -> HttpResponse**
   - Lines: 951-1160 in oauth_api.py
   - Logic: Extract code from POST body, get connection, validate code, exchange for token, test connection, store tokens, update status
   - Test cases: success, connection not found (404), missing code (400), token exchange failed, connection test failed, exception

10. **get_oauth_credentials_handler(req: HttpRequest) -> HttpResponse**
    - Lines: 1198-1369 in oauth_api.py
    - Logic: Get connection, check completed status, retrieve tokens from KeyVault, return credentials response
    - Test cases: success, not found (404), not completed status (return empty), KeyVault unavailable (503), exception

11. **get_oauth_refresh_job_status_handler(req: HttpRequest) -> HttpResponse**
    - Lines: 1394-1463 in oauth_api.py
    - Logic: Query Config table for job status, parse errors JSON, return status object or empty if not run
    - Test cases: success with data, no job run yet, exception

### Key Implementation Details for oauth_handlers.py

**Imports to include:**
```python
import json
import logging
import uuid
from datetime import datetime
from urllib.parse import urlencode

import azure.functions as func
from pydantic import ValidationError

from models.oauth_connection import (
    CreateOAuthConnectionRequest,
    OAuthConnectionDetail,
    OAuthCredentials,
    OAuthCredentialsResponse,
    UpdateOAuthConnectionRequest,
)
from services.oauth_provider import OAuthProviderClient
from services.oauth_storage_service import OAuthStorageService
from services.oauth_test_service import OAuthTestService
from shared.custom_types import get_context, get_route_param
from shared.keyvault import KeyVaultClient
from shared.models import ErrorResponse, OAuthCallbackRequest, OAuthCallbackResponse
from shared.storage import TableStorageService

logger = logging.getLogger(__name__)
```

**Error Handling Pattern:**
All handlers follow this pattern:
1. Get context and route params
2. Validate and parse request (catch ValidationError, ValueError)
3. Execute business logic (wrapped in try-except)
4. Return appropriate HTTP response with status code
5. Catch all exceptions and return 500 InternalServerError

**Example structure:**
```python
async def handler_name_handler(req: func.HttpRequest) -> func.HttpResponse:
    context = get_context(req)
    org_id = context.scope

    logger.info(f"Handler: {context.email}")

    try:
        # Business logic here
        pass
    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        error = ErrorResponse(...)
        return func.HttpResponse(json.dumps(...), status_code=400, ...)
    except ValueError as e:
        logger.error(f"Parse error: {e}")
        return func.HttpResponse(json.dumps(...), status_code=400, ...)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        error = ErrorResponse(...)
        return func.HttpResponse(json.dumps(...), status_code=500, ...)
```

---

## Part 2: Forms Handlers Extraction

### Target: `shared/handlers/forms_handlers.py` (~900 lines)

#### Handler Functions (8 total)

1. **list_forms_handler(req: HttpRequest) -> HttpResponse**
   - Lines: 111-139 in forms.py
   - Logic: Call get_user_visible_forms(context), sort by name, return list
   - Test cases: success with multiple forms, empty list, exception

2. **create_form_handler(req: HttpRequest) -> HttpResponse**
   - Lines: 162-247 in forms.py
   - Logic: Parse request, validate launch workflow params, call form_repo.create_form(), return form
   - Test cases: success, duplicate (if applicable), validation error (400), JSON error, exception

3. **get_form_handler(req: HttpRequest) -> HttpResponse**
   - Lines: 274-343 in forms.py
   - Logic: Get form_id from route, call form_repo.get_form(), check active and permissions, return form or 404/403
   - Test cases: success, not found (404), not active (404), no permission (403), exception

4. **update_form_handler(req: HttpRequest) -> HttpResponse**
   - Lines: 372-491 in forms.py
   - Logic: Parse request, get existing form, merge and validate launch workflow params, call form_repo.update_form(), return updated form
   - Test cases: success, partial update, not found (404), validation error (400), JSON error, exception

5. **delete_form_handler(req: HttpRequest) -> HttpResponse**
   - Lines: 518-548 in forms.py
   - Logic: Call form_repo.delete_form(), return 204 (idempotent)
   - Test cases: success, not found (idempotent), exception

6. **execute_form_startup_handler(req: HttpRequest) -> HttpResponse**
   - Lines: 590-781 in forms.py
   - Logic: Check form access permission, get form, validate active, execute launch workflow with merged params, return workflow result
   - Test cases: success, not found (404), not active (404), no permission (403), no launch workflow (return empty), missing required params (400), workflow error, exception

7. **execute_form_handler(req: HttpRequest) -> HttpResponse**
   - Lines: 827-1034 in forms.py
   - Logic: Check execute permission, get form, validate active, execute linked workflow, create/update execution record, return execution result
   - Test cases: success, not found (404), not active (404), no permission (403), no linked workflow, invalid JSON (400), workflow error, execution record creation, exception

8. **validate_launch_workflow_params_handler(...) -> str | None**
   - Lines: 35-88 in forms.py
   - Logic: Get workflow from registry, check each required param has either default value or query param field
   - Already extracted as standalone function, just move to handlers
   - Test cases: no workflow error, valid params, missing params

### Key Implementation Details for forms_handlers.py

**Imports to include:**
```python
import json
import logging
from datetime import datetime

import azure.functions as func
from pydantic import ValidationError

from shared.authorization import can_user_execute_form, can_user_view_form, get_user_visible_forms
from shared.error_handling import WorkflowError
from shared.middleware import with_org_context
from shared.models import (
    CreateFormRequest,
    ErrorResponse,
    Form,
    FormExecuteRequest,
    FormStartupResponse,
    UpdateFormRequest,
    ExecutionStatus,
)
from shared.repositories.forms import FormRepository
from shared.execution_logger import get_execution_logger
from shared.registry import get_registry

logger = logging.getLogger(__name__)
```

**Special considerations:**
- Forms handlers need both RequestContext and OrganizationContext
- RequestContext comes from @with_request_context decorator
- OrganizationContext comes from @with_org_context decorator
- Handlers receive req.context and req.org_context (set by decorators)
- Need to handle hot-reload by calling discover_workspace_modules()
- Execution logging via get_execution_logger()

---

## Part 3: Refactor API Functions

### Update `functions/oauth_api.py` (~200 lines after)

Replace each function body with a single call to handler:

```python
@bp.function_name("oauth_create_connection")
@bp.route(route="oauth/connections", methods=["POST"])
@openapi_endpoint(...)
@with_request_context
@require_platform_admin
async def create_oauth_connection(req: func.HttpRequest) -> func.HttpResponse:
    """..."""
    return await create_oauth_connection_handler(req)
```

Import all handlers at top:
```python
from shared.handlers.oauth_handlers import (
    create_oauth_connection_handler,
    list_oauth_connections_handler,
    get_oauth_connection_handler,
    update_oauth_connection_handler,
    delete_oauth_connection_handler,
    authorize_oauth_connection_handler,
    cancel_oauth_authorization_handler,
    refresh_oauth_token_handler,
    oauth_callback_handler,
    get_oauth_credentials_handler,
    get_oauth_refresh_job_status_handler,
)
```

### Update `functions/forms.py` (~150 lines after)

Same pattern - keep decorators, replace body with handler call:

```python
@bp.function_name("forms_list_forms")
@bp.route(route="forms", methods=["GET"])
@openapi_endpoint(...)
@with_request_context
async def list_forms(req: func.HttpRequest) -> func.HttpResponse:
    """..."""
    return await list_forms_handler(req)
```

Import handlers:
```python
from shared.handlers.forms_handlers import (
    validate_launch_workflow_params,
    list_forms_handler,
    create_form_handler,
    get_form_handler,
    update_form_handler,
    delete_form_handler,
    execute_form_startup_handler,
    execute_form_handler,
)
```

---

## Part 4: Test Structure

### File: `tests/unit/handlers/conftest.py`

**Shared fixtures:**
```python
import pytest
from unittest.mock import Mock, AsyncMock
import azure.functions as func

@pytest.fixture
def mock_http_request():
    """Create mock Azure Functions HttpRequest"""
    def _make_request(json_data=None, params=None, headers=None, method="POST", route_params=None):
        req = Mock(spec=func.HttpRequest)
        req.get_json.return_value = json_data or {}
        req.params = params or {}
        req.headers = headers or {}
        req.method = method
        req.route_params = route_params or {}
        req.url = "https://example.com/api/endpoint"
        return req
    return _make_request

@pytest.fixture
def mock_request_context():
    """Mock RequestContext"""
    return Mock(
        scope="org-test",
        email="admin@test.com",
        user_id="user-123",
        roles=["platform_admin"],
        name="Admin User",
        org_id="org-test"
    )

@pytest.fixture
def mock_org_context():
    """Mock OrganizationContext"""
    ctx = Mock()
    ctx.execution_id = "exec-123"
    ctx.set_variable = Mock()
    ctx._state_snapshots = []
    ctx._integration_calls = []
    ctx._logs = []
    ctx._variables = {}
    return ctx
```

### File: `tests/unit/handlers/test_oauth_handlers.py` (~95 tests)

**Test pattern for async handlers:**
```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
import azure.functions as func
from shared.handlers.oauth_handlers import create_oauth_connection_handler
from shared.models import ErrorResponse

@pytest.mark.asyncio
async def test_create_oauth_connection_success(mock_http_request, mock_request_context):
    """Test successful OAuth connection creation"""
    mock_req = mock_http_request(json_data={
        "connection_name": "test-conn",
        "oauth_provider": "microsoft",
        "client_id": "test-client",
        "client_secret": "test-secret",
        "scopes": ["openid"],
        "authorization_url": "https://auth.example.com",
        "token_url": "https://token.example.com",
        "redirect_uri": "/oauth/callback/test-conn",
        "oauth_flow_type": "authorization_code"
    })

    with patch('shared.handlers.oauth_handlers.get_context') as mock_ctx:
        mock_ctx.return_value = mock_request_context

        with patch('shared.handlers.oauth_handlers.OAuthStorageService') as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.get_connection = AsyncMock(return_value=None)  # No existing

            mock_conn = Mock()
            mock_conn.to_detail = Mock(return_value=Mock(
                model_dump=Mock(return_value={
                    "connection_id": "conn-123",
                    "connection_name": "test-conn",
                    "status": "not_connected"
                })
            ))
            mock_svc.create_connection = AsyncMock(return_value=mock_conn)

            response = await create_oauth_connection_handler(mock_req)

            assert response.status_code == 201
            assert response.mimetype == "application/json"
            mock_svc.create_connection.assert_called_once()
```

**Tests to write:**

OAuth Handlers (~95 tests total):
- create_oauth_connection: success, duplicate (409), validation error, JSON error, exception (5 tests)
- list_oauth_connections: success, empty list, exception (3 tests)
- get_oauth_connection: success, not found (404), exception (3 tests)
- update_oauth_connection: success, not found, validation error, JSON error, exception (5 tests)
- delete_oauth_connection: success, not found (idempotent), exception (3 tests)
- authorize_oauth_connection: success, not found, client_credentials error, state generation, PKCE, exception (6 tests)
- cancel_oauth_authorization: success, not found, exception (3 tests)
- refresh_oauth_token: success, not found, not connected status, KeyVault unavailable, no refresh token, refresh failed, exception (7 tests)
- oauth_callback: success, connection not found, missing code, token exchange failed, test connection failed, exception (6 tests)
- get_oauth_credentials: success, not found, not completed status, KeyVault unavailable, exception (5 tests)
- get_oauth_refresh_job_status: success, no job run yet, parse errors, exception (4 tests)

Total: ~55 tests

### File: `tests/unit/handlers/test_forms_handlers.py` (~55 tests)

Forms Handlers tests:
- list_forms: success, empty list, exception (3 tests)
- create_form: success, validation error, JSON error, exception (4 tests)
- get_form: success, not found, not active, no permission, exception (5 tests)
- update_form: success, partial update, not found, validation error, JSON error, exception (6 tests)
- delete_form: success, not found (idempotent), exception (3 tests)
- execute_form_startup: success, not found, not active, no permission, no launch workflow, missing params, workflow error, exception (8 tests)
- execute_form: success, not found, not active, no permission, no linked workflow, validation error, JSON error, workflow error, execution record, exception (10 tests)
- validate_launch_workflow_params: no workflow, valid params, missing params (3 tests)

Total: ~42 tests

---

## Testing Best Practices

1. **Use @pytest.mark.asyncio** for all async test functions
2. **Mock external dependencies:**
   - get_context() - always mock
   - All services (OAuthStorageService, OAuthProviderClient, etc.)
   - KeyVaultClient
   - TableStorageService
   - FormRepository
   - Workflow registry

3. **Use AsyncMock** for async method mocks:
   ```python
   from unittest.mock import AsyncMock
   mock_service.async_method = AsyncMock(return_value=result)
   ```

4. **Test error paths:**
   - ValidationError with error details
   - ValueError for JSON parse errors
   - Not found scenarios (404)
   - Permission denied (403)
   - Business logic errors (400)
   - Unexpected exceptions (500)

5. **Test model_dump() calls:**
   ```python
   mock_obj.model_dump = Mock(return_value={...})
   ```

---

## Completion Checklist

- [ ] Create `shared/handlers/` directory
- [ ] Create `shared/handlers/__init__.py` (empty)
- [ ] Create `shared/handlers/oauth_handlers.py` (11 handlers, ~1300 lines)
- [ ] Create `shared/handlers/forms_handlers.py` (8 handlers + helper function, ~900 lines)
- [ ] Refactor `functions/oauth_api.py` (thin wrappers, ~200 lines)
- [ ] Refactor `functions/forms.py` (thin wrappers, ~150 lines)
- [ ] Create `tests/unit/handlers/` directory
- [ ] Create `tests/unit/handlers/__init__.py` (empty)
- [ ] Create `tests/unit/handlers/conftest.py` (fixtures)
- [ ] Create `tests/unit/handlers/test_oauth_handlers.py` (~95 tests)
- [ ] Create `tests/unit/handlers/test_forms_handlers.py` (~55 tests)
- [ ] Run pytest and verify all tests pass (100% passing)
- [ ] Run `npx pyright shared/handlers/` and verify no errors
- [ ] Run `ruff check shared/handlers/` and verify no issues
- [ ] Verify integration tests still pass (no regressions)
- [ ] Calculate and verify handler coverage >= 80%

---

## Expected Outcome

- **Lines of code refactored:** ~2500 (1463 + 1034)
- **New test code:** ~150 tests, ~1500 test lines
- **Handler code coverage:** 80%+
- **Integration test regression:** 0 new failures
- **Type checking:** 0 errors/warnings in handler files
- **Linting:** 0 issues in handler files

