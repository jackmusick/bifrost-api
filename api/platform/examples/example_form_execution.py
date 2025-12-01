"""
Test workflows for form context and visibility testing
These workflows are used by integration tests to validate form context features
"""

from shared.decorators import workflow


@workflow(
    name="workflows_load_customer_licenses",
    description="Load customer license information for form context",
    category="Testing",
    tags=["test", "forms"]
)
async def load_customer_licenses(context):
    """
    Test workflow that returns customer license data for form context
    Used to test launch workflow functionality
    """
    return {
        "available_licenses": ["Microsoft 365 E3", "Microsoft 365 E5", "Office 365 E1"],
        "license_count": 3,
        "has_licenses": True
    }


@workflow(
    name="workflows_check_available_licenses",
    description="Check available licenses for form visibility",
    category="Testing",
    tags=["test", "forms"]
)
async def check_available_licenses(context):
    """
    Test workflow for license availability checks
    Returns license information for field visibility
    """
    return {
        "has_e3_licenses": True,
        "has_e5_licenses": False,
        "total_available": 10
    }


@workflow(
    name="workflows_check_user_exists",
    description="Check if user exists in system",
    category="Testing",
    tags=["test", "forms"]
)
async def check_user_exists(context):
    """
    Test workflow to check user existence
    Used for testing field visibility based on user status
    """
    return {
        "user_exists": True,
        "user_name": "John Doe",
        "user_email": "john.doe@example.com"
    }


@workflow(
    name="workflows_check_user_permissions",
    description="Check user permissions for form access",
    category="Testing",
    tags=["test", "forms"]
)
async def check_user_permissions(context):
    """
    Test workflow to check user permissions
    Returns permission data for conditional form fields
    """
    return {
        "is_admin": True,
        "can_approve": True,
        "department": "IT"
    }


@workflow(
    name="workflows_process_form_submission",
    description="Process form submission (test workflow)",
    category="Testing",
    tags=["test", "forms"]
)
async def process_form_submission(context, **params):
    """
    Test workflow that processes form submissions
    Accepts any parameters and returns success
    """
    return {
        "status": "success",
        "message": "Form processed successfully",
        "received_params": params
    }


@workflow(
    name="workflows_process_form",
    description="Generic form processor (test)",
    category="Testing",
    tags=["test", "forms"]
)
async def process_form(context, **params):
    """
    Generic test workflow for form processing
    """
    return {
        "status": "processed",
        "data": params
    }


@workflow(
    name="workflows_process_submission",
    description="Process submission (test)",
    category="Testing",
    tags=["test", "forms"]
)
async def process_submission(context, **params):
    """
    Simple submission processor for testing
    """
    return {
        "submitted": True,
        "timestamp": "2025-01-01T00:00:00Z"
    }


@workflow(
    name="workflows_process_simple_form",
    description="Process simple form (test)",
    category="Testing",
    tags=["test", "forms"]
)
async def process_simple_form(context, **params):
    """
    Simple form processor for basic tests
    """
    return {"result": "ok"}


@workflow(
    name="workflows_process_conditional_form",
    description="Process conditional form (test)",
    category="Testing",
    tags=["test", "forms"]
)
async def process_conditional_form(context, **params):
    """
    Conditional form processor for visibility testing
    """
    return {"processed": True, "params": params}
