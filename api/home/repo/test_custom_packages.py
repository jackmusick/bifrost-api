"""
Test workflow to verify custom package installation works.

This workflow tests that user-installed packages in /home/.packages work correctly.
"""

import sys
from pathlib import Path


async def test_custom_packages(context):
    """
    Test that custom packages can be installed and imported.

    Returns:
        dict with package test results
    """
    results = {
        "success": True,
        "python_path": sys.path[:5],  # First 5 paths for debugging
        "tests": []
    }

    # Test 1: Verify .packages directory is accessible
    try:
        packages_dir = Path(__file__).parent.parent / '.packages'
        exists = packages_dir.exists()
        results["tests"].append({
            "test": "packages_directory_exists",
            "result": exists,
            "path": str(packages_dir)
        })

        # Check if .packages is in sys.path
        packages_in_path = str(packages_dir) in sys.path
        results["tests"].append({
            "test": "packages_in_sys_path",
            "result": packages_in_path
        })

        if not packages_in_path:
            results["success"] = False
            results["error"] = ".packages directory not in sys.path - custom packages won't work"

    except Exception as e:
        results["tests"].append({
            "test": "packages_directory_check",
            "error": str(e)
        })
        results["success"] = False

    # Test 2: Try to import a common package (if installed)
    # This would test actual package installation
    try:
        # Try importing requests (commonly installed)
        import requests
        results["tests"].append({
            "test": "import_requests",
            "result": "success",
            "version": getattr(requests, '__version__', 'unknown')
        })
    except ImportError:
        results["tests"].append({
            "test": "import_requests",
            "result": "not_installed",
            "note": "Install with: pip install --target=/home/.packages requests"
        })
    except Exception as e:
        results["tests"].append({
            "test": "import_requests",
            "error": str(e)
        })

    # Test 3: Verify bifrost SDK imports work
    try:
        from bifrost import organizations, workflows, files
        results["tests"].append({
            "test": "import_bifrost_sdk",
            "result": "success",
            "modules": ["organizations", "workflows", "files"]
        })
    except ImportError as e:
        results["tests"].append({
            "test": "import_bifrost_sdk",
            "error": str(e)
        })
        results["success"] = False

    # Test 4: Verify shared modules are BLOCKED (security)
    try:
        from shared import models
        results["tests"].append({
            "test": "import_shared_modules",
            "result": "SECURITY ISSUE: shared modules should be blocked!",
            "success": False
        })
        results["success"] = False
    except ImportError:
        # Expected - this is correct behavior
        results["tests"].append({
            "test": "import_shared_modules_blocked",
            "result": "success",
            "note": "Import restrictions working correctly"
        })

    # Test 5: Verify functions modules are BLOCKED (security)
    try:
        from functions import workflows
        results["tests"].append({
            "test": "import_functions_modules",
            "result": "SECURITY ISSUE: functions modules should be blocked!",
            "success": False
        })
        results["success"] = False
    except ImportError:
        # Expected - this is correct behavior
        results["tests"].append({
            "test": "import_functions_modules_blocked",
            "result": "success",
            "note": "Import restrictions working correctly"
        })

    return results
