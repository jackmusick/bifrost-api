"""
Git Sync Worker - Dedicated queue worker for git sync operations
Processes git sync messages from Azure Storage Queue
"""

import json
import logging

import azure.functions as func

from shared.services.git_integration_service import GitIntegrationService
from shared.webpubsub_broadcaster import WebPubSubBroadcaster

logger = logging.getLogger(__name__)

# Create blueprint for git sync worker function
bp = func.Blueprint()


@bp.function_name("git_sync_worker")
@bp.queue_trigger(
    arg_name="msg",
    queue_name="git-sync-jobs",
    connection="AzureWebJobsStorage"
)
async def git_sync_worker(msg: func.QueueMessage) -> None:
    """
    Process git operations messages from queue.

    Message format:
    {
        "type": "git_sync" | "git_refresh" | "git_commit" | "git_discard",
        "job_id": "uuid",
        "org_id": "organization-id",
        "connection_id": "webpubsub-connection-id" (optional),
        "user_id": "user-id",
        "user_email": "user@example.com",
        ... (additional fields based on operation type)
    }
    """
    print(f"[GIT SYNC WORKER] Function invoked with message: {msg}", flush=True)
    logger.info("Git sync worker invoked")
    try:
        # Parse queue message
        message_body = msg.get_body().decode('utf-8')
        logger.info(f"Message body: {message_body}")
        message_data = json.loads(message_body)
        logger.info(f"Parsed message data: {message_data}")

        # Route to appropriate handler based on operation type
        operation_type = message_data.get("type", "git_sync")

        if operation_type == "git_sync":
            await handle_git_sync(message_data)
        elif operation_type == "git_refresh":
            await handle_git_refresh(message_data)
        elif operation_type == "git_commit":
            logger.error("git_commit operation not yet implemented")  # TODO: Implement git_commit
        elif operation_type == "git_discard":
            logger.error("git_discard operation not yet implemented")  # TODO: Implement git_discard
        else:
            logger.error(f"Unknown operation type: {operation_type}")
            raise ValueError(f"Unknown operation type: {operation_type}")

    except Exception as e:
        logger.error(
            f"Git sync worker error: {str(e)}",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "message_data": message_data if 'message_data' in locals() else "N/A"
            },
            exc_info=True
        )
        # Re-raise to let Azure Functions handle retry/poison queue
        raise


async def handle_git_sync(message_data: dict) -> None:
    """
    Handle git sync message - atomic pull + push operation.

    Args:
        message_data: Queue message data containing git sync details
    """
    job_id = message_data.get("job_id", "unknown")
    org_id = message_data.get("org_id")
    connection_id = message_data.get("connection_id")

    logger.info(
        "Processing git sync operation",
        extra={
            "job_id": job_id,
            "org_id": org_id
        }
    )

    # Initialize broadcaster for streaming logs to terminal
    broadcaster = WebPubSubBroadcaster()

    async def send_log(message: str, level: str = "info"):
        """Send log message to WebPubSub terminal"""
        if connection_id and broadcaster.enabled and broadcaster.client:
            try:
                broadcaster.client.send_to_connection(
                    connection_id=connection_id,
                    message={
                        "type": "log",
                        "level": level,
                        "message": message
                    },
                    content_type="application/json"
                )
            except Exception as e:
                logger.warning(f"Failed to send log to WebPubSub: {e}")

    completion_sent = False

    try:
        # Create context object with required attributes
        if not org_id:
            raise ValueError("org_id is required for git sync operation")

        class Context:
            def __init__(self, org_id: str):
                self.org_id = org_id
                self.scope = org_id  # For scoped repository access

        context = Context(org_id)

        git_service = GitIntegrationService()

        # Step 1: Pull from remote
        await send_log("Starting sync: pulling changes from GitHub...")
        pull_result = await git_service.pull(context, connection_id=connection_id)

        # Check if pull was successful
        if not pull_result.get("success"):
            error_msg = pull_result.get("error", "Pull failed")
            # Don't send duplicate log - pull() already sent error to WebPubSub
            raise Exception(f"Pull failed: {error_msg}")

        # Check for conflicts
        conflicts = pull_result.get("conflicts", [])
        if conflicts:
            conflict_count = len(conflicts)
            await send_log(
                f"⚠️ Sync stopped: {conflict_count} conflict(s) detected. "
                "Resolve conflicts in the editor and try again.",
                "warning"
            )

            # Send completion message with conflicts
            if connection_id and broadcaster.enabled and broadcaster.client:
                try:
                    broadcaster.client.send_to_connection(
                        connection_id=connection_id,
                        message={
                            "type": "complete",
                            "status": "conflict",
                            "conflicts": conflicts,
                            "message": f"Sync stopped due to {conflict_count} conflict(s)"
                        },
                        content_type="application/json"
                    )
                except Exception as e:
                    logger.error(f"Failed to send conflict completion message: {e}")
            else:
                logger.warning(f"Cannot send completion message - connection_id: {connection_id}, enabled: {broadcaster.enabled}, has_client: {broadcaster.client is not None}")

            completion_sent = True
            logger.info(
                f"Git sync stopped due to conflicts: {job_id}",
                extra={"job_id": job_id, "conflict_count": conflict_count}
            )
            return  # Don't raise - conflicts are expected, not an error

        # Step 2: Discover new workflows/providers after pull
        await send_log("Discovering workflows and data providers...")
        from function_app import discover_workspace_modules
        discover_workspace_modules()
        await send_log("Discovery complete")

        # Step 3: Push to remote (if no conflicts)
        await send_log("No conflicts detected, pushing changes to GitHub...")
        push_result = await git_service.push(context, connection_id=connection_id)

        # Check if push was successful
        if not push_result.get("success"):
            error_msg = push_result.get("error", "Push failed")
            await send_log(f"✗ Push failed: {error_msg}", "error")
            raise Exception(f"Push failed: {error_msg}")

        # Success!
        files_updated = pull_result.get("updated_files", [])
        commits_pushed = push_result.get("commits_pushed", 0)

        success_msg = (
            f"✓ Sync complete! "
            f"Updated {len(files_updated)} file(s), "
            f"pushed {commits_pushed} commit(s)"
        )
        await send_log(success_msg, "success")

        # Send completion message
        if connection_id and broadcaster.enabled and broadcaster.client:
            try:
                broadcaster.client.send_to_connection(
                    connection_id=connection_id,
                    message={
                        "type": "complete",
                        "status": "success",
                        "message": success_msg,
                        "updated_files": files_updated,
                        "commits_pushed": commits_pushed
                    },
                    content_type="application/json"
                )
            except Exception as e:
                logger.error(f"Failed to send success completion message: {e}")
        else:
            logger.warning(f"Cannot send completion message - connection_id: {connection_id}, enabled: {broadcaster.enabled}, has_client: {broadcaster.client is not None}")

        completion_sent = True
        logger.info(
            f"Git sync completed successfully: {job_id}",
            extra={
                "job_id": job_id,
                "files_updated": len(files_updated),
                "commits_pushed": commits_pushed
            }
        )

    except Exception as e:
        # Send error message only if it wasn't already sent by a child operation
        error_msg = str(e)

        # If pull or push already sent error, don't duplicate it
        if not error_msg.startswith("Pull failed:") and not error_msg.startswith("Push failed:"):
            # This is a different error - send it with Sync failed prefix
            error_msg = f"Sync failed: {error_msg}"
            await send_log(f"✗ {error_msg}", "error")
        # else: pull/push already sent the error via WebPubSub, don't duplicate

        # Always send completion message so frontend stops loading
        if connection_id and broadcaster.enabled and broadcaster.client:
            try:
                broadcaster.client.send_to_connection(
                    connection_id=connection_id,
                    message={
                        "type": "complete",
                        "status": "error",
                        "message": error_msg
                    },
                    content_type="application/json"
                )
            except Exception as pubsub_error:
                logger.error(f"Failed to send error completion to WebPubSub: {pubsub_error}")
        else:
            logger.warning(f"Cannot send error completion - connection_id: {connection_id}, enabled: {broadcaster.enabled}, has_client: {broadcaster.client is not None}")

        completion_sent = True

        logger.error(
            f"Git sync error: {job_id}",
            extra={
                "job_id": job_id,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        # Don't re-raise - job is complete (failed)
        # The error is already logged

    finally:
        # Safety net: ensure completion message is sent even if something went wrong
        if not completion_sent and connection_id and broadcaster.enabled and broadcaster.client:
            try:
                logger.warning(f"Completion message not sent, sending fallback message for job {job_id}")
                broadcaster.client.send_to_connection(
                    connection_id=connection_id,
                    message={
                        "type": "complete",
                        "status": "error",
                        "message": "Sync operation interrupted"
                    },
                    content_type="application/json"
                )
            except Exception as fallback_error:
                logger.error(f"Failed to send fallback completion message: {fallback_error}")


async def handle_git_refresh(message_data: dict) -> None:
    """
    Handle git refresh message - fetch from remote and return status.

    Args:
        message_data: Queue message data containing git refresh details
    """
    job_id = message_data.get("job_id", "unknown")
    org_id = message_data.get("org_id")
    connection_id = message_data.get("connection_id")

    logger.info(
        "Processing git refresh operation",
        extra={
            "job_id": job_id,
            "org_id": org_id
        }
    )

    # Initialize broadcaster for streaming logs to terminal
    broadcaster = WebPubSubBroadcaster()

    async def send_log(message: str, level: str = "info"):
        """Send log message to WebPubSub terminal"""
        if connection_id and broadcaster.enabled and broadcaster.client:
            try:
                broadcaster.client.send_to_connection(
                    connection_id=connection_id,
                    message={
                        "type": "log",
                        "level": level,
                        "message": message
                    },
                    content_type="application/json"
                )
            except Exception as e:
                logger.warning(f"Failed to send log to WebPubSub: {e}")

    completion_sent = False

    try:
        # Create context object with required attributes
        if not org_id:
            raise ValueError("org_id is required for git sync operation")

        class Context:
            def __init__(self, org_id: str):
                self.org_id = org_id
                self.scope = org_id  # For scoped repository access

        context = Context(org_id)

        git_service = GitIntegrationService()

        # Perform refresh (fetch + status)
        await send_log("Fetching latest changes from GitHub...")
        result = await git_service.refresh_status(context)

        if result.get("success"):
            await send_log("✓ Status refreshed successfully", "success")

            # Discover workflows and data providers after refresh
            await send_log("Discovering workflows and data providers...")
            from function_app import discover_workspace_modules
            discover_workspace_modules()
            await send_log("Discovery complete")

            # Send completion message with status data
            if connection_id and broadcaster.enabled and broadcaster.client:
                broadcaster.client.send_to_connection(
                    connection_id=connection_id,
                    message={
                        "type": "complete",
                        "status": "success",
                        "message": "Status refreshed",
                        "data": result
                    },
                    content_type="application/json"
                )

            completion_sent = True
            logger.info(
                f"Git refresh completed successfully: {job_id}",
                extra={"job_id": job_id}
            )
        else:
            error_msg = result.get("error", "Refresh failed")
            await send_log(f"✗ Refresh failed: {error_msg}", "error")
            raise Exception(error_msg)

    except Exception as e:
        # Send error message
        error_msg = f"Refresh failed: {str(e)}"
        await send_log(f"✗ {error_msg}", "error")

        # Always send completion message so frontend stops loading
        logger.info(f"Attempting to send error completion. connection_id={connection_id}, enabled={broadcaster.enabled}, has_client={broadcaster.client is not None}")

        if not connection_id:
            logger.error("Cannot send completion - no connection_id provided")
        elif not broadcaster.enabled:
            logger.error("Cannot send completion - WebPubSub not enabled")
        elif not broadcaster.client:
            logger.error("Cannot send completion - WebPubSub client not initialized")
        else:
            try:
                broadcaster.client.send_to_connection(
                    connection_id=connection_id,
                    message={
                        "type": "complete",
                        "status": "error",
                        "message": error_msg
                    },
                    content_type="application/json"
                )
                completion_sent = True
                logger.info("Error completion message sent successfully")
            except Exception as pubsub_error:
                logger.error(f"Failed to send error completion to WebPubSub: {pubsub_error}", exc_info=True)

        logger.error(
            f"Git refresh error: {job_id}",
            extra={
                "job_id": job_id,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )

    finally:
        # Safety net: ensure completion message is sent even if something went wrong
        if not completion_sent:
            logger.warning(f"Completion message not sent yet for job {job_id}, attempting fallback")

            if connection_id and broadcaster.enabled and broadcaster.client:
                try:
                    broadcaster.client.send_to_connection(
                        connection_id=connection_id,
                        message={
                            "type": "complete",
                            "status": "error",
                            "message": "Refresh operation interrupted"
                        },
                        content_type="application/json"
                    )
                    logger.info("Fallback completion message sent successfully")
                except Exception as fallback_error:
                    logger.error(f"Failed to send fallback completion message: {fallback_error}", exc_info=True)
            else:
                logger.error(f"Cannot send fallback - connection_id={connection_id}, enabled={broadcaster.enabled}, has_client={broadcaster.client is not None}")
