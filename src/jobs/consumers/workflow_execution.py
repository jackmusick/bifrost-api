"""
Workflow Execution Consumer

Processes async workflow executions from RabbitMQ queue.
Replaces the Azure Queue trigger version with full API compatibility.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from src.core.pubsub import publish_execution_update, publish_execution_log
from src.jobs.rabbitmq import BaseConsumer

logger = logging.getLogger(__name__)

# Queue name
QUEUE_NAME = "workflow-executions"


class WorkflowExecutionConsumer(BaseConsumer):
    """
    Consumer for workflow execution queue.

    Message format:
    {
        "execution_id": "uuid",
        "workflow_name": "workflow-name",
        "org_id": "ORG:uuid",
        "user_id": "uuid",
        "user_name": "User Name",
        "user_email": "user@example.com",
        "parameters": {},
        "code": "base64-encoded-script" (optional, for inline scripts)
    }
    """

    def __init__(self):
        super().__init__(
            queue_name=QUEUE_NAME,
            prefetch_count=1,  # Process one at a time for resource control
        )

    async def process_message(self, message_data: dict[str, Any]) -> None:
        """Process a workflow execution message."""
        execution_id = message_data.get("execution_id", "")
        org_id = message_data.get("org_id")
        user_id = message_data.get("user_id", "")
        start_time = datetime.utcnow()

        try:
            workflow_name = message_data["workflow_name"]
            code_base64 = message_data.get("code")
            user_name = message_data["user_name"]
            user_email = message_data["user_email"]
            parameters = message_data.get("parameters", {})

            logger.info(
                f"Processing async workflow execution: {workflow_name}",
                extra={
                    "execution_id": execution_id,
                    "workflow_name": workflow_name,
                    "org_id": org_id,
                },
            )

            # Import shared modules for execution
            from shared.context import Caller, Organization
            from shared.discovery import load_workflow
            from shared.engine import ExecutionRequest, execute
            from shared.models import ExecutionStatus

            # Check if execution was already cancelled before we started
            from src.jobs.consumers._helpers import (
                get_execution_status,
                update_execution,
            )

            current_status = await get_execution_status(execution_id, org_id)

            if current_status == ExecutionStatus.CANCELLING.value:
                logger.info(f"Execution {execution_id} was already cancelled before starting")
                await update_execution(
                    execution_id=execution_id,
                    org_id=org_id,
                    user_id=user_id,
                    status=ExecutionStatus.CANCELLED,
                    error_message="Execution was cancelled before it could start",
                    duration_ms=0,
                )
                await publish_execution_update(execution_id, "Cancelled")
                return

            # Update status to RUNNING
            await update_execution(
                execution_id=execution_id,
                org_id=org_id,
                user_id=user_id,
                status=ExecutionStatus.RUNNING,
            )
            await publish_execution_update(execution_id, "Running")

            # Recreate organization context
            org = None
            config = {}

            if org_id:
                from shared.storage import get_organization_async
                from shared.middleware import load_config_for_partition

                org_entity = await get_organization_async(org_id)
                if org_entity:
                    org_uuid = org_entity["RowKey"].split(":", 1)[1]
                    org = Organization(
                        id=org_uuid,
                        name=org_entity["Name"],
                        is_active=org_entity.get("IsActive", True),
                    )
                    config = await load_config_for_partition(org_id)
            else:
                from shared.middleware import load_config_for_partition

                config = await load_config_for_partition("GLOBAL")

            # Create Caller from message
            caller = Caller(user_id=user_id, email=user_email, name=user_name)

            # Determine if this is a script or workflow execution
            is_script = bool(code_base64)

            # Load workflow function and metadata
            workflow_func = None
            metadata = None

            if not is_script:
                try:
                    result = load_workflow(workflow_name)
                    if not result:
                        logger.error(f"Workflow not found: {workflow_name}")
                        duration_ms = int(
                            (datetime.utcnow() - start_time).total_seconds() * 1000
                        )
                        await update_execution(
                            execution_id=execution_id,
                            org_id=org_id,
                            user_id=user_id,
                            status=ExecutionStatus.FAILED,
                            result={
                                "error": "WorkflowNotFound",
                                "message": f"Workflow '{workflow_name}' not found",
                            },
                            duration_ms=duration_ms,
                        )
                        await publish_execution_update(
                            execution_id,
                            "Failed",
                            {"error": f"Workflow '{workflow_name}' not found"},
                        )
                        return

                    workflow_func, metadata = result

                except Exception as e:
                    logger.error(f"Failed to load workflow {workflow_name}: {e}")
                    duration_ms = int(
                        (datetime.utcnow() - start_time).total_seconds() * 1000
                    )
                    await update_execution(
                        execution_id=execution_id,
                        org_id=org_id,
                        user_id=user_id,
                        status=ExecutionStatus.FAILED,
                        result={
                            "error": "WorkflowLoadError",
                            "message": f"Failed to load workflow '{workflow_name}': {str(e)}",
                        },
                        duration_ms=duration_ms,
                    )
                    await publish_execution_update(
                        execution_id, "Failed", {"error": str(e)}
                    )
                    return

            timeout_seconds = metadata.timeout_seconds if metadata else 1800

            # Create pubsub broadcaster adapter for the engine
            class PubSubBroadcaster:
                """Adapter to bridge engine broadcasts to our WebSocket pubsub."""

                def __init__(self, exec_id: str):
                    self.exec_id = exec_id
                    self.enabled = True

                async def broadcast_log(self, level: str, message: str, data: dict = None):
                    await publish_execution_log(self.exec_id, level, message, data)

                def close(self):
                    pass

            broadcaster = PubSubBroadcaster(execution_id)

            # Build execution request
            request = ExecutionRequest(
                execution_id=execution_id,
                caller=caller,
                organization=org,
                config=config,
                func=workflow_func if not is_script else None,
                code=code_base64 if is_script else None,
                name=workflow_name,
                tags=["workflow"] if not is_script else [],
                timeout_seconds=timeout_seconds,
                parameters=parameters,
                transient=False,
                is_platform_admin=False,
                broadcaster=broadcaster,
            )

            # Create execution task
            execution_task = asyncio.create_task(execute(request))

            # Monitoring loop for cancellation and timeout
            check_interval = 1.0

            while not execution_task.done():
                # Check for user-initiated cancellation
                current_status = await get_execution_status(execution_id, org_id)

                if current_status == ExecutionStatus.CANCELLING.value:
                    logger.info(f"Cancellation requested for execution {execution_id}")
                    execution_task.cancel()

                    await update_execution(
                        execution_id=execution_id,
                        org_id=org_id,
                        user_id=user_id,
                        status=ExecutionStatus.CANCELLED,
                        error_message="Execution cancelled by user",
                        duration_ms=int(
                            (datetime.utcnow() - start_time).total_seconds() * 1000
                        ),
                    )
                    await publish_execution_update(execution_id, "Cancelled")
                    return

                # Check for timeout
                elapsed_seconds = (datetime.utcnow() - start_time).total_seconds()
                if elapsed_seconds > timeout_seconds:
                    logger.warning(
                        f"Execution {execution_id} exceeded timeout of {timeout_seconds}s"
                    )
                    execution_task.cancel()

                    await update_execution(
                        execution_id=execution_id,
                        org_id=org_id,
                        user_id=user_id,
                        status=ExecutionStatus.TIMEOUT,
                        error_message=f"Execution exceeded timeout of {timeout_seconds} seconds",
                        error_type="TimeoutError",
                        duration_ms=int(elapsed_seconds * 1000),
                    )
                    await publish_execution_update(execution_id, "Timeout")
                    return

                await asyncio.sleep(check_interval)

            # Execution completed - get result
            result = await execution_task

            # Update execution with result
            await update_execution(
                execution_id=execution_id,
                org_id=org_id,
                user_id=user_id,
                status=result.status,
                result=result.result,
                error_message=result.error_message,
                error_type=result.error_type,
                duration_ms=result.duration_ms,
                logs=result.logs,
                variables=result.variables,
            )

            await publish_execution_update(
                execution_id,
                result.status.value,
                {
                    "result": result.result,
                    "durationMs": result.duration_ms,
                },
            )

            logger.info(
                f"Async workflow execution completed: {workflow_name}",
                extra={
                    "execution_id": execution_id,
                    "status": result.status.value,
                    "duration_ms": result.duration_ms,
                },
            )

        except asyncio.CancelledError:
            logger.info(f"Execution task {execution_id} was cancelled")
            raise

        except Exception as e:
            # Unexpected error
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            from shared.models import ExecutionStatus
            from src.jobs.consumers._helpers import update_execution

            await update_execution(
                execution_id=execution_id,
                org_id=org_id,
                user_id=user_id,
                status=ExecutionStatus.FAILED,
                error_message=str(e),
                error_type=type(e).__name__,
                duration_ms=duration_ms,
            )

            await publish_execution_update(
                execution_id,
                "Failed",
                {"error": str(e), "errorType": type(e).__name__},
            )

            logger.error(
                f"Async workflow execution error: {execution_id}",
                extra={
                    "execution_id": execution_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise
