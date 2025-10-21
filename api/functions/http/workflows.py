"""
Workflow Execution API
Handles execution of registered workflows with org context

Business logic extracted to shared/handlers/workflows_handlers.py
"""

import azure.functions as func

from shared.decorators import require_platform_admin, with_request_context
from shared.handlers.workflows_handlers import execute_workflow_handler
from shared.middleware import with_org_context
from shared.models import WorkflowExecutionRequest, WorkflowExecutionResponse
from shared.openapi_decorators import openapi_endpoint

# Create blueprint for workflow execution endpoints
bp = func.Blueprint()


@bp.route(route="workflows/{workflowName}/execute", methods=["POST"])
@bp.function_name("execute_workflow")
@openapi_endpoint(
    path="/workflows/{workflowName}/execute",
    method="POST",
    summary="Execute a workflow",
    description="Execute a workflow with the provided parameters (Platform admin only)",
    tags=["Workflows"],
    request_model=WorkflowExecutionRequest,
    response_model=WorkflowExecutionResponse,
    path_params={
        "workflowName": {
            "description": "Name of the workflow to execute",
            "schema": {"type": "string"},
            "required": True
        }
    }
)
@with_request_context
@with_org_context
@require_platform_admin
async def execute_workflow(req: func.HttpRequest) -> func.HttpResponse:
    """Execute a workflow with the provided parameters"""
    return await execute_workflow_handler(req)
