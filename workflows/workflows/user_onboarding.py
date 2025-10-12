"""
User Onboarding Workflow
Example workflow for onboarding new M365 users with license assignment
"""

from shared.decorators import workflow, param


@workflow(
    name="user_onboarding",
    description="Onboard new Microsoft 365 user with license assignment",
    category="user_management",
    tags=["m365", "user", "onboarding"]
)
@param(
    "first_name",
    type="string",
    label="First Name",
    required=True,
    help_text="User's first name"
)
@param(
    "last_name",
    type="string",
    label="Last Name",
    required=True,
    help_text="User's last name"
)
@param(
    "email",
    type="email",
    label="Email Address",
    required=True,
    validation={"pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"},
    help_text="User's email address (will become UPN)"
)
@param(
    "license",
    type="string",
    label="License Type",
    required=True,
    data_provider="get_available_licenses",
    help_text="Microsoft 365 license to assign"
)
@param(
    "department",
    type="string",
    label="Department",
    required=False,
    default_value="",
    help_text="User's department (optional)"
)
async def onboard_user(
    context,
    first_name: str,
    last_name: str,
    email: str,
    license: str,
    department: str = ""
):
    """
    Onboard a new Microsoft 365 user with the specified license.

    This workflow performs the following steps:
    1. Creates the user in Azure AD via Microsoft Graph
    2. Assigns the specified license
    3. Sets department if provided
    4. Sends welcome email
    5. Returns user details

    Args:
        context: OrganizationContext with org_id, credentials, etc.
        first_name: User's first name
        last_name: User's last name
        email: User's email address (becomes UPN)
        license: Microsoft 365 license SKU ID
        department: User's department (optional)

    Returns:
        dict: {
            "success": bool,
            "userId": str,
            "upn": str,
            "displayName": str,
            "message": str
        }
    """
    # Get pre-authenticated Microsoft Graph client from context
    # graph = context.get_integration('msgraph')

    # For now, return mock data (will implement actual Graph API calls later)
    display_name = f"{first_name} {last_name}"

    # Mock user creation
    result = {
        "success": True,
        "userId": f"mock-user-id-{email.split('@')[0]}",
        "upn": email,
        "displayName": display_name,
        "license": license,
        "department": department or "Not specified",
        "message": f"User {display_name} created successfully with license {license}"
    }

    # Log to execution context
    # await context.log("info", f"Created user {email}", result)

    return result
