"""
Organization management SDK for Bifrost.

Provides Python API for organization operations from workflows.

All methods are async and must be called with await.
"""

from __future__ import annotations

from typing import Any

from shared.handlers.organizations_handlers import (
    create_organization_logic,
    delete_organization_logic,
    get_organization_logic,
    list_organizations_logic,
    update_organization_logic,
)
from shared.models import Organization

from ._internal import get_context, require_admin


class organizations:
    """
    Organization management operations.

    All methods enforce permissions via the execution context.
    All methods are async and must be awaited.
    """

    @staticmethod
    async def create(name: str, domain: str | None = None, is_active: bool = True) -> Organization:
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
            >>> org = await organizations.create("Acme Corp", domain="acme.com")
        """
        context = require_admin()

        return await create_organization_logic(
            context=context,
            name=name,
            domain=domain,
            is_active=is_active
        )

    @staticmethod
    async def get(org_id: str) -> Organization:
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
            >>> org = await organizations.get("org-123")
            >>> print(org.name)
        """
        context = get_context()

        org = await get_organization_logic(context, org_id)

        if not org:
            raise ValueError(f"Organization not found: {org_id}")

        return org

    @staticmethod
    async def list() -> list[Organization]:
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
            >>> orgs = await organizations.list()
            >>> for org in orgs:
            ...     print(f"{org.name}: {org.domain}")
        """
        context = require_admin()

        return await list_organizations_logic(context)

    @staticmethod
    async def update(org_id: str, **updates: Any) -> Organization:
        """
        Update an organization.

        Requires: Platform admin privileges

        Args:
            org_id: Organization ID
            **updates: Fields to update (name, domain, isActive)

        Returns:
            Organization: Updated organization object

        Raises:
            PermissionError: If user is not platform admin
            ValueError: If organization not found or validation fails
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import organizations
            >>> org = await organizations.update("org-123", name="New Name")
        """
        context = require_admin()

        org = await update_organization_logic(
            context=context,
            org_id=org_id,
            **updates
        )

        if not org:
            raise ValueError(f"Organization not found: {org_id}")

        return org

    @staticmethod
    async def delete(org_id: str) -> bool:
        """
        Delete an organization.

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
            >>> deleted = await organizations.delete("org-123")
        """
        context = require_admin()

        return await delete_organization_logic(context, org_id)
