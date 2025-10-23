"""
Contract tests for Enhanced Forms API (User Story 1 & 2)
Tests Pydantic validation for form context, query parameters, visibility, and rich components
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from shared.models import (
    CreateFormRequest,
    DataProviderInputConfig,
    DataProviderInputMode,
    FileUploadRequest,
    FileUploadResponse,
    Form,
    FormField,
    FormFieldType,
    FormSchema,
)




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


class TestDataProviderInputsValidation:
    """T020: Contract test for POST /api/forms with dataProviderInputs validation"""

    def test_form_field_with_static_data_provider_inputs(self):
        """
        Test that FormField with dataProvider and dataProviderInputs validates correctly.

        Expected behavior:
        - dataProviderInputs is optional when dataProvider is set
        - Each input config must have valid mode (static, fieldRef, expression)
        - Static mode requires 'value' field
        - Input keys should match data provider parameter names
        """
        # Valid form field with data provider and static inputs
        field = FormField(
            name="repo_selector",
            label="Select Repository",
            type=FormFieldType.SELECT,
            required=True,
            dataProvider="get_github_repos",
            dataProviderInputs={
                "token": DataProviderInputConfig(
                    mode=DataProviderInputMode.STATIC,
                    value="ghp_test_token_12345"
                ),
                "org": DataProviderInputConfig(
                    mode=DataProviderInputMode.STATIC,
                    value="my-org"
                )
            }
        )

        assert field.dataProvider == "get_github_repos"
        assert field.dataProviderInputs is not None
        assert len(field.dataProviderInputs) == 2
        assert field.dataProviderInputs["token"].mode == DataProviderInputMode.STATIC
        assert field.dataProviderInputs["token"].value == "ghp_test_token_12345"
        assert field.dataProviderInputs["org"].mode == DataProviderInputMode.STATIC
        assert field.dataProviderInputs["org"].value == "my-org"

    def test_data_provider_inputs_without_data_provider_fails(self):
        """
        Test that dataProviderInputs cannot be set without dataProvider.

        Expected behavior:
        - Setting dataProviderInputs without dataProvider should raise ValidationError
        """
        with pytest.raises(ValidationError) as exc_info:
            FormField(
                name="invalid_field",
                label="Invalid Field",
                type=FormFieldType.SELECT,
                required=False,
                # No dataProvider set!
                dataProviderInputs={
                    "param": DataProviderInputConfig(
                        mode=DataProviderInputMode.STATIC,
                        value="test"
                    )
                }
            )

        errors = exc_info.value.errors()
        assert any("dataProviderInputs requires dataProvider" in str(e.get("ctx", {}).get("error", "")) for e in errors)

    def test_static_input_mode_validation(self):
        """
        Test that static mode requires 'value' field and rejects other fields.

        Expected behavior:
        - mode="static" requires 'value' to be set
        - mode="static" should reject 'fieldName' or 'expression'
        """
        # Valid static mode
        config = DataProviderInputConfig(
            mode=DataProviderInputMode.STATIC,
            value="test_value"
        )
        assert config.mode == DataProviderInputMode.STATIC
        assert config.value == "test_value"
        assert config.fieldName is None
        assert config.expression is None

        # Invalid: static mode without value
        with pytest.raises(ValidationError) as exc_info:
            DataProviderInputConfig(
                mode=DataProviderInputMode.STATIC
                # Missing value!
            )
        assert any("value required for static mode" in str(e) for e in exc_info.value.errors())

        # Invalid: static mode with fieldName
        with pytest.raises(ValidationError) as exc_info:
            DataProviderInputConfig(
                mode=DataProviderInputMode.STATIC,
                value="test",
                fieldName="other_field"  # Should not be set for static mode
            )
        assert any("only value should be set for static mode" in str(e) for e in exc_info.value.errors())

    def test_complete_form_with_data_provider_inputs(self):
        """
        Test complete form creation with data provider inputs in multiple fields.

        Expected behavior:
        - Form can have multiple fields with dataProviderInputs
        - Each field's inputs are independent
        - Form validation passes with valid dataProviderInputs
        """
        request = CreateFormRequest(
            name="Form with Data Provider Inputs",
            linkedWorkflow="workflows.process_repo_selection",
            formSchema=FormSchema(
                fields=[
                    FormField(
                        name="github_token",
                        label="GitHub Token",
                        type=FormFieldType.TEXT,
                        required=True
                    ),
                    FormField(
                        name="repository",
                        label="Select Repository",
                        type=FormFieldType.SELECT,
                        required=True,
                        dataProvider="get_github_repos",
                        dataProviderInputs={
                            "token": DataProviderInputConfig(
                                mode=DataProviderInputMode.STATIC,
                                value="ghp_static_token"
                            )
                        }
                    ),
                    FormField(
                        name="branch",
                        label="Select Branch",
                        type=FormFieldType.SELECT,
                        required=True,
                        dataProvider="get_github_branches",
                        dataProviderInputs={
                            "token": DataProviderInputConfig(
                                mode=DataProviderInputMode.STATIC,
                                value="ghp_static_token"
                            ),
                            "repo": DataProviderInputConfig(
                                mode=DataProviderInputMode.STATIC,
                                value="my-org/my-repo"
                            )
                        }
                    )
                ]
            )
        )

        assert len(request.formSchema.fields) == 3

        # First field has no data provider
        assert request.formSchema.fields[0].dataProvider is None
        assert request.formSchema.fields[0].dataProviderInputs is None

        # Second field has data provider with 1 input
        assert request.formSchema.fields[1].dataProvider == "get_github_repos"
        assert len(request.formSchema.fields[1].dataProviderInputs) == 1
        assert "token" in request.formSchema.fields[1].dataProviderInputs

        # Third field has data provider with 2 inputs
        assert request.formSchema.fields[2].dataProvider == "get_github_branches"
        assert len(request.formSchema.fields[2].dataProviderInputs) == 2
        assert "token" in request.formSchema.fields[2].dataProviderInputs
        assert "repo" in request.formSchema.fields[2].dataProviderInputs
