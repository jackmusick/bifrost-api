"""
Roles Source API for Azure Static Web Apps
Called automatically by SWA after user authentication to determine user roles

This function is invoked by SWA's rolesSource configuration:
{
  "auth": {
    "rolesSource": "/api/GetRoles"
  }
}

Note: This endpoint delegates to shared/handlers/roles_source_handlers.py for all
role determination logic and to shared/user_provisioning.py for auto-provisioning.
"""

import json
import logging

import azure.functions as func

from shared.handlers.roles_source_handlers import handle_roles_source_request

logger = logging.getLogger(__name__)

# Create blueprint for roles source endpoint
bp = func.Blueprint()


@bp.function_name("get_roles")
@bp.route(route="GetRoles", methods=["POST"])
async def get_roles(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/GetRoles

    Called by Azure Static Web Apps after authentication to determine user roles.

    Request body from SWA:
    {
      "identityProvider": "aad",
      "userId": "user-id-from-azure-ad",
      "userDetails": "user@example.com",
      "claims": [...]
    }

    Response format:
    {
      "roles": ["PlatformAdmin", "OrgUser", "authenticated"]
    }
    """
    try:
        # Parse request from SWA
        request_body = req.get_json()

        # Log request for debugging (SWA CLI local dev may not populate body correctly)
        logger.info(f"GetRoles request body: {json.dumps(request_body)}")

        # Call async handler
        response = await handle_roles_source_request(request_body)

        return func.HttpResponse(
            json.dumps(response),
            status_code=200,
            mimetype="application/json",
        )

    except ValueError as e:
        # User could not be provisioned (no domain match)
        logger.warning(f"User provisioning failed: {e}")
        return func.HttpResponse(
            json.dumps({"roles": ["anonymous"]}),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Error in GetRoles: {str(e)}", exc_info=True)
        # On error, return minimal roles to be safe
        return func.HttpResponse(
            json.dumps({"roles": ["anonymous"]}),
            status_code=200,
            mimetype="application/json",
        )
