"""
Contract tests for Enhanced Forms API (User Story 1 & 2)
Tests Pydantic validation for form context, query parameters, visibility, and rich components
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from shared.models import (
    CreateFormRequest,
    FileUploadRequest,
    FileUploadResponse,
    Form,
    FormField,
    FormFieldType,
    FormSchema,
    UpdateFormRequest,
)


# ==================== USER STORY 1: FORM CONTEXT TESTS ====================

class TestFormContextConfiguration:
    """Test validation for form context configuration (launch workflow and query params)"""

    def test_form_with_launch_workflow(self):
        """Test form configuration with launchWorkflowId"""
        request = CreateFormRequest(
            name="Dynamic Form",
            linkedWorkflow="workflows.process_form",
            formSchema=FormSchema(fields=[]),
            launchWorkflowId="workflows.load_context"
        )
        assert request.launchWorkflowId == "workflows.load_context"

    def test_form_without_launch_workflow(self):
        """Test that launchWorkflowId is optional"""
        request = CreateFormRequest(
            name="Static Form",
            linkedWorkflow="workflows.process_form",
            formSchema=FormSchema(fields=[])
        )
        assert request.launchWorkflowId is None

    def test_form_with_allowed_query_params(self):
        """Test form configuration with allowedQueryParams"""
        request = CreateFormRequest(
            name="URL Parameterized Form",
            linkedWorkflow="workflows.process_form",
            formSchema=FormSchema(fields=[]),
            allowedQueryParams=["customer_id", "project_id", "source"]
        )
        assert request.allowedQueryParams == ["customer_id", "project_id", "source"]
        assert len(request.allowedQueryParams) == 3

    def test_form_without_allowed_query_params(self):
        """Test that allowedQueryParams is optional"""
        request = CreateFormRequest(
            name="Simple Form",
            linkedWorkflow="workflows.process_form",
            formSchema=FormSchema(fields=[])
        )
        assert request.allowedQueryParams is None

    def test_form_with_empty_allowed_query_params(self):
        """Test form with empty allowedQueryParams list"""
        request = CreateFormRequest(
            name="No Params Form",
            linkedWorkflow="workflows.process_form",
            formSchema=FormSchema(fields=[]),
            allowedQueryParams=[]
        )
        assert request.allowedQueryParams == []

    def test_form_context_full_configuration(self):
        """Test form with both launch workflow and query params"""
        request = CreateFormRequest(
            name="Full Context Form",
            linkedWorkflow="workflows.process_form",
            formSchema=FormSchema(fields=[]),
            launchWorkflowId="workflows.load_context",
            allowedQueryParams=["customer_id", "ticket_id"]
        )
        assert request.launchWorkflowId == "workflows.load_context"
        assert request.allowedQueryParams == ["customer_id", "ticket_id"]

    def test_update_form_with_launch_workflow(self):
        """Test updating form with launchWorkflowId"""
        request = UpdateFormRequest(
            launchWorkflowId="workflows.new_context_loader"
        )
        assert request.launchWorkflowId == "workflows.new_context_loader"

    def test_update_form_with_allowed_query_params(self):
        """Test updating form with allowedQueryParams"""
        request = UpdateFormRequest(
            allowedQueryParams=["new_param1", "new_param2"]
        )
        assert request.allowedQueryParams == ["new_param1", "new_param2"]

    def test_form_response_includes_context_fields(self):
        """Test that Form response model includes context fields"""
        form = Form(
            id="form-123",
            orgId="org-456",
            name="Test Form",
            linkedWorkflow="workflows.test",
            formSchema=FormSchema(fields=[]),
            isActive=True,
            isGlobal=False,
            createdBy="user-789",
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow(),
            launchWorkflowId="workflows.load_context",
            allowedQueryParams=["customer_id"]
        )
        assert form.launchWorkflowId == "workflows.load_context"
        assert form.allowedQueryParams == ["customer_id"]


class TestFormFieldVisibility:
    """Test validation for form field visibility expressions"""

    def test_field_with_visibility_expression(self):
        """Test field with visibilityExpression"""
        field = FormField(
            name="conditional_field",
            label="Conditional Field",
            type=FormFieldType.TEXT,
            required=False,
            visibilityExpression="context.field.show_advanced === true"
        )
        assert field.visibilityExpression == "context.field.show_advanced === true"

    def test_field_without_visibility_expression(self):
        """Test that visibilityExpression is optional (always visible)"""
        field = FormField(
            name="always_visible",
            label="Always Visible",
            type=FormFieldType.TEXT,
            required=True
        )
        assert field.visibilityExpression is None

    def test_field_with_complex_visibility_expression(self):
        """Test field with complex boolean visibility expression"""
        field = FormField(
            name="complex_field",
            label="Complex Field",
            type=FormFieldType.TEXT,
            required=False,
            visibilityExpression="context.workflow.user_type === 'admin' && context.field.enable_advanced"
        )
        assert field.visibilityExpression == "context.workflow.user_type === 'admin' && context.field.enable_advanced"

    def test_field_with_query_param_visibility(self):
        """Test field visibility based on query parameters"""
        field = FormField(
            name="source_dependent_field",
            label="Source Dependent",
            type=FormFieldType.TEXT,
            required=False,
            visibilityExpression="context.query.source === 'crm'"
        )
        assert field.visibilityExpression == "context.query.source === 'crm'"

    def test_field_with_workflow_result_visibility(self):
        """Test field visibility based on workflow results"""
        field = FormField(
            name="license_field",
            label="License Field",
            type=FormFieldType.SELECT,
            required=False,
            visibilityExpression="context.workflow.has_available_licenses === true"
        )
        assert field.visibilityExpression == "context.workflow.has_available_licenses === true"


# ==================== USER STORY 2: RICH COMPONENT TESTS ====================

class TestMarkdownComponent:
    """Test validation for markdown component fields"""

    def test_markdown_field_type(self):
        """Test that MARKDOWN is a valid field type"""
        field = FormField(
            name="instructions",
            label="Instructions",
            type=FormFieldType.MARKDOWN,
            required=False
        )
        assert field.type == FormFieldType.MARKDOWN

    def test_markdown_field_with_content(self):
        """Test markdown field with static content"""
        markdown_content = "# Welcome\n\nThis is a **markdown** component."
        field = FormField(
            name="markdown_section",
            label="Markdown Section",
            type=FormFieldType.MARKDOWN,
            required=False,
            content=markdown_content
        )
        assert field.content == markdown_content
        assert field.type == FormFieldType.MARKDOWN

    def test_markdown_field_without_content(self):
        """Test that content is optional for markdown fields"""
        field = FormField(
            name="markdown_display",
            label="Markdown Display",
            type=FormFieldType.MARKDOWN,
            required=False
        )
        assert field.content is None


class TestHTMLComponent:
    """Test validation for HTML component fields"""

    def test_html_field_type(self):
        """Test that HTML is a valid field type"""
        field = FormField(
            name="html_section",
            label="HTML Section",
            type=FormFieldType.HTML,
            required=False
        )
        assert field.type == FormFieldType.HTML

    def test_html_field_with_content(self):
        """Test HTML field with static content"""
        html_content = "<h1>Hello ${context.field.name}!</h1><p>Status: ${context.workflow.status}</p>"
        field = FormField(
            name="html_display",
            label="HTML Display",
            type=FormFieldType.HTML,
            required=False,
            content=html_content
        )
        assert field.content == html_content
        assert field.type == FormFieldType.HTML

    def test_html_field_with_template_syntax(self):
        """Test HTML field supports ${} template interpolation syntax"""
        field = FormField(
            name="dynamic_html",
            label="Dynamic HTML",
            type=FormFieldType.HTML,
            required=False,
            content="<div>Welcome ${context.query.customer_name}</div>"
        )
        assert "${context.query.customer_name}" in field.content


class TestDateTimeComponent:
    """Test validation for date/time component fields"""

    def test_datetime_field_type(self):
        """Test that DATETIME is a valid field type"""
        field = FormField(
            name="scheduled_date",
            label="Scheduled Date",
            type=FormFieldType.DATETIME,
            required=True
        )
        assert field.type == FormFieldType.DATETIME

    def test_datetime_field_with_validation(self):
        """Test datetime field with validation rules"""
        field = FormField(
            name="start_date",
            label="Start Date",
            type=FormFieldType.DATETIME,
            required=True,
            validation={"min": "2024-01-01T00:00:00", "max": "2024-12-31T23:59:59"}
        )
        assert field.validation == {"min": "2024-01-01T00:00:00", "max": "2024-12-31T23:59:59"}

    def test_datetime_field_with_default_value(self):
        """Test datetime field with default value"""
        field = FormField(
            name="created_at",
            label="Created At",
            type=FormFieldType.DATETIME,
            required=False,
            defaultValue="2024-01-01T12:00:00Z"
        )
        assert field.defaultValue == "2024-01-01T12:00:00Z"


class TestRadioComponent:
    """Test validation for radio button component fields"""

    def test_radio_field_type(self):
        """Test that RADIO is a valid field type"""
        field = FormField(
            name="choice",
            label="Select One",
            type=FormFieldType.RADIO,
            required=True
        )
        assert field.type == FormFieldType.RADIO

    def test_radio_field_with_options(self):
        """Test radio field with options"""
        field = FormField(
            name="priority",
            label="Priority",
            type=FormFieldType.RADIO,
            required=True,
            options=[
                {"label": "Low", "value": "low"},
                {"label": "Medium", "value": "medium"},
                {"label": "High", "value": "high"}
            ]
        )
        assert field.options is not None
        assert len(field.options) == 3
        assert field.options[0] == {"label": "Low", "value": "low"}

    def test_radio_field_without_options(self):
        """Test that options is optional (can use data provider)"""
        field = FormField(
            name="status",
            label="Status",
            type=FormFieldType.RADIO,
            required=True,
            dataProvider="get_status_options"
        )
        assert field.options is None
        assert field.dataProvider == "get_status_options"

    def test_radio_field_with_default_value(self):
        """Test radio field with default selected value"""
        field = FormField(
            name="notification_pref",
            label="Notification Preference",
            type=FormFieldType.RADIO,
            required=False,
            options=[
                {"label": "Email", "value": "email"},
                {"label": "SMS", "value": "sms"}
            ],
            defaultValue="email"
        )
        assert field.defaultValue == "email"


class TestFileUploadComponent:
    """Test validation for file upload component fields and endpoints"""

    def test_file_field_type(self):
        """Test that FILE is a valid field type"""
        field = FormField(
            name="attachment",
            label="Upload File",
            type=FormFieldType.FILE,
            required=False
        )
        assert field.type == FormFieldType.FILE

    def test_file_field_with_allowed_types(self):
        """Test file field with allowedTypes restriction"""
        field = FormField(
            name="document",
            label="Upload Document",
            type=FormFieldType.FILE,
            required=True,
            allowedTypes=["application/pdf", "application/msword", "image/png"]
        )
        assert field.allowedTypes is not None
        assert len(field.allowedTypes) == 3
        assert "application/pdf" in field.allowedTypes

    def test_file_field_with_size_limit(self):
        """Test file field with maxSizeMB restriction"""
        field = FormField(
            name="large_file",
            label="Large File Upload",
            type=FormFieldType.FILE,
            required=False,
            maxSizeMB=100
        )
        assert field.maxSizeMB == 100

    def test_file_field_multiple_uploads(self):
        """Test file field with multiple upload support"""
        field = FormField(
            name="attachments",
            label="Upload Multiple Files",
            type=FormFieldType.FILE,
            required=False,
            multiple=True
        )
        assert field.multiple is True

    def test_file_field_single_upload_default(self):
        """Test that multiple defaults to None (single upload)"""
        field = FormField(
            name="single_file",
            label="Upload Single File",
            type=FormFieldType.FILE,
            required=False
        )
        assert field.multiple is None

    def test_file_field_full_configuration(self):
        """Test file field with all configuration options"""
        field = FormField(
            name="comprehensive_upload",
            label="Comprehensive Upload",
            type=FormFieldType.FILE,
            required=True,
            allowedTypes=["image/jpeg", "image/png", "image/gif"],
            multiple=True,
            maxSizeMB=50
        )
        assert field.allowedTypes == ["image/jpeg", "image/png", "image/gif"]
        assert field.multiple is True
        assert field.maxSizeMB == 50

    def test_file_field_without_restrictions(self):
        """Test file field with no type or size restrictions"""
        field = FormField(
            name="any_file",
            label="Upload Any File",
            type=FormFieldType.FILE,
            required=False
        )
        assert field.allowedTypes is None
        assert field.maxSizeMB is None
        assert field.multiple is None


class TestFileUploadAPI:
    """Test validation for FileUpload request/response models"""

    def test_valid_file_upload_request(self):
        """Test valid file upload SAS URL request"""
        request = FileUploadRequest(
            file_name="document.pdf",
            content_type="application/pdf",
            file_size=1048576  # 1 MB in bytes
        )
        assert request.file_name == "document.pdf"
        assert request.content_type == "application/pdf"
        assert request.file_size == 1048576

    def test_file_upload_request_large_file(self):
        """Test file upload request with large file (100MB)"""
        request = FileUploadRequest(
            file_name="large_video.mp4",
            content_type="video/mp4",
            file_size=104857600  # 100 MB in bytes
        )
        assert request.file_size == 104857600

    def test_file_upload_request_missing_fields(self):
        """Test that all FileUploadRequest fields are required"""
        with pytest.raises(ValidationError) as exc_info:
            FileUploadRequest(
                file_name="test.pdf"
                # Missing: content_type, file_size
            )

        errors = exc_info.value.errors()
        required_fields = {"content_type", "file_size"}
        missing_fields = {e["loc"][0] for e in errors if e["type"] == "missing"}
        assert required_fields.issubset(missing_fields)

    def test_valid_file_upload_response(self):
        """Test valid file upload SAS URL response"""
        response = FileUploadResponse(
            upload_url="https://storage.blob.core.windows.net/uploads/file.pdf?sas_token=xyz",
            blob_uri="https://storage.blob.core.windows.net/uploads/file.pdf",
            expires_at="2024-01-01T13:00:00Z"
        )
        assert "sas_token" in response.upload_url
        assert response.blob_uri == "https://storage.blob.core.windows.net/uploads/file.pdf"
        assert response.expires_at == "2024-01-01T13:00:00Z"

    def test_file_upload_response_missing_fields(self):
        """Test that all FileUploadResponse fields are required"""
        with pytest.raises(ValidationError) as exc_info:
            FileUploadResponse(
                upload_url="https://storage.blob.core.windows.net/uploads/file.pdf"
                # Missing: blob_uri, expires_at
            )

        errors = exc_info.value.errors()
        required_fields = {"blob_uri", "expires_at"}
        missing_fields = {e["loc"][0] for e in errors if e["type"] == "missing"}
        assert required_fields.issubset(missing_fields)


# ==================== COMBINED INTEGRATION TESTS ====================

class TestEnhancedFormIntegration:
    """Test complete enhanced form configuration with all new features"""

    def test_form_with_all_new_field_types(self):
        """Test form schema with all new component types"""
        schema = FormSchema(
            fields=[
                FormField(
                    name="markdown_intro",
                    label="Introduction",
                    type=FormFieldType.MARKDOWN,
                    required=False,
                    content="# Welcome\nPlease fill out the form below."
                ),
                FormField(
                    name="html_banner",
                    label="Banner",
                    type=FormFieldType.HTML,
                    required=False,
                    content="<div class='banner'>Hello ${context.field.name}!</div>"
                ),
                FormField(
                    name="appointment_date",
                    label="Appointment Date",
                    type=FormFieldType.DATETIME,
                    required=True
                ),
                FormField(
                    name="priority",
                    label="Priority",
                    type=FormFieldType.RADIO,
                    required=True,
                    options=[
                        {"label": "Low", "value": "low"},
                        {"label": "High", "value": "high"}
                    ]
                ),
                FormField(
                    name="attachments",
                    label="Attachments",
                    type=FormFieldType.FILE,
                    required=False,
                    multiple=True,
                    allowedTypes=["application/pdf", "image/png"],
                    maxSizeMB=10
                )
            ]
        )
        assert len(schema.fields) == 5
        assert schema.fields[0].type == FormFieldType.MARKDOWN
        assert schema.fields[1].type == FormFieldType.HTML
        assert schema.fields[2].type == FormFieldType.DATETIME
        assert schema.fields[3].type == FormFieldType.RADIO
        assert schema.fields[4].type == FormFieldType.FILE

    def test_form_with_context_and_visibility(self):
        """Test form with launch workflow, query params, and field visibility"""
        request = CreateFormRequest(
            name="Advanced Dynamic Form",
            linkedWorkflow="workflows.process_advanced_form",
            formSchema=FormSchema(
                fields=[
                    FormField(
                        name="customer_type",
                        label="Customer Type",
                        type=FormFieldType.SELECT,
                        required=True
                    ),
                    FormField(
                        name="enterprise_options",
                        label="Enterprise Options",
                        type=FormFieldType.TEXT,
                        required=False,
                        visibilityExpression="context.field.customer_type === 'enterprise'"
                    ),
                    FormField(
                        name="available_licenses",
                        label="Available Licenses",
                        type=FormFieldType.SELECT,
                        required=False,
                        visibilityExpression="context.workflow.has_licenses === true",
                        dataProvider="get_available_licenses"
                    )
                ]
            ),
            launchWorkflowId="workflows.load_customer_context",
            allowedQueryParams=["customer_id", "source"]
        )
        assert request.launchWorkflowId == "workflows.load_customer_context"
        assert request.allowedQueryParams == ["customer_id", "source"]
        assert len(request.formSchema.fields) == 3
        assert request.formSchema.fields[1].visibilityExpression == "context.field.customer_type === 'enterprise'"
        assert request.formSchema.fields[2].visibilityExpression == "context.workflow.has_licenses === true"

    def test_complete_form_response_with_enhancements(self):
        """Test Form response model with all enhanced features"""
        form = Form(
            id="form-enhanced-123",
            orgId="org-456",
            name="Enhanced Form",
            description="Form with all new features",
            linkedWorkflow="workflows.process_enhanced",
            formSchema=FormSchema(
                fields=[
                    FormField(
                        name="markdown_section",
                        label="Instructions",
                        type=FormFieldType.MARKDOWN,
                        required=False,
                        content="## Instructions\nPlease complete all required fields."
                    ),
                    FormField(
                        name="date_field",
                        label="Select Date",
                        type=FormFieldType.DATETIME,
                        required=True,
                        visibilityExpression="context.query.requires_date === 'true'"
                    ),
                    FormField(
                        name="file_upload",
                        label="Upload Files",
                        type=FormFieldType.FILE,
                        required=False,
                        multiple=True,
                        allowedTypes=["application/pdf"],
                        maxSizeMB=50
                    )
                ]
            ),
            isActive=True,
            isGlobal=False,
            createdBy="user-789",
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow(),
            launchWorkflowId="workflows.context_loader",
            allowedQueryParams=["customer_id", "requires_date"]
        )

        # Verify all enhanced features are preserved
        assert form.launchWorkflowId == "workflows.context_loader"
        assert form.allowedQueryParams == ["customer_id", "requires_date"]
        assert len(form.formSchema.fields) == 3

        # Verify new field types
        assert form.formSchema.fields[0].type == FormFieldType.MARKDOWN
        assert form.formSchema.fields[1].type == FormFieldType.DATETIME
        assert form.formSchema.fields[2].type == FormFieldType.FILE

        # Verify field-specific features
        assert form.formSchema.fields[0].content is not None
        assert form.formSchema.fields[1].visibilityExpression is not None
        assert form.formSchema.fields[2].multiple is True
        assert form.formSchema.fields[2].allowedTypes == ["application/pdf"]
        assert form.formSchema.fields[2].maxSizeMB == 50
