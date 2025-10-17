"""
User Auto-Provisioning Logic

Handles automatic user creation and organization assignment.
This logic is called from multiple places:
1. roles_source.py (for immediate role assignment in production)
2. request_context.py (for local dev and fallback)

Key Features:
- First user becomes PlatformAdmin automatically
- Subsequent users auto-join by email domain matching
- Idempotent - safe to call multiple times
- Efficient - uses targeted queries with early exits
"""

import logging
from typing import Literal

from shared.models import UserType
from shared.repositories.organizations import OrganizationRepository
from shared.repositories.users import UserRepository

logger = logging.getLogger(__name__)


class UserProvisioningResult:
    """Result of user provisioning attempt"""

    def __init__(
        self,
        user_type: Literal["PLATFORM", "ORG"],
        is_platform_admin: bool,
        org_id: str | None,
        was_created: bool,
    ):
        self.user_type = user_type
        self.is_platform_admin = is_platform_admin
        self.org_id = org_id
        self.was_created = was_created

    @property
    def roles(self) -> list[str]:
        """Get SWA-compatible roles for this user"""
        roles = ["authenticated"]
        if self.is_platform_admin:
            roles.append("PlatformAdmin")
        else:
            roles.append("OrgUser")
        return roles


def ensure_user_provisioned(user_email: str) -> UserProvisioningResult:
    """
    Ensure user exists in the system, creating if necessary.

    This function is idempotent and safe to call on every request.
    It uses efficient queries to minimize database calls.

    Auto-Provisioning Rules:
    1. First user in system → PlatformAdmin
    2. Subsequent users → Match email domain to organization
    3. No domain match → Return None (user must be manually added)

    Args:
        user_email: User's email address

    Returns:
        UserProvisioningResult with user type, admin status, and org_id

    Raises:
        ValueError: If email is invalid format
    """
    if not user_email or "@" not in user_email:
        raise ValueError(f"Invalid email format: {user_email}")

    logger.info(f"Processing user provisioning for {user_email}")

    user_repo = UserRepository()

    # Check if user already exists
    user = user_repo.get_user(user_email)

    if user:
        # User exists - return current status
        logger.info(f"Existing user: type={user.userType.value}, is_platform_admin={user.isPlatformAdmin}")

        # Update last login
        try:
            user_repo.update_last_login(user_email)
        except Exception as e:
            logger.warning(f"Failed to update last login for {user_email}: {e}")

        # Get org_id if ORG user
        org_id = None
        if user.userType == UserType.ORG:
            org_id = user_repo.get_user_org_id(user_email)
            logger.info(f"Retrieved org_id for {user_email}: {org_id}")

            # If ORG user has no org assignment, try to auto-provision by domain
            if not org_id:
                logger.warning(
                    f"ORG user {user_email} exists but has no org assignment. "
                    f"Attempting domain-based auto-provisioning."
                )
                try:
                    # Try to match domain and create relationship
                    org_id = _provision_org_relationship_by_domain(user_email)
                    logger.info(f"Auto-provisioned org relationship for {user_email} -> {org_id}")
                except ValueError as e:
                    logger.error(f"Failed to auto-provision org relationship: {e}")
                    # Re-raise so caller knows provisioning failed
                    raise

        logger.debug(f"User {user_email} already exists: type={user.userType.value}, org={org_id}")

        return UserProvisioningResult(
            user_type=user.userType.value,
            is_platform_admin=user.isPlatformAdmin,
            org_id=org_id,
            was_created=False,
        )

    # User doesn't exist - check if first user
    logger.info(f"User {user_email} not found, checking provisioning rules")

    # Check if ANY users exist using repository
    has_users = user_repo.has_any_users()
    is_first_user = not has_users

    if is_first_user:
        # First user in system - create as PlatformAdmin
        return _create_first_platform_admin(user_email)

    # Not first user - try domain-based auto-provisioning
    return _provision_user_by_domain(user_email)


def _create_first_platform_admin(user_email: str) -> UserProvisioningResult:
    """Create the first user as a PlatformAdmin"""
    logger.info(f"First user login detected! Auto-promoting {user_email} to PlatformAdmin")

    user_repo = UserRepository()

    _ = user_repo.create_user(
        email=user_email,
        display_name=user_email.split("@")[0],
        user_type=UserType.PLATFORM,
        is_platform_admin=True
    )

    logger.info(f"Successfully created first user as PlatformAdmin: {user_email}")

    return UserProvisioningResult(
        user_type="PLATFORM", is_platform_admin=True, org_id=None, was_created=True
    )


def _provision_user_by_domain(user_email: str) -> UserProvisioningResult:
    """
    Attempt to provision user by matching email domain to organization.

    Returns None if no matching organization found.
    """
    logger.info(f"Attempting domain-based auto-provisioning for {user_email}")

    # Extract domain from email
    user_domain = user_email.split("@")[1].lower()
    logger.info(f"Looking for organization with domain: {user_domain}")

    # Query organizations with matching domain using repository
    org_repo = OrganizationRepository()
    matched_org = org_repo.get_organization_by_domain(user_domain)

    if not matched_org:
        logger.warning(f"No organization found with domain: {user_domain}")
        raise ValueError(
            f"No organization configured for domain: {user_domain}. "
            f"Contact your administrator to be added manually."
        )

    logger.info(f"Found matching organization: {matched_org.name} with domain {matched_org.domain}")

    # Create new ORG user
    user_repo = UserRepository()
    _ = user_repo.create_user(
        email=user_email,
        display_name=user_email.split("@")[0],
        user_type=UserType.ORG,
        is_platform_admin=False
    )

    logger.info(f"Auto-created ORG user: {user_email}")

    # Create user-org permission relationship (dual-index pattern)
    user_repo.assign_user_to_org(
        email=user_email,
        org_id=matched_org.id,
        assigned_by="system"
    )

    logger.info(f"Created org permission for {user_email} -> {matched_org.id}")

    return UserProvisioningResult(
        user_type="ORG", is_platform_admin=False, org_id=matched_org.id, was_created=True
    )


def _provision_org_relationship_by_domain(user_email: str) -> str:
    """
    Create org relationship for existing user by matching email domain.

    This is for users who exist but have no org assignment (orphaned users).

    Args:
        user_email: User's email address

    Returns:
        org_id: The organization ID that was matched and assigned

    Raises:
        ValueError: If no matching organization found
    """
    # Extract domain
    user_domain = user_email.split("@")[1].lower()
    logger.info(f"Looking for organization with domain: {user_domain}")

    user_repo = UserRepository()

    # Check if a relationship already exists (even if not found in previous query)
    existing_org_id = user_repo.get_user_org_id(user_email)

    if existing_org_id:
        logger.info(f"Found existing relationship for {user_email}: {existing_org_id}")
        return existing_org_id

    # Query organizations with matching domain using repository
    org_repo = OrganizationRepository()
    matched_org = org_repo.get_organization_by_domain(user_domain)

    if not matched_org:
        logger.warning(f"No organization found with domain: {user_domain}")
        raise ValueError(
            f"No organization configured for domain: {user_domain}. "
            f"Contact your administrator to be added manually."
        )

    logger.info(f"Found matching organization: {matched_org.name} with domain {matched_org.domain}")

    # Create user-org permission relationship (dual-index pattern handled by repository)
    user_repo.assign_user_to_org(
        email=user_email,
        org_id=matched_org.id,
        assigned_by="system"
    )

    logger.info(f"Created org permission for {user_email} -> {matched_org.id}")

    return matched_org.id


def _get_user_org_id(email: str) -> str | None:
    """
    Look up user's organization ID from Relationships table.

    This is a lightweight query that only returns the first org assignment.
    """
    try:
        user_repo = UserRepository()
        return user_repo.get_user_org_id(email)
    except Exception as e:
        logger.error(f"Error looking up user org: {e}")
        return None
