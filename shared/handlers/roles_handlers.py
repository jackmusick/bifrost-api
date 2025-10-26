"""
Roles Handlers
Business logic for role management
Extracted from functions/roles.py for unit testability
"""

import json
import logging

import azure.functions as func
from pydantic import ValidationError

from shared.models import (
    AssignFormsToRoleRequest,
    AssignUsersToRoleRequest,
    CreateRoleRequest,
    ErrorResponse,
    UpdateRoleRequest,
)
from shared.repositories.roles import RoleRepository
from shared.repositories.users import UserRepository

logger = logging.getLogger(__name__)


async def list_roles_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/roles
    List all roles

    Platform admin only endpoint
    """
    context = req.context  # type: ignore[attr-defined]
    logger.info(f"User {context.user_id} listing all roles")

    try:
        # Get all roles using repository
        role_repo = RoleRepository()
        roles = await role_repo.list_roles(org_id=context.org_id or "GLOBAL", active_only=True)

        # Sort roles by createdAt descending (most recent first)
        roles.sort(key=lambda r: r.createdAt, reverse=True)

        logger.info(f"Returning {len(roles)} roles")

        return func.HttpResponse(
            json.dumps([r.model_dump(mode="json") for r in roles]),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error listing roles: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to list roles"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


async def create_role_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/roles
    Create a new role

    Platform admin only endpoint
    """
    context = req.context  # type: ignore[attr-defined]
    logger.info(f"User {context.user_id} creating new role")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        create_request = CreateRoleRequest(**request_body)

        # Create role using repository
        role_repo = RoleRepository()
        role = await role_repo.create_role(
            role_request=create_request,
            org_id=context.org_id or "GLOBAL",
            created_by=context.user_id
        )

        logger.info(f"Created role '{role.name}' with ID {role.id}")

        return func.HttpResponse(
            json.dumps(role.model_dump(mode="json")),
            status_code=201,
            mimetype="application/json"
        )

    except ValidationError as e:
        logger.warning(f"Validation error creating role: {e}")
        error = ErrorResponse(
            error="ValidationError",
            message="Invalid request data",
            details={"errors": e.errors()}
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    except ValueError as e:
        logger.error(f"Error parsing request: {str(e)}")
        error = ErrorResponse(
            error="BadRequest",
            message="Invalid JSON in request body"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error creating role: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to create role"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


async def update_role_handler(req: func.HttpRequest, role_id: str) -> func.HttpResponse:
    """
    PUT /api/roles/{roleId}
    Update a role

    Platform admin only endpoint
    """
    context = req.context  # type: ignore[attr-defined]
    logger.info(f"User {context.user_id} updating role {role_id}")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        update_request = UpdateRoleRequest(**request_body)

        # Update role using repository
        role_repo = RoleRepository()
        role = await role_repo.update_role(
            role_id=role_id,
            org_id=context.org_id or "GLOBAL",
            updates=update_request
        )

        logger.info(f"Updated role {role_id}")

        return func.HttpResponse(
            json.dumps(role.model_dump(mode="json")),
            status_code=200,
            mimetype="application/json"
        )

    except ValidationError as e:
        logger.warning(f"Validation error updating role: {e}")
        error = ErrorResponse(
            error="ValidationError",
            message="Invalid request data",
            details={"errors": e.errors()}
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error updating role: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to update role"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


async def delete_role_handler(req: func.HttpRequest, role_id: str) -> func.HttpResponse:
    """
    DELETE /api/roles/{roleId}
    Soft delete a role (set IsActive=False)

    Platform admin only endpoint
    """
    context = req.context  # type: ignore[attr-defined]
    logger.info(f"User {context.user_id} deleting role {role_id}")

    try:
        # Soft delete using repository (idempotent - returns False if not found)
        role_repo = RoleRepository()
        await role_repo.delete_role(role_id, context.org_id or "GLOBAL")

        logger.info(f"Soft deleted role {role_id}")

        return func.HttpResponse(status_code=204)

    except Exception as e:
        logger.error(f"Error deleting role: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to delete role"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


async def get_role_users_handler(req: func.HttpRequest, role_id: str) -> func.HttpResponse:
    """
    GET /api/roles/{roleId}/users
    Get all users assigned to a role

    Platform admin only endpoint
    """
    context = req.context  # type: ignore[attr-defined]
    logger.info(f"User {context.user_id} getting users for role {role_id}")

    try:
        # Get role users using repository
        role_repo = RoleRepository()
        user_ids = await role_repo.get_role_user_ids(role_id)

        logger.info(f"Role {role_id} has {len(user_ids)} users assigned")

        return func.HttpResponse(
            json.dumps({"userIds": user_ids}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error getting role users: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to get role users"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


async def assign_users_to_role_handler(req: func.HttpRequest, role_id: str) -> func.HttpResponse:
    """
    POST /api/roles/{roleId}/users
    Assign users to a role (batch operation)

    Platform admin only endpoint
    """
    context = req.context  # type: ignore[attr-defined]
    logger.info(f"User {context.user_id} assigning users to role {role_id}")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        assign_request = AssignUsersToRoleRequest(**request_body)

        # Validate role exists
        role_repo = RoleRepository()
        role = await role_repo.get_role(role_id, context.org_id or "GLOBAL")
        if not role:
            error = ErrorResponse(
                error="NotFound",
                message=f"Role {role_id} not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Validate that all users exist and are not platform admins
        user_repo = UserRepository()
        for user_id in assign_request.userIds:
            user = await user_repo.get_user(user_id)
            if not user:
                error = ErrorResponse(
                    error="BadRequest",
                    message=f"User {user_id} not found"
                )
                return func.HttpResponse(
                    json.dumps(error.model_dump()),
                    status_code=400,
                    mimetype="application/json"
                )

            # Check if the user is a PlatformAdmin
            if user.isPlatformAdmin:
                error = ErrorResponse(
                    error="BadRequest",
                    message=f"Cannot assign roles to Platform Administrator: {user_id}"
                )
                return func.HttpResponse(
                    json.dumps(error.model_dump()),
                    status_code=400,
                    mimetype="application/json"
                )

        # Assign users using repository (handles dual indexing automatically)
        await role_repo.assign_users_to_role(
            role_id=role_id,
            user_ids=assign_request.userIds,
            assigned_by=context.user_id
        )

        logger.info(f"Assigned {len(assign_request.userIds)} users to role {role_id}")

        return func.HttpResponse(
            json.dumps({"message": f"Assigned {len(assign_request.userIds)} users to role"}),
            status_code=200,
            mimetype="application/json"
        )

    except ValidationError as e:
        logger.warning(f"Validation error assigning users: {e}")
        error = ErrorResponse(
            error="ValidationError",
            message="Invalid request data",
            details={"errors": e.errors()}
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error assigning users to role: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to assign users to role"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


async def remove_user_from_role_handler(req: func.HttpRequest, role_id: str, user_id: str) -> func.HttpResponse:
    """
    DELETE /api/roles/{roleId}/users/{userId}
    Remove a user from a role

    Platform admin only endpoint
    """
    context = req.context  # type: ignore[attr-defined]

    # Validate route parameters
    if not role_id:
        error = ErrorResponse(
            error="BadRequest",
            message="Role ID is required"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    if not user_id:
        error = ErrorResponse(
            error="BadRequest",
            message="User ID is required"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    logger.info(f"User {context.user_id} removing user {user_id} from role {role_id}")

    try:
        # Remove user from role using repository (handles dual indexing automatically, idempotent)
        role_repo = RoleRepository()
        await role_repo.remove_user_from_role(role_id, user_id)

        logger.info(f"Removed user {user_id} from role {role_id}")

        return func.HttpResponse(status_code=204)

    except Exception as e:
        logger.error(f"Error removing user from role: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to remove user from role"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


async def get_role_forms_handler(req: func.HttpRequest, role_id: str) -> func.HttpResponse:
    """
    GET /api/roles/{roleId}/forms
    Get all forms assigned to a role

    Platform admin only endpoint
    """
    context = req.context  # type: ignore[attr-defined]
    logger.info(f"User {context.user_id} getting forms for role {role_id}")

    try:
        # Get role forms using repository
        role_repo = RoleRepository()
        form_ids = await role_repo.get_role_form_ids(role_id)

        logger.info(f"Role {role_id} has access to {len(form_ids)} forms")

        return func.HttpResponse(
            json.dumps({"formIds": form_ids}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error getting role forms: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to get role forms"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


async def assign_forms_to_role_handler(req: func.HttpRequest, role_id: str) -> func.HttpResponse:
    """
    POST /api/roles/{roleId}/forms
    Assign forms to a role (batch operation)

    Platform admin only endpoint
    """
    context = req.context  # type: ignore[attr-defined]
    logger.info(f"User {context.user_id} assigning forms to role {role_id}")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        assign_request = AssignFormsToRoleRequest(**request_body)

        # Validate role exists
        role_repo = RoleRepository()
        role = await role_repo.get_role(role_id, context.org_id or "GLOBAL")
        if not role:
            error = ErrorResponse(
                error="NotFound",
                message=f"Role {role_id} not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Assign forms using repository (handles dual indexing automatically)
        await role_repo.assign_forms_to_role(
            role_id=role_id,
            form_ids=assign_request.formIds,
            assigned_by=context.user_id
        )

        logger.info(f"Assigned {len(assign_request.formIds)} forms to role {role_id}")

        return func.HttpResponse(
            json.dumps({"message": f"Assigned {len(assign_request.formIds)} forms to role"}),
            status_code=200,
            mimetype="application/json"
        )

    except ValidationError as e:
        logger.warning(f"Validation error assigning forms: {e}")
        error = ErrorResponse(
            error="ValidationError",
            message="Invalid request data",
            details={"errors": e.errors()}
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error assigning forms to role: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to assign forms to role"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


async def remove_form_from_role_handler(req: func.HttpRequest, role_id: str, form_id: str) -> func.HttpResponse:
    """
    DELETE /api/roles/{roleId}/forms/{formId}
    Remove a form from a role

    Platform admin only endpoint
    """
    context = req.context  # type: ignore[attr-defined]

    # Validate route parameters
    if not role_id:
        error = ErrorResponse(
            error="BadRequest",
            message="Role ID is required"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    if not form_id:
        error = ErrorResponse(
            error="BadRequest",
            message="Form ID is required"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    logger.info(f"User {context.user_id} removing form {form_id} from role {role_id}")

    try:
        # Remove form from role using repository (handles dual indexing automatically, idempotent)
        role_repo = RoleRepository()
        await role_repo.remove_form_from_role(role_id, form_id)

        logger.info(f"Removed form {form_id} from role {role_id}")

        return func.HttpResponse(status_code=204)

    except Exception as e:
        logger.error(f"Error removing form from role: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to remove form from role"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )
