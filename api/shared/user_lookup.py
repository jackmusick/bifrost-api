"""
User Lookup - Pure business logic for user existence and organization lookup

This module contains pure business logic that can be unit tested with mocked repositories.
It's separated from request_context.py (which handles HTTP concerns).
"""

import logging

from shared.models import UserType
from shared.repositories.users import UserRepository

logger = logging.getLogger(__name__)


def ensure_user_exists_in_db(email: str, is_platform_admin: bool) -> None:
    """
    Ensure user exists in Users table, creating if necessary.

    This is pure business logic - takes email and admin status, ensures user record exists.
    Used by request_context during authentication to handle development scenarios
    where GetRoles endpoint isn't called (e.g., local dev with direct headers).

    Args:
        email: User's email address
        is_platform_admin: Whether user has PlatformAdmin role (from SWA/GetRoles)

    Note:
        The user's role (PlatformAdmin vs OrgUser) comes from SWA/GetRoles,
        so we trust that as the source of truth.
    """
    user_repo = UserRepository()

    # Check if user exists
    user = user_repo.get_user(email)

    if user:
        # User exists - update last login
        try:
            user_repo.update_last_login(email)
        except Exception as e:
            logger.warning(f"Failed to update last login for {email}: {e}")
        return

    # User doesn't exist - create based on their role
    logger.info(f"Auto-creating user {email} (PlatformAdmin={is_platform_admin})")

    user_type = UserType.PLATFORM if is_platform_admin else UserType.ORG
    user_repo.create_user(
        email=email,
        display_name=email.split("@")[0],
        user_type=user_type,
        is_platform_admin=is_platform_admin
    )

    logger.info(f"Created user {email} in database")

    # If ORG user, try to auto-provision org relationship by domain
    if not is_platform_admin:
        try:
            from shared.user_provisioning import _provision_org_relationship_by_domain
            org_id = _provision_org_relationship_by_domain(email)
            if org_id:
                logger.info(f"Auto-provisioned org relationship for {email} -> {org_id}")
        except ValueError as e:
            logger.warning(f"Could not auto-provision org relationship: {e}")
            # Don't raise - user will get proper error when we try to get org_id


def get_user_organization(email: str) -> str | None:
    """
    Look up user's organization ID from database.

    Pure business logic - takes email, queries repository, returns org_id or None.

    Args:
        email: User's email address

    Returns:
        Organization ID if user has org assignment, None otherwise
    """
    try:
        user_repo = UserRepository()
        org_id = user_repo.get_user_org_id(email)

        if org_id:
            logger.debug(f"User {email} belongs to org: {org_id}")
        else:
            logger.warning(f"User {email} has no org assignments")

        return org_id

    except Exception as e:
        logger.error(f"Error looking up user org: {e}")
        return None
