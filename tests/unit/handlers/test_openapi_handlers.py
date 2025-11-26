"""
Unit tests for OpenAPI handlers

Tests the OpenAPI schema generation business logic including:
- Pydantic model collection
- Python type to OpenAPI type mapping
- Workflow parameter and request body generation
- Workflow operation definition building
- Dynamic endpoint generation
- Security scheme configuration
"""

import json
import yaml
from unittest.mock import Mock, patch

from shared.handlers.openapi_handlers import (
    collect_pydantic_models,
    map_python_type_to_openapi,
    build_workflow_parameters,
    build_workflow_request_body,
    build_workflow_operation,
    generate_workflow_endpoints,
    ensure_security_schemes,
    generate_openapi_spec,
)


class TestCollectPydanticModels:
    """Test Pydantic model collection"""

    def test_collect_models_returns_list(self):
        """Should return a list of model classes"""
        models = collect_pydantic_models()

        assert isinstance(models, list)
        assert len(models) > 0

    def test_collect_models_includes_shared_models(self):
        """Should include models from shared.models"""
        models = collect_pydantic_models()
        model_names = [m.__name__ for m in models]

        # Should include at least one shared model
        assert len([n for n in model_names if 'Error' in n or 'Execution' in n]) > 0

    def test_collect_models_includes_metadata_response(self):
        """Should include MetadataResponse which contains data provider metadata"""
        models = collect_pydantic_models()
        model_names = [m.__name__ for m in models]

        assert 'MetadataResponse' in model_names

    def test_all_collected_models_are_basemodel_subclasses(self):
        """All collected models should be Pydantic BaseModel subclasses"""
        from pydantic import BaseModel

        models = collect_pydantic_models()

        for model in models:
            assert isinstance(model, type)
            assert issubclass(model, BaseModel)


class TestMapPythonTypeToOpenAPI:
    """Test Python to OpenAPI type mapping"""

    def test_map_int_to_integer(self):
        """Should map 'int' to 'integer'"""
        assert map_python_type_to_openapi('int') == 'integer'

    def test_map_integer_to_integer(self):
        """Should map 'integer' to 'integer'"""
        assert map_python_type_to_openapi('integer') == 'integer'

    def test_map_bool_to_boolean(self):
        """Should map 'bool' to 'boolean'"""
        assert map_python_type_to_openapi('bool') == 'boolean'

    def test_map_float_to_number(self):
        """Should map 'float' to 'number'"""
        assert map_python_type_to_openapi('float') == 'number'

    def test_map_unknown_to_string(self):
        """Should map unknown types to 'string'"""
        assert map_python_type_to_openapi('string') == 'string'
        assert map_python_type_to_openapi('unknown') == 'string'
        assert map_python_type_to_openapi('custom') == 'string'


class TestBuildWorkflowParameters:
    """Test workflow parameter building"""

    def test_build_parameters_returns_list(self):
        """Should return a list of parameter objects"""
        mock_param = Mock()
        mock_param.name = "test_param"
        mock_param.type = "string"
        mock_param.required = True
        mock_param.help_text = "Test parameter"

        mock_metadata = Mock()
        mock_metadata.parameters = [mock_param]

        parameters = build_workflow_parameters(mock_metadata)

        assert isinstance(parameters, list)
        assert len(parameters) == 1

    def test_build_parameters_includes_required_fields(self):
        """Parameter definitions should include required fields"""
        mock_param = Mock()
        mock_param.name = "test_param"
        mock_param.type = "int"
        mock_param.required = True
        mock_param.help_text = "Test parameter"

        mock_metadata = Mock()
        mock_metadata.parameters = [mock_param]

        parameters = build_workflow_parameters(mock_metadata)
        param = parameters[0]

        assert "name" in param
        assert "in" in param
        assert "required" in param
        assert "description" in param
        assert "schema" in param

    def test_build_parameters_sets_query_location(self):
        """Parameters should be located in query"""
        mock_param = Mock()
        mock_param.name = "test_param"
        mock_param.type = "string"
        mock_param.required = False
        mock_param.help_text = None

        mock_metadata = Mock()
        mock_metadata.parameters = [mock_param]

        parameters = build_workflow_parameters(mock_metadata)

        assert parameters[0]["in"] == "query"

    def test_build_parameters_maps_types_correctly(self):
        """Should map Python types to OpenAPI types correctly"""
        params_config = [
            ("int", "integer"),
            ("bool", "boolean"),
            ("float", "number"),
            ("string", "string"),
        ]

        for python_type, expected_openapi_type in params_config:
            mock_param = Mock()
            mock_param.name = "param"
            mock_param.type = python_type
            mock_param.required = False
            mock_param.help_text = None

            mock_metadata = Mock()
            mock_metadata.parameters = [mock_param]

            parameters = build_workflow_parameters(mock_metadata)

            assert parameters[0]["schema"]["type"] == expected_openapi_type

    def test_build_parameters_multiple_parameters(self):
        """Should handle multiple parameters correctly"""
        mock_param1 = Mock()
        mock_param1.name = "param1"
        mock_param1.type = "string"
        mock_param1.required = True
        mock_param1.help_text = "First parameter"

        mock_param2 = Mock()
        mock_param2.name = "param2"
        mock_param2.type = "int"
        mock_param2.required = False
        mock_param2.help_text = "Second parameter"

        mock_metadata = Mock()
        mock_metadata.parameters = [mock_param1, mock_param2]

        parameters = build_workflow_parameters(mock_metadata)

        assert len(parameters) == 2
        assert parameters[0]["name"] == "param1"
        assert parameters[1]["name"] == "param2"


class TestBuildWorkflowRequestBody:
    """Test workflow request body building"""

    def test_build_request_body_returns_none_for_no_params(self):
        """Should return None when no parameters exist"""
        mock_metadata = Mock()
        mock_metadata.parameters = []

        request_body = build_workflow_request_body(mock_metadata)

        assert request_body is None

    def test_build_request_body_returns_dict_for_params(self):
        """Should return dict structure for parameters"""
        mock_param = Mock()
        mock_param.name = "test_param"
        mock_param.type = "string"
        mock_param.required = True

        mock_metadata = Mock()
        mock_metadata.parameters = [mock_param]

        request_body = build_workflow_request_body(mock_metadata)

        assert isinstance(request_body, dict)
        assert "content" in request_body
        assert "application/json" in request_body["content"]

    def test_build_request_body_includes_schema(self):
        """Request body should include JSON schema"""
        mock_param = Mock()
        mock_param.name = "test_param"
        mock_param.type = "int"
        mock_param.required = False

        mock_metadata = Mock()
        mock_metadata.parameters = [mock_param]

        request_body = build_workflow_request_body(mock_metadata)
        schema = request_body["content"]["application/json"]["schema"]

        assert schema["type"] == "object"
        assert "properties" in schema
        assert "test_param" in schema["properties"]

    def test_build_request_body_marks_required_fields(self):
        """Should mark required fields in schema"""
        mock_param1 = Mock()
        mock_param1.name = "required_param"
        mock_param1.type = "string"
        mock_param1.required = True

        mock_param2 = Mock()
        mock_param2.name = "optional_param"
        mock_param2.type = "string"
        mock_param2.required = False

        mock_metadata = Mock()
        mock_metadata.parameters = [mock_param1, mock_param2]

        request_body = build_workflow_request_body(mock_metadata)
        schema = request_body["content"]["application/json"]["schema"]

        assert "required" in schema
        assert "required_param" in schema["required"]
        assert "optional_param" not in schema["required"]


class TestBuildWorkflowOperation:
    """Test workflow operation building"""

    def test_build_operation_returns_dict(self):
        """Should return operation object as dict"""
        mock_metadata = Mock()
        mock_metadata.name = "test_workflow"
        mock_metadata.description = "Test workflow description"
        mock_metadata.parameters = []
        mock_metadata.allowed_methods = ['POST']

        operation = build_workflow_operation(mock_metadata, 'POST')

        assert isinstance(operation, dict)

    def test_build_operation_includes_required_fields(self):
        """Operation should include all required OpenAPI fields"""
        mock_metadata = Mock()
        mock_metadata.name = "test_workflow"
        mock_metadata.description = "Test workflow description"
        mock_metadata.parameters = []
        mock_metadata.allowed_methods = ['POST']

        operation = build_workflow_operation(mock_metadata, 'POST')

        required_fields = [
            'summary', 'description', 'tags', 'operationId',
            'parameters', 'security', 'responses'
        ]
        for field in required_fields:
            assert field in operation

    def test_build_operation_sets_security_bearer(self):
        """Should set BearerAuth security requirement"""
        mock_metadata = Mock()
        mock_metadata.name = "test_workflow"
        mock_metadata.description = "Test"
        mock_metadata.parameters = []
        mock_metadata.allowed_methods = ['POST']

        operation = build_workflow_operation(mock_metadata, 'POST')

        assert "BearerAuth" in operation["security"][0]

    def test_build_operation_includes_success_response(self):
        """Should include 200 success response with proper schema"""
        mock_metadata = Mock()
        mock_metadata.name = "test_workflow"
        mock_metadata.description = "Test"
        mock_metadata.parameters = []
        mock_metadata.allowed_methods = ['POST']

        operation = build_workflow_operation(mock_metadata, 'POST')

        assert "200" in operation["responses"]
        response_200 = operation["responses"]["200"]
        assert "description" in response_200
        assert "content" in response_200
        assert "application/json" in response_200["content"]

    def test_build_operation_response_schema_has_execution_fields(self):
        """Response schema should include execution result fields"""
        mock_metadata = Mock()
        mock_metadata.name = "test_workflow"
        mock_metadata.description = "Test"
        mock_metadata.parameters = []
        mock_metadata.allowed_methods = ['POST']

        operation = build_workflow_operation(mock_metadata, 'POST')

        schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
        properties = schema["properties"]

        expected_fields = [
            "executionId", "status", "result", "durationMs",
            "startedAt", "completedAt"
        ]
        for field in expected_fields:
            assert field in properties

    def test_build_operation_includes_error_responses(self):
        """Should include error response codes"""
        mock_metadata = Mock()
        mock_metadata.name = "test_workflow"
        mock_metadata.description = "Test"
        mock_metadata.parameters = []
        mock_metadata.allowed_methods = ['POST']

        operation = build_workflow_operation(mock_metadata, 'POST')
        responses = operation["responses"]

        expected_error_codes = ["400", "401", "404", "405", "500"]
        for code in expected_error_codes:
            assert code in responses

    def test_build_operation_post_includes_request_body(self):
        """POST operation with parameters should include request body"""
        mock_param = Mock()
        mock_param.name = "param1"
        mock_param.type = "string"
        mock_param.required = True

        mock_metadata = Mock()
        mock_metadata.name = "test_workflow"
        mock_metadata.description = "Test"
        mock_metadata.parameters = [mock_param]
        mock_metadata.allowed_methods = ['POST']

        operation = build_workflow_operation(mock_metadata, 'POST')

        assert "requestBody" in operation

    def test_build_operation_get_excludes_request_body(self):
        """GET operation should not include request body"""
        mock_param = Mock()
        mock_param.name = "param1"
        mock_param.type = "string"
        mock_param.required = True

        mock_metadata = Mock()
        mock_metadata.name = "test_workflow"
        mock_metadata.description = "Test"
        mock_metadata.parameters = [mock_param]
        mock_metadata.allowed_methods = ['GET']

        operation = build_workflow_operation(mock_metadata, 'GET')

        # GET should not have request body
        assert "requestBody" not in operation or not operation.get("requestBody")


class TestGenerateWorkflowEndpoints:
    """Test workflow endpoint generation"""

    def test_generate_workflow_endpoints_initializes_paths(self):
        """Should initialize paths if not present"""
        spec = {}

        with patch('shared.handlers.openapi_handlers.scan_all_workflows') as mock_scan:
            mock_scan.return_value = []

            generate_workflow_endpoints(spec)

            assert "paths" in spec

    def test_generate_workflow_endpoints_preserves_existing_paths(self):
        """Should preserve existing paths in spec"""
        spec = {"paths": {"/existing": {"get": {}}}}

        with patch('shared.handlers.openapi_handlers.scan_all_workflows') as mock_scan:
            mock_scan.return_value = []

            generate_workflow_endpoints(spec)

            assert "/existing" in spec["paths"]

    def test_generate_workflow_endpoints_adds_enabled_workflows(self):
        """Should add paths for enabled workflows only"""
        spec = {"paths": {}}

        mock_workflow1 = Mock()
        mock_workflow1.endpoint_enabled = True
        mock_workflow1.name = "workflow1"
        mock_workflow1.allowed_methods = ['POST']
        mock_workflow1.parameters = []
        mock_workflow1.description = "Workflow 1"

        mock_workflow2 = Mock()
        mock_workflow2.endpoint_enabled = False
        mock_workflow2.name = "workflow2"

        with patch('shared.handlers.openapi_handlers.scan_all_workflows') as mock_scan:
            mock_scan.return_value = [mock_workflow1, mock_workflow2]

            generate_workflow_endpoints(spec)

            assert "/endpoints/workflow1" in spec["paths"]
            assert "/endpoints/workflow2" not in spec["paths"]

    def test_generate_workflow_endpoints_adds_methods_for_workflow(self):
        """Should add HTTP methods for each workflow"""
        spec = {"paths": {}}

        mock_workflow = Mock()
        mock_workflow.endpoint_enabled = True
        mock_workflow.name = "test_workflow"
        mock_workflow.allowed_methods = ['GET', 'POST']
        mock_workflow.parameters = []
        mock_workflow.description = "Test workflow"

        with patch('shared.handlers.openapi_handlers.scan_all_workflows') as mock_scan:
            mock_scan.return_value = [mock_workflow]

            generate_workflow_endpoints(spec)

            path = spec["paths"]["/endpoints/test_workflow"]
            assert "get" in path
            assert "post" in path


class TestEnsureSecuritySchemes:
    """Test security scheme configuration"""

    def test_ensure_security_schemes_initializes_components(self):
        """Should initialize components if not present"""
        spec = {}

        ensure_security_schemes(spec)

        assert "components" in spec

    def test_ensure_security_schemes_initializes_security_schemes(self):
        """Should initialize securitySchemes if not present"""
        spec = {"components": {}}

        ensure_security_schemes(spec)

        assert "securitySchemes" in spec["components"]

    def test_ensure_security_schemes_adds_bearer_auth(self):
        """Should add BearerAuth scheme"""
        spec = {}

        ensure_security_schemes(spec)

        assert "BearerAuth" in spec["components"]["securitySchemes"]

    def test_bearer_auth_has_required_fields(self):
        """BearerAuth scheme should have required fields"""
        spec = {}

        ensure_security_schemes(spec)

        bearer = spec["components"]["securitySchemes"]["BearerAuth"]

        assert bearer["type"] == "http"
        assert bearer["scheme"] == "bearer"
        assert bearer["bearerFormat"] == "JWT"
        assert "description" in bearer


class TestGenerateOpenAPISpec:
    """Test complete OpenAPI spec generation"""

    def test_generate_openapi_spec_returns_dict(self):
        """Should generate OpenAPI spec as dictionary"""
        spec = generate_openapi_spec()

        assert isinstance(spec, dict)
        assert "openapi" in spec

    def test_generate_openapi_spec_includes_info(self):
        """Should include info section"""
        spec = generate_openapi_spec()

        assert "info" in spec
        assert "title" in spec["info"]
        assert "version" in spec["info"]
        assert "Bifrost Integrations" in spec["info"]["title"]

    def test_generate_openapi_spec_includes_servers(self):
        """Should include servers configuration"""
        spec = generate_openapi_spec()

        assert "servers" in spec
        assert isinstance(spec["servers"], list)
        assert len(spec["servers"]) >= 2

    def test_generate_openapi_spec_includes_paths(self):
        """Should include paths section"""
        spec = generate_openapi_spec()

        assert "paths" in spec

    def test_generate_openapi_spec_includes_components(self):
        """Should include components section"""
        spec = generate_openapi_spec()

        assert "components" in spec
        assert "schemas" in spec["components"]
        assert "securitySchemes" in spec["components"]

    def test_generate_openapi_spec_includes_bearer_auth(self):
        """Should configure BearerAuth security scheme"""
        spec = generate_openapi_spec()

        bearer = spec["components"]["securitySchemes"]["BearerAuth"]
        assert bearer["type"] == "http"
        assert bearer["scheme"] == "bearer"

    def test_generate_openapi_spec_includes_models(self):
        """Should include Pydantic model schemas"""
        spec = generate_openapi_spec()

        schemas = spec["components"]["schemas"]
        assert len(schemas) > 0

    def test_generate_openapi_spec_is_json_serializable(self):
        """Generated spec should be JSON serializable"""
        spec = generate_openapi_spec()

        # Should not raise an exception
        json_str = json.dumps(spec)
        assert isinstance(json_str, str)

        # Should be able to parse back
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    def test_generate_openapi_spec_is_yaml_serializable(self):
        """Generated spec should be YAML serializable"""
        spec = generate_openapi_spec()

        # Should not raise an exception
        yaml_str = yaml.dump(spec, sort_keys=False)
        assert isinstance(yaml_str, str)

        # Should be able to parse back
        parsed = yaml.safe_load(yaml_str)
        assert isinstance(parsed, dict)
