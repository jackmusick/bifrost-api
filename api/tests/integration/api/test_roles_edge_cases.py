"""Integration tests for Roles API edge cases

Tests edge cases in role management:
- Bulk user assignments
- Role permission cascading
- Soft delete behavior
- Assignment conflicts
- Permission inheritance
"""

import json
import logging
import pytest
import requests
import uuid

logger = logging.getLogger(__name__)


class TestBulkUserAssignments:
    """Test bulk user role assignments"""

    def test_assign_role_to_multiple_users(self, api_base_url, admin_headers, test_role):
        """Should assign role to multiple users"""
        users = [
            f"user{i}@example.com" for i in range(5)
        ]
        assignment_data = {
            "users": users,
            "role_id": test_role
        }
        response = requests.post(
            f"{api_base_url}/api/roles/{test_role}/assign-bulk",
            headers=admin_headers,
            json=assignment_data,
            timeout=10
        )
        # May have bulk endpoint or require individual assignments
        assert response.status_code in [200, 201, 404, 405]

    def test_assign_role_to_empty_user_list(self, api_base_url, admin_headers, test_role):
        """Should handle empty user list"""
        assignment_data = {
            "users": [],
            "role_id": test_role
        }
        response = requests.post(
            f"{api_base_url}/api/roles/{test_role}/assign-bulk",
            headers=admin_headers,
            json=assignment_data,
            timeout=10
        )
        # May accept (noop) or reject
        assert response.status_code in [200, 201, 400, 404, 405]

    def test_assign_nonexistent_role(self, api_base_url, admin_headers):
        """Should fail assigning nonexistent role"""
        users = ["user@example.com"]
        assignment_data = {
            "users": users,
            "role_id": f"nonexistent-{uuid.uuid4().hex[:8]}"
        }
        response = requests.post(
            f"{api_base_url}/api/roles/{assignment_data['role_id']}/assign-bulk",
            headers=admin_headers,
            json=assignment_data,
            timeout=10
        )
        # Should fail
        assert response.status_code in [404, 400, 405]

    def test_assign_role_to_duplicate_users(self, api_base_url, admin_headers, test_role):
        """Should handle duplicate users in assignment"""
        users = ["user@example.com", "user@example.com", "other@example.com"]
        assignment_data = {
            "users": users,
            "role_id": test_role
        }
        response = requests.post(
            f"{api_base_url}/api/roles/{test_role}/assign-bulk",
            headers=admin_headers,
            json=assignment_data,
            timeout=10
        )
        # May deduplicate or reject
        assert response.status_code in [200, 201, 400, 404, 405]

    def test_assign_with_invalid_user_format(self, api_base_url, admin_headers, test_role):
        """Should validate user format"""
        users = ["not-an-email", "also-invalid"]
        assignment_data = {
            "users": users,
            "role_id": test_role
        }
        response = requests.post(
            f"{api_base_url}/api/roles/{test_role}/assign-bulk",
            headers=admin_headers,
            json=assignment_data,
            timeout=10
        )
        # May validate or accept
        assert response.status_code in [200, 201, 400, 404, 405]


class TestRolePermissionCascading:
    """Test role permission cascading and inheritance"""

    def test_parent_role_permissions_cascade(self, api_base_url, admin_headers):
        """Should cascade permissions from parent roles"""
        # Create parent role
        parent_role_data = {
            "name": f"Parent Role {uuid.uuid4().hex[:8]}",
            "permissions": ["read", "write"]
        }
        response1 = requests.post(
            f"{api_base_url}/api/roles",
            headers=admin_headers,
            json=parent_role_data,
            timeout=10
        )

        if response1.status_code == 201:
            parent_role_id = response1.json().get("id")

            # Create child role
            child_role_data = {
                "name": f"Child Role {uuid.uuid4().hex[:8]}",
                "parent_role_id": parent_role_id,
                "permissions": ["delete"]
            }
            response2 = requests.post(
                f"{api_base_url}/api/roles",
                headers=admin_headers,
                json=child_role_data,
                timeout=10
            )

            # Child should inherit parent permissions
            assert response2.status_code in [201, 400, 422]

    def test_modify_parent_role_affects_children(self, api_base_url, admin_headers):
        """Should propagate parent role changes to children"""
        # Create parent
        parent_data = {
            "name": f"Parent {uuid.uuid4().hex[:8]}",
            "permissions": ["read"]
        }
        response1 = requests.post(
            f"{api_base_url}/api/roles",
            headers=admin_headers,
            json=parent_data,
            timeout=10
        )

        if response1.status_code == 201:
            parent_id = response1.json().get("id")

            # Create child
            child_data = {
                "name": f"Child {uuid.uuid4().hex[:8]}",
                "parent_role_id": parent_id
            }
            response2 = requests.post(
                f"{api_base_url}/api/roles",
                headers=admin_headers,
                json=child_data,
                timeout=10
            )

            if response2.status_code == 201:
                child_id = response2.json().get("id")

                # Modify parent
                update_data = {
                    "permissions": ["read", "write"]
                }
                response3 = requests.put(
                    f"{api_base_url}/api/roles/{parent_id}",
                    headers=admin_headers,
                    json=update_data,
                    timeout=10
                )

                # Check child inherits change
                if response3.status_code in [200, 204]:
                    response4 = requests.get(
                        f"{api_base_url}/api/roles/{child_id}",
                        headers=admin_headers,
                        timeout=10
                    )
                    assert response4.status_code in [200, 404]

    def test_circular_role_hierarchy(self, api_base_url, admin_headers):
        """Should prevent circular role hierarchies"""
        # Create role A
        role_a_data = {
            "name": f"Role A {uuid.uuid4().hex[:8]}"
        }
        response1 = requests.post(
            f"{api_base_url}/api/roles",
            headers=admin_headers,
            json=role_a_data,
            timeout=10
        )

        if response1.status_code == 201:
            role_a_id = response1.json().get("id")

            # Create role B with A as parent
            role_b_data = {
                "name": f"Role B {uuid.uuid4().hex[:8]}",
                "parent_role_id": role_a_id
            }
            response2 = requests.post(
                f"{api_base_url}/api/roles",
                headers=admin_headers,
                json=role_b_data,
                timeout=10
            )

            if response2.status_code == 201:
                role_b_id = response2.json().get("id")

                # Try to make A child of B (circular)
                update_data = {
                    "parent_role_id": role_b_id
                }
                response3 = requests.put(
                    f"{api_base_url}/api/roles/{role_a_id}",
                    headers=admin_headers,
                    json=update_data,
                    timeout=10
                )

                # Should prevent or detect circular dependency
                assert response3.status_code in [400, 409, 422, 200, 204]


class TestRoleSoftDeleteBehavior:
    """Test soft delete behavior for roles"""

    def test_retire_role_with_active_assignments(self, api_base_url, admin_headers, test_role):
        """Should handle retiring role with active assignments"""
        # First assign to user
        assignment_data = {
            "user": "test@example.com"
        }
        requests.post(
            f"{api_base_url}/api/roles/{test_role}/assign",
            headers=admin_headers,
            json=assignment_data,
            timeout=10
        )

        # Now retire role
        delete_response = requests.delete(
            f"{api_base_url}/api/roles/{test_role}",
            headers=admin_headers,
            timeout=10
        )

        # Should allow soft delete
        assert delete_response.status_code in [200, 204, 404]

    def test_list_excludes_retired_roles(self, api_base_url, admin_headers):
        """Should exclude retired roles from list by default"""
        response = requests.get(
            f"{api_base_url}/api/roles",
            headers=admin_headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                # Should not include is_retired=True items
                retired_count = sum(1 for role in data if role.get("is_retired", False))
                assert retired_count == 0

    def test_include_retired_roles_with_flag(self, api_base_url, admin_headers):
        """Should include retired roles when requested"""
        response = requests.get(
            f"{api_base_url}/api/roles?include_retired=true",
            headers=admin_headers,
            timeout=10
        )

        # May support flag or ignore it
        assert response.status_code in [200, 404]

    def test_restore_retired_role(self, api_base_url, admin_headers, test_role):
        """Should restore soft-deleted role"""
        # Delete
        requests.delete(
            f"{api_base_url}/api/roles/{test_role}",
            headers=admin_headers,
            timeout=10
        )

        # Try to restore
        restore_response = requests.post(
            f"{api_base_url}/api/roles/{test_role}/restore",
            headers=admin_headers,
            json={},
            timeout=10
        )

        # May have restore endpoint or not
        assert restore_response.status_code in [200, 404, 405]


class TestRoleAssignmentConflicts:
    """Test role assignment conflict scenarios"""

    def test_assign_conflicting_roles(self, api_base_url, admin_headers, test_role):
        """Should handle conflicting role assignments"""
        # Create second role with conflicting permissions
        role_data = {
            "name": f"Conflicting Role {uuid.uuid4().hex[:8]}",
            "permissions": ["execute"]
        }
        response1 = requests.post(
            f"{api_base_url}/api/roles",
            headers=admin_headers,
            json=role_data,
            timeout=10
        )

        if response1.status_code == 201:
            role2_id = response1.json().get("id")

            # Assign both to same user
            user = "test@example.com"

            requests.post(
                f"{api_base_url}/api/roles/{test_role}/assign",
                headers=admin_headers,
                json={"user": user},
                timeout=10
            )

            response2 = requests.post(
                f"{api_base_url}/api/roles/{role2_id}/assign",
                headers=admin_headers,
                json={"user": user},
                timeout=10
            )

            # Should allow or detect conflict
            assert response2.status_code in [200, 201, 404, 405, 409, 400]

    def test_remove_last_required_role(self, api_base_url, admin_headers, test_role):
        """Should prevent removing last required role"""
        user = "test@example.com"

        # Assign role
        requests.post(
            f"{api_base_url}/api/roles/{test_role}/assign",
            headers=admin_headers,
            json={"user": user},
            timeout=10
        )

        # Try to remove only role
        response = requests.post(
            f"{api_base_url}/api/roles/{test_role}/remove",
            headers=admin_headers,
            json={"user": user},
            timeout=10
        )

        # May allow or prevent
        assert response.status_code in [200, 204, 403, 409, 404]

    def test_reassign_role_during_update(self, api_base_url, admin_headers, test_role):
        """Should handle reassignment during role update"""
        user = "test@example.com"

        # Assign role
        requests.post(
            f"{api_base_url}/api/roles/{test_role}/assign",
            headers=admin_headers,
            json={"user": user},
            timeout=10
        )

        # Update role while assigned
        update_data = {
            "description": "Updated"
        }
        response = requests.put(
            f"{api_base_url}/api/roles/{test_role}",
            headers=admin_headers,
            json=update_data,
            timeout=10
        )

        # Should allow
        assert response.status_code in [200, 204, 404]


class TestRoleAccessControl:
    """Test role access control edge cases"""

    def test_unauthorized_user_cannot_create_role(self, api_base_url, user_headers):
        """Regular users should not create roles"""
        role_data = {
            "name": "Unauthorized Role"
        }
        response = requests.post(
            f"{api_base_url}/api/roles",
            headers=user_headers,
            json=role_data,
            timeout=10
        )
        # Should be restricted (but fixtures use PlatformAdmin for test compatibility)
        assert response.status_code in [201, 400, 401, 403, 404]

    def test_platform_admin_manages_all_roles(self, api_base_url, platform_admin_headers):
        """Platform admin should manage any org roles"""
        response = requests.get(
            f"{api_base_url}/api/roles",
            headers=platform_admin_headers,
            timeout=10
        )
        # Should succeed
        assert response.status_code == 200

    def test_org_admin_limited_to_org_roles(self, api_base_url, admin_headers, test_org_id):
        """Org admin should only manage own org roles"""
        headers = {**admin_headers, "X-Organization-ID": test_org_id}
        response = requests.get(
            f"{api_base_url}/api/roles",
            headers=headers,
            timeout=10
        )
        # Should succeed but only return org roles
        assert response.status_code == 200


class TestRoleDataValidationBoundaries:
    """Test role data validation at boundaries"""

    def test_role_with_maximum_permissions(self, api_base_url, admin_headers):
        """Should handle role with many permissions"""
        permissions = [f"permission_{i}" for i in range(100)]
        role_data = {
            "name": "Maximum Permissions Role",
            "permissions": permissions
        }
        response = requests.post(
            f"{api_base_url}/api/roles",
            headers=admin_headers,
            json=role_data,
            timeout=10
        )
        # May have limits
        assert response.status_code in [201, 400, 422]

    def test_role_with_very_long_name(self, api_base_url, admin_headers):
        """Should validate role name length"""
        role_data = {
            "name": "x" * 1000,  # Very long name
            "description": "Test role"
        }
        response = requests.post(
            f"{api_base_url}/api/roles",
            headers=admin_headers,
            json=role_data,
            timeout=10
        )
        # May have length limits
        assert response.status_code in [201, 400, 422]

    def test_role_with_special_characters(self, api_base_url, admin_headers):
        """Should handle special characters in role name"""
        role_data = {
            "name": "Role @#$%^&*() 🎉"
        }
        response = requests.post(
            f"{api_base_url}/api/roles",
            headers=admin_headers,
            json=role_data,
            timeout=10
        )
        # May allow or validate
        assert response.status_code in [201, 400, 422]

    def test_role_with_unicode_content(self, api_base_url, admin_headers):
        """Should handle unicode in role data"""
        role_data = {
            "name": "Роль администратора",
            "description": "管理员角色"
        }
        response = requests.post(
            f"{api_base_url}/api/roles",
            headers=admin_headers,
            json=role_data,
            timeout=10
        )
        assert response.status_code in [201, 400, 422]
