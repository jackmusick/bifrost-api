"""
Async Workflow Execution
Handles queueing and execution of long-running workflows
"""

import json
import logging
import os
import uuid
from typing import Any

from azure.storage.queue import QueueServiceClient, TextBase64EncodePolicy  # type: ignore[import-untyped]

from shared.execution_logger import get_execution_logger
from shared.models import ExecutionStatus
from shared.request_context import RequestContext

logger = logging.getLogger(__name__)

QUEUE_NAME = "workflow-executions"


def get_queue_client():
    """Get Azure Storage Queue client for workflow executions"""
    connection_str = os.environ.get("AzureWebJobsStorage", "UseDevelopmentStorage=true")
    queue_service = QueueServiceClient.from_connection_string(connection_str)

    # Use TextBase64EncodePolicy for proper Azure Functions queue compatibility
    queue_client = queue_service.get_queue_client(
        QUEUE_NAME,
        message_encode_policy=TextBase64EncodePolicy()
    )

    # Auto-create queue if it doesn't exist
    try:
        queue_client.create_queue()
        logger.info(f"Created queue: {QUEUE_NAME}")
    except Exception as e:
        # Queue might already exist, that's fine
        if "QueueAlreadyExists" not in str(e):
            logger.debug(f"Queue {QUEUE_NAME} status: {e}")

    return queue_client


async def enqueue_workflow_execution(
    context: RequestContext,
    workflow_name: str,
    parameters: dict[str, Any],
    form_id: str | None = None
) -> str:
    """
    Enqueue a workflow for async execution.

    Creates execution record with status=PENDING, enqueues message to Azure Storage Queue,
    and returns execution ID immediately (<500ms).

    Args:
        context: Request context with org scope and user info
        workflow_name: Name of workflow to execute
        parameters: Workflow parameters
        form_id: Optional form ID if triggered by form

    Returns:
        execution_id: UUID of the queued execution
    """
    # Generate execution ID
    execution_id = str(uuid.uuid4())

    # Create execution record with PENDING status
    exec_logger = get_execution_logger()
    await exec_logger.create_execution(
        execution_id=execution_id,
        org_id=context.org_id,
        user_id=context.user_id,
        user_name=context.name,
        workflow_name=workflow_name,
        input_data=parameters,
        form_id=form_id
    )

    # Update status to PENDING (queued)
    await exec_logger.update_execution(
        execution_id=execution_id,
        org_id=context.org_id,
        user_id=context.user_id,
        status=ExecutionStatus.PENDING
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
        "form_id": form_id
    }

    # Enqueue message
    queue_client = get_queue_client()
    queue_client.send_message(json.dumps(message))

    logger.info(
        f"Enqueued async workflow execution: {workflow_name}",
        extra={
            "execution_id": execution_id,
            "workflow_name": workflow_name,
            "org_id": context.org_id
        }
    )

    return execution_id
