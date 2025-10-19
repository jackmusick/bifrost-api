# Phase 1: API Integration Tests - Detailed Specification

**Target: +2000 lines coverage | Timeline: 2 weeks | Priority: Critical**

## Overview

API endpoints are the entry points to the system. They need **integration tests** that make real HTTP requests to running Azure Functions. We'll use `func start` + `requests` library to test complete request/response flows.

## Testing Infrastructure

### Prerequisites
1. **Docker Compose running:**
   ```bash
   docker compose up -d  # Azurite on ports 10000-10002
   ```

2. **Function App running:**
   ```bash
   cd api
   func start  # Runs on http://localhost:7071
   ```

3. **Test fixtures for HTTP requests:**
   ```python
   @pytest.fixture(scope="module")
   def api_base_url():
       return "http://localhost:7071"

   @pytest.fixture(scope="module")
   def test_org_id():
       """Create test organization and return ID"""
       # Create test org in Azurite
       return "test-org-integration-123"

   @pytest.fixture
   def auth_headers(test_org_id):
       """Headers for authenticated requests"""
       return {
           "x-organization-id": test_org_id,
           "x-ms-client-principal": base64.b64encode(
               json.dumps({
                   "userId": "test-user-456",
                   "userDetails": "test@example.com",
                   "userRoles": ["Owner"]
               }).encode()
           ).decode()
       }
   ```

---

## Priority 1: OAuth API (Week 1, Days 1-3)

**File:** `tests/integration/api/test_oauth_endpoints.py`
**Source:** `functions/oauth_api.py`
**Impact:** +300 lines

### Endpoints to Test

#### `GET /api/oauth/providers`
**Purpose:** List available OAuth providers

**Test Cases:**
```python
def test_list_oauth_providers(api_base_url):
    """Should return list of configured OAuth providers"""
    response = requests.get(f"{api_base_url}/api/oauth/providers")

    assert response.status_code == 200
    data = response.json()
    assert "providers" in data
    assert isinstance(data["providers"], list)
    assert "microsoft" in [p["id"] for p in data["providers"]]
```

#### `POST /api/oauth/connect`
**Purpose:** Initiate OAuth connection flow

**Test Cases:**
```python
def test_oauth_connect_microsoft(api_base_url, auth_headers, test_org_id):
    """Should initiate OAuth flow and return redirect URL"""
    response = requests.post(
        f"{api_base_url}/api/oauth/connect",
        headers=auth_headers,
        json={
            "provider": "microsoft",
            "scopes": ["User.Read", "Mail.Send"]
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "authUrl" in data
    assert "state" in data
    assert "microsoft" in data["authUrl"]

    # Verify state was stored in table storage for CSRF protection
    # (Check Azurite)

def test_oauth_connect_invalid_provider(api_base_url, auth_headers):
    """Should reject invalid provider"""
    response = requests.post(
        f"{api_base_url}/api/oauth/connect",
        headers=auth_headers,
        json={"provider": "invalid_provider"}
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
```

#### `GET /api/oauth/callback`
**Purpose:** Handle OAuth provider callback

**Test Cases:**
```python
def test_oauth_callback_success(api_base_url, auth_headers, test_org_id):
    """Should complete OAuth flow and store connection"""
    # Step 1: Initiate flow to get state
    connect_response = requests.post(
        f"{api_base_url}/api/oauth/connect",
        headers=auth_headers,
        json={"provider": "microsoft"}
    )
    state = connect_response.json()["state"]

    # Step 2: Simulate callback with mock authorization code
    # (In real test, you'd mock the OAuth provider's token endpoint)
    with patch('services.oauth_provider.OAuthProvider.exchange_code_for_token') as mock_exchange:
        mock_exchange.return_value = {
            "access_token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
            "expires_in": 3600
        }

        callback_response = requests.get(
            f"{api_base_url}/api/oauth/callback",
            params={
                "code": "mock_auth_code",
                "state": state
            }
        )

    assert callback_response.status_code == 302  # Redirect to success page

    # Verify connection was stored
    # Query Azurite to check connection exists

def test_oauth_callback_invalid_state(api_base_url):
    """Should reject callback with invalid/expired state"""
    response = requests.get(
        f"{api_base_url}/api/oauth/callback",
        params={
            "code": "mock_code",
            "state": "invalid_state_token"
        }
    )

    assert response.status_code == 400
```

#### `GET /api/oauth/connections`
**Purpose:** List OAuth connections for organization

**Test Cases:**
```python
def test_list_oauth_connections(api_base_url, auth_headers, test_org_id):
    """Should return list of OAuth connections"""
    # Setup: Create a test connection first
    # (Helper function to insert into Azurite)

    response = requests.get(
        f"{api_base_url}/api/oauth/connections",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "connections" in data
    assert isinstance(data["connections"], list)
```

#### `DELETE /api/oauth/connections/{connection_id}`
**Purpose:** Revoke OAuth connection

**Test Cases:**
```python
def test_revoke_oauth_connection(api_base_url, auth_headers, test_connection_id):
    """Should revoke connection and delete tokens"""
    response = requests.delete(
        f"{api_base_url}/api/oauth/connections/{test_connection_id}",
        headers=auth_headers
    )

    assert response.status_code == 200

    # Verify connection was marked as revoked
    # Verify tokens were deleted from storage
```

### Mocking Strategy for OAuth Tests

**Mock OAuth Provider:**
```python
@pytest.fixture(autouse=True)
def mock_oauth_provider_requests():
    """Mock external OAuth provider HTTP calls"""
    with patch('requests.post') as mock_post:
        # Mock token exchange
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "access_token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer"
        }
        yield mock_post
```

---

## Priority 2: Forms API (Week 1, Days 4-5)

**File:** `tests/integration/api/test_forms_endpoints.py`
**Source:** `functions/forms.py`
**Impact:** +240 lines

### Endpoints to Test

#### `POST /api/forms`
**Purpose:** Create new form

**Test Cases:**
```python
def test_create_form_success(api_base_url, auth_headers):
    """Should create form and return form_id"""
    response = requests.post(
        f"{api_base_url}/api/forms",
        headers=auth_headers,
        json={
            "name": "User Onboarding",
            "description": "Onboard new users",
            "fields": [
                {
                    "type": "text",
                    "name": "email",
                    "label": "Email Address",
                    "required": True
                }
            ]
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert "formId" in data
    assert data["name"] == "User Onboarding"

def test_create_form_missing_required_fields(api_base_url, auth_headers):
    """Should reject form without required fields"""
    response = requests.post(
        f"{api_base_url}/api/forms",
        headers=auth_headers,
        json={"description": "Missing name"}
    )

    assert response.status_code == 400
```

#### `GET /api/forms`
**Purpose:** List forms for organization

**Test Cases:**
```python
def test_list_forms(api_base_url, auth_headers):
    """Should return list of forms"""
    # Setup: Create 2 test forms

    response = requests.get(
        f"{api_base_url}/api/forms",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "forms" in data
    assert len(data["forms"]) >= 2
```

#### `GET /api/forms/{form_id}`
**Purpose:** Get single form

**Test Cases:**
```python
def test_get_form_success(api_base_url, auth_headers, test_form_id):
    """Should return form details"""
    response = requests.get(
        f"{api_base_url}/api/forms/{test_form_id}",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["formId"] == test_form_id

def test_get_form_not_found(api_base_url, auth_headers):
    """Should return 404 for nonexistent form"""
    response = requests.get(
        f"{api_base_url}/api/forms/nonexistent-form-id",
        headers=auth_headers
    )

    assert response.status_code == 404
```

#### `PUT /api/forms/{form_id}`
**Purpose:** Update form

**Test Cases:**
```python
def test_update_form_success(api_base_url, auth_headers, test_form_id):
    """Should update form fields"""
    response = requests.put(
        f"{api_base_url}/api/forms/{test_form_id}",
        headers=auth_headers,
        json={
            "name": "Updated Form Name",
            "description": "Updated description"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Form Name"
```

#### `DELETE /api/forms/{form_id}`
**Purpose:** Soft delete form

**Test Cases:**
```python
def test_delete_form_success(api_base_url, auth_headers, test_form_id):
    """Should soft delete form"""
    response = requests.delete(
        f"{api_base_url}/api/forms/{test_form_id}",
        headers=auth_headers
    )

    assert response.status_code == 204

    # Verify form is marked as retired
    get_response = requests.get(
        f"{api_base_url}/api/forms/{test_form_id}",
        headers=auth_headers
    )
    assert get_response.status_code == 404  # Retired forms are hidden
```

#### `POST /api/forms/{form_id}/submit`
**Purpose:** Submit form with workflow launch

**Test Cases:**
```python
def test_submit_form_with_workflow(api_base_url, auth_headers, test_form_id):
    """Should submit form and launch associated workflow"""
    response = requests.post(
        f"{api_base_url}/api/forms/{test_form_id}/submit",
        headers=auth_headers,
        json={
            "email": "newuser@example.com",
            "name": "John Doe"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "executionId" in data  # Workflow was launched
    assert data["status"] in ["Pending", "Running", "Success"]
```

---

## Priority 3: Roles API (Week 2, Days 1-2)

**File:** `tests/integration/api/test_roles_endpoints.py`
**Source:** `functions/roles.py`
**Impact:** +140 lines

### Endpoints to Test

#### `POST /api/roles/assign`
**Purpose:** Assign role to user

**Test Cases:**
```python
def test_assign_role_success(api_base_url, admin_headers):
    """Should assign role to user"""
    response = requests.post(
        f"{api_base_url}/api/roles/assign",
        headers=admin_headers,
        json={
            "userId": "user-123",
            "role": "Contributor"
        }
    )

    assert response.status_code == 200

def test_assign_role_unauthorized(api_base_url, user_headers):
    """Should reject role assignment from non-admin"""
    response = requests.post(
        f"{api_base_url}/api/roles/assign",
        headers=user_headers,  # Regular user, not admin
        json={
            "userId": "user-456",
            "role": "Admin"
        }
    )

    assert response.status_code == 403
```

#### `POST /api/roles/revoke`
**Purpose:** Revoke role from user

#### `GET /api/roles/users/{user_id}`
**Purpose:** Get user's roles

#### `GET /api/roles/members`
**Purpose:** List all members and their roles

---

## Priority 4: Permissions API (Week 2, Day 3)

**File:** `tests/integration/api/test_permissions_endpoints.py`
**Source:** `functions/permissions.py`
**Impact:** +90 lines

### Endpoints to Test

#### `GET /api/permissions/check`
**Purpose:** Check if user has specific permission

**Test Cases:**
```python
def test_permission_check_allowed(api_base_url, auth_headers):
    """Should return true when user has permission"""
    response = requests.get(
        f"{api_base_url}/api/permissions/check",
        headers=auth_headers,
        params={
            "resource": "forms",
            "action": "read"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is True

def test_permission_check_denied(api_base_url, auth_headers):
    """Should return false when user lacks permission"""
    response = requests.get(
        f"{api_base_url}/api/permissions/check",
        headers=auth_headers,
        params={
            "resource": "workflows",
            "action": "delete"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is False
```

---

## Common Test Utilities

Create `tests/integration/api/conftest.py`:

```python
"""Shared fixtures for API integration tests"""

import base64
import json
import pytest
import requests
from azure.data.tables import TableServiceClient


@pytest.fixture(scope="module")
def api_base_url():
    """Base URL for API (func start must be running)"""
    return "http://localhost:7071"


@pytest.fixture(scope="module")
def azurite_connection_string():
    """Connection string for Azurite TEST environment"""
    return (
        "DefaultEndpointsProtocol=http;"
        "AccountName=devstoreaccount1;"
        "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
        "BlobEndpoint=http://localhost:10100/devstoreaccount1;"
        "QueueEndpoint=http://localhost:10101/devstoreaccount1;"
        "TableEndpoint=http://localhost:10102/devstoreaccount1;"
    )


@pytest.fixture(scope="module")
def table_service(azurite_connection_string):
    """TableServiceClient for test data setup"""
    return TableServiceClient.from_connection_string(azurite_connection_string)


@pytest.fixture(scope="module")
def test_org_id(table_service):
    """Create test organization and return ID"""
    org_id = "test-org-integration-123"

    # Create organization in Azurite
    table_service.get_table_client("Organizations").upsert_entity({
        "PartitionKey": "Organizations",
        "RowKey": f"org:{org_id}",
        "org_id": org_id,
        "name": "Test Organization",
        "is_active": True
    })

    yield org_id

    # Cleanup after tests
    try:
        table_service.get_table_client("Organizations").delete_entity(
            partition_key="Organizations",
            row_key=f"org:{org_id}"
        )
    except:
        pass


@pytest.fixture
def auth_headers(test_org_id):
    """Headers for authenticated requests (Owner role)"""
    principal = {
        "userId": "test-user-456",
        "userDetails": "test@example.com",
        "userRoles": ["Owner"]
    }

    return {
        "x-organization-id": test_org_id,
        "x-ms-client-principal": base64.b64encode(
            json.dumps(principal).encode()
        ).decode(),
        "Content-Type": "application/json"
    }


@pytest.fixture
def admin_headers(test_org_id):
    """Headers for admin user"""
    principal = {
        "userId": "admin-user-789",
        "userDetails": "admin@example.com",
        "userRoles": ["Admin"]
    }

    return {
        "x-organization-id": test_org_id,
        "x-ms-client-principal": base64.b64encode(
            json.dumps(principal).encode()
        ).decode(),
        "Content-Type": "application/json"
    }


@pytest.fixture
def user_headers(test_org_id):
    """Headers for regular user (Contributor role)"""
    principal = {
        "userId": "regular-user-999",
        "userDetails": "user@example.com",
        "userRoles": ["Contributor"]
    }

    return {
        "x-organization-id": test_org_id,
        "x-ms-client-principal": base64.b64encode(
            json.dumps(principal).encode()
        ).decode(),
        "Content-Type": "application/json"
    }


@pytest.fixture
def test_form_id(api_base_url, auth_headers):
    """Create test form and return form_id"""
    response = requests.post(
        f"{api_base_url}/api/forms",
        headers=auth_headers,
        json={
            "name": "Test Form",
            "description": "For integration tests",
            "fields": [
                {"type": "text", "name": "email", "required": True}
            ]
        }
    )

    form_id = response.json()["formId"]
    yield form_id

    # Cleanup
    requests.delete(f"{api_base_url}/api/forms/{form_id}", headers=auth_headers)
```

---

## Running Integration Tests

### Prerequisites Check
```bash
# Check if func is running
curl http://localhost:7071/api/health || echo "Start func with: func start"

# Check if Azurite TEST is running (ports 10100-10102)
curl http://localhost:10102 || echo "Azurite-test should be running (docker compose up -d already started it)"
```

### Run Tests
```bash
# Run all API integration tests
pytest tests/integration/api/ -v

# Run specific endpoint tests
pytest tests/integration/api/test_oauth_endpoints.py -v

# Run with coverage
pytest tests/integration/api/ --cov=functions --cov-report=term-missing
```

---

## Success Criteria

For Phase 1 to be considered complete:

1. ✅ All API endpoint test files created
2. ✅ Minimum 80% coverage for tested endpoint files
3. ✅ All tests pass with func running
4. ✅ Tests properly clean up test data
5. ✅ Tests run reliably (no flaky tests)
6. ✅ Coverage report shows improvement

## Estimated Impact

| Endpoint File | Current Coverage | Target | Lines to Cover |
|---------------|-----------------|--------|----------------|
| oauth_api.py | 17.7% | 80% | +300 |
| forms.py | 15.4% | 75% | +240 |
| roles.py | 27.8% | 80% | +140 |
| permissions.py | 33.5% | 80% | +90 |
| org_config.py | 25.0% | 70% | +100 |
| organizations.py | 31.2% | 75% | +80 |
| secrets.py | 20.4% | 70% | +120 |
| **TOTAL** | | | **+1070** |

Additional coverage from error paths and edge cases: ~+930 lines

**Total Phase 1 Impact: +2000 lines**
