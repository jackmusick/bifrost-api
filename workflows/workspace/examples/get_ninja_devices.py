"""
Get NinjaOne Devices Example
Demonstrates how to use OAuth connections to call external APIs

This workflow retrieves devices from NinjaOne using OAuth authentication.
"""

import requests
from typing import Dict, Any
from engine.shared.decorators import workflow
from engine.shared.context import OrganizationContext


@workflow(
    name="get_ninja_devices",
    description="Retrieves devices from NinjaOne using OAuth authentication",
    category="Examples"
)
async def get_ninja_devices(context: OrganizationContext) -> Dict[str, Any]:
    """
    Gets devices from NinjaOne via the devices API endpoint.

    Prerequisites:
    - OAuth connection named 'NinjaOne' must be created and authorized

    Args:
        context: Organization context with org info, config, and OAuth access

    Returns:
        Dictionary with success status and devices list
    """
    context.log("info", "Starting NinjaOne devices retrieval")

    try:
        # Get OAuth credentials for NinjaOne
        # This uses the consistent context.get_oauth_connection() method
        context.log("info", "Retrieving OAuth credentials for NinjaOne")
        oauth_creds = await context.get_oauth_connection('NinjaOne')

        # Check if token is expired
        if oauth_creds.is_expired():
            error_msg = f"OAuth token for NinjaOne is expired (expired at {oauth_creds.expires_at})"
            context.log("error", error_msg)
            return {
                "success": False,
                "error": error_msg
            }

        # Make API request using OAuth credentials
        headers = {
            "Accept": "application/json",
            # Formats as "Bearer {token}"
            "Authorization": oauth_creds.get_auth_header(),
        }

        context.log("info", "Calling NinjaOne devices API")

        response = requests.get(
            "https://app.ninjarmm.com/v2/devices",
            headers=headers,
            timeout=30
        )

        # Check response status
        response.raise_for_status()

        # Parse response
        devices = response.json()

        context.log(
            "info", f"Successfully retrieved {len(devices)} devices from NinjaOne")

        # Log device details
        for device in devices:
            device_id = device.get('id', 'N/A')
            system_name = device.get('systemName', 'N/A')
            node_class = device.get('nodeClass', 'N/A')

            # context.log("info", f"Device: {system_name}", {
            #     "device_id": device_id,
            #     "node_class": node_class
            # })

        return {
            "success": True,
            "device_count": len(devices)
        }

    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP error from NinjaOne API: {e.response.status_code} - {e.response.text}"
        context.log("error", error_msg)
        return {
            "success": False,
            "error": error_msg
        }

    except requests.exceptions.Timeout:
        error_msg = "Request to NinjaOne API timed out"
        context.log("error", error_msg)
        return {
            "success": False,
            "error": error_msg
        }

    except ValueError as e:
        # Catches OAuth connection errors (not found, not authorized, expired, etc.)
        error_msg = f"OAuth connection error: {str(e)}"
        context.log("error", error_msg)
        return {
            "success": False,
            "error": error_msg
        }

    except Exception as e:
        error_msg = f"Unexpected error fetching NinjaOne devices: {str(e)}"
        context.log("error", error_msg, {"exception_type": type(e).__name__})
        return {
            "success": False,
            "error": error_msg
        }
