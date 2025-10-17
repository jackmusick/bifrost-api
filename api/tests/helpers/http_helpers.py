"""
Helper utilities for creating mock Azure Functions HttpRequest objects in tests.

This module provides utilities for integration tests that call Azure Functions
directly without going through HTTP.
"""

import base64
import json
from typing import Any
from urllib.parse import urlencode

import azure.functions as func


def create_mock_request(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | str | bytes | None = None,
    route_params: dict[str, str] | None = None,
    query_params: dict[str, str] | None = None,
) -> func.HttpRequest:
    """
    Create a mock HttpRequest object for testing Azure Functions.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        url: Request URL (e.g., "/api/oauth/connections")
        headers: Optional HTTP headers dict
        body: Optional request body (dict will be JSON-encoded)
        route_params: Optional route parameters (e.g., {"connection_name": "test"})
        query_params: Optional query parameters

    Returns:
        Azure Functions HttpRequest object

    Example:
        >>> req = create_mock_request(
        ...     method="POST",
        ...     url="/api/oauth/connections",
        ...     headers={"Content-Type": "application/json"},
        ...     body={"connection_name": "test"}
        ... )
    """
    # Convert body to bytes if needed
    body_bytes = None
    if body is not None:
        if isinstance(body, dict):
            body_bytes = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            body_bytes = body.encode("utf-8")
        elif isinstance(body, bytes):
            body_bytes = body
        else:
            raise ValueError(f"Unsupported body type: {type(body)}")

    # Build URL with query params
    full_url = url
    if query_params:
        full_url = f"{url}?{urlencode(query_params)}"

    # Create request
    req = func.HttpRequest(
        method=method,
        url=full_url,
        headers=headers or {},
        body=body_bytes,
        route_params=route_params or {},
    )

    return req


def create_platform_admin_headers(user_email: str = "jack@gocovi.com") -> dict[str, str]:
    """
    Create headers for platform admin user.

    Args:
        user_email: User email (default: jack@gocovi.com)

    Returns:
        Headers dict with X-MS-Client-Principal for platform admin
    """
    client_principal = {
        "identityProvider": "aad",
        "userId": user_email,
        "userDetails": user_email,
        "userRoles": ["authenticated", "PlatformAdmin"],
    }

    encoded = base64.b64encode(json.dumps(client_principal).encode()).decode()

    return {
        "X-MS-Client-Principal": encoded,
        "Content-Type": "application/json",
    }


def create_org_user_headers(user_email: str = "jack@gocovi.dev") -> dict[str, str]:
    """
    Create headers for org user.

    Args:
        user_email: User email (default: jack@gocovi.dev)

    Returns:
        Headers dict with X-MS-Client-Principal for org user
    """
    client_principal = {
        "identityProvider": "aad",
        "userId": user_email,
        "userDetails": user_email,
        "userRoles": ["authenticated"],
    }

    encoded = base64.b64encode(json.dumps(client_principal).encode()).decode()

    return {
        "X-MS-Client-Principal": encoded,
        "Content-Type": "application/json",
    }


def create_anonymous_headers() -> dict[str, str]:
    """
    Create headers for anonymous requests (no authentication).

    Returns:
        Headers dict with just Content-Type
    """
    return {
        "Content-Type": "application/json",
    }


def parse_response(response: func.HttpResponse) -> tuple[int, dict[str, Any] | None]:
    """
    Parse an Azure Functions HttpResponse.

    Args:
        response: HttpResponse object from Azure Function

    Returns:
        Tuple of (status_code, body_dict)
        Body dict is None if response has no body or body is not JSON

    Raises:
        AssertionError: If response has body but JSON parsing fails for status codes
                       that should return JSON (200, 201, 400, 403, 404, 500)

    Example:
        >>> status, body = parse_response(response)
        >>> assert status == 200
        >>> assert body["connection_name"] == "test"
    """
    status_code = response.status_code

    # Try to parse body as JSON
    body_dict = None
    if response.get_body():
        try:
            body_dict = json.loads(response.get_body().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            # For status codes that should return JSON, fail loudly
            if status_code in [200, 201, 400, 403, 404, 500]:
                body_preview = response.get_body().decode("utf-8", errors="replace")[:200]
                raise AssertionError(
                    f"Expected JSON response for status {status_code}, but parsing failed: {e}\n"
                    f"Body preview: {body_preview}"
                )
            # For other status codes (204, 301, etc.), empty body is acceptable
            pass

    return status_code, body_dict
