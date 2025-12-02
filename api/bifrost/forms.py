"""
Forms SDK for Bifrost.

Provides Python API for form operations (read-only for now).

All methods are async and must be called with await.
"""

from __future__ import annotations

from shared.handlers.forms_logic import get_form_logic, list_forms_logic
from src.models.schemas import Form

from ._internal import get_context


class forms:
    """
    Form operations (read-only).

    Allows workflows to list and get form definitions.

    All methods are async and must be awaited.
    """

    @staticmethod
    async def list() -> list[Form]:
        """
        List all forms available to the current user.

        Returns:
            list[Form]: List of form objects

        Raises:
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import forms
            >>> all_forms = await forms.list()
            >>> for form in all_forms:
            ...     print(f"{form.id}: {form.title}")
        """
        context = get_context()

        return await list_forms_logic(context)

    @staticmethod
    async def get(form_id: str) -> Form:
        """
        Get a form definition by ID.

        Args:
            form_id: Form ID

        Returns:
            Form: Form object

        Raises:
            ValueError: If form not found
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import forms
            >>> form = await forms.get("form-123")
            >>> print(form.title)
            >>> print(form.schema)
        """
        context = get_context()

        form = await get_form_logic(context, form_id)

        if not form:
            raise ValueError(f"Form not found: {form_id}")

        return form
