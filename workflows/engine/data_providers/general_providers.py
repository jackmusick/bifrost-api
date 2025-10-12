"""
General Data Providers
Data providers for common dropdown options
"""

from engine.shared.decorators import data_provider


@data_provider(
    name="get_priority_levels",
    description="Returns ticket priority levels (Low, Medium, High, Critical)",
    category="general",
    cache_ttl_seconds=3600
)
async def get_priority_levels(context):
    """
    Get standard priority level options for tickets or tasks.

    Args:
        context: OrganizationContext

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

    context.log(
        "info",
        f"Retrieved {len(priorities)} priority levels",
        {"org_id": context.org_id}
    )

    return priorities


@data_provider(
    name="get_ticket_categories",
    description="Returns IT ticket categories (Hardware, Software, Network, etc.)",
    category="helpdesk",
    cache_ttl_seconds=3600
)
async def get_ticket_categories(context):
    """
    Get common IT ticket categories.

    Args:
        context: OrganizationContext

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

    context.log(
        "info",
        f"Retrieved {len(categories)} ticket categories",
        {"org_id": context.org_id}
    )

    return categories


@data_provider(
    name="get_departments",
    description="Returns organization departments",
    category="organization",
    cache_ttl_seconds=1800
)
async def get_departments(context):
    """
    Get list of departments for the organization.

    For MVP: Returns mock data. In production, this could come from:
    - Azure AD groups
    - HaloPSA departments
    - OrganizationConfig table

    Args:
        context: OrganizationContext

    Returns:
        List of department options
    """
    # For MVP: Return mock departments
    # In production: Could query from org config or external system
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

    context.log(
        "info",
        f"Retrieved {len(departments)} departments",
        {"org_id": context.org_id}
    )

    return departments


@data_provider(
    name="get_office_locations",
    description="Returns office location options",
    category="organization",
    cache_ttl_seconds=3600
)
async def get_office_locations(context):
    """
    Get list of office locations for the organization.

    Args:
        context: OrganizationContext

    Returns:
        List of office location options
    """
    # For MVP: Return mock locations
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
            "label": "Austin - Satellite Office",
            "value": "aus_satellite",
            "metadata": {
                "address": "321 Congress Ave, Austin, TX 78701",
                "capacity": 50,
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

    context.log(
        "info",
        f"Retrieved {len(locations)} office locations",
        {"org_id": context.org_id}
    )

    return locations


@data_provider(
    name="get_countries",
    description="Returns country list for address forms",
    category="general",
    cache_ttl_seconds=86400  # 24 hours - countries don't change often
)
async def get_countries(context):
    """
    Get list of common countries.

    Args:
        context: OrganizationContext

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
        {"label": "Belgium", "value": "BE"},
        {"label": "Switzerland", "value": "CH"},
        {"label": "Sweden", "value": "SE"},
        {"label": "Norway", "value": "NO"},
        {"label": "Denmark", "value": "DK"},
        {"label": "Finland", "value": "FI"},
        {"label": "Poland", "value": "PL"},
        {"label": "Ireland", "value": "IE"},
        {"label": "Austria", "value": "AT"},
        {"label": "Portugal", "value": "PT"},
        {"label": "Japan", "value": "JP"},
        {"label": "South Korea", "value": "KR"},
        {"label": "Singapore", "value": "SG"},
        {"label": "India", "value": "IN"},
        {"label": "Brazil", "value": "BR"},
        {"label": "Mexico", "value": "MX"}
    ]

    context.log(
        "info",
        f"Retrieved {len(countries)} countries",
        {"org_id": context.org_id}
    )

    return countries
