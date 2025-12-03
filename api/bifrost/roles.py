"""
Roles management SDK for Bifrost.

Provides Python API for role operations (CRUD + user/form assignments).

All methods are async and must be called with await.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from src.models.schemas import Role

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
        from src.core.database import get_session_factory
        from src.models import Role as RoleModel

        context = require_permission("roles.create")
        session_factory = get_session_factory()

        org_uuid = None
        if context.org_id and context.org_id != "GLOBAL":
            try:
                org_uuid = UUID(context.org_id)
            except ValueError:
                pass

        async with session_factory() as db:
            role = RoleModel(
                name=name,
                description=description,
                permissions=permissions or [],
                organization_id=org_uuid,
                created_by=context.user_id,
            )
            db.add(role)
            await db.flush()
            await db.refresh(role)
            await db.commit()

            return Role(
                id=str(role.id),
                name=role.name,
                description=role.description,
                permissions=role.permissions or [],
                orgId=str(role.organization_id) if role.organization_id else None,
                isActive=role.is_active,
                createdBy=role.created_by,
                createdAt=role.created_at,
                updatedAt=role.updated_at,
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
        from sqlalchemy import select
        from src.core.database import get_session_factory
        from src.models import Role as RoleModel

        get_context()  # Validates user is authenticated
        session_factory = get_session_factory()

        role_uuid = UUID(role_id)

        async with session_factory() as db:
            result = await db.execute(
                select(RoleModel).where(RoleModel.id == role_uuid)
            )
            role = result.scalar_one_or_none()

            if not role:
                raise ValueError(f"Role not found: {role_id}")

            return Role(
                id=str(role.id),
                name=role.name,
                description=role.description,
                permissions=role.permissions or [],
                orgId=str(role.organization_id) if role.organization_id else None,
                isActive=role.is_active,
                createdBy=role.created_by,
                createdAt=role.created_at,
                updatedAt=role.updated_at,
            )

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
        from sqlalchemy import select, or_
        from src.core.database import get_session_factory
        from src.models import Role as RoleModel

        context = get_context()
        session_factory = get_session_factory()

        org_uuid = None
        if context.org_id and context.org_id != "GLOBAL":
            try:
                org_uuid = UUID(context.org_id)
            except ValueError:
                pass

        async with session_factory() as db:
            query = select(RoleModel).where(
                RoleModel.is_active == True,  # noqa: E712
                or_(
                    RoleModel.organization_id == org_uuid,
                    RoleModel.organization_id.is_(None)
                )
            ).order_by(RoleModel.name)

            result = await db.execute(query)
            role_models = result.scalars().all()

            return [
                Role(
                    id=str(r.id),
                    name=r.name,
                    description=r.description,
                    permissions=r.permissions or [],
                    orgId=str(r.organization_id) if r.organization_id else None,
                    isActive=r.is_active,
                    createdBy=r.created_by,
                    createdAt=r.created_at,
                    updatedAt=r.updated_at,
                )
                for r in role_models
            ]

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
        from sqlalchemy import select
        from src.core.database import get_session_factory
        from src.models import Role as RoleModel

        require_permission("roles.update")
        session_factory = get_session_factory()

        role_uuid = UUID(role_id)

        async with session_factory() as db:
            result = await db.execute(
                select(RoleModel).where(RoleModel.id == role_uuid)
            )
            role = result.scalar_one_or_none()

            if not role:
                raise ValueError(f"Role not found: {role_id}")

            # Apply updates
            for field, value in updates.items():
                if hasattr(role, field):
                    setattr(role, field, value)

            await db.flush()
            await db.refresh(role)
            await db.commit()

            return Role(
                id=str(role.id),
                name=role.name,
                description=role.description,
                permissions=role.permissions or [],
                orgId=str(role.organization_id) if role.organization_id else None,
                isActive=role.is_active,
                createdBy=role.created_by,
                createdAt=role.created_at,
                updatedAt=role.updated_at,
            )

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
        from sqlalchemy import select
        from src.core.database import get_session_factory
        from src.models import Role as RoleModel

        require_permission("roles.delete")
        session_factory = get_session_factory()

        role_uuid = UUID(role_id)

        async with session_factory() as db:
            result = await db.execute(
                select(RoleModel).where(RoleModel.id == role_uuid)
            )
            role = result.scalar_one_or_none()

            if not role:
                raise ValueError(f"Role not found: {role_id}")

            role.is_active = False
            await db.commit()

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
        from sqlalchemy import select
        from src.core.database import get_session_factory
        from src.models import Role as RoleModel, UserRole

        get_context()  # Validates user is authenticated
        session_factory = get_session_factory()

        role_uuid = UUID(role_id)

        async with session_factory() as db:
            # Verify role exists
            result = await db.execute(
                select(RoleModel).where(RoleModel.id == role_uuid)
            )
            role = result.scalar_one_or_none()
            if not role:
                raise ValueError(f"Role not found: {role_id}")

            # Get user IDs
            result = await db.execute(
                select(UserRole.user_id).where(UserRole.role_id == role_uuid)
            )
            return [str(uid) for uid in result.scalars().all()]

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
        from sqlalchemy import select
        from src.core.database import get_session_factory
        from src.models import Role as RoleModel, FormRole

        get_context()  # Validates user is authenticated
        session_factory = get_session_factory()

        role_uuid = UUID(role_id)

        async with session_factory() as db:
            # Verify role exists
            result = await db.execute(
                select(RoleModel).where(RoleModel.id == role_uuid)
            )
            role = result.scalar_one_or_none()
            if not role:
                raise ValueError(f"Role not found: {role_id}")

            # Get form IDs
            result = await db.execute(
                select(FormRole.form_id).where(FormRole.role_id == role_uuid)
            )
            return [str(fid) for fid in result.scalars().all()]

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
        from sqlalchemy import select
        from src.core.database import get_session_factory
        from src.models import Role as RoleModel, UserRole

        context = require_permission("roles.assign_users")
        session_factory = get_session_factory()

        role_uuid = UUID(role_id)

        async with session_factory() as db:
            # Verify role exists
            result = await db.execute(
                select(RoleModel).where(RoleModel.id == role_uuid)
            )
            role = result.scalar_one_or_none()
            if not role:
                raise ValueError(f"Role not found: {role_id}")

            for user_id in user_ids:
                user_uuid = UUID(user_id)

                # Check if already assigned
                existing = await db.execute(
                    select(UserRole).where(
                        UserRole.user_id == user_uuid,
                        UserRole.role_id == role_uuid,
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                user_role = UserRole(
                    user_id=user_uuid,
                    role_id=role_uuid,
                    assigned_by=context.user_id,
                )
                db.add(user_role)

            await db.commit()

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
        from sqlalchemy import select
        from src.core.database import get_session_factory
        from src.models import Role as RoleModel, FormRole

        context = require_permission("roles.assign_forms")
        session_factory = get_session_factory()

        role_uuid = UUID(role_id)

        async with session_factory() as db:
            # Verify role exists
            result = await db.execute(
                select(RoleModel).where(RoleModel.id == role_uuid)
            )
            role = result.scalar_one_or_none()
            if not role:
                raise ValueError(f"Role not found: {role_id}")

            for form_id in form_ids:
                form_uuid = UUID(form_id)

                # Check if already assigned
                existing = await db.execute(
                    select(FormRole).where(
                        FormRole.form_id == form_uuid,
                        FormRole.role_id == role_uuid,
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                form_role = FormRole(
                    form_id=form_uuid,
                    role_id=role_uuid,
                    assigned_by=context.user_id,
                )
                db.add(form_role)

            await db.commit()
