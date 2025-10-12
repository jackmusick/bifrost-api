"""
Example: Error Handling

Demonstrates proper error handling with ValidationError and IntegrationError.
"""

from engine.shared.decorators import workflow, param
from engine.shared.context import OrganizationContext
from engine.shared.error_handling import ValidationError, IntegrationError


@workflow(
    name="error_handling_example",
    description="Demonstrates error handling best practices",
    category="Examples"
)
@param("operation", str, "Operation to perform: validate, integrate, success", required=True)
async def error_handling_example(context: OrganizationContext, operation: str) -> dict:
    """
    Workflow demonstrating error handling patterns.

    Args:
        context: Organization context
        operation: Which type of operation to demonstrate

    Returns:
        dict: Result of operation

    Raises:
        ValidationError: For validation operation
        IntegrationError: For integrate operation
    """
    context.log(f"Running operation: {operation}")

    if operation == "validate":
        # Demonstrate validation error (returns HTTP 400)
        raise ValidationError(
            message="Invalid operation parameter",
            details={"operation": operation, "allowed": ["validate", "integrate", "success"]}
        )

    elif operation == "integrate":
        # Demonstrate integration error (returns HTTP 500)
        raise IntegrationError(
            message="Failed to connect to external API",
            details={"api": "ExampleAPI", "reason": "Connection timeout"}
        )

    elif operation == "success":
        # Successful execution
        return {
            "status": "success",
            "message": "Operation completed successfully",
            "operation": operation
        }

    else:
        # Unknown operation
        raise ValidationError(
            message=f"Unknown operation: {operation}",
            details={"provided": operation, "allowed": ["validate", "integrate", "success"]}
        )
