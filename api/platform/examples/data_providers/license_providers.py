"""
License Data Providers
Data providers for Microsoft 365 license selection
"""

import logging

from bifrost import data_provider

logger = logging.getLogger(__name__)


@data_provider(
    name="get_available_licenses",
    description="Returns available Microsoft 365 licenses for the organization",
    category="m365",
    cache_ttl_seconds=300
)
async def get_available_licenses(context):
    """
    Get list of available Microsoft 365 licenses.

    For MVP, returns mock data. In production, this would call:
    - Microsoft Graph API subscribed_skus endpoint
    - Filter by available units > consumed units

    Args:
        context: ExecutionContext with org_id, integrations, etc.

    Returns:
        List of license options:
        [
            {
                "label": "Microsoft 365 E3",
                "value": "O365_E3_SKU_ID",
                "metadata": {"available": 25, "total": 50}
            },
            ...
        ]
    """
    # For MVP: Return mock license data
    # In production:
    # graph = context.get_integration('msgraph')
    # skus = await graph.subscribed_skus.get()

    mock_licenses = [
        {
            "label": "Microsoft 365 Business Basic",
            "value": "O365_BUSINESS_ESSENTIALS",
            "metadata": {
                "available": 10,
                "total": 25,
                "consumed": 15
            }
        },
        {
            "label": "Microsoft 365 Business Standard",
            "value": "O365_BUSINESS_PREMIUM",
            "metadata": {
                "available": 5,
                "total": 10,
                "consumed": 5
            }
        },
        {
            "label": "Microsoft 365 E3",
            "value": "SPE_E3",
            "metadata": {
                "available": 20,
                "total": 50,
                "consumed": 30
            }
        },
        {
            "label": "Microsoft 365 E5",
            "value": "SPE_E5",
            "metadata": {
                "available": 3,
                "total": 5,
                "consumed": 2
            }
        }
    ]

    # Filter to only licenses with available units
    available = [lic for lic in mock_licenses if lic["metadata"]["available"] > 0]

    logger.info(
        f"Retrieved {len(available)} available licenses",
        {"org_id": context.org_id, "total_skus": len(mock_licenses)}
    )

    return available


@data_provider(
    name="get_all_licenses",
    description="Returns all Microsoft 365 licenses (including unavailable)",
    category="m365",
    cache_ttl_seconds=300
)
async def get_all_licenses(context):
    """
    Get list of all Microsoft 365 licenses (including those with 0 available).

    Useful for license reporting and planning.

    Args:
        context: ExecutionContext

    Returns:
        List of all license options with availability info
    """
    # For MVP: Return mock data
    all_licenses = [
        {
            "label": "Microsoft 365 Business Basic",
            "value": "O365_BUSINESS_ESSENTIALS",
            "metadata": {
                "available": 10,
                "total": 25,
                "consumed": 15,
                "status": "active"
            }
        },
        {
            "label": "Microsoft 365 Business Standard",
            "value": "O365_BUSINESS_PREMIUM",
            "metadata": {
                "available": 5,
                "total": 10,
                "consumed": 5,
                "status": "active"
            }
        },
        {
            "label": "Microsoft 365 E3",
            "value": "SPE_E3",
            "metadata": {
                "available": 20,
                "total": 50,
                "consumed": 30,
                "status": "active"
            }
        },
        {
            "label": "Microsoft 365 E5",
            "value": "SPE_E5",
            "metadata": {
                "available": 3,
                "total": 5,
                "consumed": 2,
                "status": "active"
            }
        },
        {
            "label": "Microsoft 365 F3",
            "value": "SPE_F1",
            "metadata": {
                "available": 0,
                "total": 100,
                "consumed": 100,
                "status": "capacity_reached"
            }
        }
    ]

    return all_licenses
