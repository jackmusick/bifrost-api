"""
Forms API endpoints
- CRUD operations for workflow forms
- Support for org-specific and global forms
"""

import logging
import json
from datetime import datetime
from typing import List
import azure.functions as func
import uuid

from shared.auth import require_auth, is_platform_admin
from shared.storage import TableStorageService
from shared.models import (
    Form,
    CreateFormRequest,
    UpdateFormRequest,
    ErrorResponse
)
from pydantic import ValidationError

logger = logging.getLogger(__name__)

# Create blueprint for forms endpoints
bp = func.Blueprint()


@bp.function_name("forms_list_forms")
@bp.route(route="forms", methods=["GET"])
@require_auth
def list_forms(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/forms
    List all forms for an organization (org-specific + global)

    Headers:
    - X-Organization-Id: Organization ID (optional for platform admins)

    Returns:
    - Platform admins without org: All forms (all orgs + global)
    - Platform admins with org: Org forms + global forms
    - Org users: Only forms they can access (public forms + forms assigned to their groups)
    """
    from shared.auth_headers import get_auth_headers

    user = req.user

    # Get auth headers - org is optional for platform admins
    org_id, user_id, error = get_auth_headers(req, require_org=False)
    if error:
        return error

    logger.info(f"User {user.email} listing forms for org {org_id}")

    try:
        # Query Forms table for forms
        forms_service = TableStorageService("Forms")

        # Platform admins without org_id: get ALL forms from all orgs
        if not org_id:
            logger.info(f"Platform admin {user.email} listing all forms (no org filter)")
            all_forms = list(forms_service.query_entities(
                filter="IsActive eq true"
            ))
        else:
            # Org-specific query: get org-specific + global forms
            # Get org-specific forms
            org_forms = list(forms_service.query_entities(
                filter=f"PartitionKey eq '{org_id}' and IsActive eq true"
            ))

            # Get global forms
            global_forms = list(forms_service.query_entities(
                filter="PartitionKey eq 'GLOBAL' and IsActive eq true"
            ))

            all_forms = org_forms + global_forms

        # Filter forms based on user access
        is_admin = is_platform_admin(user.user_id)

        # Get user's groups for filtering (if not admin)
        user_group_ids = []
        if not is_admin:
            user_roles_service = TableStorageService("UserRoles")
            user_role_entities = list(user_roles_service.query_entities(
                filter=f"UserId eq '{user.user_id}'"
            ))
            user_group_ids = [entity["RoleId"] for entity in user_role_entities]
            logger.debug(f"User {user.user_id} is in groups: {user_group_ids}")

        # Get form-group assignments for filtering
        form_roles_service = TableStorageService("FormRoles")

        # Convert to response models and filter
        forms = []
        for entity in all_forms:
            # Parse formSchema from JSON string
            form_schema = json.loads(entity["FormSchema"]) if isinstance(entity["FormSchema"], str) else entity["FormSchema"]

            # Check if user has access to this form
            if is_admin:
                has_access = True
            elif entity.get("IsPublic", False):
                has_access = True
            else:
                # Check if form is assigned to any of user's groups
                form_id = entity["RowKey"]
                has_access = False
                for group_id in user_group_ids:
                    if form_roles_service.get_entity(form_id, f"role:{group_id}"):
                        has_access = True
                        break

            if has_access:
                form = Form(
                    id=entity["RowKey"],
                    orgId=entity["PartitionKey"],
                    name=entity["Name"],
                    description=entity.get("Description"),
                    linkedWorkflow=entity["LinkedWorkflow"],
                    formSchema=form_schema,
                    isActive=entity.get("IsActive", True),
                    isGlobal=entity["PartitionKey"] == "GLOBAL",
                    isPublic=entity.get("IsPublic", False),
                    createdBy=entity["CreatedBy"],
                    createdAt=entity["CreatedAt"],
                    updatedAt=entity["UpdatedAt"]
                )
                forms.append(form.model_dump(mode="json"))

        # Sort by name
        forms.sort(key=lambda f: f["name"])

        logger.info(f"Returning {len(forms)} forms for org {org_id} (user has access to)")

        return func.HttpResponse(
            json.dumps(forms),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error listing forms: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to list forms"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("forms_create_form")
@bp.route(route="forms", methods=["POST"])
@require_auth
def create_form(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/forms    Create a new form

    Headers:
    - X-Organization-Id: Organization ID (required)

    Requires: User must be PlatformAdmin
    """
    user = req.user
    org_id = req.headers.get("X-Organization-Id")

    logger.info(f"User {user.email} creating form for org {org_id}")

    try:
        # Validate query parameter
        if not org_id:
            error = ErrorResponse(
                error="BadRequest",
                message="X-Organization-Id header is required"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # Only platform admins can create forms
        if not is_platform_admin(user.user_id):
            logger.warning(f"User {user.email} is not a platform admin - denied form creation")
            error = ErrorResponse(
                error="Forbidden",
                message="Only platform administrators can create forms"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        # Parse and validate request body
        request_body = req.get_json()
        create_request = CreateFormRequest(**request_body)

        # Create form entity
        form_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Determine partition key based on isGlobal flag
        partition_key = "GLOBAL" if create_request.isGlobal else org_id

        form_entity = {
            "PartitionKey": partition_key,
            "RowKey": form_id,
            "Name": create_request.name,
            "Description": create_request.description,
            "LinkedWorkflow": create_request.linkedWorkflow,
            "FormSchema": json.dumps(create_request.formSchema.model_dump()),
            "IsActive": True,
            "IsPublic": create_request.isPublic,
            "CreatedBy": user.user_id,
            "CreatedAt": now.isoformat(),
            "UpdatedAt": now.isoformat()
        }

        # Insert entity
        forms_service = TableStorageService("Forms")
        forms_service.upsert_entity(form_entity)

        logger.info(f"Created form {form_id} for org {org_id}")

        # Create response model
        form_response = Form(
            id=form_id,
            orgId=partition_key,
            name=create_request.name,
            description=create_request.description,
            linkedWorkflow=create_request.linkedWorkflow,
            formSchema=create_request.formSchema,
            isActive=True,
            isGlobal=create_request.isGlobal,
            isPublic=create_request.isPublic,
            createdBy=user.user_id,
            createdAt=now,
            updatedAt=now
        )

        return func.HttpResponse(
            json.dumps(form_response.model_dump(mode="json")),
            status_code=201,
            mimetype="application/json"
        )

    except ValidationError as e:
        logger.warning(f"Validation error creating form: {e}")
        # Convert validation errors to JSON-serializable format
        errors = []
        for err in e.errors():
            error_dict = {"loc": err["loc"], "type": err["type"], "msg": str(err["msg"])}
            if "input" in err:
                error_dict["input"] = str(err["input"])
            errors.append(error_dict)

        error = ErrorResponse(
            error="ValidationError",
            message="Invalid request data",
            details={"errors": errors}
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
        logger.error(f"Error creating form: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to create form"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("forms_get_form")
@bp.route(route="forms/{formId}", methods=["GET"])
@require_auth
def get_form(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/forms/{formId}    Get a specific form by ID

    Headers:
    - X-Organization-Id: Organization ID (optional - platform admins can omit)

    Requires: User must have access to the form (public or group-assigned)
    """
    from shared.auth import has_form_access

    user = req.user
    form_id = req.route_params.get("formId")
    org_id = req.headers.get("X-Organization-Id")

    logger.info(f"User {user.email} retrieving form {form_id} (org: {org_id or 'none'})")

    try:
        # Check if user has access to this form
        if not has_form_access(user.user_id, form_id):
            logger.warning(f"User {user.email} denied access to form {form_id}")
            error = ErrorResponse(
                error="Forbidden",
                message="You don't have permission to access this form"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        # Try to get form from org partition (if provided), then GLOBAL
        forms_service = TableStorageService("Forms")
        form_entity = None

        if org_id:
            form_entity = forms_service.get_entity(org_id, form_id)

        if not form_entity:
            # Try GLOBAL partition
            form_entity = forms_service.get_entity("GLOBAL", form_id)

        if not form_entity:
            logger.warning(f"Form {form_id} not found")
            error = ErrorResponse(
                error="NotFound",
                message="Form not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Check if form is active
        if not form_entity.get("IsActive", True):
            logger.warning(f"Form {form_id} is not active")
            error = ErrorResponse(
                error="NotFound",
                message="Form not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Parse formSchema from JSON string
        form_schema = json.loads(form_entity["FormSchema"]) if isinstance(form_entity["FormSchema"], str) else form_entity["FormSchema"]

        # Convert to response model
        form = Form(
            id=form_entity["RowKey"],
            orgId=form_entity["PartitionKey"],
            name=form_entity["Name"],
            description=form_entity.get("Description"),
            linkedWorkflow=form_entity["LinkedWorkflow"],
            formSchema=form_schema,
            isActive=form_entity.get("IsActive", True),
            isGlobal=form_entity["PartitionKey"] == "GLOBAL",
            isPublic=form_entity.get("IsPublic", False),
            createdBy=form_entity["CreatedBy"],
            createdAt=form_entity["CreatedAt"],
            updatedAt=form_entity["UpdatedAt"]
        )

        logger.info(f"Returning form {form_id}")

        return func.HttpResponse(
            json.dumps(form.model_dump(mode="json")),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error retrieving form: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to retrieve form"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("forms_update_form")
@bp.route(route="forms/{formId}", methods=["PUT"])
@require_auth
def update_form(req: func.HttpRequest) -> func.HttpResponse:
    """
    PUT /api/forms/{formId}    Update a form

    Headers:
    - X-Organization-Id: Organization ID (required)

    Requires: User must be PlatformAdmin
    """
    user = req.user
    form_id = req.route_params.get("formId")
    org_id = req.headers.get("X-Organization-Id")

    logger.info(f"User {user.email} updating form {form_id}")

    try:
        # Validate query parameter
        if not org_id:
            error = ErrorResponse(
                error="BadRequest",
                message="X-Organization-Id header is required"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # Only platform admins can update forms
        if not is_platform_admin(user.user_id):
            logger.warning(f"User {user.email} is not a platform admin - denied form update")
            error = ErrorResponse(
                error="Forbidden",
                message="Only platform administrators can update forms"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        # Parse and validate request body
        request_body = req.get_json()
        update_request = UpdateFormRequest(**request_body)

        # Get existing form
        forms_service = TableStorageService("Forms")
        form_entity = forms_service.get_entity(org_id, form_id)

        if not form_entity:
            # Try GLOBAL partition
            form_entity = forms_service.get_entity("GLOBAL", form_id)

        if not form_entity:
            logger.warning(f"Form {form_id} not found")
            error = ErrorResponse(
                error="NotFound",
                message="Form not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Check if form is active
        if not form_entity.get("IsActive", True):
            logger.warning(f"Form {form_id} is not active")
            error = ErrorResponse(
                error="NotFound",
                message="Form not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Cannot update GLOBAL forms from org context
        if form_entity["PartitionKey"] == "GLOBAL":
            logger.warning(f"User {user.email} attempted to update global form {form_id}")
            error = ErrorResponse(
                error="Forbidden",
                message="Cannot update global forms"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        # Update entity fields
        now = datetime.utcnow()

        if update_request.name is not None:
            form_entity["Name"] = update_request.name
        if update_request.description is not None:
            form_entity["Description"] = update_request.description
        if update_request.linkedWorkflow is not None:
            form_entity["LinkedWorkflow"] = update_request.linkedWorkflow
        if update_request.formSchema is not None:
            form_entity["FormSchema"] = json.dumps(update_request.formSchema.model_dump())

        form_entity["UpdatedAt"] = now.isoformat()

        # Update entity
        forms_service.upsert_entity(form_entity)

        logger.info(f"Updated form {form_id}")

        # Parse formSchema for response
        form_schema = json.loads(form_entity["FormSchema"]) if isinstance(form_entity["FormSchema"], str) else form_entity["FormSchema"]

        # Create response model
        form_response = Form(
            id=form_entity["RowKey"],
            orgId=form_entity["PartitionKey"],
            name=form_entity["Name"],
            description=form_entity.get("Description"),
            linkedWorkflow=form_entity["LinkedWorkflow"],
            formSchema=form_schema,
            isActive=form_entity.get("IsActive", True),
            isGlobal=form_entity["PartitionKey"] == "GLOBAL",
            isPublic=form_entity.get("IsPublic", False),
            createdBy=form_entity["CreatedBy"],
            createdAt=form_entity["CreatedAt"],
            updatedAt=now
        )

        return func.HttpResponse(
            json.dumps(form_response.model_dump(mode="json")),
            status_code=200,
            mimetype="application/json"
        )

    except ValidationError as e:
        logger.warning(f"Validation error updating form: {e}")
        # Convert validation errors to JSON-serializable format
        errors = []
        for err in e.errors():
            error_dict = {"loc": err["loc"], "type": err["type"], "msg": str(err["msg"])}
            if "input" in err:
                error_dict["input"] = str(err["input"])
            errors.append(error_dict)

        error = ErrorResponse(
            error="ValidationError",
            message="Invalid request data",
            details={"errors": errors}
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
        logger.error(f"Error updating form: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to update form"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("forms_delete_form")
@bp.route(route="forms/{formId}", methods=["DELETE"])
@require_auth
def delete_form(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/forms/{formId}    Soft delete a form (set IsActive=False)

    Headers:
    - X-Organization-Id: Organization ID (required)

    Requires: User must be PlatformAdmin
    """
    user = req.user
    form_id = req.route_params.get("formId")
    org_id = req.headers.get("X-Organization-Id")

    logger.info(f"User {user.email} deleting form {form_id}")

    try:
        # Validate query parameter
        if not org_id:
            error = ErrorResponse(
                error="BadRequest",
                message="X-Organization-Id header is required"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # Only platform admins can delete forms
        if not is_platform_admin(user.user_id):
            logger.warning(f"User {user.email} is not a platform admin - denied form deletion")
            error = ErrorResponse(
                error="Forbidden",
                message="Only platform administrators can delete forms"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        # Get existing form
        forms_service = TableStorageService("Forms")
        form_entity = forms_service.get_entity(org_id, form_id)

        if not form_entity:
            # Try GLOBAL partition (but can't delete global forms)
            form_entity = forms_service.get_entity("GLOBAL", form_id)
            if form_entity:
                logger.warning(f"User {user.email} attempted to delete global form {form_id}")
                error = ErrorResponse(
                    error="Forbidden",
                    message="Cannot delete global forms"
                )
                return func.HttpResponse(
                    json.dumps(error.model_dump()),
                    status_code=403,
                    mimetype="application/json"
                )

        if not form_entity:
            # Idempotent - return 204 even if not found
            logger.debug(f"Form {form_id} not found, returning 204")
            return func.HttpResponse(status_code=204)

        # Soft delete by setting IsActive=False
        form_entity["IsActive"] = False
        form_entity["UpdatedAt"] = datetime.utcnow().isoformat()
        forms_service.upsert_entity(form_entity)

        logger.info(f"Soft deleted form {form_id}")

        return func.HttpResponse(status_code=204)  # No Content

    except Exception as e:
        logger.error(f"Error deleting form: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to delete form"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("forms_submit_form")
@bp.route(route="forms/{formId}/submit", methods=["POST"])
@require_auth
def submit_form(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/forms/{formId}/submit    Submit a form and execute the linked workflow

    Headers:
    - X-Organization-Id: Organization ID (optional for platform admins)

    Request Body:
    {
        "form_data": {
            "field1": "value1",
            "field2": "value2"
        }
    }

    Returns workflow execution result

    Requires: User must have access to the form (public or group-assigned)
    """
    import requests
    from shared.auth import has_form_access
    from functions.workflows import get_workflows_engine_config

    user = req.user
    form_id = req.route_params.get("formId")
    org_id = req.headers.get("X-Organization-Id")

    logger.info(f"User {user.email} submitting form {form_id} (org: {org_id or 'none'})")

    try:

        # Check if user has access to this form
        if not has_form_access(user.user_id, form_id):
            logger.warning(f"User {user.email} denied access to form {form_id}")
            error = ErrorResponse(
                error="Forbidden",
                message="You don't have permission to execute this form"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        # Get form - try org partition (if provided), then GLOBAL
        forms_service = TableStorageService("Forms")
        form_entity = None

        if org_id:
            form_entity = forms_service.get_entity(org_id, form_id)

        if not form_entity:
            # Try GLOBAL partition
            form_entity = forms_service.get_entity("GLOBAL", form_id)

        if not form_entity:
            logger.warning(f"Form {form_id} not found")
            error = ErrorResponse(
                error="NotFound",
                message="Form not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Check if form is active
        if not form_entity.get("IsActive", True):
            logger.warning(f"Form {form_id} is not active")
            error = ErrorResponse(
                error="NotFound",
                message="Form not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Get linked workflow
        linked_workflow = form_entity.get("LinkedWorkflow")
        if not linked_workflow:
            logger.error(f"Form {form_id} has no linked workflow")
            error = ErrorResponse(
                error="InternalServerError",
                message="Form configuration error: No linked workflow"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=500,
                mimetype="application/json"
            )

        # Parse request body
        request_body = req.get_json()
        form_data = request_body.get("form_data", {})

        logger.info(f"Executing workflow {linked_workflow} with form data: {form_data}")

        # Get workflows engine config
        workflow_engine_url, function_key = get_workflows_engine_config()

        # Use flat JSON format (parameters at root level, metadata prefixed with _)
        workflow_payload = {
            **form_data,
            "_formId": form_id
        }

        headers = {
            "Content-Type": "application/json",
            "X-User-Id": user.user_id
        }

        # Only add org header if present
        if org_id:
            headers["X-Organization-Id"] = org_id

        # Execute workflow - only add code parameter if function key is configured (not needed locally)
        workflow_url = f"{workflow_engine_url}/api/workflows/{linked_workflow}"
        if function_key:
            workflow_url += f"?code={function_key}"
            logger.info(f"Executing workflow via form with function key")
        else:
            logger.info(f"Executing workflow via form without function key (local mode)")

        response = requests.post(workflow_url, json=workflow_payload, headers=headers, timeout=60)

        if response.status_code != 200:
            logger.error(f"Workflow execution failed: {response.status_code} - {response.text}")
            error = ErrorResponse(
                error="WorkflowExecutionFailed",
                message=f"Failed to execute workflow: {response.text}"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=500,
                mimetype="application/json"
            )

        # Return workflow execution result
        execution_result = response.json()
        logger.info(f"Workflow execution completed: {execution_result.get('executionId')}")

        return func.HttpResponse(
            json.dumps(execution_result),
            status_code=200,
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
        logger.error(f"Error submitting form: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to submit form"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )
