"""
Metrics Router

Dashboard metrics and statistics.
Provides overview of platform usage and system health.
"""

import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func, case, literal_column

from shared.models import DashboardMetricsResponse, ExecutionStats, RecentFailure
from src.core.auth import Context, CurrentActiveUser
from src.models import Execution as ExecutionModel, Workflow, Form, DataProvider
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
        # Single query for all entity counts using subqueries
        counts_query = select(
            select(func.count(Workflow.id))
            .where(Workflow.is_active.is_(True))
            .correlate(None)
            .scalar_subquery()
            .label("workflow_count"),
            select(func.count(Form.id))
            .where(Form.is_active.is_(True))
            .correlate(None)
            .scalar_subquery()
            .label("form_count"),
            select(func.count(DataProvider.id))
            .where(DataProvider.is_active.is_(True))
            .correlate(None)
            .scalar_subquery()
            .label("provider_count"),
        )
        counts_result = await ctx.db.execute(counts_query)
        counts_row = counts_result.one()
        workflow_count = counts_row.workflow_count or 0
        form_count = counts_row.form_count or 0
        provider_count = counts_row.provider_count or 0

        # Single query for all execution stats using conditional aggregation
        exec_stats_query = select(
            func.count(ExecutionModel.id).label("total"),
            func.sum(
                case(
                    (ExecutionModel.status == ExecutionStatus.SUCCESS.value, 1),
                    else_=0,
                )
            ).label("success_count"),
            func.sum(
                case(
                    (ExecutionModel.status == ExecutionStatus.FAILED.value, 1),
                    else_=0,
                )
            ).label("failed_count"),
            func.sum(
                case(
                    (ExecutionModel.status == ExecutionStatus.RUNNING.value, 1),
                    else_=0,
                )
            ).label("running_count"),
            func.sum(
                case(
                    (ExecutionModel.status == ExecutionStatus.PENDING.value, 1),
                    else_=0,
                )
            ).label("pending_count"),
            func.avg(
                case(
                    (ExecutionModel.status == ExecutionStatus.SUCCESS.value, ExecutionModel.duration_ms),
                    else_=literal_column("NULL"),
                )
            ).label("avg_duration_ms"),
        )
        exec_result = await ctx.db.execute(exec_stats_query)
        exec_row = exec_result.one()

        total_executions = exec_row.total or 0
        success_count = exec_row.success_count or 0
        failed_count = exec_row.failed_count or 0
        running_count = exec_row.running_count or 0
        pending_count = exec_row.pending_count or 0
        avg_duration_ms = exec_row.avg_duration_ms or 0

        success_rate = (success_count / total_executions * 100) if total_executions > 0 else 0.0
        avg_duration_seconds = float(avg_duration_ms) / 1000.0 if avg_duration_ms else 0.0

        # Get recent failures (separate query - needs full rows)
        failures_query = (
            select(
                ExecutionModel.id,
                ExecutionModel.workflow_name,
                ExecutionModel.error_message,
                ExecutionModel.started_at,
            )
            .where(ExecutionModel.status == ExecutionStatus.FAILED.value)
            .order_by(ExecutionModel.started_at.desc())
            .limit(5)
        )
        failures_result = await ctx.db.execute(failures_query)
        failures_rows = failures_result.all()

        recent_failures = [
            RecentFailure(
                execution_id=str(f.id),
                workflow_name=f.workflow_name or "Unknown",
                error_message=f.error_message,
                started_at=f.started_at.isoformat() if f.started_at else None,
            )
            for f in failures_rows
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
            workflow_count=workflow_count,
            form_count=form_count,
            data_provider_count=provider_count,
            execution_stats=execution_stats,
            recent_failures=recent_failures,
        )

        logger.info(
            f"Dashboard metrics: {workflow_count} workflows, {form_count} forms, "
            f"{provider_count} providers, {total_executions} total executions"
        )

        return response

    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get metrics",
        )
