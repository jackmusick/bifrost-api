"""
Integration tests for user provisioning workflows.

Tests the complete first user experience:
- First user becomes platform admin
- Subsequent users are not auto-promoted
- Domain-based user assignment to organizations
"""

import pytest
import requests

from tests.fixtures.auth import create_test_jwt, auth_headers


@pytest.mark.integration
class TestFirstUserJourney:
    """Test the complete first user provisioning experience"""

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
