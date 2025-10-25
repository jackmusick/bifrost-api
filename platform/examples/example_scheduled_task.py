"""
Test Scheduled Workflow
Runs every 5 minutes to validate scheduling system
"""

import logging
from datetime import datetime
from bifrost import workflow, ExecutionContext

logger = logging.getLogger(__name__)


@workflow(
    name="test_scheduled_workflow",
    description="Test Scheduled Workflow (Every 5 Minutes)",
    schedule="*/5 * * * *",  # Every 5 minutes
    execution_mode="async",
    category="Testing"
)
async def test_scheduled_workflow(context: ExecutionContext):
    """
    Test workflow that runs every 5 minutes.
    Validates that the scheduling system is working correctly.
    """
    current_time = datetime.utcnow()

    logger.info(f"Test scheduled workflow executed at {current_time.isoformat()}")

    return {
        "status": "success",
        "executed_at": current_time.isoformat(),
        "message": "Scheduled workflow test completed successfully"
    }
