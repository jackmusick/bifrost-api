"""
Role Repository
Manages roles and role assignments (user-role, form-role relationships)
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, cast

from shared.models import CreateRoleRequest, Role, UpdateRoleRequest, generate_entity_id
from shared.storage import TableStorageService

from .base import BaseRepository

if TYPE_CHECKING:
    from shared.context import ExecutionContext

logger = logging.getLogger(__name__)


class RoleRepository(BaseRepository):
    """
    Repository for roles and role assignments

    Roles are stored in Entities table with RowKey: role:{uuid}
    Role assignments stored in Relationships table:
    - User-Role: userrole:{user_id}:{role_uuid}
    - Form-Role: formrole:{form_id}:{role_uuid}
    """

    def __init__(self, context: 'ExecutionContext | None' = None):
        super().__init__("Entities", context)
        self.relationships_service = TableStorageService("Relationships")

    def create_role(
        self,
        role_request: CreateRoleRequest,
        org_id: str,
        created_by: str
    ) -> Role:
        """
        Create new role

        Args:
            role_request: Role creation request
            org_id: Organization ID
            created_by: User ID creating the role

        Returns:
            Created Role model
        """
        role_id = generate_entity_id()
        now = datetime.utcnow()

        role_entity = {
            "PartitionKey": org_id,
            "RowKey": f"role:{role_id}",
            "Name": role_request.name,
            "Description": role_request.description,
            "IsActive": True,
            "CreatedBy": created_by,
            "CreatedAt": now.isoformat(),
            "UpdatedAt": now.isoformat(),
        }

        self.insert(role_entity)

        logger.info(f"Created role {role_id} in org {org_id}: {role_request.name}")

        return self._entity_to_model(role_entity, role_id)

    def get_role(self, role_id: str, org_id: str) -> Role | None:
        """
        Get role by ID

        Args:
            role_id: Role ID (UUID)
            org_id: Organization ID

        Returns:
            Role model or None if not found
        """
        entity = self.get_by_id(org_id, f"role:{role_id}")

        if entity:
            return self._entity_to_model(entity, role_id)

        return None

    def list_roles(self, org_id: str, active_only: bool = True) -> list[Role]:
        """
        List all roles for an organization

        Args:
            org_id: Organization ID
            active_only: Only return active roles

        Returns:
            List of Role models
        """
        filter_query = f"PartitionKey eq '{org_id}' and RowKey ge 'role:' and RowKey lt 'role;'"

        if active_only:
            filter_query += " and IsActive eq true"

        entities = list(self.query(filter_query))

        roles = []
        for entity in entities:
            role_id = entity["RowKey"].split(":", 1)[1]
            roles.append(self._entity_to_model(entity, role_id))

        logger.info(f"Found {len(roles)} roles in org {org_id}")
        return roles

    def update_role(
        self,
        role_id: str,
        org_id: str,
        updates: UpdateRoleRequest
    ) -> Role:
        """
        Update role

        Args:
            role_id: Role ID
            org_id: Organization ID
            updates: Update request

        Returns:
            Updated Role model

        Raises:
            ValueError: If role not found
        """
        entity = self.get_by_id(org_id, f"role:{role_id}")

        if not entity:
            raise ValueError(f"Role {role_id} not found in organization {org_id}")

        now = datetime.utcnow()

        if updates.name is not None:
            entity["Name"] = updates.name

        if updates.description is not None:
            entity["Description"] = updates.description

        entity["UpdatedAt"] = now.isoformat()

        self.update(entity)

        logger.info(f"Updated role {role_id} in org {org_id}")
        return self._entity_to_model(entity, role_id)

    def assign_users_to_role(
        self,
        role_id: str,
        user_ids: list[str],
        assigned_by: str
    ) -> None:
        """
        Assign users to a role

        Creates relationships: userrole:{user_id}:{role_uuid}

        Args:
            role_id: Role ID (UUID)
            user_ids: List of user IDs to assign
            assigned_by: User ID who made the assignment
        """
        now = datetime.utcnow()

        for user_id in user_ids:
            relationship_entity = {
                "PartitionKey": "GLOBAL",
                "RowKey": f"userrole:{user_id}:{role_id}",
                "UserId": user_id,
                "RoleId": role_id,
                "AssignedBy": assigned_by,
                "AssignedAt": now.isoformat(),
            }

            try:
                self.relationships_service.insert_entity(relationship_entity)
                logger.debug(f"Assigned user {user_id} to role {role_id}")
            except Exception as e:
                logger.warning(f"Failed to assign user {user_id} to role {role_id}: {e}")

        logger.info(f"Assigned {len(user_ids)} users to role {role_id}")

    def assign_forms_to_role(
        self,
        role_id: str,
        form_ids: list[str],
        assigned_by: str
    ) -> None:
        """
        Assign forms to a role

        Creates relationships: formrole:{form_id}:{role_uuid}

        Args:
            role_id: Role ID (UUID)
            form_ids: List of form IDs to assign
            assigned_by: User ID who made the assignment
        """
        now = datetime.utcnow()

        for form_id in form_ids:
            relationship_entity = {
                "PartitionKey": "GLOBAL",
                "RowKey": f"formrole:{form_id}:{role_id}",
                "FormId": form_id,
                "RoleId": role_id,
                "AssignedBy": assigned_by,
                "AssignedAt": now.isoformat(),
            }

            try:
                self.relationships_service.insert_entity(relationship_entity)
                logger.debug(f"Assigned form {form_id} to role {role_id}")
            except Exception as e:
                logger.warning(f"Failed to assign form {form_id} to role {role_id}: {e}")

        logger.info(f"Assigned {len(form_ids)} forms to role {role_id}")

    def get_user_role_ids(self, user_id: str) -> list[str]:
        """
        Get all role IDs assigned to a user

        Args:
            user_id: User ID

        Returns:
            List of role UUIDs
        """
        query_filter = (
            f"PartitionKey eq 'GLOBAL' and "
            f"RowKey ge 'userrole:{user_id}:' and "
            f"RowKey lt 'userrole:{user_id}~'"
        )

        entities = list(self.relationships_service.query_entities(query_filter))

        # Extract role UUID from RowKey "userrole:{user_id}:{role_uuid}"
        role_ids = [entity["RowKey"].split(":", 2)[2] for entity in entities]

        logger.debug(f"Found {len(role_ids)} roles for user {user_id}")
        return role_ids

    def get_form_role_ids(self, form_id: str) -> list[str]:
        """
        Get all role IDs that can access a form

        Args:
            form_id: Form ID (UUID)

        Returns:
            List of role UUIDs
        """
        query_filter = (
            f"PartitionKey eq 'GLOBAL' and "
            f"RowKey ge 'formrole:{form_id}:' and "
            f"RowKey lt 'formrole:{form_id}~'"
        )

        entities = list(self.relationships_service.query_entities(query_filter))

        # Extract role UUID from RowKey "formrole:{form_id}:{role_uuid}"
        role_ids = [entity["RowKey"].split(":", 2)[2] for entity in entities]

        logger.debug(f"Found {len(role_ids)} roles for form {form_id}")
        return role_ids

    def get_role_user_ids(self, role_id: str) -> list[str]:
        """
        Get all user IDs assigned to a role (reverse lookup)

        Args:
            role_id: Role ID (UUID)

        Returns:
            List of user IDs
        """
        query_filter = f"PartitionKey eq 'GLOBAL' and RowKey ge 'userrole:' and RowKey lt 'userrole~' and RoleId eq '{role_id}'"

        entities = list(self.relationships_service.query_entities(query_filter))

        user_ids = [cast(str, entity["UserId"]) for entity in entities if "UserId" in entity and entity["UserId"]]

        logger.debug(f"Found {len(user_ids)} users for role {role_id}")
        return user_ids

    def get_role_form_ids(self, role_id: str) -> list[str]:
        """
        Get all form IDs assigned to a role (reverse lookup)

        Args:
            role_id: Role ID (UUID)

        Returns:
            List of form IDs
        """
        query_filter = f"PartitionKey eq 'GLOBAL' and RowKey ge 'formrole:' and RowKey lt 'formrole~' and RoleId eq '{role_id}'"

        entities = list(self.relationships_service.query_entities(query_filter))

        form_ids = [cast(str, entity["FormId"]) for entity in entities if "FormId" in entity and entity["FormId"]]

        logger.debug(f"Found {len(form_ids)} forms for role {role_id}")
        return form_ids

    def delete_role(self, role_id: str, org_id: str) -> bool:
        """
        Soft delete role (sets IsActive=False)

        Args:
            role_id: Role ID to delete
            org_id: Organization ID

        Returns:
            True if deleted, False if not found
        """
        entity = self.get_by_id(org_id, f"role:{role_id}")

        if not entity:
            return False

        # Soft delete - set IsActive to False
        entity["IsActive"] = False
        entity["UpdatedAt"] = datetime.utcnow().isoformat()

        self.update(entity)

        logger.info(f"Soft deleted role {role_id} in org {org_id}")
        return True

    def remove_user_from_role(self, role_id: str, user_id: str) -> bool:
        """
        Remove user from role assignment

        Args:
            role_id: Role ID
            user_id: User ID to remove

        Returns:
            True if removed, False if assignment not found
        """
        # Delete forward index: userrole:{user_id}:{role_uuid}
        forward_key = f"userrole:{user_id}:{role_id}"
        # Delete reverse index: roleuser:{role_uuid}:{user_id}
        reverse_key = f"roleuser:{role_id}:{user_id}"

        deleted = False

        try:
            self.relationships_service.delete_entity("GLOBAL", forward_key)
            deleted = True
            logger.debug(f"Deleted forward user-role index: {forward_key}")
        except Exception as e:
            logger.debug(f"Forward index not found: {forward_key} ({e})")

        try:
            self.relationships_service.delete_entity("GLOBAL", reverse_key)
            deleted = True
            logger.debug(f"Deleted reverse user-role index: {reverse_key}")
        except Exception as e:
            logger.debug(f"Reverse index not found: {reverse_key} ({e})")

        if deleted:
            logger.info(f"Removed user {user_id} from role {role_id}")

        return deleted

    def remove_form_from_role(self, role_id: str, form_id: str) -> bool:
        """
        Remove form from role assignment

        Args:
            role_id: Role ID
            form_id: Form ID to remove

        Returns:
            True if removed, False if assignment not found
        """
        # Delete forward index: formrole:{form_id}:{role_uuid}
        forward_key = f"formrole:{form_id}:{role_id}"
        # Delete reverse index: roleform:{role_uuid}:{form_id}
        reverse_key = f"roleform:{role_id}:{form_id}"

        deleted = False

        try:
            self.relationships_service.delete_entity("GLOBAL", forward_key)
            deleted = True
            logger.debug(f"Deleted forward form-role index: {forward_key}")
        except Exception as e:
            logger.debug(f"Forward index not found: {forward_key} ({e})")

        try:
            self.relationships_service.delete_entity("GLOBAL", reverse_key)
            deleted = True
            logger.debug(f"Deleted reverse form-role index: {reverse_key}")
        except Exception as e:
            logger.debug(f"Reverse index not found: {reverse_key} ({e})")

        if deleted:
            logger.info(f"Removed form {form_id} from role {role_id}")

        return deleted

    def _entity_to_model(self, entity: dict, role_id: str) -> Role:
        """
        Convert entity dict to Role model

        Args:
            entity: Entity dictionary from table storage
            role_id: Role ID

        Returns:
            Role model
        """
        # Parse datetime fields
        created_at = cast(datetime, self._parse_datetime(entity.get("CreatedAt"), datetime.utcnow()))
        updated_at = cast(datetime, self._parse_datetime(entity.get("UpdatedAt"), datetime.utcnow()))

        return Role(
            id=role_id,
            name=cast(str, entity.get("Name", "")),
            description=entity.get("Description"),
            isActive=entity.get("IsActive", True),
            createdBy=cast(str, entity.get("CreatedBy", "")),
            createdAt=created_at,
            updatedAt=updated_at,
        )
