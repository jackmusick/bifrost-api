import azure.functions as func
import json
import logging
import os

# T033-T034: Install import restrictions BEFORE importing workspace code
from engine.shared.import_restrictor import install_import_restrictions

# Calculate workspace path
WORKSPACE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'workspace')

# Install import restrictions to prevent workspace code from importing engine internals
install_import_restrictions([WORKSPACE_PATH])

# Now safe to import workspace code - restrictions are active
import workspace.workflows

# Import engine data providers to trigger auto-discovery
import engine.data_providers

from engine.admin.metadata import bp as metadata_bp
from engine.execute import bp as execute_bp
from engine.functions.data_provider_api import bp as data_provider_bp
from engine.functions.openapi import bp as openapi_bp

app = func.FunctionApp(http_auth_level=func.AuthLevel.ADMIN)

# Register blueprints
app.register_functions(metadata_bp)
app.register_functions(execute_bp)
app.register_functions(data_provider_bp)
app.register_functions(openapi_bp)  # OpenAPI/Swagger endpoints

@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Health check endpoint called")
    return func.HttpResponse(
        json.dumps({"status": "healthy", "service": "Workflow Engine"}),
        mimetype="application/json"
    )

@app.route(route="registry/workflows", methods=["GET"])
def admin_workflow(req: func.HttpRequest) -> func.HttpResponse:
    # Will be populated by decorator registry
    # Optional query parameter: ?type=workflows or ?type=options
    workflow_type = req.params.get('type')

    logging.info(f"Admin workflow endpoint called with type={workflow_type}")

    response_data = {
        "workflows": [],
        "option_generators": []
    }

    # Filter by type if specified
    if workflow_type == 'workflows':
        response_data = {"workflows": response_data["workflows"]}
    elif workflow_type == 'options':
        response_data = {"option_generators": response_data["option_generators"]}

    return func.HttpResponse(
        json.dumps(response_data),
        mimetype="application/json"
    )
