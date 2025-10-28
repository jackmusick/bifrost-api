"""
Package Installation Worker - Dedicated queue worker for package installations
Processes package installation messages from Azure Storage Queue
"""

import json
import logging
import os
from pathlib import Path

import azure.functions as func

from shared.package_manager import WorkspacePackageManager
from shared.webpubsub_broadcaster import WebPubSubBroadcaster

logger = logging.getLogger(__name__)

# Create blueprint for package worker function
bp = func.Blueprint()


@bp.function_name("package_installation_worker")
@bp.queue_trigger(
    arg_name="msg",
    queue_name="package-installations",
    connection="AzureWebJobsStorage"
)
async def package_installation_worker(msg: func.QueueMessage) -> None:
    """
    Process package installation messages from queue.

    Message format:
    {
        "type": "package_install",
        "job_id": "uuid",
        "package": "package-name" (optional - if not provided, installs from requirements.txt),
        "version": "1.0.0" (optional),
        "connection_id": "webpubsub-connection-id" (optional),
        "user_id": "user-id",
        "user_email": "user@example.com"
    }
    """
    print(f"[PACKAGE WORKER] Function invoked with message: {msg}", flush=True)
    logger.info("Package installation worker invoked")
    try:
        # Parse queue message
        message_body = msg.get_body().decode('utf-8')
        logger.info(f"Message body: {message_body}")
        message_data = json.loads(message_body)
        logger.info(f"Parsed message data: {message_data}")

        await handle_package_install(message_data)

    except Exception as e:
        logger.error(
            f"Package installation worker error: {str(e)}",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "message_data": message_data if 'message_data' in locals() else "N/A"
            },
            exc_info=True
        )
        # Re-raise to let Azure Functions handle retry/poison queue
        raise


async def handle_package_install(message_data: dict) -> None:
    """
    Handle package installation message.

    Args:
        message_data: Queue message data containing package installation details
    """
    job_id = message_data.get("job_id", "unknown")
    package = message_data.get("package")
    version = message_data.get("version")
    connection_id = message_data.get("connection_id")

    logger.info(
        f"Processing package installation: {package or 'requirements.txt'}",
        extra={
            "job_id": job_id,
            "package": package,
            "version": version
        }
    )

    # Initialize broadcaster for streaming logs to terminal
    broadcaster = WebPubSubBroadcaster()

    async def send_log(message: str):
        """Send log message to WebPubSub terminal"""
        if connection_id and broadcaster.enabled and broadcaster.client:
            try:
                broadcaster.client.send_to_connection(
                    connection_id=connection_id,
                    message={
                        "type": "log",
                        "level": "info",
                        "message": message
                    },
                    content_type="application/json"
                )
            except Exception as e:
                logger.warning(f"Failed to send log to WebPubSub: {e}")

    try:
        # Get workspace path
        workspace_location = os.environ.get(
            'BIFROST_WORKSPACE_LOCATION', '/mounts/workspace')
        workspace_path = Path(workspace_location)

        pkg_manager = WorkspacePackageManager(workspace_path)

        if package:
            # Install specific package
            await send_log(f"Installing package: {package}{f'=={version}' if version else ''}")
            await pkg_manager.install_package(
                package_name=package,
                version=version,
                log_callback=send_log,
                append_to_requirements=True
            )
        else:
            # Install from requirements.txt
            await send_log("Installing packages from requirements.txt")
            await pkg_manager.install_requirements_streaming(
                log_callback=send_log
            )

        # Send completion message
        if connection_id and broadcaster.enabled and broadcaster.client:
            broadcaster.client.send_to_connection(
                connection_id=connection_id,
                message={
                    "type": "complete",
                    "status": "success",
                    "message": "Package installation completed successfully"
                },
                content_type="application/json"
            )

        logger.info(
            f"Package installation completed: {package or 'requirements.txt'}",
            extra={"job_id": job_id}
        )

    except Exception as e:
        # Send error message
        error_msg = f"Package installation failed: {str(e)}"
        await send_log(f"✗ {error_msg}")

        if connection_id and broadcaster.enabled and broadcaster.client:
            broadcaster.client.send_to_connection(
                connection_id=connection_id,
                message={
                    "type": "complete",
                    "status": "error",
                    "message": error_msg
                },
                content_type="application/json"
            )

        logger.error(
            f"Package installation error: {job_id}",
            extra={
                "job_id": job_id,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        raise  # Re-raise to trigger retry/poison queue
