# Comprehensive Testing Refactor Specification

## Executive Summary

**Objective:** Transform test suite from mock-heavy pseudo-integration tests to real integration tests that exercise the actual Azure Functions HTTP stack with isolated infrastructure.

**Key Principles:**
1. **Real HTTP requests** - Integration tests hit actual `func start` server
2. **Isolated infrastructure** - Dedicated Azurite (ports 10100-10102) and Functions (port 8080)
3. **No seed data** - Create entities organically through API calls
4. **Test real workflows** - Follow actual user journeys from first login to complex workflows
5. **Minimal mocking** - Only mock what we can't run locally (Key Vault, Microsoft Graph)

---

## Infrastructure Setup

### Dedicated Test Ports (Never Conflict with Dev)

| Service | Dev Ports | Test Ports |
|---------|-----------|------------|
| **Azurite Blob** | 10000 | 10100 |
| **Azurite Queue** | 10001 | 10101 |
| **Azurite Table** | 10002 | 10102 |
| **Azure Functions** | 7071 | 8080 |

### Test Environment Configuration

```python
# tests/conftest.py (session fixtures)

TEST_AZURITE_CONNECTION = (
    "DefaultEndpointsProtocol=http;"
    "AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    "BlobEndpoint=http://127.0.0.1:10100/devstoreaccount1;"
    "QueueEndpoint=http://127.0.0.1:10101/devstoreaccount1;"
    "TableEndpoint=http://127.0.0.1:10102/devstoreaccount1;"
)

TEST_FUNCTIONS_PORT = 8080
TEST_FUNCTIONS_URL = f"http://localhost:{TEST_FUNCTIONS_PORT}"
```

---

## Phase 1: Test Infrastructure Setup

### 1.1 Dedicated Azurite Instance

```python
# tests/conftest.py

import subprocess
import pytest
import time
import shutil
import os

@pytest.fixture(scope="session")
def test_azurite():
    """
    Start dedicated Azurite instance for tests on ports 10100-10102.
    Completely isolated from dev docker-compose (ports 10000-10002).
    """
    storage_path = "/tmp/azurite-tests"

    # Clean any previous test data
    shutil.rmtree(storage_path, ignore_errors=True)
    os.makedirs(storage_path, exist_ok=True)

    # Start Azurite on test ports
    process = subprocess.Popen([
        "npx", "azurite",
        "--silent",
        "--location", storage_path,
        "--blobPort", "10100",
        "--queuePort", "10101",
        "--tablePort", "10102"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Wait for Azurite to start
    time.sleep(3)

    yield {
        "connection_string": TEST_AZURITE_CONNECTION,
        "blob_port": 10100,
        "queue_port": 10101,
        "table_port": 10102
    }

    # Cleanup
    process.terminate()
    process.wait(timeout=10)
    shutil.rmtree(storage_path, ignore_errors=True)
```

### 1.2 Mock Key Vault

```python
# tests/conftest.py

@pytest.fixture(scope="session", autouse=True)
def mock_key_vault():
    """
    Mock Azure Key Vault globally for all tests.
    We can't connect to real Key Vault in tests.
    """
    from unittest.mock import MagicMock, patch

    mock_client = MagicMock()

    # In-memory secret storage
    secrets_store = {}

    def mock_set_secret(name, value):
        secrets_store[name] = value
        return MagicMock(name=name, value=value)

    def mock_get_secret(name):
        if name not in secrets_store:
            from azure.core.exceptions import ResourceNotFoundError
            raise ResourceNotFoundError(f"Secret '{name}' not found")
        return MagicMock(name=name, value=secrets_store[name])

    def mock_delete_secret(name):
        if name in secrets_store:
            del secrets_store[name]
        return MagicMock()

    mock_client.set_secret = mock_set_secret
    mock_client.get_secret = mock_get_secret
    mock_client.begin_delete_secret = lambda name: MagicMock(wait=lambda: mock_delete_secret(name))

    # Patch SecretClient globally
    with patch("shared.keyvault.SecretClient", return_value=mock_client):
        yield mock_client
```

### 1.3 Azure Functions Test Server

```python
# tests/conftest.py

@pytest.fixture(scope="session")
def azure_functions_server(test_azurite, mock_key_vault):
    """
    Start Azure Functions on port 8080 with test Azurite connection.
    Isolated from dev Functions running on port 7071.
    """
    import requests

    # Environment for Functions process
    env = os.environ.copy()
    env["AzureWebJobsStorage"] = test_azurite["connection_string"]
    env["AZURE_KEY_VAULT_URL"] = "https://test-vault.vault.azure.net/"
    env["FUNCTIONS_WORKER_RUNTIME"] = "python"

    # Start Functions on test port
    process = subprocess.Popen(
        ["func", "start", "--port", str(TEST_FUNCTIONS_PORT)],
        cwd=os.path.join(os.path.dirname(__file__), "..", "api"),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Wait for Functions to be ready (up to 60 seconds)
    base_url = TEST_FUNCTIONS_URL
    for i in range(60):
        try:
            # Try to hit a simple endpoint
            response = requests.get(f"{base_url}/api/data-providers", timeout=2)
            if response.status_code in [200, 401]:  # 401 is fine - server is up
                print(f"\n✓ Azure Functions ready on {base_url}")
                break
        except Exception as e:
            if i == 59:
                raise RuntimeError(f"Azure Functions failed to start: {e}")
            time.sleep(1)

    yield base_url

    # Cleanup
    process.terminate()
    process.wait(timeout=10)
```

### 1.4 Test Authentication Helpers

```python
# tests/helpers/auth.py

import jwt
from datetime import datetime, timedelta

def create_test_jwt(user_id="test-user", email="test@example.com", name="Test User"):
    """
    Create test JWT token for authentication.
    In integration tests, this bypasses real Azure AD.
    """
    payload = {
        "oid": user_id,
        "preferred_username": email,
        "name": name,
        "exp": datetime.utcnow() + timedelta(hours=2),
        "iat": datetime.utcnow(),
        "iss": "https://login.microsoftonline.com/test-tenant/v2.0",
        "aud": "test-client-id"
    }
    # Sign with test secret (middleware should accept this in test mode)
    return jwt.encode(payload, "test-secret", algorithm="HS256")

def auth_headers(token):
    """Create authorization headers with JWT token"""
    return {"Authorization": f"Bearer {token}"}

def org_headers(org_id, token):
    """Create headers with org context and auth"""
    return {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": org_id
    }
```

---

## Phase 2: Real User Journey Integration Tests

### Test Scenario Order (Critical - Follows Actual User Flow)

**1. First User Becomes Platform Admin**
- User authenticates for first time
- Auto-created as PlatformAdmin
- Can access platform-wide resources

**2. Platform Admin Creates Organizations**
- Create organization with domain
- Verify org appears in list

**3. Second User Auto-Joins by Domain**
- User with matching email domain authenticates
- Auto-provisioned to matching org
- Cannot see other orgs

**4. Platform Admin Creates Configs**
- Add global config
- Add org-specific config
- Verify org config overrides global

**5. Users Work with Secrets**
- Create org-scoped secret
- Create global secret (admin only)
- Retrieve secret in workflow
- Verify secret isolation

**6. Users Create Forms**
- Create form with basic fields
- Create form with rich components (file upload, tags, etc.)
- Create form with launch workflow
- Create form with visibility expressions

**7. Users Create and Use Data Providers**
- Register data provider
- Use in form field
- Verify data loads correctly

**8. Users Execute Workflows**
- Execute simple workflow
- Execute workflow with parameters
- Execute workflow that accesses secrets
- Execute workflow that accesses configs
- Verify execution history

**9. Form Context and Visibility**
- Submit form with launch workflow
- Verify context propagates
- Test field visibility based on context
- Test field visibility based on workflow results

### 2.1 First User Journey Tests

```python
# tests/integration/test_user_provisioning_journey.py

import requests
import pytest
from tests.helpers.auth import create_test_jwt, auth_headers

class TestFirstUserJourney:
    """Test the complete first user experience"""

    def test_first_user_becomes_platform_admin(self, azure_functions_server):
        """
        SCENARIO: First user to authenticate becomes PlatformAdmin automatically

        STEPS:
        1. User authenticates (JWT with new email)
        2. System detects no users exist
        3. Auto-creates user as PlatformAdmin
        4. User can access platform resources
        """
        # First user authenticates
        token = create_test_jwt(
            user_id="admin-001",
            email="admin@platform.com",
            name="Platform Admin"
        )

        # Try to access platform resource (organizations list)
        response = requests.get(
            f"{azure_functions_server}/api/organizations",
            headers=auth_headers(token)
        )

        # Should succeed - user auto-created and promoted to admin
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_second_user_cannot_access_platform_resources(self, azure_functions_server):
        """
        SCENARIO: Second user is NOT auto-promoted to PlatformAdmin

        STEPS:
        1. Second user authenticates
        2. Has no domain match, so no org assigned
        3. Cannot access platform-wide resources
        """
        # Different user authenticates
        token = create_test_jwt(
            user_id="user-002",
            email="user@nowhere.com",
            name="Regular User"
        )

        # Try to access platform resources
        response = requests.get(
            f"{azure_functions_server}/api/organizations",
            headers=auth_headers(token)
        )

        # Should fail - not a platform admin
        assert response.status_code in [403, 404]
```

### 2.2 Organization Creation Journey

```python
# tests/integration/test_organization_journey.py

class TestOrganizationJourney:
    """Test organization creation and domain-based provisioning"""

    @pytest.fixture
    def platform_admin_token(self):
        """First user is always platform admin"""
        return create_test_jwt(
            user_id="admin-001",
            email="admin@platform.com",
            name="Platform Admin"
        )

    def test_admin_creates_organization(self, azure_functions_server, platform_admin_token):
        """
        SCENARIO: Platform admin creates organization with domain

        STEPS:
        1. Admin creates org with domain "acme.com"
        2. Org appears in org list
        3. Org has correct properties
        """
        response = requests.post(
            f"{azure_functions_server}/api/organizations",
            json={
                "name": "Acme Corp",
                "domain": "acme.com"
            },
            headers=auth_headers(platform_admin_token)
        )

        assert response.status_code == 201
        org = response.json()
        assert org["name"] == "Acme Corp"
        assert org["domain"] == "acme.com"
        assert "id" in org

        # Verify appears in list
        list_response = requests.get(
            f"{azure_functions_server}/api/organizations",
            headers=auth_headers(platform_admin_token)
        )
        assert response.status_code == 200
        org_names = [o["name"] for o in list_response.json()]
        assert "Acme Corp" in org_names

    def test_user_auto_joins_by_domain(self, azure_functions_server, platform_admin_token):
        """
        SCENARIO: User with matching email domain auto-joins org

        STEPS:
        1. Admin creates org with domain "acme.com"
        2. User with email "john@acme.com" authenticates
        3. User auto-provisioned to Acme Corp org
        4. User can see their org but not others
        """
        # Create org
        org_response = requests.post(
            f"{azure_functions_server}/api/organizations",
            json={"name": "Acme Corp", "domain": "acme.com"},
            headers=auth_headers(platform_admin_token)
        )
        org_id = org_response.json()["id"]

        # User with matching domain authenticates
        user_token = create_test_jwt(
            user_id="john-123",
            email="john@acme.com",
            name="John Doe"
        )

        # User tries to access their org's forms
        forms_response = requests.get(
            f"{azure_functions_server}/api/forms",
            headers=org_headers(org_id, user_token)
        )

        # Should succeed - user auto-joined
        assert forms_response.status_code == 200
```

### 2.3 Configuration Journey

```python
# tests/integration/test_config_journey.py

class TestConfigJourney:
    """Test configuration management across global and org scopes"""

    def test_global_config_with_org_override(self, azure_functions_server, platform_admin_token):
        """
        SCENARIO: Global config can be overridden per-org

        STEPS:
        1. Admin sets global config: default_timeout=30
        2. Admin creates org
        3. Admin sets org-specific config: default_timeout=60
        4. Org user gets timeout=60 (org override)
        5. Other org gets timeout=30 (global default)
        """
        # Set global config
        global_response = requests.post(
            f"{azure_functions_server}/api/config",
            json={
                "key": "default_timeout",
                "value": "30",
                "scope": "global"
            },
            headers=auth_headers(platform_admin_token)
        )
        assert global_response.status_code == 201

        # Create org
        org_response = requests.post(
            f"{azure_functions_server}/api/organizations",
            json={"name": "Acme Corp", "domain": "acme.com"},
            headers=auth_headers(platform_admin_token)
        )
        org_id = org_response.json()["id"]

        # Set org-specific override
        org_config_response = requests.post(
            f"{azure_functions_server}/api/config",
            json={
                "key": "default_timeout",
                "value": "60",
                "organizationId": org_id
            },
            headers=auth_headers(platform_admin_token)
        )
        assert org_config_response.status_code == 201

        # Org user gets config - should see override
        user_token = create_test_jwt(email="user@acme.com")
        get_response = requests.get(
            f"{azure_functions_server}/api/config/default_timeout",
            headers=org_headers(org_id, user_token)
        )

        assert get_response.status_code == 200
        assert get_response.json()["value"] == "60"  # Org override
```

### 2.4 Secrets Journey

```python
# tests/integration/test_secrets_journey.py

class TestSecretsJourney:
    """Test secrets management and isolation"""

    def test_org_secrets_isolated(self, azure_functions_server, platform_admin_token):
        """
        SCENARIO: Org secrets are isolated between organizations

        STEPS:
        1. Create two orgs
        2. Each org creates secret with same key name
        3. Each org can only see their own secret
        """
        # Create Org A
        org_a = requests.post(
            f"{azure_functions_server}/api/organizations",
            json={"name": "Org A", "domain": "orga.com"},
            headers=auth_headers(platform_admin_token)
        ).json()

        # Create Org B
        org_b = requests.post(
            f"{azure_functions_server}/api/organizations",
            json={"name": "Org B", "domain": "orgb.com"},
            headers=auth_headers(platform_admin_token)
        ).json()

        # Org A creates secret
        org_a_token = create_test_jwt(email="user@orga.com")
        requests.post(
            f"{azure_functions_server}/api/secrets",
            json={
                "key": "api_key",
                "value": "secret-a-value",
                "organizationId": org_a["id"]
            },
            headers=org_headers(org_a["id"], org_a_token)
        )

        # Org B creates secret with SAME key
        org_b_token = create_test_jwt(email="user@orgb.com")
        requests.post(
            f"{azure_functions_server}/api/secrets",
            json={
                "key": "api_key",
                "value": "secret-b-value",
                "organizationId": org_b["id"]
            },
            headers=org_headers(org_b["id"], org_b_token)
        )

        # Org A gets their secret
        get_a = requests.get(
            f"{azure_functions_server}/api/secrets/api_key",
            headers=org_headers(org_a["id"], org_a_token)
        )
        assert get_a.json()["value"] == "secret-a-value"

        # Org B gets their secret
        get_b = requests.get(
            f"{azure_functions_server}/api/secrets/api_key",
            headers=org_headers(org_b["id"], org_b_token)
        )
        assert get_b.json()["value"] == "secret-b-value"
```

### 2.5 Forms and Dynamic Data Journey

```python
# tests/integration/test_forms_journey.py

class TestFormsJourney:
    """Test form creation with dynamic data providers"""

    def test_form_with_data_provider(self, azure_functions_server):
        """
        SCENARIO: Create form that uses data provider for dropdown options

        STEPS:
        1. Create org and user
        2. Register data provider (exists in workspace/examples/)
        3. Create form with field using data provider
        4. Get form - verify data provider is listed
        5. Call data provider - verify returns options
        """
        # Setup
        admin_token = create_test_jwt(email="admin@platform.com")
        org = requests.post(
            f"{azure_functions_server}/api/organizations",
            json={"name": "Test Org", "domain": "test.com"},
            headers=auth_headers(admin_token)
        ).json()

        user_token = create_test_jwt(email="user@test.com")

        # List available data providers (from workspace)
        providers_response = requests.get(
            f"{azure_functions_server}/api/data-providers",
            headers=org_headers(org["id"], user_token)
        )
        assert providers_response.status_code == 200
        providers = providers_response.json()

        # Should have license providers from workspace/examples/
        provider_names = [p["name"] for p in providers]
        assert "get_available_licenses" in provider_names

        # Create form using data provider
        form_response = requests.post(
            f"{azure_functions_server}/api/forms",
            json={
                "name": "User Onboarding",
                "linkedWorkflow": "user_onboarding",
                "formSchema": {
                    "fields": [
                        {
                            "name": "license_type",
                            "type": "select",
                            "label": "License Type",
                            "dataProvider": "get_available_licenses",
                            "required": True
                        }
                    ]
                }
            },
            headers=org_headers(org["id"], user_token)
        )

        assert form_response.status_code == 201
        form = form_response.json()

        # Call data provider to get options
        data_response = requests.post(
            f"{azure_functions_server}/api/data-providers/get_available_licenses/execute",
            json={},
            headers=org_headers(org["id"], user_token)
        )

        assert data_response.status_code == 200
        licenses = data_response.json()
        assert isinstance(licenses, list)
        assert len(licenses) > 0
```

### 2.6 Workflow Execution Journey

```python
# tests/integration/test_workflow_execution_journey.py

class TestWorkflowExecutionJourney:
    """Test workflow execution with configs and secrets"""

    def test_workflow_accesses_config_and_secret(self, azure_functions_server):
        """
        SCENARIO: Workflow retrieves org config and secret during execution

        STEPS:
        1. Create org, config, and secret
        2. Create workflow that uses context.get_config() and context.get_secret()
        3. Execute workflow
        4. Verify workflow received correct values
        """
        # Setup org
        admin_token = create_test_jwt(email="admin@platform.com")
        org = requests.post(
            f"{azure_functions_server}/api/organizations",
            json={"name": "Test Org", "domain": "test.com"},
            headers=auth_headers(admin_token)
        ).json()

        user_token = create_test_jwt(email="user@test.com")

        # Create config
        requests.post(
            f"{azure_functions_server}/api/config",
            json={
                "key": "company_name",
                "value": "Test Company",
                "organizationId": org["id"]
            },
            headers=org_headers(org["id"], user_token)
        )

        # Create secret
        requests.post(
            f"{azure_functions_server}/api/secrets",
            json={
                "key": "api_token",
                "value": "super-secret-token",
                "organizationId": org["id"]
            },
            headers=org_headers(org["id"], user_token)
        )

        # Execute workflow that accesses config and secret
        # (This workflow should exist in workspace/examples/)
        exec_response = requests.post(
            f"{azure_functions_server}/api/workflows/simple_greeting/execute",
            json={
                "parameters": {"name": "John"}
            },
            headers=org_headers(org["id"], user_token)
        )

        assert exec_response.status_code == 200
        result = exec_response.json()

        # Verify workflow completed
        assert result["status"] == "completed"
```

### 2.7 Form Context and Visibility Journey

```python
# tests/integration/test_form_context_journey.py

class TestFormContextJourney:
    """Test form context propagation and field visibility"""

    def test_form_launch_workflow_and_visibility(self, azure_functions_server):
        """
        SCENARIO: Form with launch workflow provides context for field visibility

        STEPS:
        1. Create form with launch workflow
        2. Form has field visible only if workflow returns specific value
        3. Submit form with query params
        4. Launch workflow executes, returns data
        5. Field visibility determined by workflow result
        """
        # Setup
        admin_token = create_test_jwt(email="admin@platform.com")
        org = requests.post(
            f"{azure_functions_server}/api/organizations",
            json={"name": "Test Org", "domain": "test.com"},
            headers=auth_headers(admin_token)
        ).json()

        user_token = create_test_jwt(email="user@test.com")

        # Create form with launch workflow and visibility
        form_response = requests.post(
            f"{azure_functions_server}/api/forms",
            json={
                "name": "License Assignment Form",
                "linkedWorkflow": "assign_license",
                "launchWorkflow": "workflows.load_customer_licenses",
                "allowedQueryParams": ["customer_id"],
                "formSchema": {
                    "fields": [
                        {
                            "name": "license_type",
                            "type": "select",
                            "label": "License Type",
                            "dataProvider": "get_available_licenses",
                            "required": True,
                            # Only visible if customer has licenses available
                            "visibilityExpression": "context.license_count > 0"
                        },
                        {
                            "name": "no_licenses_message",
                            "type": "info",
                            "label": "No licenses available for this customer",
                            # Only visible if NO licenses
                            "visibilityExpression": "context.license_count === 0"
                        }
                    ]
                }
            },
            headers=org_headers(org["id"], user_token)
        )

        assert form_response.status_code == 201
        form = form_response.json()

        # Get form with query param (triggers launch workflow)
        get_response = requests.get(
            f"{azure_functions_server}/api/forms/{form['id']}?customer_id=cust-123",
            headers=org_headers(org["id"], user_token)
        )

        assert get_response.status_code == 200
        form_data = get_response.json()

        # Verify launch workflow configuration stored
        assert form_data["launchWorkflow"] == "workflows.load_customer_licenses"
        assert "customer_id" in form_data["allowedQueryParams"]
```

---

## Phase 3: Unit Test Fixes

### 3.1 Registry Isolation Fix

```python
# tests/fixtures/registry.py

import pytest
from shared.registry import WorkflowRegistry

@pytest.fixture
def isolated_registry(monkeypatch):
    """
    Provides completely isolated WorkflowRegistry for each test.
    No shared state between tests.
    """
    # Create new instance bypassing singleton
    reg = object.__new__(WorkflowRegistry)
    reg._workflows = {}
    reg._data_providers = {}
    reg._initialized = True

    # Patch all get_registry() calls to return our instance
    monkeypatch.setattr("shared.registry.get_registry", lambda: reg)
    monkeypatch.setattr("shared.decorators.get_registry", lambda: reg)

    yield reg

    # Cleanup automatic via monkeypatch
```

**Update these files to use `isolated_registry`:**
- `tests/unit/engine/test_registry.py`
- `tests/unit/engine/test_decorators.py`
- Any other test that calls `get_registry()`

### 3.2 Remove Mock HTTP Helpers

**Delete these (no longer needed):**
- `tests/helpers/http_helpers.py` - Mock HTTP requests
- `tests/helpers/mock_requests.py` - Mock request builder

**Keep these:**
- `tests/helpers/auth.py` - JWT token generation (still useful)

---

## Phase 4: Directory Reorganization

### New Structure

```
tests/
├── conftest.py (session fixtures: azurite, functions server, mock keyvault)
├── pytest.ini (markers, test config)
├── README.md (testing guide)
│
├── fixtures/
│   ├── __init__.py
│   ├── auth.py (create_test_jwt, auth_headers, org_headers)
│   └── registry.py (isolated_registry fixture)
│
├── unit/
│   ├── conftest.py (unit-specific fixtures if needed)
│   ├── test_authorization.py
│   ├── test_user_provisioning.py
│   ├── test_request_context.py
│   ├── test_roles_source.py
│   │
│   ├── models/
│   │   └── test_pydantic_models.py (consolidated from 9 files)
│   │
│   └── workflows/
│       ├── test_registry.py
│       ├── test_decorators.py
│       ├── test_execution.py
│       └── test_import_restrictions.py
│
├── integration/
│   ├── conftest.py (integration fixtures - API helpers)
│   │
│   ├── test_user_provisioning_journey.py
│   ├── test_organization_journey.py
│   ├── test_config_journey.py
│   ├── test_secrets_journey.py
│   ├── test_forms_journey.py
│   ├── test_workflow_execution_journey.py
│   ├── test_form_context_journey.py
│   └── test_file_uploads_journey.py
│
└── e2e/
    ├── conftest.py (e2e-specific fixtures)
    └── test_complete_user_workflow_e2e.py
```

**Deletions:**
- `tests/contract/` - Merged into integration
- `tests/integration/api/` - Reorganized to journey-based tests
- `tests/integration/engine/` - Reorganized to journey-based tests
- `tests/helpers/http_helpers.py` - No longer needed
- `tests/helpers/mock_requests.py` - No longer needed

---

## Phase 5: Test Configuration

### pytest.ini

```ini
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

markers =
    unit: Unit tests (fast, mocked dependencies)
    integration: Integration tests (real HTTP + Azurite)
    e2e: End-to-end tests (complete workflows)
    slow: Tests that take >1 second

addopts =
    -v
    --tb=short
    --strict-markers
    --disable-warnings

# Run unit tests first, then integration, then e2e
# Unit tests should be fast, integration slower, e2e slowest
```

### Coverage Configuration

```ini
[tool.coverage.run]
source = ["shared", "functions"]
omit = [
    "*/tests/*",
    "*/workspace/*",
    "*/__pycache__/*"
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "@abstractmethod"
]
```

---

## Phase 6: Documentation

### tests/README.md

```markdown
# Integration Testing Guide

## Quick Start

```bash
# Install dependencies
pip install -r requirements-dev.txt
npm install -g azurite  # For isolated test Azurite

# Run all tests
pytest

# Run only unit tests (fast)
pytest -m unit

# Run integration tests (requires Azurite + Functions startup)
pytest -m integration

# Run with coverage
pytest --cov=shared --cov=functions
```

## Architecture

Integration tests use **real HTTP requests** to a **real Azure Functions server** running on isolated infrastructure:

- **Azure Functions:** Port 8080 (dev uses 7071)
- **Azurite Blob:** Port 10100 (dev uses 10000)
- **Azurite Queue:** Port 10101 (dev uses 10001)
- **Azurite Table:** Port 10102 (dev uses 10002)

This ensures tests exercise the actual code path users will experience.

## Test Types

### Unit Tests (`tests/unit/`)
- Test business logic in isolation
- Mock all external dependencies (database, HTTP, etc.)
- Fast (<10ms per test)
- No real infrastructure needed

### Integration Tests (`tests/integration/`)
- Test complete API endpoints via real HTTP
- Use real Azure Functions + Azurite
- Create data organically through APIs
- Test actual user workflows
- Medium speed (50-200ms per test)

### E2E Tests (`tests/e2e/`)
- Test complete multi-step user journeys
- Full stack from authentication to workflow completion
- Fewer tests, high value
- Slow (200ms-1s per test)

## Writing Integration Tests

Integration tests follow **user journey patterns**:

```python
def test_user_creates_form_and_submits(azure_functions_server):
    """Real HTTP requests to real Functions server"""

    # 1. User authenticates
    token = create_test_jwt(email="user@test.com")

    # 2. Create organization via API
    org = requests.post(
        f"{azure_functions_server}/api/organizations",
        json={"name": "Test Org", "domain": "test.com"},
        headers=auth_headers(token)
    ).json()

    # 3. Create form via API
    form = requests.post(
        f"{azure_functions_server}/api/forms",
        json={"name": "Test Form", ...},
        headers=org_headers(org["id"], token)
    ).json()

    # 4. Submit form via API
    response = requests.post(
        f"{azure_functions_server}/api/forms/{form['id']}/submit",
        json={"field1": "value1"},
        headers=org_headers(org["id"], token)
    )

    assert response.status_code == 200
```

## Fixtures

**Session-scoped (start once per test run):**
- `test_azurite` - Dedicated Azurite on ports 10100-10102
- `azure_functions_server` - Functions on port 8080
- `mock_key_vault` - Mocked Key Vault (can't connect to real one)

**Function-scoped (per test):**
- `isolated_registry` - Clean WorkflowRegistry for each test
- Helper functions: `create_test_jwt()`, `auth_headers()`, `org_headers()`

## Common Patterns

**Authentication:**
```python
token = create_test_jwt(email="user@test.com", name="Test User")
headers = auth_headers(token)
```

**Org Context:**
```python
headers = org_headers(org_id="org-123", token=token)
```

**API Call:**
```python
response = requests.post(
    f"{azure_functions_server}/api/endpoint",
    json={...},
    headers=headers
)
assert response.status_code == 201
```
```

### Update CLAUDE.md

Add testing section with key principles:
- Integration tests = Real HTTP to real Functions server
- Isolated infrastructure (different ports)
- No seed data - create organically via APIs
- Test user journeys, not individual functions
- Mock only what can't run locally (Key Vault, external APIs)

---

## Execution Steps for Code Executor

### Step 1: Infrastructure Setup (30 min)
1. Create `tests/conftest.py` with session fixtures
2. Create `tests/fixtures/auth.py` with JWT helpers
3. Create `tests/fixtures/registry.py` with isolation fixture
4. Test that Azurite starts on ports 10100-10102
5. Test that Functions starts on port 8080
6. Verify mock Key Vault works

### Step 2: Convert Integration Tests (90 min)
1. Create journey-based test files
2. Implement user provisioning journey tests
3. Implement organization journey tests
4. Implement config journey tests
5. Implement secrets journey tests
6. Implement forms journey tests
7. Implement workflow execution journey tests
8. Implement form context journey tests

### Step 3: Fix Unit Tests (30 min)
1. Update `test_registry.py` to use `isolated_registry`
2. Update `test_decorators.py` to use `isolated_registry`
3. Remove mock HTTP dependencies
4. Verify all unit tests pass with isolation

### Step 4: Cleanup (20 min)
1. Delete old mock helpers
2. Delete contract/ directory
3. Reorganize directory structure
4. Remove redundant fixtures from old conftest.py

### Step 5: Documentation (20 min)
1. Create `tests/README.md`
2. Update `CLAUDE.md` testing section
3. Add pytest.ini configuration
4. Add inline comments to complex fixtures

### Step 6: Validation (10 min)
1. Run all tests: `pytest`
2. Verify unit tests fast (<5s total)
3. Verify integration tests work (may be slower on first run)
4. Check that dev infrastructure not affected (ports different)

---

## Success Criteria

- [ ] All tests pass
- [ ] Integration tests use real HTTP (no mock requests)
- [ ] Test Azurite runs on ports 10100-10102 (isolated from dev)
- [ ] Test Functions runs on port 8080 (isolated from dev)
- [ ] No seed data - all entities created organically
- [ ] Unit tests use `isolated_registry` fixture
- [ ] Journey tests cover all major user workflows
- [ ] Documentation complete (README.md + CLAUDE.md)
- [ ] Dev infrastructure unaffected (can run docker-compose and func start simultaneously)

---

## Timeline Estimate

- Infrastructure: 30 minutes
- Convert integration tests: 90 minutes
- Fix unit tests: 30 minutes
- Cleanup: 20 minutes
- Documentation: 20 minutes
- Validation: 10 minutes

**Total: ~3 hours**
