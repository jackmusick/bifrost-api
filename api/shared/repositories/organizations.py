"""
Organization Repository
Manages organizations (always in GLOBAL partition)
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, cast

from shared.models import CreateOrganizationRequest, Organization, UpdateOrganizationRequest, generate_entity_id

from .base import BaseRepository

if TYPE_CHECKING:
    from shared.context import ExecutionContext

logger = logging.getLogger(__name__)


class OrganizationRepository(BaseRepository):
    """
    Repository for organizations

    Organizations are always stored in GLOBAL partition with RowKey: org:{uuid}
    """

    def __init__(self, context: 'ExecutionContext | None' = None):
        super().__init__("Entities", context)

    async def create_organization(
        self,
        org_request: CreateOrganizationRequest,
        created_by: str
    ) -> Organization:
        """
        Create new organization

        Args:
            org_request: Organization creation request
            created_by: User ID creating the organization

        Returns:
            Created Organization model
        """
        org_id = generate_entity_id()
        now = datetime.utcnow()

        org_entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"org:{org_id}",
            "Name": org_request.name,
            "Domain": org_request.domain,
            "IsActive": True,
            "CreatedAt": now.isoformat(),
            "CreatedBy": created_by,
            "UpdatedAt": now.isoformat(),
        }

        await self.insert(org_entity)

        logger.info(f"Created organization {org_id}: {org_request.name}")

        return Organization(
            id=org_id,
            name=org_request.name,
            domain=org_request.domain,
            isActive=True,
            createdAt=now,
            createdBy=created_by,
            updatedAt=now,
        )

    async def get_organization(self, org_id: str) -> Organization | None:
        """
        Get organization by ID

        Args:
            org_id: Organization ID (UUID)

        Returns:
            Organization model or None if not found
        """
        entity = await self.get_by_id("GLOBAL", f"org:{org_id}")

        if entity:
            return self._entity_to_model(entity, org_id)

        return None

    async def get_organization_by_domain(self, domain: str) -> Organization | None:
        """
        Get organization by domain (for auto-provisioning)

        Args:
            domain: Email domain (e.g., "acme.com")

        Returns:
            Organization model or None if not found
        """
        filter_query = (
            f"PartitionKey eq 'GLOBAL' and "
            f"RowKey ge 'org:' and RowKey lt 'org;' and "
            f"Domain eq '{domain.lower()}' and "
            f"IsActive eq true"
        )

        results = await self.query(filter_query)

        if results:
            org_id = results[0]["RowKey"].split(":", 1)[1]
            return self._entity_to_model(results[0], org_id)

        return None

    async def list_organizations(self, active_only: bool = True) -> list[Organization]:
        """
        List all organizations

        Args:
            active_only: Only return active organizations

        Returns:
            List of Organization models
        """
        filter_query = "PartitionKey eq 'GLOBAL' and RowKey ge 'org:' and RowKey lt 'org;'"

        if active_only:
            filter_query += " and IsActive eq true"

        entities = await self.query(filter_query)

        organizations = []
        for entity in entities:
            org_id = entity["RowKey"].split(":", 1)[1]
            organizations.append(self._entity_to_model(entity, org_id))

        logger.info(f"Found {len(organizations)} organizations (active_only={active_only})")
        return organizations

    async def update_organization(
        self,
        org_id: str,
        updates: UpdateOrganizationRequest
    ) -> Organization:
        """
        Update organization

        Args:
            org_id: Organization ID
            updates: Update request

        Returns:
            Updated Organization model

        Raises:
            ValueError: If organization not found
        """
        entity = await self.get_by_id("GLOBAL", f"org:{org_id}")

        if not entity:
            raise ValueError(f"Organization {org_id} not found")

        now = datetime.utcnow()

        if updates.name is not None:
            entity["Name"] = updates.name

        if updates.domain is not None:
            entity["Domain"] = updates.domain

        if updates.isActive is not None:
            entity["IsActive"] = updates.isActive

        entity["UpdatedAt"] = now.isoformat()

        await self.update(entity)

        logger.info(f"Updated organization {org_id}")
        return self._entity_to_model(entity, org_id)

    async def soft_delete_organization(self, org_id: str) -> bool:
        """
        Soft delete organization (set IsActive=False)

        Args:
            org_id: Organization ID

        Returns:
            True if deleted, False if not found
        """
        entity = await self.get_by_id("GLOBAL", f"org:{org_id}")

        if not entity:
            return False

        now = datetime.utcnow()
        entity["IsActive"] = False
        entity["UpdatedAt"] = now.isoformat()

        await self.update(entity)

        logger.info(f"Soft deleted organization {org_id}")
        return True

    async def delete_organization(self, org_id: str) -> bool:
        """
        Permanently delete organization.

        WARNING: This is a hard delete and will remove ALL organization data.
        Use soft_delete_organization for safer alternative.

        Args:
            org_id: Organization ID to permanently delete

        Returns:
            True if deleted, False if not found
        """
        entity = await self.get_by_id("GLOBAL", f"org:{org_id}")

        if not entity:
            logger.info(f"Cannot delete organization {org_id}: Not found")
            return False

        try:
            # Delete organization record
            await self.delete("GLOBAL", f"org:{org_id}")

            logger.info(f"Permanently deleted organization {org_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete organization {org_id}: {e}", exc_info=True)
            return False

    def _entity_to_model(self, entity: dict, org_id: str) -> Organization:
        """
        Convert entity dict to Organization model

        Args:
            entity: Entity dictionary from table storage
            org_id: Organization ID

        Returns:
            Organization model
        """
        # Parse datetime fields
        created_at = cast(datetime, self._parse_datetime(entity.get("CreatedAt"), datetime.utcnow()))
        updated_at = cast(datetime, self._parse_datetime(entity.get("UpdatedAt"), datetime.utcnow()))

        return Organization(
            id=org_id,
            name=cast(str, entity.get("Name", "")),
            domain=entity.get("Domain"),
            isActive=entity.get("IsActive", True),
            createdAt=created_at,
            createdBy=cast(str, entity.get("CreatedBy", "")),
            updatedAt=updated_at,
        )
