"""
Forms Business Logic

Reusable functions for form operations (used by both HTTP handlers and Bifrost SDK).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from shared.models import Form
from shared.repositories.forms import FormRepository

if TYPE_CHECKING:
    from shared.request_context import RequestContext

logger = logging.getLogger(__name__)


def list_forms_logic(context: 'RequestContext') -> list[Form]:
    """
    List all forms for current organization (business logic).

    Args:
        context: Request context with org info

    Returns:
        list[Form]: List of form objects
    """
    logger.info(f"User {context.user_id} listing forms for org {context.org_id}")

    repo = FormRepository(context)
    forms = repo.list_forms(context.org_id)

    logger.info(f"Returning {len(forms)} forms for org {context.org_id}")

    return forms


def get_form_logic(context: 'RequestContext', form_id: str) -> Form | None:
    """
    Get form by ID (business logic).

    Args:
        context: Request context with org info
        form_id: Form ID

    Returns:
        Form | None: Form object or None if not found
    """
    logger.info(f"User {context.user_id} getting form {form_id}")

    repo = FormRepository(context)
    form = repo.get_form(form_id, context.org_id)

    if not form:
        logger.warning(f"Form {form_id} not found in org {context.org_id}")

    return form
