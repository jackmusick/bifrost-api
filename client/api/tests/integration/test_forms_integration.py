"""
Integration tests for Forms API
Tests full CRUD operations with Azure Table Storage (Azurite)
"""

import pytest
import json
import os
from unittest.mock import MagicMock
from datetime import datetime
import azure.functions as func

# Set development environment for mock auth
os.environ["AZURE_FUNCTIONS_ENVIRONMENT"] = "Development"

from functions.forms import (
    list_forms,
    create_form,
    get_form,
    update_form,
    delete_form
)
from shared.storage import TableStorageService
from shared.models import FormFieldType


def create_mock_request(user_id, email="test@example.com", display_name="Test User", **kwargs):
    """Helper to create a properly mocked request for testing"""
    req = MagicMock(spec=func.HttpRequest)
    req.headers = MagicMock()
    req.headers.get = lambda key, default=None: {
        "X-Test-User-Id": user_id,
        "X-Test-User-Email": email,
        "X-Test-User-Name": display_name
    }.get(key, default)
    req.url = "http://localhost:7071/api/test"

    # Add any additional attributes
    for key, value in kwargs.items():
        setattr(req, key, value)

    return req


class TestListForms:
    """Test GET /api/forms"""

    def test_list_forms_for_org(
        self,
        test_user_with_full_permissions,
        test_form,
        azurite_tables
    ):
        """Test listing forms for an organization"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.params = {"orgId": test_user_with_full_permissions["org_id"]}

        response = list_forms(req)

        assert response.status_code == 200
        forms = json.loads(response.get_body())
        assert isinstance(forms, list)
        assert len(forms) >= 1  # At least the fixture form

        # Find the test form
        test_form_found = any(f["id"] == test_form["form_id"] for f in forms)
        assert test_form_found

    def test_list_forms_includes_global(
        self,
        test_user_with_full_permissions,
        test_global_form,
        azurite_tables
    ):
        """Test that listing forms includes global forms"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.params = {"orgId": test_user_with_full_permissions["org_id"]}

        response = list_forms(req)

        assert response.status_code == 200
        forms = json.loads(response.get_body())

        # Should include global form
        global_forms = [f for f in forms if f["isGlobal"]]
        assert len(global_forms) >= 1

    def test_list_forms_missing_org_id(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test that orgId query parameter is required"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.params = {}

        response = list_forms(req)

        assert response.status_code == 400
        error = json.loads(response.get_body())
        assert error["error"] == "BadRequest"

    def test_list_forms_no_permission(
        self,
        test_user_2,
        test_org,
        azurite_tables
    ):
        """Test that user without org access cannot list forms"""
        req = create_mock_request(
            test_user_2["user_id"],
            test_user_2["email"]
        )
        req.params = {"orgId": test_org["org_id"]}

        response = list_forms(req)

        assert response.status_code == 403
        error = json.loads(response.get_body())
        assert error["error"] == "Forbidden"


class TestCreateForm:
    """Test POST /api/forms"""

    def test_create_form(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test creating a new form"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.params = {"orgId": test_user_with_full_permissions["org_id"]}
        req.get_json.return_value = {
            "name": "New Customer Form",
            "description": "Form for onboarding new customers",
            "linkedWorkflow": "workflows.onboarding.new_customer",
            "formSchema": {
                "fields": [
                    {
                        "name": "company_name",
                        "label": "Company Name",
                        "type": FormFieldType.TEXT.value,
                        "required": True
                    },
                    {
                        "name": "contact_email",
                        "label": "Contact Email",
                        "type": FormFieldType.EMAIL.value,
                        "required": True
                    }
                ]
            },
            "isGlobal": False
        }

        response = create_form(req)

        assert response.status_code == 201  # Created
        form = json.loads(response.get_body())
        assert form["name"] == "New Customer Form"
        assert form["description"] == "Form for onboarding new customers"
        assert form["orgId"] == test_user_with_full_permissions["org_id"]
        assert form["isGlobal"] is False
        assert len(form["formSchema"]["fields"]) == 2

        # Verify in storage
        forms_service = TableStorageService("Forms")
        stored_form = forms_service.get_entity(
            test_user_with_full_permissions["org_id"],
            form["id"]
        )
        assert stored_form is not None
        assert stored_form["Name"] == "New Customer Form"

    def test_create_global_form(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test creating a global form"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.params = {"orgId": test_user_with_full_permissions["org_id"]}
        req.get_json.return_value = {
            "name": "Global Template",
            "linkedWorkflow": "workflows.templates.global",
            "formSchema": {
                "fields": []
            },
            "isGlobal": True
        }

        response = create_form(req)

        assert response.status_code == 201
        form = json.loads(response.get_body())
        assert form["isGlobal"] is True
        assert form["orgId"] == "GLOBAL"

        # Verify in GLOBAL partition
        forms_service = TableStorageService("Forms")
        stored_form = forms_service.get_entity("GLOBAL", form["id"])
        assert stored_form is not None

    def test_create_form_missing_org_id(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test that orgId query parameter is required"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.params = {}
        req.get_json.return_value = {
            "name": "Test Form",
            "linkedWorkflow": "workflows.test",
            "formSchema": {"fields": []}
        }

        response = create_form(req)

        assert response.status_code == 400
        error = json.loads(response.get_body())
        assert error["error"] == "BadRequest"

    def test_create_form_without_permission(
        self,
        test_user_with_limited_permissions,
        azurite_tables
    ):
        """Test that user without canManageForms cannot create forms"""
        req = create_mock_request(
            test_user_with_limited_permissions["user_id"],
            test_user_with_limited_permissions["email"]
        )
        req.params = {"orgId": test_user_with_limited_permissions["org_id"]}
        req.get_json.return_value = {
            "name": "Test Form",
            "linkedWorkflow": "workflows.test",
            "formSchema": {"fields": []}
        }

        response = create_form(req)

        assert response.status_code == 403
        error = json.loads(response.get_body())
        assert error["error"] == "Forbidden"
        assert "manage forms" in error["message"].lower()

    def test_create_form_validation_error(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test validation error when required fields are missing"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.params = {"orgId": test_user_with_full_permissions["org_id"]}
        req.get_json.return_value = {
            "name": "Test Form"
            # Missing: linkedWorkflow, formSchema
        }

        response = create_form(req)

        assert response.status_code == 400
        error = json.loads(response.get_body())
        assert error["error"] == "ValidationError"


class TestGetForm:
    """Test GET /api/forms/{formId}"""

    def test_get_form(
        self,
        test_user_with_full_permissions,
        test_form,
        azurite_tables
    ):
        """Test retrieving a specific form"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"formId": test_form["form_id"]}
        req.params = {"orgId": test_user_with_full_permissions["org_id"]}

        response = get_form(req)

        assert response.status_code == 200
        form = json.loads(response.get_body())
        assert form["id"] == test_form["form_id"]
        assert form["name"] == test_form["name"]

    def test_get_global_form(
        self,
        test_user_with_full_permissions,
        test_global_form,
        azurite_tables
    ):
        """Test retrieving a global form"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"formId": test_global_form["form_id"]}
        req.params = {"orgId": test_user_with_full_permissions["org_id"]}

        response = get_form(req)

        assert response.status_code == 200
        form = json.loads(response.get_body())
        assert form["id"] == test_global_form["form_id"]
        assert form["isGlobal"] is True
        assert form["orgId"] == "GLOBAL"

    def test_get_form_not_found(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test retrieving a non-existent form"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"formId": "non-existent-form-id"}
        req.params = {"orgId": test_user_with_full_permissions["org_id"]}

        response = get_form(req)

        assert response.status_code == 404
        error = json.loads(response.get_body())
        assert error["error"] == "NotFound"

    def test_get_form_without_permission(
        self,
        test_user_2,
        test_org,
        test_form,
        azurite_tables
    ):
        """Test that user without org access cannot get form"""
        req = create_mock_request(
            test_user_2["user_id"],
            test_user_2["email"]
        )
        req.route_params = {"formId": test_form["form_id"]}
        req.params = {"orgId": test_org["org_id"]}

        response = get_form(req)

        assert response.status_code == 403
        error = json.loads(response.get_body())
        assert error["error"] == "Forbidden"


class TestUpdateForm:
    """Test PUT /api/forms/{formId}"""

    def test_update_form_name(
        self,
        test_user_with_full_permissions,
        test_form,
        azurite_tables
    ):
        """Test updating form name"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"formId": test_form["form_id"]}
        req.params = {"orgId": test_user_with_full_permissions["org_id"]}
        req.get_json.return_value = {
            "name": "Updated Form Name"
        }

        response = update_form(req)

        assert response.status_code == 200
        form = json.loads(response.get_body())
        assert form["name"] == "Updated Form Name"

        # Verify in storage
        forms_service = TableStorageService("Forms")
        stored_form = forms_service.get_entity(
            test_user_with_full_permissions["org_id"],
            test_form["form_id"]
        )
        assert stored_form["Name"] == "Updated Form Name"

    def test_update_form_schema(
        self,
        test_user_with_full_permissions,
        test_form,
        azurite_tables
    ):
        """Test updating form schema"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"formId": test_form["form_id"]}
        req.params = {"orgId": test_user_with_full_permissions["org_id"]}
        req.get_json.return_value = {
            "formSchema": {
                "fields": [
                    {
                        "name": "new_field",
                        "label": "New Field",
                        "type": FormFieldType.TEXT.value,
                        "required": False
                    }
                ]
            }
        }

        response = update_form(req)

        assert response.status_code == 200
        form = json.loads(response.get_body())
        assert len(form["formSchema"]["fields"]) == 1
        assert form["formSchema"]["fields"][0]["name"] == "new_field"

    def test_update_form_not_found(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test updating a non-existent form"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"formId": "non-existent-form-id"}
        req.params = {"orgId": test_user_with_full_permissions["org_id"]}
        req.get_json.return_value = {
            "name": "Updated Name"
        }

        response = update_form(req)

        assert response.status_code == 404
        error = json.loads(response.get_body())
        assert error["error"] == "NotFound"

    def test_update_global_form_forbidden(
        self,
        test_user_with_full_permissions,
        test_global_form,
        azurite_tables
    ):
        """Test that updating global forms is forbidden"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"formId": test_global_form["form_id"]}
        req.params = {"orgId": test_user_with_full_permissions["org_id"]}
        req.get_json.return_value = {
            "name": "Updated Name"
        }

        response = update_form(req)

        assert response.status_code == 403
        error = json.loads(response.get_body())
        assert error["error"] == "Forbidden"
        assert "global" in error["message"].lower()

    def test_update_form_without_permission(
        self,
        test_user_with_limited_permissions,
        test_form,
        azurite_tables
    ):
        """Test that user without canManageForms cannot update forms"""
        # Need to create a form in the limited user's org first
        forms_service = TableStorageService("Forms")
        form_id = "limited-user-form"
        forms_service.upsert_entity({
            "PartitionKey": test_user_with_limited_permissions["org_id"],
            "RowKey": form_id,
            "Name": "Limited User Form",
            "LinkedWorkflow": "workflows.test",
            "FormSchema": json.dumps({"fields": []}),
            "IsActive": True,
            "CreatedBy": test_user_with_limited_permissions["user_id"],
            "CreatedAt": datetime.utcnow().isoformat(),
            "UpdatedAt": datetime.utcnow().isoformat()
        })

        req = create_mock_request(
            test_user_with_limited_permissions["user_id"],
            test_user_with_limited_permissions["email"]
        )
        req.route_params = {"formId": form_id}
        req.params = {"orgId": test_user_with_limited_permissions["org_id"]}
        req.get_json.return_value = {
            "name": "Updated Name"
        }

        response = update_form(req)

        assert response.status_code == 403
        error = json.loads(response.get_body())
        assert error["error"] == "Forbidden"
        assert "manage forms" in error["message"].lower()


class TestDeleteForm:
    """Test DELETE /api/forms/{formId}"""

    def test_delete_form(
        self,
        test_user_with_full_permissions,
        test_form,
        azurite_tables
    ):
        """Test soft deleting a form"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"formId": test_form["form_id"]}
        req.params = {"orgId": test_user_with_full_permissions["org_id"]}

        response = delete_form(req)

        assert response.status_code == 204

        # Verify form is soft deleted (IsActive=False)
        forms_service = TableStorageService("Forms")
        stored_form = forms_service.get_entity(
            test_user_with_full_permissions["org_id"],
            test_form["form_id"]
        )
        assert stored_form is not None
        assert stored_form["IsActive"] is False

    def test_delete_form_idempotent(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test that deleting a non-existent form is idempotent"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"formId": "non-existent-form-id"}
        req.params = {"orgId": test_user_with_full_permissions["org_id"]}

        response = delete_form(req)

        assert response.status_code == 204

    def test_delete_global_form_forbidden(
        self,
        test_user_with_full_permissions,
        test_global_form,
        azurite_tables
    ):
        """Test that deleting global forms is forbidden"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"formId": test_global_form["form_id"]}
        req.params = {"orgId": test_user_with_full_permissions["org_id"]}

        response = delete_form(req)

        assert response.status_code == 403
        error = json.loads(response.get_body())
        assert error["error"] == "Forbidden"
        assert "global" in error["message"].lower()

    def test_delete_form_without_permission(
        self,
        test_user_with_limited_permissions,
        azurite_tables
    ):
        """Test that user without canManageForms cannot delete forms"""
        # Create a form in the limited user's org
        forms_service = TableStorageService("Forms")
        form_id = "limited-user-form-to-delete"
        forms_service.upsert_entity({
            "PartitionKey": test_user_with_limited_permissions["org_id"],
            "RowKey": form_id,
            "Name": "Form to Delete",
            "LinkedWorkflow": "workflows.test",
            "FormSchema": json.dumps({"fields": []}),
            "IsActive": True,
            "CreatedBy": test_user_with_limited_permissions["user_id"],
            "CreatedAt": datetime.utcnow().isoformat(),
            "UpdatedAt": datetime.utcnow().isoformat()
        })

        req = create_mock_request(
            test_user_with_limited_permissions["user_id"],
            test_user_with_limited_permissions["email"]
        )
        req.route_params = {"formId": form_id}
        req.params = {"orgId": test_user_with_limited_permissions["org_id"]}

        response = delete_form(req)

        assert response.status_code == 403
        error = json.loads(response.get_body())
        assert error["error"] == "Forbidden"
        assert "manage forms" in error["message"].lower()
