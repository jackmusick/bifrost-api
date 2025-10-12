"""
Workflow Auto-Discovery
Automatically imports all workflow modules to trigger decorator registration
"""

import os
import importlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Get the directory containing workflow modules
WORKFLOWS_DIR = Path(__file__).parent


def discover_workflows():
    """
    Automatically discover and import all workflow modules

    This function:
    1. Scans the workflows/ directory for .py files
    2. Skips __init__.py and private files (starting with _)
    3. Imports each module to trigger @workflow decorator registration
    4. Logs discovered workflows

    Called automatically when this module is imported.
    """
    discovered_count = 0

    logger.info(f"Starting workflow auto-discovery in {WORKFLOWS_DIR}")

    # Find all Python files in workflows directory
    for file_path in WORKFLOWS_DIR.glob("*.py"):
        # Skip __init__.py and private files
        if file_path.name.startswith("_"):
            continue

        # Get module name (without .py extension)
        module_name = file_path.stem

        try:
            # Import the module (this triggers @workflow decorators)
            full_module_name = f"workflows.{module_name}"
            importlib.import_module(full_module_name)

            logger.info(f" Discovered workflow module: {module_name}")
            discovered_count += 1

        except Exception as e:
            logger.error(
                f" Failed to import workflow module '{module_name}': {e}",
                exc_info=True
            )

    logger.info(f"Workflow auto-discovery complete: {discovered_count} modules imported")

    # Log registry summary
    from shared.registry import get_registry
    registry = get_registry()
    summary = registry.get_summary()

    logger.info(
        f"Registry contains: {summary['workflows_count']} workflows, "
        f"{summary['data_providers_count']} data providers"
    )

    if summary['workflows']:
        logger.info(f"Registered workflows: {', '.join(summary['workflows'])}")
    if summary['data_providers']:
        logger.info(f"Registered data providers: {', '.join(summary['data_providers'])}")


# Auto-discover workflows when this module is imported
discover_workflows()
