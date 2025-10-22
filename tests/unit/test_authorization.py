"""
Unit tests for authorization helpers
Tests permission checking, form access control, and data visibility filtering
"""

import uuid
from unittest.mock import Mock

import pytest

from shared.authorization import (
    can_user_view_execution,
    can_user_view_form,
    get_form_role_ids,
    get_user_role_ids,
    get_user_visible_forms,
)
from shared.request_context import RequestContext
from shared.storage import TableStorageService


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
        """Platform admins can view all active forms regardless of scope"""
        from shared.models import Form, FormSchema
        from datetime import datetime

        context = RequestContext(
            user_id="admin@example.com",
            email="admin@example.com",
            name="Admin",
            org_id="org-123",
            is_platform_admin=True,
            is_function_key=False
        )

        form_id = str(uuid.uuid4())

        # Mock FormRepository to return an active form
        mock_form = Form(
            id=form_id,
            orgId="other-org",
            name="Other Org Form",
            description="Form from another org",
            linkedWorkflow="test_workflow",
            formSchema=FormSchema(fields=[]),
            isActive=True,
            isPublic=False,
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow(),
            createdBy="user@example.com"
        )

        # Mock the repository's get_form method
        def mock_get_form(repo_self, form_id):
            return mock_form

        monkeypatch.setattr("shared.repositories.forms.FormRepository.get_form", mock_get_form)

        result = can_user_view_form(context, form_id)

        # Platform admin can view active forms from any org
        assert result is True

    def test_regular_user_can_view_global_active_form(self, mock_entities_table, mock_relationships_table, monkeypatch):
        """Regular users can view active global forms"""
        from shared.models import Form, FormSchema
        from datetime import datetime

        form_id = str(uuid.uuid4())

        # Mock FormRepository to return an active global form
        mock_form = Form(
            id=form_id,
            orgId="GLOBAL",
            name="Global Form",
            description=None,
            linkedWorkflow="test_workflow",
            formSchema=FormSchema(fields=[]),
            isActive=True,
            isGlobal=True,
            isPublic=True,
            createdBy="system",
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )

        mock_form_repo = Mock()
        mock_form_repo.get_form.return_value = mock_form

        monkeypatch.setattr("shared.authorization.FormRepository", lambda context: mock_form_repo)

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

    def test_regular_user_can_view_org_form(self, mock_entities_table, mock_relationships_table, monkeypatch):
        """Regular users can view active forms in their org"""
        from shared.models import Form, FormSchema
        from datetime import datetime

        form_id = str(uuid.uuid4())

        # Mock FormRepository to return an active org form
        mock_form = Form(
            id=form_id,
            orgId="org-123",
            name="Org Form",
            description=None,
            linkedWorkflow="test_workflow",
            formSchema=FormSchema(fields=[]),
            isActive=True,
            isGlobal=False,
            isPublic=False,
            createdBy="system",
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )

        mock_form_repo = Mock()
        mock_form_repo.get_form.return_value = mock_form

        monkeypatch.setattr("shared.authorization.FormRepository", lambda context: mock_form_repo)

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

    def test_regular_user_cannot_view_inactive_form(self, mock_entities_table, mock_relationships_table, monkeypatch):
        """Regular users cannot view inactive forms"""
        from shared.models import Form, FormSchema
        from datetime import datetime

        form_id = str(uuid.uuid4())

        # Mock FormRepository to return an INACTIVE form
        mock_form = Form(
            id=form_id,
            orgId="GLOBAL",
            name="Inactive Form",
            description=None,
            linkedWorkflow="test_workflow",
            formSchema=FormSchema(fields=[]),
            isActive=False,  # INACTIVE
            isGlobal=True,
            isPublic=True,
            createdBy="system",
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )

        mock_form_repo = Mock()
        mock_form_repo.get_form.return_value = mock_form

        monkeypatch.setattr("shared.authorization.FormRepository", lambda context: mock_form_repo)

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

    def test_regular_user_cannot_view_other_org_form(self, mock_entities_table, mock_relationships_table, monkeypatch):
        """Regular users cannot view forms from other organizations"""
        form_id = str(uuid.uuid4())

        # Mock FormRepository to return None (form not found in user's scope)
        # This simulates the repository's fallback logic not finding the form
        mock_form_repo = Mock()
        mock_form_repo.get_form.return_value = None

        monkeypatch.setattr("shared.authorization.FormRepository", lambda context: mock_form_repo)

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
        """Platform admins see all forms in their selected scope (including inactive)"""
        from shared.models import Form, FormSchema
        from datetime import datetime

        form1_id = str(uuid.uuid4())
        form2_id = str(uuid.uuid4())

        # Mock FormRepository to return both active and inactive forms
        mock_forms = [
            Form(
                id=form1_id,
                orgId="org-123",
                name="Form 1",
                description=None,
                linkedWorkflow="workflow1",
                formSchema=FormSchema(fields=[]),
                isActive=True,
                isGlobal=False,
                isPublic=False,
                createdBy="admin",
                createdAt=datetime.utcnow(),
                updatedAt=datetime.utcnow()
            ),
            Form(
                id=form2_id,
                orgId="org-123",
                name="Form 2",
                description=None,
                linkedWorkflow="workflow2",
                formSchema=FormSchema(fields=[]),
                isActive=False,  # INACTIVE but admin can still see it
                isGlobal=False,
                isPublic=False,
                createdBy="admin",
                createdAt=datetime.utcnow(),
                updatedAt=datetime.utcnow()
            )
        ]

        mock_form_repo = Mock()
        mock_form_repo.list_forms.return_value = mock_forms

        monkeypatch.setattr("shared.authorization.FormRepository", lambda context: mock_form_repo)

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
        assert forms[0]["name"] == "Form 1"
        assert forms[1]["name"] == "Form 2"

    def test_regular_user_sees_global_and_org_forms(self, mock_entities_table, mock_relationships_table, monkeypatch):
        """Regular users see active forms from BOTH GLOBAL and their org"""
        from shared.models import Form, FormSchema
        from datetime import datetime

        global_form_id = str(uuid.uuid4())
        org_form_id = str(uuid.uuid4())

        # Mock FormRepository to return both global and org forms (active only)
        mock_forms = [
            Form(
                id=global_form_id,
                orgId="GLOBAL",
                name="Global Form",
                description=None,
                linkedWorkflow="workflow1",
                formSchema=FormSchema(fields=[]),
                isActive=True,
                isGlobal=True,
                isPublic=True,
                createdBy="system",
                createdAt=datetime.utcnow(),
                updatedAt=datetime.utcnow()
            ),
            Form(
                id=org_form_id,
                orgId="org-123",
                name="Org Form",
                description=None,
                linkedWorkflow="workflow2",
                formSchema=FormSchema(fields=[]),
                isActive=True,
                isGlobal=False,
                isPublic=False,
                createdBy="admin",
                createdAt=datetime.utcnow(),
                updatedAt=datetime.utcnow()
            )
        ]

        mock_form_repo = Mock()
        mock_form_repo.list_forms.return_value = mock_forms

        monkeypatch.setattr("shared.authorization.FormRepository", lambda context: mock_form_repo)

        context = RequestContext(
            user_id="user@example.com",
            email="user@example.com",
            name="User",
            org_id="org-123",
            is_platform_admin=False,
            is_function_key=False
        )

        forms = get_user_visible_forms(context)

        # Should see both GLOBAL and org forms (both active in this test)
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
        role1_id = str(uuid.uuid4())
        role2_id = str(uuid.uuid4())

        # Mock RoleRepository
        mock_role_repo = Mock()
        mock_role_repo.get_user_role_ids.return_value = [role1_id, role2_id]

        role_ids = get_user_role_ids("user@example.com", mock_role_repo)

        assert len(role_ids) == 2
        assert role1_id in role_ids
        assert role2_id in role_ids

    def test_get_form_role_ids(self, monkeypatch):
        """Test get_form_role_ids() extracts role UUIDs correctly"""
        form_id = str(uuid.uuid4())
        role1_id = str(uuid.uuid4())
        role2_id = str(uuid.uuid4())

        # Mock RoleRepository
        mock_role_repo = Mock()
        mock_role_repo.get_form_role_ids.return_value = [role1_id, role2_id]

        role_ids = get_form_role_ids(form_id, mock_role_repo)

        assert len(role_ids) == 2
        assert role1_id in role_ids
        assert role2_id in role_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
