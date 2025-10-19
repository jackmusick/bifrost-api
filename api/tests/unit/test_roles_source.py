"""
Unit tests for GetRoles endpoint (roles_source.py)
Tests automatic role assignment by Azure Static Web Apps

Note: Now that business logic is in shared/user_provisioning.py,
these tests focus on HTTP request/response handling.
"""

import json
from unittest.mock import Mock, patch

import azure.functions as func
import pytest

from functions.roles_source import get_roles
from shared.user_provisioning import UserProvisioningResult


class TestGetRoles:
    """Test GetRoles endpoint for SWA role assignment"""

    @patch("shared.handlers.roles_source_handlers.ensure_user_provisioned")
    def test_platform_admin_user(self, mock_provision):
        """PlatformAdmin user gets correct roles"""
        # Mock provisioning returns PlatformAdmin
        mock_provision.return_value = UserProvisioningResult(
            user_type="PLATFORM", is_platform_admin=True, org_id=None, was_created=False
        )

        # Create request from SWA
        req = Mock(spec=func.HttpRequest)
        req.get_json.return_value = {
            "userId": "admin-id-456",
            "userDetails": "admin@example.com",
            "identityProvider": "aad",
        }

        # Call GetRoles
        response = get_roles(req)

        # Verify response
        assert response.status_code == 200
        body = json.loads(response.get_body())
        assert "roles" in body
        assert "authenticated" in body["roles"]
        assert "PlatformAdmin" in body["roles"]

        # Verify provisioning was called
        mock_provision.assert_called_once_with("admin@example.com")

    @patch("shared.handlers.roles_source_handlers.ensure_user_provisioned")
    def test_org_user(self, mock_provision):
        """OrgUser gets correct roles"""
        # Mock provisioning returns OrgUser
        mock_provision.return_value = UserProvisioningResult(
            user_type="ORG", is_platform_admin=False, org_id="org-123", was_created=False
        )

        # Create request from SWA
        req = Mock(spec=func.HttpRequest)
        req.get_json.return_value = {
            "userId": "user-id-789",
            "userDetails": "user@example.com",
            "identityProvider": "aad",
        }

        # Call GetRoles
        response = get_roles(req)

        # Verify response
        assert response.status_code == 200
        body = json.loads(response.get_body())
        assert "roles" in body
        assert "authenticated" in body["roles"]
        assert "OrgUser" in body["roles"]
        assert "PlatformAdmin" not in body["roles"]

    @patch("shared.handlers.roles_source_handlers.ensure_user_provisioned")
    def test_first_user_creation(self, mock_provision):
        """First user is auto-promoted to PlatformAdmin"""
        # Mock provisioning creates first user
        mock_provision.return_value = UserProvisioningResult(
            user_type="PLATFORM", is_platform_admin=True, org_id=None, was_created=True
        )

        # Create request from SWA
        req = Mock(spec=func.HttpRequest)
        req.get_json.return_value = {
            "userId": "first-user-id",
            "userDetails": "first@example.com",
            "identityProvider": "aad",
        }

        # Call GetRoles
        response = get_roles(req)

        # Verify response
        assert response.status_code == 200
        body = json.loads(response.get_body())
        assert "authenticated" in body["roles"]
        assert "PlatformAdmin" in body["roles"]

    @patch("shared.handlers.roles_source_handlers.ensure_user_provisioned")
    def test_provisioning_failure_no_domain_match(self, mock_provision):
        """User with no domain match gets anonymous role"""
        # Mock provisioning raises ValueError (no domain match)
        mock_provision.side_effect = ValueError("No organization configured for domain")

        # Create request from SWA
        req = Mock(spec=func.HttpRequest)
        req.get_json.return_value = {
            "userId": "new-user-id",
            "userDetails": "newuser@nomatch.com",
            "identityProvider": "aad",
        }

        # Call GetRoles
        response = get_roles(req)

        # Verify response (anonymous)
        assert response.status_code == 200
        body = json.loads(response.get_body())
        assert "roles" in body
        assert body["roles"] == ["anonymous"]

    def test_no_user_id_provided(self):
        """Request without userId gets anonymous role"""
        # Create request without userId
        req = Mock(spec=func.HttpRequest)
        req.get_json.return_value = {"identityProvider": "aad"}

        # Call GetRoles
        response = get_roles(req)

        # Verify response
        assert response.status_code == 200
        body = json.loads(response.get_body())
        assert "roles" in body
        assert body["roles"] == ["anonymous"]

    def test_no_user_email_provided(self):
        """Request without userDetails gets anonymous role"""
        # Create request without userDetails
        req = Mock(spec=func.HttpRequest)
        req.get_json.return_value = {"userId": "user-id", "identityProvider": "aad"}

        # Call GetRoles
        response = get_roles(req)

        # Verify response
        assert response.status_code == 200
        body = json.loads(response.get_body())
        assert "roles" in body
        assert body["roles"] == ["anonymous"]

    @patch("shared.handlers.roles_source_handlers.ensure_user_provisioned")
    def test_error_handling(self, mock_provision):
        """Unexpected errors result in anonymous role for safety"""
        # Mock provisioning raises unexpected exception
        mock_provision.side_effect = Exception("Database error")

        # Create request
        req = Mock(spec=func.HttpRequest)
        req.get_json.return_value = {
            "userId": "user-id",
            "userDetails": "user@example.com",
            "identityProvider": "aad",
        }

        # Call GetRoles
        response = get_roles(req)

        # Verify response (should return anonymous on error)
        assert response.status_code == 200
        body = json.loads(response.get_body())
        assert "roles" in body
        assert body["roles"] == ["anonymous"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
