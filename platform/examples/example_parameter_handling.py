"""
Example Test Workflow

A simple test workflow for validating the workflow system.
This workflow demonstrates basic parameter handling and execution.
"""

import logging

from bifrost import ExecutionContext, param, workflow

logger = logging.getLogger(__name__)


@workflow(
    name="test_workflow",
    description="Simple test workflow for validation",
    category="testing",
    tags=["test", "example"],
    execution_mode="sync",
    endpoint_enabled=True,
    allowed_methods=["GET", "POST"],
    disable_global_key=False
)
@param("name", type="string", label="Name", required=True, help_text="Name to greet")
@param("count", type="int", label="Count", required=False, default_value=1, help_text="Number of times to greet")
async def test_workflow(context: ExecutionContext, name: str, count: int = 1) -> dict:
    """
    Simple test workflow that greets a name.

    This workflow is exposed as an HTTP endpoint at:
    - GET /api/endpoints/test_workflow?name=John&count=3
    - POST /api/endpoints/test_workflow (with JSON body)

    Args:
        context: Organization context with org info and integrations
        name: Name to greet (required)
        count: Number of times to greet (default: 1)

    Returns:
        Dictionary with greeting message and metadata

    Example:
        curl -X POST \\
          -H "x-functions-key: YOUR_API_KEY" \\
          -H "Content-Type: application/json" \\
          -d '{"name": "World", "count": 3}' \\
          https://app.azurestaticapps.net/api/endpoints/test_workflow
    """
    greetings = []

    for i in range(count):
        greeting = f"Hello, {name}! (#{i + 1})"
        greetings.append(greeting)

        # Log each greeting
        logger.info(f"Generated greeting: {greeting}")

    # Note: save_checkpoint() has been removed - no longer needed

    return {
        "greetings": greetings,
        "total_count": count,
        "org_id": context.org_id,
        "org_name": context.org_name
    }
