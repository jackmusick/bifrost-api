"""
Unit tests for RequestContext system

Tests pure business logic (dataclass properties, scope calculations)
and simple HTTP parsing (function keys, EasyAuth header parsing).

Complex integration scenarios (user provisioning, org lookup) are covered by:
- tests/unit/test_user_lookup.py (business logic with mocked repos)
- tests/unit/test_user_provisioning.py (business logic with mocked repos)
- tests/integration/test_user_provisioning_journey.py (real HTTP + Azurite)
"""

import base64
import json
from unittest.mock import Mock, patch

import azure.functions as func
import pytest

from shared.request_context import RequestContext, get_request_context


class TestRequestContextCreation:
    """Test RequestContext dataclass creation and properties (pure unit tests)"""

    def test_platform_admin_context_with_org(self):
        """Platform admin context with org_id specified"""
        context = RequestContext(
            user_id="admin@example.com",
            email="admin@example.com",
            name="Admin User",
            org_id="org-123",
            is_platform_admin=True,
            is_function_key=False
        )

        assert context.user_id == "admin@example.com"
        assert context.email == "admin@example.com"
        assert context.org_id == "org-123"
        assert context.scope == "org-123"
        assert context.is_platform_admin is True
        assert context.is_function_key is False

    def test_platform_admin_context_global_scope(self):
        """Platform admin context with GLOBAL scope (no org_id)"""
        context = RequestContext(
            user_id="admin@example.com",
            email="admin@example.com",
            name="Admin User",
            org_id=None,
            is_platform_admin=True,
            is_function_key=False
        )

        assert context.user_id == "admin@example.com"
        assert context.org_id is None
        assert context.scope == "GLOBAL"
        assert context.is_platform_admin is True

    def test_regular_user_context(self):
        """Regular user context with fixed org_id"""
        context = RequestContext(
            user_id="user@example.com",
            email="user@example.com",
            name="Regular User",
            org_id="org-456",
            is_platform_admin=False,
            is_function_key=False
        )

        assert context.user_id == "user@example.com"
        assert context.org_id == "org-456"
        assert context.scope == "org-456"
        assert context.is_platform_admin is False
        assert context.is_function_key is False

    def test_function_key_context_global(self):
        """Function key authentication with GLOBAL scope"""
        context = RequestContext(
            user_id="system",
            email="system@local",
            name="System",
            org_id=None,
            is_platform_admin=True,
            is_function_key=True
        )

        assert context.user_id == "system"
        assert context.org_id is None
        assert context.scope == "GLOBAL"
        assert context.is_platform_admin is True
        assert context.is_function_key is True

    def test_function_key_context_with_org(self):
        """Function key authentication with org_id specified"""
        context = RequestContext(
            user_id="system",
            email="system@local",
            name="System",
            org_id="org-789",
            is_platform_admin=True,
            is_function_key=True
        )

        assert context.scope == "org-789"
        assert context.is_platform_admin is True


class TestHttpParsing:
    """Test HTTP header parsing (infrastructure layer, minimal mocking)"""

    def test_function_key_auth_global_scope(self):
        """Function key authentication without org header creates GLOBAL context"""
        req = Mock(spec=func.HttpRequest)
        req.headers = {'x-functions-key': 'test-key'}
        req.params = {}

        context = get_request_context(req)

        assert context.user_id == "system"
        assert context.email == "system@local"
        assert context.org_id is None
        assert context.scope == "GLOBAL"
        assert context.is_platform_admin is True
        assert context.is_function_key is True

    def test_function_key_auth_with_org_header(self):
        """Function key authentication with org header creates org-scoped context"""
        req = Mock(spec=func.HttpRequest)
        req.headers = {
            'x-functions-key': 'test-key',
            'X-Organization-Id': 'org-123'
        }
        req.params = {}

        context = get_request_context(req)

        assert context.user_id == "system"
        assert context.org_id == "org-123"
        assert context.scope == "org-123"
        assert context.is_platform_admin is True
        assert context.is_function_key is True

    @patch("shared.user_lookup.ensure_user_exists_in_db")
    @patch("shared.user_lookup.get_user_organization")
    def test_platform_admin_user_global_scope(self, mock_get_org, mock_ensure_user):
        """Platform admin user without org header uses GLOBAL scope"""
        principal = {
            "userId": "admin@example.com",
            "userDetails": "admin@example.com",
            "userRoles": ["authenticated", "PlatformAdmin"]
        }
        principal_header = base64.b64encode(json.dumps(principal).encode()).decode()

        req = Mock(spec=func.HttpRequest)
        req.headers = {"X-MS-CLIENT-PRINCIPAL": principal_header}
        req.params = {}

        context = get_request_context(req)

        assert context.email == "admin@example.com"
        assert context.is_platform_admin is True
        assert context.org_id is None
        assert context.scope == "GLOBAL"
        # Note: ensure_user_exists_in_db is now called in GetRoles endpoint, not here

    @patch("shared.user_lookup.ensure_user_exists_in_db")
    @patch("shared.user_lookup.get_user_organization")
    def test_platform_admin_user_with_org_header(self, mock_get_org, mock_ensure_user):
        """Platform admin user with org header uses specified org"""
        principal = {
            "userId": "admin@example.com",
            "userDetails": "admin@example.com",
            "userRoles": ["authenticated", "PlatformAdmin"]
        }
        principal_header = base64.b64encode(json.dumps(principal).encode()).decode()

        req = Mock(spec=func.HttpRequest)
        req.headers = {
            "X-MS-CLIENT-PRINCIPAL": principal_header,
            "X-Organization-Id": "org-456"
        }
        req.params = {}

        context = get_request_context(req)

        assert context.email == "admin@example.com"
        assert context.org_id == "org-456"
        assert context.scope == "org-456"

    @patch("shared.user_lookup.ensure_user_exists_in_db")
    @patch("shared.user_lookup.get_user_organization")
    def test_regular_user_with_org(self, mock_get_org, mock_ensure_user):
        """Regular user gets org_id from database lookup"""
        mock_get_org.return_value = "org-789"

        principal = {
            "userId": "user@example.com",
            "userDetails": "user@example.com",
            "userRoles": ["authenticated"]
        }
        principal_header = base64.b64encode(json.dumps(principal).encode()).decode()

        req = Mock(spec=func.HttpRequest)
        req.headers = {"X-MS-CLIENT-PRINCIPAL": principal_header}
        req.params = {}

        context = get_request_context(req)

        assert context.email == "user@example.com"
        assert context.is_platform_admin is False
        assert context.org_id == "org-789"
        assert context.scope == "org-789"
        # Note: ensure_user_exists_in_db is now called in GetRoles endpoint, not here
        mock_get_org.assert_called_once_with("user@example.com")

    @patch("shared.user_lookup.ensure_user_exists_in_db")
    @patch("shared.user_lookup.get_user_organization")
    def test_regular_user_cannot_override_org(self, mock_get_org, mock_ensure_user):
        """Regular user attempting to set org header gets error"""
        mock_get_org.return_value = "org-789"

        principal = {
            "userId": "user@example.com",
            "userDetails": "user@example.com",
            "userRoles": ["authenticated"]
        }
        principal_header = base64.b64encode(json.dumps(principal).encode()).decode()

        req = Mock(spec=func.HttpRequest)
        req.headers = {
            "X-MS-CLIENT-PRINCIPAL": principal_header,
            "X-Organization-Id": "org-different"  # User tries to override
        }
        req.params = {}

        with pytest.raises(PermissionError, match="Only platform administrators"):
            get_request_context(req)


class TestContextScoping:
    """Test context scoping logic (pure unit tests)"""

    def test_scoped_table_uses_context_scope(self):
        """Org-scoped context uses org_id as partition key"""
        context = RequestContext(
            user_id="user@example.com",
            email="user@example.com",
            name="User",
            org_id="org-123",
            is_platform_admin=False,
            is_function_key=False
        )

        assert context.scope == "org-123"

    def test_global_context_scoping(self):
        """GLOBAL context uses 'GLOBAL' as partition key"""
        context = RequestContext(
            user_id="admin@example.com",
            email="admin@example.com",
            name="Admin",
            org_id=None,
            is_platform_admin=True,
            is_function_key=False
        )

        assert context.scope == "GLOBAL"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
