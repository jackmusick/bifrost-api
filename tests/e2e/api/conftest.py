"""
E2E API test fixtures.

E2E tests inherit fixtures from integration tests since they use the same
test infrastructure (Azurite, Azure Functions running locally).

The only difference is that E2E tests also require KeyVault to be configured.
"""

# Import all integration test fixtures
from tests.integration.api.conftest import (
    api_base_url,
    azurite_connection_string,
    table_service,
    test_org_id,
    auth_headers,
    platform_admin_headers,
    admin_headers,
    user_headers,
    regular_user_headers,
    test_oauth_connection,
    test_form,
    test_role,
)

__all__ = [
    "api_base_url",
    "azurite_connection_string",
    "table_service",
    "test_org_id",
    "auth_headers",
    "platform_admin_headers",
    "admin_headers",
    "user_headers",
    "regular_user_headers",
    "test_oauth_connection",
    "test_form",
    "test_role",
]
