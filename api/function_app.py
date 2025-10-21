import importlib.util
import logging
import os
import sys
from pathlib import Path

import azure.functions as func

from functions.http.branding import bp as branding_bp
from functions.http.data_providers import bp as data_providers_bp
from functions.http.discovery import bp as discovery_bp
from functions.http.endpoints import bp as endpoints_bp
from functions.http.executions import bp as executions_bp
from functions.http.execution_cleanup import bp as execution_cleanup_http_bp
from functions.http.file_uploads import bp as file_uploads_bp
from functions.http.forms import bp as forms_bp
from functions.http.health import bp as health_bp
from functions.http.metrics import bp as metrics_bp
from functions.http.oauth_api import bp as oauth_api_bp
from functions.http.openapi import bp as openapi_bp
from functions.http.org_config import bp as org_config_bp
from functions.http.organizations import bp as organizations_bp
from functions.http.permissions import bp as permissions_bp
from functions.http.roles import bp as roles_bp
from functions.http.roles_source import bp as roles_source_bp
from functions.http.secrets import bp as secrets_bp
from functions.http.workflows import bp as workflows_bp
from functions.http.workflow_keys import bp as workflow_keys_bp
from functions.http.schedules import bp as schedules_bp
from functions.timer.oauth_refresh_timer import bp as oauth_refresh_timer_bp
from functions.timer.schedule_processor import bp as schedule_processor_bp
from functions.timer.execution_cleanup import bp as execution_cleanup_timer_bp
from functions.queue.worker import bp as worker_bp
from functions.queue.poison_queue_handler import bp as poison_queue_handler_bp
from shared.init_tables import init_tables
from shared.queue_init import init_queues

# ==================== DEBUGPY INITIALIZATION ====================
# Enable debugpy for remote debugging if ENABLE_DEBUGGING=true (T016)
if os.getenv('ENABLE_DEBUGGING') == 'true':
    import debugpy
    debugpy.listen(("0.0.0.0", 5678))
    logging.info(
        "🐛 Debugpy listening on port 5678 - attach VS Code debugger anytime")

# ==================== IMPORT RESTRICTIONS ====================
# T006: Install import restrictions BEFORE importing workspace code
from shared.import_restrictor import install_import_restrictions

# Calculate workspace paths - support both system and user workspaces
# System workspace: /workspace (Azure Files mount in production)
# User workspace: ./workspace (local development)


def get_workspace_paths():
    """
    Dynamically determine workspace paths.

    Returns list of existing workspace directories:
    - System workspace: /workspace (Azure Files mount in production)
    - User workspace: ./workspace (local development)

    This is a function (not a constant) to support hot-reload scenarios
    where workspace directories might be created after startup.
    """
    paths = []

    system_path = Path('/workspace')
    if system_path.exists():
        paths.append(str(system_path))

    # Use absolute path like original workflows/function_app.py did
    user_path = Path(os.path.dirname(os.path.abspath(__file__))) / 'workspace'
    if user_path.exists():
        paths.append(str(user_path))

    return paths


# Install import restrictions to prevent workspace code from importing engine internals
# Initial setup - gets paths at startup time
install_import_restrictions(get_workspace_paths())

# ==================== TABLE INITIALIZATION ====================
# T007: Initialize Azure Table Storage tables at startup

try:
    logging.info("Initializing Azure Table Storage tables...")
    results = init_tables()

    if results["created"]:
        logging.info(
            f"Created {len(results['created'])} tables: {', '.join(results['created'])}")
    if results["already_exists"]:
        logging.info(f"{len(results['already_exists'])} tables already exist")
    if results["failed"]:
        logging.warning(
            f"Failed to create {len(results['failed'])} tables - some features may not work")

except Exception as e:
    logging.warning(
        f"Table initialization failed: {e} - continuing without table initialization")

# ==================== QUEUE INITIALIZATION ====================
# T008: Initialize Azure Storage Queues at startup
# Must initialize queues BEFORE registering queue triggers to prevent binding failures

try:
    logging.info("Initializing Azure Storage Queues...")
    queue_results = init_queues()

    if queue_results["created"]:
        logging.info(
            f"Created {len(queue_results['created'])} queues: {', '.join(queue_results['created'])}")
    if queue_results["already_exists"]:
        logging.info(
            f"{len(queue_results['already_exists'])} queues already exist")
    if queue_results["failed"]:
        logging.warning(
            f"Failed to create {len(queue_results['failed'])} queues - async workflow execution may not work")

except Exception as e:
    logging.warning(
        f"Queue initialization failed: {e} - continuing but async workflow execution may fail at runtime")

# ==================== WORKSPACE DISCOVERY ====================
# T005: Discover workspace modules to register workflows and data providers


def discover_workspace_modules():
    """
    Dynamically discover and import all Python files in workspace/ subdirectories.

    This function scans BOTH system and user workspace paths:
    - System workspace: /workspace (Azure Files mount in production)
    - User workspace: ./workspace (local development)

    This allows developers to add workflows without restarting the app,
    and supports both production (mounted volumes) and development (local files).

    No __init__.py files are required - this allows workspace/ to be purely
    user code without any framework dependencies.
    """
    discovered_count = 0

    # Get workspace paths dynamically (supports hot-reload)
    workspace_paths = get_workspace_paths()

    print(
        f"[WORKSPACE DISCOVERY] Found {len(workspace_paths)} workspace paths: {workspace_paths}")

    if not workspace_paths:
        print("[WORKSPACE DISCOVERY] No workspace paths exist - skipping discovery")
        logging.warning("No workspace paths exist - skipping discovery")
        return

    print(
        f"[WORKSPACE DISCOVERY] Starting dynamic workspace discovery in {len(workspace_paths)} location(s)")
    logging.info(
        f"Starting dynamic workspace discovery in {len(workspace_paths)} location(s)")

    # Scan each workspace path
    for workspace_root in workspace_paths:
        workspace_path = Path(workspace_root)

        logging.info(f"Scanning workspace: {workspace_path}")

        # Recursively find all .py files in workspace subdirectories
        for py_file in workspace_path.rglob("*.py"):
            # Skip __init__.py and private files
            if py_file.name.startswith("_"):
                continue

            # Calculate module path relative to workspace root
            relative_path = py_file.relative_to(workspace_path)
            module_parts = list(relative_path.parts[:-1]) + [py_file.stem]
            module_name = f"workspace.{'.'.join(module_parts)}"

            # Skip if already imported (prevents duplicate imports from multiple workspace paths)
            if module_name in sys.modules:
                logging.debug(f"⊘ Already imported: {module_name}")
                continue

            try:
                # Import the module using importlib (this triggers decorators)
                spec = importlib.util.spec_from_file_location(
                    module_name, py_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)

                    logging.info(
                        f"✓ Discovered: {module_name} (from {workspace_path})")
                    discovered_count += 1

            except Exception as e:
                logging.error(
                    f"✗ Failed to import {module_name}: {e}",
                    exc_info=True
                )

    logging.info(
        f"Workspace discovery complete: {discovered_count} modules imported")

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

# ==================== BLUEPRINT IMPORTS ====================
# API Management Blueprints

# Workflow Engine Blueprints (unified in functions/)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Register blueprints - API Management
app.register_functions(organizations_bp)
app.register_functions(org_config_bp)
app.register_functions(permissions_bp)
app.register_functions(forms_bp)
app.register_functions(file_uploads_bp)  # File upload SAS URL generation (User Story 2)
app.register_functions(branding_bp)  # Platform branding configuration (User Story 7)
app.register_functions(roles_bp)
app.register_functions(executions_bp)  # Workflow execution history
app.register_functions(execution_cleanup_http_bp)  # Stuck execution cleanup HTTP API
app.register_functions(roles_source_bp)  # SWA roles source
app.register_functions(openapi_bp)  # OpenAPI/Swagger endpoints
app.register_functions(secrets_bp)  # Secret management endpoints
app.register_functions(health_bp)  # Health monitoring endpoints
app.register_functions(metrics_bp)  # System metrics endpoints
app.register_functions(oauth_api_bp)  # OAuth connection management endpoints

if (os.getenv('AZURE_FUNCTIONS_ENVIRONMENT') != 'Testing'):
    app.register_functions(oauth_refresh_timer_bp)  # OAuth token refresh timer
    app.register_functions(schedule_processor_bp)  # CRON schedule processor timer (User Story 5)
    app.register_functions(execution_cleanup_timer_bp)  # Execution cleanup timer (timeout stuck executions)

# Register blueprints - Workflow Engine (unified in functions/)
app.register_functions(discovery_bp)  # Workflow and data provider discovery
app.register_functions(workflows_bp)  # Workflow execution
app.register_functions(endpoints_bp)  # Workflow HTTP endpoints (API key auth)
app.register_functions(workflow_keys_bp)  # Workflow API key management (User Story 3)
app.register_functions(schedules_bp)  # Scheduled workflows viewer (User Story 5)
app.register_functions(data_providers_bp)  # Data provider API endpoints
app.register_functions(worker_bp)  # Async workflow execution worker (User Story 4)
app.register_functions(poison_queue_handler_bp)  # Poison queue handler for failed executions
