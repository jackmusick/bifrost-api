"""
Test the pytest fixtures themselves to ensure they work correctly
"""

import pytest


def test_azurite_tables(azurite_tables):
    """Test that Azurite tables fixture works"""
    assert azurite_tables == "UseDevelopmentStorage=true"


def test_table_service(table_service):
    """Test that table_service fixture returns TableStorageService"""
    assert table_service is not None
    assert table_service.table_name == "Organizations"


def test_test_org_fixture(test_org):
    """Test that test_org fixture creates an organization"""
    assert "org_id" in test_org
    assert "name" in test_org
    assert "tenant_id" in test_org
    assert test_org["name"] == "Test Organization"


def test_test_user_fixture(test_user):
    """Test that test_user fixture creates a user"""
    assert "user_id" in test_user
    assert "email" in test_user
    assert test_user["email"] == "test@example.com"


def test_test_user_with_full_permissions(test_user_with_full_permissions):
    """Test that user with full permissions is created correctly"""
    assert "user_id" in test_user_with_full_permissions
    assert "org_id" in test_user_with_full_permissions
    assert "permissions" in test_user_with_full_permissions
    assert test_user_with_full_permissions["permissions"]["canExecuteWorkflows"] is True
    assert test_user_with_full_permissions["permissions"]["canManageConfig"] is True


def test_test_org_with_config(test_org_with_config, org_config_service):
    """Test that org with config is created correctly"""
    assert "configs" in test_org_with_config
    assert test_org_with_config["configs"]["default_location"] == "NYC"
    assert test_org_with_config["configs"]["timeout"] == "30"

    # Verify configs exist in table
    configs = list(org_config_service.query_by_org(
        test_org_with_config["org_id"],
        row_key_prefix="config:"
    ))
    assert len(configs) == 2


def test_test_form_fixture(test_form):
    """Test that form fixture creates a form"""
    assert "form_id" in test_form
    assert "org_id" in test_form
    assert "linked_workflow" in test_form
    assert test_form["linked_workflow"] == "user_onboarding"
    assert len(test_form["form_schema"]["fields"]) == 3


def test_mock_context_fixture(mock_context, test_org):
    """Test that mock context is created correctly"""
    assert mock_context.org_id == test_org["org_id"]
    assert mock_context.org_name == test_org["name"]
    assert mock_context.get_config("test_key") == "mock-value"


def test_mock_jwt_token_fixture(mock_jwt_token, test_user):
    """Test that mock JWT token is created"""
    assert mock_jwt_token is not None
    assert isinstance(mock_jwt_token, str)

    # Decode and verify payload
    import jwt
    payload = jwt.decode(mock_jwt_token, options={"verify_signature": False})
    assert payload["oid"] == test_user["user_id"]
    assert payload["preferred_username"] == test_user["email"]


def test_multiple_orgs(test_org, test_org_2):
    """Test that multiple org fixtures work together"""
    assert test_org["org_id"] != test_org_2["org_id"]
    assert test_org["name"] != test_org_2["name"]


def test_multiple_users(test_user, test_user_2):
    """Test that multiple user fixtures work together"""
    assert test_user["user_id"] != test_user_2["user_id"]
    assert test_user["email"] != test_user_2["email"]
