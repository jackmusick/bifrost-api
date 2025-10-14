"""
Integration tests for permission system
Tests end-to-end permission checking with real table storage
"""

import pytest
import uuid
from datetime import datetime
from shared.request_context import RequestContext
from shared.authorization import (
    can_user_view_form,
    get_user_visible_forms,
    can_user_view_execution,
    get_user_executions
)
from shared.storage import TableStorageService, get_table_service
from shared.models import generate_entity_id


@pytest.fixture(scope="function")
def clean_tables():
    """Clean all tables before each test"""
    tables = ["Config", "Entities", "Relationships", "Users"]
    for table_name in tables:
        service = TableStorageService(table_name)
        try:
            # Fix: query_entities() requires a filter parameter
            entities = list(service.query_entities(filter=""))
            for entity in entities:
                service.delete_entity(entity["PartitionKey"], entity["RowKey"])
        except Exception as e:
            # Log but continue - table might not exist yet
            pass
    yield
    # Cleanup after test as well
    for table_name in tables:
        service = TableStorageService(table_name)
        try:
            entities = list(service.query_entities(filter=""))
            for entity in entities:
                service.delete_entity(entity["PartitionKey"], entity["RowKey"])
        except:
            pass


class TestPlatformAdminScopeSwitching:
    """Test platform admin ability to switch between scopes"""

    def test_platform_admin_can_switch_to_global_scope(self, clean_tables):
        """Platform admin can view GLOBAL entities"""
        # Create GLOBAL form
        entities_service = TableStorageService("Entities")
        form_id = generate_entity_id()
        form_entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"form:{form_id}",
            "Name": "Global Form",
            "Description": "Available globally",
            "IsPublic": True,
            "CreatedAt": datetime.utcnow().isoformat()
        }
        entities_service.insert_entity(form_entity)

        # Platform admin with GLOBAL scope
        admin_context = RequestContext(
            user_id="admin@example.com",
            email="admin@example.com",
            name="Admin",
            org_id=None,  # GLOBAL scope
            is_platform_admin=True,
            is_function_key=False
        )

        forms = get_user_visible_forms(admin_context)

        assert len(forms) == 1
        assert forms[0]["Name"] == "Global Form"

    def test_platform_admin_can_switch_to_org_scope(self, clean_tables):
        """Platform admin can switch to specific org scope"""
        org_id = generate_entity_id()

        # Create org-specific form
        entities_service = TableStorageService("Entities")
        form_id = generate_entity_id()
        form_entity = {
            "PartitionKey": org_id,
            "RowKey": f"form:{form_id}",
            "Name": "Org Form",
            "Description": "Org specific",
            "IsPublic": True,
            "CreatedAt": datetime.utcnow().isoformat()
        }
        entities_service.insert_entity(form_entity)

        # Platform admin viewing specific org
        admin_context = RequestContext(
            user_id="admin@example.com",
            email="admin@example.com",
            name="Admin",
            org_id=org_id,
            is_platform_admin=True,
            is_function_key=False
        )

        forms = get_user_visible_forms(admin_context)

        assert len(forms) == 1
        assert forms[0]["Name"] == "Org Form"
        assert forms[0]["PartitionKey"] == org_id


class TestRegularUserDataVisibility:
    """Test regular user data visibility rules"""

    def test_regular_user_sees_both_global_and_org_forms(self, clean_tables):
        """Regular users see GLOBAL + their org's forms"""
        org_id = generate_entity_id()

        entities_service = TableStorageService("Entities")

        # Create GLOBAL form
        global_form_id = generate_entity_id()
        global_form = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"form:{global_form_id}",
            "Name": "Global Template Form",
            "IsPublic": True,
            "CreatedAt": datetime.utcnow().isoformat()
        }
        entities_service.insert_entity(global_form)

        # Create org-specific form
        org_form_id = generate_entity_id()
        org_form = {
            "PartitionKey": org_id,
            "RowKey": f"form:{org_form_id}",
            "Name": "Org Custom Form",
            "IsPublic": True,
            "CreatedAt": datetime.utcnow().isoformat()
        }
        entities_service.insert_entity(org_form)

        # Regular user in this org
        user_context = RequestContext(
            user_id="user@example.com",
            email="user@example.com",
            name="User",
            org_id=org_id,
            is_platform_admin=False,
            is_function_key=False
        )

        forms = get_user_visible_forms(user_context)

        # Should see both GLOBAL and org forms
        assert len(forms) == 2
        form_names = {f["Name"] for f in forms}
        assert "Global Template Form" in form_names
        assert "Org Custom Form" in form_names

    def test_regular_user_cannot_see_other_org_forms(self, clean_tables):
        """Regular users cannot see forms from other orgs"""
        org1_id = generate_entity_id()
        org2_id = generate_entity_id()

        entities_service = TableStorageService("Entities")

        # Create form in org1
        form1_id = generate_entity_id()
        form1 = {
            "PartitionKey": org1_id,
            "RowKey": f"form:{form1_id}",
            "Name": "Org1 Form",
            "IsPublic": True,
            "CreatedAt": datetime.utcnow().isoformat()
        }
        entities_service.insert_entity(form1)

        # Create form in org2
        form2_id = generate_entity_id()
        form2 = {
            "PartitionKey": org2_id,
            "RowKey": f"form:{form2_id}",
            "Name": "Org2 Form",
            "IsPublic": True,
            "CreatedAt": datetime.utcnow().isoformat()
        }
        entities_service.insert_entity(form2)

        # User in org1
        user_context = RequestContext(
            user_id="user@example.com",
            email="user@example.com",
            name="User",
            org_id=org1_id,
            is_platform_admin=False,
            is_function_key=False
        )

        forms = get_user_visible_forms(user_context)

        # Should only see org1 form
        assert len(forms) == 1
        assert forms[0]["Name"] == "Org1 Form"


class TestRoleBasedFormAccess:
    """Test role-based form access control"""

    def test_user_can_view_form_with_assigned_role(self, clean_tables):
        """User with assigned role can view private form"""
        org_id = generate_entity_id()
        user_id = "user@example.com"
        form_id = generate_entity_id()
        role_id = generate_entity_id()

        # Create private form
        entities_service = TableStorageService("Entities")
        form_entity = {
            "PartitionKey": org_id,
            "RowKey": f"form:{form_id}",
            "Name": "Private Form",
            "IsPublic": False,  # Private
            "CreatedAt": datetime.utcnow().isoformat()
        }
        entities_service.insert_entity(form_entity)

        # Create role
        relationships_service = TableStorageService("Relationships")
        role_entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"role:{role_id}",
            "Name": "IT Managers",
            "Description": "IT management team",
            "CreatedAt": datetime.utcnow().isoformat()
        }
        relationships_service.insert_entity(role_entity)

        # Assign role to user
        user_role_entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"userrole:{user_id}:{role_id}",
            "UserId": user_id,
            "RoleId": role_id,
            "AssignedAt": datetime.utcnow().isoformat()
        }
        relationships_service.insert_entity(user_role_entity)

        # Assign form to role
        form_role_entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"formrole:{form_id}:{role_id}",
            "FormId": form_id,
            "RoleId": role_id,
            "AssignedAt": datetime.utcnow().isoformat()
        }
        relationships_service.insert_entity(form_role_entity)

        # User context
        user_context = RequestContext(
            user_id=user_id,
            email=user_id,
            name="User",
            org_id=org_id,
            is_platform_admin=False,
            is_function_key=False
        )

        # User should be able to view the form
        can_view = can_user_view_form(user_context, form_id)
        assert can_view is True

        # Form should appear in visible forms list
        forms = get_user_visible_forms(user_context)
        assert len(forms) == 1
        assert forms[0]["Name"] == "Private Form"

    def test_user_cannot_view_form_without_assigned_role(self, clean_tables):
        """User without assigned role cannot view private form"""
        org_id = generate_entity_id()
        user_id = "user@example.com"
        form_id = generate_entity_id()
        role_id = generate_entity_id()

        # Create private form
        entities_service = TableStorageService("Entities")
        form_entity = {
            "PartitionKey": org_id,
            "RowKey": f"form:{form_id}",
            "Name": "Private Form",
            "IsPublic": False,  # Private
            "CreatedAt": datetime.utcnow().isoformat()
        }
        entities_service.insert_entity(form_entity)

        # Create role
        relationships_service = TableStorageService("Relationships")
        role_entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"role:{role_id}",
            "Name": "IT Managers",
            "CreatedAt": datetime.utcnow().isoformat()
        }
        relationships_service.insert_entity(role_entity)

        # Assign form to role (but NOT user to role)
        form_role_entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"formrole:{form_id}:{role_id}",
            "FormId": form_id,
            "RoleId": role_id,
            "AssignedAt": datetime.utcnow().isoformat()
        }
        relationships_service.insert_entity(form_role_entity)

        # User context (no role assignment)
        user_context = RequestContext(
            user_id=user_id,
            email=user_id,
            name="User",
            org_id=org_id,
            is_platform_admin=False,
            is_function_key=False
        )

        # User should NOT be able to view the form
        can_view = can_user_view_form(user_context, form_id)
        assert can_view is False

        # Form should NOT appear in visible forms list
        forms = get_user_visible_forms(user_context)
        assert len(forms) == 0


class TestExecutionVisibility:
    """Test execution visibility and ownership"""

    def test_user_can_only_see_own_executions(self, clean_tables):
        """Regular users can only see their own executions"""
        org_id = generate_entity_id()
        user1_id = "user1@example.com"
        user2_id = "user2@example.com"

        entities_service = TableStorageService("Entities")
        relationships_service = TableStorageService("Relationships")

        # Create execution by user1
        exec1_id = generate_entity_id()
        exec1_entity = {
            "PartitionKey": org_id,
            "RowKey": f"execution:9999999999999_{exec1_id}",
            "ExecutionId": exec1_id,
            "ExecutedBy": user1_id,
            "WorkflowName": "test_workflow",
            "Status": "completed",
            "StartedAt": datetime.utcnow().isoformat()
        }
        entities_service.insert_entity(exec1_entity)

        # Create dual index for user1
        user1_exec_rel = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"userexec:{user1_id}:{exec1_id}",
            "ExecutionId": exec1_id,
            "UserId": user1_id
        }
        relationships_service.insert_entity(user1_exec_rel)

        # Create execution by user2
        exec2_id = generate_entity_id()
        exec2_entity = {
            "PartitionKey": org_id,
            "RowKey": f"execution:9999999999998_{exec2_id}",
            "ExecutionId": exec2_id,
            "ExecutedBy": user2_id,
            "WorkflowName": "test_workflow",
            "Status": "completed",
            "StartedAt": datetime.utcnow().isoformat()
        }
        entities_service.insert_entity(exec2_entity)

        # Create dual index for user2
        user2_exec_rel = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"userexec:{user2_id}:{exec2_id}",
            "ExecutionId": exec2_id,
            "UserId": user2_id
        }
        relationships_service.insert_entity(user2_exec_rel)

        # User1 context
        user1_context = RequestContext(
            user_id=user1_id,
            email=user1_id,
            name="User 1",
            org_id=org_id,
            is_platform_admin=False,
            is_function_key=False
        )

        # User1 should only see their own execution
        can_view_own = can_user_view_execution(user1_context, exec1_entity)
        assert can_view_own is True

        can_view_other = can_user_view_execution(user1_context, exec2_entity)
        assert can_view_other is False

    def test_platform_admin_can_see_all_executions(self, clean_tables):
        """Platform admins can see all executions in their selected scope"""
        org_id = generate_entity_id()
        user_id = "user@example.com"

        entities_service = TableStorageService("Entities")

        # Create execution by regular user
        exec_id = generate_entity_id()
        exec_entity = {
            "PartitionKey": org_id,
            "RowKey": f"execution:9999999999999_{exec_id}",
            "ExecutionId": exec_id,
            "ExecutedBy": user_id,
            "WorkflowName": "test_workflow",
            "Status": "completed",
            "StartedAt": datetime.utcnow().isoformat()
        }
        entities_service.insert_entity(exec_entity)

        # Platform admin context
        admin_context = RequestContext(
            user_id="admin@example.com",
            email="admin@example.com",
            name="Admin",
            org_id=org_id,
            is_platform_admin=True,
            is_function_key=False
        )

        # Admin should be able to view any execution
        can_view = can_user_view_execution(admin_context, exec_entity)
        assert can_view is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
