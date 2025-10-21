"""
CRON Schedule Processor Timer
Scheduled job that triggers workflows based on their CRON schedules every 5 minutes
"""

import logging
from datetime import datetime

import azure.functions as func

from croniter import croniter

from shared.async_executor import enqueue_workflow_execution
from shared.registry import get_registry
from shared.request_context import RequestContext
from shared.storage import TableStorageService
from shared.workflows.cron_parser import calculate_next_run, is_cron_expression_valid, validate_cron_expression

logger = logging.getLogger(__name__)

# Create blueprint for timer function
bp = func.Blueprint()


@bp.function_name("schedule_processor")
@bp.timer_trigger(schedule="0 */5 * * * *", arg_name="timer", run_on_startup=False)
async def schedule_processor(timer: func.TimerRequest) -> None:
    """
    Timer trigger that runs every 5 minutes to process scheduled workflows.

    Schedule: "0 */5 * * * *" = Every 5 minutes at second 0

    Process:
    1. Hot-reload workspace to get latest workflows
    2. Query all workflows with schedule parameter
    3. For each scheduled workflow:
       - Initialize state if not exists
       - Check if CRON expression changed
       - If next_run_at <= now: Execute via queue
       - Update last_run_at and next_run_at
       - Increment execution_count
    """
    start_time = datetime.utcnow()
    logger.info(f"Schedule processor started at {start_time.isoformat()}")

    config_service = TableStorageService("Config")
    results = {
        "total_schedules": 0,
        "executed": 0,
        "updated": 0,
        "errors": []
    }

    try:
        # Hot-reload workspace to discover any new workflows with schedules
        from function_app import discover_workspace_modules
        discover_workspace_modules()

        # Get all workflows from registry
        registry = get_registry()
        all_workflows = registry.get_all_workflows()
        scheduled_workflows = [w for w in all_workflows if w.schedule]

        results["total_schedules"] = len(scheduled_workflows)
        logger.info(f"Found {len(scheduled_workflows)} scheduled workflows")

        now = datetime.utcnow()

        # Process each scheduled workflow
        for workflow_meta in scheduled_workflows:
            try:
                workflow_name = workflow_meta.name
                workflow_description = workflow_meta.description
                cron_expression = workflow_meta.schedule

                # Validate CRON expression using comprehensive validation
                if not is_cron_expression_valid(cron_expression):
                    logger.warning(
                        f"Invalid CRON expression for workflow {workflow_name}: {cron_expression}. "
                        f"Skipping schedule processing."
                    )
                    results["errors"].append({
                        "workflow_name": workflow_name,
                        "error": f"Invalid CRON expression: {cron_expression}"
                    })

                    # Delete existing schedule state if it exists (clean up old invalid schedules)
                    row_key = f"schedule:{workflow_name}"
                    existing_schedule = config_service.get_entity("GLOBAL", row_key)
                    if existing_schedule:
                        logger.info(f"Removing schedule state for {workflow_name} due to invalid CRON expression")
                        config_service.delete_entity("GLOBAL", row_key)

                    continue

                # Check if schedule interval is too frequent (< 5 minutes)
                try:
                    cron = croniter(cron_expression, now)
                    first_run = cron.get_next(datetime)
                    second_run = cron.get_next(datetime)
                    interval_seconds = (second_run - first_run).total_seconds()

                    if interval_seconds < 300:  # Less than 5 minutes
                        logger.warning(
                            f"Schedule interval for {workflow_name} is {interval_seconds}s (< 5 minutes). "
                            f"This may cause excessive executions. Expression: {cron_expression}"
                        )
                        results["errors"].append({
                            "workflow_name": workflow_name,
                            "error": f"Schedule interval ({int(interval_seconds)}s) is less than 5 minutes"
                        })
                        # Continue to create schedule but log warning
                except Exception as e:
                    logger.error(f"Failed to validate schedule interval for {workflow_name}: {e}")

                # Get or initialize schedule state in Config table
                row_key = f"schedule:{workflow_name}"
                schedule_state = config_service.get_entity("GLOBAL", row_key)

                if not schedule_state:
                    # Initialize new schedule
                    logger.info(f"Initializing schedule for workflow: {workflow_name}")
                    next_run_at = calculate_next_run(cron_expression, now)

                    schedule_entity = {
                        "PartitionKey": "GLOBAL",
                        "RowKey": row_key,
                        "WorkflowName": workflow_description,
                        "CronExpression": cron_expression,
                        "NextRunAt": next_run_at.isoformat(),
                        "LastRunAt": None,
                        "LastExecutionId": None,
                        "ExecutionCount": 0,
                        "CreatedAt": now.isoformat()
                    }
                    config_service.upsert_entity(schedule_entity)
                    results["updated"] += 1
                    continue

                # Check if workflow description changed
                stored_description = schedule_state.get("WorkflowName", "")
                stored_cron = schedule_state.get("CronExpression", "")

                if stored_description != workflow_description or stored_cron != cron_expression:
                    logger.info(
                        f"Schedule metadata changed for {workflow_name}: "
                        f"description '{stored_description}' -> '{workflow_description}', "
                        f"cron '{stored_cron}' -> '{cron_expression}'"
                    )
                    # Recalculate next run if CRON changed
                    if stored_cron != cron_expression:
                        next_run_at = calculate_next_run(cron_expression, now)
                    else:
                        next_run_at = datetime.fromisoformat(
                            schedule_state.get("NextRunAt", now.isoformat())
                        )

                    schedule_state["WorkflowName"] = workflow_description
                    schedule_state["CronExpression"] = cron_expression
                    schedule_state["NextRunAt"] = next_run_at.isoformat()
                    config_service.upsert_entity(schedule_state)
                    results["updated"] += 1

                # Check if it's time to execute
                next_run_at = datetime.fromisoformat(schedule_state.get("NextRunAt", now.isoformat()))

                if next_run_at <= now:
                    logger.info(
                        f"Executing scheduled workflow: {workflow_name}",
                        extra={
                            "workflow_name": workflow_name,
                            "cron_expression": cron_expression,
                            "next_run_at": next_run_at.isoformat()
                        }
                    )

                    # Create system context for scheduled execution
                    try:
                        # Create system request context with GLOBAL scope
                        context = RequestContext(
                            org_id=None,  # System/global context
                            user_id="system:scheduler",
                            name="Scheduled Execution",
                            email="system@scheduler",
                            is_platform_admin=True,
                            is_function_key=True
                        )

                        # Enqueue workflow execution
                        execution_id = await enqueue_workflow_execution(
                            context=context,
                            workflow_name=workflow_name,
                            parameters={},
                            form_id=None
                        )

                        logger.info(
                            "Enqueued scheduled workflow execution",
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
                            f"Failed to enqueue scheduled workflow: {workflow_name}",
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
                    "Error processing scheduled workflow",
                    extra=error_info,
                    exc_info=True
                )

        # Calculate duration
        end_time = datetime.utcnow()
        duration_seconds = (end_time - start_time).total_seconds()

        # Log summary
        logger.info(
            f"Schedule processor completed in {duration_seconds:.2f}s: "
            f"Total={results['total_schedules']}, "
            f"Executed={results['executed']}, "
            f"Updated={results['updated']}, "
            f"Errors={len(results['errors'])}"
        )

    except Exception as e:
        logger.error(f"Schedule processor failed: {str(e)}", exc_info=True)
