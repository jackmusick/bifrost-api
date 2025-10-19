"""Integration tests for Forms API endpoints

Tests the form management endpoints:
- POST /api/forms - Create form
- GET /api/forms - List forms
- GET /api/forms/{formId} - Get form
- PUT /api/forms/{formId} - Update form
- DELETE /api/forms/{formId} - Delete form (soft delete)
- POST /api/forms/{formId}/startup - Execute form's launch workflow
- POST /api/forms/{formId}/execute - Submit form and execute linked workflow
"""

import json
import logging
import pytest
import requests

logger = logging.getLogger(__name__)


class TestFormCRUD:
    """Test form CRUD operations"""

    def test_create_form_success(self, api_base_url, admin_headers):
        """Should create form and return form details"""
        form_data = {
            "name": "New User Onboarding",
            "description": "Form to onboard new users",
            "formSchema": {
                "fields": [
                    {
                        "type": "text",
                        "name": "email",
                        "label": "Email Address",
                        "required": True
                    },
                    {
                        "type": "text",
                        "name": "name",
                        "label": "Full Name",
                        "required": True
                    }
                ]
            },
            "linkedWorkflow": "",
            "isPublic": True
        }

        response = requests.post(
            f"{api_base_url}/api/forms",
            headers=admin_headers,
            json=form_data,
            timeout=10
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["name"] == "New User Onboarding"
        assert data["description"] == "Form to onboard new users"
        assert data["isPublic"] is True
        logger.info(f"Successfully created form: {data['id']}")

    def test_create_form_missing_required_field(self, api_base_url, admin_headers):
        """Should reject form without required name"""
        form_data = {
            "description": "Missing name field",
            "formSchema": {"fields": []}
        }

        response = requests.post(
            f"{api_base_url}/api/forms",
            headers=admin_headers,
            json=form_data,
            timeout=10
        )

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        logger.info("Correctly rejected form without required name")

    def test_create_form_invalid_json(self, api_base_url, admin_headers):
        """Should reject request with invalid JSON"""
        response = requests.post(
            f"{api_base_url}/api/forms",
            headers=admin_headers,
            data="not valid json",
            timeout=10
        )

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        logger.info("Correctly rejected invalid JSON")

    def test_list_forms(self, api_base_url, admin_headers, test_form):
        """Should list all forms visible to user"""
        response = requests.get(
            f"{api_base_url}/api/forms",
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        # Should contain at least our test form
        form_ids = [f["id"] for f in data]
        assert test_form in form_ids, f"Test form {test_form} not in list"
        logger.info(f"Listed {len(data)} forms")

    def test_get_form_success(self, api_base_url, admin_headers, test_form):
        """Should retrieve form by ID"""
        response = requests.get(
            f"{api_base_url}/api/forms/{test_form}",
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["id"] == test_form
        assert "name" in data
        assert "formSchema" in data
        logger.info(f"Retrieved form: {test_form}")

    def test_get_form_not_found(self, api_base_url, admin_headers):
        """Should return 404 for nonexistent form"""
        fake_form_id = "00000000-0000-0000-0000-000000000000"
        response = requests.get(
            f"{api_base_url}/api/forms/{fake_form_id}",
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        logger.info("Correctly returned 404 for nonexistent form")

    def test_update_form_success(self, api_base_url, admin_headers, test_form):
        """Should update form name and description"""
        update_data = {
            "name": "Updated Onboarding Form",
            "description": "Updated description"
        }

        response = requests.put(
            f"{api_base_url}/api/forms/{test_form}",
            headers=admin_headers,
            json=update_data,
            timeout=10
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["name"] == "Updated Onboarding Form"
        assert data["description"] == "Updated description"
        logger.info(f"Updated form: {test_form}")

    def test_update_form_not_found(self, api_base_url, admin_headers):
        """Should return 404 when updating nonexistent form"""
        fake_form_id = "00000000-0000-0000-0000-000000000000"
        response = requests.put(
            f"{api_base_url}/api/forms/{fake_form_id}",
            headers=admin_headers,
            json={"name": "Updated Name"},
            timeout=10
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        logger.info("Correctly returned 404 for nonexistent form on update")

    def test_delete_form_success(self, api_base_url, admin_headers):
        """Should soft delete form (set isActive=False)"""
        # Create a form to delete
        form_data = {
            "name": "Form to Delete",
            "description": "Will be deleted",
            "formSchema": {"fields": []},
            "isPublic": True
        }

        create_response = requests.post(
            f"{api_base_url}/api/forms",
            headers=admin_headers,
            json=form_data,
            timeout=10
        )
        assert create_response.status_code == 201
        form_id = create_response.json()["id"]

        # Delete the form
        delete_response = requests.delete(
            f"{api_base_url}/api/forms/{form_id}",
            headers=admin_headers,
            timeout=10
        )

        assert delete_response.status_code == 204, f"Expected 204, got {delete_response.status_code}"

        # Verify form is deleted (returns 404)
        get_response = requests.get(
            f"{api_base_url}/api/forms/{form_id}",
            headers=admin_headers,
            timeout=10
        )
        assert get_response.status_code == 404, f"Deleted form should return 404, got {get_response.status_code}"
        logger.info(f"Soft deleted form: {form_id}")

    def test_delete_form_idempotent(self, api_base_url, admin_headers):
        """Should return 204 even if form already deleted (idempotent)"""
        fake_form_id = "00000000-0000-0000-0000-000000000000"
        response = requests.delete(
            f"{api_base_url}/api/forms/{fake_form_id}",
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code == 204, f"Expected 204 (idempotent), got {response.status_code}"
        logger.info("Delete is idempotent")


class TestFormPermissions:
    """Test form access control and permissions"""

    def test_regular_user_can_list_forms(self, api_base_url, user_headers):
        """Regular users should be able to list public forms"""
        response = requests.get(
            f"{api_base_url}/api/forms",
            headers=user_headers,
            timeout=10
        )

        # Should either return 200 (empty list for user) or 403 depending on implementation
        assert response.status_code in [200, 403], f"Expected 200 or 403, got {response.status_code}"
        logger.info(f"Regular user list forms returned {response.status_code}")

    def test_regular_user_cannot_create_form(self, api_base_url, user_headers):
        """Regular users should not be able to create forms"""
        form_data = {
            "name": "Unauthorized Form",
            "formSchema": {"fields": []},
            "isPublic": True
        }

        response = requests.post(
            f"{api_base_url}/api/forms",
            headers=user_headers,
            json=form_data,
            timeout=10
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        logger.info("Correctly rejected non-admin form creation")

    def test_regular_user_cannot_delete_form(self, api_base_url, user_headers, admin_headers, test_form):
        """Regular users should not be able to delete forms"""
        response = requests.delete(
            f"{api_base_url}/api/forms/{test_form}",
            headers=user_headers,
            timeout=10
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        logger.info("Correctly rejected non-admin form deletion")


class TestFormStartup:
    """Test form startup/launch workflow endpoint"""

    def test_form_startup_no_launch_workflow(self, api_base_url, admin_headers, test_form):
        """Should return empty result if form has no launch workflow"""
        response = requests.post(
            f"{api_base_url}/api/forms/{test_form}/startup",
            headers=admin_headers,
            json={},
            timeout=10
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "result" in data
        logger.info("Form startup returned empty result for no launch workflow")

    def test_form_startup_not_found(self, api_base_url, admin_headers):
        """Should return 404 for nonexistent form"""
        fake_form_id = "00000000-0000-0000-0000-000000000000"
        response = requests.post(
            f"{api_base_url}/api/forms/{fake_form_id}/startup",
            headers=admin_headers,
            json={},
            timeout=10
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        logger.info("Correctly returned 404 for nonexistent form in startup")

    def test_form_startup_via_get(self, api_base_url, admin_headers, test_form):
        """Should support both GET and POST methods for startup"""
        response = requests.get(
            f"{api_base_url}/api/forms/{test_form}/startup",
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "result" in data
        logger.info("Form startup via GET succeeded")


class TestFormExecution:
    """Test form execution endpoint"""

    def test_form_execute_without_linked_workflow(self, api_base_url, admin_headers, test_form):
        """Should return error if form has no linked workflow"""
        response = requests.post(
            f"{api_base_url}/api/forms/{test_form}/execute",
            headers=admin_headers,
            json={"form_data": {}},
            timeout=10
        )

        # Form without linked workflow should fail
        # Could be 400 (bad request) or 500 (internal error)
        assert response.status_code in [400, 500], f"Expected 400 or 500, got {response.status_code}"
        logger.info("Correctly returned error for form without linked workflow")

    def test_form_execute_not_found(self, api_base_url, admin_headers):
        """Should return 404 for nonexistent form"""
        fake_form_id = "00000000-0000-0000-0000-000000000000"
        response = requests.post(
            f"{api_base_url}/api/forms/{fake_form_id}/execute",
            headers=admin_headers,
            json={"form_data": {}},
            timeout=10
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        logger.info("Correctly returned 404 for nonexistent form in execute")

    def test_form_execute_invalid_json(self, api_base_url, admin_headers, test_form):
        """Should reject request with invalid JSON"""
        response = requests.post(
            f"{api_base_url}/api/forms/{test_form}/execute",
            headers=admin_headers,
            data="not valid json",
            timeout=10
        )

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        logger.info("Correctly rejected invalid JSON in execute")


class TestFormAuthorizationRequired:
    """Test form endpoints require authentication"""

    def test_list_forms_no_headers(self, api_base_url):
        """Should reject request without auth headers"""
        response = requests.get(
            f"{api_base_url}/api/forms",
            timeout=10
        )

        # Could return 400 (missing header) or 401 (unauthorized)
        assert response.status_code in [400, 401, 403], f"Expected 400/401/403, got {response.status_code}"
        logger.info("Correctly rejected list without auth headers")

    def test_create_form_no_headers(self, api_base_url):
        """Should reject request without auth headers"""
        response = requests.post(
            f"{api_base_url}/api/forms",
            json={"name": "Test"},
            timeout=10
        )

        assert response.status_code in [400, 401, 403], f"Expected 400/401/403, got {response.status_code}"
        logger.info("Correctly rejected create without auth headers")

    def test_create_form_non_admin(self, api_base_url, user_headers):
        """Should reject form creation from non-admin user"""
        form_data = {
            "name": "Test Form",
            "formSchema": {"fields": []},
            "isPublic": True
        }

        response = requests.post(
            f"{api_base_url}/api/forms",
            headers=user_headers,
            json=form_data,
            timeout=10
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        logger.info("Correctly rejected non-admin form creation")


class TestFormSchema:
    """Test form schema validation"""

    def test_create_form_complex_schema(self, api_base_url, admin_headers):
        """Should create form with complex field schema"""
        form_data = {
            "name": "Complex Form",
            "description": "Form with various field types",
            "formSchema": {
                "fields": [
                    {
                        "type": "text",
                        "name": "name",
                        "label": "Full Name",
                        "required": True
                    },
                    {
                        "type": "email",
                        "name": "email",
                        "label": "Email",
                        "required": True
                    },
                    {
                        "type": "textarea",
                        "name": "message",
                        "label": "Message",
                        "required": False
                    },
                    {
                        "type": "select",
                        "name": "department",
                        "label": "Department",
                        "options": ["Sales", "Engineering", "Support"],
                        "required": True
                    }
                ]
            },
            "isPublic": True
        }

        response = requests.post(
            f"{api_base_url}/api/forms",
            headers=admin_headers,
            json=form_data,
            timeout=10
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert len(data["formSchema"]["fields"]) == 4
        logger.info("Successfully created form with complex schema")

    def test_create_form_empty_fields(self, api_base_url, admin_headers):
        """Should allow form with empty fields array"""
        form_data = {
            "name": "Empty Fields Form",
            "formSchema": {"fields": []},
            "isPublic": True
        }

        response = requests.post(
            f"{api_base_url}/api/forms",
            headers=admin_headers,
            json=form_data,
            timeout=10
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        logger.info("Successfully created form with empty fields")
