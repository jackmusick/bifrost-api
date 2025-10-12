"""
Example: Hello World Workflow

Demonstrates the simplest possible workflow with basic logging and return values.
"""

from engine.shared.decorators import workflow, param
from engine.shared.context import OrganizationContext


@workflow(
    name="hello_world",
    description="Simple hello world workflow demonstrating basic concepts",
    category="Examples"
)
@param("name", str, "Name to greet", required=False, default="World")
async def hello_world(context: OrganizationContext, name: str) -> dict:
    """
    Simple hello world workflow.

    Args:
        context: Organization context
        name: Name to greet

    Returns:
        dict: Greeting message
    """
    # Log execution
    context.log(f"Greeting: {name}")

    # Return result
    return {
        "message": f"Hello, {name}!",
        "org": context.org.name,
        "caller": context.caller.email
    }
