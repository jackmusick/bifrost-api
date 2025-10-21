"""
Integration Test Workflow for Bifrost SDK

This workflow tests all SDK modules from actual user code in /home/repo.
Tests:
- Organizations SDK
- Workflows SDK
- Files SDK
- Forms SDK
- Executions SDK
- Roles SDK
- Config SDK
- Secrets SDK
- OAuth SDK
- Import restrictions
- Path sandboxing
"""

from bifrost import (
    organizations, workflows, files, forms, executions, roles,
    config, secrets, oauth
)


async def test_all_sdk_modules(context, mode: str = "read_only"):
    """
    Comprehensive integration test for all SDK modules.

    Args:
        context: Execution context
        mode: "read_only" (default) or "write" (requires permissions)

    Returns:
        dict: Test results with pass/fail for each module
    """
    results = {
        "success": True,
        "tests_passed": [],
        "tests_failed": [],
        "tests_skipped": []
    }

    # Test 1: Organizations SDK
    try:
        orgs = organizations.list()
        results["tests_passed"].append({
            "module": "organizations",
            "operation": "list",
            "count": len(orgs) if orgs else 0
        })
    except Exception as e:
        results["tests_failed"].append({
            "module": "organizations",
            "operation": "list",
            "error": str(e)
        })
        results["success"] = False

    # Test 2: Workflows SDK
    try:
        workflow_list = workflows.list()
        results["tests_passed"].append({
            "module": "workflows",
            "operation": "list",
            "count": len(workflow_list) if workflow_list else 0
        })
    except Exception as e:
        results["tests_failed"].append({
            "module": "workflows",
            "operation": "list",
            "error": str(e)
        })
        results["success"] = False

    # Test 3: Files SDK - Read/Write/List operations
    try:
        # Test write
        files.write("test_integration.txt", "Integration test content")

        # Test read
        content = files.read("test_integration.txt")
        assert content == "Integration test content", "File content mismatch"

        # Test exists
        exists = files.exists("test_integration.txt")
        assert exists is True, "File should exist"

        # Test list
        file_list = files.list(".")
        assert "test_integration.txt" in file_list, "File not in list"

        # Test delete
        files.delete("test_integration.txt")

        results["tests_passed"].append({
            "module": "files",
            "operation": "write/read/exists/list/delete",
            "details": "All file operations successful"
        })
    except Exception as e:
        results["tests_failed"].append({
            "module": "files",
            "operation": "file operations",
            "error": str(e)
        })
        results["success"] = False

    # Test 4: Files SDK - Path sandboxing (security test)
    try:
        # This should FAIL with ValueError
        files.read("/etc/passwd")

        # If we got here, security check failed!
        results["tests_failed"].append({
            "module": "files",
            "operation": "path_sandboxing",
            "error": "SECURITY ISSUE: Path traversal allowed!"
        })
        results["success"] = False
    except ValueError:
        # Expected - path sandboxing is working
        results["tests_passed"].append({
            "module": "files",
            "operation": "path_sandboxing",
            "details": "Path traversal correctly blocked"
        })
    except Exception as e:
        results["tests_failed"].append({
            "module": "files",
            "operation": "path_sandboxing",
            "error": f"Unexpected error: {str(e)}"
        })
        results["success"] = False

    # Test 5: Forms SDK
    try:
        form_list = forms.list()
        results["tests_passed"].append({
            "module": "forms",
            "operation": "list",
            "count": len(form_list) if form_list else 0
        })
    except Exception as e:
        results["tests_failed"].append({
            "module": "forms",
            "operation": "list",
            "error": str(e)
        })
        results["success"] = False

    # Test 6: Executions SDK
    try:
        exec_list = executions.list(limit=5)
        results["tests_passed"].append({
            "module": "executions",
            "operation": "list",
            "count": len(exec_list) if exec_list else 0
        })
    except Exception as e:
        results["tests_failed"].append({
            "module": "executions",
            "operation": "list",
            "error": str(e)
        })
        results["success"] = False

    # Test 7: Roles SDK
    try:
        role_list = roles.list()
        results["tests_passed"].append({
            "module": "roles",
            "operation": "list",
            "count": len(role_list) if role_list else 0
        })
    except Exception as e:
        results["tests_failed"].append({
            "module": "roles",
            "operation": "list",
            "error": str(e)
        })
        results["success"] = False

    # Test 8: Config SDK
    try:
        # Test get with default
        value = config.get("test_integration_key", default="default_value")
        assert value == "default_value", "Config get with default failed"

        # Test set (only in write mode)
        if mode == "write":
            config.set("test_integration_key", "test_value")
            value = config.get("test_integration_key")
            assert value == "test_value", "Config set/get failed"

            # Test list
            all_config = config.list()
            assert isinstance(all_config, dict), "Config list should return dict"

            # Test delete
            deleted = config.delete("test_integration_key")
            assert deleted is True, "Config delete failed"

        results["tests_passed"].append({
            "module": "config",
            "operation": "get/set/list/delete" if mode == "write" else "get (read_only)",
            "details": "Config operations successful"
        })
    except Exception as e:
        results["tests_failed"].append({
            "module": "config",
            "operation": "config operations",
            "error": str(e)
        })
        results["success"] = False

    # Test 9: Secrets SDK
    try:
        # Test get non-existent secret
        value = secrets.get("test_integration_secret")
        assert value is None, "Non-existent secret should return None"

        # Test list (should work even if empty)
        secret_keys = secrets.list()
        assert isinstance(secret_keys, list), "Secrets list should return list"

        # Skip write operations in read_only mode
        if mode == "write":
            results["tests_skipped"].append({
                "module": "secrets",
                "operation": "set/delete",
                "reason": "Write operations require Azure Key Vault"
            })

        results["tests_passed"].append({
            "module": "secrets",
            "operation": "get/list",
            "details": "Secrets read operations successful"
        })
    except Exception as e:
        results["tests_failed"].append({
            "module": "secrets",
            "operation": "secrets operations",
            "error": str(e)
        })
        results["success"] = False

    # Test 10: OAuth SDK
    try:
        # Test get non-existent token
        token = oauth.get_token("test_provider")
        assert token is None or isinstance(token, dict), "Token should be None or dict"

        # Test list providers
        providers = oauth.list_providers()
        assert isinstance(providers, list), "Providers should be a list"

        results["tests_passed"].append({
            "module": "oauth",
            "operation": "get_token/list_providers",
            "details": "OAuth read operations successful"
        })
    except Exception as e:
        results["tests_failed"].append({
            "module": "oauth",
            "operation": "oauth operations",
            "error": str(e)
        })
        results["success"] = False

    # Test 11: Import Restrictions (security test)
    try:
        # This should FAIL - user code cannot import from shared.*
        from shared.models import Organization  # noqa: F401

        # If we got here, import restriction failed!
        results["tests_failed"].append({
            "module": "import_restrictions",
            "operation": "block_shared_imports",
            "error": "SECURITY ISSUE: Import restriction bypassed!"
        })
        results["success"] = False
    except ImportError:
        # Expected - import restrictions are working
        results["tests_passed"].append({
            "module": "import_restrictions",
            "operation": "block_shared_imports",
            "details": "Import restrictions correctly enforced"
        })
    except Exception as e:
        results["tests_failed"].append({
            "module": "import_restrictions",
            "operation": "block_shared_imports",
            "error": f"Unexpected error: {str(e)}"
        })
        results["success"] = False

    # Test 12: Cross-org operations (optional org_id parameter)
    try:
        # Config with explicit org_id
        value = config.get("test_key", org_id=context.org_id)

        # Secrets with explicit org_id
        secret = secrets.get("test_secret", org_id=context.org_id)

        # OAuth with explicit org_id
        token = oauth.get_token("test_provider", org_id=context.org_id)

        results["tests_passed"].append({
            "module": "cross_org_operations",
            "operation": "optional_org_id_parameter",
            "details": "Cross-org operations work correctly"
        })
    except Exception as e:
        results["tests_failed"].append({
            "module": "cross_org_operations",
            "operation": "optional_org_id_parameter",
            "error": str(e)
        })
        results["success"] = False

    # Summary
    results["summary"] = {
        "total_tests": len(results["tests_passed"]) + len(results["tests_failed"]) + len(results["tests_skipped"]),
        "passed": len(results["tests_passed"]),
        "failed": len(results["tests_failed"]),
        "skipped": len(results["tests_skipped"]),
        "pass_rate": f"{(len(results['tests_passed']) / (len(results['tests_passed']) + len(results['tests_failed'])) * 100):.1f}%" if (len(results['tests_passed']) + len(results['tests_failed'])) > 0 else "N/A"
    }

    return results
