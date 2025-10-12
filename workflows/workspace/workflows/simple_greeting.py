"""
Simple Greeting Workflow
A basic workflow for testing form submission and instant responses
"""

from engine.shared.decorators import workflow, param


@workflow(
    name="simple_greeting",
    description="Generate a personalized greeting message (instant response)",
    category="testing",
    tags=["test", "demo", "greeting"]
)
@param(
    "name",
    type="string",
    label="Your Name",
    required=True,
    help_text="Enter your name to receive a personalized greeting"
)
@param(
    "greeting_type",
    type="string",
    label="Greeting Type",
    required=False,
    default_value="Hello",
    help_text="Type of greeting (Hello, Hi, Welcome, etc.)"
)
@param(
    "include_time",
    type="bool",
    label="Include Timestamp",
    required=False,
    default_value=False,
    help_text="Include current date/time in the greeting"
)
async def generate_greeting(
    context,
    name: str,
    greeting_type: str = "Hello",
    include_time: bool = False
):
    """
    Generate a personalized greeting message.

    This is a simple synchronous workflow that returns immediately,
    perfect for testing form submission and result display.

    Args:
        context: OrganizationContext with org_id, credentials, etc.
        name: User's name
        greeting_type: Type of greeting to use
        include_time: Whether to include timestamp

    Returns:
        dict: {
            "success": bool,
            "message": str,
            "greeting": str,
            "timestamp": str (optional)
        }
    """
    from datetime import datetime

    # Log workflow start
    context.log("info", f"Starting greeting generation for {name}")

    greeting = f"{greeting_type}, {name}!"

    # Log the greeting type being used
    context.log("debug", f"Using greeting type: {greeting_type}")

    # Check if country was passed as an extra variable
    # Extra variables are injected into context even if not in function signature
    country = context.get_variable("country")
    if country:
        greeting = f"{greeting_type}, {name} from {country}!"
        context.log("info", f"Country extra variable detected: {country}")

    result = {
        "success": True,
        "message": "Greeting generated successfully",
        "greeting": greeting,
        "input_name": name,
        "input_type": greeting_type
    }

    # Include country in result if it was provided
    if country:
        result["country"] = country

    if include_time:
        timestamp = datetime.utcnow().isoformat()
        result["timestamp"] = timestamp
        result["greeting"] = f"{greeting} The time is {timestamp}"
        context.log("info", "Timestamp included in greeting", {"timestamp": timestamp})

    # Log successful completion
    context.log("info", "Greeting generated successfully", {"greeting_length": len(greeting)})

    return result
