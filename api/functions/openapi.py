"""
OpenAPI/Swagger Endpoint
Serves the auto-generated OpenAPI spec at /api/openapi.json and /api/openapi.yaml
Also provides Swagger UI at /api/docs
"""

import json

import azure.functions as func
import yaml
from pydantic import BaseModel

import models.oauth_connection as oauth_models
import shared.models as models_module
from shared.openapi_decorators import build_openapi_spec

bp = func.Blueprint()


def generate_openapi_spec() -> dict:
    """
    Generate OpenAPI 3.0 spec using decorator registry + Pydantic models.

    Returns:
        dict: OpenAPI specification
    """

    # Import all endpoint modules to ensure decorators are executed
    # This triggers the @openapi_endpoint decorators and populates the registry
    # Import engine endpoints (now unified in functions/)

    # Import data provider models
    from functions.data_providers import DataProviderListResponse

    # Auto-collect all models from shared.models.__all__
    # This ensures we never forget to add new models to the spec!
    models: list[type[BaseModel]] = []

    # Add all models from shared.models (auto-discovered from __all__)
    for name in models_module.__all__:
        obj = getattr(models_module, name)
        # Only include BaseModel subclasses (skip regular classes, enums, and functions)
        if isinstance(obj, type) and issubclass(obj, BaseModel):
            models.append(obj)

    # Add OAuth models (auto-discovered from __all__)
    for name in oauth_models.__all__:
        obj = getattr(oauth_models, name)
        # Only include BaseModel subclasses
        if isinstance(obj, type) and issubclass(obj, BaseModel):
            models.append(obj)

    # Add Data Provider models
    models.append(DataProviderListResponse)

    # Build spec using decorator system
    spec = build_openapi_spec(
        title='Bifrost Integrations - Management API',
        version='1.0.0',
        description='API for managing forms, organizations, permissions, and users. Auto-generated from decorators and Pydantic models.',
        servers=[
            {
                'url': 'http://localhost:7071',
                'description': 'Local development server'
            },
            {
                'url': 'https://{environment}.azurewebsites.net',
                'description': 'Azure deployment',
                'variables': {
                    'environment': {
                        'default': 'msp-automation-api-dev',
                        'enum': ['msp-automation-api-dev', 'msp-automation-api-prod']
                    }
                }
            }
        ],
        models=models
    )

    # ==================== GENERATE DYNAMIC WORKFLOW ENDPOINTS ====================
    # Add endpoint definitions for enabled workflows to the OpenAPI spec
    from shared.registry import get_registry

    registry = get_registry()

    # Initialize paths if not present
    if "paths" not in spec:
        spec["paths"] = {}

    # Generate endpoint paths for each enabled workflow
    for metadata in registry.get_all_workflows():
        # Skip workflows that aren't enabled as endpoints
        if not metadata.endpoint_enabled:
            continue

        # Get allowed methods for this workflow
        allowed_methods = metadata.allowed_methods or ['POST']
        workflow_name = metadata.name

        # Create path entry if not already present (might be from decorator)
        path_key = f"/endpoints/{workflow_name}"
        if path_key not in spec["paths"]:
            spec["paths"][path_key] = {}

        # Add definition for each allowed HTTP method
        for method in allowed_methods:
            method_lower = method.lower()

            # Build parameter list from workflow parameters
            parameters = []

            # Add query parameters for all workflow parameters
            for param in metadata.parameters:
                param_name = param.name
                param_type = param.type
                param_required = param.required
                param_description = param.help_text or f"{param_name} parameter"

                # Map Python types to OpenAPI types
                openapi_type = 'string'
                if param_type in ['int', 'integer']:
                    openapi_type = 'integer'
                elif param_type == 'bool':
                    openapi_type = 'boolean'
                elif param_type == 'float':
                    openapi_type = 'number'

                # For GET requests, always use query parameters
                # For POST/PUT/DELETE, add as query parameters as well (body is merged)
                param_in = 'query'

                parameters.append({
                    "name": param_name,
                    "in": param_in,
                    "required": param_required,
                    "description": param_description,
                    "schema": {
                        "type": openapi_type
                    }
                })

            # Build request body schema for POST/PUT methods
            request_body = None
            if method_lower in ['post', 'put']:
                # For POST/PUT, parameters can also come from JSON body
                properties = {}
                required_fields = []

                for param in getattr(metadata, 'parameters', []):
                    param_name = getattr(param, 'name', None)
                    param_type = getattr(param, 'type', 'string')
                    param_required = getattr(param, 'required', False)

                    openapi_type = 'string'
                    if param_type in ['int', 'integer']:
                        openapi_type = 'integer'
                    elif param_type == 'bool':
                        openapi_type = 'boolean'
                    elif param_type == 'float':
                        openapi_type = 'number'

                    properties[param_name] = {"type": openapi_type}

                    if param_required:
                        required_fields.append(param_name)

                if properties:
                    request_body = {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": properties,
                                    "required": required_fields if required_fields else None
                                }
                            }
                        }
                    }

            # Build operation definition
            operation = {
                "summary": f"{method.upper()} {workflow_name}",
                "description": getattr(metadata, 'description', f"Execute {workflow_name} workflow via HTTP endpoint"),
                "tags": ["Workflow Endpoints"],
                "operationId": f"execute_workflow_endpoint_{workflow_name}_{method_lower}",
                "parameters": parameters if parameters else [],
                "security": [{"BearerAuth": []}],
                "responses": {
                    "200": {
                        "description": "Workflow executed successfully",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "executionId": {"type": "string"},
                                        "status": {"type": "string"},
                                        "result": {"type": "object"},
                                        "durationMs": {"type": "integer"},
                                        "startedAt": {"type": "string", "format": "date-time"},
                                        "completedAt": {"type": "string", "format": "date-time"}
                                    }
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "Bad request (invalid input or validation errors)"
                    },
                    "401": {
                        "description": "Unauthorized (invalid or missing API key)"
                    },
                    "404": {
                        "description": "Endpoint not found or not enabled"
                    },
                    "405": {
                        "description": f"Method not allowed (only {', '.join(allowed_methods)} allowed for this endpoint)"
                    },
                    "500": {
                        "description": "Server error"
                    }
                }
            }

            # Add request body if present
            if request_body:
                operation["requestBody"] = request_body

            # Add the operation to the spec
            spec["paths"][path_key][method_lower] = operation

    # Ensure security schemes are defined for API key auth
    if "components" not in spec:
        spec["components"] = {}
    if "securitySchemes" not in spec["components"]:
        spec["components"]["securitySchemes"] = {}

    spec["components"]["securitySchemes"]["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "API key for workflow endpoint access. Use format: Authorization: Bearer <api_key>"
    }

    return spec


@bp.route(route="openapi.json", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def get_openapi_json(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get OpenAPI spec as JSON

    Usage: GET /api/openapi.json
    """
    spec = generate_openapi_spec()

    return func.HttpResponse(
        json.dumps(spec, indent=2),
        status_code=200,
        mimetype="application/json",
        headers={
            "Access-Control-Allow-Origin": "*",  # Allow CORS for local dev
        }
    )


@bp.route(route="openapi.yaml", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def get_openapi_yaml(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get OpenAPI spec as YAML

    Usage: GET /api/openapi.yaml
    """
    spec = generate_openapi_spec()
    yaml_output = yaml.dump(
        spec,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=120
    )

    return func.HttpResponse(
        yaml_output,
        status_code=200,
        mimetype="application/x-yaml",
        headers={
            "Access-Control-Allow-Origin": "*",  # Allow CORS for local dev
        }
    )


@bp.route(route="docs", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def swagger_ui(req: func.HttpRequest) -> func.HttpResponse:
    """
    Swagger UI for interactive API documentation

    Usage: GET /api/docs
    """
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Bifrost Integrations - API Documentation</title>
        <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
        <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
        <script>
            window.onload = function() {
                SwaggerUIBundle({
                    url: "/api/openapi.json",
                    dom_id: '#swagger-ui',
                    deepLinking: true,
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIStandalonePreset
                    ],
                    plugins: [
                        SwaggerUIBundle.plugins.DownloadUrl
                    ],
                    layout: "StandaloneLayout"
                })
            }
        </script>
    </body>
    </html>
    """

    return func.HttpResponse(
        html,
        status_code=200,
        mimetype="text/html"
    )
