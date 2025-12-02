"""
Schedules Router

Manages scheduled workflow execution.
Allows listing and triggering scheduled workflows.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from src.models.schemas import ScheduleInfo, SchedulesListResponse, ProcessSchedulesResponse
from shared.discovery import scan_all_workflows
from src.core.auth import Context, CurrentSuperuser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/schedules", tags=["Schedules"])


# =============================================================================
# HTTP Endpoints
# =============================================================================


@router.get(
    "",
    response_model=SchedulesListResponse,
    summary="List scheduled workflows",
    description="List all scheduled workflows (Platform admin only)",
)
async def list_schedules(
    ctx: Context,
    user: CurrentSuperuser,
) -> SchedulesListResponse:
    """
    List all scheduled workflows.

    Returns a list of workflows that have cron schedules configured.
    """
    try:
        # Try to import cron_parser, but don't fail if croniter isn't installed
        try:
            from shared.workflows.cron_parser import cron_to_human_readable
            get_human_readable = cron_to_human_readable
        except ImportError:
            get_human_readable = lambda x: x  # noqa: E731

        workflows = scan_all_workflows()

        schedules = []
        for workflow in workflows:
            if hasattr(workflow, 'schedule') and workflow.schedule:
                human_readable = get_human_readable(workflow.schedule) or workflow.schedule
                schedule = ScheduleInfo(
                    workflow_name=workflow.name,
                    workflow_description=getattr(workflow, 'description', workflow.name),
                    cron_expression=workflow.schedule,
                    human_readable=human_readable,
                    next_run_at=None,
                    last_run_at=None,
                    last_execution_id=None,
                    execution_count=0,
                    enabled=True,
                    validation_status=None,
                    validation_message=None,
                    is_overdue=False,
                )
                schedules.append(schedule)

        logger.info(f"Listed {len(schedules)} scheduled workflows")
        return SchedulesListResponse(schedules=schedules, total_count=len(schedules))

    except Exception as e:
        logger.error(f"Error listing schedules: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list schedules",
        )


@router.post(
    "/{workflow_name}/trigger",
    summary="Manually trigger a scheduled workflow",
    description="Manually trigger execution of a scheduled workflow (Platform admin only)",
)
async def trigger_schedule(
    workflow_name: str,
    ctx: Context,
    user: CurrentSuperuser,
) -> dict:
    """
    Manually trigger a scheduled workflow.

    Args:
        workflow_name: Name of the scheduled workflow to trigger

    Returns:
        Execution response
    """
    try:
        from shared.handlers.workflows_logic import execute_workflow_logic
        from shared.context import ExecutionContext as SharedContext, Organization
        from uuid import uuid4

        # Create organization object if org_id is set
        org = None
        if ctx.org_id:
            org = Organization(id=str(ctx.org_id), name="", is_active=True)

        # Create shared context
        shared_ctx = SharedContext(
            user_id=str(ctx.user.user_id),
            name=ctx.user.name,
            email=ctx.user.email,
            scope=str(ctx.org_id) if ctx.org_id else "GLOBAL",
            organization=org,
            is_platform_admin=ctx.user.is_superuser,
            is_function_key=False,
            execution_id=str(uuid4()),
        )

        # Execute the workflow
        result = await execute_workflow_logic(
            context=shared_ctx,
            workflow_name=workflow_name,
            input_data={},
            transient=False,
        )

        logger.info(f"Manually triggered workflow: {workflow_name} (execution_id: {result.execution_id})")

        return {
            "message": f"Scheduled workflow '{workflow_name}' triggered",
            "execution_id": result.execution_id,
            "status": result.status.value,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error triggering schedule {workflow_name}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger schedule",
        )


@router.post(
    "/process",
    response_model=ProcessSchedulesResponse,
    summary="Process all due schedules",
    description="Process and trigger all due scheduled workflows (Timer trigger only)",
)
async def process_schedules(
    ctx: Context,
    user: CurrentSuperuser,
) -> ProcessSchedulesResponse:
    """
    Process all due scheduled workflows.

    This is typically called by a timer trigger (e.g., every minute).
    It checks which schedules are due and triggers their workflows.

    Note: In production, this would be called by an Azure Timer Trigger
    or similar scheduled job, not directly by users.
    """
    try:
        from uuid import uuid4
        from croniter import croniter
        from shared.workflows.cron_parser import is_cron_expression_valid
        from shared.handlers.workflows_logic import execute_workflow_logic
        from shared.context import ExecutionContext as SharedContext, Organization

        workflows = scan_all_workflows()
        now = datetime.utcnow()
        processed = 0
        triggered = 0

        for workflow in workflows:
            if not hasattr(workflow, 'schedule') or not workflow.schedule:
                continue

            processed += 1

            # Check if schedule is due
            try:
                if is_cron_expression_valid(workflow.schedule):
                    cron = croniter(workflow.schedule, now)
                    last_run = cron.get_prev(datetime)

                    # If last run was less than 1 minute ago, it's probably been triggered
                    if (now - last_run).total_seconds() < 60:
                        continue

                    # Create shared context and trigger
                    org = None
                    if ctx.org_id:
                        org = Organization(id=str(ctx.org_id), name="", is_active=True)
                    shared_ctx = SharedContext(
                        user_id=str(ctx.user.user_id),
                        name=ctx.user.name,
                        email=ctx.user.email,
                        scope=str(ctx.org_id) if ctx.org_id else "GLOBAL",
                        organization=org,
                        is_platform_admin=ctx.user.is_superuser,
                        is_function_key=False,
                        execution_id=str(uuid4()),
                    )

                    await execute_workflow_logic(
                        context=shared_ctx,
                        workflow_name=workflow.name,
                        input_data={},
                        transient=False,
                    )
                    triggered += 1
                    logger.info(f"Triggered scheduled workflow: {workflow.name}")
            except Exception as e:
                logger.error(f"Error processing schedule {workflow.name}: {str(e)}")

        logger.info(f"Processed schedules: {processed} checked, {triggered} triggered")

        return ProcessSchedulesResponse(
            total=processed,
            due=triggered,
            executed=triggered,
            failed=0,
            errors=[],
        )

    except Exception as e:
        logger.error(f"Error processing schedules: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process schedules",
        )
