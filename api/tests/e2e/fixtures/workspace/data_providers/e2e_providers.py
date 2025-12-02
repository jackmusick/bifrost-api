"""
E2E General Data Providers

Copy of platform/examples/data_providers/general_providers.py with renamed providers for E2E testing.
Data providers for common dropdown options.
"""

import logging

from bifrost import data_provider

logger = logging.getLogger(__name__)


@data_provider(
    name="e2e_get_priority_levels",
    description="E2E: Returns ticket priority levels (Low, Medium, High, Critical)",
    category="e2e_testing",
    cache_ttl_seconds=3600
)
async def e2e_get_priority_levels(context):
    """
    E2E: Get standard priority level options for tickets or tasks.

    Args:
        context: ExecutionContext

    Returns:
        List of priority options
    """
    priorities = [
        {
            "label": "Low",
            "value": "low",
            "metadata": {"color": "green", "sla_hours": 72}
        },
        {
            "label": "Medium",
            "value": "medium",
            "metadata": {"color": "yellow", "sla_hours": 24}
        },
        {
            "label": "High",
            "value": "high",
            "metadata": {"color": "orange", "sla_hours": 8}
        },
        {
            "label": "Critical",
            "value": "critical",
            "metadata": {"color": "red", "sla_hours": 4}
        }
    ]

    logger.info(
        f"E2E: Retrieved {len(priorities)} priority levels",
        {"org_id": context.org_id}
    )

    return priorities


@data_provider(
    name="e2e_get_ticket_categories",
    description="E2E: Returns IT ticket categories (Hardware, Software, Network, etc.)",
    category="e2e_testing",
    cache_ttl_seconds=3600
)
async def e2e_get_ticket_categories(context):
    """
    E2E: Get common IT ticket categories.

    Args:
        context: ExecutionContext

    Returns:
        List of ticket category options
    """
    categories = [
        {
            "label": "Hardware Issue",
            "value": "hardware",
            "metadata": {"icon": "laptop", "typical_resolution_hours": 24}
        },
        {
            "label": "Software Issue",
            "value": "software",
            "metadata": {"icon": "code", "typical_resolution_hours": 8}
        },
        {
            "label": "Network/Connectivity",
            "value": "network",
            "metadata": {"icon": "wifi", "typical_resolution_hours": 4}
        },
        {
            "label": "Email & Communication",
            "value": "email",
            "metadata": {"icon": "mail", "typical_resolution_hours": 2}
        },
        {
            "label": "Access/Permissions",
            "value": "access",
            "metadata": {"icon": "key", "typical_resolution_hours": 2}
        },
        {
            "label": "Password Reset",
            "value": "password",
            "metadata": {"icon": "lock", "typical_resolution_hours": 1}
        },
        {
            "label": "Other",
            "value": "other",
            "metadata": {"icon": "help-circle", "typical_resolution_hours": 8}
        }
    ]

    logger.info(
        f"E2E: Retrieved {len(categories)} ticket categories",
        {"org_id": context.org_id}
    )

    return categories


@data_provider(
    name="e2e_get_departments",
    description="E2E: Returns organization departments",
    category="e2e_testing",
    cache_ttl_seconds=1800
)
async def e2e_get_departments(context):
    """
    E2E: Get list of departments for the organization.

    Args:
        context: ExecutionContext

    Returns:
        List of department options
    """
    departments = [
        {
            "label": "IT & Technology",
            "value": "it",
            "metadata": {"head_count": 12, "manager": "John Smith"}
        },
        {
            "label": "Sales",
            "value": "sales",
            "metadata": {"head_count": 25, "manager": "Jane Doe"}
        },
        {
            "label": "Marketing",
            "value": "marketing",
            "metadata": {"head_count": 8, "manager": "Bob Johnson"}
        },
        {
            "label": "Finance",
            "value": "finance",
            "metadata": {"head_count": 6, "manager": "Sarah Williams"}
        },
        {
            "label": "Human Resources",
            "value": "hr",
            "metadata": {"head_count": 4, "manager": "Mike Brown"}
        },
        {
            "label": "Operations",
            "value": "operations",
            "metadata": {"head_count": 15, "manager": "Lisa Davis"}
        },
        {
            "label": "Customer Support",
            "value": "support",
            "metadata": {"head_count": 20, "manager": "Tom Wilson"}
        }
    ]

    logger.info(
        f"E2E: Retrieved {len(departments)} departments",
        {"org_id": context.org_id}
    )

    return departments


@data_provider(
    name="e2e_get_office_locations",
    description="E2E: Returns office location options",
    category="e2e_testing",
    cache_ttl_seconds=3600
)
async def e2e_get_office_locations(context):
    """
    E2E: Get list of office locations for the organization.

    Args:
        context: ExecutionContext

    Returns:
        List of office location options
    """
    locations = [
        {
            "label": "New York - Main Office",
            "value": "ny_main",
            "metadata": {
                "address": "123 Broadway, New York, NY 10001",
                "capacity": 200,
                "timezone": "America/New_York"
            }
        },
        {
            "label": "San Francisco - Tech Hub",
            "value": "sf_tech",
            "metadata": {
                "address": "456 Market St, San Francisco, CA 94102",
                "capacity": 150,
                "timezone": "America/Los_Angeles"
            }
        },
        {
            "label": "Chicago - Regional Office",
            "value": "chi_regional",
            "metadata": {
                "address": "789 Michigan Ave, Chicago, IL 60611",
                "capacity": 100,
                "timezone": "America/Chicago"
            }
        },
        {
            "label": "Remote",
            "value": "remote",
            "metadata": {
                "address": "N/A",
                "capacity": None,
                "timezone": None
            }
        }
    ]

    logger.info(
        f"E2E: Retrieved {len(locations)} office locations",
        {"org_id": context.org_id}
    )

    return locations


@data_provider(
    name="e2e_get_countries",
    description="E2E: Returns country list for address forms",
    category="e2e_testing",
    cache_ttl_seconds=86400
)
async def e2e_get_countries(context):
    """
    E2E: Get list of common countries.

    Args:
        context: ExecutionContext

    Returns:
        List of country options
    """
    countries = [
        {"label": "United States", "value": "US"},
        {"label": "Canada", "value": "CA"},
        {"label": "United Kingdom", "value": "GB"},
        {"label": "Australia", "value": "AU"},
        {"label": "Germany", "value": "DE"},
        {"label": "France", "value": "FR"},
        {"label": "Spain", "value": "ES"},
        {"label": "Italy", "value": "IT"},
        {"label": "Netherlands", "value": "NL"},
        {"label": "Japan", "value": "JP"}
    ]

    logger.info(
        f"E2E: Retrieved {len(countries)} countries",
        {"org_id": context.org_id}
    )

    return countries
