# Phase 6B: Extract Roles, Secrets & Permissions Handlers

## Objective
Extract business logic from `roles.py` (783 lines), `secrets.py` (609 lines), and `permissions.py` (582 lines) into unit-testable handler functions in `shared/handlers/`.

## Files to Refactor

### 1. roles.py → shared/handlers/roles_handlers.py

**Current Structure:**
- 13 endpoint functions with inline business logic
- ~783 lines total

**Handlers to Extract (13 total):**
1. `create_role_handler`
2. `list_roles_handler`
3. `get_role_handler`
4. `update_role_handler`
5. `delete_role_handler`
6. `assign_role_handler`
7. `unassign_role_handler`
8. `get_role_assignments_handler`
9. `get_user_roles_handler`
10. `validate_role_permissions_handler`
11. `get_role_permissions_handler`
12. `update_role_permissions_handler`
13. `get_available_permissions_handler`

### 2. secrets.py → shared/handlers/secrets_handlers.py

**Current Structure:**
- 9 endpoint functions with inline business logic
- ~609 lines total

**Handlers to Extract (9 total):**
1. `set_secret_handler`
2. `get_secret_handler`
3. `list_secrets_handler`
4. `delete_secret_handler`
5. `get_secret_metadata_handler`
6. `update_secret_metadata_handler`
7. `rotate_secret_handler`
8. `validate_secret_access_handler`
9. `get_secret_versions_handler`

### 3. permissions.py → shared/handlers/permissions_handlers.py

**Current Structure:**
- 10 endpoint functions with inline business logic
- ~582 lines total

**Handlers to Extract (10 total):**
1. `list_users_handler`
2. `get_user_details_handler`
3. `get_user_roles_handler`
4. `get_user_forms_handler`
5. `get_user_workflows_handler`
6. `assign_user_permission_handler`
7. `revoke_user_permission_handler`
8. `get_user_organizations_handler`
9. `validate_user_access_handler`
10. `get_user_activity_handler`

## Implementation Pattern

### Step 1: Create Handler Files
```bash
mkdir -p shared/handlers
touch shared/handlers/roles_handlers.py
touch shared/handlers/secrets_handlers.py
touch shared/handlers/permissions_handlers.py
```

### Step 2: Extract Handler Functions

**Example - roles.py:**

**Before:**
```python
# functions/roles.py
@bp.route(route="roles", methods=["POST"])
@with_request_context
@require_platform_admin
async def create_role(req: func.HttpRequest) -> func.HttpResponse:
    context = get_context(req)
    try:
        request_body = req.get_json()
        create_request = CreateRoleRequest(**request_body)
        # ... 60 lines of business logic
        return func.HttpResponse(json.dumps(role.model_dump()), status_code=201, ...)
    except ValidationError as e:
        # ... error handling
```

**After:**
```python
# functions/roles.py (~80 lines)
from shared.handlers.roles_handlers import create_role_handler

@bp.route(route="roles", methods=["POST"])
@with_request_context
@require_platform_admin
async def create_role(req: func.HttpRequest) -> func.HttpResponse:
    return await create_role_handler(req)

# shared/handlers/roles_handlers.py
async def create_role_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Business logic for creating a role - unit testable"""
    context = get_context(req)
    try:
        request_body = req.get_json()
        create_request = CreateRoleRequest(**request_body)
        # ... all 60 lines of business logic here
        return func.HttpResponse(json.dumps(role.model_dump()), status_code=201, ...)
    except ValidationError as e:
        # ... error handling
```

### Step 3: Write Unit Tests

**Test File Structure:**
```
tests/unit/handlers/
├── test_roles_handlers.py        # Roles handler tests
├── test_secrets_handlers.py      # Secrets handler tests
└── test_permissions_handlers.py  # Permissions handler tests
```

**Test Pattern:**
```python
# tests/unit/handlers/test_roles_handlers.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
import azure.functions as func
from shared.handlers.roles_handlers import create_role_handler

@pytest.mark.asyncio
async def test_create_role_success():
    # Arrange
    mock_req = Mock(spec=func.HttpRequest)
    mock_req.get_json.return_value = {
        "role_name": "test-role",
        "description": "Test role",
        "permissions": ["read", "write"]
    }

    with patch('shared.handlers.roles_handlers.get_context') as mock_ctx:
        mock_ctx.return_value = Mock(
            scope="org-123",
            email="admin@test.com",
            user_id="user-123"
        )

        with patch('shared.handlers.roles_handlers.RolesRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_role = AsyncMock(return_value=None)  # No duplicate
            mock_repo.create_role = AsyncMock(return_value=Mock(
                role_id="role-123",
                role_name="test-role",
                model_dump=lambda: {"role_id": "role-123", "role_name": "test-role"}
            ))

            # Act
            response = await create_role_handler(mock_req)

            # Assert
            assert response.status_code == 201
            mock_repo.create_role.assert_called_once()

@pytest.mark.asyncio
async def test_create_role_duplicate():
    """Test duplicate role name"""
    mock_req = Mock(spec=func.HttpRequest)
    mock_req.get_json.return_value = {"role_name": "existing", ...}

    with patch('shared.handlers.roles_handlers.get_context') as mock_ctx:
        mock_ctx.return_value = Mock(scope="org-123")

        with patch('shared.handlers.roles_handlers.RolesRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_role = AsyncMock(return_value=Mock(role_name="existing"))

            response = await create_role_handler(mock_req)

            assert response.status_code == 409
            mock_repo.create_role.assert_not_called()

@pytest.mark.asyncio
async def test_create_role_validation_error():
    """Test invalid request data"""
    mock_req = Mock(spec=func.HttpRequest)
    mock_req.get_json.return_value = {"invalid": "data"}  # Missing required fields

    with patch('shared.handlers.roles_handlers.get_context'):
        response = await create_role_handler(mock_req)

        assert response.status_code == 400
        assert b"ValidationError" in response.get_body()
```

**Secrets Handler Test Pattern:**
```python
@pytest.mark.asyncio
async def test_set_secret_with_keyvault():
    """Test secret storage with Key Vault encryption"""
    mock_req = Mock(spec=func.HttpRequest)
    mock_req.get_json.return_value = {
        "key": "api_key",
        "value": "secret-value-123",
        "description": "API Key"
    }

    with patch('shared.handlers.secrets_handlers.get_context') as mock_ctx:
        mock_ctx.return_value = Mock(scope="org-123", user_id="user-123")

        with patch('shared.handlers.secrets_handlers.KeyVaultClient') as MockKV:
            mock_kv = MockKV.return_value
            mock_kv.set_secret = AsyncMock()

            with patch('shared.handlers.secrets_handlers.TableStorageService') as MockTable:
                mock_table = MockTable.return_value
                mock_table.create_entity = AsyncMock()

                response = await set_secret_handler(mock_req)

                assert response.status_code == 201
                mock_kv.set_secret.assert_called_once()
                mock_table.create_entity.assert_called_once()
```

**Permissions Handler Test Pattern:**
```python
@pytest.mark.asyncio
async def test_list_users_with_filters():
    """Test listing users with type and organization filters"""
    mock_req = Mock(spec=func.HttpRequest)
    mock_req.params = {"user_type": "platform_admin", "organization_id": "org-123"}

    with patch('shared.handlers.permissions_handlers.get_context') as mock_ctx:
        mock_ctx.return_value = Mock(scope="GLOBAL", roles=["platform_admin"])

        with patch('shared.handlers.permissions_handlers.UsersRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.list_users = AsyncMock(return_value=[
                Mock(email="admin1@test.com", user_type="platform_admin"),
                Mock(email="admin2@test.com", user_type="platform_admin")
            ])

            response = await list_users_handler(mock_req)

            assert response.status_code == 200
            mock_repo.list_users.assert_called_once_with(
                user_type="platform_admin",
                organization_id="org-123"
            )
```

## Test Coverage Targets

### Roles Handlers Tests (~65 tests)
- `create_role_handler`: 5 tests (success, duplicate, validation, permissions, exception)
- `list_roles_handler`: 3 tests (success, empty, filtering)
- `get_role_handler`: 3 tests (success, not found, exception)
- `update_role_handler`: 5 tests (success, not found, validation, partial, exception)
- `delete_role_handler`: 4 tests (success, not found, in use, exception)
- `assign_role_handler`: 5 tests (success, user not found, role not found, already assigned, exception)
- `unassign_role_handler`: 4 tests (success, not assigned, user not found, exception)
- `get_role_assignments_handler`: 3 tests (success, empty, pagination)
- `get_user_roles_handler`: 3 tests (success, no roles, invalid user)
- Plus ~30 more for remaining handlers

### Secrets Handlers Tests (~45 tests)
- `set_secret_handler`: 6 tests (success, update, KeyVault integration, validation, encryption, exception)
- `get_secret_handler`: 4 tests (success, not found, decryption, permission denied)
- `list_secrets_handler`: 3 tests (success, empty, metadata only)
- `delete_secret_handler`: 3 tests (success, not found, cascade delete)
- `get_secret_metadata_handler`: 3 tests (success, not found, permissions)
- `update_secret_metadata_handler`: 4 tests (success, not found, validation, exception)
- `rotate_secret_handler`: 5 tests (success, version creation, notification, not found, exception)
- Plus ~17 more for remaining handlers

### Permissions Handlers Tests (~50 tests)
- `list_users_handler`: 5 tests (success, filters, pagination, types, organizations)
- `get_user_details_handler`: 3 tests (success, not found, exception)
- `get_user_roles_handler`: 4 tests (success, multiple orgs, no roles, invalid user)
- `get_user_forms_handler`: 3 tests (success, empty, filtering)
- `get_user_workflows_handler`: 3 tests (success, empty, filtering)
- `assign_user_permission_handler`: 5 tests (success, duplicate, invalid, exception, validation)
- `revoke_user_permission_handler`: 4 tests (success, not found, validation, exception)
- Plus ~23 more for remaining handlers

## Completion Criteria

- [ ] `shared/handlers/roles_handlers.py` created with 13 handler functions (~700 lines)
- [ ] `shared/handlers/secrets_handlers.py` created with 9 handler functions (~550 lines)
- [ ] `shared/handlers/permissions_handlers.py` created with 10 handler functions (~520 lines)
- [ ] `functions/roles.py` refactored to thin wrappers (~100 lines)
- [ ] `functions/secrets.py` refactored to thin wrappers (~80 lines)
- [ ] `functions/permissions.py` refactored to thin wrappers (~90 lines)
- [ ] `tests/unit/handlers/test_roles_handlers.py` with ~65 tests
- [ ] `tests/unit/handlers/test_secrets_handlers.py` with ~45 tests
- [ ] `tests/unit/handlers/test_permissions_handlers.py` with ~50 tests
- [ ] All tests pass (100%)
- [ ] Type checking passes (`npx pyright shared/handlers/`)
- [ ] Linting passes (`ruff check shared/handlers/`)
- [ ] Coverage of handlers >= 80%
- [ ] Integration tests still pass (no regressions)

## Estimated Impact
- **Lines of code refactored:** ~1974
- **New test coverage:** ~160 tests, ~1600 test lines
- **Expected coverage increase:** +6-8% (handlers now measurable)
