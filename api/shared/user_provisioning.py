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

from src.models.schemas import UserType
from src.repositories.organizations import OrganizationRepository
from src.repositories.users import UserRepository

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


async def ensure_user_provisioned(
    user_email: str,
    entra_user_id: str | None = None,
    display_name: str | None = None
) -> UserProvisioningResult:
    """
    Ensure user exists in the system, creating if necessary.

    This function is idempotent and safe to call on every request.
    It uses efficient queries to minimize database calls.

    Auto-Provisioning Rules:
    1. First user in system → PlatformAdmin
    2. Subsequent users → Match email domain to organization
    3. No domain match → Return None (user must be manually added)

    Lookup Strategy (when entra_user_id provided):
    1. Look up by Entra user ID first (stable identifier)
    2. If found but email/name changed, update user profile
    3. If not found, look up by email
    4. If found by email but no Entra ID stored, backfill it

    Args:
        user_email: User's email address
        entra_user_id: Azure AD user object ID (oid claim), if available
        display_name: User's display name from auth provider

    Returns:
        UserProvisioningResult with user type, admin status, and org_id

    Raises:
        ValueError: If email is invalid format
    """
    if not user_email or "@" not in user_email:
        raise ValueError(f"Invalid email format: {user_email}")

    logger.info(f"Processing user provisioning for {user_email} (entra_id={entra_user_id})")

    user_repo = UserRepository()

    # Strategy 1: If we have Entra ID, look up by that first (most reliable)
    if entra_user_id:
        user = await user_repo.get_user_by_entra_id(entra_user_id)

        if user:
            logger.info(f"Found user by Entra ID: {user.email}")

            # Check if email or display name has changed
            email_changed = user.email != user_email
            name_changed = display_name and user.display_name != display_name

            if email_changed or name_changed:
                logger.info(
                    f"User profile changed - email: {user.email} -> {user_email}, "
                    f"name: {user.display_name} -> {display_name}"
                )
                updated_user = await user_repo.update_user_profile(
                    old_email=user.email,
                    new_email=user_email,
                    display_name=display_name or user.display_name
                )
                if updated_user:
                    user = updated_user

            # Update last login
            try:
                await user_repo.update_last_login(user.email)
            except Exception as e:
                logger.warning(f"Failed to update last login for {user.email}: {e}")

            # Get org_id if ORG user
            org_id = None
            if user.user_type == UserType.ORG:
                org_id = await user_repo.get_user_org_id(user.email)
                logger.info(f"Retrieved org_id for {user.email}: {org_id}")

                # If ORG user has no org assignment, try to auto-provision by domain
                if not org_id:
                    logger.warning(
                        f"ORG user {user.email} exists but has no org assignment. "
                        f"Attempting domain-based auto-provisioning."
                    )
                    try:
                        org_id = await _provision_org_relationship_by_domain(user.email)
                        logger.info(f"Auto-provisioned org relationship for {user.email} -> {org_id}")
                    except ValueError as e:
                        logger.error(f"Failed to auto-provision org relationship: {e}")
                        raise

            return UserProvisioningResult(
                user_type=user.user_type.value,
                is_platform_admin=user.is_platform_admin,
                org_id=org_id,
                was_created=False,
            )

    # Strategy 2: Look up by email
    user = await user_repo.get_user(user_email)

    if user:
        logger.info(f"Found user by email: {user_email}")

        # If we have Entra ID but user doesn't, backfill it
        if entra_user_id and not user.entra_user_id:
            logger.info(f"Backfilling Entra ID for {user_email}")
            await user_repo.update_user_entra_id(user_email, entra_user_id)

        # Update last login
        try:
            await user_repo.update_last_login(user_email)
        except Exception as e:
            logger.warning(f"Failed to update last login for {user_email}: {e}")

        # Get org_id if ORG user
        org_id = None
        if user.user_type == UserType.ORG:
            org_id = await user_repo.get_user_org_id(user_email)
            logger.info(f"Retrieved org_id for {user_email}: {org_id}")

            # If ORG user has no org assignment, try to auto-provision by domain
            if not org_id:
                logger.warning(
                    f"ORG user {user_email} exists but has no org assignment. "
                    f"Attempting domain-based auto-provisioning."
                )
                try:
                    org_id = await _provision_org_relationship_by_domain(user_email)
                    logger.info(f"Auto-provisioned org relationship for {user_email} -> {org_id}")
                except ValueError as e:
                    logger.error(f"Failed to auto-provision org relationship: {e}")
                    raise

        return UserProvisioningResult(
            user_type=user.user_type.value,
            is_platform_admin=user.is_platform_admin,
            org_id=org_id,
            was_created=False,
        )

    # User doesn't exist - check if first user
    logger.info(f"User {user_email} not found, checking provisioning rules")

    # Check if ANY users exist using repository
    has_users = await user_repo.has_any_users()
    is_first_user = not has_users

    if is_first_user:
        # First user in system - create as PlatformAdmin
        return await _create_first_platform_admin(user_email, entra_user_id, display_name)

    # Not first user - try domain-based auto-provisioning
    return await _provision_user_by_domain(user_email, entra_user_id, display_name)


async def _create_first_platform_admin(
    user_email: str,
    entra_user_id: str | None = None,
    display_name: str | None = None
) -> UserProvisioningResult:
    """Create the first user as a PlatformAdmin"""
    logger.info(f"First user login detected! Auto-promoting {user_email} to PlatformAdmin")

    user_repo = UserRepository()

    _ = await user_repo.create_user(
        email=user_email,
        display_name=display_name or user_email.split("@")[0],
        user_type=UserType.PLATFORM,
        is_platform_admin=True,
        entra_user_id=entra_user_id
    )

    logger.info(f"Successfully created first user as PlatformAdmin: {user_email}")

    return UserProvisioningResult(
        user_type="PLATFORM", is_platform_admin=True, org_id=None, was_created=True
    )


async def _provision_user_by_domain(
    user_email: str,
    entra_user_id: str | None = None,
    display_name: str | None = None
) -> UserProvisioningResult:
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
    matched_org = await org_repo.get_organization_by_domain(user_domain)

    if not matched_org:
        logger.warning(f"No organization found with domain: {user_domain}")
        raise ValueError(
            f"No organization configured for domain: {user_domain}. "
            f"Contact your administrator to be added manually."
        )

    logger.info(f"Found matching organization: {matched_org.name} with domain {matched_org.domain}")

    # Create new ORG user
    user_repo = UserRepository()
    _ = await user_repo.create_user(
        email=user_email,
        display_name=display_name or user_email.split("@")[0],
        user_type=UserType.ORG,
        is_platform_admin=False,
        entra_user_id=entra_user_id
    )

    logger.info(f"Auto-created ORG user: {user_email}")

    # Create user-org permission relationship (dual-index pattern)
    await user_repo.assign_user_to_org(
        email=user_email,
        org_id=matched_org.id,
        assigned_by="system"
    )

    logger.info(f"Created org permission for {user_email} -> {matched_org.id}")

    return UserProvisioningResult(
        user_type="ORG", is_platform_admin=False, org_id=matched_org.id, was_created=True
    )


async def _provision_org_relationship_by_domain(user_email: str) -> str:
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
    existing_org_id = await user_repo.get_user_org_id(user_email)

    if existing_org_id:
        logger.info(f"Found existing relationship for {user_email}: {existing_org_id}")
        return existing_org_id

    # Query organizations with matching domain using repository
    org_repo = OrganizationRepository()
    matched_org = await org_repo.get_organization_by_domain(user_domain)

    if not matched_org:
        logger.warning(f"No organization found with domain: {user_domain}")
        raise ValueError(
            f"No organization configured for domain: {user_domain}. "
            f"Contact your administrator to be added manually."
        )

    logger.info(f"Found matching organization: {matched_org.name} with domain {matched_org.domain}")

    # Create user-org permission relationship (dual-index pattern handled by repository)
    await user_repo.assign_user_to_org(
        email=user_email,
        org_id=matched_org.id,
        assigned_by="system"
    )

    logger.info(f"Created org permission for {user_email} -> {matched_org.id}")

    return matched_org.id


async def _get_user_org_id(email: str) -> str | None:
    """
    Look up user's organization ID from Relationships table.

    This is a lightweight query that only returns the first org assignment.
    """
    try:
        user_repo = UserRepository()
        return await user_repo.get_user_org_id(email)
    except Exception as e:
        logger.error(f"Error looking up user org: {e}")
        return None
