"""
Forms SDK for Bifrost.

Provides Python API for form operations (read-only).

All methods are synchronous and can be called directly (no await needed).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select, or_

from src.models.orm import Form, FormRole, UserRole

from ._db import get_sync_session
from ._internal import get_context


def _form_to_dict(form: Form) -> dict[str, Any]:
    """Convert ORM Form to dictionary."""
    return {
        "id": str(form.id),
        "organization_id": str(form.organization_id) if form.organization_id else None,
        "name": form.name,
        "description": form.description,
        "linked_workflow": form.linked_workflow,
        "is_active": form.is_active,
        "created_by": form.created_by,
        "created_at": form.created_at.isoformat() if form.created_at else None,
        "updated_at": form.updated_at.isoformat() if form.updated_at else None,
    }


class forms:
    """
    Form operations (read-only).

    Allows workflows to list and get form definitions.

    All methods are synchronous - no await needed.
    """

    @staticmethod
    def list() -> list[dict[str, Any]]:
        """
        List all forms available to the current user.

        Returns:
            list[dict]: List of form dictionaries

        Raises:
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import forms
            >>> all_forms = forms.list()
            >>> for form in all_forms:
            ...     print(f"{form['id']}: {form['name']}")
        """
        context = get_context()

        org_uuid = None
        if context.org_id and context.org_id != "GLOBAL":
            try:
                org_uuid = UUID(context.org_id)
            except ValueError:
                pass

        with get_sync_session() as db:
            if context.is_platform_admin:
                # Platform admins see all forms in their org scope
                if org_uuid:
                    query = (
                        select(Form)
                        .where(Form.is_active == True)
                        .where(or_(Form.organization_id == org_uuid, Form.organization_id.is_(None)))
                        .order_by(Form.name)
                    )
                else:
                    query = (
                        select(Form)
                        .where(Form.is_active == True)
                        .where(Form.organization_id.is_(None))
                        .order_by(Form.name)
                    )
            else:
                # Regular users see forms assigned to their roles
                query = (
                    select(Form)
                    .distinct()
                    .join(FormRole, Form.id == FormRole.form_id)
                    .join(UserRole, FormRole.role_id == UserRole.role_id)
                    .where(Form.is_active == True)
                    .where(UserRole.user_id == UUID(context.user_id))
                    .order_by(Form.name)
                )

            result = db.execute(query)
            return [_form_to_dict(f) for f in result.scalars().all()]

    @staticmethod
    def get(form_id: str) -> dict[str, Any]:
        """
        Get a form definition by ID.

        Args:
            form_id: Form ID

        Returns:
            dict: Form dictionary

        Raises:
            ValueError: If form not found
            PermissionError: If user doesn't have access to the form
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import forms
            >>> form = forms.get("form-123")
            >>> print(form['name'])
        """
        context = get_context()
        form_uuid = UUID(form_id)

        with get_sync_session() as db:
            form = db.get(Form, form_uuid)
            if not form or not form.is_active:
                raise ValueError(f"Form not found: {form_id}")

            # Check access for non-admins
            if not context.is_platform_admin:
                access_query = (
                    select(FormRole)
                    .join(UserRole, FormRole.role_id == UserRole.role_id)
                    .where(FormRole.form_id == form_uuid)
                    .where(UserRole.user_id == UUID(context.user_id))
                )
                result = db.execute(access_query)
                if not result.scalars().first():
                    raise PermissionError(f"Access denied to form: {form_id}")

            return _form_to_dict(form)
