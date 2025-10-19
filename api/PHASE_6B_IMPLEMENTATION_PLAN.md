# Phase 6B Implementation Plan: Extract Roles, Secrets & Permissions Handlers

## Overview
This plan describes how to extract business logic from three endpoint files (roles.py, secrets.py, permissions.py) into unit-testable handler functions in shared/handlers/, then refactor endpoints to be thin wrappers and write comprehensive unit tests.

**Estimated effort:** ~6-8 hours for full implementation
**Files affected:** 9 total (3 handler files, 3 refactored endpoints, 3 test files)
**Total new lines:** ~2,200 (handlers + tests)

## Phase 1: Create Handler Files (1-2 hours)

### 1.1 Create `shared/handlers/roles_handlers.py` (~700 lines)

**Extract these 13 handler functions:**
1. `list_roles_handler` - Get all roles (active only)
2. `create_role_handler` - Create new role with validation
3. `update_role_handler` - Update role fields
4. `delete_role_handler` - Soft delete role (idempotent)
5. `get_role_users_handler` - Get user IDs assigned to role
6. `assign_users_to_role_handler` - Batch assign users (validate not platform admin)
7. `remove_user_from_role_handler` - Remove user from role (idempotent)
8. `get_role_forms_handler` - Get form IDs assigned to role
9. `assign_forms_to_role_handler` - Batch assign forms to role
10. `remove_form_from_role_handler` - Remove form from role (idempotent)

**Key patterns:**
- All are async functions taking `func.HttpRequest` and returning `func.HttpResponse`
- Each extracts business logic from current `functions/roles.py` endpoint
- Error handling: ValidationError (400), NotFound (404), BadRequest (400), InternalServerError (500)
- Uses: RoleRepository, UserRepository, get_context()

**Structure:**
```python
# imports
# async def list_roles_handler(req: func.HttpRequest) -> func.HttpResponse:
# async def create_role_handler(req: func.HttpRequest) -> func.HttpResponse:
# ... etc
```

### 1.2 Create `shared/handlers/secrets_handlers.py` (~550 lines)

**Extract these 9 handler functions:**
1. `list_secrets_handler` - List secrets from Key Vault with optional org filter
2. `create_secret_handler` - Create secret (check for duplicates, Key Vault integration)
3. `update_secret_handler` - Update secret value (parse name, validate format)
4. `delete_secret_handler` - Delete secret (check for config references, cascade safe)

**Key patterns:**
- Key Vault integration: check availability, handle not found, encryption
- Secret name format: `{org_id}--{secret_key}` (e.g., "org-123--api-key")
- Error handling: BadRequest (400), NotFound (404), Conflict (409), validation
- Uses: KeyVaultClient, check_key_vault_available(), get_context()
- Table Storage queries for dependency checking (config references)

**Structure:**
```python
# imports
# async def list_secrets_handler(req: func.HttpRequest) -> func.HttpResponse:
# async def create_secret_handler(req: func.HttpRequest) -> func.HttpResponse:
# ... etc
```

### 1.3 Create `shared/handlers/permissions_handlers.py` (~520 lines)

**Extract these 10 handler functions:**
1. `list_users_handler` - List users with type/org filtering
2. `get_user_handler` - Get user details
3. `get_user_permissions_handler` - Deprecated, return empty list
4. `get_org_permissions_handler` - Deprecated, return empty list
5. `grant_permissions_handler` - Deprecated, return 501 NotImplemented
6. `revoke_permissions_handler` - Deprecated, return 501 NotImplemented
7. `get_user_roles_handler` - Get role IDs for user (query Relationships table)
8. `get_user_forms_handler` - Get form IDs user can access via roles (complex logic)

**Key patterns:**
- Complex form access logic: platform admins get all forms, regular users get forms via roles
- Query patterns: RowKey ranges for efficient table queries
- Uses: get_table_service("Entities"), get_table_service("Relationships")
- Error handling: NotFound (404), InternalServerError (500)

**Structure:**
```python
# imports
# async def list_users_handler(req: func.HttpRequest) -> func.HttpResponse:
# async def get_user_handler(req: func.HttpRequest) -> func.HttpResponse:
# ... etc
```

## Phase 2: Refactor Endpoint Files (30 minutes)

### 2.1 Refactor `functions/roles.py` (~100 lines)
Replace each endpoint function body with a single call to corresponding handler:

```python
# Before (~40 lines per endpoint)
async def list_roles(req: func.HttpRequest) -> func.HttpResponse:
    context = req.context
    logger.info(...)
    try:
        role_repo = RoleRepository()
        roles = role_repo.list_roles(...)
        # ... 35 more lines
    except Exception as e:
        # ... error handling

# After (~2 lines per endpoint)
async def list_roles(req: func.HttpRequest) -> func.HttpResponse:
    return await list_roles_handler(req)
```

### 2.2 Refactor `functions/secrets.py` (~80 lines)
Same pattern: replace body with handler call

### 2.3 Refactor `functions/permissions.py` (~90 lines)
Same pattern: replace body with handler call

## Phase 3: Write Unit Tests (3-4 hours)

### 3.1 Create `tests/unit/handlers/conftest.py`
Shared pytest fixtures for all handler tests:
- `mock_context` - RequestContext with standard values
- `mock_req` - func.HttpRequest mock
- `mock_table_service` - TableStorageService mock
- `mock_kv_manager` - KeyVaultClient mock
- Patches for: get_context, RoleRepository, UserRepository, etc.

### 3.2 Create `tests/unit/handlers/test_roles_handlers.py` (~650 lines, ~65 tests)

**Test structure by handler:**

#### list_roles_handler (3 tests)
- ✓ test_list_roles_success
- ✓ test_list_roles_empty
- ✓ test_list_roles_sorts_by_date_descending

#### create_role_handler (5 tests)
- ✓ test_create_role_success
- ✓ test_create_role_duplicate_name
- ✓ test_create_role_validation_error_missing_name
- ✓ test_create_role_validation_error_invalid_json
- ✓ test_create_role_exception

#### update_role_handler (5 tests)
- ✓ test_update_role_success
- ✓ test_update_role_not_found
- ✓ test_update_role_validation_error
- ✓ test_update_role_partial_update
- ✓ test_update_role_exception

#### delete_role_handler (4 tests)
- ✓ test_delete_role_success
- ✓ test_delete_role_not_found_idempotent
- ✓ test_delete_role_exception

#### get_role_users_handler (3 tests)
- ✓ test_get_role_users_success
- ✓ test_get_role_users_empty
- ✓ test_get_role_users_exception

#### assign_users_to_role_handler (5 tests)
- ✓ test_assign_users_success
- ✓ test_assign_users_role_not_found
- ✓ test_assign_users_user_not_found
- ✓ test_assign_users_platform_admin_blocked
- ✓ test_assign_users_validation_error

#### remove_user_from_role_handler (4 tests)
- ✓ test_remove_user_success
- ✓ test_remove_user_not_assigned_idempotent
- ✓ test_remove_user_missing_role_id
- ✓ test_remove_user_exception

#### get_role_forms_handler (3 tests)
- ✓ test_get_role_forms_success
- ✓ test_get_role_forms_empty
- ✓ test_get_role_forms_exception

#### assign_forms_to_role_handler (5 tests)
- ✓ test_assign_forms_success
- ✓ test_assign_forms_role_not_found
- ✓ test_assign_forms_validation_error
- ✓ test_assign_forms_exception

#### remove_form_from_role_handler (4 tests)
- ✓ test_remove_form_success
- ✓ test_remove_form_not_assigned_idempotent
- ✓ test_remove_form_missing_role_id
- ✓ test_remove_form_exception

**Remaining tests (10):**
- Error handling edge cases, context validation, logging

### 3.3 Create `tests/unit/handlers/test_secrets_handlers.py` (~450 lines, ~45 tests)

#### list_secrets_handler (4 tests)
- ✓ test_list_secrets_success
- ✓ test_list_secrets_with_org_filter
- ✓ test_list_secrets_key_vault_unavailable
- ✓ test_list_secrets_exception

#### create_secret_handler (6 tests)
- ✓ test_create_secret_success
- ✓ test_create_secret_duplicate
- ✓ test_create_secret_validation_error_missing_fields
- ✓ test_create_secret_validation_error_invalid_json
- ✓ test_create_secret_key_vault_unavailable
- ✓ test_create_secret_exception

#### update_secret_handler (5 tests)
- ✓ test_update_secret_success
- ✓ test_update_secret_not_found
- ✓ test_update_secret_invalid_name_format
- ✓ test_update_secret_validation_error
- ✓ test_update_secret_exception

#### delete_secret_handler (6 tests)
- ✓ test_delete_secret_success
- ✓ test_delete_secret_not_found
- ✓ test_delete_secret_invalid_name_format
- ✓ test_delete_secret_config_references_global
- ✓ test_delete_secret_config_references_org
- ✓ test_delete_secret_exception

**Remaining tests (24):**
- Key Vault integration edge cases, config reference checking variations, error cases

### 3.4 Create `tests/unit/handlers/test_permissions_handlers.py` (~450 lines, ~50 tests)

#### list_users_handler (5 tests)
- ✓ test_list_users_success
- ✓ test_list_users_filter_by_type_platform
- ✓ test_list_users_filter_by_type_org
- ✓ test_list_users_empty
- ✓ test_list_users_exception

#### get_user_handler (3 tests)
- ✓ test_get_user_success
- ✓ test_get_user_not_found
- ✓ test_get_user_exception

#### get_user_permissions_handler (1 test)
- ✓ test_get_user_permissions_deprecated_returns_empty

#### get_org_permissions_handler (1 test)
- ✓ test_get_org_permissions_deprecated_returns_empty

#### grant_permissions_handler (1 test)
- ✓ test_grant_permissions_deprecated_returns_501

#### revoke_permissions_handler (1 test)
- ✓ test_revoke_permissions_deprecated_returns_501

#### get_user_roles_handler (4 tests)
- ✓ test_get_user_roles_success
- ✓ test_get_user_roles_empty
- ✓ test_get_user_roles_multiple
- ✓ test_get_user_roles_exception

#### get_user_forms_handler (8 tests)
- ✓ test_get_user_forms_platform_admin_all_forms
- ✓ test_get_user_forms_regular_user_via_roles
- ✓ test_get_user_forms_no_roles_assigned
- ✓ test_get_user_forms_multiple_roles
- ✓ test_get_user_forms_user_not_found
- ✓ test_get_user_forms_empty
- ✓ test_get_user_forms_complex_role_form_mapping
- ✓ test_get_user_forms_exception

**Remaining tests (25):**
- Edge cases, error scenarios, table query variations

## Phase 4: Validation & Quality (30 minutes)

### 4.1 Run tests
```bash
pytest tests/unit/handlers/ -v --cov=shared/handlers --cov-report=term
```
Target: 80%+ coverage of handler files

### 4.2 Type checking
```bash
npx pyright shared/handlers/
```
Must pass with no errors or warnings

### 4.3 Linting
```bash
ruff check shared/handlers/
```
Must pass with no issues

### 4.4 Integration tests
Ensure no regressions:
```bash
pytest tests/contract/ -v
```

## Implementation Guidelines

### Mocking Strategy
- Mock `get_context()` to return standard test context
- Mock repositories (RoleRepository, UserRepository) with AsyncMock
- Mock KeyVaultClient with AsyncMock for secrets
- Mock get_table_service() for table queries
- Use `@patch` decorators or context managers

### Test Patterns
```python
@pytest.mark.asyncio
async def test_handler_success():
    # Arrange
    mock_req = Mock(spec=func.HttpRequest)
    mock_req.get_json.return_value = {"key": "value"}

    with patch('shared.handlers.roles_handlers.get_context') as mock_ctx:
        mock_ctx.return_value = Mock(...)

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.method = AsyncMock(return_value=...)

            # Act
            response = await handler_function(mock_req)

            # Assert
            assert response.status_code == 200
            mock_repo.method.assert_called_once()
```

### Error Handling
- All handlers must catch exceptions and return proper HTTP responses
- Validation errors → 400
- Not found → 404
- Conflicts → 409
- Server errors → 500

### Context Extraction
- All handlers extract context with `get_context(req)`
- Use `req.route_params.get()` for path parameters
- Use `req.params.get()` for query parameters

## Success Criteria

- [ ] All 160 tests pass (100%)
- [ ] Handler coverage >= 80%
- [ ] Type checking passes (npx pyright)
- [ ] Linting passes (ruff check)
- [ ] Integration tests pass (no regressions)
- [ ] All handlers are <= 100 lines (thin, focused)
- [ ] All endpoints are <= 10 lines (just wrapper)

## Execution Order

1. **Start with roles_handlers.py** - Simplest, most tested patterns
   - Extract functions
   - Write 65 tests
   - Validate

2. **Then secrets_handlers.py** - Key Vault integration
   - Extract functions
   - Write 45 tests
   - Validate

3. **Finally permissions_handlers.py** - Complex queries
   - Extract functions
   - Write 50 tests
   - Validate

4. **Refactor endpoints** - Last step, lowest risk
   - All endpoints become thin wrappers
   - Validate integration tests pass
