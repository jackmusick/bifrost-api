"""
Manual Poison Queue Cleanup Script
Processes stuck messages in the poison queue and updates executions to FAILED status
"""

import asyncio
import json
import os

from azure.storage.queue import QueueServiceClient

# Set up environment
os.environ['AzureWebJobsStorage'] = 'DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;'

from shared.execution_logger import get_execution_logger
from shared.models import ExecutionStatus


async def process_poison_queue():
    """Process all messages in the poison queue"""
    conn_str = os.environ['AzureWebJobsStorage']
    queue_service = QueueServiceClient.from_connection_string(conn_str)
    queue_client = queue_service.get_queue_client('workflow-executions-poison')

    exec_logger = get_execution_logger()

    processed = 0
    failed = 0

    print("Processing poison queue messages...")

    # Process messages one at a time
    while True:
        messages = queue_client.receive_messages(max_messages=1, visibility_timeout=30)
        message_list = list(messages)

        if not message_list:
            break

        msg = message_list[0]

        try:
            # Parse message
            message_data = json.loads(msg.content)

            execution_id = message_data.get("execution_id", "unknown")
            workflow_name = message_data.get("workflow_name", "unknown")
            org_id = message_data.get("org_id")
            user_id = message_data.get("user_id", "unknown")

            print(f"\nProcessing execution: {execution_id}")
            print(f"  Workflow: {workflow_name}")
            print(f"  Dequeue count: {msg.dequeue_count}")

            # Update execution to FAILED
            await exec_logger.update_execution(
                execution_id=execution_id,
                org_id=org_id,
                user_id=user_id,
                status=ExecutionStatus.FAILED,
                error_message=f"Execution failed after {msg.dequeue_count} attempts and was moved to poison queue",
                error_type="PoisonQueueFailure"
            )

            # Delete message from poison queue
            queue_client.delete_message(msg)

            print(f"  ✓ Marked as FAILED and removed from poison queue")
            processed += 1

        except Exception as e:
            print(f"  ✗ Error processing message: {e}")
            # Delete the message anyway to prevent infinite loop
            queue_client.delete_message(msg)
            failed += 1

    print(f"\n" + "="*60)
    print(f"Processed: {processed} executions")
    print(f"Failed: {failed} executions")
    print(f"="*60)


if __name__ == "__main__":
    asyncio.run(process_poison_queue())
