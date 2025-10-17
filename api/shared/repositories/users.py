"""
User Repository
Manages users and user-organization relationships
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, cast

from shared.models import User, UserType
from shared.storage import TableStorageService

from .base import BaseRepository

if TYPE_CHECKING:
    from shared.request_context import RequestContext

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository):
    """
    Repository for users

    Users are stored in Entities table (GLOBAL partition) with RowKey: user:{email}
    User-org relationships stored in Relationships table with dual indexes:
    - Forward: userperm:{email}:{org_id}
    - Reverse: orgperm:{org_id}:{email}
    """

    def __init__(self, context: 'RequestContext | None' = None):
        super().__init__("Entities", context)
        self.relationships_service = TableStorageService("Relationships")

    def has_any_users(self) -> bool:
        """
        Check if any users exist in the system

        Returns:
            True if at least one user exists, False otherwise
        """
        query_filter = "PartitionKey eq 'GLOBAL' and RowKey ge 'user:' and RowKey lt 'user;'"

        # Use select to only fetch RowKey for efficiency
        query_result = self.service.query_entities(query_filter, select=["RowKey"])

        # Check if any results exist
        first_user = next(iter(query_result), None)
        return first_user is not None

    def get_user(self, email: str) -> User | None:
        """
        Get user by email

        Args:
            email: User email

        Returns:
            User model or None if not found
        """
        entity = self.get_by_id("GLOBAL", f"user:{email}")

        if entity:
            return self._entity_to_model(entity)

        return None

    def create_user(
        self,
        email: str,
        display_name: str,
        user_type: UserType,
        is_platform_admin: bool = False
    ) -> User:
        """
        Create new user

        Args:
            email: User email
            display_name: Display name
            user_type: PLATFORM or ORG
            is_platform_admin: Whether user is platform admin

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

        self.insert(user_entity)

        logger.info(f"Created user {email} (type={user_type}, admin={is_platform_admin})")

        return self._entity_to_model(user_entity)

    def update_last_login(self, email: str) -> None:
        """
        Update user's last login timestamp

        Args:
            email: User email
        """
        entity = self.get_by_id("GLOBAL", f"user:{email}")

        if entity:
            entity["LastLogin"] = datetime.utcnow().isoformat()
            self.update(entity)

    def get_user_org_id(self, email: str) -> str | None:
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

        entities = list(self.relationships_service.query_entities(query_filter))

        if entities:
            # Extract org_id from RowKey "userperm:{email}:{org_id}"
            row_key = entities[0].get("RowKey")
            if row_key:
                parts = row_key.split(":", 2)
                if len(parts) >= 3:
                    return parts[2]

        return None

    def assign_user_to_org(self, email: str, org_id: str, assigned_by: str) -> None:
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
        self.relationships_service.insert_entity(forward_entity)
        self.relationships_service.insert_entity(reverse_entity)

        logger.info(f"Assigned user {email} to organization {org_id}")

    def list_org_users(self, org_id: str) -> list[str]:
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

        entities = list(self.relationships_service.query_entities(query_filter))

        # Extract email from RowKey "orgperm:{org_id}:{email}"
        user_emails = [entity["RowKey"].split(":", 2)[2] for entity in entities]

        logger.info(f"Found {len(user_emails)} users in organization {org_id}")
        return user_emails

    def list_org_users_full(self, org_id: str) -> list[User]:
        """
        List all users in an organization (full User models)

        Args:
            org_id: Organization ID

        Returns:
            List of User models
        """
        user_emails = self.list_org_users(org_id)

        users = []
        for email in user_emails:
            user = self.get_user(email)
            if user:
                users.append(user)

        return users

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

        return User(
            id=cast(str, entity.get("Email", "")),  # User ID is email
            email=cast(str, entity.get("Email", "")),
            displayName=cast(str, entity.get("DisplayName", "")),
            userType=UserType(entity.get("UserType", "ORG")),
            isPlatformAdmin=entity.get("IsPlatformAdmin", False),
            isActive=entity.get("IsActive", True),
            lastLogin=last_login,
            createdAt=created_at,
        )
