"""
Organization management SDK for Bifrost.

Provides Python API for organization operations from workflows.

All methods are synchronous and can be called directly (no await needed).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select

from shared.models import Organization as OrganizationSchema
from src.models.orm import Organization

from ._db import get_sync_session
from ._internal import get_context, require_admin


def _org_to_schema(org: Organization) -> OrganizationSchema:
    """Convert ORM Organization to Pydantic OrganizationSchema."""
    return OrganizationSchema(
        id=str(org.id),
        name=org.name,
        domain=org.domain,
        is_active=org.is_active,
        created_by=org.created_by,
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


class organizations:
    """
    Organization management operations.

    All methods enforce permissions via the execution context.
    All methods are synchronous - no await needed.
    """

    @staticmethod
    def create(name: str, domain: str | None = None, is_active: bool = True) -> OrganizationSchema:
        """
        Create a new organization.

        Requires: Platform admin privileges

        Args:
            name: Organization name
            domain: Organization domain (optional)
            is_active: Whether the organization is active (default: True)

        Returns:
            Organization: Created organization object

        Raises:
            PermissionError: If user is not platform admin
            ValueError: If validation fails
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import organizations
            >>> org = organizations.create("Acme Corp", domain="acme.com")
        """
        context = require_admin()

        with get_sync_session() as db:
            org = Organization(
                name=name,
                domain=domain,
                is_active=is_active,
                created_by=context.user_id,
            )
            db.add(org)
            db.flush()
            db.refresh(org)
            return _org_to_schema(org)

    @staticmethod
    def get(org_id: str) -> OrganizationSchema:
        """
        Get organization by ID.

        Args:
            org_id: Organization ID

        Returns:
            Organization: Organization object

        Raises:
            ValueError: If organization not found
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import organizations
            >>> org = organizations.get("org-123")
            >>> print(org.name)
        """
        get_context()  # Validates user is authenticated
        org_uuid = UUID(org_id)

        with get_sync_session() as db:
            org = db.get(Organization, org_uuid)
            if not org:
                raise ValueError(f"Organization not found: {org_id}")
            return _org_to_schema(org)

    @staticmethod
    def list() -> list[OrganizationSchema]:
        """
        List all organizations.

        Requires: Platform admin privileges

        Returns:
            list[Organization]: List of organization objects

        Raises:
            PermissionError: If user is not platform admin
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import organizations
            >>> orgs = organizations.list()
            >>> for org in orgs:
            ...     print(f"{org.name}: {org.domain}")
        """
        require_admin()

        with get_sync_session() as db:
            query = (
                select(Organization)
                .where(Organization.is_active == True)
                .order_by(Organization.name)
            )
            result = db.execute(query)
            return [_org_to_schema(o) for o in result.scalars().all()]

    @staticmethod
    def update(org_id: str, **updates: Any) -> OrganizationSchema:
        """
        Update an organization.

        Requires: Platform admin privileges

        Args:
            org_id: Organization ID
            **updates: Fields to update (name, domain, is_active)

        Returns:
            Organization: Updated organization object

        Raises:
            PermissionError: If user is not platform admin
            ValueError: If organization not found or validation fails
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import organizations
            >>> org = organizations.update("org-123", name="New Name")
        """
        require_admin()
        org_uuid = UUID(org_id)

        with get_sync_session() as db:
            org = db.get(Organization, org_uuid)
            if not org:
                raise ValueError(f"Organization not found: {org_id}")

            if 'name' in updates:
                org.name = updates['name']
            if 'domain' in updates:
                org.domain = updates['domain']
            if 'is_active' in updates:
                org.is_active = updates['is_active']

            db.flush()
            db.refresh(org)
            return _org_to_schema(org)

    @staticmethod
    def delete(org_id: str) -> bool:
        """
        Delete an organization (soft delete - sets is_active to false).

        Requires: Platform admin privileges

        Args:
            org_id: Organization ID

        Returns:
            bool: True if organization was deleted

        Raises:
            PermissionError: If user is not platform admin
            ValueError: If organization not found
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import organizations
            >>> deleted = organizations.delete("org-123")
        """
        require_admin()
        org_uuid = UUID(org_id)

        with get_sync_session() as db:
            org = db.get(Organization, org_uuid)
            if not org:
                raise ValueError(f"Organization not found: {org_id}")
            org.is_active = False
            return True
