"""
Async Workflow Execution
Handles queueing and execution of long-running workflows via RabbitMQ
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
    code_base64: str | None = None
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

    Returns:
        execution_id: UUID of the queued execution
    """
    from src.jobs.rabbitmq import publish_message

    # Generate execution ID
    execution_id = str(uuid.uuid4())

    # Create execution record with PENDING status
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
        "code": code_base64  # Optional: for inline scripts
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
