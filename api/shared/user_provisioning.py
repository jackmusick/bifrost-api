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
from datetime import datetime
from typing import Literal

from shared.storage import TableStorageService

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

    users_service = TableStorageService("Users")

    # Check if user already exists
    user_entity = users_service.get_entity(user_email, "user")

    if user_entity:
        # User exists - return current status
        user_type = user_entity.get("UserType", "ORG")
        is_platform_admin = user_entity.get("IsPlatformAdmin", False)

        # Update last login
        try:
            user_entity["LastLogin"] = datetime.utcnow().isoformat()
            users_service.update_entity(user_entity)
        except Exception as e:
            logger.warning(f"Failed to update last login for {user_email}: {e}")

        # Get org_id if ORG user
        org_id = None
        if user_type == "ORG":
            org_id = _get_user_org_id(user_email)

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

        logger.debug(f"User {user_email} already exists: type={user_type}, org={org_id}")

        return UserProvisioningResult(
            user_type=user_type,
            is_platform_admin=is_platform_admin,
            org_id=org_id,
            was_created=False,
        )

    # User doesn't exist - check if first user
    logger.info(f"User {user_email} not found, checking provisioning rules")

    # Efficiently check if ANY users exist (limit to 1 result)
    query_result = users_service.query_entities(
        "PartitionKey ne ''", select=["PartitionKey"]
    )
    first_user = next(iter(query_result), None)
    is_first_user = first_user is None

    if is_first_user:
        # First user in system - create as PlatformAdmin
        return _create_first_platform_admin(user_email)

    # Not first user - try domain-based auto-provisioning
    return _provision_user_by_domain(user_email)


def _create_first_platform_admin(user_email: str) -> UserProvisioningResult:
    """Create the first user as a PlatformAdmin"""
    logger.info(f"First user login detected! Auto-promoting {user_email} to PlatformAdmin")

    users_service = TableStorageService("Users")

    new_user = {
        "PartitionKey": user_email,
        "RowKey": "user",
        "Email": user_email,
        "DisplayName": user_email.split("@")[0],
        "UserType": "PLATFORM",
        "IsPlatformAdmin": True,
        "IsActive": True,
        "CreatedAt": datetime.utcnow().isoformat(),
        "LastLogin": datetime.utcnow().isoformat(),
    }

    users_service.insert_entity(new_user)
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

    # Query organizations with matching domain
    # This is efficient - we filter on IsActive and Domain in the query
    entities_service = TableStorageService("Entities")
    query_filter = (
        "PartitionKey eq 'GLOBAL' and "
        "RowKey ge 'org:' and RowKey lt 'org;' and "
        "IsActive eq true"
    )
    org_entities = list(entities_service.query_entities(query_filter))

    # Find matching domain (case-insensitive)
    matched_org = None
    for org_entity in org_entities:
        org_domain = org_entity.get("Domain")
        if org_domain and org_domain.lower() == user_domain:
            matched_org = org_entity
            logger.info(
                f"Found matching organization: {org_entity['Name']} with domain {org_domain}"
            )
            break

    if not matched_org:
        logger.warning(f"No organization found with domain: {user_domain}")
        raise ValueError(
            f"No organization configured for domain: {user_domain}. "
            f"Contact your administrator to be added manually."
        )

    # Extract org_id from RowKey "org:uuid"
    org_id = matched_org["RowKey"].split(":", 1)[1]

    # Create new ORG user
    users_service = TableStorageService("Users")
    new_user = {
        "PartitionKey": user_email,
        "RowKey": "user",
        "Email": user_email,
        "DisplayName": user_email.split("@")[0],
        "UserType": "ORG",
        "IsPlatformAdmin": False,
        "IsActive": True,
        "CreatedAt": datetime.utcnow().isoformat(),
        "LastLogin": datetime.utcnow().isoformat(),
    }

    users_service.insert_entity(new_user)
    logger.info(f"Auto-created ORG user: {user_email}")

    # Create user-org permission relationship in Relationships table
    relationships_service = TableStorageService("Relationships")
    permission_entity = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"userperm:{user_email}:{org_id}",
        "UserId": user_email,
        "OrganizationId": org_id,
        "CreatedAt": datetime.utcnow().isoformat(),
    }

    relationships_service.insert_entity(permission_entity)
    logger.info(f"Created org permission for {user_email} -> {org_id}")

    return UserProvisioningResult(
        user_type="ORG", is_platform_admin=False, org_id=org_id, was_created=True
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
    # Extract domain from email
    user_domain = user_email.split("@")[1].lower()
    logger.info(f"Looking for organization with domain: {user_domain}")

    # Query organizations with matching domain
    entities_service = TableStorageService("Entities")
    query_filter = (
        "PartitionKey eq 'GLOBAL' and "
        "RowKey ge 'org:' and RowKey lt 'org;' and "
        "IsActive eq true"
    )
    org_entities = list(entities_service.query_entities(query_filter))

    # Find matching domain (case-insensitive)
    matched_org = None
    for org_entity in org_entities:
        org_domain = org_entity.get("Domain")
        if org_domain and org_domain.lower() == user_domain:
            matched_org = org_entity
            logger.info(
                f"Found matching organization: {org_entity['Name']} with domain {org_domain}"
            )
            break

    if not matched_org:
        logger.warning(f"No organization found with domain: {user_domain}")
        raise ValueError(
            f"No organization configured for domain: {user_domain}. "
            f"Contact your administrator to be added manually."
        )

    # Extract org_id from RowKey "org:uuid"
    org_id = matched_org["RowKey"].split(":", 1)[1]

    # Create user-org permission relationship in Relationships table
    relationships_service = TableStorageService("Relationships")
    permission_entity = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"userperm:{user_email}:{org_id}",
        "UserId": user_email,
        "OrganizationId": org_id,
        "CreatedAt": datetime.utcnow().isoformat(),
    }

    relationships_service.insert_entity(permission_entity)
    logger.info(f"Created org permission for existing user {user_email} -> {org_id}")

    return org_id


def _get_user_org_id(email: str) -> str | None:
    """
    Look up user's organization ID from Relationships table.

    This is a lightweight query that only returns the first org assignment.
    """
    try:
        relationships_table = TableStorageService("Relationships")

        # Query for user permissions
        query_filter = (
            f"PartitionKey eq 'GLOBAL' and "
            f"RowKey ge 'userperm:{email}:' and "
            f"RowKey lt 'userperm:{email}~'"
        )
        entities = list(relationships_table.query_entities(query_filter))

        if not entities:
            return None

        # Extract org_id from RowKey "userperm:{email}:{org_id}"
        row_key = entities[0].get("RowKey")
        if row_key:
            parts = row_key.split(":", 2)
            if len(parts) >= 3:
                return parts[2]

        return None

    except Exception as e:
        logger.error(f"Error looking up user org: {e}")
        return None
