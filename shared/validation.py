"""
Validation helpers for API endpoints
Reduces code duplication across endpoint files
"""

import json

import azure.functions as func

from shared.models import ErrorResponse


def validate_scope_parameter(scope: str, org_id: str | None) -> tuple[bool, func.HttpResponse | None]:
    """
    Validate scope parameter and orgId requirement.

    Args:
        scope: Scope parameter value (should be "global" or "org")
        org_id: Organization ID (required when scope="org")

    Returns:
        Tuple of (is_valid, error_response)
        - If valid: (True, None)
        - If invalid: (False, HttpResponse with error)
    """
    # Normalize to lowercase
    scope_lower = scope.lower()

    # Validate scope value
    if scope_lower not in ["global", "org"]:
        error = ErrorResponse(
            error="BadRequest",
            message="scope parameter must be 'global' or 'org'"
        )
        return False, func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    # If scope=org, orgId is required
    if scope_lower == "org" and not org_id:
        error = ErrorResponse(
            error="BadRequest",
            message="orgId parameter is required when scope=org"
        )
        return False, func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    return True, None


def create_error_response(
    error_type: str,
    message: str,
    status_code: int = 400,
    details: dict | None = None
) -> func.HttpResponse:
    """
    Create a standardized error response.

    Args:
        error_type: Error type (e.g., "BadRequest", "NotFound")
        message: Error message
        status_code: HTTP status code (default 400)
        details: Optional additional details

    Returns:
        HttpResponse with error
    """
    error = ErrorResponse(
        error=error_type,
        message=message,
        details=details
    )
    return func.HttpResponse(
        json.dumps(error.model_dump()),
        status_code=status_code,
        mimetype="application/json"
    )


def check_key_vault_available(kv_manager) -> tuple[bool, func.HttpResponse | None]:
    """
    Check if Key Vault manager is available.

    Args:
        kv_manager: KeyVaultClient instance (or None if not initialized)

    Returns:
        Tuple of (is_available, error_response)
        - If available: (True, None)
        - If unavailable: (False, HttpResponse with error)
    """
    if not kv_manager:
        return False, create_error_response(
            error_type="ServiceUnavailable",
            message="Key Vault service is not configured",
            status_code=503
        )

    return True, None
