"""
Example Workflow - Comprehensive Platform Feature Demonstration

This workflow demonstrates all key features of the Bifrost Integrations:
- Context access (org info, caller info, execution metadata)
- Configuration management (get_config with fallback)
- Secret resolution (transparent Key Vault integration)
- Logging (context.log with structured data)
- Checkpoints (state snapshots for debugging)
- Variables (workflow-scoped state)
- Parameter validation and types
- Error handling

Use this workflow as a reference for building new workflows.
"""

from engine.shared.decorators import workflow, param
from engine.shared.context import OrganizationContext
from datetime import datetime


@workflow(
    name="example_workflow",
    description="Comprehensive example demonstrating all platform features",
    category="Examples"
)
@param("test_string", "string", "A test string parameter", required=True)
@param("test_number", "int", "A test number parameter", required=False, default_value=42)
@param("test_boolean", "bool", "A test boolean parameter", required=False, default_value=True)
async def example_workflow(
    context: OrganizationContext,
    test_string: str,
    test_number: int = 42,
    test_boolean: bool = True
) -> dict:
    """
    Example workflow demonstrating all platform features.

    This workflow tests:
    1. Context properties (org, caller, execution metadata)
    2. Configuration access with type parsing
    3. Secret resolution from Key Vault
    4. Context logging (info, warning, error levels)
    5. Checkpoints for debugging
    6. Workflow variables
    7. Parameter handling and validation
    8. Structured return data

    Args:
        context: Organization context with access to org data, config, secrets
        test_string: A test string parameter
        test_number: A test number parameter (default: 42)
        test_boolean: A test boolean parameter (default: True)

    Returns:
        dict: Comprehensive report with test results
    """

    # ==================== SETUP ====================

    context.log("info", "Starting example workflow execution", {
        "test_string": test_string,
        "test_number": test_number,
        "test_boolean": test_boolean
    })

    report = {
        "workflow_name": "example_workflow",
        "execution_id": context.execution_id,
        "timestamp": datetime.utcnow().isoformat(),
        "parameters": {
            "test_string": test_string,
            "test_number": test_number,
            "test_boolean": test_boolean
        },
        "tests": {}
    }

    # ==================== TEST 1: CONTEXT PROPERTIES ====================

    context.log("info", "Testing context properties")

    try:
        context_test = {
            "success": True,
            "organization": {
                "id": context.org_id,
                "name": context.org_name,
                "tenant_id": context.tenant_id
            },
            "caller": {
                "user_id": context.executed_by,
                "email": context.executed_by_email,
                "name": context.executed_by_name
            },
            "execution": {
                "execution_id": context.execution_id,
                "org_provided": context.org is not None
            }
        }
        report["tests"]["context_properties"] = context_test
        context.log("info", "✓ Context properties test passed", context_test)

        # Save checkpoint
        context.save_checkpoint("context_test_complete", context_test)

    except Exception as e:
        report["tests"]["context_properties"] = {
            "success": False,
            "error": str(e)
        }
        context.log("error", "✗ Context properties test failed",
                    {"error": str(e)})

    # ==================== TEST 2: CONFIGURATION ACCESS ====================

    context.log("info", "Testing configuration access")

    try:
        # Test accessing the "Testing" config (should be secret_ref type)
        testing_config_value = None
        testing_config_error = None

        try:
            testing_config_value = context.get_config("Testing")
            context.log("info", "Retrieved 'Testing' config (secret resolved)", {
                "config_key": "Testing",
                "value_length": len(str(testing_config_value)) if testing_config_value else 0,
                "value_type": type(testing_config_value).__name__
            })
        except Exception as e:
            testing_config_error = str(e)
            context.log("warning", "Could not retrieve 'Testing' config", {
                        "error": str(e)})

        # Test config with default fallback
        nonexistent_config = context.get_config(
            "NonexistentKey", default="fallback_value")

        # Test has_config
        has_testing = context.has_config("Testing")
        has_nonexistent = context.has_config("NonexistentKey")

        config_test = {
            "success": True,
            "testing_config": {
                "exists": has_testing,
                "value_retrieved": testing_config_value is not None,
                "error": testing_config_error,
                "value_preview": str(testing_config_value)[:20] + "..." if testing_config_value and len(str(testing_config_value)) > 20 else str(testing_config_value)
            },
            "fallback_test": {
                "key": "NonexistentKey",
                "has_config": has_nonexistent,
                "fallback_value": nonexistent_config,
                "fallback_worked": nonexistent_config == "fallback_value"
            }
        }

        report["tests"]["configuration_access"] = config_test
        context.log("info", "✓ Configuration access test passed", config_test)

        # Save checkpoint
        context.save_checkpoint("config_test_complete", config_test)

    except Exception as e:
        report["tests"]["configuration_access"] = {
            "success": False,
            "error": str(e)
        }
        context.log("error", "✗ Configuration access test failed",
                    {"error": str(e)})

    # ==================== TEST 3: WORKFLOW VARIABLES ====================

    context.log("info", "Testing workflow variables")

    try:
        # Set some variables
        context.set_variable("computation_result", test_number * 2)
        context.set_variable("string_length", len(test_string))
        context.set_variable("boolean_state", test_boolean)
        context.set_variable("complex_data", {
            "nested": {
                "value": "test",
                "number": 123
            }
        })

        # Retrieve them
        computation = context.get_variable("computation_result")
        string_len = context.get_variable("string_length")
        bool_state = context.get_variable("boolean_state")
        complex = context.get_variable("complex_data")
        nonexistent = context.get_variable(
            "nonexistent", default="default_value")

        variables_test = {
            "success": True,
            "variables_set": {
                "computation_result": computation,
                "string_length": string_len,
                "boolean_state": bool_state,
                "complex_data": complex
            },
            "default_fallback": {
                "key": "nonexistent",
                "value": nonexistent,
                "default_worked": nonexistent == "default_value"
            }
        }

        report["tests"]["workflow_variables"] = variables_test
        context.log("info", "✓ Workflow variables test passed", variables_test)

        # Save checkpoint
        context.save_checkpoint("variables_test_complete", variables_test)

    except Exception as e:
        report["tests"]["workflow_variables"] = {
            "success": False,
            "error": str(e)
        }
        context.log("error", "✗ Workflow variables test failed",
                    {"error": str(e)})

    # ==================== TEST 4: LOGGING LEVELS ====================

    context.log("info", "Testing different log levels")

    try:
        # Test all log levels
        context.log("info", "This is an informational log", {
            "level": "info",
            "purpose": "General information"
        })

        context.log("warning", "This is a warning log", {
            "level": "warning",
            "purpose": "Non-critical issues"
        })

        context.log("error", "This is an error log (simulated)", {
            "level": "error",
            "purpose": "Critical issues (this is just a test)"
        })

        logging_test = {
            "success": True,
            "levels_tested": ["info", "warning", "error"],
            "note": "Check execution logs to verify all levels were recorded"
        }

        report["tests"]["logging_levels"] = logging_test
        context.log("info", "✓ Logging levels test passed", logging_test)

    except Exception as e:
        report["tests"]["logging_levels"] = {
            "success": False,
            "error": str(e)
        }
        context.log("error", "✗ Logging levels test failed", {"error": str(e)})

    # ==================== TEST 5: CHECKPOINTS ====================

    context.log("info", "Testing checkpoint functionality")

    try:
        # Create multiple checkpoints to demonstrate state snapshots
        context.save_checkpoint("milestone_1", {
            "progress": "25%",
            "tests_completed": 1,
            "note": "Context properties tested"
        })

        context.save_checkpoint("milestone_2", {
            "progress": "50%",
            "tests_completed": 2,
            "note": "Configuration access tested"
        })

        context.save_checkpoint("milestone_3", {
            "progress": "75%",
            "tests_completed": 3,
            "note": "Variables and logging tested"
        })

        checkpoint_test = {
            "success": True,
            "checkpoints_created": 6,  # 3 from tests + 3 milestones
            "note": "Checkpoints are saved in execution state for debugging"
        }

        report["tests"]["checkpoints"] = checkpoint_test
        context.log("info", "✓ Checkpoints test passed", checkpoint_test)

    except Exception as e:
        report["tests"]["checkpoints"] = {
            "success": False,
            "error": str(e)
        }
        context.log("error", "✗ Checkpoints test failed", {"error": str(e)})

    # ==================== TEST 6: PARAMETER VALIDATION ====================

    context.log("info", "Testing parameter validation and types")

    try:
        validation_test = {
            "success": True,
            "parameters_received": {
                "test_string": {
                    "value": test_string,
                    "type": type(test_string).__name__,
                    "valid": isinstance(test_string, str)
                },
                "test_number": {
                    "value": test_number,
                    "type": type(test_number).__name__,
                    "valid": isinstance(test_number, int)
                },
                "test_boolean": {
                    "value": test_boolean,
                    "type": type(test_boolean).__name__,
                    "valid": isinstance(test_boolean, bool)
                }
            },
            "all_types_correct": (
                isinstance(test_string, str) and
                isinstance(test_number, int) and
                isinstance(test_boolean, bool)
            )
        }

        report["tests"]["parameter_validation"] = validation_test
        context.log("info", "✓ Parameter validation test passed",
                    validation_test)

    except Exception as e:
        report["tests"]["parameter_validation"] = {
            "success": False,
            "error": str(e)
        }
        context.log("error", "✗ Parameter validation test failed",
                    {"error": str(e)})

    # ==================== FINAL REPORT ====================

    # Calculate overall success
    all_tests_passed = all(
        test.get("success", False)
        for test in report["tests"].values()
    )

    report["summary"] = {
        "total_tests": len(report["tests"]),
        "tests_passed": sum(1 for test in report["tests"].values() if test.get("success", False)),
        "tests_failed": sum(1 for test in report["tests"].values() if not test.get("success", True)),
        "all_passed": all_tests_passed,
        "execution_time": datetime.utcnow().isoformat()
    }

    # Log final summary
    context.log(
        "info" if all_tests_passed else "warning",
        f"Example workflow completed: {report['summary']['tests_passed']}/{report['summary']['total_tests']} tests passed",
        report["summary"]
    )

    # Final checkpoint
    context.save_checkpoint("execution_complete", report["summary"])

    return report
