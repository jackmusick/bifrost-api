"""
Execution Cleanup Handlers
Business logic for stuck execution cleanup operations
"""

import json
import logging

import azure.functions as func

from shared.execution_logger import ExecutionLogger
from shared.models import ExecutionStatus
from shared.repositories.executions import ExecutionRepository
from shared.request_context import RequestContext

logger = logging.getLogger(__name__)


async def get_stuck_executions_handler(
    req: func.HttpRequest,
    context: RequestContext
) -> func.HttpResponse:
    """
    Get list of stuck executions.

    Returns executions that are stuck in Pending or Running status
    for longer than the timeout threshold.
    """
    # Get execution repository with context for proper org scoping
    execution_repo = ExecutionRepository(context)

    # Get stuck executions
    stuck_executions = execution_repo.get_stuck_executions(
        pending_timeout_minutes=10,
        running_timeout_minutes=30
    )

    # Convert to dict for JSON response
    executions_data = [
        {
            "executionId": ex.executionId,
            "workflowName": ex.workflowName,
            "status": ex.status.value,
            "executedBy": ex.executedBy,
            "executedByName": ex.executedByName,
            "startedAt": ex.startedAt.isoformat() if ex.startedAt else None,
        }
        for ex in stuck_executions
    ]

    logger.info(
        f"Found {len(stuck_executions)} stuck executions",
        extra={"user_id": context.user_id}
    )

    response_data = {
        "executions": executions_data,
        "count": len(executions_data)
    }

    return func.HttpResponse(
        body=json.dumps(response_data),
        status_code=200,
        mimetype="application/json"
    )


async def trigger_cleanup_handler(
    req: func.HttpRequest,
    context: RequestContext
) -> func.HttpResponse:
    """
    Manually trigger cleanup of stuck executions.

    Finds and times out executions stuck in Pending or Running status.
    """
    # Get execution logger with context for proper org scoping
    exec_logger = ExecutionLogger(context)
    execution_repo = ExecutionRepository(context)

    # Get stuck executions
    stuck_executions = execution_repo.get_stuck_executions(
        pending_timeout_minutes=10,
        running_timeout_minutes=30
    )

    logger.info(
        f"Manual cleanup triggered: {len(stuck_executions)} executions to process",
        extra={
            "user_id": context.user_id,
            "count": len(stuck_executions)
        }
    )

    pending_count = 0
    running_count = 0
    failed_count = 0

    for execution in stuck_executions:
        try:
            # Determine timeout reason
            if execution.status == ExecutionStatus.PENDING:
                timeout_reason = "Stuck in PENDING status for 10+ minutes (manual cleanup)"
                pending_count += 1
            elif execution.status == ExecutionStatus.RUNNING:
                timeout_reason = "Stuck in RUNNING status for 30+ minutes (manual cleanup)"
                running_count += 1
            else:
                continue

            logger.info(
                f"Timing out execution: {execution.executionId}",
                extra={
                    "execution_id": execution.executionId,
                    "workflow_name": execution.workflowName,
                    "status": execution.status.value,
                    "org_id": execution.orgId,  # Log org_id for debugging
                }
            )

            # Update execution to TIMEOUT status
            exec_logger.update_execution(
                execution_id=execution.executionId,
                org_id=execution.orgId,  # Get org_id from execution (retrieved from status index)
                user_id=execution.executedBy,
                status=ExecutionStatus.TIMEOUT,
                error_message=timeout_reason
            )

        except Exception as e:
            logger.error(
                f"Error cleaning up execution {execution.executionId}: {e}",
                extra={"error": str(e)},
                exc_info=True
            )
            failed_count += 1

    result = {
        "cleaned": pending_count + running_count,
        "pending": pending_count,
        "running": running_count,
        "failed": failed_count
    }

    logger.info(
        f"Manual cleanup completed: {result['cleaned']} executions timed out",
        extra={
            "user_id": context.user_id,
            "result": result
        }
    )

    return func.HttpResponse(
        body=json.dumps(result),
        status_code=200,
        mimetype="application/json"
    )
