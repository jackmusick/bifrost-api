"""
Contract tests for Forms API models
Tests Pydantic validation rules for request/response models
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from shared.models import (
    Form,
    CreateFormRequest,
    UpdateFormRequest,
    FormSchema,
    FormField,
    FormFieldType,
    ErrorResponse
)


class TestCreateFormRequest:
    """Test validation for CreateFormRequest model"""

    def test_valid_create_form_request(self):
        """Test valid create form request"""
        request = CreateFormRequest(
            name="Customer Onboarding",
            linkedWorkflow="workflows.onboarding.customer_onboarding",
            formSchema=FormSchema(
                fields=[
                    FormField(
                        name="company_name",
                        label="Company Name",
                        type=FormFieldType.TEXT,
                        required=True
                    )
                ]
            )
        )
        assert request.name == "Customer Onboarding"
        assert request.linkedWorkflow == "workflows.onboarding.customer_onboarding"
        assert len(request.formSchema.fields) == 1
        assert request.isGlobal is False  # Default

    def test_create_form_with_global_flag(self):
        """Test creating a global form"""
        request = CreateFormRequest(
            name="Global Template",
            linkedWorkflow="workflows.templates.global_template",
            formSchema=FormSchema(fields=[]),
            isGlobal=True
        )
        assert request.isGlobal is True

    def test_create_form_with_description(self):
        """Test creating form with optional description"""
        request = CreateFormRequest(
            name="Test Form",
            linkedWorkflow="workflows.test",
            formSchema=FormSchema(fields=[]),
            description="This is a test form"
        )
        assert request.description == "This is a test form"

    def test_missing_required_name(self):
        """Test that name is required"""
        with pytest.raises(ValidationError) as exc_info:
            CreateFormRequest(
                linkedWorkflow="workflows.test",
                formSchema=FormSchema(fields=[])
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) and e["type"] == "missing" for e in errors)

    def test_missing_required_linked_workflow(self):
        """Test that linkedWorkflow is required"""
        with pytest.raises(ValidationError) as exc_info:
            CreateFormRequest(
                name="Test Form",
                formSchema=FormSchema(fields=[])
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("linkedWorkflow",) and e["type"] == "missing" for e in errors)

    def test_missing_required_form_schema(self):
        """Test that formSchema is required"""
        with pytest.raises(ValidationError) as exc_info:
            CreateFormRequest(
                name="Test Form",
                linkedWorkflow="workflows.test"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("formSchema",) and e["type"] == "missing" for e in errors)


class TestUpdateFormRequest:
    """Test validation for UpdateFormRequest model"""

    def test_valid_update_form_request_all_fields(self):
        """Test valid update form request with all fields"""
        request = UpdateFormRequest(
            name="Updated Form",
            description="Updated description",
            linkedWorkflow="workflows.updated",
            formSchema=FormSchema(
                fields=[
                    FormField(
                        name="field1",
                        label="Field 1",
                        type=FormFieldType.TEXT,
                        required=True
                    )
                ]
            )
        )
        assert request.name == "Updated Form"
        assert request.description == "Updated description"

    def test_update_form_request_partial(self):
        """Test update with only some fields"""
        request = UpdateFormRequest(
            name="New Name"
        )
        assert request.name == "New Name"
        assert request.description is None
        assert request.linkedWorkflow is None
        assert request.formSchema is None

    def test_update_form_request_empty_valid(self):
        """Test that update request can be empty (all optional)"""
        request = UpdateFormRequest()
        assert request.name is None
        assert request.description is None
        assert request.linkedWorkflow is None
        assert request.formSchema is None


class TestFormSchema:
    """Test validation for FormSchema model"""

    def test_valid_form_schema_with_fields(self):
        """Test valid form schema with multiple fields"""
        schema = FormSchema(
            fields=[
                FormField(
                    name="field1",
                    label="Field 1",
                    type=FormFieldType.TEXT,
                    required=True
                ),
                FormField(
                    name="field2",
                    label="Field 2",
                    type=FormFieldType.NUMBER,
                    required=False
                )
            ]
        )
        assert len(schema.fields) == 2
        assert schema.fields[0].name == "field1"
        assert schema.fields[1].type == FormFieldType.NUMBER

    def test_empty_form_schema(self):
        """Test form schema with no fields"""
        schema = FormSchema(fields=[])
        assert len(schema.fields) == 0

    def test_missing_fields_array(self):
        """Test that fields array is required"""
        with pytest.raises(ValidationError) as exc_info:
            FormSchema()

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("fields",) and e["type"] == "missing" for e in errors)


class TestFormField:
    """Test validation for FormField model"""

    def test_valid_text_field(self):
        """Test valid text field"""
        field = FormField(
            name="company_name",
            label="Company Name",
            type=FormFieldType.TEXT,
            required=True
        )
        assert field.name == "company_name"
        assert field.label == "Company Name"
        assert field.type == FormFieldType.TEXT
        assert field.required is True

    def test_valid_number_field(self):
        """Test valid number field"""
        field = FormField(
            name="employee_count",
            label="Employee Count",
            type=FormFieldType.NUMBER,
            required=False
        )
        assert field.type == FormFieldType.NUMBER
        assert field.required is False

    def test_valid_email_field(self):
        """Test valid email field"""
        field = FormField(
            name="contact_email",
            label="Contact Email",
            type=FormFieldType.EMAIL,
            required=True
        )
        assert field.type == FormFieldType.EMAIL

    def test_valid_select_field(self):
        """Test valid select field"""
        field = FormField(
            name="region",
            label="Region",
            type=FormFieldType.SELECT,
            required=True
        )
        assert field.type == FormFieldType.SELECT

    def test_valid_textarea_field(self):
        """Test valid textarea field"""
        field = FormField(
            name="description",
            label="Description",
            type=FormFieldType.TEXTAREA,
            required=False
        )
        assert field.type == FormFieldType.TEXTAREA

    def test_field_with_validation(self):
        """Test field with validation object"""
        field = FormField(
            name="age",
            label="Age",
            type=FormFieldType.NUMBER,
            required=True,
            validation={"min": 0, "max": 120}
        )
        assert field.validation == {"min": 0, "max": 120}

    def test_field_with_data_provider(self):
        """Test field with dataProvider object"""
        field = FormField(
            name="organization",
            label="Organization",
            type=FormFieldType.SELECT,
            required=True,
            dataProvider={
                "type": "msgraph",
                "resource": "organizations",
                "valueField": "id",
                "labelField": "displayName"
            }
        )
        assert field.dataProvider["type"] == "msgraph"
        assert field.dataProvider["resource"] == "organizations"

    def test_field_defaults(self):
        """Test that optional fields have proper defaults"""
        field = FormField(
            name="test",
            label="Test",
            type=FormFieldType.TEXT
        )
        assert field.required is False  # Default
        assert field.validation is None
        assert field.dataProvider is None

    def test_missing_required_name(self):
        """Test that name is required"""
        with pytest.raises(ValidationError) as exc_info:
            FormField(
                label="Test",
                type=FormFieldType.TEXT
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) and e["type"] == "missing" for e in errors)

    def test_missing_required_label(self):
        """Test that label is required"""
        with pytest.raises(ValidationError) as exc_info:
            FormField(
                name="test",
                type=FormFieldType.TEXT
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("label",) and e["type"] == "missing" for e in errors)

    def test_missing_required_type(self):
        """Test that type is required"""
        with pytest.raises(ValidationError) as exc_info:
            FormField(
                name="test",
                label="Test"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("type",) and e["type"] == "missing" for e in errors)

    def test_invalid_field_type(self):
        """Test that type must be a valid enum value"""
        with pytest.raises(ValidationError) as exc_info:
            FormField(
                name="test",
                label="Test",
                type="invalid_type"
            )

        errors = exc_info.value.errors()
        assert any("type" in str(e) for e in errors)


class TestFormResponse:
    """Test Form response model structure"""

    def test_valid_form_response(self):
        """Test valid form response"""
        form = Form(
            id="form-123",
            orgId="org-456",
            name="Test Form",
            linkedWorkflow="workflows.test",
            formSchema=FormSchema(
                fields=[
                    FormField(
                        name="field1",
                        label="Field 1",
                        type=FormFieldType.TEXT,
                        required=True
                    )
                ]
            ),
            isActive=True,
            isGlobal=False,
            createdBy="user-789",
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )
        assert form.id == "form-123"
        assert form.orgId == "org-456"
        assert form.name == "Test Form"
        assert form.isActive is True
        assert form.isGlobal is False

    def test_form_response_with_description(self):
        """Test form response with optional description"""
        form = Form(
            id="form-123",
            orgId="org-456",
            name="Test Form",
            description="Test description",
            linkedWorkflow="workflows.test",
            formSchema=FormSchema(fields=[]),
            isActive=True,
            isGlobal=False,
            createdBy="user-789",
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )
        assert form.description == "Test description"

    def test_global_form_response(self):
        """Test global form response"""
        form = Form(
            id="form-123",
            orgId="GLOBAL",
            name="Global Form",
            linkedWorkflow="workflows.global",
            formSchema=FormSchema(fields=[]),
            isActive=True,
            isGlobal=True,
            createdBy="user-789",
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )
        assert form.orgId == "GLOBAL"
        assert form.isGlobal is True

    def test_form_defaults(self):
        """Test that form fields have proper defaults"""
        form = Form(
            id="form-123",
            orgId="org-456",
            name="Test Form",
            linkedWorkflow="workflows.test",
            formSchema=FormSchema(fields=[]),
            createdBy="user-789",
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )
        assert form.isActive is True  # Default
        assert form.isGlobal is False  # Default
        assert form.description is None

    def test_form_missing_required_fields(self):
        """Test that all required fields must be present"""
        with pytest.raises(ValidationError) as exc_info:
            Form(
                id="form-123",
                orgId="org-456",
                name="Test Form"
                # Missing: linkedWorkflow, formSchema, createdBy, createdAt, updatedAt
            )

        errors = exc_info.value.errors()
        required_fields = {"linkedWorkflow", "formSchema", "createdBy", "createdAt", "updatedAt"}
        missing_fields = {e["loc"][0] for e in errors if e["type"] == "missing"}
        assert required_fields.issubset(missing_fields)

    def test_form_serialization(self):
        """Test that form can be serialized to dict/JSON"""
        form = Form(
            id="form-123",
            orgId="org-456",
            name="Test Form",
            linkedWorkflow="workflows.test",
            formSchema=FormSchema(
                fields=[
                    FormField(
                        name="field1",
                        label="Field 1",
                        type=FormFieldType.TEXT,
                        required=True
                    )
                ]
            ),
            isActive=True,
            isGlobal=False,
            createdBy="user-789",
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )

        form_dict = form.model_dump()
        assert "id" in form_dict
        assert "orgId" in form_dict
        assert "name" in form_dict
        assert "linkedWorkflow" in form_dict
        assert "formSchema" in form_dict
        assert "isActive" in form_dict
        assert "isGlobal" in form_dict
        assert "createdBy" in form_dict
        assert "createdAt" in form_dict
        assert "updatedAt" in form_dict

    def test_form_json_serialization(self):
        """Test that form can be serialized to JSON mode"""
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
            updatedAt=datetime.utcnow()
        )

        form_dict = form.model_dump(mode="json")
        assert isinstance(form_dict["createdAt"], str)  # datetime -> ISO string
        assert isinstance(form_dict["updatedAt"], str)  # datetime -> ISO string
