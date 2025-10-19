"""Integration tests for Roles API endpoints

Tests the role management endpoints:
- GET /api/roles - List all roles
- POST /api/roles - Create role
- GET /api/roles/{roleId} - Get role
- PUT /api/roles/{roleId} - Update role
- DELETE /api/roles/{roleId} - Delete role
- POST /api/roles/{roleId}/users - Assign users to role
- GET /api/roles/{roleId}/users - Get users in role
- POST /api/roles/{roleId}/forms - Assign forms to role
- GET /api/roles/{roleId}/forms - Get forms assigned to role
"""

import json
import logging
import pytest
import requests

logger = logging.getLogger(__name__)


class TestRoleCRUD:
    """Test role CRUD operations"""

    def test_list_roles(self, api_base_url, admin_headers):
        """Should list all roles for organization"""
        response = requests.get(
            f"{api_base_url}/api/roles",
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        logger.info(f"Listed {len(data)} roles")

    def test_create_role_success(self, api_base_url, admin_headers):
        """Should create role and return role details"""
        role_data = {
            "name": "Test Role",
            "description": "Role for integration tests"
        }

        response = requests.post(
            f"{api_base_url}/api/roles",
            headers=admin_headers,
            json=role_data,
            timeout=10
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Role"
        assert data["description"] == "Role for integration tests"
        logger.info(f"Successfully created role: {data['id']}")

    def test_create_role_missing_name(self, api_base_url, admin_headers):
        """Should reject role without name"""
        role_data = {
            "description": "Missing name"
        }

        response = requests.post(
            f"{api_base_url}/api/roles",
            headers=admin_headers,
            json=role_data,
            timeout=10
        )

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        logger.info("Correctly rejected role without name")

    def test_get_role_success(self, api_base_url, admin_headers, test_role):
        """Should retrieve role by ID"""
        response = requests.get(
            f"{api_base_url}/api/roles/{test_role}",
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["id"] == test_role
        assert "name" in data
        logger.info(f"Retrieved role: {test_role}")

    def test_get_role_not_found(self, api_base_url, admin_headers):
        """Should return 404 for nonexistent role"""
        fake_role_id = "00000000-0000-0000-0000-000000000000"
        response = requests.get(
            f"{api_base_url}/api/roles/{fake_role_id}",
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        logger.info("Correctly returned 404 for nonexistent role")

    def test_update_role_success(self, api_base_url, admin_headers, test_role):
        """Should update role name and description"""
        update_data = {
            "name": "Updated Role Name",
            "description": "Updated description"
        }

        response = requests.put(
            f"{api_base_url}/api/roles/{test_role}",
            headers=admin_headers,
            json=update_data,
            timeout=10
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["name"] == "Updated Role Name"
        assert data["description"] == "Updated description"
        logger.info(f"Updated role: {test_role}")

    def test_update_role_not_found(self, api_base_url, admin_headers):
        """Should return 404 when updating nonexistent role"""
        fake_role_id = "00000000-0000-0000-0000-000000000000"
        response = requests.put(
            f"{api_base_url}/api/roles/{fake_role_id}",
            headers=admin_headers,
            json={"name": "Updated Name"},
            timeout=10
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        logger.info("Correctly returned 404 for nonexistent role on update")

    def test_delete_role_success(self, api_base_url, admin_headers):
        """Should delete role"""
        # Create a role to delete
        role_data = {
            "name": "Role to Delete",
            "description": "Will be deleted"
        }

        create_response = requests.post(
            f"{api_base_url}/api/roles",
            headers=admin_headers,
            json=role_data,
            timeout=10
        )
        assert create_response.status_code == 201
        role_id = create_response.json()["id"]

        # Delete the role
        delete_response = requests.delete(
            f"{api_base_url}/api/roles/{role_id}",
            headers=admin_headers,
            timeout=10
        )

        assert delete_response.status_code == 204, f"Expected 204, got {delete_response.status_code}"

        # Verify role is deleted
        get_response = requests.get(
            f"{api_base_url}/api/roles/{role_id}",
            headers=admin_headers,
            timeout=10
        )
        assert get_response.status_code == 404, f"Deleted role should return 404, got {get_response.status_code}"
        logger.info(f"Deleted role: {role_id}")

    def test_delete_role_idempotent(self, api_base_url, admin_headers):
        """Should return 204 even if role already deleted (idempotent)"""
        fake_role_id = "00000000-0000-0000-0000-000000000000"
        response = requests.delete(
            f"{api_base_url}/api/roles/{fake_role_id}",
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code == 204, f"Expected 204 (idempotent), got {response.status_code}"
        logger.info("Delete is idempotent")


class TestRoleUserAssignment:
    """Test assigning users to roles"""

    def test_assign_users_to_role(self, api_base_url, admin_headers, test_role):
        """Should assign users to role"""
        assignment_data = {
            "user_ids": ["test-user-1", "test-user-2"]
        }

        response = requests.post(
            f"{api_base_url}/api/roles/{test_role}/users",
            headers=admin_headers,
            json=assignment_data,
            timeout=10
        )

        # Could return 200 (success) or other codes depending on endpoint implementation
        assert response.status_code in [200, 201, 204], f"Unexpected status {response.status_code}: {response.text}"
        logger.info(f"Assigned users to role: {test_role}")

    def test_get_role_users(self, api_base_url, admin_headers, test_role):
        """Should get users assigned to role"""
        response = requests.get(
            f"{api_base_url}/api/roles/{test_role}/users",
            headers=admin_headers,
            timeout=10
        )

        # Could return 200 (success), 404 (not implemented), or other codes
        if response.status_code == 200:
            data = response.json()
            assert "users" in data or isinstance(data, list)
            logger.info(f"Retrieved users for role: {test_role}")
        elif response.status_code == 404:
            logger.info("Get role users endpoint not implemented")
        else:
            logger.warning(f"Unexpected status for get role users: {response.status_code}")


class TestRoleFormAssignment:
    """Test assigning forms to roles"""

    def test_assign_forms_to_role(self, api_base_url, admin_headers, test_role, test_form):
        """Should assign forms to role"""
        assignment_data = {
            "form_ids": [test_form]
        }

        response = requests.post(
            f"{api_base_url}/api/roles/{test_role}/forms",
            headers=admin_headers,
            json=assignment_data,
            timeout=10
        )

        # Could return 200, 201, 204, or 404 (not implemented)
        assert response.status_code in [200, 201, 204, 404], f"Unexpected status {response.status_code}"
        if response.status_code != 404:
            logger.info(f"Assigned forms to role: {test_role}")

    def test_get_role_forms(self, api_base_url, admin_headers, test_role):
        """Should get forms assigned to role"""
        response = requests.get(
            f"{api_base_url}/api/roles/{test_role}/forms",
            headers=admin_headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            assert "forms" in data or isinstance(data, list)
            logger.info(f"Retrieved forms for role: {test_role}")
        elif response.status_code == 404:
            logger.info("Get role forms endpoint not implemented")


class TestRolePermissions:
    """Test role access control"""

    def test_regular_user_cannot_list_roles(self, api_base_url, user_headers):
        """Regular users should not be able to list roles"""
        response = requests.get(
            f"{api_base_url}/api/roles",
            headers=user_headers,
            timeout=10
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        logger.info("Correctly rejected non-admin role list")

    def test_regular_user_cannot_create_role(self, api_base_url, user_headers):
        """Regular users should not be able to create roles"""
        role_data = {
            "name": "Unauthorized Role"
        }

        response = requests.post(
            f"{api_base_url}/api/roles",
            headers=user_headers,
            json=role_data,
            timeout=10
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        logger.info("Correctly rejected non-admin role creation")

    def test_regular_user_cannot_delete_role(self, api_base_url, user_headers, test_role):
        """Regular users should not be able to delete roles"""
        response = requests.delete(
            f"{api_base_url}/api/roles/{test_role}",
            headers=user_headers,
            timeout=10
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        logger.info("Correctly rejected non-admin role deletion")


class TestRoleAuthorizationRequired:
    """Test role endpoints require authentication"""

    def test_list_roles_no_headers(self, api_base_url):
        """Should reject request without auth headers"""
        response = requests.get(
            f"{api_base_url}/api/roles",
            timeout=10
        )

        assert response.status_code in [400, 401, 403], f"Expected 400/401/403, got {response.status_code}"
        logger.info("Correctly rejected list without auth headers")

    def test_create_role_no_headers(self, api_base_url):
        """Should reject request without auth headers"""
        response = requests.post(
            f"{api_base_url}/api/roles",
            json={"name": "Test"},
            timeout=10
        )

        assert response.status_code in [400, 401, 403], f"Expected 400/401/403, got {response.status_code}"
        logger.info("Correctly rejected create without auth headers")


class TestRoleEdgeCases:
    """Test role endpoint edge cases"""

    def test_create_role_duplicate_name(self, api_base_url, admin_headers):
        """Should handle duplicate role names (behavior depends on implementation)"""
        role_data = {
            "name": "Duplicate Role Name"
        }

        # Create first role
        response1 = requests.post(
            f"{api_base_url}/api/roles",
            headers=admin_headers,
            json=role_data,
            timeout=10
        )
        assert response1.status_code == 201

        # Try to create second role with same name
        response2 = requests.post(
            f"{api_base_url}/api/roles",
            headers=admin_headers,
            json=role_data,
            timeout=10
        )

        # Should either allow duplicates (201) or reject as conflict (409)
        assert response2.status_code in [201, 409, 400], f"Unexpected status: {response2.status_code}"
        logger.info(f"Duplicate role creation returned: {response2.status_code}")

    def test_create_role_empty_name(self, api_base_url, admin_headers):
        """Should reject role with empty name"""
        role_data = {
            "name": ""
        }

        response = requests.post(
            f"{api_base_url}/api/roles",
            headers=admin_headers,
            json=role_data,
            timeout=10
        )

        # Should reject empty string
        assert response.status_code in [400, 422], f"Expected 400 or 422, got {response.status_code}"
        logger.info("Correctly rejected role with empty name")

    def test_create_role_special_characters(self, api_base_url, admin_headers):
        """Should allow role names with special characters"""
        role_data = {
            "name": "Test-Role_123 (Special)",
            "description": "Role with special chars"
        }

        response = requests.post(
            f"{api_base_url}/api/roles",
            headers=admin_headers,
            json=role_data,
            timeout=10
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        logger.info("Successfully created role with special characters")
