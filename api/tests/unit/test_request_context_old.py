"""
Unit tests for RequestContext system
Tests context creation, scope determination, and user type detection
"""

import base64
import json
from unittest.mock import Mock

import azure.functions as func
import pytest

from shared.request_context import RequestContext, get_request_context
from shared.storage import TableStorageService


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

    @pytest.fixture(scope="function")
    def mock_tables(self, monkeypatch):
        """Mock Users, Entities, and Relationships tables for user lookups

        Creates fresh mocks for each test to prevent state pollution.
        """
        # These will be shared across all instances of the same table
        mock_users_table = Mock(spec=TableStorageService)
        mock_entities_table = Mock(spec=TableStorageService)
        mock_relationships_table = Mock(spec=TableStorageService)

        # Configure default returns to avoid Mock objects being returned
        mock_entities_table.get_entity.return_value = None
        mock_entities_table.query_entities.return_value = []
        mock_relationships_table.query_entities.return_value = []
        # Also set update_entity to avoid Mock issues
        mock_entities_table.update_entity = Mock()

        def mock_table_service_init(table_name, context=None):
            # Return the SAME mock instance for each table name
            # This ensures configuration in tests persists across repository instantiations
            if table_name == "Users":
                return mock_users_table
            elif table_name == "Entities":
                return mock_entities_table
            elif table_name == "Relationships":
                return mock_relationships_table
            return Mock(spec=TableStorageService)

        monkeypatch.setattr("shared.storage.TableStorageService", mock_table_service_init)

        # Return dict with all mocks so tests can configure them
        return {
            "users": mock_users_table,
            "entities": mock_entities_table,
            "relationships": mock_relationships_table
        }

    def test_function_key_auth_global_scope(self, mock_tables):
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

    def test_function_key_auth_with_org_header(self, mock_tables):
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

    def test_platform_admin_user_global_scope(self, mock_tables):
        """Platform admin user with no X-Organization-Id header"""
        # Create principal header (base64 encoded JSON) with PlatformAdmin role
        import base64
        principal = {
            "userId": "admin@example.com",
            "userDetails": "admin@example.com",
            "userRoles": ["authenticated", "PlatformAdmin"]  # Role from GetRoles
        }
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

    def test_platform_admin_user_with_org_header(self, mock_tables):
        """Platform admin user switching to specific org scope"""
        # Create principal header (base64 encoded JSON) with PlatformAdmin role
        import base64
        principal = {
            "userId": "admin@example.com",
            "userDetails": "admin@example.com",
            "userRoles": ["authenticated", "PlatformAdmin"]  # Role from GetRoles
        }
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

    def test_regular_user_with_org(self, mock_tables, monkeypatch):
        """Regular user with fixed org_id from database"""
        from shared.repositories.users import UserRepository
        from shared.models import User, UserType
        from datetime import datetime

        # Create a real User object to return
        test_user = User(
            id="user@example.com",
            email="user@example.com",
            displayName="Regular User",
            userType=UserType.ORG,
            isPlatformAdmin=False,
            isActive=True,
            createdAt=datetime(2024, 1, 1),
            lastLogin=datetime(2024, 1, 1)
        )

        # Mock UserRepository methods directly
        def mock_get_user(email: str):
            if email == "user@example.com":
                return test_user
            return None

        def mock_get_user_org_id(email: str):
            if email == "user@example.com":
                return "org-789"
            return None

        def mock_update_last_login(email: str):
            pass

        monkeypatch.setattr(UserRepository, "get_user", lambda self, email: mock_get_user(email))
        monkeypatch.setattr(UserRepository, "get_user_org_id", lambda self, email: mock_get_user_org_id(email))
        monkeypatch.setattr(UserRepository, "update_last_login", lambda self, email: mock_update_last_login(email))

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

    def test_regular_user_ignores_org_header(self, mock_tables):
        """Regular user cannot override org_id via header - raises PermissionError"""
        # Configure Entities table mock to return existing user
        mock_tables["entities"].get_entity.return_value = {
            "PartitionKey": "GLOBAL",
            "RowKey": "user:user@example.com",
            "Email": "user@example.com",
            "DisplayName": "Regular User",
            "IsPlatformAdmin": False,
            "UserType": "ORG",
            "IsActive": True,
            "CreatedAt": "2024-01-01T00:00:00Z",
            "LastLogin": "2024-01-01T00:00:00Z"
        }

        # Configure relationships table mock to return org assignment
        mock_tables["relationships"].query_entities.return_value = [
            {"RowKey": "userperm:user@example.com:org-789"}
        ]

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

    # NOTE: First user auto-promotion and platform admin auto-creation
    # now happen in GetRoles endpoint, not in request_context
    # These tests are moved to test_roles_source.py

    @pytest.mark.skip(reason="User auto-provisioning moved to GetRoles endpoint")
    def test_first_user_auto_promotion_to_platform_admin(self, mock_tables):
        """DEPRECATED: First user auto-promotion now happens in GetRoles"""
        pass

    @pytest.mark.skip(reason="User auto-provisioning moved to GetRoles endpoint")
    def test_platform_admin_auto_creation(self, mock_tables):
        """DEPRECATED: Platform admin auto-creation now happens in GetRoles"""
        pass

    def test_user_without_platform_admin_role_not_created(self, mock_tables, monkeypatch):
        """User without PlatformAdmin role should not be auto-created (when not first user)"""
        # Mock user lookup - user doesn't exist
        from azure.core.exceptions import ResourceNotFoundError
        mock_tables["users"].get_entity.side_effect = ResourceNotFoundError("Entity not found")

        # Mock query_entities to return existing users (not first user)
        mock_tables["users"].query_entities.return_value = [
            {"PartitionKey": "existing@example.com", "RowKey": "user"}
        ]

        # Mock relationships table (for org lookup)
        mock_relationships_table = Mock(spec=TableStorageService)
        mock_relationships_table.query_entities.return_value = []

        # Mock entities table (for domain-based provisioning)
        mock_entities_table = Mock(spec=TableStorageService)
        mock_entities_table.query_entities.return_value = []

        def mock_table_service_init(table_name, context=None):
            if table_name == "Users":
                return mock_tables["users"]
            elif table_name == "Relationships":
                return mock_relationships_table
            elif table_name == "Entities":
                return mock_entities_table
            return Mock(spec=TableStorageService)

        monkeypatch.setattr("shared.storage.TableStorageService", mock_table_service_init)

        # Create principal WITHOUT PlatformAdmin role
        principal = {
            "userId": "regular@example.com",
            "userDetails": "regular@example.com",
            "userRoles": ["authenticated"]  # No PlatformAdmin role
        }
        principal_header = base64.b64encode(json.dumps(principal).encode()).decode()

        req = Mock(spec=func.HttpRequest)
        req.headers = {
            "X-MS-CLIENT-PRINCIPAL": principal_header
        }
        req.params = {}

        # Should fail because user doesn't exist and has no org assignment
        with pytest.raises(ValueError, match="has no organization assignment"):
            get_request_context(req)

        # Verify user was NOT auto-created
        mock_tables["users"].insert_entity.assert_not_called()

    def test_local_dev_mode(self, mock_tables):
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

    @pytest.mark.skip(reason="User auto-provisioning moved to GetRoles endpoint")
    def test_domain_based_auto_provisioning_success(self, mock_tables, monkeypatch):
        """DEPRECATED: Domain-based auto-provisioning now happens in GetRoles"""
        pass

    def test_domain_based_auto_provisioning_no_matching_domain(self, mock_tables, monkeypatch):
        """User not auto-provisioned when no matching domain found"""
        from azure.core.exceptions import ResourceNotFoundError

        # Mock user lookup - user doesn't exist
        mock_tables["users"].get_entity.side_effect = ResourceNotFoundError("Entity not found")

        # Mock relationships table - no existing assignments
        mock_relationships_table = Mock(spec=TableStorageService)
        mock_relationships_table.query_entities.return_value = []

        # Mock entities table - organization with NON-matching domain
        mock_entities_table = Mock(spec=TableStorageService)
        mock_entities_table.query_entities.return_value = [
            {
                "PartitionKey": "GLOBAL",
                "RowKey": "org:test-org-123",
                "Name": "Other Corporation",
                "Domain": "other.com",  # Does not match user's domain
                "IsActive": True
            }
        ]

        def mock_table_service_init(table_name, context=None):
            if table_name == "Users":
                return mock_tables["users"]
            elif table_name == "Relationships":
                return mock_relationships_table
            elif table_name == "Entities":
                return mock_entities_table
            return Mock(spec=TableStorageService)

        monkeypatch.setattr("shared.storage.TableStorageService", mock_table_service_init)

        # Create principal without PlatformAdmin role
        principal = {
            "userId": "newuser@acme.com",
            "userDetails": "newuser@acme.com",
            "userRoles": ["authenticated"]
        }
        principal_header = base64.b64encode(json.dumps(principal).encode()).decode()

        req = Mock(spec=func.HttpRequest)
        req.headers = {
            "X-MS-CLIENT-PRINCIPAL": principal_header
        }
        req.params = {}

        # Should fail because no matching domain found
        with pytest.raises(ValueError, match="has no organization assignment"):
            get_request_context(req)

        # Verify user was NOT auto-created
        mock_tables["users"].insert_entity.assert_not_called()

    @pytest.mark.skip(reason="User auto-provisioning moved to GetRoles endpoint")
    def test_domain_based_auto_provisioning_case_insensitive(self, mock_tables, monkeypatch):
        """DEPRECATED: Domain-based auto-provisioning now happens in GetRoles"""
        pass


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
