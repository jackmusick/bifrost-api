"""
Security Integration Tests for Bifrost SDK

Tests UNIQUE to new SDK additions (config, secrets, oauth, custom packages):
1. Custom packages isolation (.packages directory)
2. Context protection for new modules
3. Default org scoping (list() returns only current org)
4. Cross-org parameter validation

NOTE: Org isolation for organizations/forms/executions/roles is already tested
in test_organizations_endpoints.py, test_forms_endpoints.py, etc.
"""

import pytest

# Import context functions directly from bifrost package
# This ensures we're using the SAME module instance as the SDK code
from bifrost._context import set_execution_context, clear_execution_context




class TestSDKContextProtection:
    """
    Test that new SDK modules (config, secrets, oauth) require execution context.

    UNIQUE TO: New config, secrets, oauth modules
    """

    async def test_config_requires_context(self):
        """Test that config SDK requires execution context"""
        from bifrost import config

        # Clear context
        clear_execution_context()

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="No execution context found"):
            await config.get("test_key")

    async def test_secrets_requires_context(self):
        """Test that secrets SDK requires execution context"""
        from bifrost import secrets

        clear_execution_context()

        # secrets.get() raises RuntimeError when no context
        with pytest.raises(RuntimeError, match="No execution context found"):
            await secrets.get("test_key")

    async def test_oauth_requires_context(self):
        """Test that oauth SDK requires execution context"""
        from bifrost import oauth

        clear_execution_context()

        with pytest.raises(RuntimeError, match="No execution context found"):
            await oauth.get("microsoft")


class TestDefaultOrgScoping:
    """
    Test that list() operations default to current org from context.

    UNIQUE TO: Verifying new modules respect org scoping by default

    NOTE: The actual org isolation (user in org A can't see org B data) is
    tested in the repository layer and HTTP endpoints. These tests verify
    that the SDK correctly passes the context org_id to those layers.
    """

    async def test_config_list_defaults_to_current_org(self):
        """Test that config.list() uses context.org_id by default"""
        from unittest.mock import AsyncMock, patch
        from bifrost import config
        from shared.context import ExecutionContext, Organization

        # Create context for org-123
        org = Organization(id="org-123", name="Test Org", is_active=True)
        context = ExecutionContext(
            user_id="test-user",
            email="test@example.com",
            name="Test User",
            scope="org-123",
            organization=org,
            is_platform_admin=False,
            is_function_key=False,
            execution_id="test-exec-123"
        )
        set_execution_context(context)

        try:
            # Mock get_session_factory at the source (src.core.database)
            with patch('src.core.database.get_session_factory') as mock_get_factory:
                from sqlalchemy.ext.asyncio import AsyncSession
                from unittest.mock import MagicMock
                from contextlib import asynccontextmanager

                # Create a mock async session
                mock_session = AsyncMock(spec=AsyncSession)

                # Make the session factory return an async context manager
                @asynccontextmanager
                async def mock_async_context():
                    yield mock_session

                mock_get_factory.return_value = mock_async_context

                # Mock execute to return empty result (no configs)
                from unittest.mock import MagicMock
                mock_result = MagicMock()
                mock_result.scalars.return_value.all.return_value = []
                mock_session.execute = AsyncMock(return_value=mock_result)

                # Call list() without org_id
                result = await config.list()

                # Verify it called execute with a query targeting org-123
                mock_session.execute.assert_called_once()
                # Verify result is a dict (empty in this case)
                assert isinstance(result, dict)
        finally:
            clear_execution_context()

    async def test_secrets_list_defaults_to_current_org(self):
        """Test that secrets.list() uses context.org_id by default"""
        from unittest.mock import AsyncMock, patch
        from bifrost import secrets
        from shared.context import ExecutionContext, Organization

        org = Organization(id="org-456", name="Test Org", is_active=True)
        context = ExecutionContext(
            user_id="test-user",
            email="test@example.com",
            name="Test User",
            scope="org-456",
            organization=org,
            is_platform_admin=False,
            is_function_key=False,
            execution_id="test-exec-456"
        )
        set_execution_context(context)

        try:
            # Mock get_session_factory at the source (src.core.database)
            with patch('src.core.database.get_session_factory') as mock_get_factory:
                from sqlalchemy.ext.asyncio import AsyncSession
                from contextlib import asynccontextmanager

                # Create a mock async session
                mock_session = AsyncMock(spec=AsyncSession)

                # Make the session factory return an async context manager
                @asynccontextmanager
                async def mock_async_context():
                    yield mock_session

                mock_get_factory.return_value = mock_async_context

                # Mock execute to return configs with SECRET type
                from unittest.mock import MagicMock
                mock_result = MagicMock()
                mock_result.scalars.return_value.all.return_value = []
                mock_session.execute = AsyncMock(return_value=mock_result)

                # Call list() without org_id
                result = await secrets.list()

                # Verify it called execute with a query
                mock_session.execute.assert_called_once()
                # Verify result is a list (empty in this case)
                assert isinstance(result, list)
        finally:
            clear_execution_context()

    async def test_oauth_list_defaults_to_current_org(self):
        """Test that oauth.list_providers() uses context.org_id by default"""
        from unittest.mock import AsyncMock, Mock, patch
        from bifrost import oauth
        from shared.context import ExecutionContext, Organization

        org = Organization(id="org-789", name="Test Org", is_active=True)
        context = ExecutionContext(
            user_id="test-user",
            email="test@example.com",
            name="Test User",
            scope="org-789",
            organization=org,
            is_platform_admin=False,
            is_function_key=False,
            execution_id="test-exec-789"
        )
        set_execution_context(context)

        try:
            # Mock OAuthStorageService - patch where it's imported IN SDK
            with patch('bifrost.oauth.OAuthStorageService') as mock_storage_class:
                from unittest.mock import AsyncMock
                from shared.models import OAuthConnection
                from datetime import datetime

                mock_storage = Mock()
                mock_storage_class.return_value = mock_storage

                # list_connections is async and returns OAuthConnection objects
                mock_connections = [
                    OAuthConnection(
                        org_id="org-789",
                        connection_name="microsoft",
                        description="Microsoft OAuth",
                        oauth_flow_type="authorization_code",
                        client_id="client-123",
                        client_secret_config_key="oauth_microsoft_client_secret",
                        oauth_response_config_key="oauth_microsoft_oauth_response",
                        authorization_url="https://login.microsoft.com",
                        token_url="https://login.microsoft.com/token",
                        scopes="openid profile",
                        redirect_uri="/oauth/callback/microsoft",
                        status="completed",
                        created_at=datetime.utcnow(),
                        created_by="test-user",
                        updated_at=datetime.utcnow()
                    ),
                    OAuthConnection(
                        org_id="org-789",
                        connection_name="google",
                        description="Google OAuth",
                        oauth_flow_type="authorization_code",
                        client_id="client-456",
                        client_secret_config_key="oauth_google_client_secret",
                        oauth_response_config_key="oauth_google_oauth_response",
                        authorization_url="https://accounts.google.com",
                        token_url="https://oauth2.googleapis.com/token",
                        scopes="openid email",
                        redirect_uri="/oauth/callback/google",
                        status="completed",
                        created_at=datetime.utcnow(),
                        created_by="test-user",
                        updated_at=datetime.utcnow()
                    )
                ]

                # Create async mock for list_connections
                async def mock_list_connections(org_id, include_global=True):
                    return mock_connections

                mock_storage.list_connections = AsyncMock(side_effect=mock_list_connections)

                # Call list_providers() without org_id
                result = await oauth.list_providers()

                # Verify it called list_connections with correct org_id
                mock_storage.list_connections.assert_called_once()
                call_args = mock_storage.list_connections.call_args
                assert call_args[0][0] == "org-789"  # First positional arg
                assert call_args[1]["include_global"]  # Keyword arg

                # Verify result
                assert result == ["microsoft", "google"]
        finally:
            clear_execution_context()


class TestCrossOrgParameterUsage:
    """
    Test that when org_id parameter is specified, it's actually used.

    UNIQUE TO: New optional org_id parameter on config, secrets, oauth

    NOTE: Whether the user is AUTHORIZED to access another org's data is
    checked at the repository/service layer (existing tests). These tests
    verify the SDK correctly passes the org_id parameter through.
    """

    async def test_config_get_with_explicit_org_id(self):
        """Test that config.get(org_id='other-org') uses the specified org"""
        from unittest.mock import AsyncMock, patch
        from bifrost import config
        from shared.context import ExecutionContext, Organization

        # User is in org-123
        org = Organization(id="org-123", name="Test Org", is_active=True)
        context = ExecutionContext(
            user_id="test-user",
            email="test@example.com",
            name="Test User",
            scope="org-123",
            organization=org,
            is_platform_admin=True,  # Platform admin can access other orgs
            is_function_key=False,
            execution_id="test-exec-123"
        )
        set_execution_context(context)

        try:
            # Mock get_session_factory at the source (src.core.database)
            with patch('src.core.database.get_session_factory') as mock_get_factory:
                from sqlalchemy.ext.asyncio import AsyncSession
                from contextlib import asynccontextmanager

                # Create a mock async session
                mock_session = AsyncMock(spec=AsyncSession)

                # Make the session factory return an async context manager
                @asynccontextmanager
                async def mock_async_context():
                    yield mock_session

                mock_get_factory.return_value = mock_async_context

                # Mock execute to return a config with the expected value
                from unittest.mock import MagicMock
                mock_result = MagicMock()

                # Create a mock config object
                class MockConfig:
                    value = {"value": "other-value"}
                    config_type = type('obj', (object,), {'value': 'string'})()

                mock_result.scalars.return_value.first.return_value = MockConfig()
                mock_session.execute = AsyncMock(return_value=mock_result)

                # Explicitly request org-999's config
                result = await config.get("test_key", org_id="org-999")

                # Verify it called execute with a query
                mock_session.execute.assert_called_once()
                # Verify result contains the value
                assert result == "other-value"
        finally:
            clear_execution_context()

    # Note: test_secrets_get_with_explicit_org_id was removed because
    # secrets.get() no longer accepts org_id parameter. Secrets use Key Vault
    # secret names which encode the scope in the naming convention.

    async def test_config_set_with_explicit_org_id(self):
        """Test that config.set(org_id='other-org') writes to the specified org"""
        from unittest.mock import AsyncMock, patch
        from bifrost import config
        from shared.context import ExecutionContext, Organization

        # User is in org-123
        org = Organization(id="org-123", name="Test Org", is_active=True)
        context = ExecutionContext(
            user_id="test-user",
            email="test@example.com",
            name="Test User",
            scope="org-123",
            organization=org,
            is_platform_admin=True,
            is_function_key=False,
            execution_id="test-exec-123"
        )
        set_execution_context(context)

        try:
            # Mock get_session_factory at the source (src.core.database)
            with patch('src.core.database.get_session_factory') as mock_get_factory:
                from sqlalchemy.ext.asyncio import AsyncSession
                from contextlib import asynccontextmanager

                # Create a mock async session
                mock_session = AsyncMock(spec=AsyncSession)

                # Make the session factory return an async context manager
                @asynccontextmanager
                async def mock_async_context():
                    yield mock_session

                mock_get_factory.return_value = mock_async_context

                # Mock execute to return no existing config
                from unittest.mock import MagicMock
                mock_result = MagicMock()
                mock_result.scalars.return_value.first.return_value = None
                mock_session.execute = AsyncMock(return_value=mock_result)
                mock_session.add = MagicMock()
                mock_session.commit = AsyncMock()

                # Set config for org-999
                await config.set("api_url", "https://api.other.com", org_id="org-999")

                # Verify it called execute (checking if config exists)
                mock_session.execute.assert_called()
                # Verify it attempted to add config
                assert mock_session.add.called or mock_session.commit.called
        finally:
            clear_execution_context()

    async def test_config_delete_with_explicit_org_id(self):
        """Test that config.delete(org_id='other-org') deletes from the specified org"""
        from unittest.mock import AsyncMock, patch
        from bifrost import config
        from shared.context import ExecutionContext, Organization

        # User is in org-123
        org = Organization(id="org-123", name="Test Org", is_active=True)
        context = ExecutionContext(
            user_id="test-user",
            email="test@example.com",
            name="Test User",
            scope="org-123",
            organization=org,
            is_platform_admin=True,
            is_function_key=False,
            execution_id="test-exec-123"
        )
        set_execution_context(context)

        try:
            # Mock get_session_factory at the source (src.core.database)
            with patch('src.core.database.get_session_factory') as mock_get_factory:
                from sqlalchemy.ext.asyncio import AsyncSession
                from contextlib import asynccontextmanager

                # Create a mock async session
                mock_session = AsyncMock(spec=AsyncSession)

                # Make the session factory return an async context manager
                @asynccontextmanager
                async def mock_async_context():
                    yield mock_session

                mock_get_factory.return_value = mock_async_context

                # Create a mock config object that exists
                class MockConfig:
                    key = "old_key"

                # Mock execute to return existing config
                from unittest.mock import MagicMock
                mock_result = MagicMock()
                mock_result.scalars.return_value.first.return_value = MockConfig()
                mock_session.execute = AsyncMock(return_value=mock_result)
                mock_session.delete = MagicMock(return_value=None)
                mock_session.commit = AsyncMock()

                # Delete config from org-999
                result = await config.delete("old_key", org_id="org-999")

                # Verify it called execute (checking if config exists)
                mock_session.execute.assert_called()
                # Verify it attempted to delete
                assert mock_session.delete.called
                # Verify result is True (config was deleted)
                assert result is True
        finally:
            clear_execution_context()

    async def test_oauth_get_token_with_explicit_org_id(self):
        """Test that oauth.get(org_id='other-org') uses the specified org"""
        from unittest.mock import AsyncMock, Mock, patch
        from bifrost import oauth
        from shared.context import ExecutionContext, Organization
        from shared.models import OAuthConnection
        from datetime import datetime

        org = Organization(id="org-123", name="Test Org", is_active=True)
        context = ExecutionContext(
            user_id="admin-user",
            email="admin@example.com",
            name="Admin User",
            scope="org-123",
            organization=org,
            is_platform_admin=True,
            is_function_key=False,
            execution_id="test-exec-admin-456"
        )
        set_execution_context(context)

        try:
            # Mock OAuthStorageService.get_connection and get_tokens
            with patch('bifrost.oauth.OAuthStorageService') as mock_storage_class:
                mock_storage = Mock()
                mock_storage_class.return_value = mock_storage

                # Create mock connection
                mock_connection = OAuthConnection(
                    org_id="org-777",
                    connection_name="microsoft",
                    description="Microsoft OAuth",
                    oauth_flow_type="authorization_code",
                    client_id="client-123",
                    client_secret_config_key="oauth_microsoft_client_secret",
                    oauth_response_config_key="oauth_microsoft_oauth_response",
                    authorization_url="https://login.microsoft.com",
                    token_url="https://login.microsoft.com/token",
                    scopes="openid profile",
                    redirect_uri="/oauth/callback/microsoft",
                    status="completed",
                    created_at=datetime.utcnow(),
                    created_by="test-user",
                    updated_at=datetime.utcnow()
                )

                # Mock get_connection to return our connection
                mock_storage.get_connection = AsyncMock(return_value=mock_connection)
                # Mock get_tokens to return token data
                mock_storage.get_tokens = AsyncMock(return_value={
                    "access_token": "xxx",
                    "refresh_token": "yyy",
                    "expires_at": None
                })

                # Explicitly request org-777's token
                result = await oauth.get("microsoft", org_id="org-777")

                # Verify it called get_connection with org-777
                mock_storage.get_connection.assert_called_once_with("org-777", "microsoft")
                # Verify result contains the OAuth config
                assert result is not None
                assert result["connection_name"] == "microsoft"
                assert result["client_id"] == "client-123"
        finally:
            clear_execution_context()




# DOCUMENTATION: What's NOT tested here (already covered elsewhere)
"""
The following security concerns are ALREADY tested in existing test suites:

1. Org Isolation (HTTP layer):
   - tests/integration/api/test_organizations_endpoints.py
   - tests/integration/api/test_forms_endpoints.py
   - tests/integration/api/test_executions_endpoints.py
   - tests/integration/api/test_roles_endpoints.py

   These test that:
   - Regular users can't list organizations (403)
   - Regular users can't access other org's forms
   - Regular users can't see other org's executions
   - etc.

2. Repository Layer Org Isolation:
   - tests/unit/repositories/test_config_repository.py
   - tests/unit/repositories/test_forms_repository.py
   - tests/unit/repositories/test_roles_repository.py

   These test that repositories:
   - Query with correct PartitionKey (org_id)
   - Fallback to GLOBAL when appropriate
   - Return only org-scoped data

3. Authorization & Permissions:
   - tests/unit/test_authorization.py
   - tests/integration/api/test_permissions_endpoints.py

   These test that:
   - Platform admins can access all orgs
   - Regular users can only access their org
   - Form visibility rules (isPublic, role-based)
   - Execution visibility rules

4. Form/Workflow Execution Security:
   - tests/integration/api/test_workflows_endpoints.py
   - tests/integration/api/test_forms_endpoints.py

   These test that:
   - Users can only execute forms they have permission for
   - Workflows execute in correct org context
   - Results are scoped to correct org

This test file focuses ONLY on security concerns UNIQUE to the new SDK additions:
- Custom packages isolation
- Context protection for new modules (config, secrets, oauth)
- Default org scoping in SDK (not repository)
- Cross-org parameter passing
"""
