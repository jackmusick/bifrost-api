"""
Dashboard Metrics API endpoints
Provides aggregated statistics for the dashboard
"""

import json
import azure.functions as func
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict

from shared.decorators import with_request_context
from shared.storage import get_table_service
from shared.models import ErrorResponse

logger = logging.getLogger(__name__)

# Create blueprint for dashboard endpoints
bp = func.Blueprint()


@bp.function_name("dashboard_metrics")
@bp.route(route="dashboard/metrics", methods=["GET"])
@with_request_context
async def get_dashboard_metrics(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/dashboard/metrics

    Returns aggregated metrics:
    - Workflow count
    - Form count
    - Execution statistics (30 days)
    - Recent failures
    - Success rate
    """
    from shared.registry import get_registry

    context = req.context
    logger.info(f"User {context.user_id} retrieving dashboard metrics")

    try:
        metrics = {}

        # 1. Get workflow count from registry
        try:
            registry = get_registry()
            summary = registry.get_summary()
            metrics["workflowCount"] = summary['workflows_count']
            metrics["dataProviderCount"] = summary['data_providers_count']
        except Exception as e:
            logger.warning(f"Failed to fetch workflow metadata: {e}")
            metrics["workflowCount"] = 0
            metrics["dataProviderCount"] = 0

        # 2. Get form count from Entities table
        entities_service = get_table_service("Entities", context)

        # Query forms in context scope (automatically applied by table service)
        form_entities = list(entities_service.query_entities(
            filter="RowKey ge 'form:' and RowKey lt 'form;' and IsActive eq true"
        ))
        metrics["formCount"] = len(form_entities)

        # 3. Get execution statistics (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        # Calculate reverse timestamp for 30 days ago
        reverse_ts_30_days = _get_reverse_timestamp(thirty_days_ago)

        # Query executions from Entities table (newest first due to reverse timestamp)
        # RowKey format: execution:reverse_ts_uuid
        execution_entities = list(entities_service.query_entities(
            filter=f"RowKey ge 'execution:' and RowKey le 'execution:{reverse_ts_30_days}_~'",
            select=["ExecutionId", "Status", "WorkflowName", "StartedAt", "CompletedAt", "ErrorMessage", "DurationMs"]
        ))

        # Calculate statistics
        total_executions = len(execution_entities)
        status_counts = defaultdict(int)
        total_duration_ms = 0
        duration_count = 0
        recent_failures = []

        for entity in execution_entities:
            status = entity.get("Status", "Unknown")
            status_counts[status] += 1

            # Track duration for average calculation
            duration = entity.get("DurationMs")
            if duration:
                total_duration_ms += duration
                duration_count += 1

            # Collect recent failures (limit to 10)
            if status == "Failed" and len(recent_failures) < 10:
                recent_failures.append({
                    "executionId": entity.get("ExecutionId"),
                    "workflowName": entity.get("WorkflowName"),
                    "errorMessage": entity.get("ErrorMessage"),
                    "startedAt": entity.get("StartedAt").isoformat() if entity.get("StartedAt") else None
                })

        # Calculate success rate
        success_count = status_counts.get("Success", 0)
        failed_count = status_counts.get("Failed", 0)
        completed_count = success_count + failed_count

        success_rate = (success_count / completed_count * 100) if completed_count > 0 else 0.0

        # Calculate average duration
        avg_duration_seconds = (total_duration_ms / duration_count / 1000) if duration_count > 0 else 0.0

        metrics["executionStats"] = {
            "totalExecutions": total_executions,
            "successCount": success_count,
            "failedCount": failed_count,
            "runningCount": status_counts.get("Running", 0),
            "pendingCount": status_counts.get("Pending", 0),
            "successRate": round(success_rate, 1),
            "avgDurationSeconds": round(avg_duration_seconds, 2)
        }

        metrics["recentFailures"] = recent_failures

        logger.info(f"Dashboard metrics retrieved for user {context.user_id}")

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


def _get_reverse_timestamp(dt: datetime) -> int:
    """
    Calculate reverse timestamp for descending order in Table Storage.
    Formula: 9999999999999 - timestamp_in_milliseconds
    """
    timestamp_ms = int(dt.timestamp() * 1000)
    return 9999999999999 - timestamp_ms
