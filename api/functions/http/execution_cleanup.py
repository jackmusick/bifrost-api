"""
Execution Cleanup HTTP Endpoints
Provides manual control over stuck execution cleanup
"""

import azure.functions as func

from shared.decorators import require_platform_admin, with_request_context
from shared.handlers.execution_cleanup_handlers import (
    get_stuck_executions_handler,
    trigger_cleanup_handler,
)
from shared.models import StuckExecutionsResponse, CleanupTriggeredResponse
from shared.openapi_decorators import openapi_endpoint

# Create blueprint for execution cleanup endpoints
bp = func.Blueprint()


@bp.function_name("cleanup_get_stuck")
@bp.route(route="executions/cleanup/stuck", methods=["GET"])
@openapi_endpoint(
    path="/executions/cleanup/stuck",
    method="GET",
    summary="Get stuck executions",
    description="Get list of executions stuck in Pending/Running state beyond timeout thresholds (platform admin only)",
    tags=["Executions"],
    response_model=StuckExecutionsResponse
)
@with_request_context
@require_platform_admin
async def get_stuck(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get list of stuck executions.

    Returns:
        200: List of stuck executions
    """
    return await get_stuck_executions_handler(req, req.context)


@bp.function_name("cleanup_trigger")
@bp.route(route="executions/cleanup/trigger", methods=["POST"])
@openapi_endpoint(
    path="/executions/cleanup/trigger",
    method="POST",
    summary="Trigger cleanup of stuck executions",
    description="Manually trigger cleanup of stuck executions (times them out and updates status) - platform admin only",
    tags=["Executions"],
    response_model=CleanupTriggeredResponse
)
@with_request_context
@require_platform_admin
async def trigger_cleanup(req: func.HttpRequest) -> func.HttpResponse:
    """
    Manually trigger cleanup of stuck executions.

    Returns:
        200: Cleanup results with counts
    """
    return await trigger_cleanup_handler(req, req.context)
