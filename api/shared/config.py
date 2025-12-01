"""
Configuration and Validation Module

Validates required environment variables and filesystem paths at startup.
Fails fast with clear error messages if configuration is invalid.
"""

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def validate_filesystem_config() -> None:
    """
    Validate filesystem configuration at startup.

    Checks that required environment variables are set and paths are accessible.
    Fails fast with clear error messages if configuration is invalid.

    Raises:
        SystemExit: If configuration is invalid
    """
    errors = []

    # Check BIFROST_WORKSPACE_LOCATION
    workspace_location = os.getenv("BIFROST_WORKSPACE_LOCATION")
    if not workspace_location:
        errors.append(
            "FATAL: BIFROST_WORKSPACE_LOCATION environment variable not set.\n"
            "\n"
            "  Why this is required:\n"
            "    This directory stores user code: workflows, scripts, data providers, and uploaded files.\n"
            "    The platform needs a dedicated filesystem location for sandboxed execution.\n"
            "\n"
            "  How to fix:\n"
            "  → Local: Set in local.settings.json (e.g., '/Users/yourname/bifrost-workspace')\n"
            "  → CI/CD: Export before starting function app: export BIFROST_WORKSPACE_LOCATION=\"$(mktemp -d)\"\n"
            "  → Azure: Set in deployment/azuredeploy.json app settings (e.g., '/mounts/workspace')"
        )
    else:
        workspace_path = Path(workspace_location)
        if not workspace_path.exists():
            errors.append(
                f"FATAL: Cannot access workspace directory: {workspace_location}\n"
                f"  Directory does not exist.\n"
                f"  → Local: Create directory: mkdir -p '{workspace_location}'\n"
                f"  → Azure: Check Azure Files mount configuration in deployment/azuredeploy.json"
            )
        elif not os.access(workspace_path, os.R_OK | os.W_OK):
            errors.append(
                f"FATAL: Cannot access workspace directory: {workspace_location}\n"
                f"  Directory exists but is not readable/writable.\n"
                f"  → Local: Check directory permissions: chmod 755 '{workspace_location}'\n"
                f"  → Azure: Check Azure Files mount permissions"
            )
        else:
            logger.info(f"✓ Workspace location validated: {workspace_location}")

    # Check BIFROST_TEMP_LOCATION
    temp_location = os.getenv("BIFROST_TEMP_LOCATION")
    if not temp_location:
        errors.append(
            "FATAL: BIFROST_TEMP_LOCATION environment variable not set.\n"
            "\n"
            "  Why this is required:\n"
            "    This directory stores temporary files during workflow execution:\n"
            "    - File uploads before processing\n"
            "    - Intermediate data transformations\n"
            "    - Execution artifacts and logs\n"
            "\n"
            "  How to fix:\n"
            "  → Local: Set in local.settings.json (e.g., '/Users/yourname/bifrost-temp')\n"
            "  → CI/CD: Export before starting function app: export BIFROST_TEMP_LOCATION=\"$(mktemp -d)\"\n"
            "  → Azure: Set in deployment/azuredeploy.json app settings (e.g., '/mounts/tmp')"
        )
    else:
        temp_path = Path(temp_location)
        # Try to create temp directory if it doesn't exist
        try:
            temp_path.mkdir(parents=True, exist_ok=True)
            # Test write access
            test_file = temp_path / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
            logger.info(f"✓ Temp location validated: {temp_location}")
        except PermissionError:
            errors.append(
                f"FATAL: Cannot access temp directory: {temp_location}\n"
                f"  Directory exists but is not writable.\n"
                f"  → Local: Check directory permissions\n"
                f"  → Azure: Check Azure Files mount permissions"
            )
        except Exception as e:
            errors.append(
                f"FATAL: Cannot access temp directory: {temp_location}\n"
                f"  Error: {str(e)}\n"
                f"  → Local: Ensure parent directory exists and is writable\n"
                f"  → Azure: Check Azure Files mount configuration in deployment/azuredeploy.json"
            )

    # If any errors, log them and exit
    if errors:
        error_msg = "\n" + "="*70 + "\n"
        error_msg += "CONFIGURATION VALIDATION FAILED\n"
        error_msg += "="*70 + "\n"
        for error in errors:
            error_msg += f"\n{error}\n"
        error_msg += "="*70 + "\n"
        error_msg += "Application cannot start with invalid configuration.\n"
        error_msg += "Please fix the errors above and restart.\n"

        # Log to both logger (for Azure Functions logs) and stderr (for immediate visibility)
        logger.error(error_msg)
        print(error_msg, file=sys.stderr)
        sys.exit(1)

    logger.info("✓ Filesystem configuration validated successfully")
