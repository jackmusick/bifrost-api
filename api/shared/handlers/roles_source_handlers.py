"""
Roles Source Handlers
Business logic for Azure Static Web Apps role provisioning
Extracted from functions/roles_source.py for unit testability
"""

import logging
from typing import TypedDict

from shared.user_provisioning import ensure_user_provisioned

logger = logging.getLogger(__name__)


class RolesSourceRequest(TypedDict, total=False):
    """Type definition for SWA roles source request"""

    identityProvider: str
    userId: str
    userDetails: str
    claims: list[dict]


class RolesSourceResponse(TypedDict):
    """Type definition for SWA roles source response"""

    roles: list[str]


def extract_user_info(request_body: dict) -> tuple[str | None, str | None]:
    """
    Extract user ID and email from SWA request.

    Args:
        request_body: Parsed JSON request body from SWA

    Returns:
        tuple: (user_id, user_email) - either may be None if not provided
    """
    user_id = request_body.get("userId")
    user_email = request_body.get("userDetails")
    return user_id, user_email


def get_roles_for_user(user_email: str) -> RolesSourceResponse:
    """
    Determine roles for a user through provisioning.

    This function:
    1. Ensures user exists in the system (creates if needed)
    2. Applies auto-provisioning rules (first user = admin, domain matching)
    3. Returns SWA-compatible role list

    Args:
        user_email: User's email address from authentication provider

    Returns:
        RolesSourceResponse: Dictionary with "roles" key containing list of role strings

    Raises:
        ValueError: If user cannot be provisioned (e.g., no domain match)
    """
    logger.info(f"Getting roles for user: {user_email}")

    try:
        # Ensure user is provisioned (handles first user, domain-based join, etc.)
        result = ensure_user_provisioned(user_email)

        # Return roles based on provisioning result
        response: RolesSourceResponse = {"roles": result.roles}
        logger.info(f"Returning roles for {user_email}: {result.roles}")

        return response

    except ValueError as e:
        # User could not be auto-provisioned (no domain match)
        logger.warning(f"User {user_email} could not be provisioned: {e}")
        raise


def handle_roles_source_request(request_body: dict) -> RolesSourceResponse:
    """
    Handle a complete roles source request from SWA.

    This is the main entry point for the roles source endpoint.
    It orchestrates extracting user info, provisioning, and returning roles.

    Request format from SWA:
    {
      "identityProvider": "aad",
      "userId": "user-id-from-azure-ad",
      "userDetails": "user@example.com",
      "claims": [...]
    }

    Returns:
    {
      "roles": ["PlatformAdmin", "CanExecuteWorkflows", "CanManageForms"]
    }

    Args:
        request_body: Parsed JSON request body from SWA

    Returns:
        RolesSourceResponse: Dictionary with "roles" key

    Raises:
        ValueError: If request is missing required fields or user provisioning fails
    """
    logger.info("Handling roles source request from SWA")

    # Extract user information
    user_id, user_email = extract_user_info(request_body)

    if not user_id or not user_email:
        logger.warning("No userId/userDetails provided in GetRoles request")
        # Return anonymous role for missing credentials
        return {"roles": ["anonymous"]}

    # Get roles for the user
    return get_roles_for_user(user_email)
