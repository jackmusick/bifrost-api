"""
Workflow Execution Worker
Processes async workflow executions from Azure Storage Queue
"""

import json
import logging
from datetime import datetime

import azure.functions as func

from shared.context import Caller, Organization, OrganizationContext
from shared.error_handling import WorkflowError
from shared.execution_logger import get_execution_logger
from shared.middleware import load_config_for_partition
from shared.models import ExecutionStatus
from shared.registry import get_registry
from shared.storage import get_organization
from shared.workflow_endpoint_utils import (
    coerce_parameter_types,
    separate_workflow_params,
)

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
    Process async workflow execution from queue.

    Loads execution context, updates status to RUNNING, executes workflow,
    stores result, and updates status to SUCCESS/FAILED.
    """
    execution_id: str = ""
    org_id: str | None = None
    user_id: str = ""
    start_time = datetime.utcnow()

    try:
        # Parse queue message
        message_body = msg.get_body().decode('utf-8')
        message_data = json.loads(message_body)

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

        # Get execution logger
        exec_logger = get_execution_logger()

        # Update status to RUNNING
        await exec_logger.update_execution(
            execution_id=execution_id,
            org_id=org_id,
            user_id=user_id,
            status=ExecutionStatus.RUNNING
        )

        # Recreate organization context from queue message
        org = None
        config = {}

        if org_id:
            # Load organization and config
            org_entity = get_organization(org_id)

            if org_entity:
                # Create Organization object
                # RowKey is in format "org:{uuid}", extract the UUID
                org_uuid = org_entity['RowKey'].split(':', 1)[1]
                org = Organization(
                    org_id=org_uuid,
                    name=org_entity['Name'],
                    is_active=org_entity.get('IsActive', True)
                )

                # Load organization config
                config = load_config_for_partition(org_id)
        else:
            # Load GLOBAL configs for platform admin context
            config = load_config_for_partition("GLOBAL")

        # Create Caller from queue message
        caller = Caller(
            user_id=user_id,
            email=user_email,
            name=user_name
        )

        # Create execution ID for context
        context = OrganizationContext(
            org=org,
            config=config,
            caller=caller,
            execution_id=execution_id
        )

        # Hot-reload: Re-discover workspace modules
        from function_app import discover_workspace_modules
        discover_workspace_modules()

        # Get workflow from registry
        registry = get_registry()
        workflow_metadata = registry.get_workflow(workflow_name)

        if not workflow_metadata:
            raise WorkflowError(
                error_type="WorkflowNotFound",
                message=f"Workflow '{workflow_name}' not found in registry"
            )

        # Apply type coercion to input data
        param_metadata = {param.name: param for param in workflow_metadata.parameters}
        coerced_data = coerce_parameter_types(parameters, param_metadata)

        # Separate workflow parameters from extra variables
        workflow_params, extra_variables = separate_workflow_params(
            coerced_data, workflow_metadata
        )

        # Inject extra variables into context
        for key, value in extra_variables.items():
            context.set_variable(key, value)

        # Execute workflow
        workflow_func = workflow_metadata.function
        result = await workflow_func(context, **workflow_params)

        # Calculate duration
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Update execution with SUCCESS
        await exec_logger.update_execution(
            execution_id=execution_id,
            org_id=org_id,
            user_id=user_id,
            status=ExecutionStatus.SUCCESS,
            result=result,
            duration_ms=duration_ms,
            state_snapshots=context._state_snapshots,
            integration_calls=context._integration_calls,
            logs=context._logs,
            variables=context._variables
        )

        logger.info(
            f"Async workflow execution completed: {workflow_name}",
            extra={
                "execution_id": execution_id,
                "status": "Success",
                "duration_ms": duration_ms
            }
        )

    except WorkflowError as e:
        # Expected workflow error
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

        logger.warning(
            f"Async workflow execution failed: {workflow_name}",
            extra={
                "execution_id": execution_id,
                "error": str(e),
                "error_type": type(e).__name__
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
            f"Async workflow execution error: {workflow_name}",
            extra={
                "execution_id": execution_id,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
