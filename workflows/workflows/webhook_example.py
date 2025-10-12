"""
Webhook Example Workflow
Demonstrates HTTP-triggered workflow that can be called via webhook
"""

from shared.decorators import workflow, param


@workflow(
    name="webhook_example",
    description="Example HTTP-triggered workflow for external integration testing",
    category="examples",
    tags=["http", "example", "demo", "external"],
    execution_mode="sync",
    timeout_seconds=60,
    expose_in_forms=True,
    requires_org=True
)
@param(
    "message",
    type="string",
    label="Message",
    required=True,
    help_text="Message to process via webhook"
)
@param(
    "priority",
    type="string",
    label="Priority Level",
    required=False,
    default_value="normal",
    help_text="Priority: low, normal, high"
)
@param(
    "notify",
    type="bool",
    label="Send Notification",
    required=False,
    default_value=False,
    help_text="Whether to send a notification after processing"
)
async def process_webhook_message(
    context,
    message: str,
    priority: str = "normal",
    notify: bool = False
):
    """
    Process an incoming message (from form or external HTTP call).

    This workflow demonstrates HTTP-triggered execution. It can be called:

    1. Via Form UI (authenticated with Azure AD)
    2. Via Direct HTTP POST (authenticated with Azure Function key)

    **Direct HTTP URL**: POST https://{function-app}.azurewebsites.net/api/workflows/webhook_example

    **Authentication** (for direct HTTP calls):
    - Query parameter: ?code={function-key}
    - OR Header: x-functions-key: {function-key}

    **Headers Required**:
    - Content-Type: application/json
    - X-Organization-Id: <org-uuid> (if requires_org=True)

    **Body** (flat JSON with workflow parameters):
    ```json
    {
      "message": "Hello from external system",
      "priority": "high",
      "notify": true
    }
    ```

    Args:
        context: OrganizationContext with org_id, credentials, etc.
        message: Message to process
        priority: Priority level (low, normal, high)
        notify: Whether to send notification

    Returns:
        dict: {
            "success": bool,
            "message": str,
            "processed_message": str,
            "priority": str,
            "notification_sent": bool
        }
    """
    from datetime import datetime

    # Log webhook execution
    context.log("info", f"Webhook triggered: processing message with priority {priority}")

    # Validate priority
    valid_priorities = ["low", "normal", "high"]
    if priority not in valid_priorities:
        context.log("warning", f"Invalid priority '{priority}', defaulting to 'normal'")
        priority = "normal"

    # Process the message
    processed_message = f"[{priority.upper()}] {message}"
    context.log("debug", f"Processed message: {processed_message}")

    # Simulate notification
    notification_sent = False
    if notify:
        context.log("info", f"Sending notification for message: {message}")
        # In real implementation, this would call notification service
        notification_sent = True

    # Build response
    result = {
        "success": True,
        "message": "Webhook processed successfully",
        "processed_message": processed_message,
        "original_message": message,
        "priority": priority,
        "notification_sent": notification_sent,
        "processed_at": datetime.utcnow().isoformat(),
        "organization_id": context.org_id,
        "trigger_type": "webhook" if context.get_metadata("is_webhook") else "form"
    }

    context.log(
        "info",
        "Webhook processing complete",
        {
            "message_length": len(message),
            "priority": priority,
            "notification_sent": notification_sent
        }
    )

    return result
