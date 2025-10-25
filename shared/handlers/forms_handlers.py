"""
Form endpoint handlers - extracted business logic
Provides pure async handlers for form CRUD and execution operations
"""

import logging
from datetime import datetime

import azure.functions as func
from pydantic import ValidationError

from shared.authorization import can_user_execute_form, can_user_view_form, get_user_visible_forms
from shared.error_handling import WorkflowError
from shared.models import (
    CreateFormRequest,
    ErrorResponse,
    UpdateFormRequest,
    ExecutionStatus,
)
from shared.repositories.forms import FormRepository

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
        forms = get_user_visible_forms(request_context)
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

        form_repo = FormRepository(request_context)
        form = form_repo.create_form(form_request=create_request, created_by=request_context.user_id)
        logger.info(f"Created form {form.id} in partition {form.orgId}")
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
        error = ErrorResponse(error="InternalServerError", message="Failed to create form")
        return error.model_dump(), 500


async def get_form_handler(form_id: str, request_context) -> tuple[dict, int]:
    """Get a specific form by ID"""
    logger.info(f"User {request_context.user_id} retrieving form {form_id}")

    try:
        form_repo = FormRepository(request_context)
        form = form_repo.get_form(form_id)

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
        form_repo = FormRepository(request_context)
        existing_form = form_repo.get_form(form_id)

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

        form = form_repo.update_form(form_id, update_request)

        if not form:
            logger.warning(f"Form {form_id} not found after update")
            error = ErrorResponse(error="NotFound", message="Form not found")
            return error.model_dump(), 404

        logger.info(f"Updated form {form_id}")
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
        error = ErrorResponse(error="InternalServerError", message="Failed to update form")
        return error.model_dump(), 500


async def delete_form_handler(form_id: str, request_context) -> tuple[dict | None, int]:
    """Soft delete a form (set IsActive=False)"""
    logger.info(f"User {request_context.user_id} deleting form {form_id}")

    try:
        form_repo = FormRepository(request_context)
        success = form_repo.delete_form(form_id)

        if success:
            logger.info(f"Soft deleted form {form_id}")
        else:
            logger.debug(f"Form {form_id} not found, returning 204")

        return None, 204

    except Exception as e:
        logger.error(f"Error deleting form: {str(e)}", exc_info=True)
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

        form_repo = FormRepository(request_context)
        form = form_repo.get_form(form_id)

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

        from function_app import discover_workspace_modules
        discover_workspace_modules()

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
    from shared.execution_logger import get_execution_logger
    from shared.registry import get_registry

    logger.info(f"User {request_context.user_id} submitting form {form_id}")

    try:
        if not can_user_execute_form(request_context, form_id):
            logger.warning(f"User {request_context.user_id} denied access to execute form {form_id}")
            error = ErrorResponse(error="Forbidden", message="You don't have permission to execute this form")
            return error.model_dump(), 403

        form_repo = FormRepository(request_context)
        form = form_repo.get_form(form_id)

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

        from function_app import discover_workspace_modules
        discover_workspace_modules()

        registry = get_registry()
        workflow_metadata = registry.get_workflow(linked_workflow)

        if not workflow_metadata:
            logger.error(f"Workflow '{linked_workflow}' not found in registry")
            error = ErrorResponse(error="NotFound", message=f"Workflow '{linked_workflow}' not found")
            return error.model_dump(), 404

        workflow_func = workflow_metadata.function
        execution_id = workflow_context.execution_id

        exec_logger = get_execution_logger()
        start_time = datetime.utcnow()

        exec_logger.create_execution(
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

        defined_params = {param.name for param in workflow_metadata.parameters}
        workflow_params = {}
        extra_variables = {}

        for key, value in form_data.items():
            if key in defined_params:
                workflow_params[key] = value
            else:
                extra_variables[key] = value

        # Extra variables are no longer injected into context

        result = await workflow_func(workflow_context, **workflow_params)

        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        execution_status = ExecutionStatus.SUCCESS
        error_message = None

        if isinstance(result, dict) and result.get('success') is False:
            execution_status = ExecutionStatus.COMPLETED_WITH_ERRORS
            error_message = result.get('error', 'Workflow completed with errors')

        exec_logger.update_execution(
            execution_id=execution_id,
            org_id=request_context.org_id,
            user_id=request_context.user_id,
            status=execution_status,
            result=result,
            error_message=error_message,
            duration_ms=duration_ms,
            state_snapshots=workflow_context._state_snapshots,
            integration_calls=workflow_context._integration_calls
            # Note: Forms don't capture logs or variables
        )

        logger.info(f"Workflow execution completed: {execution_id}")

        execution_result = {
            "executionId": execution_id,
            "status": execution_status.value,
            "result": result,
            "durationMs": duration_ms,
            "startedAt": start_time.isoformat(),
            "completedAt": end_time.isoformat()
        }

        return execution_result, 200

    except ValueError as e:
        logger.error(f"Error parsing request: {str(e)}")
        error = ErrorResponse(error="BadRequest", message="Invalid JSON in request body")
        return error.model_dump(), 400

    except Exception as e:
        logger.error(f"Error submitting form: {str(e)}", exc_info=True)
        error = ErrorResponse(error="InternalServerError", message="Failed to submit form")
        return error.model_dump(), 500
