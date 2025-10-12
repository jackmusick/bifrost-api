"""
Pytest fixtures for MSP Automation Platform tests
Provides reusable test infrastructure for all test files
"""

import os
import pytest
import uuid
from datetime import datetime
from typing import Dict, Any
from azure.data.tables import TableServiceClient

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.storage import TableStorageService
from shared.init_tables import init_tables, REQUIRED_TABLES


# ==================== CONFIGURATION ====================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables"""
    os.environ["TABLE_STORAGE_CONNECTION_STRING"] = "UseDevelopmentStorage=true"
    os.environ["KEY_VAULT_URL"] = "https://test-keyvault.vault.azure.net/"
    os.environ["AZURE_TENANT_ID"] = "test-tenant-id"
    os.environ["AZURE_CLIENT_ID"] = "test-client-id"
    yield


# ==================== INFRASTRUCTURE FIXTURES ====================

@pytest.fixture(scope="function")
def azurite_tables():
    """
    Initialize all 9 tables in Azurite and clean up after test
    Scope: function - ensures test isolation
    """
    connection_string = "UseDevelopmentStorage=true"

    # Initialize tables
    results = init_tables(connection_string)

    yield connection_string

    # Cleanup - delete all entities from all tables
    service_client = TableServiceClient.from_connection_string(connection_string)
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
        except Exception as e:
            # Table might not exist or be empty - that's OK
            pass


@pytest.fixture
def table_service(azurite_tables):
    """Returns TableStorageService instance for Organizations table"""
    return TableStorageService("Organizations")


@pytest.fixture
def org_config_service(azurite_tables):
    """Returns TableStorageService instance for OrgConfig table"""
    return TableStorageService("OrgConfig")


@pytest.fixture
def user_service(azurite_tables):
    """Returns TableStorageService instance for Users table"""
    return TableStorageService("Users")


@pytest.fixture
def permissions_service(azurite_tables):
    """Returns TableStorageService instance for UserPermissions table"""
    return TableStorageService("UserPermissions")


@pytest.fixture
def forms_service(azurite_tables):
    """Returns TableStorageService instance for Forms table"""
    return TableStorageService("Forms")


# ==================== ENTITY FIXTURES ====================

@pytest.fixture
def test_org(table_service) -> Dict[str, Any]:
    """
    Creates a test organization
    Returns dict with org_id, name, tenant_id
    """
    org_id = f"org-test-{uuid.uuid4()}"
    tenant_id = str(uuid.uuid4())

    entity = {
        "PartitionKey": "ORG",
        "RowKey": org_id,
        "Name": "Test Organization",
        "TenantId": tenant_id,
        "IsActive": True,
        "CreatedAt": datetime.utcnow().isoformat(),
        "CreatedBy": "test-system",
        "UpdatedAt": datetime.utcnow().isoformat(),
    }

    table_service.insert_entity(entity)

    return {
        "org_id": org_id,
        "name": "Test Organization",
        "tenant_id": tenant_id
    }


@pytest.fixture
def test_org_2(table_service) -> Dict[str, Any]:
    """
    Creates a second test organization for multi-org tests
    """
    org_id = f"org-test-2-{uuid.uuid4()}"
    tenant_id = str(uuid.uuid4())

    entity = {
        "PartitionKey": "ORG",
        "RowKey": org_id,
        "Name": "Test Organization 2",
        "TenantId": tenant_id,
        "IsActive": True,
        "CreatedAt": datetime.utcnow().isoformat(),
        "CreatedBy": "test-system",
        "UpdatedAt": datetime.utcnow().isoformat(),
    }

    table_service.insert_entity(entity)

    return {
        "org_id": org_id,
        "name": "Test Organization 2",
        "tenant_id": tenant_id
    }


@pytest.fixture
def test_user(user_service) -> Dict[str, Any]:
    """
    Creates a test user
    Returns dict with user_id, email
    """
    user_id = f"user-test-{uuid.uuid4()}"

    entity = {
        "PartitionKey": "USER",
        "RowKey": user_id,
        "Email": "test@example.com",
        "DisplayName": "Test User",
        "IsActive": True,
        "CreatedAt": datetime.utcnow().isoformat(),
        "LastLogin": datetime.utcnow().isoformat(),
    }

    user_service.insert_entity(entity)

    return {
        "user_id": user_id,
        "email": "test@example.com",
        "display_name": "Test User"
    }


@pytest.fixture
def test_user_2(user_service) -> Dict[str, Any]:
    """
    Creates a second test user for permission tests
    """
    user_id = f"user-test-2-{uuid.uuid4()}"

    entity = {
        "PartitionKey": "USER",
        "RowKey": user_id,
        "Email": "test2@example.com",
        "DisplayName": "Test User 2",
        "IsActive": True,
        "CreatedAt": datetime.utcnow().isoformat(),
        "LastLogin": datetime.utcnow().isoformat(),
    }

    user_service.insert_entity(entity)

    return {
        "user_id": user_id,
        "email": "test2@example.com",
        "display_name": "Test User 2"
    }


# ==================== PERMISSION FIXTURES ====================

@pytest.fixture
def test_user_with_full_permissions(test_org, test_user, permissions_service) -> Dict[str, Any]:
    """
    Grants all 4 permissions to test_user for test_org
    Returns combined dict with user and org info
    """
    user_permission_entity = {
        "PartitionKey": test_user["user_id"],
        "RowKey": test_org["org_id"],
        "CanExecuteWorkflows": True,
        "CanManageConfig": True,
        "CanManageForms": True,
        "CanViewHistory": True,
        "GrantedBy": "test-system",
        "GrantedAt": datetime.utcnow().isoformat(),
    }

    permissions_service.insert_entity(user_permission_entity)

    # Also insert into OrgPermissions table (dual-indexed)
    org_permissions_service = TableStorageService("OrgPermissions")
    org_permission_entity = {
        "PartitionKey": test_org["org_id"],
        "RowKey": test_user["user_id"],
        "CanExecuteWorkflows": True,
        "CanManageConfig": True,
        "CanManageForms": True,
        "CanViewHistory": True,
        "GrantedBy": "test-system",
        "GrantedAt": datetime.utcnow().isoformat(),
    }
    org_permissions_service.insert_entity(org_permission_entity)

    return {
        **test_user,
        **test_org,
        "permissions": {
            "canExecuteWorkflows": True,
            "canManageConfig": True,
            "canManageForms": True,
            "canViewHistory": True,
        }
    }


@pytest.fixture
def test_user_with_no_permissions(test_org, test_user, permissions_service) -> Dict[str, Any]:
    """
    Creates user with zero permissions (all flags False)
    """
    user_permission_entity = {
        "PartitionKey": test_user["user_id"],
        "RowKey": test_org["org_id"],
        "CanExecuteWorkflows": False,
        "CanManageConfig": False,
        "CanManageForms": False,
        "CanViewHistory": False,
        "GrantedBy": "test-system",
        "GrantedAt": datetime.utcnow().isoformat(),
    }

    permissions_service.insert_entity(user_permission_entity)

    # Also insert into OrgPermissions table
    org_permissions_service = TableStorageService("OrgPermissions")
    org_permission_entity = {
        "PartitionKey": test_org["org_id"],
        "RowKey": test_user["user_id"],
        "CanExecuteWorkflows": False,
        "CanManageConfig": False,
        "CanManageForms": False,
        "CanViewHistory": False,
        "GrantedBy": "test-system",
        "GrantedAt": datetime.utcnow().isoformat(),
    }
    org_permissions_service.insert_entity(org_permission_entity)

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


# ==================== CONFIG FIXTURES ====================

@pytest.fixture
def test_org_with_config(test_org, org_config_service) -> Dict[str, Any]:
    """
    Creates org with sample configs
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
        org_config_service.insert_entity(config)

    return {
        **test_org,
        "configs": {
            "default_location": "NYC",
            "timeout": "30"
        }
    }


# ==================== FORM FIXTURES ====================

@pytest.fixture
def test_form(test_org, forms_service) -> Dict[str, Any]:
    """
    Creates a sample form linked to user_onboarding workflow
    """
    import json

    form_id = f"form-test-{uuid.uuid4()}"

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
        "RowKey": form_id,
        "Name": "Test User Onboarding Form",
        "Description": "Test form for user onboarding workflow",
        "LinkedWorkflow": "user_onboarding",
        "FormSchema": json.dumps(form_schema),
        "IsActive": True,
        "CreatedBy": "test-system",
        "CreatedAt": datetime.utcnow().isoformat(),
        "UpdatedAt": datetime.utcnow().isoformat(),
    }

    forms_service.insert_entity(entity)

    return {
        "form_id": form_id,
        "org_id": test_org["org_id"],
        "name": "Test User Onboarding Form",
        "linked_workflow": "user_onboarding",
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
    context.tenant_id = test_org["tenant_id"]

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
    import jwt
    from datetime import timedelta

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
    connection_string = "UseDevelopmentStorage=true"
    service = TableStorageService(table_name)

    entities = list(service.query_entities())
    for entity in entities:
        service.delete_entity(
            partition_key=entity["PartitionKey"],
            row_key=entity["RowKey"]
        )
