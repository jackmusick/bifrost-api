"""
Schedules Handler
Business logic for retrieving scheduled workflows
"""

import logging
from datetime import datetime, timezone

import azure.functions as func
from croniter import croniter

from shared.async_executor import enqueue_workflow_execution
from shared.models import ExecutionStatus, ProcessSchedulesResponse, ScheduleInfo, SchedulesListResponse, WorkflowExecutionResponse
from shared.registry import get_registry
from shared.request_context import RequestContext
from shared.storage import TableStorageService
from shared.workflows.cron_parser import calculate_next_run, cron_to_human_readable, is_cron_expression_valid

logger = logging.getLogger(__name__)


async def process_due_schedules_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Process all schedules that are currently due to run.

    This is the server-side implementation of "Run Scheduled Jobs Now".
    It replicates the logic from schedule_processor timer but only processes
    schedules where next_run_at <= now.

    Returns:
        JSON response with execution results
    """
    logger.info("Processing all due schedules (manual trigger)")

    config_service = TableStorageService("Config")
    registry = get_registry()
    context: RequestContext = req.context

    # Get all workflows from registry
    all_workflows = registry.get_all_workflows()
    scheduled_workflows = [w for w in all_workflows if w.schedule]

    now = datetime.utcnow()
    results = {
        "total_schedules": len(scheduled_workflows),
        "due_schedules": 0,
        "executed": 0,
        "errors": []
    }

    # Process each scheduled workflow
    for workflow_meta in scheduled_workflows:
        try:
            workflow_name = workflow_meta.name
            cron_expression = workflow_meta.schedule

            # Validate CRON expression using comprehensive validation
            if not is_cron_expression_valid(cron_expression):
                logger.warning(
                    f"Skipping schedule with invalid CRON expression: {workflow_name} - {cron_expression}"
                )
                results["errors"].append({
                    "workflow_name": workflow_name,
                    "error": f"Invalid CRON expression: {cron_expression}"
                })
                continue

            # Get schedule state
            row_key = f"schedule:{workflow_name}"
            schedule_state = config_service.get_entity("GLOBAL", row_key)

            if not schedule_state:
                # Not initialized yet, skip
                continue

            # Check if it's due
            next_run_at = datetime.fromisoformat(schedule_state.get("NextRunAt", now.isoformat()))

            if next_run_at > now:
                # Not due yet
                continue

            results["due_schedules"] += 1
            logger.info(
                f"Processing due schedule: {workflow_name}",
                extra={
                    "workflow_name": workflow_name,
                    "next_run_at": next_run_at.isoformat(),
                    "now": now.isoformat()
                }
            )

            try:
                # Enqueue execution
                execution_id = await enqueue_workflow_execution(
                    context=context,
                    workflow_name=workflow_name,
                    parameters={},
                    form_id=None
                )

                logger.info(
                    f"Enqueued due schedule: {workflow_name}",
                    extra={
                        "workflow_name": workflow_name,
                        "execution_id": execution_id
                    }
                )

                # Update schedule state
                next_run_at = calculate_next_run(cron_expression, now)
                schedule_state["LastRunAt"] = now.isoformat()
                schedule_state["LastExecutionId"] = execution_id
                schedule_state["ExecutionCount"] = int(
                    schedule_state.get("ExecutionCount", 0)
                ) + 1
                schedule_state["NextRunAt"] = next_run_at.isoformat()
                config_service.upsert_entity(schedule_state)

                results["executed"] += 1

            except Exception as exec_error:
                error_info = {
                    "workflow_name": workflow_name,
                    "error": str(exec_error)
                }
                results["errors"].append(error_info)
                logger.error(
                    f"Failed to execute due schedule: {workflow_name}",
                    extra=error_info,
                    exc_info=True
                )

        except Exception as workflow_error:
            error_info = {
                "workflow_name": getattr(workflow_meta, "name", "unknown"),
                "error": str(workflow_error)
            }
            results["errors"].append(error_info)
            logger.error(
                "Error processing workflow schedule",
                extra=error_info,
                exc_info=True
            )

    logger.info(
        f"Processed due schedules: Total={results['total_schedules']}, "
        f"Due={results['due_schedules']}, Executed={results['executed']}, "
        f"Errors={len(results['errors'])}"
    )

    response = ProcessSchedulesResponse(
        total=results['total_schedules'],
        due=results['due_schedules'],
        executed=results['executed'],
        failed=len(results['errors']),
        errors=results['errors']
    )

    return func.HttpResponse(
        body=response.model_dump_json(),
        status_code=200,
        mimetype="application/json"
    )


async def get_schedules_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get all scheduled workflows with their CRON information and state.

    Combines registry metadata with storage state to provide complete schedule information.

    Returns:
        JSON response with list of schedules and total count
    """
    logger.info("Retrieving scheduled workflows")

    config_service = TableStorageService("Config")
    registry = get_registry()

    # Get all workflows from registry
    all_workflows = registry.get_all_workflows()
    scheduled_workflows = [w for w in all_workflows if w.schedule]

    logger.info(f"Found {len(scheduled_workflows)} scheduled workflows in registry")

    schedules_list: list[ScheduleInfo] = []

    for workflow_meta in scheduled_workflows:
        try:
            workflow_name = workflow_meta.name
            workflow_description = workflow_meta.description
            cron_expression = workflow_meta.schedule

            # Get schedule state from storage
            row_key = f"schedule:{workflow_name}"
            schedule_state = config_service.get_entity("GLOBAL", row_key)

            # Build schedule info from metadata and storage state
            next_run_at = None
            last_run_at = None
            last_execution_id = None
            execution_count = 0

            if schedule_state:
                # Parse LastRunAt timestamp from storage as UTC
                # Storage contains naive datetimes that represent UTC
                if "LastRunAt" in schedule_state:
                    try:
                        last_run_at = datetime.fromisoformat(schedule_state["LastRunAt"]).replace(tzinfo=timezone.utc)
                    except (ValueError, TypeError):
                        pass

                last_execution_id = schedule_state.get("LastExecutionId")
                execution_count = int(schedule_state.get("ExecutionCount", 0))

                # Recalculate NextRunAt to ensure it's rounded to timer intervals
                # Don't trust the stored value as it may be from before rounding was added
                if "NextRunAt" in schedule_state:
                    try:
                        datetime.fromisoformat(schedule_state["NextRunAt"])
                        # Recalculate from the CRON expression to ensure proper rounding
                        next_run_at = calculate_next_run(cron_expression, datetime.utcnow()).replace(tzinfo=timezone.utc)
                    except (ValueError, TypeError):
                        pass

            # Generate human-readable description
            human_readable = cron_to_human_readable(cron_expression)

            # Validate CRON expression and check for warnings
            validation_status = "valid"
            validation_message = None
            is_overdue = False

            # Check comprehensive CRON validation
            if not is_cron_expression_valid(cron_expression):
                validation_status = "error"
                validation_message = "Invalid CRON expression"
                # Clear next run for invalid schedules - they should never run
                next_run_at = None
            else:
                # Check if schedule is too frequent (< 5 minutes)
                # This is a warning - the schedule will still run but may not meet expectations
                try:
                    now = datetime.utcnow()
                    cron = croniter(cron_expression, now)
                    first_run = cron.get_next(datetime)
                    second_run = cron.get_next(datetime)
                    interval_seconds = (second_run - first_run).total_seconds()

                    if interval_seconds < 300:  # Less than 5 minutes
                        validation_status = "warning"
                        minutes = int(interval_seconds / 60)
                        validation_message = f"Schedule runs every {minutes} minute{'s' if minutes != 1 else ''} (< 5 min recommended)"
                except Exception as e:
                    logger.warning(f"Could not determine schedule interval for {workflow_name}: {e}")
                    # Keep as valid if we can't determine interval

                # Calculate overdue status (only for valid schedules)
                # A schedule is only "overdue" if it's past due by more than 6 minutes
                # This accounts for:
                # - Timer runs every 5 minutes
                # - Execution startup time
                # - Queue processing delays
                if next_run_at:
                    now_with_tz = datetime.utcnow().replace(tzinfo=timezone.utc)
                    overdue_buffer_seconds = 360  # 6 minutes
                    time_past_due = (now_with_tz - next_run_at).total_seconds()
                    is_overdue = time_past_due > overdue_buffer_seconds

            schedule_info = ScheduleInfo(
                workflowName=workflow_name,
                workflowDescription=workflow_description,
                cronExpression=cron_expression,
                humanReadable=human_readable,
                nextRunAt=next_run_at,
                lastRunAt=last_run_at,
                lastExecutionId=last_execution_id,
                executionCount=execution_count,
                enabled=True,
                validationStatus=validation_status,
                validationMessage=validation_message,
                isOverdue=is_overdue
            )

            schedules_list.append(schedule_info)

        except Exception as e:
            logger.error(
                f"Error retrieving schedule for workflow: {getattr(workflow_meta, 'name', 'unknown')}",
                extra={"error": str(e)},
                exc_info=True
            )
            # Continue processing other schedules

    # Sort by workflow name
    schedules_list.sort(key=lambda s: s.workflowName)

    # Create response
    response = SchedulesListResponse(
        schedules=schedules_list,
        totalCount=len(schedules_list)
    )

    logger.info(f"Returning {len(schedules_list)} scheduled workflows")

    return func.HttpResponse(
        response.model_dump_json(),
        status_code=200,
        mimetype="application/json"
    )


async def trigger_schedule_handler(req: func.HttpRequest, workflow_name: str) -> func.HttpResponse:
    """
    Manually trigger a scheduled workflow to run now.

    This mimics what the schedule processor does:
    1. Validates the workflow exists and has a schedule
    2. Enqueues the execution via async_executor
    3. Updates the schedule state (last_run_at, execution_count, next_run_at)

    Args:
        req: HTTP request with context
        workflow_name: Name of the scheduled workflow to trigger

    Returns:
        JSON response with execution ID
    """
    logger.info(f"Manually triggering scheduled workflow: {workflow_name}")

    config_service = TableStorageService("Config")
    registry = get_registry()

    # Get workflow from registry
    workflow_meta = None
    for w in registry.get_all_workflows():
        if w.name == workflow_name:
            workflow_meta = w
            break

    if not workflow_meta:
        return func.HttpResponse(
            body=f'{{"error": "Workflow not found: {workflow_name}"}}',
            status_code=404,
            mimetype="application/json"
        )

    if not workflow_meta.schedule:
        return func.HttpResponse(
            body=f'{{"error": "Workflow {workflow_name} is not scheduled"}}',
            status_code=400,
            mimetype="application/json"
        )

    # Validate CRON expression using comprehensive validation
    if not is_cron_expression_valid(workflow_meta.schedule):
        return func.HttpResponse(
            body=f'{{"error": "Workflow {workflow_name} has invalid CRON expression: {workflow_meta.schedule}"}}',
            status_code=400,
            mimetype="application/json"
        )

    # Get request context from decorator
    context: RequestContext = req.context

    try:
        # Enqueue workflow execution (same as schedule processor)
        execution_id = await enqueue_workflow_execution(
            context=context,
            workflow_name=workflow_name,
            parameters={},
            form_id=None
        )

        logger.info(
            f"Manually triggered workflow: {workflow_name}",
            extra={
                "workflow_name": workflow_name,
                "execution_id": execution_id,
                "triggered_by": context.user_id
            }
        )

        # Update schedule state (same as schedule processor)
        row_key = f"schedule:{workflow_name}"
        schedule_state = config_service.get_entity("GLOBAL", row_key)

        if schedule_state:
            now = datetime.utcnow()
            next_run_at = calculate_next_run(workflow_meta.schedule, now)

            schedule_state["LastRunAt"] = now.isoformat()
            schedule_state["LastExecutionId"] = execution_id
            schedule_state["ExecutionCount"] = int(
                schedule_state.get("ExecutionCount", 0)
            ) + 1
            schedule_state["NextRunAt"] = next_run_at.isoformat()
            config_service.upsert_entity(schedule_state)

        # Return execution response
        response = WorkflowExecutionResponse(
            executionId=execution_id,
            status=ExecutionStatus.PENDING,
        )

        return func.HttpResponse(
            body=response.model_dump_json(),
            status_code=202,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(
            f"Failed to trigger scheduled workflow: {workflow_name}",
            extra={"error": str(e)},
            exc_info=True
        )
        return func.HttpResponse(
            body=f'{{"error": "Failed to trigger workflow: {str(e)}"}}',
            status_code=500,
            mimetype="application/json"
        )
