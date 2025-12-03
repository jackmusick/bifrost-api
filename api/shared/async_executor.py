"""
Async Workflow Execution
Handles queueing and execution of long-running workflows via RabbitMQ

For sync execution (sync=True):
- Caller provides execution_id
- Worker pushes result to Redis
- Caller waits on Redis BLPOP
"""

import logging
import uuid
from typing import Any

from shared.execution_logger import get_execution_logger
from src.models.schemas import ExecutionStatus
from shared.context import ExecutionContext

logger = logging.getLogger(__name__)

QUEUE_NAME = "workflow-executions"


async def enqueue_workflow_execution(
    context: ExecutionContext,
    workflow_name: str,
    parameters: dict[str, Any],
    form_id: str | None = None,
    code_base64: str | None = None,
    execution_id: str | None = None,
    sync: bool = False,
) -> str:
    """
    Enqueue a workflow or script for async execution.

    Creates execution record with status=PENDING, enqueues message to RabbitMQ,
    and returns execution ID immediately (<500ms).

    Args:
        context: Request context with org scope and user info
        workflow_name: Name of workflow to execute (or script name for inline scripts)
        parameters: Workflow/script parameters
        form_id: Optional form ID if triggered by form
        code_base64: Optional base64-encoded inline script code
        execution_id: Optional pre-generated execution ID (for sync execution)
        sync: If True, worker will push result to Redis for caller to BLPOP

    Returns:
        execution_id: UUID of the queued execution
    """
    from src.jobs.rabbitmq import publish_message

    # Generate or use provided execution ID
    # If execution_id is provided (sync execution), record already exists
    skip_record_creation = execution_id is not None
    if execution_id is None:
        execution_id = str(uuid.uuid4())

    # Create execution record with PENDING status (unless already exists)
    if not skip_record_creation:
        exec_logger = get_execution_logger()

        # Initialize Web PubSub broadcaster for real-time updates
        from shared.webpubsub_broadcaster import WebPubSubBroadcaster
        broadcaster = WebPubSubBroadcaster()

        await exec_logger.create_execution(
            execution_id=execution_id,
            org_id=context.org_id,
            user_id=context.user_id,
            user_name=context.name,
            workflow_name=workflow_name,
            input_data=parameters,
            form_id=form_id,
            webpubsub_broadcaster=broadcaster
        )

        # Update status to PENDING (queued) - will broadcast to history page
        await exec_logger.update_execution(
            execution_id=execution_id,
            org_id=context.org_id,
            user_id=context.user_id,
            status=ExecutionStatus.PENDING,
            webpubsub_broadcaster=broadcaster
        )

    # Prepare queue message
    message = {
        "execution_id": execution_id,
        "workflow_name": workflow_name,
        "org_id": context.org_id,
        "user_id": context.user_id,
        "user_name": context.name,
        "user_email": context.email,
        "parameters": parameters,
        "form_id": form_id,
        "code": code_base64,  # Optional: for inline scripts
        "sync": sync,  # If True, worker pushes result to Redis
    }

    # Enqueue message via RabbitMQ
    await publish_message(QUEUE_NAME, message)

    logger.info(
        f"Enqueued async workflow execution: {workflow_name}",
        extra={
            "execution_id": execution_id,
            "workflow_name": workflow_name,
            "org_id": context.org_id
        }
    )

    return execution_id
