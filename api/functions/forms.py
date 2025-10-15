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
from shared.openapi_decorators import openapi_endpoint
from shared.middleware import with_org_context
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
    FormExecuteRequest,
    ErrorResponse,
    generate_entity_id
)
from pydantic import ValidationError

logger = logging.getLogger(__name__)

# Create blueprint for forms endpoints
bp = func.Blueprint()


@bp.function_name("forms_list_forms")
@bp.route(route="forms", methods=["GET"])
@openapi_endpoint(
    path="/forms",
    method="GET",
    summary="List forms",
    description="List all forms visible to the user. Platform admins see all forms in their org scope. Regular users see only forms they can access (public forms + forms assigned to their roles).",
    tags=["Forms"],
    response_model=Form
)
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
@openapi_endpoint(
    path="/forms",
    method="POST",
    summary="Create a new form",
    description="Create a new form (Platform admin only)",
    tags=["Forms"],
    request_model=CreateFormRequest,
    response_model=Form
)
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
@openapi_endpoint(
    path="/forms/{formId}",
    method="GET",
    summary="Get form by ID",
    description="Get a specific form by ID. User must have access to the form (public or role-assigned).",
    tags=["Forms"],
    response_model=Form,
    path_params={
        "formId": {
            "description": "Form ID (UUID)",
            "schema": {"type": "string", "format": "uuid"}
        }
    }
)
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
@openapi_endpoint(
    path="/forms/{formId}",
    method="PUT",
    summary="Update a form",
    description="Update an existing form (Platform admin only)",
    tags=["Forms"],
    request_model=UpdateFormRequest,
    response_model=Form,
    path_params={
        "formId": {
            "description": "Form ID (UUID)",
            "schema": {"type": "string", "format": "uuid"}
        }
    }
)
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
@openapi_endpoint(
    path="/forms/{formId}",
    method="DELETE",
    summary="Delete a form",
    description="Soft delete a form by setting IsActive=False (Platform admin only)",
    tags=["Forms"],
    path_params={
        "formId": {
            "description": "Form ID (UUID)",
            "schema": {"type": "string", "format": "uuid"}
        }
    }
)
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


@bp.function_name("forms_execute_form")
@bp.route(route="forms/{formId}/execute", methods=["POST"])
@openapi_endpoint(
    path="/forms/{formId}/execute",
    method="POST",
    summary="Execute a form",
    description="Execute a form and run the linked workflow. User must have access to execute the form (public or role-assigned).",
    tags=["Forms"],
    request_model=FormExecuteRequest,
    path_params={
        "formId": {
            "description": "Form ID (UUID)",
            "schema": {"type": "string", "format": "uuid"}
        }
    }
)
@with_request_context  # For authorization - sets req.context
@with_org_context      # For workflow execution - sets req.org_context
async def execute_form(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/forms/{formId}/execute
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
    from shared.registry import get_registry
    from shared.execution_logger import get_execution_logger
    from shared.models import ExecutionStatus
    import uuid

    # Both decorators are applied:
    # - req.context = RequestContext (for authorization)
    # - req.org_context = OrganizationContext (for workflow execution)
    request_context = req.context
    workflow_context = req.org_context
    form_id = req.route_params.get("formId")

    logger.info(f"User {request_context.user_id} submitting form {form_id}")

    try:
        # Check if user has permission to execute this form
        if not can_user_execute_form(request_context, form_id):
            logger.warning(f"User {request_context.user_id} denied access to execute form {form_id}")
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
        entities_service = get_table_service("Entities", request_context)

        # Try context scope first, then GLOBAL
        form_entity = entities_service.get_entity(request_context.scope, f"form:{form_id}")

        if not form_entity and request_context.scope != "GLOBAL":
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

        # Hot-reload: Re-discover workspace modules before execution
        # This allows adding/modifying workflows without restarting
        from function_app import discover_workspace_modules
        discover_workspace_modules()

        # Get workflow from registry
        registry = get_registry()
        workflow_metadata = registry.get_workflow(linked_workflow)

        if not workflow_metadata:
            logger.error(f"Workflow '{linked_workflow}' not found in registry")
            error = ErrorResponse(
                error="NotFound",
                message=f"Workflow '{linked_workflow}' not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Get workflow function
        workflow_func = workflow_metadata.function

        # Use execution_id from OrganizationContext (already set by @with_org_context)
        execution_id = workflow_context.execution_id

        exec_logger = get_execution_logger()
        start_time = datetime.utcnow()

        # Create execution record (status=RUNNING)
        await exec_logger.create_execution(
            execution_id=execution_id,
            org_id=request_context.org_id,
            user_id=request_context.user_id,
            workflow_name=linked_workflow,
            input_data=form_data,
            form_id=form_id
        )

        logger.info(
            f"Starting workflow execution: {linked_workflow}",
            extra={
                "execution_id": execution_id,
                "org_id": request_context.org_id,
                "user_id": request_context.user_id,
                "workflow_name": linked_workflow
            }
        )

        # Separate workflow parameters from extra data
        defined_params = {param.name for param in workflow_metadata.parameters}
        workflow_params = {}
        extra_variables = {}

        for key, value in form_data.items():
            if key in defined_params:
                workflow_params[key] = value
            else:
                extra_variables[key] = value

        # Inject extra variables into workflow context
        for key, value in extra_variables.items():
            workflow_context.set_variable(key, value)

        # Execute workflow directly with OrganizationContext
        result = await workflow_func(workflow_context, **workflow_params)

        # Calculate duration
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Determine execution status
        execution_status = ExecutionStatus.SUCCESS
        error_message = None

        if isinstance(result, dict) and result.get('success') is False:
            execution_status = ExecutionStatus.COMPLETED_WITH_ERRORS
            error_message = result.get('error', 'Workflow completed with errors')

        # Update execution record
        await exec_logger.update_execution(
            execution_id=execution_id,
            org_id=request_context.org_id,
            user_id=request_context.user_id,
            status=execution_status,
            result=result,
            error_message=error_message,
            duration_ms=duration_ms,
            state_snapshots=workflow_context._state_snapshots,
            integration_calls=workflow_context._integration_calls,
            logs=workflow_context._logs,
            variables=workflow_context._variables
        )

        logger.info(f"Workflow execution completed: {execution_id}")

        # Build response matching WorkflowExecutionResponse format
        execution_result = {
            "executionId": execution_id,
            "status": execution_status.value,
            "result": result,
            "durationMs": duration_ms,
            "startedAt": start_time.isoformat(),
            "completedAt": end_time.isoformat()
        }

        return func.HttpResponse(
            json.dumps(execution_result, default=str),
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
