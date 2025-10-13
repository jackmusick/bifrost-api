"""
Dashboard Metrics API endpoints
Provides aggregated statistics for the dashboard
"""

import json
import azure.functions as func
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict

from shared.auth import require_auth, is_platform_admin
from shared.storage import TableStorageService
from shared.models import ErrorResponse

# Create blueprint for dashboard endpoints
bp = func.Blueprint()


@bp.function_name("dashboard_metrics")
@bp.route(route="dashboard/metrics", methods=["GET"])
@require_auth
def get_dashboard_metrics(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/dashboard/metrics

    Query parameters:
    - orgId: Organization ID (optional for platform admins)

    Returns aggregated metrics:
    - Workflow count
    - Form count
    - Execution statistics (30 days)
    - Recent failures
    - Success rate
    """
    from shared.auth_headers import get_auth_headers
    from functions.workflows import get_workflows_engine_config
    import requests
    import logging

    logger = logging.getLogger(__name__)
    user = req.user

    # Get auth headers - org is optional for platform admins
    org_id, user_id, error = get_auth_headers(req, require_org=False)
    if error:
        return error

    try:
        metrics = {}

        # 1. Get workflow count from workflow engine
        try:
            url, function_key = get_workflows_engine_config()
            headers = {}
            if function_key:
                headers["x-functions-key"] = function_key

            response = requests.get(
                f"{url}/api/registry/metadata",
                headers=headers,
                timeout=5
            )

            if response.status_code == 200:
                metadata = response.json()
                metrics["workflowCount"] = len(metadata.get("workflows", []))
                metrics["dataProviderCount"] = len(metadata.get("data_providers", []))
            else:
                metrics["workflowCount"] = 0
                metrics["dataProviderCount"] = 0
        except Exception as e:
            logger.warning(f"Failed to fetch workflow metadata: {e}")
            metrics["workflowCount"] = 0
            metrics["dataProviderCount"] = 0

        # 2. Get form count
        forms_service = TableStorageService("Forms")

        if org_id:
            # Org-specific + global forms
            org_forms = list(forms_service.query_entities(
                filter=f"PartitionKey eq '{org_id}' and IsActive eq true"
            ))
            global_forms = list(forms_service.query_entities(
                filter="PartitionKey eq 'GLOBAL' and IsActive eq true"
            ))
            metrics["formCount"] = len(org_forms) + len(global_forms)
        else:
            # Platform admin - all forms
            all_forms = list(forms_service.query_entities(
                filter="IsActive eq true"
            ))
            metrics["formCount"] = len(all_forms)

        # 3. Get execution statistics (last 30 days)
        executions_service = TableStorageService("WorkflowExecutions")
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        # Calculate reverse timestamp for 30 days ago
        reverse_ts_30_days = _get_reverse_timestamp(thirty_days_ago)

        # Build filter for last 30 days
        if org_id:
            # Single org
            filter_query = f"PartitionKey eq '{org_id}' and RowKey le '{reverse_ts_30_days}_~'"
        else:
            # Platform admin - need to query all orgs
            # This is expensive, but acceptable for admin dashboard
            filter_query = f"RowKey le '{reverse_ts_30_days}_~'"

        # Use projection to only fetch needed fields
        execution_entities = list(executions_service.query_entities(
            filter=filter_query,
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

        logger.info(f"Dashboard metrics retrieved for org {org_id or 'all'}")

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
