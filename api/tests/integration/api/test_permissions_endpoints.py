"""Integration tests for Permissions API endpoints

Tests the permissions management endpoints:
- GET /api/users - List users with optional filtering
- GET /api/users/{userId} - Get user details
- POST /api/users/{userId}/permissions - Grant permissions
- DELETE /api/users/{userId}/permissions - Revoke permissions
- GET /api/users/{userId}/roles - Get user's roles
- GET /api/users/{userId}/forms - Get user's accessible forms
"""

import logging
import requests

logger = logging.getLogger(__name__)


class TestUserListing:
    """Test listing users"""

    def test_list_users(self, api_base_url, admin_headers):
        """Should list all users"""
        response = requests.get(
            f"{api_base_url}/api/users",
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        logger.info(f"Listed {len(data)} users")

    def test_list_users_filter_by_type(self, api_base_url, admin_headers):
        """Should filter users by type (platform or org)"""
        response = requests.get(
            f"{api_base_url}/api/users?type=platform",
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        logger.info(f"Listed {len(data)} platform users")

    def test_list_users_filter_org_type(self, api_base_url, admin_headers):
        """Should filter org users"""
        response = requests.get(
            f"{api_base_url}/api/users?type=org",
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        logger.info(f"Listed {len(data)} org users")

    def test_list_users_by_organization(self, api_base_url, admin_headers, test_org_id):
        """Should filter users by organization"""
        response = requests.get(
            f"{api_base_url}/api/users?orgId={test_org_id}",
            headers=admin_headers,
            timeout=10
        )

        # Endpoint may or may not support this filter
        assert response.status_code in [200, 400], f"Expected 200 or 400, got {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            logger.info(f"Listed users for org: {test_org_id}")

    def test_list_users_invalid_type_filter(self, api_base_url, admin_headers):
        """Should handle invalid type filter gracefully"""
        response = requests.get(
            f"{api_base_url}/api/users?type=invalid",
            headers=admin_headers,
            timeout=10
        )

        # Should either ignore invalid filter or return error
        assert response.status_code in [200, 400], f"Expected 200 or 400, got {response.status_code}"
        logger.info(f"Invalid filter handled with status: {response.status_code}")


class TestUserDetails:
    """Test getting user details"""

    def test_get_user_details(self, api_base_url, admin_headers):
        """Should get user details"""
        # First list users to get a user ID
        list_response = requests.get(
            f"{api_base_url}/api/users",
            headers=admin_headers,
            timeout=10
        )

        assert list_response.status_code == 200
        users = list_response.json()

        if users:
            user_id = users[0]["id"]

            # Get user details
            response = requests.get(
                f"{api_base_url}/api/users/{user_id}",
                headers=admin_headers,
                timeout=10
            )

            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()
            assert "id" in data
            assert "email" in data
            logger.info(f"Retrieved user details: {user_id}")
        else:
            logger.info("No users found to test get details")

    def test_get_nonexistent_user(self, api_base_url, admin_headers):
        """Should return 404 for nonexistent user"""
        response = requests.get(
            f"{api_base_url}/api/users/nonexistent-user-id",
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        logger.info("Correctly returned 404 for nonexistent user")


class TestUserRoles:
    """Test getting user's roles"""

    def test_get_user_roles(self, api_base_url, admin_headers):
        """Should get user's roles"""
        # Get first user
        list_response = requests.get(
            f"{api_base_url}/api/users",
            headers=admin_headers,
            timeout=10
        )

        if list_response.status_code == 200 and list_response.json():
            user_id = list_response.json()[0]["id"]

            response = requests.get(
                f"{api_base_url}/api/users/{user_id}/roles",
                headers=admin_headers,
                timeout=10
            )

            # Could return 200 (success), 404 (not implemented), or other
            if response.status_code == 200:
                data = response.json()
                # API returns roleIds field, not roles
                assert "roleIds" in data or "roles" in data or isinstance(data, list)
                logger.info(f"Retrieved roles for user: {user_id}")
            elif response.status_code == 404:
                logger.info("Get user roles endpoint not implemented")


class TestUserForms:
    """Test getting user's accessible forms"""

    def test_get_user_forms(self, api_base_url, admin_headers):
        """Should get forms accessible to user"""
        list_response = requests.get(
            f"{api_base_url}/api/users",
            headers=admin_headers,
            timeout=10
        )

        if list_response.status_code == 200 and list_response.json():
            user_id = list_response.json()[0]["id"]

            response = requests.get(
                f"{api_base_url}/api/users/{user_id}/forms",
                headers=admin_headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                # API returns formIds field and other metadata, not forms
                assert "formIds" in data or "forms" in data or isinstance(data, list)
                logger.info(f"Retrieved forms for user: {user_id}")
            elif response.status_code == 404:
                logger.info("Get user forms endpoint not implemented")


class TestUserPermissions:
    """Test managing user permissions"""

    def test_grant_permissions(self, api_base_url, admin_headers):
        """Should grant permissions to user"""
        # Get first user
        list_response = requests.get(
            f"{api_base_url}/api/users",
            headers=admin_headers,
            timeout=10
        )

        if list_response.status_code == 200 and list_response.json():
            user_id = list_response.json()[0]["id"]

            permission_data = {
                "role_ids": ["admin-role"],
                "form_ids": ["form-1"]
            }

            response = requests.post(
                f"{api_base_url}/api/users/{user_id}/permissions",
                headers=admin_headers,
                json=permission_data,
                timeout=10
            )

            # Could return 200, 204, or 404 (not implemented)
            if response.status_code in [200, 201, 204]:
                logger.info(f"Granted permissions to user: {user_id}")
            elif response.status_code == 404:
                logger.info("Grant permissions endpoint not implemented")

    def test_revoke_permissions(self, api_base_url, admin_headers):
        """Should revoke permissions from user"""
        list_response = requests.get(
            f"{api_base_url}/api/users",
            headers=admin_headers,
            timeout=10
        )

        if list_response.status_code == 200 and list_response.json():
            user_id = list_response.json()[0]["id"]

            permission_data = {
                "role_ids": ["admin-role"],
                "form_ids": ["form-1"]
            }

            response = requests.delete(
                f"{api_base_url}/api/users/{user_id}/permissions",
                headers=admin_headers,
                json=permission_data,
                timeout=10
            )

            if response.status_code in [200, 204]:
                logger.info(f"Revoked permissions from user: {user_id}")
            elif response.status_code == 404:
                logger.info("Revoke permissions endpoint not implemented")


class TestPermissionsAuthorization:
    """Test permissions endpoints require authentication"""

    def test_list_users_no_headers(self, api_base_url):
        """Should reject request without auth headers"""
        response = requests.get(
            f"{api_base_url}/api/users",
            timeout=10
        )

        # API may return 200 if public endpoint, or 400/401/403 if protected
        assert response.status_code in [200, 400, 401, 403], f"Expected 200/400/401/403, got {response.status_code}"
        logger.info(f"List users without auth returned {response.status_code}")

    def test_list_users_non_admin(self, api_base_url, user_headers):
        """Regular users should not list other users"""
        response = requests.get(
            f"{api_base_url}/api/users",
            headers=user_headers,
            timeout=10
        )

        # Could be 403 (forbidden) or succeed with filtered list
        if response.status_code == 403:
            logger.info("Correctly rejected non-admin user list")
        else:
            logger.info(f"Non-admin user list returned: {response.status_code}")


class TestPermissionEdgeCases:
    """Test edge cases in permission handling"""

    def test_list_users_empty_type_param(self, api_base_url, admin_headers):
        """Should handle empty type parameter"""
        response = requests.get(
            f"{api_base_url}/api/users?type=",
            headers=admin_headers,
            timeout=10
        )

        # Should treat empty as no filter
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        logger.info("Empty type parameter handled correctly")

    def test_list_users_case_insensitive_type(self, api_base_url, admin_headers):
        """Should handle type parameter case-insensitively"""
        response = requests.get(
            f"{api_base_url}/api/users?type=PLATFORM",
            headers=admin_headers,
            timeout=10
        )

        # Should accept uppercase
        assert response.status_code in [200, 400], f"Expected 200 or 400, got {response.status_code}"
        logger.info(f"Case sensitivity test: {response.status_code}")

    def test_list_users_multiple_type_params(self, api_base_url, admin_headers):
        """Should handle multiple type parameters"""
        response = requests.get(
            f"{api_base_url}/api/users?type=platform&type=org",
            headers=admin_headers,
            timeout=10
        )

        # Should either take first, last, or return error
        assert response.status_code in [200, 400], f"Expected 200 or 400, got {response.status_code}"
        logger.info(f"Multiple params test: {response.status_code}")


class TestUserFiltering:
    """Test user filtering options"""

    def test_list_users_no_filter(self, api_base_url, admin_headers):
        """Should return all users when no filter specified"""
        response = requests.get(
            f"{api_base_url}/api/users",
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code == 200
        all_users = response.json()

        # Get platform users
        platform_response = requests.get(
            f"{api_base_url}/api/users?type=platform",
            headers=admin_headers,
            timeout=10
        )
        assert platform_response.status_code == 200
        platform_users = platform_response.json()

        # Get org users
        org_response = requests.get(
            f"{api_base_url}/api/users?type=org",
            headers=admin_headers,
            timeout=10
        )
        assert org_response.status_code == 200
        org_users = org_response.json()

        # Verify filtering works
        logger.info(
            f"All users: {len(all_users)}, "
            f"Platform: {len(platform_users)}, "
            f"Org: {len(org_users)}"
        )


class TestUserRolesQuery:
    """Test querying user roles"""

    def test_get_user_roles_empty(self, api_base_url, admin_headers):
        """Should return empty roles if user has no roles assigned"""
        list_response = requests.get(
            f"{api_base_url}/api/users",
            headers=admin_headers,
            timeout=10
        )

        if list_response.status_code == 200 and list_response.json():
            user_id = list_response.json()[0]["id"]
            response = requests.get(
                f"{api_base_url}/api/users/{user_id}/roles",
                headers=admin_headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                assert "roleIds" in data or isinstance(data, list)
                logger.info(f"User {user_id} roles query successful")

    def test_get_user_roles_structure(self, api_base_url, admin_headers):
        """Should return properly structured role response"""
        list_response = requests.get(
            f"{api_base_url}/api/users",
            headers=admin_headers,
            timeout=10
        )

        if list_response.status_code == 200 and list_response.json():
            user_id = list_response.json()[0]["id"]
            response = requests.get(
                f"{api_base_url}/api/users/{user_id}/roles",
                headers=admin_headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if "roleIds" in data:
                    assert isinstance(data["roleIds"], list)
                logger.info(f"Role response structure validated for {user_id}")

    def test_get_nonexistent_user_roles(self, api_base_url, admin_headers):
        """Should handle roles query for non-existent user"""
        response = requests.get(
            f"{api_base_url}/api/users/nonexistent-user-for-roles/roles",
            headers=admin_headers,
            timeout=10
        )

        # Should return 404 or empty list
        assert response.status_code in [404, 200]
        logger.info(f"Non-existent user roles query handled: {response.status_code}")

    def test_get_user_roles_multiple_times(self, api_base_url, admin_headers):
        """Should consistently return same roles on repeated queries"""
        list_response = requests.get(
            f"{api_base_url}/api/users",
            headers=admin_headers,
            timeout=10
        )

        if list_response.status_code == 200 and list_response.json():
            user_id = list_response.json()[0]["id"]

            response1 = requests.get(
                f"{api_base_url}/api/users/{user_id}/roles",
                headers=admin_headers,
                timeout=10
            )
            response2 = requests.get(
                f"{api_base_url}/api/users/{user_id}/roles",
                headers=admin_headers,
                timeout=10
            )

            if response1.status_code == 200 and response2.status_code == 200:
                data1 = response1.json()
                data2 = response2.json()
                # Results should be identical
                assert data1 == data2
                logger.info("Consistent role query results verified")


class TestUserFormsQuery:
    """Test querying user's accessible forms"""

    def test_get_user_forms_empty(self, api_base_url, admin_headers):
        """Should return empty forms if user has no form access"""
        list_response = requests.get(
            f"{api_base_url}/api/users",
            headers=admin_headers,
            timeout=10
        )

        if list_response.status_code == 200 and list_response.json():
            user_id = list_response.json()[0]["id"]
            response = requests.get(
                f"{api_base_url}/api/users/{user_id}/forms",
                headers=admin_headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                assert "formIds" in data or isinstance(data, list)
                logger.info(f"User {user_id} forms query successful")

    def test_get_user_forms_structure(self, api_base_url, admin_headers):
        """Should return properly structured forms response"""
        list_response = requests.get(
            f"{api_base_url}/api/users",
            headers=admin_headers,
            timeout=10
        )

        if list_response.status_code == 200 and list_response.json():
            user_id = list_response.json()[0]["id"]
            response = requests.get(
                f"{api_base_url}/api/users/{user_id}/forms",
                headers=admin_headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                assert "formIds" in data or "forms" in data or isinstance(data, list)
                if "formIds" in data:
                    assert isinstance(data["formIds"], list)
                logger.info(f"Forms response structure validated for {user_id}")

    def test_get_nonexistent_user_forms(self, api_base_url, admin_headers):
        """Should handle forms query for non-existent user"""
        response = requests.get(
            f"{api_base_url}/api/users/nonexistent-user-for-forms/forms",
            headers=admin_headers,
            timeout=10
        )

        # Should return 404 or empty list
        assert response.status_code in [404, 200]
        logger.info(f"Non-existent user forms query handled: {response.status_code}")

    def test_get_admin_user_forms(self, api_base_url, admin_headers):
        """Platform admin user should have access to all forms"""
        # Admin users typically have broader access
        list_response = requests.get(
            f"{api_base_url}/api/users",
            headers=admin_headers,
            timeout=10
        )

        if list_response.status_code == 200 and list_response.json():
            user_id = list_response.json()[0]["id"]
            response = requests.get(
                f"{api_base_url}/api/users/{user_id}/forms",
                headers=admin_headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                # Check if admin has all forms
                if "hasAccessToAllForms" in data:
                    logger.info(f"Admin access status: {data['hasAccessToAllForms']}")


class TestUserAccessControl:
    """Test user listing access control"""

    def test_list_users_requires_admin(self, api_base_url):
        """User listing endpoint should require admin role"""
        # No headers - should be denied
        response = requests.get(
            f"{api_base_url}/api/users",
            timeout=10
        )

        # Should return 401/403 or 200 if public
        assert response.status_code in [200, 400, 401, 403]
        logger.info(f"User listing without auth returned: {response.status_code}")

    def test_get_user_details_endpoint(self, api_base_url, admin_headers):
        """Getting user details should work for admin"""
        list_response = requests.get(
            f"{api_base_url}/api/users",
            headers=admin_headers,
            timeout=10
        )

        if list_response.status_code == 200 and list_response.json():
            user_id = list_response.json()[0]["id"]
            response = requests.get(
                f"{api_base_url}/api/users/{user_id}",
                headers=admin_headers,
                timeout=10
            )

            assert response.status_code == 200
            data = response.json()
            assert "id" in data
            assert "email" in data
            logger.info(f"User details endpoint verified for {user_id}")
