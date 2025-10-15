"""
End-to-end tests for Forms API
Tests against running Azure Functions instance with real Azurite data
"""

import pytest
import requests


class TestFormsE2E:
    """Test Forms API endpoints end-to-end"""

    def test_list_forms_as_org_user(self, base_url, org_user_headers):
        """Org user should see public global forms + org forms they have access to"""
        response = requests.get(
            f"{base_url}/forms",
            headers=org_user_headers
        )

        assert response.status_code == 200
        forms = response.json()
        assert isinstance(forms, list)

        # Should include at least the public "Simple Greeting" form from seed data
        form_names = [form["name"] for form in forms]
        assert "Simple Greeting" in form_names

        # Verify public forms are marked correctly
        public_forms = [f for f in forms if f.get("isPublic")]
        assert len(public_forms) >= 1

    def test_list_forms_as_platform_admin(self, base_url, platform_admin_headers):
        """
        Platform admin in GLOBAL scope sees global forms.

        Note: Platform admins without X-Organization-Id header operate in GLOBAL scope,
        so they only see global forms. To see org-scoped forms, they must set X-Organization-Id.
        """
        response = requests.get(
            f"{base_url}/forms",
            headers=platform_admin_headers
        )

        assert response.status_code == 200
        forms = response.json()
        assert isinstance(forms, list)
        assert len(forms) >= 1  # At least the global "Simple Greeting" form from seed

        form_names = [form["name"] for form in forms]
        assert "Simple Greeting" in form_names

        # All forms should be global since we're in GLOBAL scope
        for form in forms:
            assert form.get("isGlobal") is True or form.get("orgId") == "GLOBAL"

    def test_create_form_as_platform_admin(self, base_url, platform_admin_headers):
        """Platform admin can create forms"""
        response = requests.post(
            f"{base_url}/forms",
            headers=platform_admin_headers,
            json={
                "name": "Test Form E2E",
                "description": "A test form for E2E testing",
                "linkedWorkflow": "test_workflow",
                "formSchema": {
                    "fields": [
                        {
                            "name": "test_field",
                            "label": "Test Field",
                            "type": "text",
                            "required": True
                        }
                    ]
                },
                "isGlobal": False,
                "isPublic": False
            }
        )

        assert response.status_code == 201
        form = response.json()
        assert form["name"] == "Test Form E2E"
        assert form["description"] == "A test form for E2E testing"
        assert form["isGlobal"] is False
        assert form["isPublic"] is False
        assert len(form["formSchema"]["fields"]) == 1
        assert "id" in form

        # Verify we can retrieve it
        form_id = form["id"]
        get_response = requests.get(
            f"{base_url}/forms/{form_id}",
            headers=platform_admin_headers
        )
        assert get_response.status_code == 200
        retrieved_form = get_response.json()
        assert retrieved_form["id"] == form_id
        assert retrieved_form["name"] == "Test Form E2E"

    def test_create_global_form_as_platform_admin(self, base_url, platform_admin_headers):
        """Platform admin can create global forms"""
        response = requests.post(
            f"{base_url}/forms",
            headers=platform_admin_headers,
            json={
                "name": "Global Test Form",
                "linkedWorkflow": "global_test_workflow",
                "formSchema": {"fields": []},
                "isGlobal": True,
                "isPublic": True
            }
        )

        assert response.status_code == 201
        form = response.json()
        assert form["isGlobal"] is True
        assert form["orgId"] == "GLOBAL"

    def test_get_form_by_id(self, base_url, org_user_headers):
        """User can get a form by ID if they have access"""
        # First get the list to find a form ID
        list_response = requests.get(
            f"{base_url}/forms",
            headers=org_user_headers
        )
        forms = list_response.json()
        assert len(forms) > 0

        # Get the first form
        form_id = forms[0]["id"]
        response = requests.get(
            f"{base_url}/forms/{form_id}",
            headers=org_user_headers
        )

        assert response.status_code == 200
        form = response.json()
        assert form["id"] == form_id
        assert "formSchema" in form
        assert "fields" in form["formSchema"]

    def test_get_form_not_found(self, base_url, platform_admin_headers):
        """Getting non-existent form returns 404"""
        response = requests.get(
            f"{base_url}/forms/non-existent-form-id",
            headers=platform_admin_headers
        )

        assert response.status_code == 404
        error = response.json()
        assert error["error"] == "NotFound"

    def test_update_form_as_platform_admin(self, base_url, platform_admin_headers):
        """Platform admin can update forms"""
        # First create a form
        create_response = requests.post(
            f"{base_url}/forms",
            headers=platform_admin_headers,
            json={
                "name": "Form to Update",
                "linkedWorkflow": "test",
                "formSchema": {"fields": []},
                "isGlobal": False
            }
        )
        assert create_response.status_code == 201
        form_id = create_response.json()["id"]

        # Update it
        update_response = requests.put(
            f"{base_url}/forms/{form_id}",
            headers=platform_admin_headers,
            json={
                "name": "Updated Form Name"
            }
        )

        assert update_response.status_code == 200
        updated_form = update_response.json()
        assert updated_form["name"] == "Updated Form Name"
        assert updated_form["id"] == form_id

    def test_delete_form_as_platform_admin(self, base_url, platform_admin_headers):
        """Platform admin can soft-delete forms"""
        # First create a form
        create_response = requests.post(
            f"{base_url}/forms",
            headers=platform_admin_headers,
            json={
                "name": "Form to Delete",
                "linkedWorkflow": "test",
                "formSchema": {"fields": []},
                "isGlobal": False
            }
        )
        assert create_response.status_code == 201
        form_id = create_response.json()["id"]

        # Delete it
        delete_response = requests.delete(
            f"{base_url}/forms/{form_id}",
            headers=platform_admin_headers
        )

        assert delete_response.status_code == 204

        # Verify it's soft-deleted (should return 404 or isActive=false)
        get_response = requests.get(
            f"{base_url}/forms/{form_id}",
            headers=platform_admin_headers
        )
        # Either 404 (filtered out) or 200 with isActive=false
        if get_response.status_code == 200:
            form = get_response.json()
            assert form["isActive"] is False
        else:
            assert get_response.status_code == 404

    def test_create_form_as_org_user_forbidden(self, base_url, org_user_headers):
        """Org users cannot create forms (platform admin only)"""
        response = requests.post(
            f"{base_url}/forms",
            headers=org_user_headers,
            json={
                "name": "Should Fail",
                "linkedWorkflow": "test",
                "formSchema": {"fields": []},
                "isGlobal": False
            }
        )

        assert response.status_code == 403

    def test_create_form_validation_error(self, base_url, platform_admin_headers):
        """Creating form without required fields returns 400"""
        response = requests.post(
            f"{base_url}/forms",
            headers=platform_admin_headers,
            json={
                "name": "Incomplete Form"
                # Missing: linkedWorkflow, formSchema
            }
        )

        assert response.status_code == 400
        error = response.json()
        assert error["error"] == "ValidationError"
