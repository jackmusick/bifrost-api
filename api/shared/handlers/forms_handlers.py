"""
Form endpoint handlers - extracted business logic
Provides pure async handlers for form CRUD and execution operations
"""

import logging
from typing import Any

from pydantic import ValidationError

from shared.error_handling import WorkflowError
from src.models.schemas import (
    CreateFormRequest,
    ErrorResponse,
    UpdateFormRequest,
)
from src.repositories.forms_file import FormsFileRepository
from shared.system_logger import get_system_logger

logger = logging.getLogger(__name__)


# =============================================================================
# Authorization Helpers (use PostgreSQL directly)
# =============================================================================

async def can_user_view_form(request_context, form_id: str) -> bool:
    """Check if user can view a form using PostgreSQL directly."""
    from uuid import UUID
    from sqlalchemy import select, or_
    from src.core.database import get_session_factory
    from src.models import Form, UserRole, FormRole

    # Platform admins can view all forms
    if request_context.is_platform_admin:
        return True

    session_factory = get_session_factory()
    async with session_factory() as db:
        form_uuid = UUID(form_id)
        org_uuid = UUID(request_context.org_id) if request_context.org_id else None

        # Get form with org scoping (user's org forms + global forms)
        query = select(Form).where(Form.id == form_uuid)
        if org_uuid:
            query = query.where(
                or_(Form.organization_id == org_uuid, Form.organization_id.is_(None))
            )
        else:
            query = query.where(Form.organization_id.is_(None))

        result = await db.execute(query)
        form = result.scalar_one_or_none()

        if not form:
            return False

        # Only active forms for non-admins
        if not form.is_active:
            return False

        # Check access level
        access_level = form.access_level or "role_based"
        if access_level == "public":
            return True
        if access_level == "authenticated":
            return True

        # Role-based: check if user has a role assigned to this form via FormRole table
        user_uuid = UUID(request_context.user_id)
        role_query = select(UserRole.role_id).where(UserRole.user_id == user_uuid)
        role_result = await db.execute(role_query)
        user_role_ids = list(role_result.scalars().all())

        if not user_role_ids:
            return False

        # Check if any of user's roles are assigned to this form
        form_role_query = select(FormRole).where(
            FormRole.form_id == form_uuid,
            FormRole.role_id.in_(user_role_ids),
        )
        form_role_result = await db.execute(form_role_query)
        return form_role_result.scalar_one_or_none() is not None


async def can_user_execute_form(request_context, form_id: str) -> bool:
    """Check if user can execute a form (same as view)."""
    return await can_user_view_form(request_context, form_id)


async def get_user_visible_forms(request_context) -> list[dict]:
    """Get all forms visible to user as list of dicts."""
    from uuid import UUID
    from sqlalchemy import select, or_
    from src.core.database import get_session_factory
    from src.models import Form, UserRole, FormRole

    session_factory = get_session_factory()
    async with session_factory() as db:
        org_uuid = UUID(request_context.org_id) if request_context.org_id else None

        # Base query with org scoping (user's org forms + global forms)
        query = select(Form)
        if org_uuid:
            query = query.where(
                or_(Form.organization_id == org_uuid, Form.organization_id.is_(None))
            )
        else:
            query = query.where(Form.organization_id.is_(None))

        # Platform admin sees all forms
        if request_context.is_platform_admin:
            result = await db.execute(query)
            forms = result.scalars().all()
            return [await _form_to_dict(db, f) for f in forms]

        # Regular user: filter to active forms
        query = query.where(Form.is_active)
        result = await db.execute(query)
        all_forms = list(result.scalars().all())

        # Get user's roles
        user_uuid = UUID(request_context.user_id)
        role_query = select(UserRole.role_id).where(UserRole.user_id == user_uuid)
        role_result = await db.execute(role_query)
        user_role_ids = list(role_result.scalars().all())

        # Get all form-role assignments for user's roles
        form_role_query = select(FormRole.form_id).where(
            FormRole.role_id.in_(user_role_ids)
        ) if user_role_ids else select(FormRole.form_id).where(False)
        form_role_result = await db.execute(form_role_query)
        accessible_form_ids = {r for r in form_role_result.scalars().all()}

        # Filter by access level
        visible_forms = []
        for form in all_forms:
            access_level = form.access_level or "role_based"
            if access_level == "public":
                visible_forms.append(form)
            elif access_level == "authenticated":
                visible_forms.append(form)
            elif access_level == "role_based":
                if form.id in accessible_form_ids:
                    visible_forms.append(form)

        return [await _form_to_dict(db, f) for f in visible_forms]


async def get_form_role_ids(form_id: str) -> list[str]:
    """Get role IDs assigned to a form via FormRole table."""
    from uuid import UUID
    from sqlalchemy import select
    from src.core.database import get_session_factory
    from src.models import FormRole

    session_factory = get_session_factory()
    async with session_factory() as db:
        form_uuid = UUID(form_id)
        query = select(FormRole.role_id).where(FormRole.form_id == form_uuid)
        result = await db.execute(query)
        return [str(r) for r in result.scalars().all()]


async def _form_to_dict(db, form) -> dict:
    """Convert Form ORM object to dict for handler compatibility."""
    from sqlalchemy import select
    from src.models import FormRole

    # Get assigned roles from FormRole table
    role_query = select(FormRole.role_id).where(FormRole.form_id == form.id)
    role_result = await db.execute(role_query)
    assigned_role_ids = [str(r) for r in role_result.scalars().all()]

    return {
        "id": str(form.id),
        "name": form.name,
        "description": form.description,
        "org_id": str(form.organization_id) if form.organization_id else None,
        "linked_workflow": form.linked_workflow,
        "launch_workflow_id": form.launch_workflow_id,
        "default_launch_params": form.default_launch_params,
        "allowed_query_params": form.allowed_query_params,
        "form_schema": form.form_schema,
        "is_active": form.is_active,
        "access_level": form.access_level,
        "assigned_role_ids": assigned_role_ids,
        "created_at": form.created_at.isoformat() if form.created_at else None,
        "updated_at": form.updated_at.isoformat() if form.updated_at else None,
    }


# =============================================================================
# Data Provider Helpers
# =============================================================================


async def _execute_data_provider(
    provider_name: str,
    context,
    no_cache: bool = False,
    inputs: dict | None = None
) -> tuple[dict, int]:
    """
    Execute a data provider and return options.

    Args:
        provider_name: Name of the data provider
        context: Execution context
        no_cache: Whether to bypass cache
        inputs: Optional input parameters

    Returns:
        Tuple of (response_dict, status_code)
    """
    from shared.discovery import get_data_provider
    from shared.engine import run_workflow

    # Load the data provider
    result = get_data_provider(provider_name)
    if not result:
        logger.warning(f"Data provider '{provider_name}' not found")
        error = ErrorResponse(error="NotFound", message=f"Data provider '{provider_name}' not found")
        return error.model_dump(), 404

    provider_func, provider_metadata = result

    try:
        # Execute the data provider with inputs
        provider_inputs = inputs or {}
        options = await run_workflow(provider_func, context, provider_inputs)

        response = {
            "provider": provider_name,
            "options": options if isinstance(options, list) else [],
            "cached": False,
            "cacheExpiresAt": None
        }
        return response, 200

    except TypeError as e:
        logger.warning(f"Data provider '{provider_name}' parameter error: {e}")
        error = ErrorResponse(
            error="BadRequest",
            message=f"Invalid parameters for data provider: {str(e)}"
        )
        return error.model_dump(), 400
    except Exception as e:
        logger.error(f"Data provider '{provider_name}' execution failed: {e}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message=f"Data provider execution failed: {str(e)}"
        )
        return error.model_dump(), 500


# =============================================================================
# Validation Helpers
# =============================================================================


def validate_data_provider_inputs_for_form(form_schema_fields: list) -> list[str]:
    """
    Validate dataProviderInputs for all fields in a form (T028-T030).

    Args:
        form_schema_fields: List of FormField objects

    Returns:
        List of validation error messages (empty if valid)

    Validation rules:
        1. If field has dataProvider, check if provider exists
        2. If provider has required parameters, validate that static inputs are provided
        3. dataProviderInputs validation is handled by Pydantic model validators
    """
    from shared.discovery import get_data_provider
    errors = []

    for field in form_schema_fields:
        if not field.dataProvider:
            continue

        # Dynamically load provider metadata
        result = get_data_provider(field.dataProvider)
        provider_metadata = result[1] if result else None

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
                    # Check if input is provided in data_provider_inputs
                    if not field.data_provider_inputs or param.name not in field.data_provider_inputs:
                        errors.append(
                            f"Field '{field.name}' uses data provider '{field.data_provider}': "
                            f"required parameter '{param.name}' is missing from data_provider_inputs"
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

    from shared.discovery import get_workflow
    result = get_workflow(launch_workflow_id)

    if not result:
        return f"Launch workflow '{launch_workflow_id}' not found"

    _, workflow_metadata = result

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
        from shared.discovery import get_workflow

        forms = await get_user_visible_forms(request_context)

        # Enrich forms with validation info (missing required params)
        for form in forms:
            linked_workflow = form.get("linkedWorkflow")
            logger.info(f"Validating form '{form.get('name')}' linked to workflow '{linked_workflow}'")

            if not linked_workflow:
                form["missingRequiredParams"] = []
                logger.info(f"Form '{form.get('name')}' has no linked workflow - marking as valid")
                continue

            # Dynamically load workflow metadata
            result = get_workflow(linked_workflow)
            workflow_metadata = result[1] if result else None
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
            launch_workflow_id=create_request.launch_workflow_id,
            default_launch_params=create_request.default_launch_params,
            allowed_query_params=create_request.allowed_query_params,
            form_schema_fields=create_request.form_schema.fields
        )
        if validation_error:
            logger.warning(f"Launch workflow validation failed: {validation_error}")
            error = ErrorResponse(error="ValidationError", message=validation_error)
            return error.model_dump(), 400

        # T028-T030: Validate dataProviderInputs for all form fields
        data_provider_errors = validate_data_provider_inputs_for_form(create_request.form_schema.fields)
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
        logger.info(f"Created form {form.id} in partition {form.org_id}")

        # Log to system logger
        system_logger = get_system_logger()
        await system_logger.log_form_event(
            action="create",
            form_id=form.id,
            form_name=form.name,
            scope=form.org_id or "GLOBAL",
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

        merged_launch_workflow = update_request.launch_workflow_id if update_request.launch_workflow_id is not None else existing_form.launch_workflow_id
        merged_default_params = update_request.default_launch_params if update_request.default_launch_params is not None else existing_form.default_launch_params
        merged_query_params = update_request.allowed_query_params if update_request.allowed_query_params is not None else existing_form.allowed_query_params
        merged_form_schema = update_request.form_schema if update_request.form_schema is not None else existing_form.form_schema

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
            scope=form.org_id or "GLOBAL",
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
                scope=form.org_id or "GLOBAL",
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


async def execute_form_startup_handler(form_id: str, req: Any, request_context: Any, workflow_context: Any) -> tuple[dict, int]:
    """Execute the form's launch workflow to get initial context data"""
    from shared.discovery import get_workflow

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
        if not form.is_active and not request_context.is_platform_admin:
            logger.warning(f"Form {form_id} is not active and user is not an admin")
            error = ErrorResponse(error="NotFound", message="Form not found")
            return error.model_dump(), 404

        if not form.launch_workflow_id:
            logger.info(f"Form {form_id} has no launch workflow, returning empty result")
            return {"result": {}}, 200

        input_data = dict(form.default_launch_params or {})

        if req.method == "POST":
            try:
                request_body = req.get_json()
                if request_body:
                    post_input = request_body.get('form_data', {})
                    input_data.update(post_input)
            except ValueError:
                pass

        allowed_params = form.allowed_query_params or []
        for param_name in allowed_params:
            param_value = req.params.get(param_name)
            if param_value is not None:
                input_data[param_name] = param_value

        logger.info(f"Executing launch workflow {form.launch_workflow_id} with merged input data: {input_data}")

        # Dynamically load workflow (always fresh)
        result = get_workflow(form.launch_workflow_id)

        if not result:
            logger.error(f"Launch workflow '{form.launch_workflow_id}' not found")
            error = ErrorResponse(error="NotFound", message=f"Launch workflow '{form.launch_workflow_id}' not found")
            return error.model_dump(), 404

        workflow_func, workflow_metadata = result
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
        logger.info(f"Launch workflow {form.launch_workflow_id} completed successfully")
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
        error = ErrorResponse(error="BadRequest", message=user_message, details={"workflow": form.launch_workflow_id, "error": error_msg})
        return error.model_dump(), 400

    except WorkflowError as e:
        # form is guaranteed to exist here (we've already checked and returned early if not)
        assert form is not None
        logger.error(f"Launch workflow failed: {form.launch_workflow_id} - {e.error_type}: {e.message}")
        error = ErrorResponse(error=e.error_type, message=e.message, details=e.details)
        return error.model_dump(), 400

    except Exception as e:
        logger.error(f"Unexpected error executing form startup workflow: {str(e)}", exc_info=True)
        error = ErrorResponse(error="InternalServerError", message=f"An unexpected error occurred while executing the launch workflow: {str(e)}")
        return error.model_dump(), 500


async def execute_form_handler(form_id: str, request_body: dict, request_context, workflow_context) -> tuple[dict, int]:
    """Execute a form and run the linked workflow"""
    from shared.execution_service import run_workflow, WorkflowNotFoundError, WorkflowLoadError
    from src.models.schemas import ExecutionStatus

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
        if not form.is_active and not request_context.is_platform_admin:
            logger.warning(f"Form {form_id} is not active and user is not an admin")
            error = ErrorResponse(error="NotFound", message="Form not found")
            return error.model_dump(), 404

        linked_workflow = form.linked_workflow
        if not linked_workflow:
            logger.error(f"Form {form_id} has no linked workflow")
            error = ErrorResponse(error="InternalServerError", message="Form configuration error: No linked workflow")
            return error.model_dump(), 500

        form_data = request_body.get("form_data", {})
        logger.info(f"Executing workflow {linked_workflow} with form data: {form_data}")

        # Execute workflow via execution service
        result = await run_workflow(
            context=workflow_context,
            workflow_name=linked_workflow,
            input_data=form_data,
            form_id=form_id,
            transient=False
        )

        # Convert response to dict format for HTTP response
        response_dict = {
            "executionId": result.execution_id,
            "status": result.status.value,
        }

        if result.status == ExecutionStatus.PENDING:
            response_dict["message"] = "Workflow queued for async execution"
            return response_dict, 202

        # Add execution details for completed executions
        if result.duration_ms is not None:
            response_dict["durationMs"] = result.duration_ms
        if result.started_at:
            response_dict["startedAt"] = result.started_at.isoformat()
        if result.completed_at:
            response_dict["completedAt"] = result.completed_at.isoformat()

        if result.status == ExecutionStatus.SUCCESS:
            response_dict["result"] = result.result
        if result.error:
            response_dict["error"] = result.error
        if result.error_type:
            response_dict["errorType"] = result.error_type
        if result.logs:
            response_dict["logs"] = result.logs

        return response_dict, 200

    except WorkflowNotFoundError as e:
        logger.error(f"Workflow not found: {str(e)}")
        error = ErrorResponse(error="NotFound", message=str(e))
        return error.model_dump(), 404

    except WorkflowLoadError as e:
        logger.error(f"Workflow load error: {str(e)}")
        error = ErrorResponse(error="InternalServerError", message=str(e))
        return error.model_dump(), 500

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
    # get_form_role_ids is defined in this module
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

        result, status_code = await _execute_data_provider(
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
