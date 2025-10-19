# Phase 6B Execution Checklist

## Task Overview
Extract business logic from three endpoint files into unit-testable handler functions:
- `functions/roles.py` (783 lines) → `shared/handlers/roles_handlers.py` (13 handlers)
- `functions/secrets.py` (609 lines) → `shared/handlers/secrets_handlers.py` (9 handlers)
- `functions/permissions.py` (582 lines) → `shared/handlers/permissions_handlers.py` (10 handlers)

Then write ~160 comprehensive unit tests across 3 test files.

## Acceptance Criteria
- [ ] All 160+ tests pass (100%)
- [ ] Handler files coverage >= 80%
- [ ] `npx pyright shared/handlers/` passes with no errors/warnings
- [ ] `ruff check shared/handlers/` passes with no issues
- [ ] Integration tests pass (no regressions)
- [ ] Handlers are thin, focused, and well-documented

## Implementation Steps

### Step 1: Create shared/handlers/ Directory & __init__.py
```bash
mkdir -p /Users/jack/GitHub/bifrost-integrations/api/shared/handlers
touch /Users/jack/GitHub/bifrost-integrations/api/shared/handlers/__init__.py
```

### Step 2: Create shared/handlers/roles_handlers.py

**Key handlers to extract:**
1. `list_roles_handler()` - lines 47-83 from functions/roles.py
2. `create_role_handler()` - lines 99-165
3. `update_role_handler()` - lines 187-245
4. `delete_role_handler()` - lines 265-298
5. `get_role_users_handler()` - lines 319-356
6. `assign_users_to_role_handler()` - lines 377-475
7. `remove_user_from_role_handler()` - lines 499-554
8. `get_role_forms_handler()` - lines 575-612
9. `assign_forms_to_role_handler()` - lines 633-704
10. `remove_form_from_role_handler()` - lines 728-783

**Template:**
```python
"""
Business logic handlers for roles endpoints.

Extracted from functions/roles.py for unit testing.
"""

import json
import logging
import azure.functions as func
from pydantic import ValidationError

from shared.custom_types import get_context
from shared.models import ErrorResponse, CreateRoleRequest, UpdateRoleRequest, AssignUsersToRoleRequest, AssignFormsToRoleRequest
from shared.repositories.roles import RoleRepository
from shared.repositories.users import UserRepository

logger = logging.getLogger(__name__)


async def list_roles_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Get all roles (Platform admin only)"""
    # TODO: Extract lines 47-83 from functions/roles.py


async def create_role_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Create a new role (Platform admin only)"""
    # TODO: Extract lines 99-165 from functions/roles.py


# ... continue for all 10 handlers
```

### Step 3: Create shared/handlers/secrets_handlers.py

**Key handlers to extract:**
1. `list_secrets_handler()` - lines 53-117 from functions/secrets.py
2. `create_secret_handler()` - lines 133-251
3. `update_secret_handler()` - lines 273-405
4. `delete_secret_handler()` - lines 426-609

**Template:**
```python
"""
Business logic handlers for secrets endpoints.

Extracted from functions/secrets.py for unit testing.
Handles Azure Key Vault integration and secret management.
"""

import json
import logging
import azure.functions as func
from pydantic import ValidationError

from shared.custom_types import get_context
from shared.keyvault import KeyVaultClient
from shared.models import ErrorResponse, SecretCreateRequest, SecretUpdateRequest
from shared.storage import get_table_service
from shared.validation import check_key_vault_available

logger = logging.getLogger(__name__)


async def list_secrets_handler(req: func.HttpRequest) -> func.HttpResponse:
    """List secrets from Key Vault (Platform admin only)"""
    # TODO: Extract lines 53-117 from functions/secrets.py


async def create_secret_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Create a new secret in Key Vault (Platform admin only)"""
    # TODO: Extract lines 133-251 from functions/secrets.py


# ... continue for all 4 handlers
```

### Step 4: Create shared/handlers/permissions_handlers.py

**Key handlers to extract:**
1. `list_users_handler()` - lines 55-127 from functions/permissions.py
2. `get_user_handler()` - lines 149-215
3. `get_user_permissions_handler()` - lines 236-254 (deprecated)
4. `get_org_permissions_handler()` - lines 275-293 (deprecated)
5. `grant_permissions_handler()` - lines 309-328 (deprecated)
6. `revoke_permissions_handler()` - lines 355-374 (deprecated)
7. `get_user_roles_handler()` - lines 399-445
8. `get_user_forms_handler()` - lines 467-582

**Template:**
```python
"""
Business logic handlers for permissions endpoints.

Extracted from functions/permissions.py for unit testing.
Manages user permissions, roles, and form access.
"""

import json
import logging
from datetime import datetime
import azure.functions as func

from shared.custom_types import get_context, get_route_param
from shared.models import ErrorResponse, User
from shared.storage import get_table_service

logger = logging.getLogger(__name__)


async def list_users_handler(req: func.HttpRequest) -> func.HttpResponse:
    """List users with optional filtering (Platform admin only)"""
    # TODO: Extract lines 55-127 from functions/permissions.py


async def get_user_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Get user details (Platform admin only)"""
    # TODO: Extract lines 149-215 from functions/permissions.py


# ... continue for all 8 handlers
```

### Step 5: Create Test Fixtures (tests/unit/handlers/conftest.py)

```python
"""
Shared pytest fixtures for handler tests.

Provides:
- Mock request contexts
- Mock HTTP requests
- Mock repositories
- Mock Azure services
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import azure.functions as func
from shared.request_context import RequestContext


@pytest.fixture
def mock_context():
    """Create a mock RequestContext"""
    return RequestContext(
        user_id="test-user-123",
        email="test@example.com",
        name="Test User",
        org_id="org-123",
        is_platform_admin=True,
        is_function_key=False
    )


@pytest.fixture
def mock_req():
    """Create a mock func.HttpRequest"""
    req = Mock(spec=func.HttpRequest)
    req.route_params = {}
    req.params = {}
    req.get_json = Mock(return_value={})
    req.get_body = Mock(return_value=b'{}')
    req.context = mock_context()
    return req


@pytest.fixture
def mock_table_service():
    """Mock TableStorageService"""
    service = Mock()
    service.get_entity = Mock(return_value=None)
    service.query_entities = Mock(return_value=iter([]))
    service.insert_entity = Mock()
    service.update_entity = Mock()
    service.delete_entity = Mock()
    return service


@pytest.fixture
def mock_kv_manager():
    """Mock KeyVaultClient"""
    kv = Mock()
    kv.list_secrets = AsyncMock(return_value=[])
    kv.create_secret = AsyncMock()
    kv.get_secret = AsyncMock(return_value="secret-value")
    kv.update_secret = AsyncMock()
    kv.delete_secret = AsyncMock()
    return kv
```

### Step 6: Create Unit Tests for Roles Handlers

File: `tests/unit/handlers/test_roles_handlers.py` (~65 tests, ~650 lines)

Key test classes:
- `TestListRolesHandler` (3 tests)
- `TestCreateRoleHandler` (5 tests)
- `TestUpdateRoleHandler` (5 tests)
- `TestDeleteRoleHandler` (4 tests)
- `TestGetRoleUsersHandler` (3 tests)
- `TestAssignUsersToRoleHandler` (5 tests)
- `TestRemoveUserFromRoleHandler` (4 tests)
- `TestGetRoleFormsHandler` (3 tests)
- `TestAssignFormsToRoleHandler` (5 tests)
- `TestRemoveFormFromRoleHandler` (4 tests)

### Step 7: Create Unit Tests for Secrets Handlers

File: `tests/unit/handlers/test_secrets_handlers.py` (~45 tests, ~450 lines)

Key test classes:
- `TestListSecretsHandler` (4 tests)
- `TestCreateSecretHandler` (6 tests)
- `TestUpdateSecretHandler` (5 tests)
- `TestDeleteSecretHandler` (6 tests)
- Integration tests with KeyVault (24 tests)

### Step 8: Create Unit Tests for Permissions Handlers

File: `tests/unit/handlers/test_permissions_handlers.py` (~50 tests, ~450 lines)

Key test classes:
- `TestListUsersHandler` (5 tests)
- `TestGetUserHandler` (3 tests)
- `TestGetUserPermissionsHandler` (1 test - deprecated)
- `TestGetOrgPermissionsHandler` (1 test - deprecated)
- `TestGrantPermissionsHandler` (1 test - deprecated)
- `TestRevokePermissionsHandler` (1 test - deprecated)
- `TestGetUserRolesHandler` (4 tests)
- `TestGetUserFormsHandler` (8 tests)
- Edge cases and error scenarios (22 tests)

### Step 9: Refactor functions/roles.py

Replace each endpoint function body with handler call:

**Before:**
```python
async def list_roles(req: func.HttpRequest) -> func.HttpResponse:
    context = req.context
    logger.info(f"User {context.user_id} listing all roles")

    try:
        # ... 30 lines of logic
    except Exception as e:
        # ... error handling
```

**After:**
```python
from shared.handlers.roles_handlers import list_roles_handler

async def list_roles(req: func.HttpRequest) -> func.HttpResponse:
    return await list_roles_handler(req)
```

### Step 10: Refactor functions/secrets.py

Same pattern as roles.py

### Step 11: Refactor functions/permissions.py

Same pattern as roles.py

### Step 12: Validation

```bash
# Run all tests
cd /Users/jack/GitHub/bifrost-integrations/api
pytest tests/unit/handlers/ -v --cov=shared/handlers --cov-report=term-missing

# Type checking
npx pyright shared/handlers/

# Linting
ruff check shared/handlers/

# Integration tests (ensure no regressions)
pytest tests/contract/ -v

# All tests
pytest tests/
```

## Expected Outcomes

After completion:
- **3 new handler files** (~1,770 lines total of business logic)
- **3 test files** (~1,550 lines total of tests)
- **3 refactored endpoint files** (~270 lines total, down from ~1,974)
- **160+ unit tests** covering handler business logic
- **80%+ coverage** of handler files
- **Zero regressions** in integration tests

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Missing business logic during extraction | Review original functions line-by-line, test comprehensive scenarios |
| Mocking complexity | Start with fixtures, use consistent patterns, document non-obvious mocks |
| Coverage gaps | Aim for 80%+ initially, add edge case tests based on coverage reports |
| Import issues | Verify all imports after refactoring, run pyright early |
| Integration test regressions | Run contract tests frequently, validate request/response formats |

## Time Estimate

- Setup & structure: 30 minutes
- Handlers extraction: 2 hours
- Test writing: 3-4 hours
- Validation & fixes: 1 hour
- **Total: 6-7 hours**
