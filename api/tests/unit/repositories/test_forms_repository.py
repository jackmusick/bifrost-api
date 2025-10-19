"""
Unit tests for FormRepository

Tests the forms repository with mocked TableStorageService.
Covers CRUD operations, queries, error handling, and edge cases.
"""

import json
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, call
from azure.core.exceptions import ResourceNotFoundError

from shared.repositories.forms import FormRepository
from shared.models import CreateFormRequest, FormSchema, UpdateFormRequest, Form, FormFieldType


class TestFormRepositoryCreate:
    """Test form creation operations"""

    def test_create_form_success(self, mock_table_service, mock_context):
        """Test successful form creation with all required fields"""
        repo = FormRepository(mock_context)

        form_request = CreateFormRequest(
            name="User Onboarding",
            description="Onboard new users",
            formSchema=FormSchema(fields=[
                {"type": "text", "name": "email", "label": "Email", "required": True}
            ]),
            linkedWorkflow="CreateUserWorkflow",
            isGlobal=False,
            isPublic=False,
            launchWorkflowId="launch-123",
            allowedQueryParams=["email"],
            defaultLaunchParams={"default": "value"}
        )

        mock_table_service.insert_entity.return_value = None

        result = repo.create_form(form_request, "creator-user-123")

        assert result.name == "User Onboarding"
        assert result.id is not None
        assert result.orgId == "test-org-123"
        assert result.linkedWorkflow == "CreateUserWorkflow"
        assert result.isGlobal is False
        assert mock_table_service.insert_entity.call_count == 2

    def test_create_form_with_minimal_fields(self, mock_table_service, mock_context):
        """Test form creation with minimal required fields"""
        repo = FormRepository(mock_context)

        form_request = CreateFormRequest(
            name="Simple Form",
            description=None,
            formSchema=FormSchema(fields=[
                {"type": "text", "name": "simple_field", "label": "Field"}
            ]),
            linkedWorkflow="SimpleWorkflow",
            isGlobal=False,
            isPublic=False
        )

        mock_table_service.insert_entity.return_value = None

        result = repo.create_form(form_request, "creator-user")

        assert result.name == "Simple Form"
        assert result.id is not None

    def test_create_form_global(self, mock_table_service, mock_context):
        """Test creation of global form (visible to all orgs)"""
        repo = FormRepository(mock_context)

        form_request = CreateFormRequest(
            name="Global Form",
            description="Available globally",
            formSchema=FormSchema(fields=[
                {"type": "text", "name": "field1", "label": "Field"}
            ]),
            linkedWorkflow="GlobalWorkflow",
            isGlobal=True,
            isPublic=True
        )

        mock_table_service.insert_entity.return_value = None

        result = repo.create_form(form_request, "admin-user")

        assert result.isGlobal is True

        # Verify partition key is GLOBAL for primary form
        call_args = mock_table_service.insert_entity.call_args_list[0]
        entity = call_args[0][0]
        assert entity["PartitionKey"] == "GLOBAL"

    def test_create_form_sets_created_at(self, mock_table_service, mock_context):
        """Test that created_at timestamp is set during creation"""
        repo = FormRepository(mock_context)

        form_request = CreateFormRequest(
            name="Timestamped Form",
            description=None,
            formSchema=FormSchema(fields=[
                {"type": "text", "name": "field1", "label": "Field"}
            ]),
            linkedWorkflow="TimeWorkflow",
            isGlobal=False,
            isPublic=False
        )

        mock_table_service.insert_entity.return_value = None
        before = datetime.utcnow()

        result = repo.create_form(form_request, "creator")

        after = datetime.utcnow()
        assert before <= result.createdAt <= after


class TestFormRepositoryRead:
    """Test form retrieval operations"""

    def test_get_form_success(self, mock_table_service, mock_context):
        """Test successful form retrieval from org partition"""
        repo = FormRepository(mock_context)

        mock_table_service.get_entity.return_value = {
            "PartitionKey": "test-org-123",
            "RowKey": "form:form-uuid-123",
            "Name": "My Form",
            "Description": "Test form",
            "LinkedWorkflow": "TestWorkflow",
            "FormSchema": json.dumps({"fields": [{"type": "text", "name": "field1", "label": "Field"}]}),
            "IsActive": True,
            "IsPublic": False,
            "CreatedBy": "creator",
            "CreatedAt": "2024-01-15T10:30:00",
            "UpdatedAt": "2024-01-15T10:30:00"
        }

        result = repo.get_form("form-uuid-123")

        assert result is not None
        assert result.name == "My Form"
        assert result.id == "form-uuid-123"
        assert result.orgId == "test-org-123"

    def test_get_form_fallback_to_global(self, mock_table_service, mock_context):
        """Test form retrieval with org -> GLOBAL fallback"""
        repo = FormRepository(mock_context)

        def side_effect(partition_key, row_key):
            if partition_key == "test-org-123":
                # Org-specific not found, return None
                return None
            if partition_key == "GLOBAL":
                return {
                    "PartitionKey": "GLOBAL",
                    "RowKey": "form:global-form-123",
                    "Name": "Global Form",
                    "Description": "Available to all",
                    "LinkedWorkflow": "GlobalWorkflow",
                    "FormSchema": json.dumps({"fields": [{"type": "text", "name": "field1", "label": "Field"}]}),
                    "IsActive": True,
                    "IsPublic": True,
                    "CreatedBy": "admin",
                    "CreatedAt": "2024-01-10T10:00:00",
                    "UpdatedAt": "2024-01-10T10:00:00"
                }
            return None

        mock_table_service.get_entity.side_effect = side_effect

        result = repo.get_form("global-form-123")

        assert result is not None
        assert result.name == "Global Form"
        assert result.isGlobal is True

    def test_get_form_not_found(self, mock_table_service, mock_context):
        """Test retrieval when form doesn't exist"""
        repo = FormRepository(mock_context)

        # Return None for all lookups (form not found anywhere)
        mock_table_service.get_entity.return_value = None

        result = repo.get_form("nonexistent-form-id")

        assert result is None

    def test_get_form_parses_schema_from_json(self, mock_table_service, mock_context):
        """Test that form schema is correctly deserialized from JSON"""
        repo = FormRepository(mock_context)

        schema_dict = {
            "fields": [
                {"type": "text", "name": "email", "label": "Email", "required": True},
                {"type": "select", "name": "role", "label": "Role", "options": [
                    {"label": "Admin", "value": "admin"},
                    {"label": "User", "value": "user"}
                ]}
            ]
        }

        mock_table_service.get_entity.return_value = {
            "PartitionKey": "test-org-123",
            "RowKey": "form:form-123",
            "Name": "Complex Form",
            "FormSchema": json.dumps(schema_dict),
            "LinkedWorkflow": "Workflow",
            "IsActive": True,
            "CreatedBy": "user",
            "CreatedAt": "2024-01-15T10:30:00",
            "UpdatedAt": "2024-01-15T10:30:00"
        }

        result = repo.get_form("form-123")

        assert result is not None
        assert result.formSchema is not None


class TestFormRepositoryList:
    """Test form listing/query operations"""

    def test_list_forms_empty(self, mock_table_service, mock_context):
        """Test listing forms when none exist"""
        repo = FormRepository(mock_context)

        mock_table_service.query_entities.return_value = iter([])

        result = repo.list_forms()

        assert result == []

    def test_list_forms_returns_multiple(self, mock_table_service, mock_context):
        """Test listing multiple forms"""
        repo = FormRepository(mock_context)

        forms_data = [
            {
                "PartitionKey": "test-org-123",
                "RowKey": "form:form-1",
                "Name": "Form 1",
                "LinkedWorkflow": "Workflow1",
                "FormSchema": json.dumps({"fields": [{"type": "text", "name": "f1", "label": "F1"}]}),
                "IsActive": True,
                "CreatedBy": "user",
                "CreatedAt": "2024-01-15T10:30:00",
                "UpdatedAt": "2024-01-15T10:30:00"
            },
            {
                "PartitionKey": "GLOBAL",
                "RowKey": "form:form-2",
                "Name": "Form 2",
                "LinkedWorkflow": "Workflow2",
                "FormSchema": json.dumps({"fields": [{"type": "text", "name": "f2", "label": "F2"}]}),
                "IsActive": True,
                "CreatedBy": "admin",
                "CreatedAt": "2024-01-10T10:30:00",
                "UpdatedAt": "2024-01-10T10:30:00"
            }
        ]

        mock_table_service.query_entities.return_value = iter(forms_data)

        result = repo.list_forms()

        assert len(result) == 2
        assert result[0].name == "Form 1"
        assert result[1].name == "Form 2"

    def test_list_forms_excludes_inactive(self, mock_table_service, mock_context):
        """Test that inactive forms are excluded when active_only=True"""
        repo = FormRepository(mock_context)

        mock_table_service.query_entities.return_value = iter([])

        result = repo.list_forms(active_only=True)

        assert result == []

        call_args = mock_table_service.query_entities.call_args
        filter_query = call_args[1]["filter"]
        assert "IsActive eq true" in filter_query


class TestFormRepositoryUpdate:
    """Test form update operations"""

    def test_update_form_success(self, mock_table_service, mock_context):
        """Test successful form update"""
        repo = FormRepository(mock_context)

        existing_form = {
            "PartitionKey": "test-org-123",
            "RowKey": "form:form-123",
            "Name": "Original Form",
            "Description": "Original desc",
            "LinkedWorkflow": "Workflow1",
            "FormSchema": json.dumps({"fields": [{"type": "text", "name": "f1", "label": "F1"}]}),
            "IsActive": True,
            "CreatedBy": "creator",
            "CreatedAt": "2024-01-15T10:30:00",
            "UpdatedAt": "2024-01-15T10:30:00"
        }

        mock_table_service.get_entity.return_value = existing_form
        mock_table_service.update_entity.return_value = None

        updates = UpdateFormRequest(
            name="Updated Form",
            description="New description",
            linkedWorkflow=None,
            formSchema=None,
            isActive=None
        )

        result = repo.update_form("form-123", updates)

        assert result.name == "Updated Form"
        assert result.description == "New description"

    def test_update_form_not_found(self, mock_table_service, mock_context):
        """Test update raises error when form doesn't exist"""
        repo = FormRepository(mock_context)

        # Return None when form not found
        mock_table_service.get_entity.return_value = None

        updates = UpdateFormRequest(name="Updated")

        with pytest.raises(ValueError, match="not found"):
            repo.update_form("nonexistent-form", updates)

    def test_update_form_partial_fields(self, mock_table_service, mock_context):
        """Test updating only specific fields while preserving others"""
        repo = FormRepository(mock_context)

        existing_form = {
            "PartitionKey": "test-org-123",
            "RowKey": "form:form-123",
            "Name": "Form Name",
            "Description": "Original description",
            "LinkedWorkflow": "OldWorkflow",
            "IsActive": True,
            "CreatedBy": "creator",
            "CreatedAt": "2024-01-15T10:30:00",
            "UpdatedAt": "2024-01-15T10:30:00"
        }

        mock_table_service.get_entity.return_value = existing_form
        mock_table_service.update_entity.return_value = None

        updates = UpdateFormRequest(
            name="New Name Only",
            description=None,
            linkedWorkflow=None,
            formSchema=None,
            isActive=None
        )

        result = repo.update_form("form-123", updates)

        assert result.name == "New Name Only"
        assert result.description == "Original description"


class TestFormRepositoryDelete:
    """Test form deletion operations"""

    def test_soft_delete_form_success(self, mock_table_service, mock_context):
        """Test soft delete sets IsActive to False"""
        repo = FormRepository(mock_context)

        existing_form = {
            "PartitionKey": "test-org-123",
            "RowKey": "form:form-123",
            "Name": "To Delete",
            "LinkedWorkflow": "Workflow1",
            "IsActive": True,
            "CreatedBy": "creator",
            "CreatedAt": "2024-01-15T10:30:00",
            "UpdatedAt": "2024-01-15T10:30:00"
        }

        mock_table_service.get_entity.return_value = existing_form
        mock_table_service.update_entity.return_value = None

        result = repo.soft_delete_form("form-123")

        assert result is True
        # Soft delete calls update_entity (possibly multiple times for different entities)
        assert mock_table_service.update_entity.call_count >= 1

    def test_soft_delete_form_not_found(self, mock_table_service, mock_context):
        """Test soft delete returns False when form not found"""
        repo = FormRepository(mock_context)

        # Return None when form not found
        mock_table_service.get_entity.return_value = None

        result = repo.soft_delete_form("nonexistent-form")

        assert result is False

    def test_delete_form_success(self, mock_table_service, mock_context):
        """Test hard delete removes form"""
        repo = FormRepository(mock_context)

        existing_form = {
            "PartitionKey": "test-org-123",
            "RowKey": "form:form-123",
            "Name": "To Delete",
            "LinkedWorkflow": "Workflow1",
            "CreatedBy": "creator",
            "CreatedAt": "2024-01-15T10:30:00"
        }

        mock_table_service.get_entity.return_value = existing_form
        mock_table_service.delete_entity.return_value = True

        result = repo.delete_form("form-123")

        assert result is True
        assert mock_table_service.delete_entity.call_count >= 1

    def test_delete_form_not_found(self, mock_table_service, mock_context):
        """Test hard delete returns False when form not found"""
        repo = FormRepository(mock_context)

        # Return None when form not found
        mock_table_service.get_entity.return_value = None

        result = repo.delete_form("nonexistent-form")

        assert result is False


class TestFormRepositoryEdgeCases:
    """Test edge cases and error handling"""

    def test_form_with_simple_schema(self, mock_table_service, mock_context):
        """Test form with simple schema"""
        repo = FormRepository(mock_context)

        mock_table_service.get_entity.return_value = {
            "PartitionKey": "test-org-123",
            "RowKey": "form:form-123",
            "Name": "Simple Schema Form",
            "FormSchema": json.dumps({"fields": [{"type": "text", "name": "field1", "label": "Field"}]}),
            "LinkedWorkflow": "Workflow",
            "IsActive": True,
            "CreatedBy": "user",
            "CreatedAt": "2024-01-15T10:30:00",
            "UpdatedAt": "2024-01-15T10:30:00"
        }

        result = repo.get_form("form-123")

        assert result is not None
        assert len(result.formSchema.fields) == 1

    def test_form_with_complex_launch_params(self, mock_table_service, mock_context):
        """Test form with complex launch parameters"""
        repo = FormRepository(mock_context)

        complex_params = {
            "workflow_id": "workflow-123",
            "variables": {
                "email_field": "$.email",
                "name_field": "$.name"
            }
        }

        mock_table_service.get_entity.return_value = {
            "PartitionKey": "test-org-123",
            "RowKey": "form:form-123",
            "Name": "Complex Params Form",
            "FormSchema": json.dumps({"fields": [{"type": "text", "name": "f1", "label": "F"}]}),
            "LinkedWorkflow": "Workflow",
            "DefaultLaunchParams": json.dumps(complex_params),
            "IsActive": True,
            "CreatedBy": "user",
            "CreatedAt": "2024-01-15T10:30:00",
            "UpdatedAt": "2024-01-15T10:30:00"
        }

        result = repo.get_form("form-123")

        assert result is not None
        assert result.defaultLaunchParams == complex_params

    def test_form_timestamps_parsed_correctly(self, mock_table_service, mock_context):
        """Test that ISO format timestamps are parsed correctly"""
        repo = FormRepository(mock_context)

        mock_table_service.get_entity.return_value = {
            "PartitionKey": "test-org-123",
            "RowKey": "form:form-123",
            "Name": "Form",
            "FormSchema": json.dumps({"fields": [{"type": "text", "name": "f1", "label": "F"}]}),
            "LinkedWorkflow": "Workflow",
            "IsActive": True,
            "CreatedBy": "user",
            "CreatedAt": "2024-01-15T10:30:45.123456",
            "UpdatedAt": "2024-01-16T14:22:10.654321"
        }

        result = repo.get_form("form-123")

        assert result is not None
        assert result.createdAt is not None
        assert result.updatedAt is not None
        assert result.updatedAt > result.createdAt
