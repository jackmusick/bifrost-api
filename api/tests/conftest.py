"""
Pytest fixtures for Bifrost Integrations tests
Provides reusable test infrastructure for all test files
"""

import os

# Add parent directory to path for imports
import sys
import uuid
from datetime import datetime
from typing import Any

import pytest
from azure.data.tables import TableServiceClient

from shared.init_tables import REQUIRED_TABLES, init_tables
from shared.storage import TableStorageService

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ==================== CONFIGURATION ====================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables"""
    # Full Azurite connection string (required for blob storage SDK)
    os.environ["AzureWebJobsStorage"] = (
        "DefaultEndpointsProtocol=http;"
        "AccountName=devstoreaccount1;"
        "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
        "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
        "QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;"
        "TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
    )
    os.environ["KEY_VAULT_URL"] = "https://test-keyvault.vault.azure.net/"
    os.environ["AZURE_KEY_VAULT_URL"] = "https://test-keyvault.vault.azure.net/"
    os.environ["AZURE_TENANT_ID"] = "test-tenant-id"
    os.environ["AZURE_CLIENT_ID"] = "test-client-id"
    yield


@pytest.fixture(scope="function", autouse=True)
def mock_keyvault(monkeypatch):
    """
    Mock KeyVault client for tests to avoid requiring real Azure credentials.
    Only active in test environment (AZURE_FUNCTIONS_ENVIRONMENT != Testing with real vault).
    """
    from unittest.mock import MagicMock

    from azure.core.exceptions import ResourceNotFoundError

    # Only mock if we're not using a real vault (check if running in CI or without Azure auth)
    if os.environ.get("AZURE_FUNCTIONS_ENVIRONMENT") == "Testing":
        return  # Skip mocking in integration tests that use real KeyVault

    # Create a mock KeyVault client
    mock_client = MagicMock()

    # Mock delete_secret to return success
    mock_poller = MagicMock()
    mock_poller.wait = MagicMock()
    mock_client.begin_delete_secret = MagicMock(return_value=mock_poller)

    # Mock get_secret to raise not found (simulating no secrets in test vault)
    def mock_get_secret(name):
        raise ResourceNotFoundError(f"Secret not found: {name}")
    mock_client.get_secret = MagicMock(side_effect=mock_get_secret)

    # Mock set_secret to return success
    mock_client.set_secret = MagicMock()

    # Patch the SecretClient constructor to return our mock
    def mock_secret_client_init(vault_url, credential):
        return mock_client

    monkeypatch.setattr("shared.keyvault.SecretClient", lambda **kwargs: mock_client)


# ==================== INFRASTRUCTURE FIXTURES ====================

@pytest.fixture(scope="function")
def azurite_tables():
    """
    Initialize all 9 tables in Azurite and clean up after test
    Scope: function - ensures test isolation
    """
    # Use full Azurite connection string
    connection_string = (
        "DefaultEndpointsProtocol=http;"
        "AccountName=devstoreaccount1;"
        "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
        "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
        "QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;"
        "TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
    )

    # Initialize tables
    init_tables(connection_string)

    yield connection_string

    # Cleanup - delete all entities from all tables
    service_client = TableServiceClient.from_connection_string(
        connection_string)
    for table_name in REQUIRED_TABLES:
        table_client = service_client.get_table_client(table_name)
        try:
            # Query all entities and delete them
            entities = list(table_client.query_entities(query_filter=""))
            for entity in entities:
                table_client.delete_entity(
                    partition_key=entity['PartitionKey'],
                    row_key=entity['RowKey']
                )
        except Exception:
            # Table might not exist or be empty - that's OK
            pass


@pytest.fixture
def entities_service(azurite_tables):
    """Returns TableStorageService instance for Entities table (orgs, forms, executions, audit)"""
    return TableStorageService("Entities")


@pytest.fixture
def config_service(azurite_tables):
    """Returns TableStorageService instance for Config table (config, integrations, oauth, system)"""
    return TableStorageService("Config")


@pytest.fixture
def users_service(azurite_tables):
    """Returns TableStorageService instance for Entities table (users now stored here)"""
    return TableStorageService("Entities")


@pytest.fixture
def relationships_service(azurite_tables):
    """Returns TableStorageService instance for Relationships table (roles, permissions, etc.)"""
    return TableStorageService("Relationships")


# ==================== ENTITY FIXTURES ====================

@pytest.fixture
def test_org(entities_service) -> dict[str, Any]:
    """
    Creates a test organization in the new 4-table structure
    Table: Entities
    PartitionKey: GLOBAL
    RowKey: org:{uuid}
    Returns dict with org_id, name
    """
    org_id = str(uuid.uuid4())

    entity = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"org:{org_id}",
        "Name": "Test Organization",
        "Domain": "example.com",  # Added domain for user provisioning
        "IsActive": True,
        "CreatedAt": datetime.utcnow().isoformat(),
        "CreatedBy": "test-system",
        "UpdatedAt": datetime.utcnow().isoformat(),
    }

    entities_service.insert_entity(entity)

    return {
        "org_id": org_id,
        "name": "Test Organization",
        "domain": "example.com"
    }


@pytest.fixture
def test_org_2(entities_service) -> dict[str, Any]:
    """
    Creates a second test organization for multi-org tests
    Table: Entities
    PartitionKey: GLOBAL
    RowKey: org:{uuid}
    """
    org_id = str(uuid.uuid4())

    entity = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"org:{org_id}",
        "Name": "Test Organization 2",
        "Domain": "company.com",  # Added different domain for provisioning
        "IsActive": True,
        "CreatedAt": datetime.utcnow().isoformat(),
        "CreatedBy": "test-system",
        "UpdatedAt": datetime.utcnow().isoformat(),
    }

    entities_service.insert_entity(entity)

    return {
        "org_id": org_id,
        "name": "Test Organization 2",
        "domain": "company.com"
    }


@pytest.fixture
def test_user(users_service) -> dict[str, Any]:
    """
    Creates a test user
    Table: Entities
    PartitionKey: GLOBAL
    RowKey: user:{email}
    Returns dict with user_id, email
    """
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

    return {
        "user_id": email,  # user_id is now the email
        "email": email,
        "display_name": "Test User"
    }


@pytest.fixture
def test_user_2(users_service) -> dict[str, Any]:
    """
    Creates a second test user for permission tests
    Table: Entities
    PartitionKey: GLOBAL
    RowKey: user:{email}
    """
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

    return {
        "user_id": email,  # user_id is now the email
        "email": email,
        "display_name": "Test User 2"
    }


# ==================== PERMISSION FIXTURES ====================

@pytest.fixture
def test_user_with_full_permissions(test_org, test_user, relationships_service) -> dict[str, Any]:
    """
    Creates a user with full permissions via role assignment in new 4-table structure
    Table: Relationships
    PartitionKey: GLOBAL
    RowKey patterns: userrole:{user_id}:{role_id} and assignedrole:{role_id}:{user_id}
    Returns combined dict with user and org info
    """
    # Create an "admin" role for testing
    admin_role_id = str(uuid.uuid4())
    role_entity = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"role:{admin_role_id}",
        "Name": "Admin",
        "Description": "Admin role for testing",
        "IsActive": True,
        "CreatedBy": "test-system",
        "CreatedAt": datetime.utcnow().isoformat(),
        "UpdatedAt": datetime.utcnow().isoformat()
    }
    relationships_service.insert_entity(role_entity)

    # Assign user to admin role (dual-indexed)
    now = datetime.utcnow()

    # Primary index: assignedrole:role_uuid:user_id (for querying users by role)
    entity1 = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"assignedrole:{admin_role_id}:{test_user['user_id']}",
        "UserId": test_user["user_id"],
        "RoleId": admin_role_id,
        "AssignedBy": "test-system",
        "AssignedAt": now.isoformat()
    }
    relationships_service.insert_entity(entity1)

    # Dual index: userrole:user_id:role_uuid (for querying roles by user)
    entity2 = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"userrole:{test_user['user_id']}:{admin_role_id}",
        "UserId": test_user["user_id"],
        "RoleId": admin_role_id,
        "AssignedBy": "test-system",
        "AssignedAt": now.isoformat()
    }
    relationships_service.insert_entity(entity2)

    return {
        **test_user,
        **test_org,
        "role_id": admin_role_id,
        "permissions": {
            "canExecuteWorkflows": True,
            "canManageConfig": True,
            "canManageForms": True,
            "canViewHistory": True,
        }
    }


@pytest.fixture
def test_user_with_no_permissions(test_org, test_user) -> dict[str, Any]:
    """
    Creates user with no role assignments (no permissions)
    No entities created in Relationships table - user has no roles
    """
    return {
        **test_user,
        **test_org,
        "permissions": {
            "canExecuteWorkflows": False,
            "canManageConfig": False,
            "canManageForms": False,
            "canViewHistory": False,
        }
    }


@pytest.fixture
def test_user_with_limited_permissions(test_org, test_user, relationships_service) -> dict[str, Any]:
    """
    Creates user with limited permissions via "viewer" role assignment
    Table: Relationships
    """
    # Create a "viewer" role for testing (limited permissions)
    viewer_role_id = str(uuid.uuid4())
    role_entity = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"role:{viewer_role_id}",
        "Name": "Viewer",
        "Description": "Viewer role for testing (limited permissions)",
        "IsActive": True,
        "CreatedBy": "test-system",
        "CreatedAt": datetime.utcnow().isoformat(),
        "UpdatedAt": datetime.utcnow().isoformat()
    }
    relationships_service.insert_entity(role_entity)

    # Assign user to viewer role (dual-indexed)
    now = datetime.utcnow()

    entity1 = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"assignedrole:{viewer_role_id}:{test_user['user_id']}",
        "UserId": test_user["user_id"],
        "RoleId": viewer_role_id,
        "AssignedBy": "test-system",
        "AssignedAt": now.isoformat()
    }
    relationships_service.insert_entity(entity1)

    entity2 = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"userrole:{test_user['user_id']}:{viewer_role_id}",
        "UserId": test_user["user_id"],
        "RoleId": viewer_role_id,
        "AssignedBy": "test-system",
        "AssignedAt": now.isoformat()
    }
    relationships_service.insert_entity(entity2)

    return {
        **test_user,
        **test_org,
        "role_id": viewer_role_id,
        "permissions": {
            "canExecuteWorkflows": True,
            "canManageConfig": False,
            "canManageForms": False,
            "canViewHistory": True,
        }
    }


# ==================== CONFIG FIXTURES ====================

@pytest.fixture
def test_org_with_config(test_org, config_service) -> dict[str, Any]:
    """
    Creates org with sample configs in new 4-table structure
    Table: Config
    PartitionKey: {org_id}
    RowKey: config:{key}
    """
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
        "configs": {
            "default_location": "NYC",
            "timeout": "30"
        }
    }


# ==================== FORM FIXTURES ====================

@pytest.fixture
def test_form(test_org, entities_service) -> dict[str, Any]:
    """
    Creates a sample form linked to user_onboarding workflow in new 4-table structure
    Table: Entities
    PartitionKey: {org_id}
    RowKey: form:{uuid}
    """
    import json

    form_id = str(uuid.uuid4())

    form_schema = {
        "fields": [
            {
                "name": "first_name",
                "label": "First Name",
                "type": "text",
                "required": True
            },
            {
                "name": "last_name",
                "label": "Last Name",
                "type": "text",
                "required": True
            },
            {
                "name": "email",
                "label": "Email",
                "type": "email",
                "required": True
            }
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
        "form_schema": form_schema
    }


@pytest.fixture
def test_global_form(entities_service) -> dict[str, Any]:
    """
    Creates a global form (available to all organizations) in new 4-table structure
    Table: Entities
    PartitionKey: GLOBAL
    RowKey: form:{uuid}
    """
    import json

    form_id = str(uuid.uuid4())

    form_schema = {
        "fields": [
            {
                "name": "company_name",
                "label": "Company Name",
                "type": "text",
                "required": True
            }
        ]
    }

    entity = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"form:{form_id}",
        "Name": "Global Customer Onboarding Form",
        "Description": "Global template for customer onboarding",
        "LinkedWorkflow": "global_customer_onboarding",
        "FormSchema": json.dumps(form_schema),
        "IsActive": True,
        "IsPublic": True,
        "CreatedBy": "test-system",
        "CreatedAt": datetime.utcnow().isoformat(),
        "UpdatedAt": datetime.utcnow().isoformat(),
    }

    entities_service.insert_entity(entity)

    return {
        "form_id": form_id,
        "org_id": "GLOBAL",
        "name": "Global Customer Onboarding Form",
        "linked_workflow": "global_customer_onboarding",
        "form_schema": form_schema
    }


# ==================== WORKFLOW FIXTURES ====================

@pytest.fixture
def mock_context(test_org):
    """
    Returns mock OrganizationContext for workflow testing
    """
    from unittest.mock import MagicMock

    context = MagicMock()
    context.org_id = test_org["org_id"]
    context.org_name = test_org["name"]

    # Mock methods
    context.get_config = MagicMock(return_value="mock-value")
    context.get_secret = MagicMock(return_value="mock-secret")
    context.get_integration = MagicMock(return_value=MagicMock())

    return context


@pytest.fixture
def mock_jwt_token(test_user):
    """
    Returns a mock JWT token string for testing auth middleware
    """
    from datetime import timedelta

    import jwt

    payload = {
        "oid": test_user["user_id"],
        "preferred_username": test_user["email"],
        "name": test_user["display_name"],
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
        "iss": "https://login.microsoftonline.com/test-tenant/v2.0",
        "aud": "test-client-id"
    }

    # Sign with a test secret (in real tests, this would be validated)
    token = jwt.encode(payload, "test-secret", algorithm="HS256")

    return token


# ==================== HELPER FUNCTIONS ====================

def generate_test_uuid() -> str:
    """Generate a test UUID"""
    return str(uuid.uuid4())


def clear_table(table_name: str):
    """Clear all entities from a table"""
    service = TableStorageService(table_name)

    entities = list(service.query_entities())
    for entity in entities:
        service.delete_entity(
            partition_key=entity["PartitionKey"],
            row_key=entity["RowKey"]
        )


# ==================== AUTHENTICATION FIXTURES ====================

@pytest.fixture
def platform_admin_context():
    """
    Returns a RequestContext for a platform admin user
    Used for testing admin-only endpoints and GLOBAL scope operations
    """
    from shared.request_context import RequestContext

    return RequestContext(
        user_id="admin-user-12345",
        email="admin@test.com",
        name="Test Platform Admin",
        org_id=None,  # GLOBAL scope
        is_platform_admin=True,
        is_function_key=False
    )


@pytest.fixture
def org_user_context(test_org):
    """
    Returns a RequestContext for an organization user
    Used for testing org-scoped operations
    """
    from shared.request_context import RequestContext

    return RequestContext(
        user_id="org-user-67890",
        email="user@test.com",
        name="Test Org User",
        org_id=test_org["org_id"],
        is_platform_admin=False,
        is_function_key=False
    )


@pytest.fixture
def function_key_context():
    """
    Returns a RequestContext for function key authentication
    Used for testing system-to-system operations
    """
    from shared.request_context import RequestContext

    return RequestContext(
        user_id="system",
        email="system@local",
        name="System (Function Key)",
        org_id=None,  # Can be set via headers
        is_platform_admin=True,
        is_function_key=True
    )


@pytest.fixture
def mock_admin_request():
    """
    Returns a mock HTTP request with platform admin authentication
    Used for testing admin endpoints
    """
    from tests.helpers.mock_requests import MockRequestHelper

    return MockRequestHelper.create_platform_admin_request(
        method="GET",
        url="/api/test"
    )


@pytest.fixture
def mock_org_user_request(test_org):
    """
    Returns a mock HTTP request with org user authentication
    Used for testing org user endpoints
    """
    from tests.helpers.mock_requests import MockRequestHelper

    return MockRequestHelper.create_org_user_request(
        method="GET",
        url="/api/test",
        org_id=test_org["org_id"]
    )


@pytest.fixture
def mock_function_key_request():
    """
    Returns a mock HTTP request with function key authentication
    Used for testing system endpoints
    """
    from tests.helpers.mock_requests import MockRequestHelper

    return MockRequestHelper.create_function_key_request(
        method="GET",
        url="/api/test"
    )


@pytest.fixture
def mock_anonymous_request():
    """
    Returns a mock HTTP request without authentication
    Used for testing anonymous endpoints
    """
    from tests.helpers.mock_requests import MockRequestHelper

    return MockRequestHelper.create_anonymous_request(
        method="GET",
        url="/api/test"
    )


@pytest.fixture
def test_org_with_user(test_org, test_user, relationships_service):
    """
    Creates a test organization with an assigned user via user permission relationship
    Returns combined dict with org and user info
    """
    # Create user-org permission relationship in Relationships table
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
        "is_platform_admin": False
    }


@pytest.fixture
def test_platform_admin_user(users_service, relationships_service, test_org=None):
    """
    Creates a platform admin user for testing
    Table: Entities
    PartitionKey: GLOBAL
    RowKey: user:{email}
    Returns dict with user info

    Optional test_org allows assigning the admin to an organization
    """
    email = "admin@test.com"

    user_entity = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"user:{email}",
        "Email": email,
        "DisplayName": "Test Platform Admin",
        "IsActive": True,
        "UserType": "PLATFORM",
        "IsPlatformAdmin": True,
        "CreatedAt": datetime.utcnow().isoformat(),
        "LastLogin": datetime.utcnow().isoformat(),
    }

    users_service.upsert_entity(user_entity)

    # Optional org relationship for the platform admin
    if test_org:
        permission_entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"userperm:{email}:{test_org['org_id']}",
            "UserId": email,
            "OrganizationId": test_org['org_id'],
            "GrantedBy": "test-system",
            "GrantedAt": datetime.utcnow().isoformat(),
        }
        relationships_service.insert_entity(permission_entity)

    return {
        "user_id": email,  # user_id is now the email
        "email": email,
        "display_name": "Test Platform Admin",
        "user_type": "PLATFORM",
        "is_platform_admin": True,
        "org_id": test_org["org_id"] if test_org else None
    }


@pytest.fixture(scope="function")
def load_seed_data(azurite_tables):
    """
    Load seed data for E2E tests that explicitly need it
    This creates the test users (jack@gocovi.com, jack@gocovi.dev) and sample data

    NOTE: Not autouse - tests must explicitly request this fixture if they need seed data
    """
    # Import seed data function
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

    try:
        from seed_data import seed_all_data
        # Use full Azurite connection string
        connection_string = (
            "DefaultEndpointsProtocol=http;"
            "AccountName=devstoreaccount1;"
            "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
            "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
            "QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;"
            "TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
        )
        seed_all_data(connection_string)
    except Exception as e:
        # If seed data fails, tests will fail with clearer errors
        print(f"Warning: Failed to load seed data: {e}")
        pass


@pytest.fixture
def mock_auth_users(users_service, relationships_service, test_org):
    """
    Ensures that mock authentication users actually exist in the database with proper org relationships.
    This fixture creates the test users referenced in mock_auth.py (TestUsers)
    and establishes their org relationships so integration tests don't get 401 errors.

    Creates:
    - Platform admin user (admin@test.com)
    - Org user (user@test.com) with relationship to test_org
    - Org user 2 (user2@test.com) with relationship to test_org
    - Other org user (other@test.com) with relationship to other-org
    """
    from tests.helpers.mock_auth import TestUsers

    # Create platform admin user entity
    admin_entity = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"user:{TestUsers.PLATFORM_ADMIN['email']}",
        "Email": TestUsers.PLATFORM_ADMIN["email"],
        "DisplayName": TestUsers.PLATFORM_ADMIN["name"],
        "UserType": "PLATFORM",
        "IsPlatformAdmin": True,
        "IsActive": True,
        "CreatedAt": datetime.utcnow().isoformat(),
        "LastLogin": datetime.utcnow().isoformat(),
    }
    users_service.upsert_entity(admin_entity)

    # Create org user entity
    org_user_entity = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"user:{TestUsers.ORG_USER['email']}",
        "Email": TestUsers.ORG_USER["email"],
        "DisplayName": TestUsers.ORG_USER["name"],
        "UserType": "ORG",
        "IsPlatformAdmin": False,
        "IsActive": True,
        "CreatedAt": datetime.utcnow().isoformat(),
        "LastLogin": datetime.utcnow().isoformat(),
    }
    users_service.upsert_entity(org_user_entity)

    # Create org user 2 entity
    org_user_2_entity = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"user:{TestUsers.ORG_USER_2['email']}",
        "Email": TestUsers.ORG_USER_2["email"],
        "DisplayName": TestUsers.ORG_USER_2["name"],
        "UserType": "ORG",
        "IsPlatformAdmin": False,
        "IsActive": True,
        "CreatedAt": datetime.utcnow().isoformat(),
        "LastLogin": datetime.utcnow().isoformat(),
    }
    users_service.upsert_entity(org_user_2_entity)

    # Create other org user entity
    other_user_entity = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"user:{TestUsers.OTHER_ORG_USER['email']}",
        "Email": TestUsers.OTHER_ORG_USER["email"],
        "DisplayName": TestUsers.OTHER_ORG_USER["name"],
        "UserType": "ORG",
        "IsPlatformAdmin": False,
        "IsActive": True,
        "CreatedAt": datetime.utcnow().isoformat(),
        "LastLogin": datetime.utcnow().isoformat(),
    }
    users_service.upsert_entity(other_user_entity)

    # Create user-org relationships for org users
    # Org user -> test_org
    userperm_entity_1 = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"userperm:{TestUsers.ORG_USER['email']}:{test_org['org_id']}",
        "UserId": TestUsers.ORG_USER["email"],
        "OrganizationId": test_org["org_id"],
        "GrantedBy": "test-system",
        "GrantedAt": datetime.utcnow().isoformat(),
    }
    relationships_service.upsert_entity(userperm_entity_1)

    # Org user 2 -> test_org
    userperm_entity_2 = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"userperm:{TestUsers.ORG_USER_2['email']}:{test_org['org_id']}",
        "UserId": TestUsers.ORG_USER_2["email"],
        "OrganizationId": test_org["org_id"],
        "GrantedBy": "test-system",
        "GrantedAt": datetime.utcnow().isoformat(),
    }
    relationships_service.upsert_entity(userperm_entity_2)

    # Create "other-org" for OTHER_ORG_USER
    other_org_id = TestUsers.OTHER_ORG_USER["org_id"]
    other_org_entity = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"org:{other_org_id}",
        "Name": "Other Test Organization",
        "IsActive": True,
        "CreatedAt": datetime.utcnow().isoformat(),
        "CreatedBy": "test-system",
        "UpdatedAt": datetime.utcnow().isoformat(),
    }
    users_service.upsert_entity(other_org_entity)

    # Other user -> other-org
    userperm_entity_3 = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"userperm:{TestUsers.OTHER_ORG_USER['email']}:{other_org_id}",
        "UserId": TestUsers.OTHER_ORG_USER["email"],
        "OrganizationId": other_org_id,
        "GrantedBy": "test-system",
        "GrantedAt": datetime.utcnow().isoformat(),
    }
    relationships_service.upsert_entity(userperm_entity_3)

    return {
        "platform_admin": TestUsers.PLATFORM_ADMIN,
        "org_user": TestUsers.ORG_USER,
        "org_user_2": TestUsers.ORG_USER_2,
        "other_org_user": TestUsers.OTHER_ORG_USER,
    }
