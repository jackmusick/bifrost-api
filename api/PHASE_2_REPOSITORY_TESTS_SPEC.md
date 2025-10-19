# Phase 2: Repository Unit Tests - Detailed Specification

**Target: +800 lines coverage | Timeline: 1 week | Priority: High**

## Overview

Repository classes are the data access layer. They wrap TableStorageService and provide type-safe, domain-focused methods. We need unit tests that mock TableStorageService at the boundary.

## Testing Strategy

### Mocking Pattern
```python
@pytest.fixture
def mock_table_service():
    """Mock TableStorageService for all repository tests"""
    with patch('shared.repositories.base.TableStorageService') as mock:
        instance = MagicMock()
        mock.return_value = instance
        yield instance

@pytest.fixture
def mock_context():
    """Mock RequestContext for repositories that need it"""
    return MagicMock(
        org_id="test-org-123",
        user_id="test-user-456",
        scope="test-org-123"
    )
```

### Test Structure
Each repository test file should cover:
1. **CRUD Operations** - Create, Read, Update, Delete
2. **Query Methods** - List, search, filter operations
3. **Error Handling** - Not found, validation errors, storage errors
4. **Edge Cases** - Empty results, pagination, null values
5. **Business Logic** - Any repository-specific validation or transformation

---

## Priority 1: FormsRepository (148 lines uncovered)

**File:** `tests/unit/repositories/test_forms_repository.py`
**Source:** `shared/repositories/forms.py`
**Impact:** +120 lines

### Methods to Test

#### `create_form(form_data: dict) -> Form`
**Test Cases:**
- ✅ Valid form creation with all fields
- ✅ Form creation with minimal required fields
- ✅ Assigns unique form_id
- ✅ Sets created_at timestamp
- ✅ Stores in correct partition (org_id)
- ❌ Raises ValidationError for missing required fields
- ❌ Raises ValidationError for invalid field types

**Test Pattern:**
```python
def test_create_form_success(mock_table_service, mock_context):
    repo = FormsRepository(mock_context)
    form_data = {
        "name": "User Onboarding",
        "description": "Onboard new users",
        "fields": [
            {"type": "text", "name": "email", "required": True}
        ]
    }

    result = repo.create_form(form_data)

    # Verify form object
    assert result.name == "User Onboarding"
    assert result.form_id is not None
    assert result.org_id == "test-org-123"

    # Verify TableStorageService was called correctly
    mock_table_service.insert_entity.assert_called_once()
    call_args = mock_table_service.insert_entity.call_args
    entity = call_args[0][1]  # Second argument is the entity
    assert entity["PartitionKey"] == "test-org-123"
    assert entity["RowKey"].startswith("form:")
```

#### `get_form(form_id: str) -> Optional[Form]`
**Test Cases:**
- ✅ Returns form when found
- ✅ Returns None when not found
- ✅ Handles storage errors gracefully
- ✅ Deserializes fields correctly (JSON to objects)

#### `list_forms(org_id: str) -> List[Form]`
**Test Cases:**
- ✅ Returns list of forms for organization
- ✅ Returns empty list when no forms
- ✅ Filters by org_id correctly
- ✅ Excludes retired/deleted forms

#### `update_form(form_id: str, updates: dict) -> Form`
**Test Cases:**
- ✅ Updates specified fields
- ✅ Preserves unchanged fields
- ✅ Updates updated_at timestamp
- ❌ Raises NotFoundError when form doesn't exist
- ❌ Raises ValidationError for invalid updates

#### `delete_form(form_id: str) -> bool`
**Test Cases:**
- ✅ Soft deletes form (sets is_retired=True)
- ✅ Returns True on success
- ❌ Raises NotFoundError when form doesn't exist

---

## Priority 2: RolesRepository (119 lines uncovered)

**File:** `tests/unit/repositories/test_roles_repository.py`
**Source:** `shared/repositories/roles.py`
**Impact:** +95 lines

### Methods to Test

#### `assign_role(user_id: str, org_id: str, role: str) -> bool`
**Test Cases:**
- ✅ Creates role assignment
- ✅ Stores in Relationships table with correct indexes
- ✅ Creates forward index (user -> role)
- ✅ Creates reverse index (org -> user roles)
- ❌ Raises ValidationError for invalid role
- ❌ Handles duplicate assignment gracefully

#### `revoke_role(user_id: str, org_id: str, role: str) -> bool`
**Test Cases:**
- ✅ Removes role assignment
- ✅ Deletes both forward and reverse indexes
- ✅ Returns True on success
- ✅ Returns False when assignment doesn't exist

#### `get_user_roles(user_id: str, org_id: str) -> List[str]`
**Test Cases:**
- ✅ Returns list of roles for user in org
- ✅ Returns empty list when no roles
- ✅ Queries correct partition and key pattern

#### `list_org_members(org_id: str) -> List[Dict]`
**Test Cases:**
- ✅ Returns list of users with their roles
- ✅ Groups roles by user
- ✅ Returns empty list when no members

---

## Priority 3: OrganizationsRepository (64 lines uncovered)

**File:** `tests/unit/repositories/test_organizations_repository.py`
**Source:** `shared/repositories/organizations.py`
**Impact:** +50 lines

### Methods to Test

#### `create_organization(org_data: dict) -> Organization`
**Test Cases:**
- ✅ Creates organization with unique org_id
- ✅ Sets default is_active=True
- ✅ Stores in Organizations table
- ❌ Raises ValidationError for missing name

#### `get_organization(org_id: str) -> Optional[Organization]`
**Test Cases:**
- ✅ Returns organization when found
- ✅ Returns None when not found
- ✅ Deserializes config JSON correctly

#### `update_organization(org_id: str, updates: dict) -> Organization`
**Test Cases:**
- ✅ Updates organization fields
- ✅ Merges config updates (doesn't replace entire config)
- ❌ Raises NotFoundError when org doesn't exist

#### `deactivate_organization(org_id: str) -> bool`
**Test Cases:**
- ✅ Sets is_active=False
- ✅ Returns True on success
- ❌ Raises NotFoundError when org doesn't exist

---

## Priority 4: ConfigRepository (60 lines uncovered)

**File:** `tests/unit/repositories/test_config_repository.py`
**Source:** `shared/repositories/config.py`
**Impact:** +48 lines

### Methods to Test

#### `get_config_value(key: str, org_id: Optional[str]) -> Any`
**Test Cases:**
- ✅ Returns org-specific value when exists
- ✅ Falls back to GLOBAL value when org-specific doesn't exist
- ✅ Returns None when key doesn't exist anywhere
- ✅ Deserializes JSON values correctly

**Test Pattern:**
```python
def test_get_config_value_org_specific(mock_table_service):
    repo = ConfigRepository()

    # Mock org-specific value exists
    mock_table_service.get_entity.return_value = {
        "PartitionKey": "org-123",
        "RowKey": "config:email_template",
        "value": '"custom_template.html"'
    }

    result = repo.get_config_value("email_template", org_id="org-123")

    assert result == "custom_template.html"
    mock_table_service.get_entity.assert_called_with(
        table_name="Config",
        partition_key="org-123",
        row_key="config:email_template"
    )

def test_get_config_value_fallback_to_global(mock_table_service):
    # Mock org-specific doesn't exist, but GLOBAL does
    def side_effect(*args, **kwargs):
        if kwargs["partition_key"] == "org-123":
            raise ResourceNotFoundError("Not found")
        return {
            "PartitionKey": "GLOBAL",
            "RowKey": "config:email_template",
            "value": '"default_template.html"'
        }

    mock_table_service.get_entity.side_effect = side_effect

    result = repo.get_config_value("email_template", org_id="org-123")

    assert result == "default_template.html"
    assert mock_table_service.get_entity.call_count == 2  # Tried org, fell back to GLOBAL
```

#### `set_config_value(key: str, value: Any, org_id: Optional[str]) -> bool`
**Test Cases:**
- ✅ Sets org-specific config value
- ✅ Sets GLOBAL config value when org_id is None
- ✅ Serializes complex values to JSON
- ✅ Updates existing value (upsert behavior)

#### `delete_config_value(key: str, org_id: Optional[str]) -> bool`
**Test Cases:**
- ✅ Deletes config value
- ✅ Returns True on success
- ✅ Returns False when value doesn't exist

---

## Priority 5: UsersRepository (49 lines uncovered)

**File:** `tests/unit/repositories/test_users_repository.py`
**Source:** `shared/repositories/users.py`
**Impact:** +40 lines

### Methods to Test

#### `create_user(user_data: dict) -> User`
**Test Cases:**
- ✅ Creates user with email as primary key
- ✅ Sets created_at timestamp
- ✅ Hashes password if provided
- ❌ Raises ValidationError for invalid email
- ❌ Raises ValidationError for missing required fields

#### `get_user(email: str) -> Optional[User]`
**Test Cases:**
- ✅ Returns user when found
- ✅ Returns None when not found
- ✅ Normalizes email to lowercase

#### `has_any_users() -> bool`
**Test Cases:**
- ✅ Returns True when users exist
- ✅ Returns False when no users
- ✅ Uses efficient query (select=["RowKey"], top=1)

**Test Pattern:**
```python
def test_has_any_users_true(mock_table_service):
    repo = UsersRepository()

    # Mock query returns one result
    mock_table_service.query_entities.return_value = [
        {"RowKey": "user:test@example.com"}
    ]

    result = repo.has_any_users()

    assert result is True
    mock_table_service.query_entities.assert_called_with(
        table_name="Entities",
        filter="RowKey ge 'user:' and RowKey lt 'user;'",
        select=["RowKey"],
        top=1
    )
```

---

## Priority 6: ExecutionsRepository (76 lines uncovered)

**File:** `tests/unit/repositories/test_executions_repository.py`
**Source:** `shared/repositories/executions.py`
**Impact:** +60 lines

### Methods to Test

#### `create_execution(execution_data: dict) -> Execution`
**Test Cases:**
- ✅ Creates execution with dual indexing
- ✅ Creates ByOrg index (PartitionKey=org:123, RowKey=exec:456)
- ✅ Creates ByUser index (PartitionKey=user:789, RowKey=exec:456)
- ✅ Stores both indexes in Executions table
- ✅ Sets status to PENDING by default

#### `get_execution(execution_id: str, org_id: str) -> Optional[Execution]`
**Test Cases:**
- ✅ Returns execution from ByOrg index
- ✅ Returns None when not found
- ✅ Deserializes input_data and result JSON

#### `update_execution(execution_id: str, updates: dict) -> Execution`
**Test Cases:**
- ✅ Updates execution in ByOrg index
- ✅ Updates execution in ByUser index (dual-index consistency)
- ✅ Updates duration_ms, status, result fields
- ❌ Raises NotFoundError when execution doesn't exist

#### `list_executions(org_id: str, limit: int) -> List[Execution]`
**Test Cases:**
- ✅ Returns list of executions for org
- ✅ Respects limit parameter
- ✅ Orders by RowKey (execution_id) descending
- ✅ Returns empty list when no executions

---

## Common Test Utilities

Create `tests/unit/repositories/conftest.py`:

```python
"""Shared fixtures for repository tests"""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_table_service():
    """Mock TableStorageService for all repository tests"""
    with patch('shared.repositories.base.TableStorageService') as mock:
        instance = MagicMock()
        mock.return_value = instance
        yield instance


@pytest.fixture
def mock_context():
    """Mock RequestContext for scoped repositories"""
    context = MagicMock()
    context.org_id = "test-org-123"
    context.user_id = "test-user-456"
    context.scope = "test-org-123"
    context.caller.email = "test@example.com"
    return context


@pytest.fixture
def sample_form_data():
    """Sample form data for testing"""
    return {
        "name": "User Onboarding",
        "description": "Onboard new users",
        "fields": [
            {
                "type": "text",
                "name": "email",
                "label": "Email Address",
                "required": True
            },
            {
                "type": "text",
                "name": "name",
                "label": "Full Name",
                "required": True
            }
        ]
    }


@pytest.fixture
def sample_organization_data():
    """Sample organization data for testing"""
    return {
        "name": "Test Organization",
        "config": {
            "default_license": "O365_E3",
            "welcome_email_template": "welcome_v1"
        }
    }
```

---

## Error Handling Patterns

All repositories should test these error scenarios:

### 1. ResourceNotFoundError
```python
def test_get_entity_not_found(mock_table_service):
    from azure.core.exceptions import ResourceNotFoundError

    mock_table_service.get_entity.side_effect = ResourceNotFoundError("Not found")

    repo = SomeRepository()
    result = repo.get_something("nonexistent-id")

    assert result is None  # Repository should return None, not raise
```

### 2. ValidationError
```python
def test_create_entity_validation_error(mock_table_service):
    from shared.error_handling import ValidationError

    repo = SomeRepository()

    with pytest.raises(ValidationError) as exc_info:
        repo.create_something({})  # Missing required fields

    assert "required" in str(exc_info.value).lower()
```

### 3. Storage Errors
```python
def test_storage_error_handling(mock_table_service):
    from azure.core.exceptions import ServiceRequestError

    mock_table_service.insert_entity.side_effect = ServiceRequestError("Network error")

    repo = SomeRepository()

    with pytest.raises(ServiceRequestError):
        repo.create_something({"valid": "data"})
```

---

## Success Criteria

For Phase 2 to be considered complete:

1. ✅ All 6 repository test files created
2. ✅ Minimum 85% coverage for each repository file
3. ✅ All tests pass: `pytest tests/unit/repositories/ -v`
4. ✅ Coverage improves: `pytest --cov=shared/repositories`
5. ✅ No regressions in other tests
6. ✅ Test patterns are consistent and maintainable

## Estimated Impact

| Repository | Current Coverage | Target | Lines to Cover |
|------------|-----------------|--------|----------------|
| FormsRepository | 11.9% | 85% | +120 |
| RolesRepository | 16.2% | 85% | +95 |
| OrganizationsRepository | 20.0% | 85% | +50 |
| ConfigRepository | 23.1% | 85% | +48 |
| UsersRepository | 26.9% | 85% | +40 |
| ExecutionsRepository | 57.5% | 90% | +60 |
| **TOTAL** | | | **+413** |

Additional coverage from error paths and edge cases: ~+387 lines

**Total Phase 2 Impact: +800 lines**
