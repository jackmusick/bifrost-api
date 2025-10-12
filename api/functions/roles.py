"""
Roles API endpoints
- Manage roles for organization users
- Assign users to roles (UserRoles)
- Assign forms to roles (FormRoles)
"""

import logging
import json
from datetime import datetime
from typing import List
import uuid
import azure.functions as func

from shared.auth import require_auth
from shared.storage import TableStorageService
from shared.models import (
    Role,
    CreateRoleRequest,
    UpdateRoleRequest,
    UserRole,
    FormRole,
    AssignUsersToRoleRequest,
    AssignFormsToRoleRequest,
    User,
    UserType,
    ErrorResponse
)
from pydantic import ValidationError

logger = logging.getLogger(__name__)

# Create blueprint for roles endpoints
bp = func.Blueprint()


@bp.function_name("roles_list_roles")
@bp.route(route="roles", methods=["GET"])
@require_auth
def list_roles(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/roles
    List all roles

    Requires: User must be authenticated
    """
    user = req.user

    logger.info(f"User {user.email} listing all roles")

    try:
        # Query all roles (single partition for all roles)
        roles_service = TableStorageService("Roles")
        role_entities = list(roles_service.query_by_org("ROLES", row_key_prefix="role:"))

        # Convert to response models
        roles = []
        for entity in role_entities:
            # Skip soft-deleted roles unless specifically requested
            if not entity.get("IsActive", True):
                continue

            role = Role(
                id=entity["RowKey"].replace("role:", "", 1),
                name=entity["Name"],
                description=entity.get("Description"),
                isActive=entity.get("IsActive", True),
                createdBy=entity["CreatedBy"],
                createdAt=entity["CreatedAt"],
                updatedAt=entity["UpdatedAt"]
            )
            roles.append(role.model_dump(mode="json"))

        logger.info(f"Returning {len(roles)} roles")

        return func.HttpResponse(
            json.dumps(roles),
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


@bp.function_name("roles_create_role")
@bp.route(route="roles", methods=["POST"])
@require_auth
def create_role(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/roles
    Create a new role

    Requires: User must be MSP admin (TODO: implement check)
    """
    user = req.user

    logger.info(f"User {user.email} creating new role")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        create_request = CreateRoleRequest(**request_body)

        # Generate role ID
        role_id = str(uuid.uuid4())

        # Create entity for Table Storage
        now = datetime.utcnow()
        entity = {
            "PartitionKey": "ROLES",  # Single partition for all roles
            "RowKey": f"role:{role_id}",
            "Name": create_request.name,
            "Description": create_request.description,
            "IsActive": True,
            "CreatedBy": user.user_id,
            "CreatedAt": now.isoformat(),
            "UpdatedAt": now.isoformat()
        }

        # Insert role
        roles_service = TableStorageService("Roles")
        roles_service.insert_entity(entity)

        logger.info(f"Created role '{create_request.name}' with ID {role_id}")

        # Create response model
        role = Role(
            id=role_id,
            name=create_request.name,
            description=create_request.description,
            isActive=True,
            createdBy=user.user_id,
            createdAt=now,
            updatedAt=now
        )

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


@bp.function_name("roles_update_role")
@bp.route(route="roles/{roleId}", methods=["PUT"])
@require_auth
def update_role(req: func.HttpRequest) -> func.HttpResponse:
    """
    PUT /api/roles/{roleId}
    Update a role

    Requires: User must be MSP admin (TODO: implement check)
    """
    user = req.user
    role_id = req.route_params.get("roleId")

    logger.info(f"User {user.email} updating role {role_id}")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        update_request = UpdateRoleRequest(**request_body)

        # Get existing role
        roles_service = TableStorageService("Roles")
        row_key = f"role:{role_id}"

        existing_role = roles_service.get_entity("ROLES", row_key)
        if not existing_role:
            error = ErrorResponse(
                error="NotFound",
                message=f"Role {role_id} not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Update fields (only if provided)
        now = datetime.utcnow()
        if update_request.name is not None:
            existing_role["Name"] = update_request.name
        if update_request.description is not None:
            existing_role["Description"] = update_request.description
        existing_role["UpdatedAt"] = now.isoformat()

        # Update entity
        roles_service.update_entity(existing_role)

        logger.info(f"Updated role {role_id}")

        # Create response model
        role = Role(
            id=role_id,
            name=existing_role["Name"],
            description=existing_role.get("Description"),
            isActive=existing_role.get("IsActive", True),
            createdBy=existing_role["CreatedBy"],
            createdAt=existing_role["CreatedAt"],
            updatedAt=now
        )

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


@bp.function_name("roles_delete_role")
@bp.route(route="roles/{roleId}", methods=["DELETE"])
@require_auth
def delete_role(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/roles/{roleId}
    Soft delete a role (set IsActive=False)

    Requires: User must be MSP admin (TODO: implement check)
    """
    user = req.user
    role_id = req.route_params.get("roleId")

    logger.info(f"User {user.email} deleting role {role_id}")

    try:
        # Get existing role
        roles_service = TableStorageService("Roles")
        row_key = f"role:{role_id}"

        existing_role = roles_service.get_entity("ROLES", row_key)
        if not existing_role:
            # Idempotent delete - return 204 even if not found
            logger.debug(f"Role {role_id} not found, but returning 204")
            return func.HttpResponse(status_code=204)

        # Soft delete
        existing_role["IsActive"] = False
        existing_role["UpdatedAt"] = datetime.utcnow().isoformat()
        roles_service.update_entity(existing_role)

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


@bp.function_name("roles_get_role_users")
@bp.route(route="roles/{roleId}/users", methods=["GET"])
@require_auth
def get_role_users(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/roles/{roleId}/users
    Get all users assigned to a role

    Requires: User must be authenticated
    """
    user = req.user
    role_id = req.route_params.get("roleId")

    logger.info(f"User {user.email} getting users for role {role_id}")

    try:
        # Query UserRoles table by role (partition by roleId)
        user_roles_service = TableStorageService("UserRoles")
        user_role_entities = list(user_roles_service.query_by_org(role_id, row_key_prefix="user:"))

        # Extract user IDs
        user_ids = [entity["RowKey"].replace("user:", "", 1) for entity in user_role_entities]

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


@bp.function_name("roles_assign_users_to_role")
@bp.route(route="roles/{roleId}/users", methods=["POST"])
@require_auth
def assign_users_to_role(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/roles/{roleId}/users
    Assign users to a role (batch operation)

    Validates that users are ORG type (MSP users cannot be assigned to roles)

    Requires: User must be MSP admin (TODO: implement check)
    """
    user = req.user
    role_id = req.route_params.get("roleId")

    logger.info(f"User {user.email} assigning users to role {role_id}")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        assign_request = AssignUsersToRoleRequest(**request_body)

        # Validate role exists
        roles_service = TableStorageService("Roles")
        role_exists = roles_service.get_entity("ROLES", f"role:{role_id}")
        if not role_exists:
            error = ErrorResponse(
                error="NotFound",
                message=f"Role {role_id} not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Validate that all users are ORG type (not MSP)
        users_service = TableStorageService("Users")
        for user_id in assign_request.userIds:
            user_entity = users_service.get_entity(user_id, "user")
            if not user_entity:
                error = ErrorResponse(
                    error="BadRequest",
                    message=f"User {user_id} not found"
                )
                return func.HttpResponse(
                    json.dumps(error.model_dump()),
                    status_code=400,
                    mimetype="application/json"
                )

            # Check user type
            user_type = user_entity.get("UserType", "MSP")
            if user_type == "MSP":
                error = ErrorResponse(
                    error="BadRequest",
                    message=f"Cannot assign MSP user {user_id} to a role. Only ORG users can have roles."
                )
                return func.HttpResponse(
                    json.dumps(error.model_dump()),
                    status_code=400,
                    mimetype="application/json"
                )

        # Batch insert UserRoles (PartitionKey=roleId, RowKey=user:{userId})
        user_roles_service = TableStorageService("UserRoles")
        now = datetime.utcnow()

        for user_id in assign_request.userIds:
            entity = {
                "PartitionKey": role_id,
                "RowKey": f"user:{user_id}",
                "UserId": user_id,
                "RoleId": role_id,
                "AssignedBy": user.user_id,
                "AssignedAt": now.isoformat()
            }

            # Upsert (overwrite if already exists)
            try:
                user_roles_service.insert_entity(entity)
            except:
                # If already exists, update it
                user_roles_service.update_entity(entity)

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


@bp.function_name("roles_remove_user_from_role")
@bp.route(route="roles/{roleId}/users/{userId}", methods=["DELETE"])
@require_auth
def remove_user_from_role(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/roles/{roleId}/users/{userId}
    Remove a user from a role

    Requires: User must be MSP admin (TODO: implement check)
    """
    user = req.user
    role_id = req.route_params.get("roleId")
    user_id = req.route_params.get("userId")

    logger.info(f"User {user.email} removing user {user_id} from role {role_id}")

    try:
        # Delete UserRole entity (idempotent)
        user_roles_service = TableStorageService("UserRoles")
        row_key = f"user:{user_id}"

        try:
            user_roles_service.delete_entity(role_id, row_key)
            logger.info(f"Removed user {user_id} from role {role_id}")
        except:
            # Even if not found, return 204 (idempotent)
            logger.debug(f"UserRole not found, but returning 204")

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


@bp.function_name("roles_get_role_forms")
@bp.route(route="roles/{roleId}/forms", methods=["GET"])
@require_auth
def get_role_forms(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/roles/{roleId}/forms
    Get all forms assigned to a role

    Requires: User must be authenticated
    """
    user = req.user
    role_id = req.route_params.get("roleId")

    logger.info(f"User {user.email} getting forms for role {role_id}")

    try:
        # Query FormRoles table by form (partition by formId)
        # Note: We need to scan all partitions to find forms for this role
        # This is acceptable for POC, but consider dual-indexing for production
        form_roles_service = TableStorageService("FormRoles")

        # For now, we'll use a simple approach: query with filter
        # In production, consider maintaining a RoleFormsIndex table
        all_form_roles = list(form_roles_service.query_entities(
            filter=f"RoleId eq '{role_id}'"
        ))

        form_ids = [entity["PartitionKey"] for entity in all_form_roles]

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


@bp.function_name("roles_assign_forms_to_role")
@bp.route(route="roles/{roleId}/forms", methods=["POST"])
@require_auth
def assign_forms_to_role(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/roles/{roleId}/forms
    Assign forms to a role (batch operation)

    Requires: User must be MSP admin (TODO: implement check)
    """
    user = req.user
    role_id = req.route_params.get("roleId")

    logger.info(f"User {user.email} assigning forms to role {role_id}")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        assign_request = AssignFormsToRoleRequest(**request_body)

        # Validate role exists
        roles_service = TableStorageService("Roles")
        role_exists = roles_service.get_entity("ROLES", f"role:{role_id}")
        if not role_exists:
            error = ErrorResponse(
                error="NotFound",
                message=f"Role {role_id} not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Batch insert FormRoles (PartitionKey=formId, RowKey=role:{roleId})
        form_roles_service = TableStorageService("FormRoles")
        now = datetime.utcnow()

        for form_id in assign_request.formIds:
            entity = {
                "PartitionKey": form_id,
                "RowKey": f"role:{role_id}",
                "FormId": form_id,
                "RoleId": role_id,
                "AssignedBy": user.user_id,
                "AssignedAt": now.isoformat()
            }

            # Upsert (overwrite if already exists)
            try:
                form_roles_service.insert_entity(entity)
            except:
                # If already exists, update it
                form_roles_service.update_entity(entity)

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


@bp.function_name("roles_remove_form_from_role")
@bp.route(route="roles/{roleId}/forms/{formId}", methods=["DELETE"])
@require_auth
def remove_form_from_role(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/roles/{roleId}/forms/{formId}
    Remove a form from a role

    Requires: User must be MSP admin (TODO: implement check)
    """
    user = req.user
    role_id = req.route_params.get("roleId")
    form_id = req.route_params.get("formId")

    logger.info(f"User {user.email} removing form {form_id} from role {role_id}")

    try:
        # Delete FormRole entity (idempotent)
        form_roles_service = TableStorageService("FormRoles")
        row_key = f"role:{role_id}"

        try:
            form_roles_service.delete_entity(form_id, row_key)
            logger.info(f"Removed form {form_id} from role {role_id}")
        except:
            # Even if not found, return 204 (idempotent)
            logger.debug(f"FormRole not found, but returning 204")

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
