"""
Web PubSub broadcasting utilities

Provides helpers for broadcasting real-time execution updates to connected clients
via Azure Web PubSub - the SIMPLE way that actually works!
"""

import logging
import os
from datetime import datetime

from azure.messaging.webpubsubservice import WebPubSubServiceClient
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)


class WebPubSubBroadcaster:
    """
    Helper for broadcasting execution updates via Azure Web PubSub.

    Direct HTTP-based broadcasting - no queues, no triggers, no poison queues!
    Auto-detects if Web PubSub is enabled via environment variable.
    If disabled, all broadcast calls are silently ignored (no-op).

    Usage:
        from shared.webpubsub_broadcaster import WebPubSubBroadcaster

        # Initialize broadcaster
        broadcaster = WebPubSubBroadcaster()

        # Broadcast execution update
        broadcaster.broadcast_execution_update(
            execution_id="abc-123",
            status="Running",
            executed_by="user@example.com",
            scope="org-456",
            latest_logs=[...],
            is_complete=False
        )
    """

    def __init__(self):
        """
        Initialize broadcaster.

        Supports two authentication methods:
        1. Managed Identity (production) - uses AZURE_WEBPUBSUB_ENDPOINT env var
        2. Connection String (local dev) - uses WebPubSubConnectionString env var

        Note: Client initialization is lazy to avoid event loop issues in tests.
        """
        # Get configuration
        self.hub_name = os.getenv('AZURE_WEBPUBSUB_HUB', 'bifrost')
        self.endpoint = os.getenv('AZURE_WEBPUBSUB_ENDPOINT')
        self.connection_string = os.getenv('WebPubSubConnectionString')

        self.enabled = bool(self.endpoint or self.connection_string)
        self._client = None

        if not self.enabled:
            logger.debug("Web PubSub disabled (no endpoint or connection string) - broadcasts will be skipped")

    @property
    def client(self):
        """
        Lazy initialization of Web PubSub client.

        This avoids event loop issues during initialization, especially in tests.
        Creates the client only when actually needed for sending messages.
        """
        if self._client is not None:
            return self._client

        if not self.enabled:
            return None

        try:
            if self.endpoint:
                # Use managed identity (production)
                # Import here to avoid creating credential at module load time
                logger.info(f"Initializing Web PubSub with managed identity: {self.endpoint}")
                try:
                    credential = DefaultAzureCredential()
                    self._client = WebPubSubServiceClient(
                        endpoint=self.endpoint,
                        hub=self.hub_name,
                        credential=credential
                    )
                    logger.info("Web PubSub broadcaster initialized with managed identity")
                except Exception as cred_error:
                    # If credential creation fails (e.g., in tests), disable broadcaster
                    logger.warning(f"Failed to create DefaultAzureCredential: {cred_error}")
                    self.enabled = False
                    return None
            elif self.connection_string:
                # Use connection string (local dev)
                logger.info("Initializing Web PubSub with connection string")
                self._client = WebPubSubServiceClient.from_connection_string(
                    connection_string=self.connection_string,
                    hub=self.hub_name
                )
                logger.info("Web PubSub broadcaster initialized with connection string")
            else:
                # Should not reach here, but satisfy type checker
                logger.warning("Web PubSub not configured (no endpoint or connection string)")
                self.enabled = False
                return None
        except Exception as e:
            logger.warning(f"Failed to initialize Web PubSub client: {e}")
            self.enabled = False
            self._client = None

        return self._client

    def broadcast_execution_update(
        self,
        execution_id: str,
        status: str,
        executed_by: str,
        scope: str,
        latest_logs: list[dict] | None = None,
        is_complete: bool = False
    ):
        """
        Broadcast execution update to subscribed clients.

        Args:
            execution_id: Execution ID
            status: Current execution status
            executed_by: User ID who executed
            scope: Organization scope
            latest_logs: Recent log entries (last 50)
            is_complete: Whether execution finished

        Returns:
            None (fire-and-forget)
        """
        if not self.enabled or not self.client:
            logger.debug(f"Broadcast skipped - enabled={self.enabled}, client={self.client is not None}")
            return

        logger.info(f"Broadcasting execution update for {execution_id}")

        try:
            # Prepare message
            message = {
                "executionId": execution_id,
                "status": status,
                "isComplete": is_complete,
                "timestamp": datetime.utcnow().isoformat()
            }

            if latest_logs and len(latest_logs) > 0:
                message["latestLogs"] = latest_logs[-50:]

            # Send to execution-specific group
            group_name = f"execution:{execution_id}"

            payload = {
                "target": "executionUpdate",
                "data": message
            }

            logger.info(f"Sending to {group_name}: {payload}")

            # Send message - Web PubSub will wrap it automatically
            self.client.send_to_group(
                group=group_name,
                message=payload,
                content_type="application/json"
            )

            logger.info(f"Sent execution update to group {group_name}")

        except Exception as e:
            # Log but don't fail - real-time updates are non-critical
            logger.warning(
                f"Failed to broadcast execution update (non-fatal): {str(e)}",
                extra={"execution_id": execution_id}
            )

    def broadcast_execution_to_history(
        self,
        execution_id: str,
        workflow_name: str,
        status: str,
        executed_by: str,
        executed_by_name: str,
        scope: str,
        started_at: datetime,
        completed_at: datetime | None = None,
        duration_ms: int | None = None
    ):
        """
        Broadcast execution update to history page listeners.

        Sends to scope-specific group so history page can show new executions
        and update existing ones in real-time.

        Args:
            execution_id: Execution ID
            workflow_name: Name of workflow
            status: Execution status
            executed_by: User ID who executed
            executed_by_name: Display name of user
            scope: Organization scope or "GLOBAL"
            started_at: Execution start timestamp
            completed_at: Execution completion timestamp (optional)
            duration_ms: Execution duration in milliseconds (optional)

        Returns:
            None (broadcasts are fire-and-forget)
        """
        if not self.enabled or not self.client:
            logger.debug(f"Broadcast to history skipped - enabled={self.enabled}, client={self.client is not None}")
            return

        try:
            # Build message dict with proper typing to allow both str and int values
            from typing import Any
            message: dict[str, Any] = {
                "executionId": execution_id,
                "workflowName": workflow_name,
                "status": status,
                "executedBy": executed_by,
                "executedByName": executed_by_name,
                "startedAt": started_at.isoformat(),
                "timestamp": datetime.utcnow().isoformat()
            }

            if completed_at:
                message["completedAt"] = completed_at.isoformat()
            if duration_ms is not None:
                message["durationMs"] = duration_ms

            # Send to scope-specific history group
            group_name = f"history:{scope}"

            logger.info(f"Sending history update to {group_name}: {execution_id} ({status})")

            self.client.send_to_group(
                group=group_name,
                message={
                    "target": "executionHistoryUpdate",
                    "data": message
                },
                content_type="application/json"
            )

            logger.info(f"Sent history update to group {group_name}")

        except Exception as e:
            logger.warning(
                f"Failed to broadcast to history (non-fatal): {str(e)}",
                extra={"execution_id": execution_id}
            )
