"""
Workflow Execution Worker V2 - Refactored to use unified engine
Processes async workflow executions from Azure Storage Queue with cancellation support

CANCELLATION BEHAVIOR:
- Cooperative cancellation is implemented using asyncio.CancelledError
- Cancellation only works at 'await' points in async code
- Blocking operations (time.sleep, long computations, synchronous I/O) CANNOT be cancelled
- Workflows should use 'await asyncio.sleep()' instead of 'time.sleep()' for cancellable delays
- Long-running synchronous operations will complete before cancellation takes effect
- If workflow code doesn't have await points, it cannot be cancelled until completion
"""

import asyncio
import json
import logging
from datetime import datetime

import azure.functions as func

from shared.context import Caller, Organization
from shared.engine import ExecutionRequest, execute
from shared.execution_logger import get_execution_logger
from shared.middleware import load_config_for_partition
from shared.models import ExecutionStatus
from shared.registry import get_registry
from shared.repositories.executions import ExecutionRepository
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

        # Check if execution was already cancelled before we started
        exec_repo_check = ExecutionRepository()
        try:
            current_status = await exec_repo_check.get_execution_status(execution_id, org_id)

            if current_status == ExecutionStatus.CANCELLING.value:
                logger.info(f"Execution {execution_id} was already cancelled before starting")

                await exec_logger.update_execution(
                    execution_id=execution_id,
                    org_id=org_id,
                    user_id=user_id,
                    status=ExecutionStatus.CANCELLED,
                    error_message="Execution was cancelled before it could start",
                    duration_ms=0,
                    webpubsub_broadcaster=broadcaster
                )
                return
        finally:
            await exec_repo_check.close()

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

        # Get workflow metadata for timeout
        registry = get_registry()
        metadata = registry.get_function(workflow_name)
        timeout_seconds = metadata.timeout_seconds if metadata else 1800  # Default 30 min

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

        # Create execution task (not awaiting directly - monitoring loop will wait for it)
        execution_task = asyncio.create_task(execute(request))

        # Monitoring loop for cancellation and timeout
        check_interval = 1.0  # Check every second
        execution_repo = ExecutionRepository()

        try:
            while not execution_task.done():
                # Check for user-initiated cancellation
                current_status = await execution_repo.get_execution_status(execution_id, org_id)

                if current_status == ExecutionStatus.CANCELLING.value:
                    logger.info(f"Cancellation requested for execution {execution_id}")
                    execution_task.cancel()

                    await exec_logger.update_execution(
                        execution_id=execution_id,
                        org_id=org_id,
                        user_id=user_id,
                        status=ExecutionStatus.CANCELLED,
                        error_message="Execution cancelled by user",
                        duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                        webpubsub_broadcaster=broadcaster
                    )

                    logger.info(f"Execution {execution_id} cancelled successfully")
                    return

                # Check for timeout
                elapsed_seconds = (datetime.utcnow() - start_time).total_seconds()
                if elapsed_seconds > timeout_seconds:
                    logger.warning(
                        f"Execution {execution_id} exceeded timeout of {timeout_seconds}s"
                    )
                    execution_task.cancel()

                    await exec_logger.update_execution(
                        execution_id=execution_id,
                        org_id=org_id,
                        user_id=user_id,
                        status=ExecutionStatus.TIMEOUT,
                        error_message=f"Execution exceeded timeout of {timeout_seconds} seconds",
                        error_type="TimeoutError",
                        duration_ms=int(elapsed_seconds * 1000),
                        webpubsub_broadcaster=broadcaster
                    )

                    logger.info(f"Execution {execution_id} timed out")
                    return

                # Sleep before next check
                await asyncio.sleep(check_interval)

            # Execution completed normally - get the result
            result = await execution_task

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

        except asyncio.CancelledError:
            # Task was cancelled (either by user or timeout - already handled above)
            logger.info(f"Execution task {execution_id} was cancelled")
            raise

        finally:
            # Ensure repository connections are closed
            await execution_repo.close()

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
