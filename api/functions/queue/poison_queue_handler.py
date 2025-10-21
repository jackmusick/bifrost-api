"""
Poison Queue Handler
Processes messages that failed multiple times and were moved to the poison queue

Has two triggers:
1. Queue trigger - processes messages as they arrive
2. Timer trigger - backup processor that runs every 5 minutes to catch missed messages
"""

import json
import logging

import azure.functions as func
from azure.storage.queue import QueueServiceClient

from shared.execution_logger import get_execution_logger
from shared.models import ExecutionStatus

logger = logging.getLogger(__name__)

# Create blueprint for poison queue handler
bp = func.Blueprint()


async def _process_poison_message(message_data: dict, dequeue_count: int) -> None:
    """
    Shared logic for processing a poison queue message.

    Args:
        message_data: Parsed message content
        dequeue_count: Number of times message was dequeued
    """
    execution_id = message_data.get("execution_id", "unknown")
    workflow_name = message_data.get("workflow_name", "unknown")
    org_id = message_data.get("org_id")
    user_id = message_data.get("user_id", "unknown")

    logger.error(
        f"Poison queue message for workflow: {workflow_name}",
        extra={
            "execution_id": execution_id,
            "workflow_name": workflow_name,
            "org_id": org_id,
            "dequeue_count": dequeue_count,
        }
    )

    # Update execution status to FAILED with poison queue error
    exec_logger = get_execution_logger()
    await exec_logger.update_execution(
        execution_id=execution_id,
        org_id=org_id,
        user_id=user_id,
        status=ExecutionStatus.FAILED,
        error_message=f"Execution failed after {dequeue_count} attempts and was moved to poison queue. This indicates a persistent failure that requires investigation.",
        error_type="PoisonQueueFailure"
    )

    logger.warning(
        f"Updated execution {execution_id} to FAILED status (poison queue)",
        extra={
            "execution_id": execution_id,
            "workflow_name": workflow_name,
            "dequeue_count": dequeue_count
        }
    )


@bp.function_name("workflow_execution_poison_handler")
@bp.queue_trigger(
    arg_name="msg",
    queue_name="workflow-executions-poison",
    connection="AzureWebJobsStorage"
)
async def workflow_execution_poison_handler(msg: func.QueueMessage) -> None:
    """
    Queue trigger: Process poison messages as they arrive.

    This function handles executions that failed to process multiple times:
    1. Logs the failure for monitoring
    2. Updates execution status to FAILED
    3. Records error details for investigation

    These messages are NOT retried - they represent permanent failures.
    """
    try:
        # Parse queue message
        message_body = msg.get_body().decode('utf-8')
        message_data = json.loads(message_body)

        # Process using shared logic
        await _process_poison_message(message_data, msg.dequeue_count)

    except Exception as e:
        # Log error but don't throw - we don't want poison queue handler to fail
        logger.error(
            "Error processing poison queue message (queue trigger)",
            extra={
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )


@bp.function_name("workflow_execution_poison_timer")
@bp.schedule(
    arg_name="timer",
    schedule="0 */5 * * * *",  # Every 5 minutes
    run_on_startup=False
)
async def workflow_execution_poison_timer(timer: func.TimerRequest) -> None:
    """
    Timer trigger: Backup processor that runs every 5 minutes.

    Ensures poison queue messages are processed even if queue trigger misses them.
    This provides redundancy for critical failure handling.
    """
    import os

    logger.info("Poison queue timer triggered - checking for unprocessed messages")

    try:
        # Get queue client
        connection_str = os.environ.get("AzureWebJobsStorage", "UseDevelopmentStorage=true")
        queue_service = QueueServiceClient.from_connection_string(connection_str)
        queue_client = queue_service.get_queue_client("workflow-executions-poison")

        processed = 0
        failed = 0

        # Process up to 32 messages per timer execution (Azure Queue batch limit)
        messages = queue_client.receive_messages(max_messages=32, visibility_timeout=300)

        for msg in messages:
            try:
                # Parse message
                message_data = json.loads(msg.content)

                # Process using shared logic
                await _process_poison_message(message_data, msg.dequeue_count)

                # Delete message after successful processing
                queue_client.delete_message(msg)
                processed += 1

            except Exception as e:
                logger.error(
                    "Error processing poison message in timer",
                    extra={"error": str(e)},
                    exc_info=True
                )
                # Delete message anyway to prevent infinite loop
                queue_client.delete_message(msg)
                failed += 1

        if processed > 0 or failed > 0:
            logger.warning(
                "Poison queue timer processed messages",
                extra={
                    "processed": processed,
                    "failed": failed,
                    "total": processed + failed
                }
            )
        else:
            logger.info("Poison queue timer found no messages to process")

    except Exception as e:
        logger.error(
            "Error in poison queue timer",
            extra={"error": str(e)},
            exc_info=True
        )
