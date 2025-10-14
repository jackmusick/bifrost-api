import azure.functions as func
import json
import logging
import os
import sys
import importlib.util
from pathlib import Path

# ==================== DEBUGPY INITIALIZATION ====================
# Enable debugpy for remote debugging if ENABLE_DEBUGGING=true (T016)
if os.getenv('ENABLE_DEBUGGING') == 'true':
    import debugpy
    debugpy.listen(("0.0.0.0", 5678))
    logging.info("🐛 Debugpy listening on port 5678 - attach VS Code debugger anytime")

# ==================== IMPORT RESTRICTIONS ====================
# T006: Install import restrictions BEFORE importing workspace code
from shared.import_restrictor import install_import_restrictions

# Calculate workspace path from environment variable or default to Azure Files mount
WORKSPACE_PATH = os.environ.get('WORKSPACE_PATH', '/workspace')

# Install import restrictions to prevent workspace code from importing engine internals
install_import_restrictions([WORKSPACE_PATH])

# ==================== TABLE INITIALIZATION ====================
# T007: Initialize Azure Table Storage tables at startup
from shared.init_tables import init_tables

try:
    logging.info("Initializing Azure Table Storage tables...")
    results = init_tables()

    if results["created"]:
        logging.info(f"Created {len(results['created'])} tables: {', '.join(results['created'])}")
    if results["already_exists"]:
        logging.info(f"{len(results['already_exists'])} tables already exist")
    if results["failed"]:
        logging.warning(f"Failed to create {len(results['failed'])} tables - some features may not work")

except Exception as e:
    logging.warning(f"Table initialization failed: {e} - continuing without table initialization")

# ==================== WORKSPACE DISCOVERY ====================
# T005: Discover workspace modules to register workflows and data providers
def discover_workspace_modules():
    """
    Dynamically discover and import all Python files in workspace/ subdirectories.

    This function recursively scans workspace/ for .py files and imports them
    to trigger @workflow and @data_provider decorator registration.

    No __init__.py files are required - this allows workspace/ to be purely
    user code without any framework dependencies.
    """
    workspace_root = Path(WORKSPACE_PATH)
    discovered_count = 0

    logging.info(f"Starting dynamic workspace discovery in {workspace_root}")

    if not workspace_root.exists():
        logging.warning(f"Workspace path {workspace_root} does not exist - skipping discovery")
        return

    # Recursively find all .py files in workspace subdirectories
    for py_file in workspace_root.rglob("*.py"):
        # Skip __init__.py and private files
        if py_file.name.startswith("_"):
            continue

        # Calculate module path relative to workspace root
        relative_path = py_file.relative_to(workspace_root)
        module_parts = list(relative_path.parts[:-1]) + [py_file.stem]
        module_name = f"workspace.{'.'.join(module_parts)}"

        try:
            # Import the module using importlib (this triggers decorators)
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                logging.info(f"✓ Discovered: {module_name}")
                discovered_count += 1

        except Exception as e:
            logging.error(
                f"✗ Failed to import {module_name}: {e}",
                exc_info=True
            )

    logging.info(f"Workspace discovery complete: {discovered_count} modules imported")

    # Log registry summary
    from shared.registry import get_registry
    registry = get_registry()
    summary = registry.get_summary()

    logging.info(
        f"Registry contains: {summary['workflows_count']} workflows, "
        f"{summary['data_providers_count']} data providers"
    )

    if summary.get('workflows'):
        logging.info(f"Workflows: {', '.join(summary['workflows'])}")
    if summary.get('data_providers'):
        logging.info(f"Data providers: {', '.join(summary['data_providers'])}")


# Discover all workspace modules
discover_workspace_modules()

# T008: Import engine data providers to trigger auto-discovery
import engine.data_providers

# ==================== BLUEPRINT IMPORTS ====================
# API Management Blueprints (existing)
from functions.organizations import bp as organizations_bp
from functions.org_config import bp as org_config_bp
from functions.permissions import bp as permissions_bp
from functions.forms import bp as forms_bp
from functions.roles import bp as roles_bp
from functions.executions import bp as executions_bp
from functions.roles_source import bp as roles_source_bp
from functions.openapi import bp as openapi_bp
from functions.secrets import bp as secrets_bp
from functions.health import bp as health_bp
from functions.dashboard import bp as dashboard_bp
from functions.oauth_api import bp as oauth_api_bp
from functions.oauth_refresh_timer import bp as oauth_refresh_timer_bp

# Workflow Engine Blueprints (from merged workflows/)
from engine.admin.metadata import bp as workflow_metadata_bp
from engine.execute import bp as workflow_execute_bp
from engine.functions.data_provider_api import bp as data_provider_api_bp

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Register blueprints - API Management
app.register_functions(organizations_bp)
app.register_functions(org_config_bp)
app.register_functions(permissions_bp)
app.register_functions(forms_bp)
app.register_functions(roles_bp)
app.register_functions(executions_bp)  # Updated to use direct workflow execution (T009)
app.register_functions(roles_source_bp)  # SWA roles source
app.register_functions(openapi_bp)  # OpenAPI/Swagger endpoints
app.register_functions(secrets_bp)  # Secret management endpoints
app.register_functions(health_bp)  # Health monitoring endpoints
app.register_functions(dashboard_bp)  # Dashboard metrics endpoints
app.register_functions(oauth_api_bp)  # OAuth connection management endpoints
app.register_functions(oauth_refresh_timer_bp)  # OAuth token refresh timer

# Register blueprints - Workflow Engine (unified architecture)
app.register_functions(workflow_metadata_bp)  # Workflow metadata endpoints
app.register_functions(workflow_execute_bp)  # Direct workflow execution
app.register_functions(data_provider_api_bp)  # Data provider API endpoints

@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Health check endpoint called")
    return func.HttpResponse(
        json.dumps({"status": "healthy", "service": "Management API"}),
        mimetype="application/json"
    )
