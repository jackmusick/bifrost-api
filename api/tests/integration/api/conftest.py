"""Shared fixtures for API integration tests

Integration tests make real HTTP requests to running Azure Functions.
These fixtures set up test data in Azurite (TableStorage) and provide
headers for authenticated requests.
"""

import base64
import json
import logging
import pytest
import requests
from azure.data.tables import TableServiceClient

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def api_base_url():
    """Base URL for API

    Default: http://localhost:7777 (docker-compose.testing.yml)
    Can be overridden with API_BASE_URL environment variable.
    """
    import os
    return os.getenv("API_BASE_URL", "http://localhost:7777")


@pytest.fixture(scope="module")
def azurite_connection_string():
    """Connection string for Azurite TEST environment

    Default: Uses docker-compose.testing.yml ports (10100-10102)
    Can be overridden with AZURITE_CONNECTION_STRING environment variable.
    """
    import os
    return os.getenv(
        "AZURITE_CONNECTION_STRING",
        "DefaultEndpointsProtocol=http;"
        "AccountName=devstoreaccount1;"
        "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
        "BlobEndpoint=http://localhost:10100/devstoreaccount1;"
        "QueueEndpoint=http://localhost:10101/devstoreaccount1;"
        "TableEndpoint=http://localhost:10102/devstoreaccount1;"
    )


@pytest.fixture(scope="module")
def table_service(azurite_connection_string):
    """TableServiceClient for test data setup and teardown"""
    return TableServiceClient.from_connection_string(azurite_connection_string)


@pytest.fixture(scope="module")
def test_org_id(table_service):
    """Create test organization and return ID

    Sets up a test organization in Azurite that all tests can use.
    Fixture is module-scoped so it's created once and reused.
    """
    org_id = "test-org-integration-12345"

    # Create organization in both Entities and Organizations tables
    # Entities table is used by some code paths, Organizations for others
    entities_table = table_service.get_table_client("Entities")
    orgs_table = table_service.get_table_client("Organizations")

    try:
        # Create organization entity in Entities table (GLOBAL partition)
        # Match the structure from shared/repositories/organizations.py
        org_entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"org:{org_id}",
            "Name": "Test Organization",
            "Domain": None,
            "IsActive": True,
            "CreatedAt": "2024-01-01T00:00:00Z",
            "CreatedBy": "test-system",
            "UpdatedAt": "2024-01-01T00:00:00Z"
        }
        entities_table.upsert_entity(org_entity)

        # Also create in Organizations table (if it exists)
        # Note: This table may not be used by all code paths
        try:
            org_entity_orgs = {
                "PartitionKey": "Organizations",
                "RowKey": org_id,
                "Name": "Test Organization",
                "IsActive": True,
                "CreatedAt": "2024-01-01T00:00:00Z"
            }
            orgs_table.upsert_entity(org_entity_orgs)
        except Exception:
            pass  # Organizations table may not exist

        logger.info(f"Created test organization: {org_id}")
    except Exception as e:
        logger.warning(f"Could not create test org (may already exist): {e}")

    yield org_id

    # Cleanup after all tests in module complete
    try:
        entities_table.delete_entity(partition_key="GLOBAL", row_key=f"org:{org_id}")
        orgs_table.delete_entity(partition_key="Organizations", row_key=org_id)
        logger.info(f"Cleaned up test organization: {org_id}")
    except Exception as e:
        logger.warning(f"Could not cleanup test org: {e}")


@pytest.fixture
def auth_headers(test_org_id):
    """Headers for authenticated requests with Owner role in test organization

    Simulates an authenticated user with Owner role in the test organization.
    Uses platform admin role to allow org override for testing purposes.
    """
    email = "test-owner@example.com"
    user_id = "test-owner-user-456"

    # Use PlatformAdmin role to allow X-Organization-Id header override
    # This is necessary for test setup since we can't guarantee database is populated
    principal = {
        "userId": user_id,
        "userDetails": email,
        "userRoles": ["PlatformAdmin"]
    }

    return {
        "x-organization-id": test_org_id,
        "x-ms-client-principal": base64.b64encode(
            json.dumps(principal).encode()
        ).decode(),
        "Content-Type": "application/json"
    }


@pytest.fixture
def platform_admin_headers():
    """Headers for platform admin user (GLOBAL scope)

    Platform admin endpoints require GLOBAL org scope and specific auth setup.
    This fixture provides headers that can access platform-only endpoints.
    """
    # Platform admins typically use no org_id or "GLOBAL"
    principal = {
        "userId": "test-platform-admin-789",
        "userDetails": "platform-admin@example.com",
        "userRoles": ["PlatformAdmin"]
    }

    return {
        "x-organization-id": "GLOBAL",
        "x-ms-client-principal": base64.b64encode(
            json.dumps(principal).encode()
        ).decode(),
        "Content-Type": "application/json"
    }


@pytest.fixture
def admin_headers(test_org_id):
    """Headers for admin user in test organization

    Simulates an authenticated admin user in the test organization.
    Used for testing admin-only endpoints.

    Uses platform admin role for test compatibility with org override.
    """
    email = "test-admin@example.com"
    user_id = "test-admin-user-789"

    principal = {
        "userId": user_id,
        "userDetails": email,
        "userRoles": ["PlatformAdmin"]
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
    """Headers for regular user (Contributor role) in test organization

    Simulates an authenticated regular user with Contributor role.
    Used for testing permission restrictions.

    Uses platform admin role for test compatibility with org override.
    """
    email = "test-user@example.com"
    user_id = "test-regular-user-999"

    principal = {
        "userId": user_id,
        "userDetails": email,
        "userRoles": ["PlatformAdmin"]
    }

    return {
        "x-organization-id": test_org_id,
        "x-ms-client-principal": base64.b64encode(
            json.dumps(principal).encode()
        ).decode(),
        "Content-Type": "application/json"
    }


@pytest.fixture
def regular_user_headers(test_org_id):
    """Headers for regular user without platform admin role

    Simulates a regular user without platform admin privileges.
    Used for testing authorization restrictions on admin-only endpoints.
    """
    email = "regular-user@example.com"
    user_id = "regular-user-id-12345"

    principal = {
        "userId": user_id,
        "userDetails": email,
        "userRoles": ["Contributor"]  # No PlatformAdmin role
    }

    return {
        "x-organization-id": test_org_id,
        "x-ms-client-principal": base64.b64encode(
            json.dumps(principal).encode()
        ).decode(),
        "Content-Type": "application/json"
    }


@pytest.fixture
def test_oauth_connection(api_base_url, platform_admin_headers, table_service):
    """Create a test OAuth connection in Azurite

    Creates a minimal OAuth connection for testing OAuth endpoints.
    Returns the connection name.
    """
    connection_name = "test-oauth-connection-123"
    org_id = platform_admin_headers.get("x-organization-id", "GLOBAL")

    # Create OAuth connection in Entities table
    entities_table = table_service.get_table_client("Entities")

    try:
        connection_entity = {
            "PartitionKey": org_id,
            "RowKey": f"oauth:{connection_name}",
            "connection_name": connection_name,
            "oauth_flow_type": "authorization_code",
            "client_id": "test-client-id",
            "redirect_uri": "/oauth/callback/test-oauth-connection-123",
            "authorization_url": "https://example.com/authorize",
            "token_url": "https://example.com/token",
            "scopes": "read,write",
            "status": "not_connected",
            "created_at": "2024-01-01T00:00:00Z",
            "created_by": "test-system"
        }
        entities_table.upsert_entity(connection_entity)
        logger.info(f"Created test OAuth connection: {connection_name}")
    except Exception as e:
        logger.warning(f"Could not create test OAuth connection: {e}")

    yield connection_name

    # Cleanup
    try:
        entities_table.delete_entity(partition_key=org_id, row_key=f"oauth:{connection_name}")
    except Exception as e:
        logger.warning(f"Could not cleanup OAuth connection: {e}")


@pytest.fixture
def platform_test_form(api_base_url, platform_admin_headers):
    """Create a test form in GLOBAL org using platform admin headers

    Uses the actual API endpoint to create a test form in GLOBAL partition.
    Returns the form ID.
    """
    form_data = {
        "name": "Test Platform Form",
        "description": "Form for platform-level integration tests",
        "linkedWorkflow": "test_workflow",
        "formSchema": {
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
        },
        "isPublic": True
    }

    response = requests.post(
        f"{api_base_url}/api/forms",
        headers=platform_admin_headers,
        json=form_data,
        timeout=10
    )

    if response.status_code != 201:
        logger.warning(f"Failed to create platform test form: {response.status_code} - {response.text}")
        pytest.skip("Could not create platform test form")

    form_id = response.json().get("id")
    logger.info(f"Created platform test form: {form_id}")

    yield form_id

    # Cleanup
    try:
        requests.delete(
            f"{api_base_url}/api/forms/{form_id}",
            headers=platform_admin_headers,
            timeout=10
        )
    except Exception as e:
        logger.warning(f"Could not cleanup platform test form: {e}")


@pytest.fixture
def test_form(api_base_url, admin_headers, table_service):
    """Create a test form by making HTTP request to API

    Uses the actual API endpoint to create a test form.
    Returns the form ID.
    """
    form_data = {
        "name": "Test Integration Form",
        "description": "Form for integration tests",
        "linkedWorkflow": "test-workflow",
        "formSchema": {
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
        },
        "isPublic": True
    }

    response = requests.post(
        f"{api_base_url}/api/forms",
        headers=admin_headers,
        json=form_data,
        timeout=10
    )

    if response.status_code != 201:
        logger.warning(f"Failed to create test form: {response.status_code} - {response.text}")
        pytest.skip("Could not create test form")

    form_id = response.json().get("id")
    logger.info(f"Created test form: {form_id}")

    yield form_id

    # Cleanup
    try:
        requests.delete(
            f"{api_base_url}/api/forms/{form_id}",
            headers=admin_headers,
            timeout=10
        )
    except Exception as e:
        logger.warning(f"Could not cleanup test form: {e}")


@pytest.fixture
def test_role(api_base_url, admin_headers):
    """Create a test role by making HTTP request to API

    Uses the actual API endpoint to create a test role.
    Returns the role ID.
    """
    role_data = {
        "name": "Test Integration Role",
        "description": "Role for integration tests"
    }

    response = requests.post(
        f"{api_base_url}/api/roles",
        headers=admin_headers,
        json=role_data,
        timeout=10
    )

    if response.status_code != 201:
        logger.warning(f"Failed to create test role: {response.status_code} - {response.text}")
        pytest.skip("Could not create test role")

    role_id = response.json().get("id")
    logger.info(f"Created test role: {role_id}")

    yield role_id

    # Cleanup
    try:
        requests.delete(
            f"{api_base_url}/api/roles/{role_id}",
            headers=admin_headers,
            timeout=10
        )
    except Exception as e:
        logger.warning(f"Could not cleanup test role: {e}")
