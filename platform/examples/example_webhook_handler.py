"""
Webhook Example Workflow

A public webhook endpoint that can be called without authentication.
This demonstrates the public_endpoint feature for receiving external webhooks.
"""

import logging

from bifrost import ExecutionContext, param, workflow

logger = logging.getLogger(__name__)


@workflow(
    name="webhook_example",
    description="Public webhook endpoint for external integrations",
    category="webhooks",
    tags=["webhook", "public", "example"],
    execution_mode="async",
    endpoint_enabled=True,
    allowed_methods=["POST"],
    public_endpoint=True  # No authentication required
)
@param("event_type", type="string", label="Event Type", required=True, help_text="Type of webhook event")
@param("payload", type="json", label="Payload", required=False, help_text="Event payload data")
async def webhook_example(
    context: ExecutionContext,
    event_type: str,
    payload: dict = None
) -> dict:
    """
    Public webhook endpoint that accepts events from external systems.

    This workflow is exposed as a PUBLIC HTTP endpoint at:
    - POST /api/endpoints/webhook_example

    No authentication is required. External systems can POST directly.

    Args:
        context: Organization context (will be anonymous for public endpoints)
        event_type: Type of event being received
        payload: Optional event payload data

    Returns:
        Dictionary with acknowledgment and processing details

    Example:
        curl -X POST \
          -H "Content-Type: application/json" \
          -d '{"event_type": "order.created", "payload": {"order_id": "12345"}}' \
          http://localhost:4280/api/endpoints/webhook_example

    Security Note:
        Since this is a public endpoint, implement your own validation logic:
        - Verify webhook signatures if the external system supports them
        - Validate payload structure
        - Rate limit if needed
        - Log suspicious activity
    """
    import datetime

    # Log the webhook event
    logger.info(f"Received webhook event: {event_type}")

    # Process the payload
    timestamp = datetime.datetime.utcnow().isoformat()

    result = {
        "status": "received",
        "event_type": event_type,
        "received_at": timestamp,
        "caller": context.name,  # Will be "Public Access (Webhook)"
        "has_payload": payload is not None
    }

    if payload:
        logger.info(f"Payload keys: {list(payload.keys())}")
        result["payload_keys"] = list(payload.keys())

    # Save checkpoint for audit trail
    context.save_checkpoint("webhook_received", {
        "event_type": event_type,
        "timestamp": timestamp,
        "payload_size": len(str(payload)) if payload else 0
    })

    return result
