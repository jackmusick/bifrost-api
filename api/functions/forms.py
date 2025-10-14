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

from shared.decorators import with_request_context, require_platform_admin
from shared.authorization import (
    can_user_view_form,
    can_user_execute_form,
    get_user_visible_forms
)
from shared.storage import get_table_service
from shared.models import (
    Form,
    CreateFormRequest,
    UpdateFormRequest,
    ErrorResponse,
    generate_entity_id
)
from pydantic import ValidationError

logger = logging.getLogger(__name__)

# Create blueprint for forms endpoints
bp = func.Blueprint()


@bp.function_name("forms_list_forms")
@bp.route(route="forms", methods=["GET"])
@with_request_context
async def list_forms(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/forms
    List all forms visible to the user

    Returns:
    - Platform admins: All forms in their org scope (or all if no org)
    - Regular users: Only forms they can access (public forms + forms assigned to their roles)
    """
    context = req.context
    logger.info(f"User {context.user_id} listing forms (org: {context.org_id or 'GLOBAL'})")

    try:
        # Use authorization helper to get visible forms
        form_entities = get_user_visible_forms(context)

        # Convert to response models
        forms = []
        for entity in form_entities:
            # Extract form UUID from RowKey "form:uuid"
            form_id = entity["RowKey"].split(":", 1)[1]

            # Parse formSchema from JSON string
            form_schema = json.loads(entity["FormSchema"]) if isinstance(entity["FormSchema"], str) else entity["FormSchema"]

            form = Form(
                id=form_id,
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

        logger.info(f"Returning {len(forms)} forms for user {context.user_id}")

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
@with_request_context
@require_platform_admin
async def create_form(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/forms
    Create a new form

    Platform admin only endpoint
    """
    context = req.context
    logger.info(f"User {context.user_id} creating form for org {context.org_id or 'GLOBAL'}")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        create_request = CreateFormRequest(**request_body)

        # Generate form UUID
        form_id = generate_entity_id()
        now = datetime.utcnow()

        # Determine partition key based on isGlobal flag
        # If isGlobal is True, store in GLOBAL partition
        # Otherwise, store in org's partition (from context.scope)
        partition_key = "GLOBAL" if create_request.isGlobal else context.scope

        # Create form entity for Entities table
        form_entity = {
            "PartitionKey": partition_key,
            "RowKey": f"form:{form_id}",
            "Name": create_request.name,
            "Description": create_request.description,
            "LinkedWorkflow": create_request.linkedWorkflow,
            "FormSchema": json.dumps(create_request.formSchema.model_dump()),
            "IsActive": True,
            "IsPublic": create_request.isPublic,
            "CreatedBy": context.user_id,
            "CreatedAt": now.isoformat(),
            "UpdatedAt": now.isoformat()
        }

        # Insert entity into Entities table
        entities_service = get_table_service("Entities", context)
        entities_service.insert_entity(form_entity)

        logger.info(f"Created form {form_id} in partition {partition_key}")

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
            createdBy=context.user_id,
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
@with_request_context
async def get_form(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/forms/{formId}
    Get a specific form by ID

    Requires: User must have access to the form (public or role-assigned)
    """
    context = req.context
    form_id = req.route_params.get("formId")

    logger.info(f"User {context.user_id} retrieving form {form_id}")

    try:
        # Check if user has access to this form
        if not can_user_view_form(context, form_id):
            logger.warning(f"User {context.user_id} denied access to form {form_id}")
            error = ErrorResponse(
                error="Forbidden",
                message="You don't have permission to access this form"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        # Get form from Entities table
        # Try context.scope first, then GLOBAL
        entities_service = get_table_service("Entities", context)
        form_entity = None

        # Try to get from context scope
        form_entity = entities_service.get_entity(context.scope, f"form:{form_id}")

        if not form_entity and context.scope != "GLOBAL":
            # Try GLOBAL partition
            form_entity = entities_service.get_entity("GLOBAL", f"form:{form_id}")

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
            id=form_id,
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
@with_request_context
@require_platform_admin
async def update_form(req: func.HttpRequest) -> func.HttpResponse:
    """
    PUT /api/forms/{formId}
    Update a form

    Platform admin only endpoint
    """
    context = req.context
    form_id = req.route_params.get("formId")

    logger.info(f"User {context.user_id} updating form {form_id}")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        update_request = UpdateFormRequest(**request_body)

        # Get existing form from Entities table
        entities_service = get_table_service("Entities", context)

        # Try context scope first, then GLOBAL
        form_entity = entities_service.get_entity(context.scope, f"form:{form_id}")

        if not form_entity and context.scope != "GLOBAL":
            # Try GLOBAL partition
            form_entity = entities_service.get_entity("GLOBAL", f"form:{form_id}")

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
        entities_service.update_entity(form_entity)

        logger.info(f"Updated form {form_id}")

        # Parse formSchema for response
        form_schema = json.loads(form_entity["FormSchema"]) if isinstance(form_entity["FormSchema"], str) else form_entity["FormSchema"]

        # Create response model
        form_response = Form(
            id=form_id,
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
@with_request_context
@require_platform_admin
async def delete_form(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/forms/{formId}
    Soft delete a form (set IsActive=False)

    Platform admin only endpoint
    """
    context = req.context
    form_id = req.route_params.get("formId")

    logger.info(f"User {context.user_id} deleting form {form_id}")

    try:
        # Get existing form from Entities table
        entities_service = get_table_service("Entities", context)

        # Try context scope first, then GLOBAL
        form_entity = entities_service.get_entity(context.scope, f"form:{form_id}")

        if not form_entity and context.scope != "GLOBAL":
            # Try GLOBAL partition
            form_entity = entities_service.get_entity("GLOBAL", f"form:{form_id}")

        if not form_entity:
            # Idempotent - return 204 even if not found
            logger.debug(f"Form {form_id} not found, returning 204")
            return func.HttpResponse(status_code=204)

        # Soft delete by setting IsActive=False
        form_entity["IsActive"] = False
        form_entity["UpdatedAt"] = datetime.utcnow().isoformat()
        entities_service.update_entity(form_entity)

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
@with_request_context
async def submit_form(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/forms/{formId}/submit
    Submit a form and execute the linked workflow

    Request Body:
    {
        "form_data": {
            "field1": "value1",
            "field2": "value2"
        }
    }

    Returns workflow execution result

    Requires: User must have access to execute the form (public or role-assigned)
    """
    import requests
    from functions.workflows import get_workflows_engine_config

    context = req.context
    form_id = req.route_params.get("formId")

    logger.info(f"User {context.user_id} submitting form {form_id}")

    try:
        # Check if user has permission to execute this form
        if not can_user_execute_form(context, form_id):
            logger.warning(f"User {context.user_id} denied access to execute form {form_id}")
            error = ErrorResponse(
                error="Forbidden",
                message="You don't have permission to execute this form"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        # Get form from Entities table
        entities_service = get_table_service("Entities", context)

        # Try context scope first, then GLOBAL
        form_entity = entities_service.get_entity(context.scope, f"form:{form_id}")

        if not form_entity and context.scope != "GLOBAL":
            # Try GLOBAL partition
            form_entity = entities_service.get_entity("GLOBAL", f"form:{form_id}")

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
            "X-User-Id": context.user_id
        }

        # Add org header if present
        if context.org_id:
            headers["X-Organization-Id"] = context.org_id

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
