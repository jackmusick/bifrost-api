"""
Execution Cleanup Timer
Cleans up stuck executions that remain in PENDING or RUNNING status for too long
"""

import logging
from datetime import datetime

import azure.functions as func

from shared.execution_logger import get_execution_logger
from shared.models import ExecutionStatus
from shared.repositories.executions import ExecutionRepository

logger = logging.getLogger(__name__)

# Create blueprint for cleanup timer
bp = func.Blueprint()

# Timeout thresholds
PENDING_TIMEOUT_MINUTES = 10  # If PENDING for 10+ minutes, it's stuck in queue
RUNNING_TIMEOUT_MINUTES = 30  # If RUNNING for 30+ minutes, worker likely crashed


@bp.function_name("execution_cleanup")
@bp.timer_trigger(schedule="0 */5 * * * *", arg_name="timer", run_on_startup=False)
async def execution_cleanup(timer: func.TimerRequest) -> None:
    """
    Clean up stuck executions every 5 minutes.

    Finds executions that have been stuck in PENDING or RUNNING status
    for longer than the timeout threshold and marks them as TIMEOUT.

    PENDING timeout (10 min): Likely indicates queue processing issues
    RUNNING timeout (30 min): Likely indicates worker crash or hang
    """
    logger.info("Starting execution cleanup timer")

    try:
        # Get execution logger (uses ExecutionRepository internally)
        exec_logger = get_execution_logger()

        # Get execution repository
        execution_repo = ExecutionRepository()

        # Get all stuck executions
        stuck_executions = execution_repo.get_stuck_executions(
            pending_timeout_minutes=PENDING_TIMEOUT_MINUTES,
            running_timeout_minutes=RUNNING_TIMEOUT_MINUTES
        )

        logger.info(f"Found {len(stuck_executions)} stuck executions to clean up")

        pending_count = 0
        running_count = 0

        for execution in stuck_executions:
            try:
                # Determine timeout reason based on status
                if execution.status == ExecutionStatus.PENDING:
                    timeout_reason = f"Stuck in PENDING status for {PENDING_TIMEOUT_MINUTES}+ minutes. Likely queue processing issue or worker not running."
                    pending_count += 1
                elif execution.status == ExecutionStatus.RUNNING:
                    timeout_reason = f"Stuck in RUNNING status for {RUNNING_TIMEOUT_MINUTES}+ minutes. Likely worker crash or workflow hang."
                    running_count += 1
                else:
                    continue

                logger.warning(
                    f"Timing out stuck execution: {execution.executionId}",
                    extra={
                        "execution_id": execution.executionId,
                        "workflow_name": execution.workflowName,
                        "status": execution.status.value,
                        "started_at": execution.startedAt.isoformat() if execution.startedAt else None,
                        "timeout_reason": timeout_reason
                    }
                )

                # Extract org_id from execution
                # WorkflowExecution has orgId field from the status index
                org_id = execution.orgId

                # Create log entry for timeout
                timeout_log = [
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "level": "error",
                        "message": timeout_reason,
                        "data": {
                            "timeout_type": "automatic_cleanup",
                            "original_status": execution.status.value,
                            "timeout_threshold_minutes": PENDING_TIMEOUT_MINUTES if execution.status == ExecutionStatus.PENDING else RUNNING_TIMEOUT_MINUTES
                        }
                    }
                ]

                # Update execution to TIMEOUT status with log
                exec_logger.update_execution(
                    execution_id=execution.executionId,
                    org_id=org_id,
                    user_id=execution.executedBy,
                    status=ExecutionStatus.TIMEOUT,
                    error_message=timeout_reason,
                    error_type="ExecutionTimeout",
                    logs=timeout_log
                )

            except Exception as e:
                logger.error(
                    f"Error processing execution cleanup for {execution.executionId}",
                    extra={"error": str(e)},
                    exc_info=True
                )
                # Continue processing other executions

        logger.info(
            "Execution cleanup completed",
            extra={
                "pending_timeouts": pending_count,
                "running_timeouts": running_count,
                "total_cleaned": pending_count + running_count
            }
        )

    except Exception as e:
        logger.error(
            "Error in execution cleanup timer",
            extra={"error": str(e)},
            exc_info=True
        )
