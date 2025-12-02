"""
Response Helper Functions
Utility functions to reduce boilerplate in HTTP response handlers.
Eliminates repetitive error response and success response patterns.
"""

import json
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    import azure.functions as func

from src.models.schemas import ErrorResponse


def error_response(
    error_type: str,
    message: str,
    status_code: int,
    details: Optional[dict] = None
) -> "func.HttpResponse":
    """
    Create a standardized error response.

    Args:
        error_type: Error category (e.g., "NotFound", "ValidationError")
        message: Human-readable error message
        status_code: HTTP status code
        details: Optional additional error details

    Returns:
        func.HttpResponse with JSON error payload

    Example:
        return error_response("NotFound", "Connection not found", 404)
    """
    error = ErrorResponse(error=error_type, message=message, details=details)
    return func.HttpResponse(
        json.dumps(error.model_dump()),
        status_code=status_code,
        mimetype="application/json"
    )


def success_response(
    data: Any,
    status_code: int = 200
) -> "func.HttpResponse":
    """
    Create a standardized success response.

    Args:
        data: Response data (dict, Pydantic model, or JSON-serializable object)
        status_code: HTTP status code (default: 200)

    Returns:
        func.HttpResponse with JSON payload

    Example:
        return success_response(connection.model_dump(mode="json"), 201)
    """
    # Handle Pydantic models
    if hasattr(data, 'model_dump'):
        data = data.model_dump(mode="json")

    return func.HttpResponse(
        json.dumps(data),
        status_code=status_code,
        mimetype="application/json"
    )


# Common error response shortcuts
def not_found(resource: str, identifier: str) -> "func.HttpResponse":
    """404 Not Found response"""
    return error_response(
        "NotFound",
        f"{resource} '{identifier}' not found",
        404
    )


def conflict(resource: str, identifier: str) -> "func.HttpResponse":
    """409 Conflict response (duplicate)"""
    return error_response(
        "Conflict",
        f"{resource} '{identifier}' already exists",
        409
    )


def validation_error(message: str = "Invalid request data", errors: Optional[list] = None) -> "func.HttpResponse":
    """400 Validation Error response"""
    details = {"errors": errors} if errors else None
    return error_response("ValidationError", message, 400, details)


def bad_request(message: str) -> "func.HttpResponse":
    """400 Bad Request response"""
    return error_response("BadRequest", message, 400)


def internal_error(message: str = "An internal error occurred") -> "func.HttpResponse":
    """500 Internal Server Error response"""
    return error_response("InternalServerError", message, 500)


def service_unavailable(message: str) -> "func.HttpResponse":
    """503 Service Unavailable response"""
    return error_response("ServiceUnavailable", message, 503)
