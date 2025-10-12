"""
OpenAPI/Swagger Endpoint
Serves the auto-generated OpenAPI spec at /api/openapi.json and /api/openapi.yaml
Also provides Swagger UI at /api/docs
"""

from generate_openapi import generate_openapi_spec
import azure.functions as func
import json
import yaml
from typing import Type
from pydantic import BaseModel
from enum import Enum

# Import the generator logic
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

bp = func.Blueprint()


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
    html = f"""
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
            window.onload = function() {{
                SwaggerUIBundle({{
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
                }})
            }}
        </script>
    </body>
    </html>
    """

    return func.HttpResponse(
        html,
        status_code=200,
        mimetype="text/html"
    )
