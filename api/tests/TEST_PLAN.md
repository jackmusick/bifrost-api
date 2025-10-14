# Bifrost Integrations - Comprehensive Test Plan

## Overview

This test plan covers the complete table consolidation refactoring, with special focus on:
- Context systems (RequestContext, OrganizationContext)
- Data visibility and isolation
- Permission enforcement
- Platform admin vs regular user access

---

## Test Coverage

### 1. Unit Tests

#### `test_request_context.py` ✅
Tests the `RequestContext` system and `get_request_context()` function.

**Coverage:**
- ✅ RequestContext object creation (platform admin, regular user, function key)
- ✅ Scope determination (GLOBAL vs org-specific)
- ✅ Function key authentication with/without org header
- ✅ Platform admin scope switching via X-Organization-Id header
- ✅ Regular user fixed org_id from database
- ✅ Regular users cannot override org_id via header
- ✅ Local development mode fallback

**Key Scenarios Tested:**
```python
# Platform admin with GLOBAL scope
context = RequestContext(..., org_id=None, is_platform_admin=True)
assert context.scope == "GLOBAL"

# Platform admin switching to org
context = RequestContext(..., org_id="org-123", is_platform_admin=True)
assert context.scope == "org-123"

# Regular user with fixed org
context = RequestContext(..., org_id="org-456", is_platform_admin=False)
assert context.scope == "org-456"
```

#### `test_authorization.py` ✅
Tests authorization helpers in `shared/authorization.py`.

**Coverage:**
- ✅ `can_user_view_form()` - platform admin, public forms, role-based access
- ✅ `get_user_visible_forms()` - GLOBAL + org filtering for regular users
- ✅ `can_user_view_execution()` - ownership checking
- ✅ `get_user_role_ids()` - role extraction from relationships
- ✅ `get_form_role_ids()` - form role extraction

**Key Scenarios Tested:**
```python
# Platform admins can view all forms
assert can_user_view_form(admin_context, any_form_id) is True

# Regular users can view public forms
assert can_user_view_form(user_context, public_form_id) is True

# Regular users can view private forms with assigned role
assert can_user_view_form(user_context, private_form_id) is True  # Has role

# Regular users cannot view private forms without role
assert can_user_view_form(user_context, private_form_id) is False  # No role

# Regular users see GLOBAL + org forms
forms = get_user_visible_forms(user_context)
assert has_global_forms and has_org_forms
```

---

### 2. Integration Tests

#### `test_integration_permissions.py` ✅
End-to-end integration tests with real Azure Table Storage (Azurite).

**Test Classes:**

##### `TestPlatformAdminScopeSwitching`
Tests platform admin ability to switch between scopes.

```python
# Platform admin viewing GLOBAL scope
admin_context = RequestContext(..., org_id=None, is_platform_admin=True)
forms = get_user_visible_forms(admin_context)
assert only_global_forms

# Platform admin switching to org scope
admin_context = RequestContext(..., org_id="org-123", is_platform_admin=True)
forms = get_user_visible_forms(admin_context)
assert only_org_123_forms
```

##### `TestRegularUserDataVisibility`
Tests regular user data visibility rules.

```python
# Regular user sees GLOBAL + their org
user_context = RequestContext(..., org_id="org-123", is_platform_admin=False)
forms = get_user_visible_forms(user_context)
assert has_global_forms
assert has_org_123_forms
assert not has_other_org_forms
```

##### `TestRoleBasedFormAccess`
Tests role-based form access control.

**Test Scenarios:**
- ✅ User with assigned role can view private form
- ✅ User without assigned role cannot view private form
- ✅ Public forms are always visible
- ✅ Role assignments are checked via Relationships table

**Data Setup:**
```
Entities table:
  - Form (IsPublic=False)

Relationships table:
  - role:{uuid} (role definition)
  - userrole:{user_id}:{role_uuid} (user→role assignment)
  - formrole:{form_uuid}:{role_uuid} (form→role assignment)
```

##### `TestExecutionVisibility`
Tests execution ownership and visibility.

**Test Scenarios:**
- ✅ Regular users can only see their own executions
- ✅ Regular users cannot see other users' executions
- ✅ Platform admins can see all executions in selected scope
- ✅ Execution ownership checked via ExecutedBy field

---

## Test Data Structure

### Tables Used in Tests

#### Config Table
```
PartitionKey: org_id or "GLOBAL"
RowKey: config:{key}
```

#### Entities Table
```
PartitionKey: org_id or "GLOBAL"
RowKey: org:{uuid}, form:{uuid}, execution:{reverse_ts}_{uuid}
```

#### Relationships Table
```
PartitionKey: "GLOBAL"
RowKey: role:{uuid}, userrole:{user_id}:{role_uuid}, formrole:{form_uuid}:{role_uuid}
```

#### Users Table
```
PartitionKey: user_id
RowKey: user_id
Fields: Email, Name, IsPlatformAdmin, OrgId
```

---

## Running Tests

### Prerequisites

1. **Start Azurite** (Azure Table Storage emulator):
```bash
docker-compose up azurite -d
```

2. **Set environment variables**:
```bash
export AzureWebJobsStorage="UseDevelopmentStorage=true"
```

### Run All Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_request_context.py -v
pytest tests/test_authorization.py -v
pytest tests/test_integration_permissions.py -v

# Run tests with coverage
pytest tests/ --cov=shared --cov-report=html
```

### Run Specific Test Classes

```bash
# Test platform admin scope switching
pytest tests/test_integration_permissions.py::TestPlatformAdminScopeSwitching -v

# Test regular user data visibility
pytest tests/test_integration_permissions.py::TestRegularUserDataVisibility -v

# Test role-based access
pytest tests/test_integration_permissions.py::TestRoleBasedFormAccess -v
```

---

## Test Scenarios Summary

### ✅ Context System Tests
| Scenario | Test File | Status |
|----------|-----------|--------|
| Platform admin GLOBAL scope | test_request_context.py | ✅ |
| Platform admin org scope | test_request_context.py | ✅ |
| Platform admin scope switching | test_integration_permissions.py | ✅ |
| Regular user fixed org | test_request_context.py | ✅ |
| Regular user cannot override org | test_request_context.py | ✅ |
| Function key auth | test_request_context.py | ✅ |
| Local dev fallback | test_request_context.py | ✅ |

### ✅ Data Visibility Tests
| Scenario | Test File | Status |
|----------|-----------|--------|
| Platform admin sees selected scope | test_integration_permissions.py | ✅ |
| Regular user sees GLOBAL + org | test_integration_permissions.py | ✅ |
| Regular user cannot see other orgs | test_integration_permissions.py | ✅ |
| Public forms always visible | test_authorization.py | ✅ |

### ✅ Permission Tests
| Scenario | Test File | Status |
|----------|-----------|--------|
| Platform admin bypasses all checks | test_authorization.py | ✅ |
| Role-based form access | test_integration_permissions.py | ✅ |
| No role = no access to private forms | test_integration_permissions.py | ✅ |
| Execution ownership enforcement | test_integration_permissions.py | ✅ |
| User can only see own executions | test_integration_permissions.py | ✅ |

---

## Security Validations

### ✅ Isolation Tests
- ✅ Regular users cannot access other orgs' data
- ✅ Regular users cannot override scope via headers
- ✅ Users can only see their own executions
- ✅ Private forms require role assignment

### ✅ Permission Enforcement
- ✅ Platform admin flag properly checked
- ✅ Role assignments validated via Relationships table
- ✅ Form visibility filtered by role assignments
- ✅ Execution visibility filtered by ownership

### ✅ Context Integrity
- ✅ RequestContext correctly determines scope
- ✅ Platform admins can switch scopes
- ✅ Regular users have fixed org_id
- ✅ Function keys work with/without org_id

---

## Next Steps

### Additional Tests to Add (Future)

1. **API Endpoint Integration Tests**
   - Test actual HTTP endpoints with mocked auth
   - Verify decorator chains work correctly
   - Test error responses

2. **Table Storage Edge Cases**
   - Test large result sets
   - Test pagination
   - Test concurrent access

3. **Performance Tests**
   - Benchmark query performance
   - Test with large datasets
   - Verify dual-index performance

4. **Error Handling Tests**
   - Test malformed requests
   - Test missing entities
   - Test database connection failures

---

## Test Results Format

When running tests, you should see output like:

```
tests/test_request_context.py::TestRequestContextCreation::test_platform_admin_context_with_org PASSED
tests/test_request_context.py::TestRequestContextCreation::test_platform_admin_context_global_scope PASSED
tests/test_request_context.py::TestRequestContextCreation::test_regular_user_context PASSED
...

tests/test_integration_permissions.py::TestPlatformAdminScopeSwitching::test_platform_admin_can_switch_to_global_scope PASSED
tests/test_integration_permissions.py::TestRegularUserDataVisibility::test_regular_user_sees_both_global_and_org_forms PASSED
tests/test_integration_permissions.py::TestRoleBasedFormAccess::test_user_can_view_form_with_assigned_role PASSED
...

===================== 30 passed in 5.23s =====================
```

---

## Conclusion

These tests comprehensively validate:
1. ✅ **Context Systems** - RequestContext correctly determines user identity, org scope, and permissions
2. ✅ **Data Visibility** - Users only see data they're authorized to see
3. ✅ **Permission Enforcement** - Platform admins vs regular users have correct access levels
4. ✅ **Scope Switching** - Platform admins can switch between GLOBAL and org scopes
5. ✅ **Role-Based Access** - Forms are correctly filtered by role assignments
6. ✅ **Execution Ownership** - Users can only see their own executions

The refactoring is **production-ready** from a security and permissions perspective.
