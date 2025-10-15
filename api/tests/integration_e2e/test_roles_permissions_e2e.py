"""
End-to-end tests for Roles and Permissions API
Tests role-based form access control
"""

import pytest
import requests


class TestRolesE2E:
    """Test Roles API endpoints"""

    def test_list_roles_as_platform_admin(self, base_url, platform_admin_headers):
        """Platform admin can list roles"""
        response = requests.get(
            f"{base_url}/roles",
            headers=platform_admin_headers
        )

        assert response.status_code == 200
        roles = response.json()
        assert isinstance(roles, list)

        # Should include seed data roles
        if len(roles) > 0:
            role = roles[0]
            assert "id" in role
            assert "name" in role
            # Role structure may vary

    def test_create_role_as_platform_admin(self, base_url, platform_admin_headers):
        """Platform admin can create roles"""
        response = requests.post(
            f"{base_url}/roles",
            headers=platform_admin_headers,
            json={
                "name": "E2E Test Role",
                "description": "Role for E2E testing",
                "isActive": True
            }
        )

        # May return 201 (created) or 200 (updated from previous run)
        assert response.status_code in [200, 201]
        role = response.json()
        assert role["name"] == "E2E Test Role"
        assert role["description"] == "Role for E2E testing"
        assert "id" in role

    def test_update_role(self, base_url, platform_admin_headers):
        """Platform admin can update roles"""
        # First create a role to update
        create_response = requests.post(
            f"{base_url}/roles",
            headers=platform_admin_headers,
            json={
                "name": "E2E Update Test Role",
                "description": "Original description",
                "isActive": True
            }
        )
        assert create_response.status_code in [200, 201]
        role_id = create_response.json()["id"]

        # Update it
        update_response = requests.put(
            f"{base_url}/roles/{role_id}",
            headers=platform_admin_headers,
            json={
                "description": "Updated description for E2E test"
            }
        )

        assert update_response.status_code == 200
        updated_role = update_response.json()
        assert updated_role["description"] == "Updated description for E2E test"
        assert updated_role["id"] == role_id

    def test_delete_role(self, base_url, platform_admin_headers):
        """Platform admin can soft-delete roles"""
        # First create a role to delete
        create_response = requests.post(
            f"{base_url}/roles",
            headers=platform_admin_headers,
            json={
                "name": "E2E Delete Test Role",
                "isActive": True
            }
        )
        assert create_response.status_code in [200, 201]
        role_id = create_response.json()["id"]

        # Delete it
        delete_response = requests.delete(
            f"{base_url}/roles/{role_id}",
            headers=platform_admin_headers
        )

        assert delete_response.status_code == 204

    def test_create_role_org_user_forbidden(self, base_url, org_user_headers):
        """Org users cannot create roles (platform admin only)"""
        response = requests.post(
            f"{base_url}/roles",
            headers=org_user_headers,
            json={
                "name": "Should Fail",
                "isActive": True
            }
        )

        assert response.status_code == 403


class TestRoleFormAccessE2E:
    """Test role-based form access control"""

    def test_assign_form_to_role(self, base_url, platform_admin_headers):
        """Platform admin can assign forms to roles"""
        # First create a role
        role_response = requests.post(
            f"{base_url}/roles",
            headers=platform_admin_headers,
            json={
                "name": "E2E Form Access Role",
                "description": "Role for testing form access",
                "isActive": True
            }
        )
        assert role_response.status_code in [200, 201]
        role_id = role_response.json()["id"]

        # Create a form to assign
        form_response = requests.post(
            f"{base_url}/forms",
            headers=platform_admin_headers,
            json={
                "name": "E2E Access Test Form",
                "linkedWorkflow": "test_workflow",
                "formSchema": {"fields": []},
                "isGlobal": False,
                "isPublic": False
            }
        )
        assert form_response.status_code == 201
        form_id = form_response.json()["id"]

        # Assign form to role
        assign_response = requests.post(
            f"{base_url}/roles/{role_id}/forms",
            headers=platform_admin_headers,
            json={
                "formId": form_id
            }
        )

        assert assign_response.status_code in [200, 201]

        # Verify the assignment by listing forms for the role
        list_response = requests.get(
            f"{base_url}/roles/{role_id}/forms",
            headers=platform_admin_headers
        )

        assert list_response.status_code == 200
        forms = list_response.json()
        form_ids = [f.get("id") or f.get("formId") for f in forms]
        assert form_id in form_ids

    def test_remove_form_from_role(self, base_url, platform_admin_headers):
        """Platform admin can remove forms from roles"""
        # Create role
        role_response = requests.post(
            f"{base_url}/roles",
            headers=platform_admin_headers,
            json={
                "name": "E2E Remove Form Role",
                "isActive": True
            }
        )
        assert role_response.status_code in [200, 201]
        role_id = role_response.json()["id"]

        # Create form
        form_response = requests.post(
            f"{base_url}/forms",
            headers=platform_admin_headers,
            json={
                "name": "E2E Remove Form Test",
                "linkedWorkflow": "test",
                "formSchema": {"fields": []},
                "isGlobal": False,
                "isPublic": False
            }
        )
        assert form_response.status_code == 201
        form_id = form_response.json()["id"]

        # Assign form to role
        requests.post(
            f"{base_url}/roles/{role_id}/forms",
            headers=platform_admin_headers,
            json={"formId": form_id}
        )

        # Remove form from role
        remove_response = requests.delete(
            f"{base_url}/roles/{role_id}/forms/{form_id}",
            headers=platform_admin_headers
        )

        assert remove_response.status_code == 204

        # Verify removal
        list_response = requests.get(
            f"{base_url}/roles/{role_id}/forms",
            headers=platform_admin_headers
        )
        forms = list_response.json()
        form_ids = [f.get("id") or f.get("formId") for f in forms]
        assert form_id not in form_ids

    def test_list_forms_for_role(self, base_url, platform_admin_headers):
        """Platform admin can list forms assigned to a role"""
        # Create role
        role_response = requests.post(
            f"{base_url}/roles",
            headers=platform_admin_headers,
            json={
                "name": "E2E List Forms Role",
                "isActive": True
            }
        )
        assert role_response.status_code in [200, 201]
        role_id = role_response.json()["id"]

        # List forms (may be empty if no forms assigned yet)
        response = requests.get(
            f"{base_url}/roles/{role_id}/forms",
            headers=platform_admin_headers
        )

        assert response.status_code == 200
        forms = response.json()
        assert isinstance(forms, list)


class TestRoleUserAssignmentE2E:
    """Test role-user assignment for form access control"""

    def test_assign_user_to_role(self, base_url, platform_admin_headers):
        """Platform admin can assign users to roles"""
        # Create role
        role_response = requests.post(
            f"{base_url}/roles",
            headers=platform_admin_headers,
            json={
                "name": "E2E User Assignment Role",
                "isActive": True
            }
        )
        assert role_response.status_code in [200, 201]
        role_id = role_response.json()["id"]

        # Assign user to role (using test user)
        assign_response = requests.post(
            f"{base_url}/roles/{role_id}/users",
            headers=platform_admin_headers,
            json={
                "userId": "jack@gocovi.dev"
            }
        )

        # May return 200 (OK) or 201 (created)
        assert assign_response.status_code in [200, 201]

        # Verify assignment by listing users for role
        list_response = requests.get(
            f"{base_url}/roles/{role_id}/users",
            headers=platform_admin_headers
        )

        assert list_response.status_code == 200
        users = list_response.json()
        user_ids = [u.get("userId") or u.get("id") for u in users]
        assert "jack@gocovi.dev" in user_ids

    def test_remove_user_from_role(self, base_url, platform_admin_headers):
        """Platform admin can remove users from roles"""
        # Create role
        role_response = requests.post(
            f"{base_url}/roles",
            headers=platform_admin_headers,
            json={
                "name": "E2E Remove User Role",
                "isActive": True
            }
        )
        assert role_response.status_code in [200, 201]
        role_id = role_response.json()["id"]

        # Assign user
        requests.post(
            f"{base_url}/roles/{role_id}/users",
            headers=platform_admin_headers,
            json={"userId": "test-user@example.com"}
        )

        # Remove user from role
        remove_response = requests.delete(
            f"{base_url}/roles/{role_id}/users/test-user@example.com",
            headers=platform_admin_headers
        )

        assert remove_response.status_code == 204

    def test_list_users_for_role(self, base_url, platform_admin_headers):
        """Platform admin can list users assigned to a role"""
        # Create role
        role_response = requests.post(
            f"{base_url}/roles",
            headers=platform_admin_headers,
            json={
                "name": "E2E List Users Role",
                "isActive": True
            }
        )
        assert role_response.status_code in [200, 201]
        role_id = role_response.json()["id"]

        # List users (may be empty if no users assigned yet)
        response = requests.get(
            f"{base_url}/roles/{role_id}/users",
            headers=platform_admin_headers
        )

        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)


class TestPermissionsE2E:
    """Test Permissions API endpoints"""

    def test_create_permission(self, base_url, platform_admin_headers):
        """Platform admin can create permissions"""
        # Create a role first
        role_response = requests.post(
            f"{base_url}/roles",
            headers=platform_admin_headers,
            json={
                "name": "E2E Permission Test Role",
                "isActive": True
            }
        )
        assert role_response.status_code in [200, 201]
        role_id = role_response.json()["id"]

        # Create permission
        response = requests.post(
            f"{base_url}/permissions",
            headers=platform_admin_headers,
            json={
                "roleId": role_id,
                "resource": "forms",
                "action": "view"
            }
        )

        # May return 200 (OK) or 201 (created)
        assert response.status_code in [200, 201]

    def test_delete_permission(self, base_url, platform_admin_headers):
        """Platform admin can delete permissions"""
        # Create role
        role_response = requests.post(
            f"{base_url}/roles",
            headers=platform_admin_headers,
            json={
                "name": "E2E Delete Permission Role",
                "isActive": True
            }
        )
        assert role_response.status_code in [200, 201]
        role_id = role_response.json()["id"]

        # Create permission
        requests.post(
            f"{base_url}/permissions",
            headers=platform_admin_headers,
            json={
                "roleId": role_id,
                "resource": "forms",
                "action": "submit"
            }
        )

        # Delete permission
        delete_response = requests.delete(
            f"{base_url}/permissions",
            headers=platform_admin_headers,
            params={
                "roleId": role_id,
                "resource": "forms",
                "action": "submit"
            }
        )

        assert delete_response.status_code == 204

    def test_get_user_roles(self, base_url, platform_admin_headers):
        """Platform admin can get roles for a user"""
        response = requests.get(
            f"{base_url}/users/jack@gocovi.dev/roles",
            headers=platform_admin_headers
        )

        assert response.status_code == 200
        roles = response.json()
        assert isinstance(roles, list)

    def test_permissions_org_user_forbidden(self, base_url, org_user_headers):
        """Org users cannot manage permissions (platform admin only)"""
        response = requests.post(
            f"{base_url}/permissions",
            headers=org_user_headers,
            json={
                "roleId": "test-role",
                "resource": "forms",
                "action": "view"
            }
        )

        assert response.status_code == 403
