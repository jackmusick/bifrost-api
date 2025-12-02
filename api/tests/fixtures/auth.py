"""
Test authentication helpers for integration tests.

Provides JWT token generation and HTTP header helpers for testing
authenticated endpoints with real HTTP requests to the FastAPI server.
"""

from datetime import datetime, timedelta

import jwt


def create_test_jwt(
    user_id: str = "test-user-123",
    email: str = "test@example.com",
    name: str = "Test User"
) -> str:
    """
    Create test JWT token for authentication.

    In integration tests, this bypasses real Azure AD/Entra and allows
    testing with any email/user combination.

    Args:
        user_id: User OID (object ID) - typically a UUID
        email: User email address
        name: User display name

    Returns:
        str: JWT token (unsigned for testing)

    Example:
        >>> token = create_test_jwt(email="john@acme.com", name="John Doe")
        >>> headers = auth_headers(token)
        >>> response = requests.get("/api/organizations", headers=headers)
    """
    payload = {
        "oid": user_id,
        "preferred_username": email,
        "name": name,
        "exp": datetime.utcnow() + timedelta(hours=2),
        "iat": datetime.utcnow(),
        "iss": "https://login.microsoftonline.com/test-tenant/v2.0",
        "aud": "test-client-id"
    }
    # Sign with test secret (middleware should accept this in test mode)
    return jwt.encode(payload, "test-secret", algorithm="HS256")


def auth_headers(token: str) -> dict[str, str]:
    """
    Create authorization headers with JWT token.

    Args:
        token: JWT token from create_test_jwt()

    Returns:
        dict: Headers with Authorization bearer token

    Example:
        >>> token = create_test_jwt(email="user@test.com")
        >>> headers = auth_headers(token)
        >>> response = requests.get(url, headers=headers)
    """
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def org_headers(org_id: str, token: str) -> dict[str, str]:
    """
    Create headers with organization context and authentication.

    Args:
        org_id: Organization ID
        token: JWT token from create_test_jwt()

    Returns:
        dict: Headers with auth + organization context

    Example:
        >>> token = create_test_jwt(email="user@acme.com")
        >>> headers = org_headers("org-123", token)
        >>> response = requests.post(url, json={...}, headers=headers)
    """
    return {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": org_id,
        "Content-Type": "application/json",
    }
