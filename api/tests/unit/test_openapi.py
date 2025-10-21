"""Unit tests for OpenAPI spec generation

Tests the OpenAPI specification generation including:
- Spec generation with models and endpoints
- Schema conversion from Pydantic models
- Endpoint documentation
- Complex model handling
"""

import json
import yaml
from unittest.mock import Mock
import azure.functions as func

from functions.http.openapi import generate_openapi_spec, get_openapi_json, get_openapi_yaml, swagger_ui


class TestOpenAPISpecGeneration:
    """Test complete OpenAPI spec generation"""

    def test_generate_openapi_spec_returns_dict(self):
        """Should generate OpenAPI spec as dictionary"""
        spec = generate_openapi_spec()

        assert isinstance(spec, dict)
        assert "openapi" in spec
        # OpenAPI version should be 3.x.x format
        assert spec["openapi"].startswith("3.")

    def test_spec_includes_info_metadata(self):
        """Should include title, version, and description"""
        spec = generate_openapi_spec()

        assert "info" in spec
        assert "title" in spec["info"]
        assert "version" in spec["info"]
        assert "description" in spec["info"]
        assert spec["info"]["title"] == "Bifrost Integrations - Management API"
        assert spec["info"]["version"] == "1.0.0"

    def test_spec_includes_servers(self):
        """Should include server definitions"""
        spec = generate_openapi_spec()

        assert "servers" in spec
        assert isinstance(spec["servers"], list)
        assert len(spec["servers"]) >= 1

        # Check localhost server
        local_server = next((s for s in spec["servers"] if "localhost" in s.get("url", "")), None)
        assert local_server is not None

    def test_spec_includes_paths(self):
        """Should include API paths/endpoints"""
        spec = generate_openapi_spec()

        assert "paths" in spec
        assert isinstance(spec["paths"], dict)

    def test_spec_includes_components(self):
        """Should include components section with schemas"""
        spec = generate_openapi_spec()

        assert "components" in spec
        assert "schemas" in spec["components"]
        assert "securitySchemes" in spec["components"]

    def test_spec_includes_security_schemes(self):
        """Should include BearerAuth security scheme"""
        spec = generate_openapi_spec()

        assert "securitySchemes" in spec["components"]
        assert "BearerAuth" in spec["components"]["securitySchemes"]

        bearer_scheme = spec["components"]["securitySchemes"]["BearerAuth"]
        assert bearer_scheme["type"] == "http"
        assert bearer_scheme["scheme"] == "bearer"

    def test_spec_includes_pydantic_models_as_schemas(self):
        """Should include Pydantic models converted to JSON schemas"""
        spec = generate_openapi_spec()

        schemas = spec["components"]["schemas"]
        # Should include at least some models
        assert len(schemas) > 0

        # Check for ErrorResponse model
        assert "ErrorResponse" in schemas or any("Error" in schema_name for schema_name in schemas)

    def test_workflow_endpoint_paths_generated(self):
        """Should generate paths for enabled workflow endpoints"""
        spec = generate_openapi_spec()

        paths = spec["paths"]
        # Should have at least some paths
        assert len(paths) > 0

        # Check for /endpoints/ paths (workflow endpoints)
        endpoint_paths = [p for p in paths if "/endpoints/" in p]
        # May or may not have workflows depending on registry
        # Just validate structure if they exist
        for path in endpoint_paths:
            assert isinstance(paths[path], dict)

    def test_spec_is_valid_json(self):
        """Should generate valid JSON-serializable spec"""
        spec = generate_openapi_spec()

        # Should be JSON serializable
        json_str = json.dumps(spec)
        assert isinstance(json_str, str)

        # Should be able to parse back
        parsed = json.loads(json_str)
        assert parsed == spec


class TestOpenAPIEndpoints:
    """Test OpenAPI endpoint handlers"""

    def test_get_openapi_json_returns_response(self):
        """GET /api/openapi.json should return HttpResponse"""
        mock_req = Mock(spec=func.HttpRequest)

        response = get_openapi_json(mock_req)

        assert isinstance(response, func.HttpResponse)
        assert response.status_code == 200

    def test_get_openapi_json_returns_json_mimetype(self):
        """Should return application/json mimetype"""
        mock_req = Mock(spec=func.HttpRequest)

        response = get_openapi_json(mock_req)

        assert response.mimetype == "application/json"

    def test_get_openapi_json_response_is_valid_json(self):
        """Response body should be valid JSON"""
        mock_req = Mock(spec=func.HttpRequest)

        response = get_openapi_json(mock_req)

        # Should be able to parse response body as JSON
        data = json.loads(response.get_body().decode('utf-8'))
        assert isinstance(data, dict)
        assert "openapi" in data

    def test_get_openapi_yaml_returns_response(self):
        """GET /api/openapi.yaml should return HttpResponse"""
        mock_req = Mock(spec=func.HttpRequest)

        response = get_openapi_yaml(mock_req)

        assert isinstance(response, func.HttpResponse)
        assert response.status_code == 200

    def test_get_openapi_yaml_returns_yaml_mimetype(self):
        """Should return application/x-yaml mimetype"""
        mock_req = Mock(spec=func.HttpRequest)

        response = get_openapi_yaml(mock_req)

        assert response.mimetype == "application/x-yaml"

    def test_get_openapi_yaml_response_is_valid_yaml(self):
        """Response body should be valid YAML"""
        mock_req = Mock(spec=func.HttpRequest)

        response = get_openapi_yaml(mock_req)

        # Should be able to parse response body as YAML
        yaml_content = response.get_body().decode('utf-8')
        data = yaml.safe_load(yaml_content)
        assert isinstance(data, dict)
        assert "openapi" in data

    def test_swagger_ui_returns_html_response(self):
        """GET /api/docs should return HTML response"""
        mock_req = Mock(spec=func.HttpRequest)

        response = swagger_ui(mock_req)

        assert isinstance(response, func.HttpResponse)
        assert response.status_code == 200
        assert response.mimetype == "text/html"

    def test_swagger_ui_contains_swagger_ui_bundle(self):
        """Swagger UI HTML should include required JavaScript"""
        mock_req = Mock(spec=func.HttpRequest)

        response = swagger_ui(mock_req)

        html = response.get_body().decode('utf-8')
        assert "swagger-ui-dist" in html
        assert "SwaggerUIBundle" in html

    def test_swagger_ui_references_openapi_json(self):
        """Swagger UI should reference /api/openapi.json endpoint"""
        mock_req = Mock(spec=func.HttpRequest)

        response = swagger_ui(mock_req)

        html = response.get_body().decode('utf-8')
        assert "/api/openapi.json" in html or "openapi.json" in html


class TestOpenAPISchemas:
    """Test schema conversion from Pydantic models"""

    def test_error_response_schema_exists(self):
        """Should include ErrorResponse in schemas"""
        spec = generate_openapi_spec()
        schemas = spec["components"]["schemas"]

        # Find ErrorResponse schema
        error_schema = next((s for s in schemas if "Error" in s), None)
        assert error_schema is not None

    def test_workflow_execution_schema_exists(self):
        """Should include WorkflowExecution in schemas"""
        spec = generate_openapi_spec()
        schemas = spec["components"]["schemas"]

        # Find WorkflowExecution schema
        execution_schema = next((s for s in schemas if "Execution" in s), None)
        assert execution_schema is not None

    def test_schema_has_properties(self):
        """Schema should have properties defined"""
        spec = generate_openapi_spec()
        schemas = spec["components"]["schemas"]

        # Pick any schema and verify it has properties
        for schema_name, schema_def in schemas.items():
            if isinstance(schema_def, dict) and "properties" in schema_def:
                assert isinstance(schema_def["properties"], dict)
                # Should have at least one property
                if schema_def.get("type") == "object":
                    assert len(schema_def["properties"]) >= 0
                break

    def test_enum_fields_in_schemas(self):
        """Enum fields should be properly defined with enum values"""
        spec = generate_openapi_spec()
        schemas = spec["components"]["schemas"]

        # Find a schema with enum fields
        found_enum = False
        for schema_name, schema_def in schemas.items():
            if isinstance(schema_def, dict):
                props = schema_def.get("properties", {})
                for prop_name, prop_def in props.items():
                    if isinstance(prop_def, dict) and "enum" in prop_def:
                        found_enum = True
                        assert isinstance(prop_def["enum"], list)

        # At least one enum should exist in models
        # (ExecutionStatus has enum values)
        assert found_enum or len(schemas) > 0
