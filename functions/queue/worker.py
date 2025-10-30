"""
Workflow Execution Worker V2 - Refactored to use unified engine
Processes async workflow executions from Azure Storage Queue
"""

import json
import logging
from datetime import datetime

import azure.functions as func

from shared.context import Caller, Organization
from shared.engine import ExecutionRequest, execute
from shared.execution_logger import get_execution_logger
from shared.middleware import load_config_for_partition
from shared.models import ExecutionStatus
from shared.storage import get_organization_async

logger = logging.getLogger(__name__)

# Create blueprint for worker function
bp = func.Blueprint()


@bp.function_name("workflow_execution_worker")
@bp.queue_trigger(
    arg_name="msg",
    queue_name="workflow-executions",
    connection="AzureWebJobsStorage"
)
async def workflow_execution_worker(msg: func.QueueMessage) -> None:
    """
    Process workflow execution messages from queue.

    Message format:
    {
        "execution_id": "uuid",
        "workflow_name": "workflow-name",
        "org_id": "ORG:uuid",
        "user_id": "uuid",
        "user_name": "User Name",
        "user_email": "user@example.com",
        "parameters": {}
    }
    """
    logger.info("Workflow execution worker invoked")
    try:
        # Parse queue message
        message_body = msg.get_body().decode('utf-8')
        logger.info(f"Message body: {message_body}")
        message_data = json.loads(message_body)
        logger.info(f"Parsed message data: {message_data}")

        await handle_workflow_execution(message_data)

    except Exception as e:
        logger.error(
            f"Queue worker error: {str(e)}",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "message_data": message_data if 'message_data' in locals() else "N/A"
            },
            exc_info=True
        )
        # Re-raise to let Azure Functions handle retry/poison queue
        raise


async def handle_workflow_execution(message_data: dict) -> None:
    """
    Handle workflow execution message.

    Args:
        message_data: Queue message data containing execution details
    """
    execution_id: str = ""
    org_id: str | None = None
    user_id: str = ""
    start_time = datetime.utcnow()

    exec_logger = get_execution_logger()

    try:

        execution_id = message_data["execution_id"]
        workflow_name = message_data["workflow_name"]
        org_id = message_data["org_id"]
        user_id = message_data["user_id"]
        user_name = message_data["user_name"]
        user_email = message_data["user_email"]
        parameters = message_data["parameters"]

        logger.info(
            f"Processing async workflow execution: {workflow_name}",
            extra={
                "execution_id": execution_id,
                "workflow_name": workflow_name,
                "org_id": org_id
            }
        )

        # Initialize Web PubSub broadcaster for real-time updates (used throughout)
        from shared.webpubsub_broadcaster import WebPubSubBroadcaster
        broadcaster = WebPubSubBroadcaster()

        # Update status to RUNNING - will broadcast to history page
        await exec_logger.update_execution(
            execution_id=execution_id,
            org_id=org_id,
            user_id=user_id,
            status=ExecutionStatus.RUNNING,
            webpubsub_broadcaster=broadcaster
        )

        # Recreate organization context from queue message
        org = None
        config = {}

        if org_id:
            org_entity = await get_organization_async(org_id)
            if org_entity:
                org_uuid = org_entity['RowKey'].split(':', 1)[1]
                org = Organization(
                    id=org_uuid,
                    name=org_entity['Name'],
                    is_active=org_entity.get('IsActive', True)
                )
                config = await load_config_for_partition(org_id)
        else:
            # Load GLOBAL configs for platform admin context
            config = await load_config_for_partition("GLOBAL")

        # Create Caller from queue message
        caller = Caller(
            user_id=user_id,
            email=user_email,
            name=user_name
        )

        # Hot-reload: Re-discover workspace modules
        from function_app import discover_workspace_modules
        discover_workspace_modules()

        # Build execution request for engine (reuse broadcaster initialized earlier)
        request = ExecutionRequest(
            execution_id=execution_id,
            caller=caller,
            organization=org,
            config=config,
            name=workflow_name,  # Always a workflow name for async execution
            parameters=parameters,
            transient=False,  # Async executions always write to DB
            is_platform_admin=False,  # Used for API response filtering, not execution behavior
            broadcaster=broadcaster  # Pass Web PubSub broadcaster for real-time log streaming
        )

        # Execute via unified engine
        result = await execute(request)

        # Update execution with result
        # NOTE: Broadcasts to both execution details and history are handled by update_execution
        await exec_logger.update_execution(
            execution_id=execution_id,
            org_id=org_id,
            user_id=user_id,
            status=result.status,
            result=result.result,
            error_message=result.error_message,
            error_type=result.error_type,
            duration_ms=result.duration_ms,
            integration_calls=result.integration_calls,
            logs=result.logs if result.logs else None,
            variables=result.variables if result.variables else None,
            webpubsub_broadcaster=broadcaster
        )

        logger.info(
            f"Async workflow execution completed: {workflow_name}",
            extra={
                "execution_id": execution_id,
                "status": result.status.value,
                "duration_ms": result.duration_ms
            }
        )

    except Exception as e:
        # Unexpected error
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        await exec_logger.update_execution(
            execution_id=execution_id,
            org_id=org_id,
            user_id=user_id,
            status=ExecutionStatus.FAILED,
            error_message=str(e),
            error_type=type(e).__name__,
            duration_ms=duration_ms
        )

        logger.error(
            f"Async workflow execution error: {execution_id}",
            extra={
                "execution_id": execution_id,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
