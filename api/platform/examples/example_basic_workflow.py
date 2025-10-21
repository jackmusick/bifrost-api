"""
Simple Greeting Workflow

A basic workflow for testing form submission and execution.
"""

from bifrost import OrganizationContext, param, workflow


@workflow(
    name="simple_greeting",
    description="Simple greeting workflow",
    category="testing",
    tags=["test", "greeting"],
    execution_mode="sync"
)
@param("name", type="string", label="Name", required=True, help_text="Name to greet")
@param("greeting_type", type="string", label="Greeting Type", required=False, default_value="Hello", help_text="Type of greeting")
@param("include_timestamp", type="bool", label="Include Timestamp", required=False, default_value=False, help_text="Whether to include timestamp")
async def simple_greeting(
    context: OrganizationContext,
    name: str,
    greeting_type: str = "Hello",
    include_timestamp: bool = False
) -> dict:
    """
    Simple greeting workflow that creates a personalized greeting.

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

    context.info(f"Generated greeting: {greeting}")

    return {
        "greeting": greeting,
        "name": name,
        "greeting_type": greeting_type,
        "org_id": context.org_id
    }
