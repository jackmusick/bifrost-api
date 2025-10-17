"""
Roles Source API for Azure Static Web Apps
Called automatically by SWA after user authentication to determine user roles

This function is invoked by SWA's rolesSource configuration:
{
  "auth": {
    "rolesSource": "/api/GetRoles"
  }
}

Note: This endpoint delegates to shared/user_provisioning.py for all
auto-provisioning logic (first user, domain-based join, etc.)
"""

import json
import logging

import azure.functions as func

from shared.user_provisioning import ensure_user_provisioned

logger = logging.getLogger(__name__)

# Create blueprint for roles source endpoint
bp = func.Blueprint()


@bp.function_name("get_roles")
@bp.route(route="GetRoles", methods=["POST"])
def get_roles(req: func.HttpRequest) -> func.HttpResponse:
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
      "roles": ["PlatformAdmin", "CanExecuteWorkflows", "CanManageForms"]
    }
    """
    try:
        # Parse request from SWA
        request_body = req.get_json()
        user_id = request_body.get("userId")
        user_email = request_body.get("userDetails")

        logger.info(f"GetRoles called for user: {user_email} (ID: {user_id})")

        if not user_id or not user_email:
            logger.warning("No userId/userDetails provided in GetRoles request")
            return func.HttpResponse(
                json.dumps({"roles": ["anonymous"]}),
                status_code=200,
                mimetype="application/json",
            )

        # Ensure user is provisioned (handles first user, domain-based join, etc.)
        try:
            result = ensure_user_provisioned(user_email)

            # Return roles based on provisioning result
            response = {"roles": result.roles}
            logger.info(f"Returning roles for {user_email}: {result.roles}")

            return func.HttpResponse(
                json.dumps(response),
                status_code=200,
                mimetype="application/json",
            )

        except ValueError as e:
            # User could not be auto-provisioned (no domain match)
            logger.warning(f"User {user_email} could not be provisioned: {e}")
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
