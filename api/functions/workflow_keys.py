"""
Workflow API Keys Management
Handles creation, listing, and revocation of workflow API keys

Business logic extracted to shared/handlers/workflow_keys_handlers.py
"""

import azure.functions as func

from shared.handlers.workflow_keys_handlers import (
    create_workflow_key_handler,
    list_workflow_keys_handler,
    revoke_workflow_key_handler,
)
from shared.middleware import with_org_context
from shared.models import (
    WorkflowKeyCreateRequest,
    WorkflowKeyResponse,
)
from shared.openapi_decorators import openapi_endpoint

# Create blueprint for workflow keys endpoints
bp = func.Blueprint()


@bp.route(route="workflow-keys", methods=["POST"])
@bp.function_name("create_workflow_key")
@openapi_endpoint(
    path="/workflow-keys",
    method="POST",
    summary="Create a workflow API key",
    description="Generate a new API key for workflow HTTP access (Platform admin only)",
    tags=["Workflow Keys"],
    request_model=WorkflowKeyCreateRequest,
    response_model=WorkflowKeyResponse
)
@with_org_context
async def create_workflow_key(req: func.HttpRequest) -> func.HttpResponse:
    """Create a new workflow API key"""
    return await create_workflow_key_handler(req)


@bp.route(route="workflow-keys", methods=["GET"])
@bp.function_name("list_workflow_keys")
@openapi_endpoint(
    path="/workflow-keys",
    method="GET",
    summary="List workflow API keys",
    description="Get all workflow API keys for the current user (Platform admin only)",
    tags=["Workflow Keys"],
    response_model=list[WorkflowKeyResponse]
)
@with_org_context
async def list_workflow_keys(req: func.HttpRequest) -> func.HttpResponse:
    """List all workflow API keys for the current user"""
    return await list_workflow_keys_handler(req)


@bp.route(route="workflow-keys/{keyId}", methods=["DELETE"])
@bp.function_name("revoke_workflow_key")
@openapi_endpoint(
    path="/workflow-keys/{keyId}",
    method="DELETE",
    summary="Revoke a workflow API key",
    description="Revoke an existing workflow API key (Platform admin only)",
    tags=["Workflow Keys"],
    path_params={
        "keyId": {
            "description": "ID of the key to revoke",
            "schema": {"type": "string"},
            "required": True
        }
    }
)
@with_org_context
async def revoke_workflow_key(req: func.HttpRequest) -> func.HttpResponse:
    """Revoke a workflow API key"""
    return await revoke_workflow_key_handler(req)
