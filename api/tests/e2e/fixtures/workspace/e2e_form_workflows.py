"""
E2E Test workflows for form context and visibility testing

Copy of platform/examples/example_form_execution.py with renamed workflows for E2E testing.
These workflows are used by E2E tests to validate form context features.
"""

from shared.decorators import workflow


@workflow(
    name="e2e_load_customer_licenses",
    description="E2E: Load customer license information for form context",
    category="e2e_testing",
    tags=["e2e", "test", "forms"]
)
async def e2e_load_customer_licenses(context):
    """
    E2E test workflow that returns customer license data for form context.
    Used to test launch workflow functionality.
    """
    return {
        "available_licenses": ["Microsoft 365 E3", "Microsoft 365 E5", "Office 365 E1"],
        "license_count": 3,
        "has_licenses": True
    }


@workflow(
    name="e2e_check_available_licenses",
    description="E2E: Check available licenses for form visibility",
    category="e2e_testing",
    tags=["e2e", "test", "forms"]
)
async def e2e_check_available_licenses(context):
    """
    E2E test workflow for license availability checks.
    Returns license information for field visibility.
    """
    return {
        "has_e3_licenses": True,
        "has_e5_licenses": False,
        "total_available": 10
    }


@workflow(
    name="e2e_check_user_exists",
    description="E2E: Check if user exists in system",
    category="e2e_testing",
    tags=["e2e", "test", "forms"]
)
async def e2e_check_user_exists(context):
    """
    E2E test workflow to check user existence.
    Used for testing field visibility based on user status.
    """
    return {
        "user_exists": True,
        "user_name": "John Doe",
        "user_email": "john.doe@example.com"
    }


@workflow(
    name="e2e_check_user_permissions",
    description="E2E: Check user permissions for form access",
    category="e2e_testing",
    tags=["e2e", "test", "forms"]
)
async def e2e_check_user_permissions(context):
    """
    E2E test workflow to check user permissions.
    Returns permission data for conditional form fields.
    """
    return {
        "is_admin": True,
        "can_approve": True,
        "department": "IT"
    }


@workflow(
    name="e2e_process_form_submission",
    description="E2E: Process form submission (test workflow)",
    category="e2e_testing",
    tags=["e2e", "test", "forms"]
)
async def e2e_process_form_submission(context, **params):
    """
    E2E test workflow that processes form submissions.
    Accepts any parameters and returns success.
    """
    return {
        "status": "success",
        "message": "Form processed successfully",
        "received_params": params
    }


@workflow(
    name="e2e_process_form",
    description="E2E: Generic form processor (test)",
    category="e2e_testing",
    tags=["e2e", "test", "forms"]
)
async def e2e_process_form(context, **params):
    """
    E2E generic test workflow for form processing.
    """
    return {
        "status": "processed",
        "data": params
    }


@workflow(
    name="e2e_process_submission",
    description="E2E: Process submission (test)",
    category="e2e_testing",
    tags=["e2e", "test", "forms"]
)
async def e2e_process_submission(context, **params):
    """
    E2E simple submission processor for testing.
    """
    return {
        "submitted": True,
        "timestamp": "2025-01-01T00:00:00Z"
    }


@workflow(
    name="e2e_process_simple_form",
    description="E2E: Process simple form (test)",
    category="e2e_testing",
    tags=["e2e", "test", "forms"]
)
async def e2e_process_simple_form(context, **params):
    """
    E2E simple form processor for basic tests.
    """
    return {"result": "ok"}


@workflow(
    name="e2e_process_conditional_form",
    description="E2E: Process conditional form (test)",
    category="e2e_testing",
    tags=["e2e", "test", "forms"]
)
async def e2e_process_conditional_form(context, **params):
    """
    E2E conditional form processor for visibility testing.
    """
    return {"processed": True, "params": params}
