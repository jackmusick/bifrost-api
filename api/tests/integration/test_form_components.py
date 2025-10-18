"""
Integration tests for Rich Form Components (User Story 2)
Tests component rendering, validation, and data submission with file uploads
"""


import pytest

from functions.file_uploads import generate_file_upload_url
from functions.forms import create_form
from tests.helpers.http_helpers import (
    create_mock_request,
    create_platform_admin_headers,
    parse_response,
)


class TestFileUploadComponent:
    """Test file upload component end-to-end workflow"""

    @pytest.mark.asyncio
    async def test_generate_upload_url_for_form(self, test_platform_admin_user):
        """Test requesting SAS URL for file upload"""
        # Create a form with file upload field first
        create_req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            body={
                "name": "Form with File Upload",
                "linkedWorkflow": "workflows.process_submission",
                "formSchema": {
                    "fields": [
                        {
                            "name": "document",
                            "label": "Upload Document",
                            "type": "file",
                            "required": True,
                            "allowedTypes": ["application/pdf", "image/png"],
                            "maxSizeMB": 10,
                            "multiple": False
                        }
                    ]
                }
            }
        )

        create_resp = await create_form(create_req)
        assert create_resp.status_code == 201
        status_code, form_data = parse_response(create_resp)
        form_id = form_data["id"]

        # Request SAS URL for file upload
        upload_req = create_mock_request(
            method="POST",
            url=f"/api/forms/{form_id}/files/upload-url",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            route_params={"formId": form_id},
            body={
                "file_name": "test_document.pdf",
                "content_type": "application/pdf",
                "file_size": 1024000  # 1MB
            }
        )

        upload_resp = await generate_file_upload_url(upload_req)
        assert upload_resp.status_code == 200

        status_code, upload_data = parse_response(upload_resp)
        assert "upload_url" in upload_data
        assert "blob_uri" in upload_data
        assert "expires_at" in upload_data

        # Verify blob_uri contains the file name
        assert "test_document.pdf" in upload_data["blob_uri"] or ".pdf" in upload_data["blob_uri"]

    @pytest.mark.asyncio
    async def test_file_size_limit_validation(self, test_platform_admin_user):
        """Test file size validation (max 100MB)"""
        # Try to upload a file larger than 100MB
        upload_req = create_mock_request(
            method="POST",
            url="/api/forms/test-form/files/upload-url",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            route_params={"formId": "test-form"},
            body={
                "file_name": "huge_file.pdf",
                "content_type": "application/pdf",
                "file_size": 110 * 1024 * 1024  # 110MB (exceeds limit)
            }
        )

        upload_resp = await generate_file_upload_url(upload_req)

        # Should reject with 400 Bad Request
        assert upload_resp.status_code == 400
        status_code, error_data = parse_response(upload_resp)
        assert "error" in error_data


class TestRichComponentRendering:
    """Test markdown, HTML, datetime, radio components in forms"""

    @pytest.mark.asyncio
    async def test_form_with_markdown_component(self, test_platform_admin_user):
        """Test creating and retrieving form with markdown field"""
        req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            body={
                "name": "Form with Markdown",
                "linkedWorkflow": "workflows.process_submission",
                "formSchema": {
                    "fields": [
                        {
                            "name": "instructions",
                            "label": "Instructions",
                            "type": "markdown",
                            "content": "# Welcome\\n\\nPlease fill out the form below.\\n\\n- Step 1\\n- Step 2"
                        },
                        {
                            "name": "user_name",
                            "label": "Name",
                            "type": "text",
                            "required": True
                        }
                    ]
                }
            }
        )

        resp = await create_form(req)
        assert resp.status_code == 201

        status_code, form_data = parse_response(resp)
        assert form_data["formSchema"]["fields"][0]["type"] == "markdown"
        assert "# Welcome" in form_data["formSchema"]["fields"][0]["content"]

    @pytest.mark.asyncio
    async def test_form_with_html_component(self, test_platform_admin_user):
        """Test creating form with HTML interpolation field"""
        req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            body={
                "name": "Form with HTML",
                "linkedWorkflow": "workflows.process_submission",
                # No launch workflow - just testing HTML component storage
                "formSchema": {
                    "fields": [
                        {
                            "name": "welcome_message",
                            "label": "Welcome",
                            "type": "html",
                            "content": "<div>Welcome, {context.workflow.user_name}!</div>"
                        }
                    ]
                }
            }
        )

        resp = await create_form(req)
        assert resp.status_code == 201

        status_code, form_data = parse_response(resp)
        html_field = form_data["formSchema"]["fields"][0]
        assert html_field["type"] == "html"
        assert "context.workflow" in html_field["content"]

    @pytest.mark.asyncio
    async def test_form_with_datetime_component(self, test_platform_admin_user):
        """Test creating form with datetime picker"""
        req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            body={
                "name": "Form with DateTime",
                "linkedWorkflow": "workflows.schedule_task",
                "formSchema": {
                    "fields": [
                        {
                            "name": "scheduled_time",
                            "label": "Schedule For",
                            "type": "datetime",
                            "required": True
                        }
                    ]
                }
            }
        )

        resp = await create_form(req)
        assert resp.status_code == 201

        status_code, form_data = parse_response(resp)
        assert form_data["formSchema"]["fields"][0]["type"] == "datetime"

    @pytest.mark.asyncio
    async def test_form_with_radio_component(self, test_platform_admin_user):
        """Test creating form with radio button group"""
        req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            body={
                "name": "Form with Radio",
                "linkedWorkflow": "workflows.process_selection",
                "formSchema": {
                    "fields": [
                        {
                            "name": "priority",
                            "label": "Priority Level",
                            "type": "radio",
                            "required": True,
                            "options": [
                                {"label": "Low", "value": "low"},
                                {"label": "Medium", "value": "medium"},
                                {"label": "High", "value": "high"}
                            ]
                        }
                    ]
                }
            }
        )

        resp = await create_form(req)
        assert resp.status_code == 201

        status_code, form_data = parse_response(resp)
        radio_field = form_data["formSchema"]["fields"][0]
        assert radio_field["type"] == "radio"
        assert len(radio_field["options"]) == 3
        assert radio_field["options"][0]["label"] == "Low"

    @pytest.mark.asyncio
    async def test_form_with_multiple_rich_components(self, test_platform_admin_user):
        """Test form combining multiple rich component types"""
        req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            body={
                "name": "Complex Form",
                "linkedWorkflow": "workflows.onboard_user",
                # No launch workflow - just testing component storage
                "formSchema": {
                    "fields": [
                        {
                            "name": "intro",
                            "label": "Introduction",
                            "type": "markdown",
                            "content": "# User Onboarding\\n\\nFill out the form to create a new user."
                        },
                        {
                            "name": "license_info",
                            "label": "Available Licenses",
                            "type": "html",
                            "content": "<p>Licenses available: {context.workflow.license_count}</p>"
                        },
                        {
                            "name": "user_type",
                            "label": "User Type",
                            "type": "radio",
                            "required": True,
                            "options": [
                                {"label": "Standard", "value": "standard"},
                                {"label": "Admin", "value": "admin"}
                            ]
                        },
                        {
                            "name": "start_date",
                            "label": "Start Date",
                            "type": "datetime",
                            "required": True
                        },
                        {
                            "name": "profile_photo",
                            "label": "Profile Photo",
                            "type": "file",
                            "allowedTypes": ["image/jpeg", "image/png"],
                            "maxSizeMB": 5
                        }
                    ]
                }
            }
        )

        resp = await create_form(req)
        assert resp.status_code == 201

        status_code, form_data = parse_response(resp)
        fields = form_data["formSchema"]["fields"]

        # Verify all component types are present
        field_types = [f["type"] for f in fields]
        assert "markdown" in field_types
        assert "html" in field_types
        assert "radio" in field_types
        assert "datetime" in field_types
        assert "file" in field_types
