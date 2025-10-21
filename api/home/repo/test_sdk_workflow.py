"""
Test workflow to verify Bifrost SDK functionality from user code.

This workflow tests all SDK modules from /home user code.
"""

from bifrost import organizations, workflows, files, forms, executions, roles


async def test_sdk_all_modules(context, test_mode: str = "basic"):
    """
    Test all SDK modules to verify they work from user code.

    Args:
        context: Execution context (injected by engine)
        test_mode: Type of test to run (basic, full, cleanup)

    Returns:
        dict with test results
    """
    results = {
        "success": True,
        "tests_passed": [],
        "tests_failed": [],
        "test_mode": test_mode
    }

    # Test 1: Organizations SDK
    try:
        # List organizations
        orgs = organizations.list()
        results["tests_passed"].append({
            "module": "organizations",
            "operation": "list",
            "result": f"Found {len(orgs)} organizations"
        })

        # Get current organization
        if orgs:
            org = organizations.get(context.org_id)
            results["tests_passed"].append({
                "module": "organizations",
                "operation": "get",
                "result": f"Retrieved org: {org.name}"
            })
    except Exception as e:
        results["tests_failed"].append({
            "module": "organizations",
            "error": str(e)
        })
        results["success"] = False

    # Test 2: Workflows SDK
    try:
        # List workflows
        workflow_list = workflows.list()
        results["tests_passed"].append({
            "module": "workflows",
            "operation": "list",
            "result": f"Found {len(workflow_list)} workflows"
        })
    except Exception as e:
        results["tests_failed"].append({
            "module": "workflows",
            "error": str(e)
        })
        results["success"] = False

    # Test 3: Files SDK
    try:
        # Write a test file
        test_content = f"Test file created at {context.get_variable('timestamp', 'unknown')}"
        files.write("test_output.txt", test_content.encode())
        results["tests_passed"].append({
            "module": "files",
            "operation": "write",
            "result": "Created test_output.txt"
        })

        # Read it back
        content = files.read("test_output.txt")
        if content.decode() == test_content:
            results["tests_passed"].append({
                "module": "files",
                "operation": "read",
                "result": "Read test_output.txt successfully"
            })

        # Check existence
        exists = files.exists("test_output.txt")
        results["tests_passed"].append({
            "module": "files",
            "operation": "exists",
            "result": f"File exists: {exists}"
        })

        # List files
        file_list = files.list()
        results["tests_passed"].append({
            "module": "files",
            "operation": "list",
            "result": f"Found {len(file_list)} files"
        })

        # Clean up test file
        if test_mode == "cleanup":
            files.delete("test_output.txt")
            results["tests_passed"].append({
                "module": "files",
                "operation": "delete",
                "result": "Deleted test_output.txt"
            })
    except Exception as e:
        results["tests_failed"].append({
            "module": "files",
            "error": str(e)
        })
        results["success"] = False

    # Test 4: Forms SDK
    try:
        # List forms
        form_list = forms.list()
        results["tests_passed"].append({
            "module": "forms",
            "operation": "list",
            "result": f"Found {len(form_list)} forms"
        })

        # Get a form if any exist
        if form_list:
            form = forms.get(form_list[0].id)
            results["tests_passed"].append({
                "module": "forms",
                "operation": "get",
                "result": f"Retrieved form: {form.title}"
            })
    except Exception as e:
        results["tests_failed"].append({
            "module": "forms",
            "error": str(e)
        })
        results["success"] = False

    # Test 5: Executions SDK
    try:
        # List recent executions
        exec_list = executions.list(limit=5)
        results["tests_passed"].append({
            "module": "executions",
            "operation": "list",
            "result": f"Found {len(exec_list)} recent executions"
        })

        # Get an execution if any exist
        if exec_list:
            exec_id = exec_list[0].get("id") or exec_list[0].get("executionId")
            if exec_id:
                exec_details = executions.get(exec_id)
                results["tests_passed"].append({
                    "module": "executions",
                    "operation": "get",
                    "result": f"Retrieved execution: {exec_id}"
                })
    except Exception as e:
        results["tests_failed"].append({
            "module": "executions",
            "error": str(e)
        })
        results["success"] = False

    # Test 6: Roles SDK
    try:
        # List roles
        role_list = roles.list()
        results["tests_passed"].append({
            "module": "roles",
            "operation": "list",
            "result": f"Found {len(role_list)} roles"
        })

        # Get a role if any exist
        if role_list:
            role = roles.get(role_list[0].id)
            results["tests_passed"].append({
                "module": "roles",
                "operation": "get",
                "result": f"Retrieved role: {role.name}"
            })

            # List users in role
            role_users = roles.list_users(role_list[0].id)
            results["tests_passed"].append({
                "module": "roles",
                "operation": "list_users",
                "result": f"Role has {len(role_users)} users"
            })

            # List forms for role
            role_forms = roles.list_forms(role_list[0].id)
            results["tests_passed"].append({
                "module": "roles",
                "operation": "list_forms",
                "result": f"Role has {len(role_forms)} forms"
            })
    except Exception as e:
        results["tests_failed"].append({
            "module": "roles",
            "error": str(e)
        })
        results["success"] = False

    # Test 7: Verify path sandboxing (should fail)
    try:
        # This should raise an error - testing security
        files.read("/etc/passwd")
        results["tests_failed"].append({
            "module": "files",
            "error": "SECURITY ISSUE: Path traversal was allowed!"
        })
        results["success"] = False
    except ValueError:
        # Expected - this is a pass
        results["tests_passed"].append({
            "module": "files",
            "operation": "security_check",
            "result": "Path sandboxing working correctly"
        })
    except Exception as e:
        results["tests_failed"].append({
            "module": "files",
            "error": f"Unexpected error during security check: {str(e)}"
        })

    # Summary
    results["summary"] = {
        "total_passed": len(results["tests_passed"]),
        "total_failed": len(results["tests_failed"]),
        "overall_success": results["success"]
    }

    return results
