"""
CRON Scheduler

Processes scheduled workflows based on their CRON expressions using APScheduler.

Runs every 5 minutes to check for workflows that need to be executed.
"""

import logging
import uuid
from datetime import datetime
from typing import Any

from croniter import croniter

from src.core.database import get_db_context
from shared.rabbitmq import publish_message
from src.repositories.schedules import ScheduleRepository
from shared.workflows.cron_parser import is_cron_expression_valid

logger = logging.getLogger(__name__)


async def process_scheduled_workflows() -> dict[str, Any]:
    """
    Process all scheduled workflows from the schedules table.

    Checks each enabled schedule and enqueues execution if the
    next run time has passed.

    Returns:
        Summary of processing results
    """
    logger.info("Schedule processor started")

    results = {
        "total_schedules": 0,
        "executed": 0,
        "updated": 0,
        "errors": [],
    }

    try:
        # Query scheduled records from database
        async with get_db_context() as db:
            # Global scope (None org_id) to get all organization-wide schedules
            schedule_repo = ScheduleRepository(db, org_id=None)
            db_schedules = await schedule_repo.get_due_schedules()

        results["total_schedules"] = len(db_schedules)
        logger.info(f"Found {len(db_schedules)} scheduled workflows")

        now = datetime.utcnow()

        for schedule in db_schedules:
            try:
                workflow_name = schedule.workflow_name
                cron_expression = schedule.cron_expression

                # Validate CRON expression
                if not cron_expression or not is_cron_expression_valid(cron_expression):
                    logger.warning(
                        f"Invalid CRON expression for schedule {schedule.id}: {cron_expression}"
                    )
                    results["errors"].append({
                        "schedule_id": str(schedule.id),
                        "workflow_name": workflow_name,
                        "error": f"Invalid CRON expression: {cron_expression}",
                    })
                    continue

                # Check if schedule interval is too frequent
                try:
                    cron = croniter(cron_expression, now)
                    first_run = cron.get_next(datetime)
                    second_run = cron.get_next(datetime)
                    interval_seconds = (second_run - first_run).total_seconds()

                    if interval_seconds < 300:  # Less than 5 minutes
                        logger.warning(
                            f"Schedule interval for {workflow_name} is {interval_seconds}s (< 5 minutes)"
                        )
                except Exception as e:
                    logger.error(f"Failed to validate schedule interval for {workflow_name}: {e}")

                # Check if it's time to execute
                # If last_run_at is None or enough time has passed since last run
                cron = croniter(cron_expression, now)
                last_run = cron.get_prev(datetime)

                # If last run was less than 1 minute ago, skip (already triggered)
                if (now - last_run).total_seconds() < 60:
                    continue

                logger.info(f"Executing scheduled workflow: {workflow_name}")

                # Generate execution ID
                execution_id = str(uuid.uuid4())

                # Enqueue workflow execution with schedule parameters
                await publish_message(
                    queue_name="workflow-executions",
                    message={
                        "execution_id": execution_id,
                        "workflow_name": workflow_name,
                        "org_id": str(schedule.organization_id) if schedule.organization_id else None,
                        "user_id": "system:scheduler",
                        "user_name": "Scheduled Execution",
                        "user_email": "system@scheduler",
                        "parameters": schedule.parameters or {},
                    },
                )

                logger.info(
                    "Enqueued scheduled workflow execution",
                    extra={
                        "schedule_id": str(schedule.id),
                        "workflow_name": workflow_name,
                        "execution_id": execution_id,
                    },
                )

                # Update last_run_at timestamp
                async with get_db_context() as db:
                    repo = ScheduleRepository(db, org_id=schedule.organization_id)
                    await repo.update_last_run(schedule.id, now)

                results["executed"] += 1

            except Exception as workflow_error:
                error_info = {
                    "schedule_id": str(schedule.id),
                    "workflow_name": schedule.workflow_name,
                    "error": str(workflow_error),
                }
                results["errors"].append(error_info)
                logger.error(
                    "Error processing scheduled workflow",
                    extra=error_info,
                    exc_info=True,
                )

        logger.info(
            f"Schedule processor completed: "
            f"Total={results['total_schedules']}, "
            f"Executed={results['executed']}, "
            f"Errors={len(results['errors'])}"
        )

    except Exception as e:
        logger.error(f"Schedule processor failed: {str(e)}", exc_info=True)
        results["errors"].append({"error": str(e)})

    return results
