"""
Roles management SDK for Bifrost.

Provides Python API for role operations (CRUD + user/form assignments).

All methods are async and must be called with await.
"""

from __future__ import annotations

from typing import Any

from shared.models import Role, CreateRoleRequest, UpdateRoleRequest
from shared.repositories.roles import RoleRepository

from ._internal import get_context, require_permission


class roles:
    """
    Role management operations.

    Provides CRUD operations for roles and user/form assignments.
    All methods are async and must be awaited.
    """

    @staticmethod
    async def create(name: str, description: str = "", permissions: list[str] | None = None) -> Role:
        """
        Create a new role.

        Requires: Platform admin or organization admin privileges

        Args:
            name: Role name
            description: Role description (optional)
            permissions: List of permission strings (optional)

        Returns:
            Role: Created role object

        Raises:
            PermissionError: If user lacks permission
            ValueError: If validation fails
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import roles
            >>> role = roles.create(
            ...     "Customer Manager",
            ...     description="Can manage customer data",
            ...     permissions=["customers.read", "customers.write"]
            ... )
        """
        context = require_permission("roles.create")
        repo = RoleRepository(context)

        role_request = CreateRoleRequest(
            name=name,
            description=description,
            permissions=permissions or []
        )

        return await repo.create_role(
            role_request=role_request,
            org_id=context.org_id,
            created_by=context.user_id
        )

    @staticmethod
    async def get(role_id: str) -> Role:
        """
        Get role by ID.

        Args:
            role_id: Role ID

        Returns:
            Role: Role object

        Raises:
            ValueError: If role not found
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import roles
            >>> role = roles.get("role-123")
            >>> print(role.name)
        """
        context = get_context()
        repo = RoleRepository(context)

        role = await repo.get_role(role_id, context.org_id)

        if not role:
            raise ValueError(f"Role not found: {role_id}")

        return role

    @staticmethod
    async def list() -> list[Role]:
        """
        List all roles in the current organization.

        Returns:
            list[Role]: List of role objects

        Raises:
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import roles
            >>> all_roles = roles.list()
            >>> for role in all_roles:
            ...     print(f"{role.name}: {len(role.permissions)} permissions")
        """
        context = get_context()
        repo = RoleRepository(context)

        return await repo.list_roles(context.org_id, active_only=True)

    @staticmethod
    async def update(role_id: str, **updates: Any) -> Role:
        """
        Update a role.

        Requires: Platform admin or organization admin privileges

        Args:
            role_id: Role ID
            **updates: Fields to update (name, description, permissions)

        Returns:
            Role: Updated role object

        Raises:
            PermissionError: If user lacks permission
            ValueError: If role not found or validation fails
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import roles
            >>> role = roles.update(
            ...     "role-123",
            ...     description="Updated description",
            ...     permissions=["customers.read"]
            ... )
        """
        context = require_permission("roles.update")
        repo = RoleRepository(context)

        update_request = UpdateRoleRequest(**updates)

        updated_role = await repo.update_role(
            role_id=role_id,
            role_update=update_request,
            org_id=context.org_id,
            updated_by=context.user_id
        )

        if not updated_role:
            raise ValueError(f"Role not found: {role_id}")

        return updated_role

    @staticmethod
    async def delete(role_id: str) -> None:
        """
        Delete a role.

        Requires: Platform admin or organization admin privileges

        Args:
            role_id: Role ID

        Raises:
            PermissionError: If user lacks permission
            ValueError: If role not found
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import roles
            >>> roles.delete("role-123")
        """
        context = require_permission("roles.delete")
        repo = RoleRepository(context)

        success = await repo.delete_role(role_id, context.org_id)

        if not success:
            raise ValueError(f"Role not found: {role_id}")

    @staticmethod
    async def list_users(role_id: str) -> list[str]:
        """
        List all user IDs assigned to a role.

        Args:
            role_id: Role ID

        Returns:
            list[str]: List of user IDs

        Raises:
            ValueError: If role not found
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import roles
            >>> user_ids = roles.list_users("role-123")
            >>> for user_id in user_ids:
            ...     print(user_id)
        """
        context = get_context()
        repo = RoleRepository(context)

        # Verify role exists
        role = await repo.get_role(role_id, context.org_id)
        if not role:
            raise ValueError(f"Role not found: {role_id}")

        return await repo.get_role_user_ids(role_id)

    @staticmethod
    async def list_forms(role_id: str) -> list[str]:
        """
        List all form IDs assigned to a role.

        Args:
            role_id: Role ID

        Returns:
            list[str]: List of form IDs

        Raises:
            ValueError: If role not found
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import roles
            >>> form_ids = roles.list_forms("role-123")
            >>> for form_id in form_ids:
            ...     print(form_id)
        """
        context = get_context()
        repo = RoleRepository(context)

        # Verify role exists
        role = await repo.get_role(role_id, context.org_id)
        if not role:
            raise ValueError(f"Role not found: {role_id}")

        return await repo.get_role_form_ids(role_id)

    @staticmethod
    async def assign_users(role_id: str, user_ids: list[str]) -> None:
        """
        Assign users to a role.

        Requires: Platform admin or organization admin privileges

        Args:
            role_id: Role ID
            user_ids: List of user IDs to assign

        Raises:
            PermissionError: If user lacks permission
            ValueError: If role or users not found
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import roles
            >>> roles.assign_users("role-123", ["user-1", "user-2"])
        """
        context = require_permission("roles.assign_users")
        repo = RoleRepository(context)

        # Verify role exists
        role = await repo.get_role(role_id, context.org_id)
        if not role:
            raise ValueError(f"Role not found: {role_id}")

        await repo.assign_users_to_role(
            role_id=role_id,
            user_ids=user_ids,
            org_id=context.org_id,
            created_by=context.user_id
        )

    @staticmethod
    async def assign_forms(role_id: str, form_ids: list[str]) -> None:
        """
        Assign forms to a role.

        Requires: Platform admin or organization admin privileges

        Args:
            role_id: Role ID
            form_ids: List of form IDs to assign

        Raises:
            PermissionError: If user lacks permission
            ValueError: If role or forms not found
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import roles
            >>> roles.assign_forms("role-123", ["form-1", "form-2"])
        """
        context = require_permission("roles.assign_forms")
        repo = RoleRepository(context)

        # Verify role exists
        role = await repo.get_role(role_id, context.org_id)
        if not role:
            raise ValueError(f"Role not found: {role_id}")

        await repo.assign_forms_to_role(
            role_id=role_id,
            form_ids=form_ids,
            org_id=context.org_id,
            created_by=context.user_id
        )
