"""
Read-Only Schedules API
Returns list of scheduled workflows with their CRON expressions and next run times
"""

import json
import logging
from datetime import datetime

import azure.functions as func

from shared.decorators import require_platform_admin, with_request_context
from shared.handlers.schedules_handlers import get_schedules_handler, process_due_schedules_handler, trigger_schedule_handler
from shared.models import (
    CronValidationRequest,
    CronValidationResponse,
    ProcessSchedulesResponse,
    SchedulesListResponse,
    WorkflowExecutionResponse,
)
from shared.openapi_decorators import openapi_endpoint
from shared.workflows.cron_parser import (
    cron_to_human_readable,
    validate_cron_expression,
)

logger = logging.getLogger(__name__)

# Create blueprint for schedules endpoints
bp = func.Blueprint()


@bp.route(route="schedules", methods=["GET"])
@bp.function_name("get_schedules")
@openapi_endpoint(
    path="/schedules",
    method="GET",
    summary="Get all scheduled workflows",
    description="Get list of all workflows with CRON schedules, next run times, and execution history (Platform admin only)",
    tags=["Schedules"],
    response_model=SchedulesListResponse
)
@with_request_context
@require_platform_admin
async def get_schedules(req: func.HttpRequest) -> func.HttpResponse:
    """Get all scheduled workflows with CRON information and next run times"""
    return await get_schedules_handler(req)


@bp.route(route="schedules/validate", methods=["POST"])
@bp.function_name("validate_cron_expression")
@openapi_endpoint(
    path="/schedules/validate",
    method="POST",
    summary="Validate CRON expression",
    description="Test a CRON expression and return validation results with next run times",
    tags=["Schedules"],
    request_model=CronValidationRequest,
    response_model=CronValidationResponse
)
async def validate_cron_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Validate CRON expression and calculate next run times

    POST /api/schedules/validate
    Body: {"expression": "0 9 * * *"}

    Returns validation status, human-readable description, next 5 runs, interval
    """
    try:
        # Parse request body
        body = req.get_json()
        expression = body.get("expression", "").strip()

        if not expression:
            return func.HttpResponse(
                body=json.dumps({"error": "Expression is required"}),
                status_code=400,
                mimetype="application/json",
            )

        from croniter import croniter

        # Validate CRON syntax
        is_valid = validate_cron_expression(expression)

        if not is_valid:
            response = CronValidationResponse(
                valid=False,
                humanReadable="Invalid CRON expression",
                error="Invalid CRON syntax. Use 5 fields: minute hour day month dayofweek",
                nextRuns=None,
                intervalSeconds=None,
                warning=None,
            )
            return func.HttpResponse(
                body=response.model_dump_json(),
                status_code=200,
                mimetype="application/json",
            )

        # Calculate next runs
        now = datetime.utcnow()
        cron = croniter(expression, now)
        next_runs = []

        for _ in range(5):
            next_run = cron.get_next(datetime)
            next_runs.append(next_run.isoformat() + "Z")

        # Calculate interval between first two runs
        cron_interval = croniter(expression, now)
        first_run = cron_interval.get_next(datetime)
        second_run = cron_interval.get_next(datetime)
        interval_seconds = int((second_run - first_run).total_seconds())

        # Check if too frequent
        warning = None
        if interval_seconds < 300:
            minutes = interval_seconds / 60
            warning = f"Runs every {minutes:.0f} minute{'s' if minutes != 1 else ''} (< 5 min recommended)"

        # Get human-readable description
        human_readable = cron_to_human_readable(expression)

        response = CronValidationResponse(
            valid=True,
            humanReadable=human_readable,
            nextRuns=next_runs,
            intervalSeconds=interval_seconds,
            warning=warning,
            error=None,
        )

        return func.HttpResponse(
            body=response.model_dump_json(),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Error validating CRON expression: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json",
        )


@bp.route(route="schedules/process", methods=["POST"])
@bp.function_name("process_due_schedules")
@openapi_endpoint(
    path="/schedules/process",
    method="POST",
    summary="Process all due schedules now",
    description="Manually trigger execution of all schedules that are currently due (server determines which schedules are due)",
    tags=["Schedules"],
    response_model=ProcessSchedulesResponse
)
@with_request_context
@require_platform_admin
async def process_due_schedules(req: func.HttpRequest) -> func.HttpResponse:
    """
    Process all due schedules - server-side determination of what's due.

    This replicates the schedule_processor timer logic but only runs schedules
    where next_run_at <= now.
    """
    return await process_due_schedules_handler(req)


@bp.route(route="schedules/{workflow_name}/trigger", methods=["POST"])
@bp.function_name("trigger_schedule")
@openapi_endpoint(
    path="/schedules/{workflow_name}/trigger",
    method="POST",
    summary="Trigger scheduled workflow now",
    description="Manually trigger a scheduled workflow execution (queues it like a normal scheduled run)",
    tags=["Schedules"],
    response_model=WorkflowExecutionResponse,
    path_params={
        "workflow_name": {
            "description": "Workflow name (snake_case)",
            "schema": {"type": "string", "pattern": "^[a-z0-9_]+$"},
            "required": True
        }
    }
)
@with_request_context
@require_platform_admin
async def trigger_schedule(req: func.HttpRequest) -> func.HttpResponse:
    """
    Manually trigger a scheduled workflow to run now.

    This enqueues the workflow execution just like the scheduled timer does,
    providing a real test of the scheduling system.
    """
    workflow_name = req.route_params.get("workflow_name")
    if workflow_name is None:
        return func.HttpResponse(
            body=json.dumps({"error": "workflow_name is required"}),
            status_code=400,
            mimetype="application/json",
        )
    return await trigger_schedule_handler(req, workflow_name)
