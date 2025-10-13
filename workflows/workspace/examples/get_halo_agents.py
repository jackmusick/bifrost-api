"""
Get HaloPSA Agents Example
Demonstrates how to use OAuth connections to call external APIs

This workflow retrieves active agents from HaloPSA using OAuth authentication.
"""

import requests
from typing import Dict, Any
from engine.shared.decorators import workflow
from engine.shared.context import OrganizationContext


@workflow(
    name="get_halo_agents",
    description="Retrieves active agents from HaloPSA using OAuth authentication",
    category="Examples"
)
async def get_halo_agents(context: OrganizationContext) -> Dict[str, Any]:
    """
    Gets active agents from HaloPSA by executing a SQL query via the Report API.

    Prerequisites:
    - OAuth connection named 'HaloPSA' must be created and authorized
    - Config 'halopsa_base_url' must be set (e.g., https://your-tenant.halopsa.com)

    Args:
        context: Organization context with org info, config, and OAuth access

    Returns:
        Dictionary with success status and agent list
    """
    context.log("info", "Starting HaloPSA agents retrieval")

    try:
        # Get OAuth credentials for HaloPSA
        # This uses the consistent context.get_oauth_connection() method
        context.log("info", "Retrieving OAuth credentials for HaloPSA")
        oauth_creds = await context.get_oauth_connection('HaloPSA')

        # Check if token is expired
        if oauth_creds.is_expired():
            error_msg = f"OAuth token for HaloPSA is expired (expired at {oauth_creds.expires_at})"
            context.log("error", error_msg)
            return {
                "success": False,
                "error": error_msg
            }

        # Get HaloPSA base URL from config
        base_url = context.get_config('halopsa_base_url')
        if not base_url:
            error_msg = "HaloPSA base URL not configured. Please set 'halopsa_base_url' in config."
            context.log("error", error_msg)
            return {
                "success": False,
                "error": error_msg
            }

        context.log("info", f"Using HaloPSA base URL: {base_url}")

        # Prepare SQL query for agents
        sql_query = """
SELECT
    uname.uname [Name],
    uname.usmtp [Email Address],
    uname.usection [Team],
    lookup.fvalue [Status]
FROM uname
LEFT JOIN lookup
ON lookup.fid = 49 AND lookup.fcode = uname.utechstatus
WHERE uname.uisapiagent = 0 OR uname.uisapiagent IS NULL AND uname.uname != 'Unassigned' and uname.Uisdisabled = 0
"""

        # Prepare request body (HaloPSA Report API format)
        body = [
            {
                "sql": sql_query,
                "_testonly": True,
                "_loadreportonly": True
            }
        ]

        # Make API request using OAuth credentials
        headers = {
            "Accept": "application/json",
            "Authorization": oauth_creds.get_auth_header(),  # Formats as "Bearer {token}"
            "Content-Type": "application/json"
        }

        context.log("info", "Calling HaloPSA Report API")

        response = requests.post(
            f"{base_url}/api/Report",
            headers=headers,
            json=body,
            timeout=30
        )

        # Check response status
        response.raise_for_status()

        # Parse response
        result = response.json()
        agents = result.get('report', {}).get('rows', [])

        context.log("info", f"Successfully retrieved {len(agents)} active agents from HaloPSA")

        # Log agent details
        for agent in agents:
            name = agent.get('Name', 'N/A')
            email = agent.get('Email Address', 'N/A')
            team = agent.get('Team', 'N/A')
            status = agent.get('Status', 'N/A')

            context.log("info", f"Agent: {name}", {
                "email": email,
                "team": team,
                "status": status
            })

        # Save checkpoint with agent data for debugging/auditing
        context.save_checkpoint("agents_retrieved", {
            "agent_count": len(agents),
            "agents": agents
        })

        return {
            "success": True,
            "agent_count": len(agents),
            "agents": agents
        }

    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP error from HaloPSA API: {e.response.status_code} - {e.response.text}"
        context.log("error", error_msg)
        return {
            "success": False,
            "error": error_msg
        }

    except requests.exceptions.Timeout:
        error_msg = "Request to HaloPSA API timed out"
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
        error_msg = f"Unexpected error fetching HaloPSA agents: {str(e)}"
        context.log("error", error_msg, {"exception_type": type(e).__name__})
        return {
            "success": False,
            "error": error_msg
        }
