"""
Forms API endpoints
- CRUD operations for workflow forms
- Support for org-specific and global forms
"""

import json
import logging
from datetime import datetime

import azure.functions as func
from pydantic import ValidationError

from shared.authorization import can_user_execute_form, can_user_view_form, get_user_visible_forms
from shared.decorators import require_platform_admin, with_request_context
from shared.error_handling import WorkflowError
from shared.middleware import with_org_context
from shared.models import (
    CreateFormRequest,
    ErrorResponse,
    Form,
    FormExecuteRequest,
    FormStartupResponse,
    UpdateFormRequest,
)
from shared.openapi_decorators import openapi_endpoint
from shared.repositories.forms import FormRepository

logger = logging.getLogger(__name__)

# Create blueprint for forms endpoints
bp = func.Blueprint()


def validate_launch_workflow_params(
    launch_workflow_id: str | None,
    default_launch_params: dict[str, any] | None,
    allowed_query_params: list[str] | None,
    form_schema_fields: list
) -> str | None:
    """
    Validate that all required launch workflow parameters have either:
    - A form field with allowAsQueryParam enabled, OR
    - A default value in defaultLaunchParams

    Args:
        launch_workflow_id: Name of the launch workflow
        default_launch_params: Default parameters for the workflow
        allowed_query_params: List of allowed query parameter names
        form_schema_fields: List of form fields

    Returns:
        Error message if validation fails, None if valid
    """
    if not launch_workflow_id:
        # No launch workflow, nothing to validate
        return None

    # Get workflow metadata from registry
    from shared.registry import get_registry
    registry = get_registry()
    workflow_metadata = registry.get_workflow(launch_workflow_id)

    if not workflow_metadata:
        return f"Launch workflow '{launch_workflow_id}' not found in registry"

    # Check each required parameter
    default_params = default_launch_params or {}
    query_param_fields = allowed_query_params or []

    missing_params = []
    for param in workflow_metadata.parameters:
        if param.required:
            # Check if param has a default value or a query param field
            has_default = param.name in default_params
            has_query_field = param.name in query_param_fields

            if not has_default and not has_query_field:
                missing_params.append(param.name)

    if missing_params:
        return (
            f"Launch workflow '{launch_workflow_id}' requires parameters that have no default values or query parameter fields: "
            f"{', '.join(missing_params)}. Please either add default values in 'defaultLaunchParams' or enable 'allowAsQueryParam' "
            f"for form fields with these names."
        )

    return None


@bp.function_name("forms_list_forms")
@bp.route(route="forms", methods=["GET"])
@openapi_endpoint(
    path="/forms",
    method="GET",
    summary="List forms",
    description="List all forms visible to the user. Platform admins see all forms in their org scope. Regular users see only forms they can access (public forms + forms assigned to their roles).",
    tags=["Forms"],
    response_model=list[Form]
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
    context = req.context  # type: ignore[attr-defined]
    logger.info(f"User {context.user_id} listing forms (org: {context.org_id or 'GLOBAL'})")

    try:
        # Use authorization helper to get visible forms (returns Form model dicts)
        forms = get_user_visible_forms(context)

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
    context = req.context  # type: ignore[attr-defined]
    logger.info(f"User {context.user_id} creating form for org {context.org_id or 'GLOBAL'}")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        create_request = CreateFormRequest(**request_body)

        # Validate launch workflow parameters if launch workflow is configured
        validation_error = validate_launch_workflow_params(
            launch_workflow_id=create_request.launchWorkflowId,
            default_launch_params=create_request.defaultLaunchParams,
            allowed_query_params=create_request.allowedQueryParams,
            form_schema_fields=create_request.formSchema.fields
        )
        if validation_error:
            logger.warning(f"Launch workflow validation failed: {validation_error}")
            error = ErrorResponse(
                error="ValidationError",
                message=validation_error
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # Create form using repository
        form_repo = FormRepository(context)
        form = form_repo.create_form(
            form_request=create_request,
            created_by=context.user_id
        )

        logger.info(f"Created form {form.id} in partition {form.orgId}")

        return func.HttpResponse(
            json.dumps(form.model_dump(mode="json")),
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
    context = req.context  # type: ignore[attr-defined]
    form_id = req.route_params.get("formId")
    # Type narrowing for Pyright - formId comes from route so should always exist
    assert form_id is not None

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

        # Get form using repository (handles GLOBAL fallback)
        form_repo = FormRepository(context)
        form = form_repo.get_form(form_id)

        if not form:
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

        # Check if form is active (skip for platform admins who can manage inactive forms)
        if not context.is_platform_admin and not form.isActive:
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
    context = req.context  # type: ignore[attr-defined]
    form_id = req.route_params.get("formId")
    assert form_id is not None, "formId is required"

    logger.info(f"User {context.user_id} updating form {form_id}")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        update_request = UpdateFormRequest(**request_body)

        # Get existing form to validate against (for merging with update)
        form_repo = FormRepository(context)
        existing_form = form_repo.get_form(form_id)

        if not existing_form:
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

        # Merge update request with existing form for validation
        # Use updated values if provided, otherwise use existing values
        merged_launch_workflow = update_request.launchWorkflowId if update_request.launchWorkflowId is not None else existing_form.launchWorkflowId
        merged_default_params = update_request.defaultLaunchParams if update_request.defaultLaunchParams is not None else existing_form.defaultLaunchParams
        merged_query_params = update_request.allowedQueryParams if update_request.allowedQueryParams is not None else existing_form.allowedQueryParams
        merged_form_schema = update_request.formSchema if update_request.formSchema is not None else existing_form.formSchema

        # Validate launch workflow parameters with merged values
        validation_error = validate_launch_workflow_params(
            launch_workflow_id=merged_launch_workflow,
            default_launch_params=merged_default_params,
            allowed_query_params=merged_query_params,
            form_schema_fields=merged_form_schema.fields
        )
        if validation_error:
            logger.warning(f"Launch workflow validation failed: {validation_error}")
            error = ErrorResponse(
                error="ValidationError",
                message=validation_error
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # Update form using repository
        form = form_repo.update_form(form_id, update_request)

        if not form:
            logger.warning(f"Form {form_id} not found after update")
            error = ErrorResponse(
                error="NotFound",
                message="Form not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        logger.info(f"Updated form {form_id}")

        return func.HttpResponse(
            json.dumps(form.model_dump(mode="json")),
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
    context = req.context  # type: ignore[attr-defined]
    form_id = req.route_params.get("formId")

    assert form_id is not None, "formId is required"

    logger.info(f"User {context.user_id} deleting form {form_id}")

    try:
        # Soft delete form using repository
        form_repo = FormRepository(context)
        success = form_repo.delete_form(form_id)

        if success:
            logger.info(f"Soft deleted form {form_id}")
        else:
            # Idempotent - return 204 even if not found
            logger.debug(f"Form {form_id} not found, returning 204")

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


@bp.function_name("forms_startup")
@bp.route(route="forms/{formId}/startup", methods=["GET", "POST"])
@openapi_endpoint(
    path="/forms/{formId}/startup",
    method="POST",
    summary="Execute form's launch workflow",
    description="Execute the form's launch workflow to populate initial form context. Accepts parameters via query string (GET) or request body (POST). User must have access to view the form.",
    tags=["Forms"],
    request_model=FormExecuteRequest,  # Uses same request format as /execute
    response_model=FormStartupResponse,  # Returns workflow result
    path_params={
        "formId": {
            "description": "Form ID (UUID)",
            "schema": {"type": "string", "format": "uuid"}
        }
    }
)
@with_request_context
@with_org_context
async def execute_form_startup(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/forms/{formId}/startup
    Execute the form's launch workflow to get initial context data

    This endpoint:
    1. Checks if user has access to view the form (same as viewing the form)
    2. Executes the form's launchWorkflowId if configured
    3. Returns the workflow results to populate context.workflow

    Query Parameters:
    - Can include query params that match form's allowedQueryParams
    - These are passed to the launch workflow as parameters

    Returns workflow execution result

    Requires: User must have access to view the form (public or role-assigned)
    """
    from shared.registry import get_registry

    request_context = req.context  # type: ignore[attr-defined]
    workflow_context = req.org_context  # type: ignore[attr-defined]
    form_id = req.route_params.get("formId")
    assert form_id is not None

    logger.info(f"User {request_context.user_id} requesting startup workflow for form {form_id}")

    try:
        # Check if user has permission to VIEW this form (same check as GET /forms/{formId})
        if not can_user_view_form(request_context, form_id):
            logger.warning(f"User {request_context.user_id} denied access to form {form_id}")
            error = ErrorResponse(
                error="Forbidden",
                message="You don't have permission to access this form"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        # Get form using repository
        form_repo = FormRepository(request_context)
        form = form_repo.get_form(form_id)

        if not form:
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
        if not form.isActive:
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

        # Check if form has a launch workflow configured
        if not form.launchWorkflowId:
            logger.info(f"Form {form_id} has no launch workflow, returning empty result")
            return func.HttpResponse(
                json.dumps({"result": {}}),
                status_code=200,
                mimetype="application/json"
            )

        # Extract and merge parameters from multiple sources (priority: form_data > queryParams > defaultLaunchParams)
        # 1. Start with default launch params (lowest priority)
        input_data = dict(form.defaultLaunchParams or {})

        # 2. Add parameters from POST body (medium priority)
        if req.method == "POST":
            try:
                request_body = req.get_json()
                if request_body:
                    # Use 'form_data' to match FormExecuteRequest model
                    post_input = request_body.get('form_data', {})
                    input_data.update(post_input)  # Override defaults
            except ValueError:
                # No body or invalid JSON - that's okay for POST
                pass

        # 3. Add query parameters (highest priority - override everything)
        # Only accept query params that are in allowedQueryParams (for security)
        allowed_params = form.allowedQueryParams or []
        for param_name in allowed_params:
            param_value = req.params.get(param_name)
            if param_value is not None:
                input_data[param_name] = param_value  # Override defaults and POST body

        logger.info(f"Executing launch workflow {form.launchWorkflowId} with merged input data: {input_data}")

        # Hot-reload: Re-discover workspace modules
        from function_app import discover_workspace_modules
        discover_workspace_modules()

        # Get workflow from registry
        registry = get_registry()
        workflow_metadata = registry.get_workflow(form.launchWorkflowId)

        if not workflow_metadata:
            logger.error(f"Launch workflow '{form.launchWorkflowId}' not found in registry")
            error = ErrorResponse(
                error="NotFound",
                message=f"Launch workflow '{form.launchWorkflowId}' not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Get workflow function
        workflow_func = workflow_metadata.function

        # Separate workflow parameters from extra data
        defined_params = {param.name for param in workflow_metadata.parameters}
        workflow_params = {}
        extra_variables = {}

        for key, value in input_data.items():
            if key in defined_params:
                workflow_params[key] = value
            else:
                extra_variables[key] = value

        # Inject extra variables into workflow context
        for key, value in extra_variables.items():
            workflow_context.set_variable(key, value)

        # Execute workflow directly with OrganizationContext
        # Note: This is a GET request, so we don't create an execution record
        # Launch workflows are considered lightweight/read-only operations
        result = await workflow_func(workflow_context, **workflow_params)

        logger.info(f"Launch workflow {form.launchWorkflowId} completed successfully")

        # Return just the result (no execution metadata needed for startup)
        return func.HttpResponse(
            json.dumps({"result": result}, default=str),
            status_code=200,
            mimetype="application/json"
        )

    except TypeError as e:
        # Handle missing or invalid workflow parameters
        error_msg = str(e)
        logger.warning(f"Launch workflow parameter error: {error_msg}")

        # Check if it's a missing parameter error
        if "missing" in error_msg and "required positional argument" in error_msg:
            # Extract parameter name from error message
            # Example: "simple_greeting() missing 1 required positional argument: 'name'"
            param_name = error_msg.split("'")[-2] if "'" in error_msg else "unknown"
            user_message = f"Launch workflow requires parameter '{param_name}' but it was not provided. Check the form's allowed query parameters configuration."
        else:
            user_message = f"Invalid parameters for launch workflow: {error_msg}"

        # form is guaranteed to exist here (we've already checked and returned early if not)
        assert form is not None
        error = ErrorResponse(
            error="BadRequest",
            message=user_message,
            details={"workflow": form.launchWorkflowId, "error": error_msg}
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    except WorkflowError as e:
        # Handle known workflow errors
        # form is guaranteed to exist here (we've already checked and returned early if not)
        assert form is not None
        logger.error(f"Launch workflow failed: {form.launchWorkflowId} - {e.error_type}: {e.message}")
        error = ErrorResponse(
            error=e.error_type,
            message=e.message,
            details=e.details
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error executing form startup workflow: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message=f"An unexpected error occurred while executing the launch workflow: {str(e)}"
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

    from shared.execution_logger import get_execution_logger
    from shared.models import ExecutionStatus
    from shared.registry import get_registry

    # Both decorators are applied:
    # - req.context = RequestContext (for authorization)
    # - req.org_context = OrganizationContext (for workflow execution)
    request_context = req.context  # type: ignore[attr-defined]
    workflow_context = req.org_context  # type: ignore[attr-defined]
    form_id = req.route_params.get("formId")
    # Type narrowing for Pyright - formId comes from route so should always exist
    assert form_id is not None

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

        # Get form using repository
        form_repo = FormRepository(request_context)
        form = form_repo.get_form(form_id)

        if not form:
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
        if not form.isActive:
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
        linked_workflow = form.linkedWorkflow
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
            user_name=request_context.name,
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
