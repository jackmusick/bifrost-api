"""
Test Custom Package Installation and Import at Runtime

This workflow tests that:
1. Packages can be installed to /home/.packages at runtime
2. Installed packages can be imported in workflows
3. Packages work correctly after installation

Usage:
    POST /api/workflows/test_custom_packages_runtime/execute
    {
        "inputData": {
            "package": "requests",  // Package to test
            "test_import": true,    // Whether to test import
            "test_usage": true      // Whether to test actual usage
        }
    }
"""

import subprocess
import sys
from pathlib import Path


async def test_custom_packages_runtime(context, package: str = "colorama", test_import: bool = True, test_usage: bool = True):
    """
    Test installing and using a custom package at runtime.

    Args:
        context: Execution context
        package: Package name to install (default: requests)
        test_import: Whether to test importing the package
        test_usage: Whether to test using the package

    Returns:
        dict: Test results
    """
    results = {
        "success": True,
        "package": package,
        "steps": []
    }

    # Step 1: Verify .packages directory exists
    packages_dir = Path("/Users/jack/GitHub/bifrost-integrations/api/home/.packages")
    if not packages_dir.exists():
        results["success"] = False
        results["error"] = ".packages directory does not exist"
        return results

    results["steps"].append({
        "step": "verify_packages_dir",
        "status": "success",
        "path": str(packages_dir)
    })

    # Step 2: Check if package is already installed
    try:
        __import__(package)
        already_installed = True
        results["steps"].append({
            "step": "check_existing",
            "status": "already_installed",
            "message": f"{package} is already installed"
        })
    except ImportError:
        already_installed = False
        results["steps"].append({
            "step": "check_existing",
            "status": "not_installed",
            "message": f"{package} is not installed"
        })

    # Step 3: Install package if not already installed
    if not already_installed:
        try:
            # Install to .packages directory
            install_result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--target",
                    str(packages_dir),
                    package
                ],
                capture_output=True,
                text=True,
                timeout=60
            )

            if install_result.returncode == 0:
                results["steps"].append({
                    "step": "install",
                    "status": "success",
                    "stdout": install_result.stdout[-500:] if len(install_result.stdout) > 500 else install_result.stdout,
                    "message": f"Successfully installed {package}"
                })
            else:
                results["success"] = False
                results["steps"].append({
                    "step": "install",
                    "status": "failed",
                    "stderr": install_result.stderr,
                    "returncode": install_result.returncode
                })
                return results

        except subprocess.TimeoutExpired:
            results["success"] = False
            results["steps"].append({
                "step": "install",
                "status": "timeout",
                "error": "Installation timed out after 60 seconds"
            })
            return results
        except Exception as e:
            results["success"] = False
            results["steps"].append({
                "step": "install",
                "status": "error",
                "error": str(e)
            })
            return results

    # Step 4: Test import and verify source location
    if test_import:
        try:
            # Force reload if already imported
            if package in sys.modules:
                import importlib
                importlib.reload(sys.modules[package])
            else:
                __import__(package)

            # Get the actual module to check its location
            mod = sys.modules[package]
            module_file = getattr(mod, '__file__', None)

            # Check if it's from .packages
            from_packages = False
            if module_file:
                from_packages = '.packages' in module_file

            results["steps"].append({
                "step": "test_import",
                "status": "success",
                "message": f"Successfully imported {package}",
                "module_file": module_file,
                "from_packages": from_packages,
                "warning": None if from_packages else "Module may not be from .packages - check module_file path"
            })
        except ImportError as e:
            results["success"] = False
            results["steps"].append({
                "step": "test_import",
                "status": "failed",
                "error": str(e)
            })
            return results

    # Step 5: Test actual usage (package-specific)
    if test_usage:
        try:
            if package == "colorama":
                # Test colorama package (terminal colors)
                from colorama import Fore, Back, Style, init
                init(autoreset=True)

                # Test that we can access color codes
                test_string = f"{Fore.RED}Red text{Style.RESET_ALL}"

                results["steps"].append({
                    "step": "test_usage",
                    "status": "success",
                    "test": "Terminal color formatting",
                    "has_fore": hasattr(Fore, 'RED'),
                    "has_back": hasattr(Back, 'BLACK'),
                    "has_style": hasattr(Style, 'BRIGHT'),
                    "message": "colorama color codes accessible"
                })

            elif package == "tabulate":
                # Test tabulate package (table formatting)
                from tabulate import tabulate

                data = [["Name", "Age"], ["Alice", 30], ["Bob", 25]]
                table = tabulate(data, headers="firstrow", tablefmt="grid")

                results["steps"].append({
                    "step": "test_usage",
                    "status": "success",
                    "test": "Table formatting",
                    "table_length": len(table),
                    "message": "tabulate.tabulate() worked"
                })

            elif package == "requests":
                # Test requests package (ALREADY IN requirements.txt - not a good test!)
                import requests
                response = requests.get("https://httpbin.org/get", timeout=10)
                results["steps"].append({
                    "step": "test_usage",
                    "status": "success",
                    "test": "HTTP GET request",
                    "response_code": response.status_code,
                    "message": f"requests.get() worked, status={response.status_code}",
                    "warning": "requests is in requirements.txt - may not be from .packages"
                })

            elif package == "python-dateutil":
                # Test dateutil package
                from dateutil import parser
                dt = parser.parse("2024-01-15T10:30:00Z")
                results["steps"].append({
                    "step": "test_usage",
                    "status": "success",
                    "test": "Date parsing",
                    "parsed_date": dt.isoformat(),
                    "message": "dateutil.parser.parse() worked"
                })

            elif package == "pyyaml":
                # Test yaml package
                import yaml
                data = yaml.safe_load("key: value\nlist:\n  - item1\n  - item2")
                results["steps"].append({
                    "step": "test_usage",
                    "status": "success",
                    "test": "YAML parsing",
                    "parsed_data": data,
                    "message": "yaml.safe_load() worked"
                })

            else:
                # Generic test - just check module has attributes
                mod = sys.modules[package]
                attrs = [attr for attr in dir(mod) if not attr.startswith('_')]
                results["steps"].append({
                    "step": "test_usage",
                    "status": "success",
                    "test": "Module introspection",
                    "attributes_count": len(attrs),
                    "sample_attributes": attrs[:5],
                    "message": f"Module has {len(attrs)} public attributes"
                })

        except Exception as e:
            results["success"] = False
            results["steps"].append({
                "step": "test_usage",
                "status": "failed",
                "error": str(e),
                "error_type": type(e).__name__
            })
            return results

    # Step 6: Verify .packages in sys.path
    packages_path_str = str(packages_dir)
    in_sys_path = packages_path_str in sys.path

    results["steps"].append({
        "step": "verify_sys_path",
        "status": "success" if in_sys_path else "warning",
        "in_sys_path": in_sys_path,
        "message": ".packages is in sys.path" if in_sys_path else ".packages not in sys.path (added by function_app.py at startup)"
    })

    # Summary
    results["summary"] = {
        "package": package,
        "already_installed": already_installed,
        "import_successful": test_import,
        "usage_successful": test_usage,
        "total_steps": len(results["steps"]),
        "all_successful": results["success"]
    }

    return results
