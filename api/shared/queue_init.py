"""
Azure Storage Queue Initialization
Ensures queues exist before Azure Functions tries to bind to them

This module initializes all required queues during function app startup
to prevent binding failures when queues don't exist yet.
"""

import logging
import os

from azure.storage.queue import QueueServiceClient

logger = logging.getLogger(__name__)

# Define all required queues
REQUIRED_QUEUES = [
    "workflow-executions",
    "workflow-executions-poison"  # Poison queue for failed messages
]


def init_queues(connection_string: str | None = None) -> dict:
    """
    Initialize all required Azure Storage Queues.

    Called during function app startup to ensure queues exist before
    Azure Functions tries to bind queue triggers to them.

    Args:
        connection_string: Azure Storage connection string
                          Defaults to AzureWebJobsStorage env var
                          Falls back to UseDevelopmentStorage=true for local development

    Returns:
        dict: Summary of queue creation results
    """
    if connection_string is None:
        connection_string = os.environ.get(
            "AzureWebJobsStorage", "UseDevelopmentStorage=true")

    logger.info("Initializing Azure Storage Queues...")
    logger.info(f"Connection: {_mask_connection_string(connection_string)}")

    try:
        queue_service = QueueServiceClient.from_connection_string(
            connection_string)

        results = {
            "created": [],
            "already_exists": [],
            "failed": []
        }

        for queue_name in REQUIRED_QUEUES:
            try:
                queue_client = queue_service.get_queue_client(queue_name)

                # Try to create the queue
                try:
                    queue_client.create_queue()
                    logger.info(f"✓ Created queue '{queue_name}'")
                    results["created"].append(queue_name)
                except Exception as e:
                    # Check if queue already exists
                    error_str = str(e)
                    error_lower = error_str.lower()
                    if ("QueueAlreadyExists" in error_str or
                            "already exists" in error_lower):
                        logger.info(f"✓ Queue '{queue_name}' already exists")
                        results["already_exists"].append(queue_name)
                    else:
                        # Some other error occurred
                        logger.error(
                            f"✗ Failed to create queue '{queue_name}': "
                            f"{error_str}")
                        results["failed"].append(
                            {"queue": queue_name, "error": error_str})

            except Exception as e:
                logger.error(
                    f"✗ Unexpected error with queue '{queue_name}': {str(e)}")
                results["failed"].append(
                    {"queue": queue_name, "error": str(e)})

        # Summary
        logger.info("\n" + "="*60)
        logger.info("Queue Initialization Summary")
        logger.info("="*60)
        logger.info(f"Created: {len(results['created'])} queues")
        if results["created"]:
            for queue in results["created"]:
                logger.info(f"  - {queue}")

        logger.info(f"\nAlready existed: {len(results['already_exists'])} queues")
        if results["already_exists"]:
            for queue in results["already_exists"]:
                logger.info(f"  - {queue}")

        if results["failed"]:
            logger.error(f"\nFailed: {len(results['failed'])} queues")
            for failure in results["failed"]:
                logger.error(f"  - {failure['queue']}: {failure['error']}")

        logger.info("="*60 + "\n")

        return results

    except Exception as e:
        logger.error(
            f"Fatal error during queue initialization: {str(e)}",
            exc_info=True)
        raise


def _mask_connection_string(conn_str: str) -> str:
    """Mask sensitive parts of connection string for logging"""
    if "UseDevelopmentStorage=true" in conn_str:
        return "UseDevelopmentStorage=true (Azurite)"

    # Mask the account key
    if "AccountKey=" in conn_str:
        parts = conn_str.split("AccountKey=")
        if len(parts) == 2:
            key_part = parts[1].split(";")[0]
            masked_key = key_part[:8] + "..." + \
                key_part[-4:] if len(key_part) > 12 else "***"
            return conn_str.replace(key_part, masked_key)

    return conn_str


# CLI support - can run directly
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Allow override via command line argument
    conn_str: str | None = sys.argv[1] if len(sys.argv) > 1 else None

    try:
        results = init_queues(conn_str)

        # Exit code based on failures
        if results["failed"]:
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        logger.error(f"Fatal error during queue initialization: {str(e)}")
        sys.exit(1)
