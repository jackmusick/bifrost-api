"""
Metrics Router

Dashboard metrics and statistics.
Provides overview of platform usage and system health.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func

from shared.discovery import scan_all_workflows, scan_all_forms
from src.models.schemas import DashboardMetricsResponse, ExecutionStats, RecentFailure
from src.core.auth import Context, CurrentActiveUser
from src.models import Execution as ExecutionModel
from src.models.enums import ExecutionStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/metrics", tags=["Metrics"])


# =============================================================================
# HTTP Endpoints
# =============================================================================


@router.get(
    "",
    response_model=DashboardMetricsResponse,
    summary="Get dashboard metrics",
    description="Get platform metrics for the dashboard",
)
async def get_metrics(
    ctx: Context,
    user: CurrentActiveUser,
) -> DashboardMetricsResponse:
    """
    Get dashboard metrics.

    Returns:
        Dashboard metrics including workflow/form counts, execution stats, etc.
    """
    try:
        # Scan workflows and forms
        workflows = list(scan_all_workflows())
        forms = list(scan_all_forms())

        # Query execution statistics from database
        datetime.utcnow()

        # Total executions
        total_query = select(func.count(ExecutionModel.id))
        total_result = await ctx.db.execute(total_query)
        total_executions = total_result.scalar() or 0

        # Success count
        success_query = select(func.count(ExecutionModel.id)).where(
            ExecutionModel.status == ExecutionStatus.SUCCESS.value,
        )
        success_result = await ctx.db.execute(success_query)
        success_count = success_result.scalar() or 0

        # Failed count
        failed_query = select(func.count(ExecutionModel.id)).where(
            ExecutionModel.status == ExecutionStatus.FAILED.value,
        )
        failed_result = await ctx.db.execute(failed_query)
        failed_count = failed_result.scalar() or 0

        # Running count
        running_query = select(func.count(ExecutionModel.id)).where(
            ExecutionModel.status == ExecutionStatus.RUNNING.value,
        )
        running_result = await ctx.db.execute(running_query)
        running_count = running_result.scalar() or 0

        # Pending count
        pending_query = select(func.count(ExecutionModel.id)).where(
            ExecutionModel.status == ExecutionStatus.PENDING.value,
        )
        pending_result = await ctx.db.execute(pending_query)
        pending_count = pending_result.scalar() or 0

        # Success rate
        success_rate = (success_count / total_executions * 100) if total_executions > 0 else 0.0

        # Average execution time (successful executions, in seconds)
        avg_time_query = select(func.avg(ExecutionModel.duration_ms)).where(
            ExecutionModel.status == ExecutionStatus.SUCCESS.value,
        )
        avg_time_result = await ctx.db.execute(avg_time_query)
        avg_duration_ms = avg_time_result.scalar() or 0
        avg_duration_seconds = float(avg_duration_ms) / 1000.0 if avg_duration_ms else 0.0

        # Get recent failures
        failures_query = (
            select(ExecutionModel)
            .where(
                ExecutionModel.status == ExecutionStatus.FAILED.value,
            )
            .order_by(ExecutionModel.started_at.desc())
            .limit(5)
        )
        failures_result = await ctx.db.execute(failures_query)
        failures_models = failures_result.scalars().all()

        recent_failures = [
            RecentFailure(
                execution_id=str(f.id),
                workflow_name=f.workflow_name or "Unknown",
                error_message=f.error_message,
                started_at=f.started_at.isoformat() if f.started_at else None,
            )
            for f in failures_models
        ]

        # Execution statistics
        execution_stats = ExecutionStats(
            total_executions=total_executions,
            success_count=success_count,
            failed_count=failed_count,
            running_count=running_count,
            pending_count=pending_count,
            success_rate=success_rate,
            avg_duration_seconds=avg_duration_seconds,
        )

        # Create response
        response = DashboardMetricsResponse(
            workflow_count=len(workflows),
            form_count=len(forms),
            data_provider_count=0,  # Would scan data providers if available
            execution_stats=execution_stats,
            recent_failures=recent_failures,
        )

        logger.info(
            f"Dashboard metrics: {len(workflows)} workflows, {len(forms)} forms, "
            f"{total_executions} total executions"
        )

        return response

    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get metrics",
        )
