"""
Integration tests for Roles and Permissions API
Tests role-based form access control by calling Azure Functions directly (no HTTP)
"""

import pytest

from functions.forms import create_form
from functions.permissions import get_user_roles
from functions.roles import (
    assign_forms_to_role,
    assign_users_to_role,
    create_role,
    delete_role,
    get_role_forms,
    get_role_users,
    list_roles,
    remove_form_from_role,
    remove_user_from_role,
    update_role,
)
from tests.helpers.http_helpers import (
    create_mock_request,
    create_org_user_headers,
    create_platform_admin_headers,
    parse_response,
)


class TestRolesIntegration:
    """Test Roles API endpoints"""

    @pytest.mark.asyncio
    async def test_list_roles_as_platform_admin(self):
        """Platform admin can list roles"""
        req = create_mock_request(
            method="GET",
            url="/api/roles",
            headers=create_platform_admin_headers(),
        )

        response = await list_roles(req)
        status, body = parse_response(response)

        assert status == 200
        roles = body
        assert isinstance(roles, list)

        # Should include seed data roles
        if len(roles) > 0:
            role = roles[0]
            assert "id" in role
            assert "name" in role
            # Role structure may vary

    @pytest.mark.asyncio
    async def test_create_role_as_platform_admin(self):
        """Platform admin can create roles"""
        req = create_mock_request(
            method="POST",
            url="/api/roles",
            headers=create_platform_admin_headers(),
            body={
                "name": "Integration Test Role",
                "description": "Role for integration testing",
                "isActive": True
            }
        )

        response = await create_role(req)
        status, body = parse_response(response)

        # Should return 201 (created)
        assert status == 201
        assert body["name"] == "Integration Test Role"
        assert body["description"] == "Role for integration testing"
        assert "id" in body

    @pytest.mark.asyncio
    async def test_update_role(self):
        """Platform admin can update roles"""
        # First create a role to update
        create_req = create_mock_request(
            method="POST",
            url="/api/roles",
            headers=create_platform_admin_headers(),
            body={
                "name": "Integration Update Test Role",
                "description": "Original description",
                "isActive": True
            }
        )
        create_response = await create_role(create_req)
        create_status, create_body = parse_response(create_response)
        assert create_status == 201
        role_id = create_body["id"]

        # Update it
        update_req = create_mock_request(
            method="PUT",
            url=f"/api/roles/{role_id}",
            headers=create_platform_admin_headers(),
            route_params={"roleId": role_id},
            body={
                "description": "Updated description for integration test"
            }
        )

        response = await update_role(update_req)
        status, body = parse_response(response)

        assert status == 200
        assert body["description"] == "Updated description for integration test"
        assert body["id"] == role_id

    @pytest.mark.asyncio
    async def test_delete_role(self):
        """Platform admin can soft-delete roles"""
        # First create a role to delete
        create_req = create_mock_request(
            method="POST",
            url="/api/roles",
            headers=create_platform_admin_headers(),
            body={
                "name": "Integration Delete Test Role",
                "isActive": True
            }
        )
        create_response = await create_role(create_req)
        create_status, create_body = parse_response(create_response)
        assert create_status == 201
        role_id = create_body["id"]

        # Delete it
        delete_req = create_mock_request(
            method="DELETE",
            url=f"/api/roles/{role_id}",
            headers=create_platform_admin_headers(),
            route_params={"roleId": role_id}
        )

        response = await delete_role(delete_req)
        status, _ = parse_response(response)

        assert status == 204

    @pytest.mark.asyncio
    async def test_create_role_org_user_forbidden(self):
        """Org users cannot create roles (platform admin only)"""
        req = create_mock_request(
            method="POST",
            url="/api/roles",
            headers=create_org_user_headers(),
            body={
                "name": "Should Fail",
                "isActive": True
            }
        )

        response = await create_role(req)
        status, _ = parse_response(response)

        assert status == 403


class TestRoleFormAccessIntegration:
    """Test role-based form access control"""

    @pytest.mark.asyncio
    async def test_assign_form_to_role(self):
        """Platform admin can assign forms to roles"""
        # First create a role
        role_req = create_mock_request(
            method="POST",
            url="/api/roles",
            headers=create_platform_admin_headers(),
            body={
                "name": "Integration Form Access Role",
                "description": "Role for testing form access",
                "isActive": True
            }
        )
        role_response = await create_role(role_req)
        role_status, role_body = parse_response(role_response)
        assert role_status == 201
        role_id = role_body["id"]

        # Create a form to assign
        form_req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(),
            body={
                "name": "Integration Access Test Form",
                "linkedWorkflow": "test_workflow",
                "formSchema": {"fields": []},
                "isGlobal": False,
                "isPublic": False
            }
        )
        form_response = await create_form(form_req)
        form_status, form_body = parse_response(form_response)
        assert form_status == 201
        form_id = form_body["id"]

        # Assign form to role
        assign_req = create_mock_request(
            method="POST",
            url=f"/api/roles/{role_id}/forms",
            headers=create_platform_admin_headers(),
            route_params={"roleId": role_id},
            body={
                "formIds": [form_id]
            }
        )

        response = await assign_forms_to_role(assign_req)
        status, _ = parse_response(response)

        assert status == 200

        # Verify the assignment by listing forms for the role
        list_req = create_mock_request(
            method="GET",
            url=f"/api/roles/{role_id}/forms",
            headers=create_platform_admin_headers(),
            route_params={"roleId": role_id}
        )

        list_response = await get_role_forms(list_req)
        list_status, list_body = parse_response(list_response)

        assert list_status == 200
        assert "formIds" in list_body
        assert isinstance(list_body["formIds"], list)
        assert form_id in list_body["formIds"]

    @pytest.mark.asyncio
    async def test_remove_form_from_role(self):
        """Platform admin can remove forms from roles"""
        # Create role
        role_req = create_mock_request(
            method="POST",
            url="/api/roles",
            headers=create_platform_admin_headers(),
            body={
                "name": "Integration Remove Form Role",
                "isActive": True
            }
        )
        role_response = await create_role(role_req)
        role_status, role_body = parse_response(role_response)
        assert role_status == 201
        role_id = role_body["id"]

        # Create form
        form_req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(),
            body={
                "name": "Integration Remove Form Test",
                "linkedWorkflow": "test",
                "formSchema": {"fields": []},
                "isGlobal": False,
                "isPublic": False
            }
        )
        form_response = await create_form(form_req)
        form_status, form_body = parse_response(form_response)
        assert form_status == 201
        form_id = form_body["id"]

        # Assign form to role
        assign_req = create_mock_request(
            method="POST",
            url=f"/api/roles/{role_id}/forms",
            headers=create_platform_admin_headers(),
            route_params={"roleId": role_id},
            body={"formIds": [form_id]}
        )
        await assign_forms_to_role(assign_req)

        # Remove form from role
        remove_req = create_mock_request(
            method="DELETE",
            url=f"/api/roles/{role_id}/forms/{form_id}",
            headers=create_platform_admin_headers(),
            route_params={"roleId": role_id, "formId": form_id}
        )

        response = await remove_form_from_role(remove_req)
        status, _ = parse_response(response)

        assert status == 204

        # Verify removal
        list_req = create_mock_request(
            method="GET",
            url=f"/api/roles/{role_id}/forms",
            headers=create_platform_admin_headers(),
            route_params={"roleId": role_id}
        )
        list_response = await get_role_forms(list_req)
        _, list_body = parse_response(list_response)
        assert "formIds" in list_body
        assert isinstance(list_body["formIds"], list)
        assert form_id not in list_body["formIds"]

    @pytest.mark.asyncio
    async def test_list_forms_for_role(self):
        """Platform admin can list forms assigned to a role"""
        # Create role
        role_req = create_mock_request(
            method="POST",
            url="/api/roles",
            headers=create_platform_admin_headers(),
            body={
                "name": "Integration List Forms Role",
                "isActive": True
            }
        )
        role_response = await create_role(role_req)
        role_status, role_body = parse_response(role_response)
        assert role_status == 201
        role_id = role_body["id"]

        # List forms (may be empty if no forms assigned yet)
        req = create_mock_request(
            method="GET",
            url=f"/api/roles/{role_id}/forms",
            headers=create_platform_admin_headers(),
            route_params={"roleId": role_id}
        )

        response = await get_role_forms(req)
        status, body = parse_response(response)

        assert status == 200
        assert "formIds" in body
        assert isinstance(body["formIds"], list)


class TestRoleUserAssignmentIntegration:
    """Test role-user assignment for form access control"""

    @pytest.mark.asyncio
    async def test_assign_user_to_role(self):
        """Platform admin can assign users to roles"""
        # Create role
        role_req = create_mock_request(
            method="POST",
            url="/api/roles",
            headers=create_platform_admin_headers(),
            body={
                "name": "Integration User Assignment Role",
                "isActive": True
            }
        )
        role_response = await create_role(role_req)
        role_status, role_body = parse_response(role_response)
        assert role_status == 201
        role_id = role_body["id"]

        # Assign user to role (using test user)
        assign_req = create_mock_request(
            method="POST",
            url=f"/api/roles/{role_id}/users",
            headers=create_platform_admin_headers(),
            route_params={"roleId": role_id},
            body={
                "userIds": ["jack@gocovi.dev"]
            }
        )

        response = await assign_users_to_role(assign_req)
        status, _ = parse_response(response)

        # Should return 200 (OK)
        assert status == 200

        # Verify assignment by listing users for role
        list_req = create_mock_request(
            method="GET",
            url=f"/api/roles/{role_id}/users",
            headers=create_platform_admin_headers(),
            route_params={"roleId": role_id}
        )

        list_response = await get_role_users(list_req)
        list_status, list_body = parse_response(list_response)

        assert list_status == 200
        assert "userIds" in list_body
        assert isinstance(list_body["userIds"], list)
        assert "jack@gocovi.dev" in list_body["userIds"]

    @pytest.mark.asyncio
    async def test_remove_user_from_role(self):
        """Platform admin can remove users from roles"""
        # Create role
        role_req = create_mock_request(
            method="POST",
            url="/api/roles",
            headers=create_platform_admin_headers(),
            body={
                "name": "Integration Remove User Role",
                "isActive": True
            }
        )
        role_response = await create_role(role_req)
        role_status, role_body = parse_response(role_response)
        assert role_status == 201
        role_id = role_body["id"]

        # Assign user
        assign_req = create_mock_request(
            method="POST",
            url=f"/api/roles/{role_id}/users",
            headers=create_platform_admin_headers(),
            route_params={"roleId": role_id},
            body={"userIds": ["test-user@example.com"]}
        )
        await assign_users_to_role(assign_req)

        # Remove user from role
        remove_req = create_mock_request(
            method="DELETE",
            url=f"/api/roles/{role_id}/users/test-user@example.com",
            headers=create_platform_admin_headers(),
            route_params={"roleId": role_id, "userId": "test-user@example.com"}
        )

        response = await remove_user_from_role(remove_req)
        status, _ = parse_response(response)

        assert status == 204

    @pytest.mark.asyncio
    async def test_list_users_for_role(self):
        """Platform admin can list users assigned to a role"""
        # Create role
        role_req = create_mock_request(
            method="POST",
            url="/api/roles",
            headers=create_platform_admin_headers(),
            body={
                "name": "Integration List Users Role",
                "isActive": True
            }
        )
        role_response = await create_role(role_req)
        role_status, role_body = parse_response(role_response)
        assert role_status == 201
        role_id = role_body["id"]

        # List users (may be empty if no users assigned yet)
        req = create_mock_request(
            method="GET",
            url=f"/api/roles/{role_id}/users",
            headers=create_platform_admin_headers(),
            route_params={"roleId": role_id}
        )

        response = await get_role_users(req)
        status, body = parse_response(response)

        assert status == 200
        assert "userIds" in body
        assert isinstance(body["userIds"], list)


class TestPermissionsIntegration:
    """Test Permissions API endpoints"""

    @pytest.mark.asyncio
    async def test_create_permission(self):
        """Platform admin cannot create permissions (deprecated endpoint)"""
        # Create role first
        role_req = create_mock_request(
            method="POST",
            url="/api/roles",
            headers=create_platform_admin_headers(),
            body={
                "name": "Integration Permission Test Role",
                "isActive": True
            }
        )
        role_response = await create_role(role_req)
        role_status, role_body = parse_response(role_response)
        assert role_status == 201
        role_id = role_body["id"]

        # Try to create permission (should fail - deprecated)
        # Note: The E2E test calls POST /permissions, but there's no such endpoint in permissions.py
        # The actual endpoint is POST /permissions which calls grant_permissions
        from functions.permissions import grant_permissions

        req = create_mock_request(
            method="POST",
            url="/api/permissions",
            headers=create_platform_admin_headers(),
            body={
                "roleId": role_id,
                "resource": "forms",
                "action": "view"
            }
        )

        response = await grant_permissions(req)
        status, body = parse_response(response)

        # Should return 501 (Not Implemented) - permissions are deprecated
        assert status == 501
        assert body["error"] == "NotImplemented"

    @pytest.mark.asyncio
    async def test_delete_permission(self):
        """Platform admin cannot delete permissions (deprecated endpoint)"""
        # Create role
        role_req = create_mock_request(
            method="POST",
            url="/api/roles",
            headers=create_platform_admin_headers(),
            body={
                "name": "Integration Delete Permission Role",
                "isActive": True
            }
        )
        role_response = await create_role(role_req)
        role_status, role_body = parse_response(role_response)
        assert role_status == 201
        role_id = role_body["id"]

        # Try to delete permission (should fail - deprecated)
        from functions.permissions import revoke_permissions

        delete_req = create_mock_request(
            method="DELETE",
            url="/api/permissions",
            headers=create_platform_admin_headers(),
            query_params={
                "roleId": role_id,
                "resource": "forms",
                "action": "submit"
            }
        )

        response = await revoke_permissions(delete_req)
        status, body = parse_response(response)

        # Should return 501 (Not Implemented) - permissions are deprecated
        assert status == 501
        assert body["error"] == "NotImplemented"

    @pytest.mark.asyncio
    async def test_get_user_roles(self):
        """Platform admin can get roles for a user"""
        req = create_mock_request(
            method="GET",
            url="/api/users/jack@gocovi.dev/roles",
            headers=create_platform_admin_headers(),
            route_params={"userId": "jack@gocovi.dev"}
        )

        response = await get_user_roles(req)
        status, body = parse_response(response)

        assert status == 200
        assert "roleIds" in body
        assert isinstance(body["roleIds"], list)

    @pytest.mark.asyncio
    async def test_permissions_org_user_forbidden(self):
        """Org users cannot manage permissions (platform admin only)"""
        from functions.permissions import grant_permissions

        req = create_mock_request(
            method="POST",
            url="/api/permissions",
            headers=create_org_user_headers(),
            body={
                "roleId": "test-role",
                "resource": "forms",
                "action": "view"
            }
        )

        response = await grant_permissions(req)
        status, _ = parse_response(response)

        assert status == 403
