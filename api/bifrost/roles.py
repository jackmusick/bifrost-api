"""
Roles management SDK for Bifrost.

Provides Python API for role operations (CRUD + user/form assignments).

All methods are synchronous and can be called directly (no await needed).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select, or_

from shared.models import Role as RoleSchema
from src.models.orm import Role, UserRole, FormRole

from ._db import get_sync_session
from ._internal import get_context, require_permission


def _role_to_schema(role: Role) -> RoleSchema:
    """Convert ORM Role to Pydantic RoleSchema."""
    return RoleSchema(
        id=str(role.id),
        name=role.name,
        description=role.description,
        is_active=role.is_active,
        created_by=role.created_by,
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


class roles:
    """
    Role management operations.

    Provides CRUD operations for roles and user/form assignments.
    All methods are synchronous - no await needed.
    """

    @staticmethod
    def create(name: str, description: str = "") -> RoleSchema:
        """
        Create a new role.

        Requires: Platform admin or organization admin privileges

        Args:
            name: Role name
            description: Role description (optional)

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
            ...     description="Can manage customer data"
            ... )
        """
        context = require_permission("roles.create")

        org_uuid = None
        if context.org_id and context.org_id != "GLOBAL":
            try:
                org_uuid = UUID(context.org_id)
            except ValueError:
                pass

        with get_sync_session() as db:
            role = Role(
                name=name,
                description=description,
                organization_id=org_uuid,
                created_by=context.user_id,
                is_active=True,
            )
            db.add(role)
            db.flush()  # Get the ID
            db.refresh(role)
            return _role_to_schema(role)

    @staticmethod
    def get(role_id: str) -> RoleSchema:
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
        get_context()  # Validates user is authenticated
        role_uuid = UUID(role_id)

        with get_sync_session() as db:
            role = db.get(Role, role_uuid)
            if not role:
                raise ValueError(f"Role not found: {role_id}")
            return _role_to_schema(role)

    @staticmethod
    def list() -> list[RoleSchema]:
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
            ...     print(f"{role.name}: {role.description}")
        """
        context = get_context()

        org_uuid = None
        if context.org_id and context.org_id != "GLOBAL":
            try:
                org_uuid = UUID(context.org_id)
            except ValueError:
                pass

        with get_sync_session() as db:
            if org_uuid:
                query = (
                    select(Role)
                    .where(Role.is_active == True)
                    .where(or_(Role.organization_id == org_uuid, Role.organization_id.is_(None)))
                    .order_by(Role.name)
                )
            else:
                query = (
                    select(Role)
                    .where(Role.is_active == True)
                    .where(Role.organization_id.is_(None))
                    .order_by(Role.name)
                )

            result = db.execute(query)
            return [_role_to_schema(r) for r in result.scalars().all()]

    @staticmethod
    def update(role_id: str, **updates: Any) -> RoleSchema:
        """
        Update a role.

        Requires: Platform admin or organization admin privileges

        Args:
            role_id: Role ID
            **updates: Fields to update (name, description)

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
            ...     description="Updated description"
            ... )
        """
        require_permission("roles.update")
        role_uuid = UUID(role_id)

        with get_sync_session() as db:
            role = db.get(Role, role_uuid)
            if not role:
                raise ValueError(f"Role not found: {role_id}")

            if 'name' in updates:
                role.name = updates['name']
            if 'description' in updates:
                role.description = updates['description']

            db.flush()
            db.refresh(role)
            return _role_to_schema(role)

    @staticmethod
    def delete(role_id: str) -> None:
        """
        Delete a role (soft delete - sets is_active to false).

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
        require_permission("roles.delete")
        role_uuid = UUID(role_id)

        with get_sync_session() as db:
            role = db.get(Role, role_uuid)
            if not role:
                raise ValueError(f"Role not found: {role_id}")
            role.is_active = False

    @staticmethod
    def list_users(role_id: str) -> list[str]:
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
        get_context()  # Validates user is authenticated
        role_uuid = UUID(role_id)

        with get_sync_session() as db:
            # Verify role exists
            role = db.get(Role, role_uuid)
            if not role:
                raise ValueError(f"Role not found: {role_id}")

            query = select(UserRole.user_id).where(UserRole.role_id == role_uuid)
            result = db.execute(query)
            return [str(row[0]) for row in result.all()]

    @staticmethod
    def list_forms(role_id: str) -> list[str]:
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
        get_context()  # Validates user is authenticated
        role_uuid = UUID(role_id)

        with get_sync_session() as db:
            # Verify role exists
            role = db.get(Role, role_uuid)
            if not role:
                raise ValueError(f"Role not found: {role_id}")

            query = select(FormRole.form_id).where(FormRole.role_id == role_uuid)
            result = db.execute(query)
            return [str(row[0]) for row in result.all()]

    @staticmethod
    def assign_users(role_id: str, user_ids: list[str]) -> None:
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
        role_uuid = UUID(role_id)

        with get_sync_session() as db:
            # Verify role exists
            role = db.get(Role, role_uuid)
            if not role:
                raise ValueError(f"Role not found: {role_id}")

            for user_id in user_ids:
                user_uuid = UUID(user_id)

                # Check if already assigned
                existing = db.execute(
                    select(UserRole)
                    .where(UserRole.user_id == user_uuid)
                    .where(UserRole.role_id == role_uuid)
                ).scalars().first()

                if not existing:
                    user_role = UserRole(
                        user_id=user_uuid,
                        role_id=role_uuid,
                        assigned_by=context.user_id,
                    )
                    db.add(user_role)

    @staticmethod
    def assign_forms(role_id: str, form_ids: list[str]) -> None:
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
        role_uuid = UUID(role_id)

        with get_sync_session() as db:
            # Verify role exists
            role = db.get(Role, role_uuid)
            if not role:
                raise ValueError(f"Role not found: {role_id}")

            for form_id in form_ids:
                form_uuid = UUID(form_id)

                # Check if already assigned
                existing = db.execute(
                    select(FormRole)
                    .where(FormRole.form_id == form_uuid)
                    .where(FormRole.role_id == role_uuid)
                ).scalars().first()

                if not existing:
                    form_role = FormRole(
                        form_id=form_uuid,
                        role_id=role_uuid,
                        assigned_by=context.user_id,
                    )
                    db.add(form_role)
