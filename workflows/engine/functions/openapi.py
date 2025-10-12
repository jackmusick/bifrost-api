"""
OpenAPI and Swagger UI endpoints for Workflow Engine
"""

import azure.functions as func
import json
import yaml

from engine.functions.openapi_generator import generate_openapi_spec

bp = func.Blueprint()


@bp.route(route="openapi.json", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def get_openapi_json(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/openapi.json
    Returns the OpenAPI specification in JSON format.
    """
    spec = generate_openapi_spec()

    return func.HttpResponse(
        json.dumps(spec, indent=2),
        status_code=200,
        mimetype="application/json",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        }
    )


@bp.route(route="openapi.yaml", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def get_openapi_yaml(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/openapi.yaml
    Returns the OpenAPI specification in YAML format.
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
        mimetype="text/yaml",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        }
    )


@bp.route(route="docs", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def get_swagger_ui(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/docs
    Returns Swagger UI for interactive API documentation.
    """
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Workflow Engine API - Swagger UI</title>
        <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui.css">
        <style>
            body { margin: 0; padding: 0; }
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-bundle.js"></script>
        <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-standalone-preset.js"></script>
        <script>
            window.onload = function() {
                window.ui = SwaggerUIBundle({
                    url: '/api/openapi.json',
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
                });
            };
        </script>
    </body>
    </html>
    """

    return func.HttpResponse(
        html,
        status_code=200,
        mimetype="text/html",
        headers={
            "Access-Control-Allow-Origin": "*"
        }
    )
