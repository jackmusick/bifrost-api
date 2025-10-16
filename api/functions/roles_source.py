"""
Roles Source API for Azure Static Web Apps
Called automatically by SWA after user authentication to determine user roles

This function is invoked by SWA's rolesSource configuration:
{
  "auth": {
    "rolesSource": "/api/GetRoles"
  }
}
"""

import json
import logging

import azure.functions as func

from shared.storage import TableStorageService

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

        if not user_id:
            logger.warning("No userId provided in GetRoles request")
            return func.HttpResponse(
                json.dumps({"roles": ["anonymous"]}),
                status_code=200,
                mimetype="application/json"
            )

        # Query Users table to get user details
        users_service = TableStorageService("Users")
        user_entity = users_service.get_entity("USER", user_id)

        if not user_entity:
            logger.warning(f"User {user_id} not found in database, assigning anonymous role")
            return func.HttpResponse(
                json.dumps({"roles": ["anonymous"]}),
                status_code=200,
                mimetype="application/json"
            )

        # Start building roles list
        roles = ["authenticated"]  # All authenticated users get this base role

        # Check if platform admin
        is_platform_admin = user_entity.get("IsPlatformAdmin", False)
        user_type = user_entity.get("UserType", "ORG")

        if is_platform_admin and user_type == "PLATFORM":
            roles.append("PlatformAdmin")
            logger.info(f"User {user_email} assigned PlatformAdmin role")
        else:
            # Organization user
            roles.append("OrgUser")
            logger.info(f"User {user_email} assigned OrgUser role")

        # Return roles to SWA
        response = {"roles": roles}
        logger.info(f"Returning roles for {user_email}: {roles}")

        return func.HttpResponse(
            json.dumps(response),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in GetRoles: {str(e)}", exc_info=True)
        # On error, return minimal roles to be safe
        return func.HttpResponse(
            json.dumps({"roles": ["anonymous"]}),
            status_code=200,
            mimetype="application/json"
        )
