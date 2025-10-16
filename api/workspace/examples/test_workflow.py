"""
Example Test Workflow

A simple test workflow for validating the workflow system.
This workflow demonstrates basic parameter handling and execution.
"""

from bifrost import OrganizationContext, param, workflow


@workflow(
    name="test_workflow",
    description="Simple test workflow for validation",
    category="testing",
    tags=["test", "example"],
    requires_org=True
)
@param("name", type="string", label="Name", required=True, help_text="Name to greet")
@param("count", type="int", label="Count", required=False, default_value=1, help_text="Number of times to greet")
async def test_workflow(context: OrganizationContext, name: str, count: int = 1) -> dict:
    """
    Simple test workflow that greets a name.

    Args:
        context: Organization context with org info and integrations
        name: Name to greet
        count: Number of times to greet (default: 1)

    Returns:
        Dictionary with greeting message and metadata
    """
    greetings = []

    for i in range(count):
        greeting = f"Hello, {name}! (#{i + 1})"
        greetings.append(greeting)

        # Log each greeting
        context.info(f"Generated greeting: {greeting}")

    # Save a checkpoint
    context.save_checkpoint("greetings_generated", {
        "count": len(greetings),
        "name": name
    })

    return {
        "greetings": greetings,
        "total_count": count,
        "org_id": context.org_id,
        "org_name": context.org_name
    }
