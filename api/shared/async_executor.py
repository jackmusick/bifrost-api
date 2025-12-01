"""
Async Workflow Execution
Handles queueing and execution of long-running workflows
"""

import json
import logging
import os
import uuid
from typing import Any

from azure.storage.queue.aio import QueueServiceClient  # type: ignore[import-untyped]
from azure.storage.queue import TextBase64EncodePolicy  # type: ignore[import-untyped]

from shared.execution_logger import get_execution_logger
from shared.models import ExecutionStatus
from shared.context import ExecutionContext

logger = logging.getLogger(__name__)

QUEUE_NAME = "workflow-executions"


class QueueClientContextManager:
    """Async context manager for Azure Storage Queue client"""

    def __init__(self, connection_str: str):
        self.connection_str = connection_str
        self.queue_service = None
        self.queue_client = None

    async def __aenter__(self):
        """Create and return queue client"""
        self.queue_service = QueueServiceClient.from_connection_string(self.connection_str)

        # Use TextBase64EncodePolicy for proper Azure Functions queue compatibility
        self.queue_client = self.queue_service.get_queue_client(
            QUEUE_NAME,
            message_encode_policy=TextBase64EncodePolicy()
        )

        # Auto-create queue if it doesn't exist
        try:
            await self.queue_client.create_queue()
            logger.info(f"Created queue: {QUEUE_NAME}")
        except Exception as e:
            # Queue might already exist, that's fine
            if "QueueAlreadyExists" not in str(e):
                logger.debug(f"Queue {QUEUE_NAME} status: {e}")

        return self.queue_client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close queue client properly"""
        if self.queue_client:
            await self.queue_client.close()
        return False


def get_queue_client():
    """Get Azure Storage Queue client context manager for workflow executions"""
    connection_str = os.environ.get("AzureWebJobsStorage", "UseDevelopmentStorage=true")
    return QueueClientContextManager(connection_str)


async def enqueue_workflow_execution(
    context: ExecutionContext,
    workflow_name: str,
    parameters: dict[str, Any],
    form_id: str | None = None,
    code_base64: str | None = None
) -> str:
    """
    Enqueue a workflow or script for async execution.

    Creates execution record with status=PENDING, enqueues message to Azure Storage Queue,
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

    # Enqueue message with automatic cleanup
    async with get_queue_client() as queue_client:
        await queue_client.send_message(json.dumps(message))

    logger.info(
        f"Enqueued async workflow execution: {workflow_name}",
        extra={
            "execution_id": execution_id,
            "workflow_name": workflow_name,
            "org_id": context.org_id
        }
    )

    return execution_id
