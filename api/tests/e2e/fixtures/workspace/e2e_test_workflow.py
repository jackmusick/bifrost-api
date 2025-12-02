"""
E2E Test Workflow

Copy of platform/examples/test_workflow.py with renamed workflow for E2E testing.
This workflow is used by E2E tests to verify workspace discovery and execution.
"""

import logging

from bifrost import workflow, param, ExecutionContext

logger = logging.getLogger(__name__)


@workflow(
    name="e2e_test_workflow",
    description="E2E test workflow for validation",
    category="e2e_testing",
    tags=["e2e", "test", "example"]
)
@param("name", "string", label="Name", required=True, help_text="Name to greet")
@param("count", "int", label="Count", required=False, default_value=1, help_text="Number of times to greet")
async def e2e_test_workflow(context: ExecutionContext, name: str, count: int = 1):
    """E2E test workflow for validation"""
    logger.info(f"E2E test workflow executed with name={name}, count={count}")

    messages = []
    for i in range(count):
        message = f"Hello, {name}! (iteration {i+1})"
        messages.append(message)
        logger.info(message)

    return {
        "status": "success",
        "name": name,
        "count": count,
        "messages": messages
    }
