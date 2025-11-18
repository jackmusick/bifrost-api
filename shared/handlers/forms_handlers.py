"""
Form endpoint handlers - extracted business logic
Provides pure async handlers for form CRUD and execution operations
"""

import logging

import azure.functions as func
from pydantic import ValidationError

from shared.authorization import can_user_execute_form, can_user_view_form, get_user_visible_forms
from shared.error_handling import WorkflowError
from shared.models import (
    CreateFormRequest,
    ErrorResponse,
    UpdateFormRequest,
)
from shared.repositories.forms_file import FormsFileRepository
from shared.system_logger import get_system_logger

logger = logging.getLogger(__name__)


def validate_data_provider_inputs_for_form(form_schema_fields: list) -> list[str]:
    """
    Validate dataProviderInputs for all fields in a form (T028-T030).

    Args:
        form_schema_fields: List of FormField objects

    Returns:
        List of validation error messages (empty if valid)

    Validation rules:
        1. If field has dataProvider, check if provider exists in registry
        2. If provider has required parameters, validate that static inputs are provided
        3. dataProviderInputs validation is handled by Pydantic model validators
    """
    from shared.registry import get_registry
    errors = []

    registry = get_registry()

    for field in form_schema_fields:
        if not field.dataProvider:
            continue

        # Get provider metadata from registry
        provider_metadata = registry.get_data_provider(field.dataProvider)

        if not provider_metadata:
            errors.append(
                f"Field '{field.name}' references unknown data provider '{field.dataProvider}'"
            )
            continue

        # T029: Validate required parameters are provided (for static mode only)
        # Note: For fieldRef and expression modes, validation happens at runtime
        if provider_metadata.parameters:
            for param in provider_metadata.parameters:
                if param.required:
                    # Check if input is provided in dataProviderInputs
                    if not field.dataProviderInputs or param.name not in field.dataProviderInputs:
                        errors.append(
                            f"Field '{field.name}' uses data provider '{field.dataProvider}': "
                            f"required parameter '{param.name}' is missing from dataProviderInputs"
                        )

    return errors


def validate_launch_workflow_params(
    launch_workflow_id: str | None,
    default_launch_params: dict | None,
    allowed_query_params: list[str] | None,
    form_schema_fields: list
) -> str | None:
    """
    Validate that all required launch workflow parameters have either:
    - A form field with allowAsQueryParam enabled, OR
    - A default value in defaultLaunchParams
    """
    if not launch_workflow_id:
        return None

    from shared.registry import get_registry
    registry = get_registry()
    workflow_metadata = registry.get_workflow(launch_workflow_id)

    if not workflow_metadata:
        return f"Launch workflow '{launch_workflow_id}' not found in registry"

    default_params = default_launch_params or {}
    query_param_fields = allowed_query_params or []

    missing_params = []
    for param in workflow_metadata.parameters:
        if param.required:
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


async def list_forms_handler(context, request_context) -> tuple:
    """List all forms visible to the user"""
    logger.info(f"User {request_context.user_id} listing forms (org: {request_context.org_id or 'GLOBAL'})")

    try:
        from shared.registry import get_registry

        forms = await get_user_visible_forms(request_context)
        registry = get_registry()

        # Enrich forms with validation info (missing required params)
        for form in forms:
            linked_workflow = form.get("linkedWorkflow")
            logger.info(f"Validating form '{form.get('name')}' linked to workflow '{linked_workflow}'")

            if not linked_workflow:
                form["missingRequiredParams"] = []
                logger.info(f"Form '{form.get('name')}' has no linked workflow - marking as valid")
                continue

            # Get workflow metadata
            workflow_metadata = registry.get_workflow(linked_workflow)
            logger.info(f"Found workflow metadata: {workflow_metadata is not None}")

            if not workflow_metadata or not workflow_metadata.parameters:
                form["missingRequiredParams"] = []
                logger.info(f"Workflow '{linked_workflow}' not found or has no parameters - marking as valid")
                continue

            # Get required parameter names
            required_params = [
                p.name for p in workflow_metadata.parameters if p.required
            ]

            # Get form field names
            field_names = set(
                field.get("name")
                for field in form.get("formSchema", {}).get("fields", [])
                if field.get("name")
            )

            logger.info(f"Required params: {required_params}, Form fields: {field_names}")

            # Find missing required parameters
            missing = [p for p in required_params if p not in field_names]
            form["missingRequiredParams"] = missing

            logger.info(
                f"Form '{form.get('name')}' validation: missing={missing}, valid={len(missing) == 0}"
            )

        forms.sort(key=lambda f: f["name"])
        logger.info(f"Returning {len(forms)} forms for user {request_context.user_id}")
        return forms, 200
    except Exception as e:
        logger.error(f"Error listing forms: {str(e)}", exc_info=True)
        error = ErrorResponse(error="InternalServerError", message="Failed to list forms")
        return error.model_dump(), 500


async def create_form_handler(request_body: dict, request_context) -> tuple[dict, int]:
    """Create a new form (Platform admin only)"""
    logger.info(f"User {request_context.user_id} creating form for org {request_context.org_id or 'GLOBAL'}")

    try:
        create_request = CreateFormRequest(**request_body)

        validation_error = validate_launch_workflow_params(
            launch_workflow_id=create_request.launchWorkflowId,
            default_launch_params=create_request.defaultLaunchParams,
            allowed_query_params=create_request.allowedQueryParams,
            form_schema_fields=create_request.formSchema.fields
        )
        if validation_error:
            logger.warning(f"Launch workflow validation failed: {validation_error}")
            error = ErrorResponse(error="ValidationError", message=validation_error)
            return error.model_dump(), 400

        # T028-T030: Validate dataProviderInputs for all form fields
        data_provider_errors = validate_data_provider_inputs_for_form(create_request.formSchema.fields)
        if data_provider_errors:
            logger.warning(f"Data provider validation failed: {data_provider_errors}")
            error = ErrorResponse(
                error="ValidationError",
                message="Data provider configuration validation failed",
                details={"errors": data_provider_errors}
            )
            return error.model_dump(), 400

        form_repo = FormsFileRepository(request_context)
        form = await form_repo.create_form(form_request=create_request, created_by=request_context.user_id)
        logger.info(f"Created form {form.id} in partition {form.orgId}")

        # Log to system logger
        system_logger = get_system_logger()
        await system_logger.log_form_event(
            action="create",
            form_id=form.id,
            form_name=form.name,
            scope=form.orgId or "GLOBAL",
            executed_by=request_context.user_id,
            executed_by_name=request_context.name or request_context.user_id
        )

        return form.model_dump(mode="json"), 201

    except ValidationError as e:
        logger.warning(f"Validation error creating form: {e}")
        errors = []
        for err in e.errors():
            error_dict = {"loc": err["loc"], "type": err["type"], "msg": str(err["msg"])}
            if "input" in err:
                error_dict["input"] = str(err["input"])
            errors.append(error_dict)
        error = ErrorResponse(error="ValidationError", message="Invalid request data", details={"errors": errors})
        return error.model_dump(), 400

    except ValueError as e:
        logger.error(f"Error parsing request: {str(e)}")
        error = ErrorResponse(error="BadRequest", message="Invalid JSON in request body")
        return error.model_dump(), 400

    except Exception as e:
        logger.error(f"Error creating form: {str(e)}", exc_info=True)

        # Log error to system logger
        system_logger = get_system_logger()
        await system_logger.log(
            category="form",
            level="error",
            message=f"Failed to create form: {str(e)}",
            executed_by=request_context.user_id,
            executed_by_name=request_context.name or request_context.user_id,
            details={"error": str(e), "error_type": type(e).__name__}
        )

        error = ErrorResponse(error="InternalServerError", message="Failed to create form")
        return error.model_dump(), 500


async def get_form_handler(form_id: str, request_context) -> tuple[dict, int]:
    """Get a specific form by ID"""
    logger.info(f"User {request_context.user_id} retrieving form {form_id}")

    try:
        form_repo = FormsFileRepository(request_context)
        form = await form_repo.get_form(form_id)

        if not form:
            logger.warning(f"Form {form_id} not found")
            error = ErrorResponse(error="NotFound", message="Form not found")
            return error.model_dump(), 404

        # Check authorization (handles admin vs regular user permissions)
        if not can_user_view_form(request_context, form_id):
            logger.warning(f"User {request_context.user_id} denied access to form {form_id}")
            error = ErrorResponse(error="Forbidden", message="You don't have permission to access this form")
            return error.model_dump(), 403

        logger.info(f"Returning form {form_id}")
        return form.model_dump(mode="json"), 200

    except Exception as e:
        logger.error(f"Error retrieving form: {str(e)}", exc_info=True)
        error = ErrorResponse(error="InternalServerError", message="Failed to retrieve form")
        return error.model_dump(), 500


async def update_form_handler(form_id: str, request_body: dict, request_context) -> tuple[dict, int]:
    """Update an existing form (Platform admin only)"""
    logger.info(f"User {request_context.user_id} updating form {form_id}")

    try:
        update_request = UpdateFormRequest(**request_body)
        form_repo = FormsFileRepository(request_context)
        existing_form = await form_repo.get_form(form_id)

        if not existing_form:
            logger.warning(f"Form {form_id} not found")
            error = ErrorResponse(error="NotFound", message="Form not found")
            return error.model_dump(), 404

        merged_launch_workflow = update_request.launchWorkflowId if update_request.launchWorkflowId is not None else existing_form.launchWorkflowId
        merged_default_params = update_request.defaultLaunchParams if update_request.defaultLaunchParams is not None else existing_form.defaultLaunchParams
        merged_query_params = update_request.allowedQueryParams if update_request.allowedQueryParams is not None else existing_form.allowedQueryParams
        merged_form_schema = update_request.formSchema if update_request.formSchema is not None else existing_form.formSchema

        validation_error = validate_launch_workflow_params(
            launch_workflow_id=merged_launch_workflow,
            default_launch_params=merged_default_params,
            allowed_query_params=merged_query_params,
            form_schema_fields=merged_form_schema.fields
        )
        if validation_error:
            logger.warning(f"Launch workflow validation failed: {validation_error}")
            error = ErrorResponse(error="ValidationError", message=validation_error)
            return error.model_dump(), 400

        # T028-T030: Validate dataProviderInputs for all form fields
        data_provider_errors = validate_data_provider_inputs_for_form(merged_form_schema.fields)
        if data_provider_errors:
            logger.warning(f"Data provider validation failed: {data_provider_errors}")
            error = ErrorResponse(
                error="ValidationError",
                message="Data provider configuration validation failed",
                details={"errors": data_provider_errors}
            )
            return error.model_dump(), 400

        form = await form_repo.update_form(form_id, update_request)

        if not form:
            logger.warning(f"Form {form_id} not found after update")
            error = ErrorResponse(error="NotFound", message="Form not found")
            return error.model_dump(), 404

        logger.info(f"Updated form {form_id}")

        # Log to system logger
        system_logger = get_system_logger()
        await system_logger.log_form_event(
            action="update",
            form_id=form.id,
            form_name=form.name,
            scope=form.orgId or "GLOBAL",
            executed_by=request_context.user_id,
            executed_by_name=request_context.name or request_context.user_id
        )

        return form.model_dump(mode="json"), 200

    except ValidationError as e:
        logger.warning(f"Validation error updating form: {e}")
        errors = []
        for err in e.errors():
            error_dict = {"loc": err["loc"], "type": err["type"], "msg": str(err["msg"])}
            if "input" in err:
                error_dict["input"] = str(err["input"])
            errors.append(error_dict)
        error = ErrorResponse(error="ValidationError", message="Invalid request data", details={"errors": errors})
        return error.model_dump(), 400

    except ValueError as e:
        logger.error(f"Error parsing request: {str(e)}")
        error = ErrorResponse(error="BadRequest", message="Invalid JSON in request body")
        return error.model_dump(), 400

    except Exception as e:
        logger.error(f"Error updating form: {str(e)}", exc_info=True)

        # Log error to system logger
        system_logger = get_system_logger()
        await system_logger.log(
            category="form",
            level="error",
            message=f"Failed to update form {form_id}: {str(e)}",
            executed_by=request_context.user_id,
            executed_by_name=request_context.name or request_context.user_id,
            details={"form_id": form_id, "error": str(e), "error_type": type(e).__name__}
        )

        error = ErrorResponse(error="InternalServerError", message="Failed to update form")
        return error.model_dump(), 500


async def delete_form_handler(form_id: str, request_context) -> tuple[dict | None, int]:
    """Soft delete a form (set IsActive=False)"""
    logger.info(f"User {request_context.user_id} deleting form {form_id}")

    try:
        form_repo = FormsFileRepository(request_context)

        # Get form details before deletion for logging
        form = await form_repo.get_form(form_id)

        success = await form_repo.delete_form(form_id)

        if success and form:
            logger.info(f"Soft deleted form {form_id}")

            # Log to system logger
            system_logger = get_system_logger()
            await system_logger.log_form_event(
                action="delete",
                form_id=form.id,
                form_name=form.name,
                scope=form.orgId or "GLOBAL",
                executed_by=request_context.user_id,
                executed_by_name=request_context.name or request_context.user_id
            )
        else:
            logger.debug(f"Form {form_id} not found, returning 204")

        return None, 204

    except Exception as e:
        logger.error(f"Error deleting form: {str(e)}", exc_info=True)

        # Log error to system logger
        system_logger = get_system_logger()
        await system_logger.log(
            category="form",
            level="error",
            message=f"Failed to delete form {form_id}: {str(e)}",
            executed_by=request_context.user_id,
            executed_by_name=request_context.name or request_context.user_id,
            details={"form_id": form_id, "error": str(e), "error_type": type(e).__name__}
        )

        error = ErrorResponse(error="InternalServerError", message="Failed to delete form")
        return error.model_dump(), 500


async def execute_form_startup_handler(form_id: str, req: func.HttpRequest, request_context, workflow_context) -> tuple[dict, int]:
    """Execute the form's launch workflow to get initial context data"""
    from shared.registry import get_registry

    logger.info(f"User {request_context.user_id} requesting startup workflow for form {form_id}")

    try:
        if not can_user_view_form(request_context, form_id):
            logger.warning(f"User {request_context.user_id} denied access to form {form_id}")
            error = ErrorResponse(error="Forbidden", message="You don't have permission to access this form")
            return error.model_dump(), 403

        form_repo = FormsFileRepository(request_context)
        form = await form_repo.get_form(form_id)

        if not form:
            logger.warning(f"Form {form_id} not found")
            error = ErrorResponse(error="NotFound", message="Form not found")
            return error.model_dump(), 404

        # Regular users cannot execute inactive forms; admins can (for testing/development)
        if not form.isActive and not request_context.is_platform_admin:
            logger.warning(f"Form {form_id} is not active and user is not an admin")
            error = ErrorResponse(error="NotFound", message="Form not found")
            return error.model_dump(), 404

        if not form.launchWorkflowId:
            logger.info(f"Form {form_id} has no launch workflow, returning empty result")
            return {"result": {}}, 200

        input_data = dict(form.defaultLaunchParams or {})

        if req.method == "POST":
            try:
                request_body = req.get_json()
                if request_body:
                    post_input = request_body.get('form_data', {})
                    input_data.update(post_input)
            except ValueError:
                pass

        allowed_params = form.allowedQueryParams or []
        for param_name in allowed_params:
            param_value = req.params.get(param_name)
            if param_value is not None:
                input_data[param_name] = param_value

        logger.info(f"Executing launch workflow {form.launchWorkflowId} with merged input data: {input_data}")

        registry = get_registry()
        workflow_metadata = registry.get_workflow(form.launchWorkflowId)

        if not workflow_metadata:
            logger.error(f"Launch workflow '{form.launchWorkflowId}' not found in registry")
            error = ErrorResponse(error="NotFound", message=f"Launch workflow '{form.launchWorkflowId}' not found")
            return error.model_dump(), 404

        workflow_func = workflow_metadata.function
        defined_params = {param.name for param in workflow_metadata.parameters}
        workflow_params = {}
        extra_variables = {}

        for key, value in input_data.items():
            if key in defined_params:
                workflow_params[key] = value
            else:
                extra_variables[key] = value

        # Extra variables are no longer injected into context

        result = await workflow_func(workflow_context, **workflow_params)
        logger.info(f"Launch workflow {form.launchWorkflowId} completed successfully")
        return {"result": result}, 200

    except TypeError as e:
        error_msg = str(e)
        logger.warning(f"Launch workflow parameter error: {error_msg}")

        if "missing" in error_msg and "required positional argument" in error_msg:
            param_name = error_msg.split("'")[-2] if "'" in error_msg else "unknown"
            user_message = f"Launch workflow requires parameter '{param_name}' but it was not provided. Check the form's allowed query parameters configuration."
        else:
            user_message = f"Invalid parameters for launch workflow: {error_msg}"

        # form is guaranteed to exist here (we've already checked and returned early if not)
        assert form is not None
        error = ErrorResponse(error="BadRequest", message=user_message, details={"workflow": form.launchWorkflowId, "error": error_msg})
        return error.model_dump(), 400

    except WorkflowError as e:
        # form is guaranteed to exist here (we've already checked and returned early if not)
        assert form is not None
        logger.error(f"Launch workflow failed: {form.launchWorkflowId} - {e.error_type}: {e.message}")
        error = ErrorResponse(error=e.error_type, message=e.message, details=e.details)
        return error.model_dump(), 400

    except Exception as e:
        logger.error(f"Unexpected error executing form startup workflow: {str(e)}", exc_info=True)
        error = ErrorResponse(error="InternalServerError", message=f"An unexpected error occurred while executing the launch workflow: {str(e)}")
        return error.model_dump(), 500


async def execute_form_handler(form_id: str, request_body: dict, request_context, workflow_context) -> tuple[dict, int]:
    """Execute a form and run the linked workflow"""
    from shared.handlers.workflows_handlers import execute_workflow_internal

    logger.info(f"User {request_context.user_id} submitting form {form_id}")

    try:
        # Form-specific permission checks
        if not can_user_execute_form(request_context, form_id):
            logger.warning(f"User {request_context.user_id} denied access to execute form {form_id}")
            error = ErrorResponse(error="Forbidden", message="You don't have permission to execute this form")
            return error.model_dump(), 403

        form_repo = FormsFileRepository(request_context)
        form = await form_repo.get_form(form_id)

        if not form:
            logger.warning(f"Form {form_id} not found")
            error = ErrorResponse(error="NotFound", message="Form not found")
            return error.model_dump(), 404

        # Regular users cannot execute inactive forms; admins can (for testing/development)
        if not form.isActive and not request_context.is_platform_admin:
            logger.warning(f"Form {form_id} is not active and user is not an admin")
            error = ErrorResponse(error="NotFound", message="Form not found")
            return error.model_dump(), 404

        linked_workflow = form.linkedWorkflow
        if not linked_workflow:
            logger.error(f"Form {form_id} has no linked workflow")
            error = ErrorResponse(error="InternalServerError", message="Form configuration error: No linked workflow")
            return error.model_dump(), 500

        form_data = request_body.get("form_data", {})
        logger.info(f"Executing workflow {linked_workflow} with form data: {form_data}")

        # Delegate to shared workflow execution logic
        # This handles async/sync execution, queueing, engine execution, etc.
        response_dict, status_code = await execute_workflow_internal(
            context=workflow_context,
            workflow_name=linked_workflow,
            parameters=form_data,
            form_id=form_id,
            transient=False
        )

        return response_dict, status_code

    except ValueError as e:
        logger.error(f"Error parsing request: {str(e)}")
        error = ErrorResponse(error="BadRequest", message="Invalid JSON in request body")
        return error.model_dump(), 400

    except Exception as e:
        logger.error(f"Error submitting form: {str(e)}", exc_info=True)
        error = ErrorResponse(error="InternalServerError", message="Failed to submit form")
        return error.model_dump(), 500


async def get_form_roles_handler(form_id: str, request_context) -> tuple[dict, int]:
    """Get all roles assigned to a form"""
    from shared.authorization import get_form_role_ids

    logger.info(f"User {request_context.user_id} requesting roles for form {form_id}")

    try:
        # Check if form exists and user has access
        form_repo = FormsFileRepository(request_context)
        form = await form_repo.get_form(form_id)

        if not form:
            logger.warning(f"Form {form_id} not found")
            error = ErrorResponse(error="NotFound", message="Form not found")
            return error.model_dump(), 404

        # Only platform admins can view role assignments
        if not request_context.is_platform_admin:
            logger.warning(f"User {request_context.user_id} is not authorized to view form roles")
            error = ErrorResponse(error="Forbidden", message="Only platform admins can view form roles")
            return error.model_dump(), 403

        # Get assigned role IDs
        role_ids = await get_form_role_ids(form_id)

        logger.info(f"Form {form_id} has {len(role_ids)} assigned roles")
        return {"roleIds": role_ids}, 200

    except Exception as e:
        logger.error(f"Error retrieving form roles: {str(e)}", exc_info=True)
        error = ErrorResponse(error="InternalServerError", message="Failed to retrieve form roles")
        return error.model_dump(), 500


async def execute_form_data_provider_handler(
    form_id: str,
    provider_name: str,
    request_context,
    workflow_context,
    no_cache: bool = False,
    inputs: dict | None = None
) -> tuple[dict, int]:
    """
    Execute a data provider in the context of a form.

    This endpoint replaces the global /api/data-providers/{providerName} endpoint
    and ensures users can only access data providers through forms they have access to.

    Args:
        form_id: Form ID (UUID)
        provider_name: Name of the data provider to execute
        request_context: Request context with user info
        workflow_context: Workflow execution context
        no_cache: If True, bypass cache
        inputs: Optional input parameter values for the data provider

    Returns:
        Tuple of (response_dict, status_code)

    Response structure:
        {
            "provider": "get_available_licenses",
            "options": [...],
            "cached": False,
            "cache_expires_at": "2025-10-10T12:05:00Z"
        }

    Status codes:
        200: Success
        400: Invalid provider name or parameters
        403: User doesn't have access to the form
        404: Form or provider not found
        500: Provider execution error
    """
    from shared.handlers.data_providers_handlers import get_data_provider_options_handler

    logger.info(
        f"User {request_context.user_id} requesting data provider {provider_name} for form {form_id}"
    )

    try:
        # 1. Check if form exists
        form_repo = FormsFileRepository(request_context)
        form = await form_repo.get_form(form_id)

        if not form:
            logger.warning(f"Form {form_id} not found")
            error = ErrorResponse(error="NotFound", message="Form not found")
            return error.model_dump(), 404

        # 2. Check if user has access to view the form (applies access level rules)
        if not can_user_view_form(request_context, form_id):
            logger.warning(
                f"User {request_context.user_id} does not have access to form {form_id}"
            )
            error = ErrorResponse(
                error="Forbidden",
                message="You do not have access to this form"
            )
            return error.model_dump(), 403

        # 3. Execute the data provider using workflow context (for org scope)
        logger.info(
            f"Executing data provider {provider_name} for form {form_id} "
            f"(user={request_context.user_id}, org={workflow_context.org_id})"
        )

        result, status_code = await get_data_provider_options_handler(
            provider_name=provider_name,
            context=workflow_context,
            no_cache=no_cache,
            inputs=inputs
        )

        return result, status_code

    except Exception as e:
        logger.error(
            f"Error executing data provider {provider_name} for form {form_id}: {str(e)}",
            exc_info=True
        )
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to execute data provider"
        )
        return error.model_dump(), 500
