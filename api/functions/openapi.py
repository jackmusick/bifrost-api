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
