"""
Organizations Handlers
Business logic for organization management
"""

import logging
from typing import TYPE_CHECKING

from pydantic import ValidationError

from shared.models import (
    CreateOrganizationRequest,
    Organization,
    UpdateOrganizationRequest,
)
from src.repositories.organizations import OrganizationRepository
from shared.system_logger import get_system_logger

if TYPE_CHECKING:
    from shared.context import ExecutionContext

logger = logging.getLogger(__name__)


# ==================== BUSINESS LOGIC FUNCTIONS ====================
# These functions contain the core business logic and can be called by both
# HTTP handlers and the Bifrost SDK


async def list_organizations_logic(context: 'ExecutionContext') -> list[Organization]:
    """
    List all organizations (business logic).

    Args:
        context: Request context with user info

    Returns:
        list[Organization]: List of organization objects
    """
    logger.info(f"User {context.user_id} listing organizations")

    org_repo = OrganizationRepository()
    orgs = await org_repo.list_organizations(active_only=True)

    # Sort by name
    orgs.sort(key=lambda o: o.name)

    logger.info(f"Returning {len(orgs)} organizations for user {context.user_id}")

    return orgs


async def create_organization_logic(
    context: 'ExecutionContext',
    name: str,
    domain: str | None = None,
    is_active: bool = True
) -> Organization:
    """
    Create a new organization (business logic).

    Args:
        context: Request context with user info
        name: Organization name
        domain: Organization domain (optional)
        is_active: Whether organization is active (default: True)

    Returns:
        Organization: Created organization object
    """
    logger.info(f"User {context.user_id} creating organization: {name}")

    create_request = CreateOrganizationRequest(
        name=name,
        domain=domain
    )

    org_repo = OrganizationRepository()
    org = await org_repo.create_organization(
        org_request=create_request,
        created_by=context.user_id
    )

    logger.info(f"Created organization {org.id}: {org.name}")

    # Log to system logger
    system_logger = get_system_logger()
    await system_logger.log_organization_event(
        action="create",
        org_id=org.id,
        org_name=org.name,
        executed_by=context.user_id,
        executed_by_name=context.name or context.user_id
    )

    return org


async def get_organization_logic(context: 'ExecutionContext', org_id: str) -> Organization | None:
    """
    Get organization by ID (business logic).

    Args:
        context: Request context with user info
        org_id: Organization ID

    Returns:
        Organization | None: Organization object or None if not found
    """
    logger.info(f"User {context.user_id} retrieving organization {org_id}")

    org_repo = OrganizationRepository()
    org = await org_repo.get_organization(org_id)

    if not org:
        logger.warning(f"Organization {org_id} not found")

    return org


async def update_organization_logic(
    context: 'ExecutionContext',
    org_id: str,
    **updates
) -> Organization | None:
    """
    Update organization (business logic).

    Args:
        context: Request context with user info
        org_id: Organization ID
        **updates: Fields to update (name, domain, isActive)

    Returns:
        Organization | None: Updated organization object or None if not found
    """
    logger.info(f"User {context.user_id} updating organization {org_id}")

    update_request = UpdateOrganizationRequest(**updates)

    org_repo = OrganizationRepository()
    org = await org_repo.update_organization(org_id, update_request)

    if org:
        logger.info(f"Updated organization {org_id}")

        # Log to system logger
        system_logger = get_system_logger()
        await system_logger.log_organization_event(
            action="update",
            org_id=org.id,
            org_name=org.name,
            executed_by=context.user_id,
            executed_by_name=context.name or context.user_id
        )
    else:
        logger.warning(f"Organization {org_id} not found for update")

    return org


async def delete_organization_logic(context: 'ExecutionContext', org_id: str) -> bool:
    """
    Soft delete organization (business logic).

    Args:
        context: Request context with user info
        org_id: Organization ID

    Returns:
        bool: True if deleted, False if not found
    """
    logger.info(f"User {context.user_id} deleting organization {org_id}")

    org_repo = OrganizationRepository()
    success = await org_repo.delete_organization(org_id)

    if success:
        logger.info(f"Soft deleted organization {org_id}")

        # Log to system logger
        system_logger = get_system_logger()
        await system_logger.log_organization_event(
            action="delete",
            org_id=org_id,
            org_name=org_id,  # Use org_id as fallback since we don't have the name after deletion
            executed_by=context.user_id,
            executed_by_name=context.name or context.user_id
        )
    else:
        logger.warning(f"Organization {org_id} not found for deletion")

    return success
