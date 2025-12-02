"""
E2E Simple Greeting Workflow

Copy of platform/examples/example_basic_workflow.py with renamed workflow for E2E testing.
A basic workflow for testing form submission and execution.
"""

import logging

from bifrost import ExecutionContext, param, workflow

logger = logging.getLogger(__name__)


@workflow(
    name="e2e_simple_greeting",
    description="E2E simple greeting workflow",
    category="e2e_testing",
    tags=["e2e", "test", "greeting"]
)
@param("name", type="string", label="Name", required=True, help_text="Name to greet")
@param("greeting_type", type="string", label="Greeting Type", required=False, default_value="Hello", help_text="Type of greeting")
@param("include_timestamp", type="bool", label="Include Timestamp", required=False, default_value=False, help_text="Whether to include timestamp")
async def e2e_simple_greeting(
    context: ExecutionContext,
    name: str,
    greeting_type: str = "Hello",
    include_timestamp: bool = False
) -> dict:
    """
    E2E simple greeting workflow that creates a personalized greeting.

    Args:
        context: Organization context
        name: Name to greet
        greeting_type: Type of greeting (default: "Hello")
        include_timestamp: Whether to include timestamp

    Returns:
        Dictionary with greeting message
    """
    import datetime

    greeting = f"{greeting_type}, {name}!"

    if include_timestamp:
        timestamp = datetime.datetime.utcnow().isoformat()
        greeting += f" (at {timestamp})"

    logger.info(f"Generated greeting: {greeting}")

    return {
        "greeting": greeting,
        "name": name,
        "greeting_type": greeting_type,
        "org_id": context.org_id
    }
