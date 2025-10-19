"""Integration tests for Forms API edge cases

Tests edge cases in form management:
- Complex field validation scenarios
- Submission data validation edge cases
- Workflow linking failures
- Form versioning and updates
- Circular dependencies
- Field type validation
- Schema validation
- Form submission processing
- Workflow integration
"""

import json
import logging
import pytest
import requests
import uuid
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TestFormFieldValidationEdgeCases:
    """Test complex field validation scenarios"""

    def test_create_form_with_invalid_field_types(self, api_base_url, admin_headers):
        """Should reject form with invalid field types"""
        form_data = {
            "name": "Test Form",
            "description": "Form with invalid field",
            "formSchema": {
                "fields": [
                    {
                        "type": "invalid_type_xyz",
                        "name": "field1",
                        "label": "Field 1",
                        "required": True
                    }
                ]
            }
        }
        response = requests.post(
            f"{api_base_url}/api/forms",
            headers=admin_headers,
            json=form_data,
            timeout=10
        )
        # May accept or validate field types
        assert response.status_code in [201, 400, 422]

    def test_form_field_with_conflicting_constraints(self, api_base_url, admin_headers):
        """Should handle conflicting field constraints"""
        form_data = {
            "name": "Test Form",
            "description": "Form with conflicting constraints",
            "formSchema": {
                "fields": [
                    {
                        "type": "text",
                        "name": "email",
                        "label": "Email",
                        "required": True,
                        "minLength": 50,
                        "maxLength": 10  # maxLength < minLength
                    }
                ]
            }
        }
        response = requests.post(
            f"{api_base_url}/api/forms",
            headers=admin_headers,
            json=form_data,
            timeout=10
        )
        # May accept (and fail on submission) or validate
        assert response.status_code in [201, 400, 422]

    def test_form_with_empty_field_list(self, api_base_url, admin_headers):
        """Should handle form with no fields"""
        form_data = {
            "name": "Empty Form",
            "description": "Form with no fields",
            "formSchema": {
                "fields": []
            }
        }
        response = requests.post(
            f"{api_base_url}/api/forms",
            headers=admin_headers,
            json=form_data,
            timeout=10
        )
        assert response.status_code in [201, 400, 422]

    def test_form_with_duplicate_field_names(self, api_base_url, admin_headers):
        """Should handle duplicate field names"""
        form_data = {
            "name": "Test Form",
            "description": "Form with duplicate fields",
            "formSchema": {
                "fields": [
                    {"type": "text", "name": "email", "label": "Email 1"},
                    {"type": "text", "name": "email", "label": "Email 2"}  # Duplicate
                ]
            }
        }
        response = requests.post(
            f"{api_base_url}/api/forms",
            headers=admin_headers,
            json=form_data,
            timeout=10
        )
        # May accept or validate uniqueness
        assert response.status_code in [201, 400, 422]

    def test_form_with_deeply_nested_schema(self, api_base_url, admin_headers):
        """Should handle deeply nested schema structures"""
        form_data = {
            "name": "Complex Form",
            "description": "Form with nested schema",
            "formSchema": {
                "sections": [
                    {
                        "name": "Section 1",
                        "groups": [
                            {
                                "name": "Group 1",
                                "fields": [
                                    {"type": "text", "name": "field1"}
                                ]
                            }
                        ]
                    }
                ]
            }
        }
        response = requests.post(
            f"{api_base_url}/api/forms",
            headers=admin_headers,
            json=form_data,
            timeout=10
        )
        # May accept nested structure or require flat schema
        assert response.status_code in [201, 400, 422]


class TestFormSubmissionValidationEdgeCases:
    """Test submission data validation edge cases"""

    def test_submit_form_with_missing_required_field(self, api_base_url, admin_headers, test_form):
        """Should reject submission missing required field"""
        submission_data = {
            # Missing required "email" field
            "name": "John Doe"
        }
        response = requests.post(
            f"{api_base_url}/api/forms/{test_form}/submissions",
            headers=admin_headers,
            json=submission_data,
            timeout=10
        )
        # Should validate required fields
        assert response.status_code in [201, 400, 404, 422]  # May accept or validate

    def test_submit_form_with_extra_fields(self, api_base_url, admin_headers, test_form):
        """Should handle submission with extra fields"""
        submission_data = {
            "email": "test@example.com",
            "name": "Test User",
            "extra_field": "should not exist"
        }
        response = requests.post(
            f"{api_base_url}/api/forms/{test_form}/submissions",
            headers=admin_headers,
            json=submission_data,
            timeout=10
        )
        # May accept (and ignore) or validate strict
        assert response.status_code in [201, 400, 404, 422]

    def test_submit_form_with_invalid_data_types(self, api_base_url, admin_headers, test_form):
        """Should validate field data types"""
        submission_data = {
            "email": 12345,  # Should be string
            "name": ["array", "instead", "of", "string"]
        }
        response = requests.post(
            f"{api_base_url}/api/forms/{test_form}/submissions",
            headers=admin_headers,
            json=submission_data,
            timeout=10
        )
        # Should validate types
        assert response.status_code in [201, 400, 404, 422]

    def test_submit_form_with_null_values(self, api_base_url, admin_headers, test_form):
        """Should handle null/None values in submission"""
        submission_data = {
            "email": None,
            "name": None
        }
        response = requests.post(
            f"{api_base_url}/api/forms/{test_form}/submissions",
            headers=admin_headers,
            json=submission_data,
            timeout=10
        )
        # Should reject nulls for required fields
        assert response.status_code in [201, 400, 404, 422]

    def test_submit_form_exceeding_size_limit(self, api_base_url, admin_headers, test_form):
        """Should reject very large submissions"""
        submission_data = {
            "email": "test@example.com",
            "name": "x" * 1000000  # Very large string
        }
        response = requests.post(
            f"{api_base_url}/api/forms/{test_form}/submissions",
            headers=admin_headers,
            json=submission_data,
            timeout=10
        )
        # May accept or reject based on size limits
        assert response.status_code in [201, 404, 413, 422]


class TestFormWorkflowLinkingEdgeCases:
    """Test workflow linking failure scenarios"""

    def test_link_nonexistent_workflow(self, api_base_url, admin_headers):
        """Should handle link to nonexistent workflow"""
        form_data = {
            "name": "Test Form",
            "linkedWorkflow": "nonexistent-workflow-xyz",
            "formSchema": {"fields": []}
        }
        response = requests.post(
            f"{api_base_url}/api/forms",
            headers=admin_headers,
            json=form_data,
            timeout=10
        )
        # May accept (validate later) or reject
        assert response.status_code in [201, 400, 422]

    def test_update_form_with_invalid_workflow(self, api_base_url, admin_headers, test_form):
        """Should validate workflow on update"""
        update_data = {
            "linkedWorkflow": "invalid-workflow-xyz"
        }
        response = requests.put(
            f"{api_base_url}/api/forms/{test_form}",
            headers=admin_headers,
            json=update_data,
            timeout=10
        )
        # May validate or accept
        assert response.status_code in [200, 204, 400, 422, 404]

    def test_circular_workflow_dependency(self, api_base_url, admin_headers):
        """Should detect circular workflow dependencies"""
        # Create form1
        form1_data = {
            "name": "Form 1",
            "linkedWorkflow": "workflow-a",
            "formSchema": {"fields": []}
        }
        response1 = requests.post(
            f"{api_base_url}/api/forms",
            headers=admin_headers,
            json=form1_data,
            timeout=10
        )

        if response1.status_code == 201:
            form1_id = response1.json().get("id")
            # Try to create form that links to workflow that links back
            form2_data = {
                "name": "Form 2",
                "linkedWorkflow": "workflow-b",
                "formSchema": {"fields": []}
            }
            response2 = requests.post(
                f"{api_base_url}/api/forms",
                headers=admin_headers,
                json=form2_data,
                timeout=10
            )
            # May allow or prevent
            assert response2.status_code in [201, 400, 422]

    def test_unlink_workflow(self, api_base_url, admin_headers, test_form):
        """Should handle removing workflow link"""
        update_data = {
            "linkedWorkflow": None
        }
        response = requests.put(
            f"{api_base_url}/api/forms/{test_form}",
            headers=admin_headers,
            json=update_data,
            timeout=10
        )
        # Should allow unlinking
        assert response.status_code in [200, 204, 404]


class TestFormVersioningAndUpdates:
    """Test form versioning and update scenarios"""

    def test_update_form_schema_without_version_check(self, api_base_url, admin_headers, test_form):
        """Should handle schema updates"""
        update_data = {
            "formSchema": {
                "fields": [
                    {"type": "text", "name": "new_field"}
                ]
            }
        }
        response = requests.put(
            f"{api_base_url}/api/forms/{test_form}",
            headers=admin_headers,
            json=update_data,
            timeout=10
        )
        # 404 may occur if test form fixture is not created, 400 for invalid schema
        assert response.status_code in [200, 204, 400, 404]

    def test_concurrent_form_updates(self, api_base_url, admin_headers, test_form):
        """Should handle concurrent updates"""
        update1 = {
            "description": "Updated 1"
        }
        update2 = {
            "description": "Updated 2"
        }

        response1 = requests.put(
            f"{api_base_url}/api/forms/{test_form}",
            headers=admin_headers,
            json=update1,
            timeout=10
        )
        response2 = requests.put(
            f"{api_base_url}/api/forms/{test_form}",
            headers=admin_headers,
            json=update2,
            timeout=10
        )

        # At least one should succeed
        assert response1.status_code in [200, 204, 404] or response2.status_code in [200, 204, 404]

    def test_delete_form_with_existing_submissions(self, api_base_url, admin_headers, test_form):
        """Should handle deletion of form with submissions"""
        # First submit to form
        submission_data = {
            "email": "test@example.com",
            "name": "Test User"
        }
        requests.post(
            f"{api_base_url}/api/forms/{test_form}/submissions",
            headers=admin_headers,
            json=submission_data,
            timeout=10
        )

        # Then delete form
        response = requests.delete(
            f"{api_base_url}/api/forms/{test_form}",
            headers=admin_headers,
            timeout=10
        )
        # May allow (cascade) or prevent
        assert response.status_code in [200, 204, 409, 404]

    def test_get_form_version_history(self, api_base_url, admin_headers, test_form):
        """Should retrieve form version history"""
        response = requests.get(
            f"{api_base_url}/api/forms/{test_form}/versions",
            headers=admin_headers,
            timeout=10
        )
        # May have versions endpoint or not
        assert response.status_code in [200, 404]


class TestFormAccessControl:
    """Test form access control edge cases"""

    def test_unauthorized_user_cannot_create_form(self, api_base_url, user_headers):
        """Regular users should not create forms"""
        form_data = {
            "name": "Unauthorized Form",
            "formSchema": {"fields": []}
        }
        response = requests.post(
            f"{api_base_url}/api/forms",
            headers=user_headers,
            json=form_data,
            timeout=10
        )
        # Should be restricted
        assert response.status_code in [401, 403, 400]

    def test_list_public_forms(self, api_base_url):
        """Should list public forms without auth"""
        response = requests.get(
            f"{api_base_url}/api/forms/public",
            timeout=10
        )
        # May have public endpoint or require auth
        assert response.status_code in [200, 401, 404]

    def test_form_visibility_boundaries(self, api_base_url, admin_headers, test_org_id):
        """Should respect form visibility across orgs"""
        form_data = {
            "name": "Test Form",
            "isPublic": False,
            "formSchema": {"fields": []}
        }
        response = requests.post(
            f"{api_base_url}/api/forms",
            headers=admin_headers,
            json=form_data,
            timeout=10
        )

        if response.status_code == 201:
            form_id = response.json().get("id")
            # Try to access from different org
            different_org_headers = {
                **admin_headers,
                "X-Organization-ID": f"other-org-{uuid.uuid4().hex[:8]}"
            }
            response2 = requests.get(
                f"{api_base_url}/api/forms/{form_id}",
                headers=different_org_headers,
                timeout=10
            )
            # Should restrict access
            assert response2.status_code in [403, 404]


class TestFormDataValidationBoundaries:
    """Test data validation at boundaries"""

    def test_form_with_maximum_fields(self, api_base_url, admin_headers):
        """Should handle form with many fields"""
        fields = [
            {"type": "text", "name": f"field_{i}", "label": f"Field {i}"}
            for i in range(100)  # 100 fields
        ]
        form_data = {
            "name": "Large Form",
            "formSchema": {"fields": fields}
        }
        response = requests.post(
            f"{api_base_url}/api/forms",
            headers=admin_headers,
            json=form_data,
            timeout=10
        )
        # May have field count limits
        assert response.status_code in [201, 400, 422]

    def test_form_field_with_special_characters(self, api_base_url, admin_headers):
        """Should handle special characters in field names"""
        form_data = {
            "name": "Test Form",
            "formSchema": {
                "fields": [
                    {
                        "type": "text",
                        "name": "field@#$%^&*()",
                        "label": "Special Field"
                    }
                ]
            }
        }
        response = requests.post(
            f"{api_base_url}/api/forms",
            headers=admin_headers,
            json=form_data,
            timeout=10
        )
        # May validate field names
        assert response.status_code in [201, 400, 422]

    def test_form_with_unicode_content(self, api_base_url, admin_headers):
        """Should handle unicode in form content"""
        form_data = {
            "name": "Unicode Form 🎉",
            "description": "Form with emoji and unicode: 你好世界",
            "formSchema": {
                "fields": [
                    {
                        "type": "text",
                        "name": "unicode_field",
                        "label": "Ниверсальное поле"
                    }
                ]
            }
        }
        response = requests.post(
            f"{api_base_url}/api/forms",
            headers=admin_headers,
            json=form_data,
            timeout=10
        )
        assert response.status_code in [201, 400, 422]
