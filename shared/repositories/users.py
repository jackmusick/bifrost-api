"""
User Repository
Manages users and user-organization relationships
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, cast

from shared.models import User, UserType
from shared.async_storage import AsyncTableStorageService

from .base import BaseRepository

if TYPE_CHECKING:
    from shared.context import ExecutionContext

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository):
    """
    Repository for users

    Users are stored in Entities table (GLOBAL partition) with RowKey: user:{email}
    User-org relationships stored in Relationships table with dual indexes:
    - Forward: userperm:{email}:{org_id}
    - Reverse: orgperm:{org_id}:{email}
    """

    def __init__(self, context: 'ExecutionContext | None' = None):
        super().__init__("Entities", context)
        self.relationships_service = AsyncTableStorageService("Relationships")

    async def has_any_users(self) -> bool:
        """
        Check if any users exist in the system

        Returns:
            True if at least one user exists, False otherwise
        """
        query_filter = "PartitionKey eq 'GLOBAL' and RowKey ge 'user:' and RowKey lt 'user;'"

        # Use select to only fetch RowKey for efficiency
        query_result = await self._service.query_entities(query_filter, select=["RowKey"])

        # Check if any results exist
        first_user = next(iter(query_result), None)
        return first_user is not None

    async def get_user(self, email: str) -> User | None:
        """
        Get user by email

        Args:
            email: User email

        Returns:
            User model or None if not found
        """
        entity = await self.get_by_id("GLOBAL", f"user:{email}")

        if entity:
            return self._entity_to_model(entity)

        return None

    async def get_user_by_entra_id(self, entra_user_id: str) -> User | None:
        """
        Get user by Entra (Azure AD) user ID

        This performs a partition scan, so it's slower than lookup by email.
        Use this for initial authentication when only the Entra ID is known.

        Args:
            entra_user_id: Azure AD user object ID (oid claim)

        Returns:
            User model or None if not found
        """
        query_filter = (
            f"PartitionKey eq 'GLOBAL' and "
            f"RowKey ge 'user:' and "
            f"RowKey lt 'user;' and "
            f"EntraUserId eq '{entra_user_id}'"
        )

        entities = await self._service.query_entities(query_filter)

        if entities:
            return self._entity_to_model(entities[0])

        return None

    async def create_user(
        self,
        email: str,
        display_name: str,
        user_type: UserType,
        is_platform_admin: bool = False,
        entra_user_id: str | None = None
    ) -> User:
        """
        Create new user

        Args:
            email: User email
            display_name: Display name
            user_type: PLATFORM or ORG
            is_platform_admin: Whether user is platform admin
            entra_user_id: Azure AD user object ID (oid claim)

        Returns:
            Created User model
        """
        now = datetime.utcnow()

        user_entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"user:{email}",
            "Email": email,
            "DisplayName": display_name,
            "UserType": user_type.value,
            "IsPlatformAdmin": is_platform_admin,
            "IsActive": True,
            "CreatedAt": now.isoformat(),
            "LastLogin": now.isoformat(),
        }

        # Add entra_user_id if provided
        if entra_user_id:
            user_entity["EntraUserId"] = entra_user_id
            user_entity["LastEntraIdSync"] = now.isoformat()

        await self.insert(user_entity)

        logger.info(f"Created user {email} (type={user_type}, admin={is_platform_admin}, entra_id={entra_user_id})")

        return self._entity_to_model(user_entity)

    async def update_last_login(self, email: str) -> None:
        """
        Update user's last login timestamp

        Args:
            email: User email
        """
        entity = await self.get_by_id("GLOBAL", f"user:{email}")

        if entity:
            entity["LastLogin"] = datetime.utcnow().isoformat()
            await self.update(entity)

    async def update_user_entra_id(self, email: str, entra_user_id: str) -> None:
        """
        Backfill Entra user ID for existing user

        This is called when we match a user by email but they don't have
        an Entra ID stored yet.

        Args:
            email: User email
            entra_user_id: Azure AD user object ID (oid claim)
        """
        entity = await self.get_by_id("GLOBAL", f"user:{email}")

        if entity:
            now = datetime.utcnow()
            entity["EntraUserId"] = entra_user_id
            entity["LastEntraIdSync"] = now.isoformat()
            await self.update(entity)
            logger.info(f"Backfilled Entra ID for {email}: {entra_user_id}")

    async def update_user_profile(self, old_email: str, new_email: str, display_name: str) -> User | None:
        """
        Update user's email and display name

        This is called when we match a user by Entra ID but their email/name has changed.
        Note: This involves deleting and recreating the entity because email is part of RowKey.

        Args:
            old_email: Current email (used for lookup)
            new_email: New email address
            display_name: New display name

        Returns:
            Updated User model or None if user not found
        """
        entity = await self.get_by_id("GLOBAL", f"user:{old_email}")

        if not entity:
            logger.warning(f"Cannot update profile: user {old_email} not found")
            return None

        # If email hasn't changed, just update display name
        if old_email == new_email:
            entity["DisplayName"] = display_name
            entity["LastEntraIdSync"] = datetime.utcnow().isoformat()
            await self.update(entity)
            logger.info(f"Updated display name for {old_email} to {display_name}")
            return self._entity_to_model(entity)

        # Email changed - need to delete old and create new
        # (because email is part of RowKey)
        logger.info(f"Email changed from {old_email} to {new_email}, migrating user entity")

        # Create new entity with updated email
        new_entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"user:{new_email}",
            "Email": new_email,
            "DisplayName": display_name,
            "UserType": entity.get("UserType"),
            "IsPlatformAdmin": entity.get("IsPlatformAdmin", False),
            "IsActive": entity.get("IsActive", True),
            "CreatedAt": entity.get("CreatedAt"),
            "LastLogin": datetime.utcnow().isoformat(),
            "EntraUserId": entity.get("EntraUserId"),
            "LastEntraIdSync": datetime.utcnow().isoformat(),
        }

        # Insert new entity
        await self.insert(new_entity)

        # Delete old entity
        await self._service.delete_entity("GLOBAL", f"user:{old_email}")

        logger.info(f"Migrated user from {old_email} to {new_email}")

        # Update relationships if this is an ORG user
        org_id = await self.get_user_org_id(old_email)
        if org_id:
            logger.info(f"Updating org relationships for migrated user {old_email} -> {new_email}")
            # Delete old relationships
            await self.relationships_service.delete_entity("GLOBAL", f"userperm:{old_email}:{org_id}")
            await self.relationships_service.delete_entity("GLOBAL", f"orgperm:{org_id}:{old_email}")
            # Create new relationships
            await self.assign_user_to_org(new_email, org_id, "system")

        return self._entity_to_model(new_entity)

    async def get_user_org_id(self, email: str) -> str | None:
        """
        Get user's organization ID from relationships

        Args:
            email: User email

        Returns:
            Organization ID or None if user has no org
        """
        query_filter = (
            f"PartitionKey eq 'GLOBAL' and "
            f"RowKey ge 'userperm:{email}:' and "
            f"RowKey lt 'userperm:{email}~'"
        )

        entities = await self.relationships_service.query_entities(query_filter)

        if entities:
            # Extract org_id from RowKey "userperm:{email}:{org_id}"
            row_key = entities[0].get("RowKey")
            if row_key:
                parts = row_key.split(":", 2)
                if len(parts) >= 3:
                    return parts[2]

        return None

    async def assign_user_to_org(self, email: str, org_id: str, assigned_by: str) -> None:
        """
        Assign user to organization (dual-index pattern)

        Creates two relationships:
        - Forward: userperm:{email}:{org_id} (user → org lookup)
        - Reverse: orgperm:{org_id}:{email} (org → users lookup)

        Args:
            email: User email
            org_id: Organization ID
            assigned_by: User ID who made the assignment
        """
        now = datetime.utcnow()

        # Forward relationship (user → org)
        forward_entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"userperm:{email}:{org_id}",
            "UserId": email,
            "OrganizationId": org_id,
            "CreatedAt": now.isoformat(),
            "CreatedBy": assigned_by,
        }

        # Reverse relationship (org → user)
        reverse_entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"orgperm:{org_id}:{email}",
            "UserId": email,
            "OrganizationId": org_id,
            "CreatedAt": now.isoformat(),
            "CreatedBy": assigned_by,
        }

        # Insert both (dual-index pattern)
        await self.relationships_service.insert_entity(forward_entity)
        await self.relationships_service.insert_entity(reverse_entity)

        logger.info(f"Assigned user {email} to organization {org_id}")

    async def list_org_users(self, org_id: str) -> list[str]:
        """
        List all users in an organization (emails only)

        Uses reverse index for efficient query.

        Args:
            org_id: Organization ID

        Returns:
            List of user emails
        """
        query_filter = (
            f"PartitionKey eq 'GLOBAL' and "
            f"RowKey ge 'orgperm:{org_id}:' and "
            f"RowKey lt 'orgperm:{org_id}~'"
        )

        entities = await self.relationships_service.query_entities(query_filter)

        # Extract email from RowKey "orgperm:{org_id}:{email}"
        user_emails = [entity["RowKey"].split(":", 2)[2] for entity in entities]

        logger.info(f"Found {len(user_emails)} users in organization {org_id}")
        return user_emails

    async def list_org_users_full(self, org_id: str) -> list[User]:
        """
        List all users in an organization (full User models)

        Args:
            org_id: Organization ID

        Returns:
            List of User models
        """
        user_emails = await self.list_org_users(org_id)

        users = []
        for email in user_emails:
            user = await self.get_user(email)
            if user:
                users.append(user)

        return users

    async def update_user(
        self,
        email: str,
        display_name: str | None = None,
        is_active: bool | None = None,
        is_platform_admin: bool | None = None,
        org_id: str | None = None,
        updated_by: str = "system"
    ) -> User | None:
        """
        Update user properties

        This method handles role transitions:
        - Promoting to Platform Admin: Sets isPlatformAdmin=True, userType=PLATFORM, removes org assignments
        - Demoting to Org User: Sets isPlatformAdmin=False, userType=ORG, requires org_id assignment

        Args:
            email: User email
            display_name: New display name (optional)
            is_active: New active status (optional)
            is_platform_admin: New platform admin status (optional)
            org_id: Organization ID (required when demoting to org user)
            updated_by: User ID who made the update

        Returns:
            Updated User model or None if user not found

        Raises:
            ValueError: If demoting to org user without providing org_id
        """
        entity = await self.get_by_id("GLOBAL", f"user:{email}")

        if not entity:
            logger.warning(f"Cannot update user: {email} not found")
            return None

        current_is_platform_admin = entity.get("IsPlatformAdmin", False)

        # Update fields if provided
        if display_name is not None:
            entity["DisplayName"] = display_name

        if is_active is not None:
            entity["IsActive"] = is_active

        # Handle platform admin role changes
        if is_platform_admin is not None:
            # Demoting from platform admin to org user
            if current_is_platform_admin and not is_platform_admin:
                if not org_id:
                    raise ValueError("org_id is required when demoting user to org user")

                logger.info(f"Demoting {email} from Platform Admin to Org User (org: {org_id})")
                entity["IsPlatformAdmin"] = False
                entity["UserType"] = UserType.ORG.value

                # Assign to organization
                await self.assign_user_to_org(email, org_id, updated_by)

            # Promoting from org user to platform admin
            elif not current_is_platform_admin and is_platform_admin:
                logger.info(f"Promoting {email} from Org User to Platform Admin")
                entity["IsPlatformAdmin"] = True
                entity["UserType"] = UserType.PLATFORM.value

                # Remove existing org assignments
                old_org_id = await self.get_user_org_id(email)
                if old_org_id:
                    logger.info(f"Removing org assignment for promoted user: {old_org_id}")
                    await self.remove_user_from_org(email, old_org_id)

        await self.update(entity)
        logger.info(f"Updated user {email}")

        return self._entity_to_model(entity)

    async def remove_user_from_org(self, email: str, org_id: str) -> None:
        """
        Remove user from organization (delete dual-index relationships)

        Args:
            email: User email
            org_id: Organization ID
        """
        # Delete forward relationship (user → org)
        try:
            await self.relationships_service.delete_entity("GLOBAL", f"userperm:{email}:{org_id}")
        except Exception as e:
            logger.warning(f"Failed to delete forward relationship: {e}")

        # Delete reverse relationship (org → user)
        try:
            await self.relationships_service.delete_entity("GLOBAL", f"orgperm:{org_id}:{email}")
        except Exception as e:
            logger.warning(f"Failed to delete reverse relationship: {e}")

        logger.info(f"Removed user {email} from organization {org_id}")

    def _entity_to_model(self, entity: dict) -> User:
        """
        Convert entity dict to User model

        Args:
            entity: Entity dictionary from table storage

        Returns:
            User model
        """
        # Parse datetime fields
        created_at = self._parse_datetime(entity.get("CreatedAt"), datetime.utcnow())
        last_login = self._parse_datetime(entity.get("LastLogin"), None)
        last_entra_id_sync = self._parse_datetime(entity.get("LastEntraIdSync"), None)

        return User(
            id=cast(str, entity.get("Email", "")),  # User ID is email
            email=cast(str, entity.get("Email", "")),
            displayName=cast(str, entity.get("DisplayName", "")),
            userType=UserType(entity.get("UserType", "ORG")),
            isPlatformAdmin=entity.get("IsPlatformAdmin", False),
            isActive=entity.get("IsActive", True),
            lastLogin=last_login,
            createdAt=created_at or datetime.utcnow(),  # Fallback to now if None
            entraUserId=entity.get("EntraUserId"),
            lastEntraIdSync=last_entra_id_sync,
        )
