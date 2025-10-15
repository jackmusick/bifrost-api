"""
Unit tests for authorization helpers
Tests permission checking, form access control, and data visibility filtering
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from shared.authorization import (
    can_user_view_form,
    can_user_execute_form,
    get_user_visible_forms,
    can_user_view_execution,
    get_user_executions,
    get_user_role_ids,
    get_form_role_ids
)
from shared.request_context import RequestContext
from shared.storage import TableStorageService
import uuid


class TestCanUserViewForm:
    """Test can_user_view_form() permission checking"""

    @pytest.fixture
    def mock_entities_table(self):
        """Mock Entities table"""
        return Mock(spec=TableStorageService)

    @pytest.fixture
    def mock_relationships_table(self):
        """Mock Relationships table"""
        return Mock(spec=TableStorageService)

    def test_platform_admin_can_view_any_form(self, mock_entities_table, mock_relationships_table, monkeypatch):
        """Platform admins can view all forms regardless of scope"""
        # Mock table services
        def mock_get_table_service(table_name, context=None):
            if table_name == "Entities":
                return mock_entities_table
            elif table_name == "Relationships":
                return mock_relationships_table
            return Mock()

        monkeypatch.setattr("shared.authorization.TableStorageService", lambda table_name, context=None: mock_get_table_service(table_name, context))

        context = RequestContext(
            user_id="admin@example.com",
            email="admin@example.com",
            name="Admin",
            org_id="org-123",
            is_platform_admin=True,
            is_function_key=False
        )

        form_id = str(uuid.uuid4())
        result = can_user_view_form(context, form_id)

        assert result is True

    def test_regular_user_can_view_public_form(self, mock_entities_table, mock_relationships_table, monkeypatch):
        """Regular users can view public forms"""
        form_id = str(uuid.uuid4())

        # Mock form entity (public)
        mock_entities_table.get_entity.return_value = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"form:{form_id}",
            "Name": "Public Form",
            "IsPublic": True
        }

        def mock_table_storage_service(table_name, context=None):
            if "Entities" in table_name or table_name == "Entities":
                return mock_entities_table
            return Mock()

        monkeypatch.setattr("shared.authorization.TableStorageService", mock_table_storage_service)

        context = RequestContext(
            user_id="user@example.com",
            email="user@example.com",
            name="User",
            org_id="org-123",
            is_platform_admin=False,
            is_function_key=False
        )

        result = can_user_view_form(context, form_id)

        assert result is True

    def test_regular_user_can_view_form_with_assigned_role(self, mock_entities_table, mock_relationships_table, monkeypatch):
        """Regular users can view private forms if they have an assigned role"""
        form_id = str(uuid.uuid4())
        role_id = str(uuid.uuid4())

        # Mock form entity (private)
        mock_entities_table.get_entity.return_value = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"form:{form_id}",
            "Name": "Private Form",
            "IsPublic": False
        }

        # Mock user roles
        mock_relationships_table.query_entities.side_effect = [
            # First call: get user's roles
            iter([{
                "PartitionKey": "GLOBAL",
                "RowKey": f"userrole:user@example.com:{role_id}"
            }]),
            # Second call: get form's roles
            iter([{
                "PartitionKey": "GLOBAL",
                "RowKey": f"formrole:{form_id}:{role_id}"
            }])
        ]

        def mock_table_storage_service(table_name, context=None):
            if "Entities" in table_name or table_name == "Entities":
                return mock_entities_table
            elif "Relationships" in table_name or table_name == "Relationships":
                return mock_relationships_table
            return Mock()

        monkeypatch.setattr("shared.authorization.TableStorageService", mock_table_storage_service)

        context = RequestContext(
            user_id="user@example.com",
            email="user@example.com",
            name="User",
            org_id="org-123",
            is_platform_admin=False,
            is_function_key=False
        )

        result = can_user_view_form(context, form_id)

        assert result is True

    def test_regular_user_cannot_view_form_without_role(self, mock_entities_table, mock_relationships_table, monkeypatch):
        """Regular users cannot view private forms without assigned role"""
        form_id = str(uuid.uuid4())
        role_id = str(uuid.uuid4())

        # Mock form entity (private)
        mock_entities_table.get_entity.return_value = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"form:{form_id}",
            "Name": "Private Form",
            "IsPublic": False
        }

        # Mock user roles (different role than form requires)
        mock_relationships_table.query_entities.side_effect = [
            # First call: get user's roles
            iter([{
                "PartitionKey": "GLOBAL",
                "RowKey": f"userrole:user@example.com:{role_id}"
            }]),
            # Second call: check for form role match (no match)
            iter([])
        ]

        def mock_table_storage_service(table_name, context=None):
            if "Entities" in table_name or table_name == "Entities":
                return mock_entities_table
            elif "Relationships" in table_name or table_name == "Relationships":
                return mock_relationships_table
            return Mock()

        monkeypatch.setattr("shared.authorization.TableStorageService", mock_table_storage_service)

        context = RequestContext(
            user_id="user@example.com",
            email="user@example.com",
            name="User",
            org_id="org-123",
            is_platform_admin=False,
            is_function_key=False
        )

        result = can_user_view_form(context, form_id)

        assert result is False


class TestGetUserVisibleForms:
    """Test get_user_visible_forms() filtering logic"""

    @pytest.fixture
    def mock_entities_table(self):
        return Mock(spec=TableStorageService)

    @pytest.fixture
    def mock_relationships_table(self):
        return Mock(spec=TableStorageService)

    def test_platform_admin_sees_forms_in_selected_scope(self, mock_entities_table, mock_relationships_table, monkeypatch):
        """Platform admins see all forms in their selected scope"""
        form1_id = str(uuid.uuid4())
        form2_id = str(uuid.uuid4())

        # Mock forms in org-123
        mock_entities_table.query_entities.return_value = iter([
            {
                "PartitionKey": "org-123",
                "RowKey": f"form:{form1_id}",
                "Name": "Form 1",
                "IsPublic": True
            },
            {
                "PartitionKey": "org-123",
                "RowKey": f"form:{form2_id}",
                "Name": "Form 2",
                "IsPublic": False
            }
        ])

        def mock_table_storage_service(table_name, context=None):
            if table_name == "Entities":
                return mock_entities_table
            return Mock()

        monkeypatch.setattr("shared.authorization.TableStorageService", mock_table_storage_service)

        context = RequestContext(
            user_id="admin@example.com",
            email="admin@example.com",
            name="Admin",
            org_id="org-123",
            is_platform_admin=True,
            is_function_key=False
        )

        forms = get_user_visible_forms(context)

        assert len(forms) == 2
        assert forms[0]["Name"] == "Form 1"
        assert forms[1]["Name"] == "Form 2"

    def test_regular_user_sees_global_and_org_forms(self, mock_entities_table, mock_relationships_table, monkeypatch):
        """Regular users see forms from BOTH GLOBAL and their org (filtered by roles)"""
        global_form_id = str(uuid.uuid4())
        org_form_id = str(uuid.uuid4())
        role_id = str(uuid.uuid4())

        # Mock will be called twice: once for GLOBAL, once for org
        query_results = [
            # GLOBAL forms
            iter([{
                "PartitionKey": "GLOBAL",
                "RowKey": f"form:{global_form_id}",
                "Name": "Global Form",
                "IsPublic": True
            }]),
            # Org forms
            iter([{
                "PartitionKey": "org-123",
                "RowKey": f"form:{org_form_id}",
                "Name": "Org Form",
                "IsPublic": True
            }])
        ]
        mock_entities_table.query_entities.side_effect = query_results

        # Mock user roles
        mock_relationships_table.query_entities.return_value = iter([{
            "PartitionKey": "GLOBAL",
            "RowKey": f"userrole:user@example.com:{role_id}"
        }])

        call_count = [0]

        def mock_table_storage_service(table_name, context=None):
            if table_name == "Entities":
                call_count[0] += 1
                return mock_entities_table
            elif table_name == "Relationships":
                return mock_relationships_table
            return Mock()

        monkeypatch.setattr("shared.authorization.TableStorageService", mock_table_storage_service)

        # RequestContext is imported directly in the module, no need to patch

        context = RequestContext(
            user_id="user@example.com",
            email="user@example.com",
            name="User",
            org_id="org-123",
            is_platform_admin=False,
            is_function_key=False
        )

        forms = get_user_visible_forms(context)

        # Should see both GLOBAL and org forms (both public in this test)
        assert len(forms) == 2


class TestExecutionVisibility:
    """Test execution visibility and filtering"""

    def test_platform_admin_can_view_any_execution(self):
        """Platform admins can view all executions"""
        context = RequestContext(
            user_id="admin@example.com",
            email="admin@example.com",
            name="Admin",
            org_id="org-123",
            is_platform_admin=True,
            is_function_key=False
        )

        execution_entity = {
            "ExecutionId": str(uuid.uuid4()),
            "ExecutedBy": "other-user@example.com"
        }

        result = can_user_view_execution(context, execution_entity)

        assert result is True

    def test_regular_user_can_only_view_own_executions(self):
        """Regular users can only view their own executions"""
        user_id = "user@example.com"

        context = RequestContext(
            user_id=user_id,
            email=user_id,
            name="User",
            org_id="org-123",
            is_platform_admin=False,
            is_function_key=False
        )

        # User's own execution
        own_execution = {
            "ExecutionId": str(uuid.uuid4()),
            "ExecutedBy": user_id
        }

        result = can_user_view_execution(context, own_execution)
        assert result is True

        # Someone else's execution
        other_execution = {
            "ExecutionId": str(uuid.uuid4()),
            "ExecutedBy": "other-user@example.com"
        }

        result = can_user_view_execution(context, other_execution)
        assert result is False


class TestHelperFunctions:
    """Test authorization helper functions"""

    def test_get_user_role_ids(self, monkeypatch):
        """Test get_user_role_ids() extracts role UUIDs correctly"""
        mock_relationships = Mock(spec=TableStorageService)
        role1_id = str(uuid.uuid4())
        role2_id = str(uuid.uuid4())

        mock_relationships.query_entities.return_value = iter([
            {"RowKey": f"userrole:user@example.com:{role1_id}"},
            {"RowKey": f"userrole:user@example.com:{role2_id}"}
        ])

        role_ids = get_user_role_ids("user@example.com", mock_relationships)

        assert len(role_ids) == 2
        assert role1_id in role_ids
        assert role2_id in role_ids

    def test_get_form_role_ids(self, monkeypatch):
        """Test get_form_role_ids() extracts role UUIDs correctly"""
        mock_relationships = Mock(spec=TableStorageService)
        form_id = str(uuid.uuid4())
        role1_id = str(uuid.uuid4())
        role2_id = str(uuid.uuid4())

        mock_relationships.query_entities.return_value = iter([
            {"RowKey": f"formrole:{form_id}:{role1_id}"},
            {"RowKey": f"formrole:{form_id}:{role2_id}"}
        ])

        role_ids = get_form_role_ids(form_id, mock_relationships)

        assert len(role_ids) == 2
        assert role1_id in role_ids
        assert role2_id in role_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
