import azure.functions as func
import json
import logging

# Import blueprints
from functions.organizations import bp as organizations_bp
from functions.org_config import bp as org_config_bp
from functions.permissions import bp as permissions_bp
from functions.forms import bp as forms_bp
from functions.roles import bp as roles_bp
from functions.executions import bp as executions_bp
from functions.roles_source import bp as roles_source_bp
from functions.openapi import bp as openapi_bp
from functions.workflows import bp as workflows_bp

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Register blueprints
app.register_functions(organizations_bp)
app.register_functions(org_config_bp)
app.register_functions(permissions_bp)
app.register_functions(forms_bp)
app.register_functions(roles_bp)
app.register_functions(executions_bp)
app.register_functions(roles_source_bp)  # SWA roles source
app.register_functions(openapi_bp)  # OpenAPI/Swagger endpoints
app.register_functions(workflows_bp)  # Workflow engine proxy endpoints

@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Health check endpoint called")
    return func.HttpResponse(
        json.dumps({"status": "healthy", "service": "Management API"}),
        mimetype="application/json"
    )
