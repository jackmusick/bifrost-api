"""
Forms Business Logic

Reusable functions for form operations (used by both HTTP handlers and Bifrost SDK).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from shared.models import Form
from src.repositories.forms_file import FormsFileRepository

if TYPE_CHECKING:
    from shared.context import ExecutionContext

logger = logging.getLogger(__name__)


async def list_forms_logic(context: 'ExecutionContext') -> list[Form]:
    """
    List all forms for current organization (business logic).

    Args:
        context: Request context with org info

    Returns:
        list[Form]: List of form objects
    """
    logger.info(f"User {context.user_id} listing forms for org {context.org_id}")

    repo = FormsFileRepository(context)
    forms = await repo.list_forms()

    logger.info(f"Returning {len(forms)} forms for org {context.org_id}")

    return forms


async def get_form_logic(context: 'ExecutionContext', form_id: str) -> Form | None:
    """
    Get form by ID (business logic).

    Args:
        context: Request context with org info
        form_id: Form ID

    Returns:
        Form | None: Form object or None if not found
    """
    logger.info(f"User {context.user_id} getting form {form_id}")

    repo = FormsFileRepository(context)
    form = await repo.get_form(form_id)

    if not form:
        logger.warning(f"Form {form_id} not found in org {context.org_id}")

    return form
