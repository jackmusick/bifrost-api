"""
Metrics API
Provides aggregated statistics and metrics
"""

import json
import logging

import azure.functions as func

from shared.decorators import with_request_context
from shared.handlers.metrics_handlers import get_dashboard_metrics
from shared.models import DashboardMetricsResponse, ErrorResponse
from shared.openapi_decorators import openapi_endpoint

logger = logging.getLogger(__name__)

# Create blueprint for metrics endpoints
bp = func.Blueprint()


@bp.function_name("get_metrics")
@bp.route(route="metrics", methods=["GET"])
@openapi_endpoint(
    path="/metrics",
    method="GET",
    summary="Get system metrics",
    description="Get aggregated system statistics including workflow count, form count, execution statistics (30 days), recent failures, and success rate",
    tags=["Metrics"],
    response_model=DashboardMetricsResponse
)
@with_request_context
async def get_metrics(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/metrics

    Returns aggregated metrics via handler:
    - Workflow count
    - Form count
    - Execution statistics (30 days)
    - Recent failures
    - Success rate
    """
    context = req.context  # type: ignore[attr-defined]
    logger.info(f"User {context.user_id} retrieving dashboard metrics")

    try:
        metrics = await get_dashboard_metrics(context)
        return func.HttpResponse(
            json.dumps(metrics),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error retrieving dashboard metrics: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to retrieve dashboard metrics"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )
