import azure.functions as func
import json
import logging
import os
import sys
import importlib.util
from pathlib import Path

# Enable debugpy for remote debugging if ENABLE_DEBUGGING=true
if os.getenv('ENABLE_DEBUGGING') == 'true':
    import debugpy
    debugpy.listen(("0.0.0.0", 5678))
    logging.info("🐛 Debugpy listening on port 5678 - attach VS Code debugger anytime")

# T033-T034: Install import restrictions BEFORE importing workspace code
from engine.shared.import_restrictor import install_import_restrictions

# Calculate workspace path from environment variable or default to Azure Files mount
WORKSPACE_PATH = os.environ.get('WORKSPACE_PATH', '/workspace')

# Install import restrictions to prevent workspace code from importing engine internals
install_import_restrictions([WORKSPACE_PATH])

# ==================== TABLE INITIALIZATION ====================
# Initialize Azure Table Storage tables at startup
from engine.shared.init_tables import init_tables

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

# ==================== DYNAMIC WORKSPACE DISCOVERY ====================
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
    from engine.shared.registry import get_registry
    registry = get_registry()
    summary = registry.get_summary()

    logging.info(
        f"Registry contains: {summary['workflows_count']} workflows, "
        f"{summary['data_providers_count']} data providers"
    )

    if summary['workflows']:
        logging.info(f"Workflows: {', '.join(summary['workflows'])}")
    if summary['data_providers']:
        logging.info(f"Data providers: {', '.join(summary['data_providers'])}")


# Discover all workspace modules (examples/ and workflows/ subdirectories)
discover_workspace_modules()

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
