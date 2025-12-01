"""
Simple test workflow for validation

This workflow is used by integration tests to verify auto-discovery.
"""

import logging

from bifrost import workflow, param, ExecutionContext

logger = logging.getLogger(__name__)


@workflow(
    name="test_workflow",
    description="Simple test workflow for validation",
    category="testing",
    tags=["test", "example"]
)
@param("name", "string", label="Name", required=True, help_text="Name to greet")
@param("count", "int", label="Count", required=False, default_value=1, help_text="Number of times to greet")
async def test_workflow(context: ExecutionContext, name: str, count: int = 1):
    """Simple test workflow for validation"""
    logger.info(f"Test workflow executed with name={name}, count={count}")

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
