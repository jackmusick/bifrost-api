"""
Metrics Handlers
Business logic for dashboard metrics and statistics
Extracted from functions/metrics.py for unit testability
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from shared.registry import get_registry
from shared.storage import get_table_service

logger = logging.getLogger(__name__)


def get_reverse_timestamp(dt: datetime) -> int:
    """
    Calculate reverse timestamp for descending order in Table Storage.
    Formula: 9999999999999 - timestamp_in_milliseconds

    Args:
        dt: Datetime object to convert

    Returns:
        Reverse timestamp as integer
    """
    timestamp_ms = int(dt.timestamp() * 1000)
    return 9999999999999 - timestamp_ms


def get_workflow_metadata(registry: Any) -> dict[str, int]:
    """
    Get workflow and data provider counts from registry.

    Args:
        registry: The workflow registry instance

    Returns:
        Dict with workflowCount and dataProviderCount, defaults to 0 on error
    """
    try:
        summary = registry.get_summary()
        return {
            "workflowCount": summary.get("workflows_count", 0),
            "dataProviderCount": summary.get("data_providers_count", 0)
        }
    except Exception as e:
        logger.warning(f"Failed to fetch workflow metadata: {e}")
        return {
            "workflowCount": 0,
            "dataProviderCount": 0
        }


def get_form_count(entities_service: Any) -> int:
    """
    Get count of active forms from Entities table.

    Args:
        entities_service: Table service for Entities table

    Returns:
        Count of active form entities
    """
    try:
        form_entities = list(entities_service.query_entities(
            filter="RowKey ge 'form:' and RowKey lt 'form;' and IsActive eq true"
        ))
        return len(form_entities)
    except Exception as e:
        logger.warning(f"Failed to fetch form count: {e}")
        return 0


def get_execution_statistics(entities_service: Any, days: int = 30) -> dict[str, Any]:
    """
    Get execution statistics for the last N days.

    Args:
        entities_service: Table service for Entities table
        days: Number of days to look back (default 30)

    Returns:
        Dict with execution stats including counts, success rate, duration
    """
    try:
        # Calculate cutoff timestamp
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        reverse_ts_cutoff = get_reverse_timestamp(cutoff_time)

        # Query executions (reverse timestamp provides newest first)
        execution_entities = list(entities_service.query_entities(
            filter=f"RowKey ge 'execution:' and RowKey le 'execution:{reverse_ts_cutoff}_~'",
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
                started_at = entity.get("StartedAt")
                recent_failures.append({
                    "executionId": entity.get("ExecutionId"),
                    "workflowName": entity.get("WorkflowName"),
                    "errorMessage": entity.get("ErrorMessage"),
                    "startedAt": started_at.isoformat() if started_at else None
                })

        # Calculate success rate
        success_count = status_counts.get("Success", 0)
        failed_count = status_counts.get("Failed", 0)
        completed_count = success_count + failed_count

        success_rate = (success_count / completed_count * 100) if completed_count > 0 else 0.0

        # Calculate average duration
        avg_duration_seconds = (total_duration_ms / duration_count / 1000) if duration_count > 0 else 0.0

        return {
            "totalExecutions": total_executions,
            "successCount": success_count,
            "failedCount": failed_count,
            "runningCount": status_counts.get("Running", 0),
            "pendingCount": status_counts.get("Pending", 0),
            "successRate": round(success_rate, 1),
            "avgDurationSeconds": round(avg_duration_seconds, 2),
            "recentFailures": recent_failures
        }
    except Exception as e:
        logger.warning(f"Failed to fetch execution statistics: {e}")
        return {
            "totalExecutions": 0,
            "successCount": 0,
            "failedCount": 0,
            "runningCount": 0,
            "pendingCount": 0,
            "successRate": 0.0,
            "avgDurationSeconds": 0.0,
            "recentFailures": []
        }


def get_dashboard_metrics(context: Any) -> dict[str, Any]:
    """
    Aggregate all dashboard metrics into a single response.

    This is the main handler that orchestrates fetching workflow metadata,
    form counts, and execution statistics.

    Args:
        context: RequestContext with user/org information

    Returns:
        Dict containing aggregated metrics

    Raises:
        Exception: Re-raised exceptions from sub-handlers are caught internally
    """
    try:
        metrics: dict[str, Any] = {}

        # 1. Get workflow and data provider counts
        registry = get_registry()
        metadata = get_workflow_metadata(registry)
        metrics.update(metadata)

        # 2. Get form count
        entities_service = get_table_service("Entities", context)
        metrics["formCount"] = get_form_count(entities_service)

        # 3. Get execution statistics (last 30 days)
        execution_stats = get_execution_statistics(entities_service, days=30)
        metrics["executionStats"] = {
            "totalExecutions": execution_stats["totalExecutions"],
            "successCount": execution_stats["successCount"],
            "failedCount": execution_stats["failedCount"],
            "runningCount": execution_stats["runningCount"],
            "pendingCount": execution_stats["pendingCount"],
            "successRate": execution_stats["successRate"],
            "avgDurationSeconds": execution_stats["avgDurationSeconds"]
        }
        metrics["recentFailures"] = execution_stats["recentFailures"]

        logger.info(f"Dashboard metrics retrieved for user {context.user_id}")
        return metrics

    except Exception as e:
        logger.error(f"Error retrieving dashboard metrics: {str(e)}", exc_info=True)
        raise
