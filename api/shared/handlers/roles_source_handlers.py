"""
Roles Source Handlers
Business logic for identity provider role provisioning
"""

import logging
from typing import TypedDict

from shared.user_provisioning import ensure_user_provisioned

logger = logging.getLogger(__name__)


class RolesSourceRequest(TypedDict, total=False):
    """Type definition for identity provider roles source request"""

    identityProvider: str
    userId: str
    userDetails: str
    claims: list[dict]


class RolesSourceResponse(TypedDict):
    """Type definition for identity provider roles source response"""

    roles: list[str]


def extract_user_info(request_body: dict) -> tuple[str | None, str | None, str | None]:
    """
    Extract user ID, email, and display name from identity provider request.

    Args:
        request_body: Parsed JSON request body from identity provider

    Returns:
        tuple: (user_id, user_email, display_name) - any may be None if not provided
    """
    user_id = request_body.get("userId")
    user_email = request_body.get("userDetails")

    # Try to extract display name from claims if available
    display_name = None
    claims = request_body.get("claims", [])
    for claim in claims:
        if claim.get("typ") == "name":
            display_name = claim.get("val")
            break

    return user_id, user_email, display_name


async def get_roles_for_user(
    user_email: str,
    user_id: str | None = None,
    display_name: str | None = None
) -> RolesSourceResponse:
    """
    Determine roles for a user through provisioning.

    This function:
    1. Ensures user exists in the system (creates if needed)
    2. Applies auto-provisioning rules (first user = admin, domain matching)
    3. Returns identity provider-compatible role list

    Args:
        user_email: User's email address from authentication provider
        user_id: User object ID from identity provider, if available
        display_name: User's display name from auth provider

    Returns:
        RolesSourceResponse: Dictionary with "roles" key containing list of role strings

    Raises:
        ValueError: If user cannot be provisioned (e.g., no domain match)
    """
    logger.info(f"Getting roles for user: {user_email} (user_id={user_id})")

    try:
        # Ensure user is provisioned (handles first user, domain-based join, etc.)
        result = await ensure_user_provisioned(user_email, user_id, display_name)

        # Return roles based on provisioning result
        response: RolesSourceResponse = {"roles": result.roles}
        logger.info(f"Returning roles for {user_email}: {result.roles}")

        return response

    except ValueError as e:
        # User could not be auto-provisioned (no domain match)
        logger.warning(f"User {user_email} could not be provisioned: {e}")
        raise


async def handle_roles_source_request(request_body: dict) -> RolesSourceResponse:
    """
    Handle a complete roles source request from identity provider.

    This is the main entry point for the roles source endpoint.
    It orchestrates extracting user info, provisioning, and returning roles.

    Request format from identity provider:
    {
      "identityProvider": "aad",
      "userId": "user-id-from-provider",
      "userDetails": "user@example.com",
      "claims": [...]
    }

    Returns:
    {
      "roles": ["PlatformAdmin", "CanExecuteWorkflows", "CanManageForms"]
    }

    Args:
        request_body: Parsed JSON request body from identity provider

    Returns:
        RolesSourceResponse: Dictionary with "roles" key

    Raises:
        ValueError: If request is missing required fields or user provisioning fails
    """
    logger.info("Handling roles source request from identity provider")

    # Extract user information
    user_id, user_email, display_name = extract_user_info(request_body)

    if not user_email:
        logger.warning("No userDetails (email) provided in GetRoles request")
        # Return anonymous role for missing credentials
        return {"roles": ["anonymous"]}

    # Get roles for the user
    return await get_roles_for_user(user_email, user_id, display_name)
