"""
Queue Processor Workflow
Simulates a queued task with delayed processing for testing async execution tracking
"""

import asyncio
from engine.shared.decorators import workflow, param


@workflow(
    name="queue_processor",
    description="Process an item through a simulated queue (delayed response)",
    category="testing",
    tags=["test", "demo", "queue", "async"]
)
@param(
    "item_name",
    type="string",
    label="Item Name",
    required=True,
    help_text="Name of the item to process"
)
@param(
    "priority",
    type="int",
    label="Priority",
    required=False,
    default_value=5,
    help_text="Processing priority (1-10, higher = more important)"
)
@param(
    "delay_seconds",
    type="int",
    label="Processing Delay (seconds)",
    required=False,
    default_value=5,
    help_text="Simulated processing time in seconds"
)
@param(
    "description",
    type="string",
    label="Description",
    required=False,
    default_value="",
    help_text="Optional description of the item"
)
async def process_queue_item(
    context,
    item_name: str,
    priority: int = 5,
    delay_seconds: int = 5,
    description: str = ""
):
    """
    Process an item through a simulated queue with configurable delay.

    This workflow simulates an asynchronous task that takes time to complete,
    perfect for testing execution status tracking and live updates.

    Args:
        context: OrganizationContext with org_id, credentials, etc.
        item_name: Name of the item to process
        priority: Processing priority (1-10)
        delay_seconds: How long to simulate processing
        description: Optional item description

    Returns:
        dict: {
            "success": bool,
            "item_name": str,
            "queue_position": int,
            "processing_time": float,
            "priority": int,
            "status": str,
            "message": str
        }
    """
    from datetime import datetime
    import random

    start_time = datetime.utcnow()

    # Simulate queue position based on priority
    queue_position = max(1, 11 - priority)

    # Log initial status
    # await context.log("info", f"Item '{item_name}' added to queue at position {queue_position}")

    # Simulate processing delay
    await asyncio.sleep(delay_seconds)

    # Calculate actual processing time
    end_time = datetime.utcnow()
    processing_time = (end_time - start_time).total_seconds()

    # Simulate occasional failures for testing error handling
    success_rate = 0.9  # 90% success rate
    success = random.random() < success_rate

    if success:
        result = {
            "success": True,
            "item_name": item_name,
            "queue_position": queue_position,
            "processing_time": round(processing_time, 2),
            "priority": priority,
            "status": "completed",
            "message": f"Item '{item_name}' processed successfully",
            "processed_at": end_time.isoformat(),
            "description": description or "No description provided"
        }
    else:
        # Simulate processing failure
        result = {
            "success": False,
            "item_name": item_name,
            "queue_position": queue_position,
            "processing_time": round(processing_time, 2),
            "priority": priority,
            "status": "failed",
            "message": f"Failed to process item '{item_name}' - simulated error",
            "error": "Simulated processing failure (10% chance)",
            "failed_at": end_time.isoformat()
        }

    return result
