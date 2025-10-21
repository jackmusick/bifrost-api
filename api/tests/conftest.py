"""
Pytest fixtures for Bifrost Integrations testing infrastructure.

This module provides:
1. ISOLATED infrastructure (Azurite on ports 10100-10102, Functions on port 8080)
2. Real HTTP integration tests (no mock requests)
3. Session-scoped fixtures for efficiency
4. Function-scoped fixtures for isolation
"""

import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests
from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import TableServiceClient

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.init_tables import REQUIRED_TABLES, init_tables
from shared.storage import TableStorageService

# Import fixture modules
pytest_plugins = ["tests.fixtures.registry", "tests.fixtures.auth"]

# ==================== CONFIGURATION ====================

# Test infrastructure ports (ISOLATED from dev)
TEST_AZURITE_BLOB_PORT = 10100
TEST_AZURITE_QUEUE_PORT = 10101
TEST_AZURITE_TABLE_PORT = 10102
TEST_FUNCTIONS_PORT = 8080
TEST_FUNCTIONS_URL = f"http://localhost:{TEST_FUNCTIONS_PORT}"

# Azurite connection string for tests
TEST_AZURITE_CONNECTION = (
    "DefaultEndpointsProtocol=http;"
    "AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    f"BlobEndpoint=http://127.0.0.1:{TEST_AZURITE_BLOB_PORT}/devstoreaccount1;"
    f"QueueEndpoint=http://127.0.0.1:{TEST_AZURITE_QUEUE_PORT}/devstoreaccount1;"
    f"TableEndpoint=http://127.0.0.1:{TEST_AZURITE_TABLE_PORT}/devstoreaccount1;"
)


# ==================== SESSION FIXTURES (Start Once Per Test Run) ====================


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables once per session"""
    os.environ["AzureWebJobsStorage"] = TEST_AZURITE_CONNECTION
    os.environ["FUNCTIONS_WORKER_RUNTIME"] = "python"
    # NOTE: KeyVault env vars intentionally NOT set for integration tests
    # Unit tests mock KeyVault, E2E tests should configure KeyVault separately
    yield


@pytest.fixture(scope="session", autouse=True)
def mock_key_vault():
    """
    Mock Azure Key Vault globally for all tests (session-scoped).
    We can't connect to real Key Vault in tests.
    """
    mock_client = MagicMock()

    # In-memory secret storage
    secrets_store = {}

    def mock_set_secret(name, value):
        secrets_store[name] = value
        return MagicMock(name=name, value=value)

    def mock_get_secret(name):
        if name not in secrets_store:
            raise ResourceNotFoundError(f"Secret '{name}' not found")
        return MagicMock(name=name, value=secrets_store[name])

    def mock_delete_secret(name):
        if name in secrets_store:
            del secrets_store[name]
        return MagicMock()

    mock_client.set_secret = mock_set_secret
    mock_client.get_secret = mock_get_secret
    mock_client.begin_delete_secret = lambda name: MagicMock(
        wait=lambda: mock_delete_secret(name)
    )

    # Patch SecretClient globally
    with patch("shared.keyvault.SecretClient", return_value=mock_client):
        yield mock_client


@pytest.fixture(scope="session")
def docker_compose_services():
    """
    Start Docker Compose services (Azurite + Azure Functions) for integration tests.
    Uses docker-compose.testing.yml to start both services.

    Yields:
        tuple: (connection_string, functions_url)
    """
    # Get project root (two levels up from tests/)
    project_root = os.path.join(os.path.dirname(__file__), "../..")

    # Start Docker Compose services
    print("\n🐳 Starting Docker Compose services...")
    subprocess.run(
        ["docker", "compose", "-f", "docker-compose.testing.yml", "up", "-d", "--build"],
        cwd=project_root,
        check=True,
    )

    # Wait for Functions to be ready (up to 120 seconds for Docker startup + func init)
    print("⏳ Waiting for Azure Functions to be ready...")
    for i in range(120):
        try:
            response = requests.get(f"{TEST_FUNCTIONS_URL}/api/data-providers", timeout=2)
            if response.status_code in [200, 401]:  # 401 is fine - server is up
                print(f"✓ Azure Functions ready on {TEST_FUNCTIONS_URL}")
                break
        except Exception:
            if i == 119:
                # Print logs before failing
                print("\n❌ Failed to start. Docker logs:")
                subprocess.run(
                    ["docker", "compose", "-f", "docker-compose.testing.yml", "logs"],
                    cwd=project_root,
                )
                subprocess.run(
                    ["docker", "compose", "-f", "docker-compose.testing.yml", "down"],
                    cwd=project_root,
                )
                raise RuntimeError(
                    f"Azure Functions failed to start on port {TEST_FUNCTIONS_PORT}"
                )
            time.sleep(1)

    yield (TEST_AZURITE_CONNECTION, TEST_FUNCTIONS_URL)

    # Cleanup: Stop Docker Compose services
    print("\n🧹 Stopping Docker Compose services...")
    subprocess.run(
        ["docker", "compose", "-f", "docker-compose.testing.yml", "down"],
        cwd=project_root,
        check=False,  # Don't fail if already stopped
    )


@pytest.fixture(scope="session")
def test_azurite(docker_compose_services):
    """
    Provides Azurite connection string for tests.
    Azurite runs in Docker via docker_compose_services fixture.

    Returns:
        dict: Configuration with connection_string and port information
    """
    connection_string, _ = docker_compose_services
    yield {
        "connection_string": connection_string,
        "blob_port": TEST_AZURITE_BLOB_PORT,
        "queue_port": TEST_AZURITE_QUEUE_PORT,
        "table_port": TEST_AZURITE_TABLE_PORT,
    }


@pytest.fixture(scope="session")
def azure_functions_server(docker_compose_services):
    """
    Provides Azure Functions server URL for tests.
    Functions run in Docker via docker_compose_services fixture.

    Yields:
        str: Base URL for Functions server (http://localhost:8080)
    """
    _, functions_url = docker_compose_services
    yield functions_url


# ==================== FUNCTION-SCOPED FIXTURES (Per Test) ====================


@pytest.fixture(scope="function")
def azurite_tables(test_azurite):
    """
    Initialize all required tables in test Azurite for each test.
    Scope: function - ensures test isolation

    Yields:
        str: Full Azurite connection string
    """
    # Initialize tables
    init_tables(TEST_AZURITE_CONNECTION)

    yield TEST_AZURITE_CONNECTION

    # Cleanup - delete all entities from all tables
    service_client = TableServiceClient.from_connection_string(TEST_AZURITE_CONNECTION)
    for table_name in REQUIRED_TABLES:
        table_client = service_client.get_table_client(table_name)
        try:
            # Query all entities and delete them
            entities = list(table_client.query_entities(query_filter=""))
            for entity in entities:
                table_client.delete_entity(
                    partition_key=entity["PartitionKey"], row_key=entity["RowKey"]
                )
        except Exception:
            # Table might not exist or be empty - that's OK
            pass


# ==================== TABLE SERVICE FIXTURES ====================


@pytest.fixture
def entities_service(azurite_tables):
    """Returns TableStorageService instance for Entities table"""
    return TableStorageService("Entities")


@pytest.fixture
def config_service(azurite_tables):
    """Returns TableStorageService instance for Config table"""
    return TableStorageService("Config")


@pytest.fixture
def users_service(azurite_tables):
    """Returns TableStorageService instance for Entities table (users)"""
    return TableStorageService("Entities")


@pytest.fixture
def relationships_service(azurite_tables):
    """Returns TableStorageService instance for Relationships table"""
    return TableStorageService("Relationships")


# ==================== ENTITY FIXTURES ====================


@pytest.fixture
def test_org(entities_service) -> dict[str, Any]:
    """
    Creates a test organization in Azurite.
    Table: Entities
    PartitionKey: GLOBAL
    RowKey: org:{uuid}
    """
    import uuid

    org_id = str(uuid.uuid4())

    entity = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"org:{org_id}",
        "Name": "Test Organization",
        "Domain": "example.com",
        "IsActive": True,
        "CreatedAt": datetime.utcnow().isoformat(),
        "CreatedBy": "test-system",
        "UpdatedAt": datetime.utcnow().isoformat(),
    }

    entities_service.insert_entity(entity)

    return {"org_id": org_id, "name": "Test Organization", "domain": "example.com"}


@pytest.fixture
def test_org_2(entities_service) -> dict[str, Any]:
    """Creates a second test organization for multi-org tests"""
    import uuid

    org_id = str(uuid.uuid4())

    entity = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"org:{org_id}",
        "Name": "Test Organization 2",
        "Domain": "company.com",
        "IsActive": True,
        "CreatedAt": datetime.utcnow().isoformat(),
        "CreatedBy": "test-system",
        "UpdatedAt": datetime.utcnow().isoformat(),
    }

    entities_service.insert_entity(entity)

    return {"org_id": org_id, "name": "Test Organization 2", "domain": "company.com"}


@pytest.fixture
def test_user(users_service) -> dict[str, Any]:
    """Creates a test user"""
    email = "test@example.com"

    entity = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"user:{email}",
        "Email": email,
        "DisplayName": "Test User",
        "UserType": "ORG",
        "IsPlatformAdmin": False,
        "IsActive": True,
        "CreatedAt": datetime.utcnow().isoformat(),
        "LastLogin": datetime.utcnow().isoformat(),
    }

    users_service.insert_entity(entity)

    return {"user_id": email, "email": email, "display_name": "Test User"}


@pytest.fixture
def test_user_2(users_service) -> dict[str, Any]:
    """Creates a second test user for permission tests"""
    email = "test2@company.com"

    entity = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"user:{email}",
        "Email": email,
        "DisplayName": "Test User 2",
        "UserType": "ORG",
        "IsPlatformAdmin": False,
        "IsActive": True,
        "CreatedAt": datetime.utcnow().isoformat(),
        "LastLogin": datetime.utcnow().isoformat(),
    }

    users_service.insert_entity(entity)

    return {"user_id": email, "email": email, "display_name": "Test User 2"}


@pytest.fixture
def test_platform_admin_user(users_service) -> dict[str, Any]:
    """
    Creates a platform admin user for testing.

    This fixture is used by tests that require platform-level administrative access.
    """
    email = "admin@platform.test"

    entity = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"user:{email}",
        "Email": email,
        "DisplayName": "Platform Admin",
        "UserType": "PLATFORM",
        "IsPlatformAdmin": True,
        "IsActive": True,
        "CreatedAt": datetime.utcnow().isoformat(),
        "LastLogin": datetime.utcnow().isoformat(),
    }

    users_service.insert_entity(entity)

    return {
        "user_id": email,
        "email": email,
        "display_name": "Platform Admin",
        "user_type": "PLATFORM",
        "is_platform_admin": True,
    }


@pytest.fixture
def test_form(test_org, entities_service) -> dict[str, Any]:
    """Creates a sample form linked to user_onboarding workflow"""
    import json
    import uuid

    form_id = str(uuid.uuid4())

    form_schema = {
        "fields": [
            {"name": "first_name", "label": "First Name", "type": "text", "required": True},
            {"name": "last_name", "label": "Last Name", "type": "text", "required": True},
            {"name": "email", "label": "Email", "type": "email", "required": True},
        ]
    }

    entity = {
        "PartitionKey": test_org["org_id"],
        "RowKey": f"form:{form_id}",
        "Name": "Test User Onboarding Form",
        "Description": "Test form for user onboarding workflow",
        "LinkedWorkflow": "user_onboarding",
        "FormSchema": json.dumps(form_schema),
        "IsActive": True,
        "IsPublic": False,
        "CreatedBy": "test-system",
        "CreatedAt": datetime.utcnow().isoformat(),
        "UpdatedAt": datetime.utcnow().isoformat(),
    }

    entities_service.insert_entity(entity)

    return {
        "form_id": form_id,
        "org_id": test_org["org_id"],
        "name": "Test User Onboarding Form",
        "linked_workflow": "user_onboarding",
        "form_schema": form_schema,
    }


@pytest.fixture
def test_global_form(entities_service) -> dict[str, Any]:
    """Creates a sample global form"""
    import json
    import uuid

    form_id = str(uuid.uuid4())

    form_schema = {
        "fields": [
            {"name": "company_name", "label": "Company Name", "type": "text", "required": True},
            {"name": "industry", "label": "Industry", "type": "text", "required": False},
        ]
    }

    entity = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"form:{form_id}",
        "Name": "Test Global Form",
        "Description": "Test global form visible to all users",
        "LinkedWorkflow": "global_workflow",
        "FormSchema": json.dumps(form_schema),
        "IsActive": True,
        "IsPublic": True,
        "IsGlobal": True,
        "CreatedBy": "test-system",
        "CreatedAt": datetime.utcnow().isoformat(),
        "UpdatedAt": datetime.utcnow().isoformat(),
    }

    entities_service.insert_entity(entity)

    return {
        "form_id": form_id,
        "org_id": "GLOBAL",
        "name": "Test Global Form",
        "linked_workflow": "global_workflow",
        "form_schema": form_schema,
        "is_global": True,
        "is_public": True,
    }


# ==================== PERMISSION FIXTURES ====================


@pytest.fixture
def test_org_with_user(test_org, test_user, relationships_service):
    """Creates a test organization with an assigned user"""
    permission_entity = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"userperm:{test_user['email']}:{test_org['org_id']}",
        "UserId": test_user["email"],
        "OrganizationId": test_org["org_id"],
        "GrantedBy": "test-system",
        "GrantedAt": datetime.utcnow().isoformat(),
    }

    relationships_service.insert_entity(permission_entity)

    return {
        **test_org,
        **test_user,
        "user_type": "ORG",
        "is_platform_admin": False,
    }


# ==================== CONFIG FIXTURES ====================


@pytest.fixture
def test_org_with_config(test_org, config_service) -> dict[str, Any]:
    """Creates org with sample configs"""
    configs = [
        {
            "PartitionKey": test_org["org_id"],
            "RowKey": "config:default_location",
            "Value": "NYC",
            "Type": "string",
            "Description": "Default office location",
            "UpdatedAt": datetime.utcnow().isoformat(),
            "UpdatedBy": "test-system",
        },
        {
            "PartitionKey": test_org["org_id"],
            "RowKey": "config:timeout",
            "Value": "30",
            "Type": "int",
            "Description": "Request timeout in seconds",
            "UpdatedAt": datetime.utcnow().isoformat(),
            "UpdatedBy": "test-system",
        },
    ]

    for config in configs:
        config_service.insert_entity(config)

    return {
        **test_org,
        "configs": {"default_location": "NYC", "timeout": "30"},
    }


@pytest.fixture
def load_seed_data(azurite_tables):
    """
    Loads seed data into Azurite for integration tests.

    This fixture initializes realistic sample data including:
    - Organizations
    - Users
    - Forms
    - Workflows
    - Configuration

    Scope: function - ensures each test has fresh seed data
    """
    from seed_data import seed_all_data

    # Seed all data using the test Azurite connection
    seed_all_data(TEST_AZURITE_CONNECTION)

    yield TEST_AZURITE_CONNECTION

    # Cleanup happens automatically via azurite_tables fixture


# ==================== CONTEXT FIXTURES ====================


@pytest.fixture
def platform_admin_context():
    """Returns a RequestContext for a platform admin user"""
    from shared.request_context import RequestContext

    return RequestContext(
        user_id="admin-user-12345",
        email="admin@test.com",
        name="Test Platform Admin",
        org_id=None,  # GLOBAL scope
        is_platform_admin=True,
        is_function_key=False,
    )


@pytest.fixture
def org_user_context(test_org):
    """Returns a RequestContext for an organization user"""
    from shared.request_context import RequestContext

    return RequestContext(
        user_id="org-user-67890",
        email="user@test.com",
        name="Test Org User",
        org_id=test_org["org_id"],
        is_platform_admin=False,
        is_function_key=False,
    )


@pytest.fixture
def function_key_context():
    """Returns a RequestContext for function key authentication"""
    from shared.request_context import RequestContext

    return RequestContext(
        user_id="system",
        email="system@local",
        name="System (Function Key)",
        org_id=None,
        is_platform_admin=True,
        is_function_key=True,
    )


# ==================== MARKERS ====================


def pytest_configure(config):
    """Register custom pytest markers"""
    config.addinivalue_line("markers", "unit: Unit tests (fast, mocked dependencies)")
    config.addinivalue_line(
        "markers", "integration: Integration tests (real HTTP + Azurite)"
    )
    config.addinivalue_line("markers", "e2e: End-to-end tests (complete workflows)")
    config.addinivalue_line("markers", "slow: Tests that take >1 second")
