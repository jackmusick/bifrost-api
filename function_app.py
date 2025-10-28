from shared.config import validate_filesystem_config
from shared.import_restrictor import install_import_restrictions
from functions.queue.poison_queue_handler import bp as poison_queue_handler_bp
from functions.queue.worker import bp as worker_bp
from functions.queue.package_worker import bp as package_worker_bp
from functions.timer.execution_cleanup import bp as execution_cleanup_timer_bp
from functions.timer.schedule_processor import bp as schedule_processor_bp
from functions.timer.oauth_refresh_timer import bp as oauth_refresh_timer_bp
from functions.http.schedules import bp as schedules_bp
from functions.http.workflow_keys import bp as workflow_keys_bp
from functions.http.workflows import bp as workflows_bp
from functions.http.secrets import bp as secrets_bp
from functions.http.webpubsub import bp as webpubsub_bp
from functions.http.roles_source import bp as roles_source_bp
from functions.http.roles import bp as roles_bp
from functions.http.permissions import bp as permissions_bp
from functions.http.organizations import bp as organizations_bp
from functions.http.org_config import bp as org_config_bp
from functions.http.openapi import bp as openapi_bp
from functions.http.oauth_api import bp as oauth_api_bp
from functions.http.metrics import bp as metrics_bp
from functions.http.health import bp as health_bp
from functions.http.forms import bp as forms_bp
from functions.http.file_uploads import bp as file_uploads_bp
from functions.http.execution_cleanup import bp as execution_cleanup_http_bp
from functions.http.executions import bp as executions_bp
from functions.http.endpoints import bp as endpoints_bp
from functions.http.editor_files import bp as editor_files_bp
from functions.http.discovery import bp as discovery_bp
from functions.http.branding import bp as branding_bp
from functions.http.logs import bp as logs_bp
from functions.http.packages import bp as packages_bp
import importlib.util
import logging
import os
import sys
from pathlib import Path

import azure.functions as func

# ==================== EARLY INITIALIZATION ====================
# CRITICAL: Initialize queues BEFORE importing queue blueprints
# Queue triggers bind immediately when imported, so queues must exist first
from shared.init_tables import init_tables
from shared.queue_init import init_queues

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("="*60)
logger.info("PRE-IMPORT QUEUE INITIALIZATION")
logger.info("="*60)

try:
    queue_results = init_queues()
    if queue_results["created"]:
        logger.info(f"✓ Created {len(queue_results['created'])} queues")
    if queue_results["already_exists"]:
        logger.info(
            f"✓ {len(queue_results['already_exists'])} queues already exist")
    if queue_results["failed"]:
        logger.error(
            f"✗ Failed to create {len(queue_results['failed'])} queues")
except Exception as e:
    logger.error(f"Queue initialization failed: {e}", exc_info=True)

logger.info("="*60 + "\n")

# Now safe to import queue blueprints
# ruff: noqa: E402

# ==================== DEBUGPY INITIALIZATION ====================
# Enable debugpy for remote debugging if ENABLE_DEBUGGING=true (T016)
if os.getenv('ENABLE_DEBUGGING') == 'true':
    import debugpy
    debugpy.listen(("0.0.0.0", 5678))
    logging.info(
        "🐛 Debugpy listening on port 5678 - attach VS Code debugger anytime")

# ==================== FILESYSTEM CONFIGURATION ====================
# Validate filesystem configuration before anything else
validate_filesystem_config()

# ==================== IMPORT RESTRICTIONS ====================
# T006: Install import restrictions BEFORE importing workspace code

# Calculate workspace paths - support both system and user workspaces
# System workspace: /workspace (Azure Files mount in production)
# User workspace: ./workspace (local development)


def get_workspace_paths():
    """
    Dynamically determine workspace paths.

    Returns list of existing workspace directories:
    - BIFROST_WORKSPACE_LOCATION env var: User code (workflows, scripts, files)
    - ./platform: Platform-provided code (SDK, examples, integrations)

    This is a function (not a constant) to support hot-reload scenarios
    where workspace directories might be created after startup.
    """
    paths = []
    base_dir = Path(os.path.dirname(os.path.abspath(__file__)))

    # User workspace from environment variable
    workspace_loc = os.getenv("BIFROST_WORKSPACE_LOCATION")
    if workspace_loc:
        workspace_path = Path(workspace_loc)
        if workspace_path.exists():
            paths.append(str(workspace_path))

    # Platform code directory (always relative to project root)
    platform_path = base_dir / 'platform'
    if platform_path.exists():
        paths.append(str(platform_path))

    return paths


def get_home_path() -> str | None:
    """Get the user workspace directory path from BIFROST_WORKSPACE_LOCATION."""
    workspace_loc = os.getenv("BIFROST_WORKSPACE_LOCATION")
    if workspace_loc:
        workspace_path = Path(workspace_loc)
        return str(workspace_path) if workspace_path.exists() else None
    return None


# Add /platform to sys.path so bifrost imports work
# This allows: from bifrost import organizations
base_dir = Path(os.path.dirname(os.path.abspath(__file__)))
platform_path = base_dir / 'platform'
if platform_path.exists() and str(platform_path) not in sys.path:
    sys.path.insert(0, str(platform_path))
    logging.info(f"Added /platform to sys.path: {platform_path}")

# Add workspace/.packages to sys.path for user-installed packages
# This allows users to: pip install --target=<workspace>/.packages <package>
workspace_loc = os.getenv("BIFROST_WORKSPACE_LOCATION")
if workspace_loc:
    packages_path = Path(workspace_loc) / '.packages'
    # Ensure .packages directory exists so users don't need to restart after first package install
    packages_path.mkdir(parents=True, exist_ok=True)
    if str(packages_path) not in sys.path:
        sys.path.insert(0, str(packages_path))
        logging.info(f"Added workspace/.packages to sys.path: {packages_path}")

# Install import restrictions to prevent workspace code from importing engine internals
# /home code has stricter restrictions (only bifrost SDK)
# /platform code can import from shared.* (needs handlers)
install_import_restrictions(get_workspace_paths(), home_path=get_home_path())

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
# Queue initialization moved to TOP of file (before blueprint imports)
# See lines 9-33 for queue initialization code

# ==================== WORKSPACE DISCOVERY ====================
# T005: Discover workspace modules to register workflows and data providers


def discover_workspace_modules(force_reload: bool = False):
    """
    Dynamically discover and import all Python files in workspace subdirectories.

    This function scans all workspace paths:
    - /home: User code (workflows, scripts)
    - /platform: Platform-provided code (SDK, examples, integrations)
    - /workspace: Legacy support (backwards compatibility)

    This allows developers to add workflows without restarting the app,
    and supports both production (mounted volumes) and development (local files).

    No __init__.py files are required - this allows workspace code to be purely
    user/platform code without any framework dependencies.

    Args:
        force_reload: If True, clears registry and re-imports all modules (for hot-reload)
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

    # If force_reload, clear registry and remove workspace modules from sys.modules
    if force_reload:
        from shared.registry import get_registry
        registry = get_registry()
        registry.clear_all()
        logging.info("Cleared registry for hot-reload")

        # Remove all workspace.* modules from sys.modules
        modules_to_remove = [
            name for name in sys.modules.keys() if name.startswith('workspace.')]
        for module_name in modules_to_remove:
            del sys.modules[module_name]
        logging.info(
            f"Removed {len(modules_to_remove)} workspace modules from sys.modules")

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

            # Skip .packages directory (user-installed Python packages)
            if ".packages" in py_file.parts:
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

                # Log to system logger for visibility
                try:
                    from shared.system_logger import get_system_logger
                    system_logger = get_system_logger()
                    import asyncio
                    asyncio.create_task(system_logger.log_discovery_failure(
                        module_name=module_name,
                        file_path=str(py_file),
                        error=str(e)
                    ))
                except Exception as log_error:
                    logging.warning(
                        f"Failed to log discovery failure: {log_error}")

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
# File upload SAS URL generation (User Story 2)
app.register_functions(file_uploads_bp)
# Platform branding configuration (User Story 7)
app.register_functions(branding_bp)
app.register_functions(roles_bp)
app.register_functions(executions_bp)  # Workflow execution history
# Stuck execution cleanup HTTP API
app.register_functions(execution_cleanup_http_bp)
app.register_functions(roles_source_bp)  # SWA roles source
app.register_functions(openapi_bp)  # OpenAPI/Swagger endpoints
app.register_functions(secrets_bp)  # Secret management endpoints
app.register_functions(health_bp)  # Health monitoring endpoints
app.register_functions(metrics_bp)  # System metrics endpoints
app.register_functions(oauth_api_bp)  # OAuth connection management endpoints
app.register_functions(webpubsub_bp)  # Web PubSub real-time connection negotiation
app.register_functions(logs_bp)  # System logs viewing (admin-only)
# Browser-based code editor file operations
app.register_functions(editor_files_bp)
# Package management for workspace
app.register_functions(packages_bp)

if (os.getenv('AZURE_FUNCTIONS_ENVIRONMENT') != 'Testing'):
    app.register_functions(oauth_refresh_timer_bp)  # OAuth token refresh timer
    # CRON schedule processor timer (User Story 5)
    app.register_functions(schedule_processor_bp)
    # Execution cleanup timer (timeout stuck executions)
    app.register_functions(execution_cleanup_timer_bp)

# Register blueprints - Workflow Engine (unified in functions/)
app.register_functions(discovery_bp)  # Workflow and data provider discovery
app.register_functions(workflows_bp)  # Workflow execution
app.register_functions(endpoints_bp)  # Workflow HTTP endpoints (API key auth)
# Workflow API key management (User Story 3)
app.register_functions(workflow_keys_bp)
# Scheduled workflows viewer (User Story 5)
app.register_functions(schedules_bp)
# Async workflow execution worker (User Story 4)
app.register_functions(worker_bp)
# Package installation worker
app.register_functions(package_worker_bp)
# Poison queue handler for failed executions
app.register_functions(poison_queue_handler_bp)
logging.info("Function app initialization complete!")
