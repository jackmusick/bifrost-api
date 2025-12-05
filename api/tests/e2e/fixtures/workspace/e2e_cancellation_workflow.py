"""
E2E Cancellation Test Workflow

A workflow with a configurable sleep duration for testing cancellation.
This workflow is used by E2E tests to verify that running workflows can be cancelled.
"""

import logging
import time

from shared.decorators import workflow, param

logger = logging.getLogger(__name__)


@workflow(
    name="e2e_cancellation_test",
    description="Workflow with configurable sleep for cancellation testing",
    execution_mode="async",
    category="e2e_testing",
    tags=["e2e", "test", "cancellation"],
)
@param("sleep_seconds", "int", default_value=30, help_text="Seconds to sleep")
async def e2e_cancellation_test(context, sleep_seconds: int = 30):
    """
    A workflow that sleeps for a configurable duration.
    Used to test cancellation of running workflows.
    """
    logger.info(f"Starting sleep for {sleep_seconds} seconds...")
    time.sleep(sleep_seconds)
    logger.info("Sleep completed - this should not appear if cancelled")
    return {"status": "completed", "slept_for": sleep_seconds}
