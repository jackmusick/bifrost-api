"""
Unit tests for roles source handlers
Tests role determination logic with mocked provisioning
"""

from unittest.mock import patch

import pytest

from shared.handlers.roles_source_handlers import (
    extract_user_info,
    get_roles_for_user,
    handle_roles_source_request,
)
from shared.user_provisioning import UserProvisioningResult


class TestExtractUserInfo:
    """Tests for extract_user_info function"""

    def test_extracts_valid_user_info(self):
        """Test extraction of valid user ID and email"""
        request_body = {
            "identityProvider": "aad",
            "userId": "user-123",
            "userDetails": "user@example.com",
            "claims": [{"typ": "name", "val": "Test User"}],
        }

        entra_id, user_email, display_name = extract_user_info(request_body)

        assert entra_id == "user-123"
        assert user_email == "user@example.com"
        assert display_name == "Test User"

    def test_handles_missing_userId(self):
        """Test extraction when userId is missing"""
        request_body = {
            "identityProvider": "aad",
            "userDetails": "user@example.com",
            "claims": [],
        }

        entra_id, user_email, display_name = extract_user_info(request_body)

        assert entra_id is None
        assert user_email == "user@example.com"
        assert display_name is None

    def test_handles_missing_userDetails(self):
        """Test extraction when userDetails is missing"""
        request_body = {
            "identityProvider": "aad",
            "userId": "user-123",
            "claims": [],
        }

        entra_id, user_email, display_name = extract_user_info(request_body)

        assert entra_id == "user-123"
        assert user_email is None
        assert display_name is None

    def test_handles_empty_request(self):
        """Test extraction from empty request body"""
        request_body: dict = {}

        entra_id, user_email, display_name = extract_user_info(request_body)

        assert entra_id is None
        assert user_email is None
        assert display_name is None

    def test_handles_none_values(self):
        """Test extraction when userId and userDetails are None"""
        request_body = {
            "identityProvider": "aad",
            "userId": None,
            "userDetails": None,
            "claims": [],
        }

        entra_id, user_email, display_name = extract_user_info(request_body)

        assert entra_id is None
        assert user_email is None
        assert display_name is None


class TestGetRolesForUser:
    """Tests for get_roles_for_user function"""

    @patch("shared.handlers.roles_source_handlers.ensure_user_provisioned")
    def test_returns_platform_admin_roles(self, mock_provision):
        """Test returning roles for a platform admin user"""
        # Create result for platform admin
        result = UserProvisioningResult(
            user_type="PLATFORM",
            is_platform_admin=True,
            org_id=None,
            was_created=False,
        )
        mock_provision.return_value = result

        response = get_roles_for_user("admin@example.com")

        assert response["roles"] == ["authenticated", "PlatformAdmin"]
        mock_provision.assert_called_once_with("admin@example.com", None, None)

    @patch("shared.handlers.roles_source_handlers.ensure_user_provisioned")
    def test_returns_org_user_roles(self, mock_provision):
        """Test returning roles for an organization user"""
        # Create result for org user
        result = UserProvisioningResult(
            user_type="ORG",
            is_platform_admin=False,
            org_id="org-123",
            was_created=False,
        )
        mock_provision.return_value = result

        response = get_roles_for_user("user@org.com")

        assert response["roles"] == ["authenticated", "OrgUser"]
        mock_provision.assert_called_once_with("user@org.com", None, None)

    @patch("shared.handlers.roles_source_handlers.ensure_user_provisioned")
    def test_raises_on_provisioning_failure(self, mock_provision):
        """Test that ValueError is re-raised when provisioning fails"""
        mock_provision.side_effect = ValueError("No matching domain found")

        with pytest.raises(ValueError) as exc_info:
            get_roles_for_user("unknown@nomatch.com")

        assert "No matching domain found" in str(exc_info.value)
        mock_provision.assert_called_once_with("unknown@nomatch.com", None, None)

    @patch("shared.handlers.roles_source_handlers.ensure_user_provisioned")
    def test_new_user_created_as_admin(self, mock_provision):
        """Test that new user becomes platform admin if first user"""
        result = UserProvisioningResult(
            user_type="PLATFORM",
            is_platform_admin=True,
            org_id=None,
            was_created=True,
        )
        mock_provision.return_value = result

        response = get_roles_for_user("firstuser@example.com")

        assert response["roles"] == ["authenticated", "PlatformAdmin"]
        assert mock_provision.return_value.was_created is True

    @patch("shared.handlers.roles_source_handlers.ensure_user_provisioned")
    def test_new_user_created_as_org_user(self, mock_provision):
        """Test that new user joins org if domain matches"""
        result = UserProvisioningResult(
            user_type="ORG",
            is_platform_admin=False,
            org_id="org-456",
            was_created=True,
        )
        mock_provision.return_value = result

        response = get_roles_for_user("newuser@existing-org.com")

        assert response["roles"] == ["authenticated", "OrgUser"]
        assert mock_provision.return_value.org_id == "org-456"


class TestHandleRolesSourceRequest:
    """Tests for handle_roles_source_request (main entry point)"""

    @patch("shared.handlers.roles_source_handlers.get_roles_for_user")
    def test_valid_request_with_both_fields(self, mock_get_roles):
        """Test handling valid request with userId and userDetails"""
        mock_get_roles.return_value = {"roles": ["authenticated", "PlatformAdmin"]}

        request_body = {
            "identityProvider": "aad",
            "userId": "user-123",
            "userDetails": "user@example.com",
            "claims": [],
        }

        response = handle_roles_source_request(request_body)

        assert response["roles"] == ["authenticated", "PlatformAdmin"]
        mock_get_roles.assert_called_once_with("user@example.com", "user-123", None)

    @patch("shared.handlers.roles_source_handlers.get_roles_for_user")
    def test_missing_userId_still_provisions_user(self, mock_get_roles):
        """Test that missing userId doesn't prevent provisioning if userDetails is present"""
        # userId is optional - userDetails (email) is what matters for provisioning
        mock_get_roles.return_value = {"roles": ["authenticated", "PlatformAdmin"]}

        request_body = {
            "identityProvider": "aad",
            "userDetails": "user@example.com",
            "claims": [],
        }

        response = handle_roles_source_request(request_body)

        assert response["roles"] == ["authenticated", "PlatformAdmin"]
        mock_get_roles.assert_called_once_with("user@example.com", None, None)

    def test_missing_userDetails_returns_anonymous(self):
        """Test that missing userDetails returns anonymous role"""
        request_body = {
            "identityProvider": "aad",
            "userId": "user-123",
            "claims": [],
        }

        response = handle_roles_source_request(request_body)

        assert response["roles"] == ["anonymous"]

    def test_missing_both_fields_returns_anonymous(self):
        """Test that missing both fields returns anonymous role"""
        request_body = {
            "identityProvider": "aad",
            "claims": [],
        }

        response = handle_roles_source_request(request_body)

        assert response["roles"] == ["anonymous"]

    def test_empty_request_returns_anonymous(self):
        """Test that empty request returns anonymous role"""
        request_body: dict = {}

        response = handle_roles_source_request(request_body)

        assert response["roles"] == ["anonymous"]

    @patch("shared.handlers.roles_source_handlers.get_roles_for_user")
    def test_provisioning_failure_raises_error(self, mock_get_roles):
        """Test that provisioning failures are propagated"""
        mock_get_roles.side_effect = ValueError("No domain match")

        request_body = {
            "identityProvider": "aad",
            "userId": "user-123",
            "userDetails": "user@nomatch.com",
            "claims": [],
        }

        with pytest.raises(ValueError) as exc_info:
            handle_roles_source_request(request_body)

        assert "No domain match" in str(exc_info.value)

    @patch("shared.handlers.roles_source_handlers.get_roles_for_user")
    def test_different_identity_providers(self, mock_get_roles):
        """Test that different identity providers are handled"""
        mock_get_roles.return_value = {"roles": ["authenticated", "OrgUser"]}

        for provider in ["aad", "github", "google", "twitter"]:
            request_body = {
                "identityProvider": provider,
                "userId": "user-123",
                "userDetails": "user@example.com",
                "claims": [],
            }

            response = handle_roles_source_request(request_body)

            assert response["roles"] == ["authenticated", "OrgUser"]

    @patch("shared.handlers.roles_source_handlers.get_roles_for_user")
    def test_multiple_roles_returned(self, mock_get_roles):
        """Test that multiple roles are properly returned"""
        mock_get_roles.return_value = {
            "roles": ["authenticated", "PlatformAdmin", "CanExecuteWorkflows"]
        }

        request_body = {
            "identityProvider": "aad",
            "userId": "user-123",
            "userDetails": "admin@example.com",
            "claims": [],
        }

        response = handle_roles_source_request(request_body)

        assert len(response["roles"]) == 3
        assert "authenticated" in response["roles"]
        assert "PlatformAdmin" in response["roles"]
        assert "CanExecuteWorkflows" in response["roles"]


class TestResponseStructure:
    """Tests for response format and structure"""

    def test_response_has_roles_key(self):
        """Test that response contains 'roles' key"""
        request_body = {
            "identityProvider": "aad",
            "claims": [],
        }

        response = handle_roles_source_request(request_body)

        assert "roles" in response
        assert isinstance(response["roles"], list)

    def test_roles_are_strings(self):
        """Test that all roles in response are strings"""
        request_body = {
            "identityProvider": "aad",
            "claims": [],
        }

        response = handle_roles_source_request(request_body)

        for role in response["roles"]:
            assert isinstance(role, str)

    @patch("shared.handlers.roles_source_handlers.get_roles_for_user")
    def test_response_format_matches_swa_expectation(self, mock_get_roles):
        """Test that response matches SWA expected format"""
        mock_get_roles.return_value = {"roles": ["authenticated", "PlatformAdmin"]}

        request_body = {
            "identityProvider": "aad",
            "userId": "user-123",
            "userDetails": "user@example.com",
            "claims": [],
        }

        response = handle_roles_source_request(request_body)

        # Response should be a dict with only "roles" key
        assert isinstance(response, dict)
        assert list(response.keys()) == ["roles"]
        assert isinstance(response["roles"], list)
