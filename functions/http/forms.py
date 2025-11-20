"""
Forms API endpoints
- CRUD operations for workflow forms
- Support for org-specific and global forms
"""

import json
import logging

import azure.functions as func

from shared.decorators import require_platform_admin, with_request_context
from shared.middleware import with_org_context
from shared.models import (
    CreateFormRequest,
    DataProviderRequest,
    DataProviderResponse,
    Form,
    FormExecuteRequest,
    FormStartupResponse,
    UpdateFormRequest,
)
from shared.openapi_decorators import openapi_endpoint
from shared.handlers.forms_handlers import (
    list_forms_handler,
    create_form_handler,
    get_form_handler,
    update_form_handler,
    delete_form_handler,
    execute_form_startup_handler,
    execute_form_handler,
    get_form_roles_handler,
    execute_form_data_provider_handler,
)

logger = logging.getLogger(__name__)

# Create blueprint for forms endpoints
bp = func.Blueprint()


@bp.function_name("forms_list_forms")
@bp.route(route="forms", methods=["GET"])
@openapi_endpoint(
    path="/forms",
    method="GET",
    summary="List forms",
    description="List all forms visible to the user. Platform admins see all forms in their org scope. Regular users see only forms they can access (public forms + forms assigned to their roles). Triggers forms re-scan to pick up new forms.",
    tags=["Forms"],
    response_model=list[Form]
)
@with_request_context
async def list_forms(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/forms - List all forms visible to the user"""
    # Re-scan workspace to pick up new forms (matches workflow list behavior)
    from function_app import get_workspace_paths
    from shared.forms_registry import get_forms_registry
    from pathlib import Path

    logger.info("Triggering forms registry reload before returning forms")
    forms_registry = get_forms_registry()
    workspace_paths = [Path(str(p)) for p in get_workspace_paths()]
    forms_registry.load_all_forms(workspace_paths)

    context = req.context  # type: ignore[attr-defined]
    result, status_code = await list_forms_handler(req, context)
    return func.HttpResponse(
        json.dumps(result),
        status_code=status_code,
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
    """POST /api/forms - Create a new form (Platform admin only)"""
    context = req.context  # type: ignore[attr-defined]
    request_body = req.get_json()
    result, status_code = await create_form_handler(request_body, context)
    return func.HttpResponse(
        json.dumps(result),
        status_code=status_code,
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
    """GET /api/forms/{formId} - Get a specific form by ID"""
    # Re-scan workspace to pick up new forms (matches list behavior)
    from function_app import get_workspace_paths
    from shared.forms_registry import get_forms_registry
    from pathlib import Path

    logger.info("Triggering forms registry reload before getting form")
    forms_registry = get_forms_registry()
    workspace_paths = [Path(str(p)) for p in get_workspace_paths()]
    forms_registry.load_all_forms(workspace_paths)

    context = req.context  # type: ignore[attr-defined]
    form_id = req.route_params.get("formId")
    assert form_id is not None
    result, status_code = await get_form_handler(form_id, context)
    return func.HttpResponse(
        json.dumps(result),
        status_code=status_code,
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
    """PUT /api/forms/{formId} - Update a form (Platform admin only)"""
    context = req.context  # type: ignore[attr-defined]
    form_id = req.route_params.get("formId")
    assert form_id is not None
    request_body = req.get_json()
    result, status_code = await update_form_handler(form_id, request_body, context)
    return func.HttpResponse(
        json.dumps(result),
        status_code=status_code,
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
    """DELETE /api/forms/{formId} - Soft delete a form (Platform admin only)"""
    context = req.context  # type: ignore[attr-defined]
    form_id = req.route_params.get("formId")
    assert form_id is not None
    result, status_code = await delete_form_handler(form_id, context)

    if status_code == 204:
        return func.HttpResponse(status_code=204)
    return func.HttpResponse(
        json.dumps(result),
        status_code=status_code,
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
    request_model=FormExecuteRequest,
    response_model=FormStartupResponse,
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
    """GET/POST /api/forms/{formId}/startup - Execute form's launch workflow"""
    request_context = req.context  # type: ignore[attr-defined]
    workflow_context = req.org_context  # type: ignore[attr-defined]
    form_id = req.route_params.get("formId")
    assert form_id is not None
    result, status_code = await execute_form_startup_handler(form_id, req, request_context, workflow_context)
    return func.HttpResponse(
        json.dumps(result, default=str),
        status_code=status_code,
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
@with_request_context
@with_org_context
async def execute_form(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/forms/{formId}/execute - Execute a form and run linked workflow"""
    request_context = req.context  # type: ignore[attr-defined]
    workflow_context = req.org_context  # type: ignore[attr-defined]
    form_id = req.route_params.get("formId")
    assert form_id is not None
    request_body = req.get_json()
    result, status_code = await execute_form_handler(form_id, request_body, request_context, workflow_context)
    return func.HttpResponse(
        json.dumps(result, default=str),
        status_code=status_code,
        mimetype="application/json"
    )


@bp.function_name("forms_get_form_roles")
@bp.route(route="forms/{formId}/roles", methods=["GET"])
@openapi_endpoint(
    path="/forms/{formId}/roles",
    method="GET",
    summary="Get roles assigned to a form",
    description="Get all roles that have access to this form (Platform admin only)",
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
async def get_form_roles(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/forms/{formId}/roles - Get roles assigned to form"""
    # Re-scan workspace to pick up new forms (matches list behavior)
    from function_app import get_workspace_paths
    from shared.forms_registry import get_forms_registry
    from pathlib import Path

    logger.info("Triggering forms registry reload before getting form roles")
    forms_registry = get_forms_registry()
    workspace_paths = [Path(str(p)) for p in get_workspace_paths()]
    forms_registry.load_all_forms(workspace_paths)

    request_context = req.context  # type: ignore[attr-defined]
    form_id = req.route_params.get("formId")
    assert form_id is not None
    result, status_code = await get_form_roles_handler(form_id, request_context)
    return func.HttpResponse(
        json.dumps(result),
        status_code=status_code,
        mimetype="application/json"
    )


@bp.function_name("forms_execute_data_provider")
@bp.route(route="forms/{formId}/data-providers/{providerName}", methods=["POST"])
@openapi_endpoint(
    path="/forms/{formId}/data-providers/{providerName}",
    method="POST",
    summary="Execute a data provider in the context of a form",
    description="Execute a data provider to retrieve options for form fields. User must have access to view the form (enforces form access level rules). This replaces the global /api/data-providers/{providerName} endpoint.",
    tags=["Forms"],
    request_model=DataProviderRequest,
    response_model=DataProviderResponse,
    path_params={
        "formId": {
            "description": "Form ID (UUID)",
            "schema": {"type": "string", "format": "uuid"}
        },
        "providerName": {
            "description": "Data provider name",
            "schema": {"type": "string"}
        }
    }
)
@with_request_context
@with_org_context
async def execute_form_data_provider(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/forms/{formId}/data-providers/{providerName} - Execute data provider for form"""
    request_context = req.context  # type: ignore[attr-defined]
    workflow_context = req.org_context  # type: ignore[attr-defined]
    form_id = req.route_params.get("formId")
    provider_name = req.route_params.get("providerName")
    assert form_id is not None
    assert provider_name is not None

    # Parse request body for inputs and no_cache flag
    request_body = req.get_json() if req.get_body() else {}
    inputs = request_body.get("inputs")
    no_cache = request_body.get("noCache", False)

    result, status_code = await execute_form_data_provider_handler(
        form_id=form_id,
        provider_name=provider_name,
        request_context=request_context,
        workflow_context=workflow_context,
        no_cache=no_cache,
        inputs=inputs
    )
    return func.HttpResponse(
        json.dumps(result, default=str),
        status_code=status_code,
        mimetype="application/json"
    )
