"""
Contract Tests for Enhanced Data Provider Models
Tests for T017-T019: Data provider parameters and input validation
These are Pydantic model validation tests, NOT API endpoint tests
"""

import pytest
from pydantic import ValidationError

from shared.models import (
    DataProviderInputMode,
    DataProviderInputConfig,
    DataProviderRequest,
    FormField,
    FormFieldType,
)


class TestDataProviderInputConfigContract:
    """T017-T019: Contract tests for DataProviderInputConfig model"""

    def test_static_mode_valid(self):
        """
        T019: Test valid static mode configuration

        Expected behavior:
        - mode="static" requires 'value' field
        - Other fields (fieldName, expression) must be None
        """
        config = DataProviderInputConfig(
            mode=DataProviderInputMode.STATIC,
            value="test_value"
        )

        assert config.mode == DataProviderInputMode.STATIC
        assert config.value == "test_value"
        assert config.fieldName is None
        assert config.expression is None

    def test_static_mode_without_value_fails(self):
        """
        T019: Test that static mode requires value field

        Expected behavior:
        - Missing 'value' in static mode raises ValidationError
        """
        with pytest.raises(ValidationError) as exc_info:
            DataProviderInputConfig(
                mode=DataProviderInputMode.STATIC
                # Missing value!
            )

        errors = exc_info.value.errors()
        assert any("value required for static mode" in str(e) for e in errors)

    def test_static_mode_with_extra_fields_fails(self):
        """
        T019: Test that static mode rejects fieldName and expression

        Expected behavior:
        - Setting fieldName or expression in static mode raises ValidationError
        """
        with pytest.raises(ValidationError) as exc_info:
            DataProviderInputConfig(
                mode=DataProviderInputMode.STATIC,
                value="test",
                fieldName="other_field"  # Should not be set for static mode
            )

        errors = exc_info.value.errors()
        assert any("only value should be set for static mode" in str(e) for e in errors)

    def test_fieldref_mode_valid(self):
        """Test valid fieldRef mode configuration"""
        config = DataProviderInputConfig(
            mode=DataProviderInputMode.FIELD_REF,
            fieldName="other_field"
        )

        assert config.mode == DataProviderInputMode.FIELD_REF
        assert config.fieldName == "other_field"
        assert config.value is None
        assert config.expression is None

    def test_fieldref_mode_without_fieldname_fails(self):
        """Test that fieldRef mode requires fieldName"""
        with pytest.raises(ValidationError) as exc_info:
            DataProviderInputConfig(
                mode=DataProviderInputMode.FIELD_REF
                # Missing fieldName!
            )

        errors = exc_info.value.errors()
        assert any("fieldName required for fieldRef mode" in str(e) for e in errors)

    def test_expression_mode_valid(self):
        """Test valid expression mode configuration"""
        config = DataProviderInputConfig(
            mode=DataProviderInputMode.EXPRESSION,
            expression="context.field.first_name + ' ' + context.field.last_name"
        )

        assert config.mode == DataProviderInputMode.EXPRESSION
        assert config.expression == "context.field.first_name + ' ' + context.field.last_name"
        assert config.value is None
        assert config.fieldName is None

    def test_expression_mode_without_expression_fails(self):
        """Test that expression mode requires expression"""
        with pytest.raises(ValidationError) as exc_info:
            DataProviderInputConfig(
                mode=DataProviderInputMode.EXPRESSION
                # Missing expression!
            )

        errors = exc_info.value.errors()
        assert any("expression required for expression mode" in str(e) for e in errors)


class TestDataProviderRequestContract:
    """T018: Contract tests for DataProviderRequest model"""

    def test_data_provider_request_with_inputs(self):
        """
        T018: Test DataProviderRequest accepts inputs object

        Expected behavior:
        - inputs field is optional
        - inputs can be a dict mapping parameter names to values
        - orgId is optional
        """
        request = DataProviderRequest(
            orgId="test-org-123",
            inputs={
                "token": "ghp_test_token",
                "org": "my-org",
                "filter": "active"
            }
        )

        assert request.orgId == "test-org-123"
        assert request.inputs is not None
        assert len(request.inputs) == 3
        assert request.inputs["token"] == "ghp_test_token"
        assert request.inputs["org"] == "my-org"
        assert request.inputs["filter"] == "active"

    def test_data_provider_request_without_inputs(self):
        """
        T018: Test DataProviderRequest with no inputs (backward compatibility)

        Expected behavior:
        - inputs field can be None
        - Request is still valid
        """
        request = DataProviderRequest(
            orgId="test-org-123"
            # No inputs field
        )

        assert request.orgId == "test-org-123"
        assert request.inputs is None

    def test_data_provider_request_empty_inputs(self):
        """Test DataProviderRequest with empty inputs dict"""
        request = DataProviderRequest(
            orgId="test-org-123",
            inputs={}  # Empty dict
        )

        assert request.orgId == "test-org-123"
        assert request.inputs == {}

    def test_data_provider_request_no_org_id(self):
        """Test DataProviderRequest without orgId (for global providers)"""
        request = DataProviderRequest(
            inputs={"param": "value"}
        )

        assert request.orgId is None
        assert request.inputs == {"param": "value"}


class TestFormFieldDataProviderInputsContract:
    """T020: Contract tests for FormField.dataProviderInputs"""

    def test_form_field_with_data_provider_inputs(self):
        """
        T020: Test FormField with dataProvider and dataProviderInputs

        Expected behavior:
        - dataProviderInputs can be set when dataProvider is set
        - Each input config must be valid DataProviderInputConfig
        """
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

    def test_data_provider_inputs_without_data_provider_fails(self):
        """
        T020: Test that dataProviderInputs requires dataProvider

        Expected behavior:
        - Setting dataProviderInputs without dataProvider raises ValidationError
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
        # The error comes from our custom validator
        assert any("dataProviderInputs requires dataProvider" in str(e) for e in errors)

    def test_data_provider_without_inputs_is_valid(self):
        """
        Test that dataProvider can be set without dataProviderInputs (backward compatibility)

        Expected behavior:
        - dataProvider without dataProviderInputs is valid
        - This supports providers with no required parameters
        """
        field = FormField(
            name="license_selector",
            label="Select License",
            type=FormFieldType.SELECT,
            required=True,
            dataProvider="get_available_licenses"
            # No dataProviderInputs
        )

        assert field.dataProvider == "get_available_licenses"
        assert field.dataProviderInputs is None

    def test_mixed_input_modes_in_single_field(self):
        """
        Test FormField with multiple dataProviderInputs using different modes

        Expected behavior:
        - One field can have multiple inputs with different modes
        - Each input is validated independently
        """
        field = FormField(
            name="complex_field",
            label="Complex Field",
            type=FormFieldType.SELECT,
            required=True,
            dataProvider="get_complex_data",
            dataProviderInputs={
                "static_param": DataProviderInputConfig(
                    mode=DataProviderInputMode.STATIC,
                    value="static_value"
                ),
                "field_param": DataProviderInputConfig(
                    mode=DataProviderInputMode.FIELD_REF,
                    fieldName="other_field"
                ),
                "expr_param": DataProviderInputConfig(
                    mode=DataProviderInputMode.EXPRESSION,
                    expression="context.field.a + context.field.b"
                )
            }
        )

        assert len(field.dataProviderInputs) == 3
        assert field.dataProviderInputs["static_param"].mode == DataProviderInputMode.STATIC
        assert field.dataProviderInputs["field_param"].mode == DataProviderInputMode.FIELD_REF
        assert field.dataProviderInputs["expr_param"].mode == DataProviderInputMode.EXPRESSION
