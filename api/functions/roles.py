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
import azure.functions as func

from shared.decorators import with_request_context, require_platform_admin
from shared.storage import get_table_service
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
    ErrorResponse,
    generate_entity_id
)
from pydantic import ValidationError

logger = logging.getLogger(__name__)

# Create blueprint for roles endpoints
bp = func.Blueprint()


@bp.function_name("roles_list_roles")
@bp.route(route="roles", methods=["GET"])
@with_request_context
@require_platform_admin
async def list_roles(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/roles
    List all roles

    Platform admin only endpoint
    """
    context = req.context
    logger.info(f"User {context.user_id} listing all roles")

    try:
        # Query all roles from Relationships table (GLOBAL partition, row key prefix "role:")
        relationships_service = get_table_service("Relationships", context)
        role_entities = list(relationships_service.query_entities(
            filter="PartitionKey eq 'GLOBAL' and RowKey ge 'role:' and RowKey lt 'role;' and IsActive eq true"
        ))

        # Convert to response models
        roles = []
        for entity in role_entities:
            # Extract UUID from RowKey "role:uuid"
            role_id = entity["RowKey"].split(":", 1)[1]

            role = Role(
                id=role_id,
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
@with_request_context
@require_platform_admin
async def create_role(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/roles
    Create a new role

    Platform admin only endpoint
    """
    context = req.context
    logger.info(f"User {context.user_id} creating new role")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        create_request = CreateRoleRequest(**request_body)

        # Generate role UUID
        role_id = generate_entity_id()

        # Create entity for Relationships table
        now = datetime.utcnow()
        entity = {
            "PartitionKey": "GLOBAL",  # All roles in GLOBAL partition
            "RowKey": f"role:{role_id}",
            "Name": create_request.name,
            "Description": create_request.description,
            "IsActive": True,
            "CreatedBy": context.user_id,
            "CreatedAt": now.isoformat(),
            "UpdatedAt": now.isoformat()
        }

        # Insert role into Relationships table
        relationships_service = get_table_service("Relationships", context)
        relationships_service.insert_entity(entity)

        logger.info(f"Created role '{create_request.name}' with ID {role_id}")

        # Create response model
        role = Role(
            id=role_id,
            name=create_request.name,
            description=create_request.description,
            isActive=True,
            createdBy=context.user_id,
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
@with_request_context
@require_platform_admin
async def update_role(req: func.HttpRequest) -> func.HttpResponse:
    """
    PUT /api/roles/{roleId}
    Update a role

    Platform admin only endpoint
    """
    context = req.context
    role_id = req.route_params.get("roleId")

    logger.info(f"User {context.user_id} updating role {role_id}")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        update_request = UpdateRoleRequest(**request_body)

        # Get existing role from Relationships table
        relationships_service = get_table_service("Relationships", context)
        row_key = f"role:{role_id}"

        existing_role = relationships_service.get_entity("GLOBAL", row_key)
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
        relationships_service.update_entity(existing_role)

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
@with_request_context
@require_platform_admin
async def delete_role(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/roles/{roleId}
    Soft delete a role (set IsActive=False)

    Platform admin only endpoint
    """
    context = req.context
    role_id = req.route_params.get("roleId")

    logger.info(f"User {context.user_id} deleting role {role_id}")

    try:
        # Get existing role from Relationships table
        relationships_service = get_table_service("Relationships", context)
        row_key = f"role:{role_id}"

        existing_role = relationships_service.get_entity("GLOBAL", row_key)
        if not existing_role:
            # Idempotent delete - return 204 even if not found
            logger.debug(f"Role {role_id} not found, but returning 204")
            return func.HttpResponse(status_code=204)

        # Soft delete
        existing_role["IsActive"] = False
        existing_role["UpdatedAt"] = datetime.utcnow().isoformat()
        relationships_service.update_entity(existing_role)

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
@with_request_context
@require_platform_admin
async def get_role_users(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/roles/{roleId}/users
    Get all users assigned to a role

    Platform admin only endpoint
    """
    context = req.context
    role_id = req.route_params.get("roleId")

    logger.info(f"User {context.user_id} getting users for role {role_id}")

    try:
        # Query Relationships table for assigned roles (assignedrole:role_uuid:user_id pattern)
        relationships_service = get_table_service("Relationships", context)
        user_role_entities = list(relationships_service.query_entities(
            filter=f"PartitionKey eq 'GLOBAL' and RowKey ge 'assignedrole:{role_id}:' and RowKey lt 'assignedrole:{role_id};'"
        ))

        # Extract user IDs from RowKey "assignedrole:role_uuid:user_id"
        user_ids = [entity["RowKey"].split(":", 2)[2] for entity in user_role_entities]

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
@with_request_context
@require_platform_admin
async def assign_users_to_role(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/roles/{roleId}/users
    Assign users to a role (batch operation)

    Platform admin only endpoint
    """
    context = req.context
    role_id = req.route_params.get("roleId")

    logger.info(f"User {context.user_id} assigning users to role {role_id}")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        assign_request = AssignUsersToRoleRequest(**request_body)

        # Validate role exists in Relationships table
        relationships_service = get_table_service("Relationships", context)
        role_exists = relationships_service.get_entity("GLOBAL", f"role:{role_id}")
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

        # Validate that all users exist
        users_service = get_table_service("Users", context)
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

        # Batch insert user-role assignments with DUAL INDEXING
        # Pattern: assignedrole:role_uuid:user_id AND userrole:user_id:role_uuid
        now = datetime.utcnow()

        for user_id in assign_request.userIds:
            # Primary index: assignedrole:role_uuid:user_id (for querying users by role)
            entity1 = {
                "PartitionKey": "GLOBAL",
                "RowKey": f"assignedrole:{role_id}:{user_id}",
                "UserId": user_id,
                "RoleId": role_id,
                "AssignedBy": context.user_id,
                "AssignedAt": now.isoformat()
            }

            # Dual index: userrole:user_id:role_uuid (for querying roles by user)
            entity2 = {
                "PartitionKey": "GLOBAL",
                "RowKey": f"userrole:{user_id}:{role_id}",
                "UserId": user_id,
                "RoleId": role_id,
                "AssignedBy": context.user_id,
                "AssignedAt": now.isoformat()
            }

            # Upsert both indexes
            try:
                relationships_service.insert_entity(entity1)
            except:
                relationships_service.update_entity(entity1)

            try:
                relationships_service.insert_entity(entity2)
            except:
                relationships_service.update_entity(entity2)

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
@with_request_context
@require_platform_admin
async def remove_user_from_role(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/roles/{roleId}/users/{userId}
    Remove a user from a role

    Platform admin only endpoint
    """
    context = req.context
    role_id = req.route_params.get("roleId")
    user_id = req.route_params.get("userId")

    logger.info(f"User {context.user_id} removing user {user_id} from role {role_id}")

    try:
        # Delete BOTH dual-indexed entities (idempotent)
        relationships_service = get_table_service("Relationships", context)

        # Delete primary index: assignedrole:role_uuid:user_id
        try:
            relationships_service.delete_entity("GLOBAL", f"assignedrole:{role_id}:{user_id}")
        except:
            pass  # Idempotent

        # Delete dual index: userrole:user_id:role_uuid
        try:
            relationships_service.delete_entity("GLOBAL", f"userrole:{user_id}:{role_id}")
        except:
            pass  # Idempotent

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


@bp.function_name("roles_get_role_forms")
@bp.route(route="roles/{roleId}/forms", methods=["GET"])
@with_request_context
@require_platform_admin
async def get_role_forms(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/roles/{roleId}/forms
    Get all forms assigned to a role

    Platform admin only endpoint
    """
    context = req.context
    role_id = req.route_params.get("roleId")

    logger.info(f"User {context.user_id} getting forms for role {role_id}")

    try:
        # Query Relationships table for role-form assignments (roleform:role_uuid:form_uuid pattern)
        relationships_service = get_table_service("Relationships", context)
        role_form_entities = list(relationships_service.query_entities(
            filter=f"PartitionKey eq 'GLOBAL' and RowKey ge 'roleform:{role_id}:' and RowKey lt 'roleform:{role_id};'"
        ))

        # Extract form UUIDs from RowKey "roleform:role_uuid:form_uuid"
        form_ids = [entity["RowKey"].split(":", 2)[2] for entity in role_form_entities]

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
@with_request_context
@require_platform_admin
async def assign_forms_to_role(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/roles/{roleId}/forms
    Assign forms to a role (batch operation)

    Platform admin only endpoint
    """
    context = req.context
    role_id = req.route_params.get("roleId")

    logger.info(f"User {context.user_id} assigning forms to role {role_id}")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        assign_request = AssignFormsToRoleRequest(**request_body)

        # Validate role exists in Relationships table
        relationships_service = get_table_service("Relationships", context)
        role_exists = relationships_service.get_entity("GLOBAL", f"role:{role_id}")
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

        # Batch insert form-role assignments with DUAL INDEXING
        # Pattern: formrole:form_uuid:role_uuid AND roleform:role_uuid:form_uuid
        now = datetime.utcnow()

        for form_id in assign_request.formIds:
            # Primary index: formrole:form_uuid:role_uuid (for querying roles by form)
            entity1 = {
                "PartitionKey": "GLOBAL",
                "RowKey": f"formrole:{form_id}:{role_id}",
                "FormId": form_id,
                "RoleId": role_id,
                "AssignedBy": context.user_id,
                "AssignedAt": now.isoformat()
            }

            # Dual index: roleform:role_uuid:form_uuid (for querying forms by role)
            entity2 = {
                "PartitionKey": "GLOBAL",
                "RowKey": f"roleform:{role_id}:{form_id}",
                "FormId": form_id,
                "RoleId": role_id,
                "AssignedBy": context.user_id,
                "AssignedAt": now.isoformat()
            }

            # Upsert both indexes
            try:
                relationships_service.insert_entity(entity1)
            except:
                relationships_service.update_entity(entity1)

            try:
                relationships_service.insert_entity(entity2)
            except:
                relationships_service.update_entity(entity2)

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
@with_request_context
@require_platform_admin
async def remove_form_from_role(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/roles/{roleId}/forms/{formId}
    Remove a form from a role

    Platform admin only endpoint
    """
    context = req.context
    role_id = req.route_params.get("roleId")
    form_id = req.route_params.get("formId")

    logger.info(f"User {context.user_id} removing form {form_id} from role {role_id}")

    try:
        # Delete BOTH dual-indexed entities (idempotent)
        relationships_service = get_table_service("Relationships", context)

        # Delete primary index: formrole:form_uuid:role_uuid
        try:
            relationships_service.delete_entity("GLOBAL", f"formrole:{form_id}:{role_id}")
        except:
            pass  # Idempotent

        # Delete dual index: roleform:role_uuid:form_uuid
        try:
            relationships_service.delete_entity("GLOBAL", f"roleform:{role_id}:{form_id}")
        except:
            pass  # Idempotent

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
