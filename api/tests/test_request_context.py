"""
Unit tests for RequestContext system
Tests context creation, scope determination, and user type detection
"""

import pytest
import json
import base64
from unittest.mock import Mock, MagicMock
from shared.request_context import RequestContext, get_request_context
from shared.storage import TableStorageService
import azure.functions as func


class TestRequestContextCreation:
    """Test RequestContext object creation and properties"""

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
        assert context.is_function_key is True


class TestGetRequestContext:
    """Test get_request_context() function with various auth scenarios"""

    @pytest.fixture
    def mock_users_table(self, monkeypatch):
        """Mock Users table for user lookups"""
        mock_users_table = Mock(spec=TableStorageService)
        mock_relationships_table = Mock(spec=TableStorageService)

        def mock_table_service_init(table_name):
            if table_name == "Users":
                return mock_users_table
            elif table_name == "Relationships":
                return mock_relationships_table
            return Mock(spec=TableStorageService)

        monkeypatch.setattr("shared.storage.TableStorageService", mock_table_service_init)
        return mock_users_table

    def test_function_key_auth_global_scope(self, mock_users_table):
        """Function key auth with no X-Organization-Id header"""
        req = Mock(spec=func.HttpRequest)
        req.headers = {
            "x-functions-key": "test-key"
        }
        req.params = {}

        context = get_request_context(req)

        assert context.is_function_key is True
        assert context.is_platform_admin is True
        assert context.org_id is None
        assert context.scope == "GLOBAL"

    def test_function_key_auth_with_org_header(self, mock_users_table):
        """Function key auth with X-Organization-Id header"""
        req = Mock(spec=func.HttpRequest)
        req.headers = {
            "x-functions-key": "test-key",
            "X-Organization-Id": "org-123"
        }
        req.params = {}

        context = get_request_context(req)

        assert context.is_function_key is True
        assert context.is_platform_admin is True
        assert context.org_id == "org-123"
        assert context.scope == "org-123"

    def test_platform_admin_user_global_scope(self, mock_users_table):
        """Platform admin user with no X-Organization-Id header"""
        # Mock user lookup - platform admin
        mock_users_table.get_entity.return_value = {
            "PartitionKey": "admin@example.com",
            "RowKey": "user",
            "Email": "admin@example.com",
            "Name": "Admin User",
            "IsPlatformAdmin": True,
            "UserType": "PLATFORM"
        }

        # Create principal header (base64 encoded JSON)
        import base64
        principal = {"userId": "admin@example.com", "userDetails": "admin@example.com"}
        principal_header = base64.b64encode(json.dumps(principal).encode()).decode()

        req = Mock(spec=func.HttpRequest)
        req.headers = {
            "X-MS-CLIENT-PRINCIPAL": principal_header
        }
        req.params = {}

        context = get_request_context(req)

        assert context.user_id == "admin@example.com"
        assert context.is_platform_admin is True
        assert context.org_id is None
        assert context.scope == "GLOBAL"

    def test_platform_admin_user_with_org_header(self, mock_users_table):
        """Platform admin user switching to specific org scope"""
        # Mock user lookup - platform admin
        mock_users_table.get_entity.return_value = {
            "PartitionKey": "admin@example.com",
            "RowKey": "user",
            "Email": "admin@example.com",
            "Name": "Admin User",
            "IsPlatformAdmin": True,
            "UserType": "PLATFORM"
        }

        # Create principal header (base64 encoded JSON)
        import base64
        principal = {"userId": "admin@example.com", "userDetails": "admin@example.com"}
        principal_header = base64.b64encode(json.dumps(principal).encode()).decode()

        req = Mock(spec=func.HttpRequest)
        req.headers = {
            "X-MS-CLIENT-PRINCIPAL": principal_header,
            "X-Organization-Id": "org-456"
        }
        req.params = {}

        context = get_request_context(req)

        assert context.user_id == "admin@example.com"
        assert context.is_platform_admin is True
        assert context.org_id == "org-456"
        assert context.scope == "org-456"

    def test_regular_user_with_org(self, mock_users_table, monkeypatch):
        """Regular user with fixed org_id from database"""
        # Mock user lookup - regular user (not platform admin)
        mock_users_table.get_entity.return_value = {
            "PartitionKey": "user@example.com",
            "RowKey": "user",
            "Email": "user@example.com",
            "Name": "Regular User",
            "IsPlatformAdmin": False,
            "UserType": "ORG"
        }

        # Mock relationships table to return org assignment
        mock_relationships_table = Mock(spec=TableStorageService)
        mock_relationships_table.query_entities.return_value = [
            {"RowKey": "userperm:user@example.com:org-789"}
        ]

        def mock_table_service_init(table_name):
            if table_name == "Users":
                return mock_users_table
            elif table_name == "Relationships":
                return mock_relationships_table
            return Mock(spec=TableStorageService)

        monkeypatch.setattr("shared.storage.TableStorageService", mock_table_service_init)

        # Create principal header (base64 encoded JSON)
        import base64
        principal = {"userId": "user@example.com", "userDetails": "user@example.com"}
        principal_header = base64.b64encode(json.dumps(principal).encode()).decode()

        req = Mock(spec=func.HttpRequest)
        req.headers = {
            "X-MS-CLIENT-PRINCIPAL": principal_header
        }
        req.params = {}

        context = get_request_context(req)

        assert context.user_id == "user@example.com"
        assert context.is_platform_admin is False
        assert context.org_id == "org-789"
        assert context.scope == "org-789"

    def test_regular_user_ignores_org_header(self, mock_users_table, monkeypatch):
        """Regular user cannot override org_id via header - raises PermissionError"""
        # Mock user lookup - regular user (not platform admin)
        mock_users_table.get_entity.return_value = {
            "PartitionKey": "user@example.com",
            "RowKey": "user",
            "Email": "user@example.com",
            "Name": "Regular User",
            "IsPlatformAdmin": False,
            "UserType": "ORG"
        }

        # Mock relationships table to return org assignment
        mock_relationships_table = Mock(spec=TableStorageService)
        mock_relationships_table.query_entities.return_value = [
            {"RowKey": "userperm:user@example.com:org-789"}
        ]

        def mock_table_service_init(table_name):
            if table_name == "Users":
                return mock_users_table
            elif table_name == "Relationships":
                return mock_relationships_table
            return Mock(spec=TableStorageService)

        monkeypatch.setattr("shared.storage.TableStorageService", mock_table_service_init)

        # Create principal header (base64 encoded JSON)
        import base64
        principal = {"userId": "user@example.com", "userDetails": "user@example.com"}
        principal_header = base64.b64encode(json.dumps(principal).encode()).decode()

        req = Mock(spec=func.HttpRequest)
        req.headers = {
            "X-MS-CLIENT-PRINCIPAL": principal_header,
            "X-Organization-Id": "org-different"  # Should raise PermissionError
        }
        req.params = {}

        # Regular user attempting to override org_id should raise PermissionError
        with pytest.raises(PermissionError, match="Only platform administrators"):
            get_request_context(req)

    def test_local_dev_mode(self, mock_users_table):
        """Local development mode with no auth headers"""
        req = Mock(spec=func.HttpRequest)
        req.headers = {}
        req.params = {}

        context = get_request_context(req)

        assert context.user_id == "local-dev"
        assert context.is_platform_admin is True
        assert context.is_function_key is True
        assert context.org_id is None
        assert context.scope == "GLOBAL"


class TestContextScoping:
    """Test context scoping logic for table queries"""

    def test_scoped_table_uses_context_scope(self):
        """Scoped tables (Config, Entities) use context.scope as PartitionKey"""
        context = RequestContext(
            user_id="user@example.com",
            email="user@example.com",
            name="User",
            org_id="org-123",
            is_platform_admin=False,
            is_function_key=False
        )

        # When using get_table_service with context, queries are automatically scoped
        assert context.scope == "org-123"

    def test_global_context_scoping(self):
        """GLOBAL context uses 'GLOBAL' as PartitionKey"""
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
