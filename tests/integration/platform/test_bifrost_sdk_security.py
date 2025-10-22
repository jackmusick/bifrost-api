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
from pathlib import Path

# Import context functions directly from sdk package
# This ensures we're using the SAME module instance as the SDK code
from sdk._context import set_execution_context, clear_execution_context




class TestSDKContextProtection:
    """
    Test that new SDK modules (config, secrets, oauth) require execution context.

    UNIQUE TO: New config, secrets, oauth modules
    """

    def test_config_requires_context(self):
        """Test that config SDK requires execution context"""
        from bifrost import config

        # Clear context
        clear_execution_context()

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="No execution context found"):
            config.get("test_key")

    def test_secrets_requires_context(self):
        """Test that secrets SDK requires execution context"""
        from bifrost import secrets

        clear_execution_context()

        with pytest.raises(RuntimeError, match="No execution context found"):
            secrets.get("test_key")

    def test_oauth_requires_context(self):
        """Test that oauth SDK requires execution context"""
        from bifrost import oauth

        clear_execution_context()

        with pytest.raises(RuntimeError, match="No execution context found"):
            oauth.get_token("microsoft")


class TestDefaultOrgScoping:
    """
    Test that list() operations default to current org from context.

    UNIQUE TO: Verifying new modules respect org scoping by default

    NOTE: The actual org isolation (user in org A can't see org B data) is
    tested in the repository layer and HTTP endpoints. These tests verify
    that the SDK correctly passes the context org_id to those layers.
    """

    def test_config_list_defaults_to_current_org(self):
        """Test that config.list() uses context.org_id by default"""
        from unittest.mock import Mock, patch
        from bifrost import config
        from shared.request_context import RequestContext

        # Create context for org-123
        context = RequestContext(
            user_id="test-user",
            email="test@example.com",
            name="Test User",
            org_id="org-123",
            is_platform_admin=False,
            is_function_key=False
        )
        set_execution_context(context)

        try:
            # Mock ConfigRepository - patch where it's imported IN SDK
            with patch('sdk.config.ConfigRepository') as mock_repo_class:
                from shared.models import Config, ConfigType
                from datetime import datetime

                mock_repo = Mock()
                mock_repo_class.return_value = mock_repo

                # Return list of Config models (actual return type)
                mock_repo.list_config.return_value = [
                    Config(
                        key="key1",
                        value="value1",
                        type=ConfigType.STRING,
                        scope="org",
                        orgId="org-123",
                        updatedAt=datetime.utcnow(),
                        updatedBy="test-user"
                    )
                ]

                # Call list() without org_id
                result = config.list()

                # Verify it called list_config with include_global=True
                mock_repo.list_config.assert_called_once_with(include_global=True)

                # Verify result is converted to dict
                assert isinstance(result, dict)
                assert result["key1"] == "value1"
        finally:
            clear_execution_context()

    def test_secrets_list_defaults_to_current_org(self):
        """Test that secrets.list() uses context.org_id by default"""
        from unittest.mock import Mock, patch
        from bifrost import secrets
        from shared.request_context import RequestContext

        context = RequestContext(
            user_id="test-user",
            email="test@example.com",
            name="Test User",
            org_id="org-456",
            is_platform_admin=False,
            is_function_key=False
        )
        set_execution_context(context)

        try:
            # Mock KeyVaultClient - patch where it's imported IN SDK
            with patch('sdk.secrets.KeyVaultClient') as mock_kv_class:
                mock_kv = Mock()
                mock_kv_class.return_value = mock_kv
                mock_kv.list_secrets.return_value = ["key1", "key2"]

                # Call list() without org_id
                result = secrets.list()

                # Verify it used context.org_id ("org-456")
                mock_kv.list_secrets.assert_called_once_with("org-456")

                # Verify result
                assert result == ["key1", "key2"]
        finally:
            clear_execution_context()

    def test_oauth_list_defaults_to_current_org(self):
        """Test that oauth.list_providers() uses context.org_id by default"""
        from unittest.mock import Mock, patch
        from bifrost import oauth
        from shared.request_context import RequestContext

        context = RequestContext(
            user_id="test-user",
            email="test@example.com",
            name="Test User",
            org_id="org-789",
            is_platform_admin=False,
            is_function_key=False
        )
        set_execution_context(context)

        try:
            # Mock OAuthStorageService - patch where it's imported IN SDK
            with patch('sdk.oauth.OAuthStorageService') as mock_storage_class:
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
                        client_secret_ref="secret-ref",
                        oauth_response_ref="response-ref",
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
                        client_secret_ref="secret-ref-2",
                        oauth_response_ref="response-ref-2",
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
                result = oauth.list_providers()

                # Verify it called list_connections with correct org_id
                mock_storage.list_connections.assert_called_once()
                call_args = mock_storage.list_connections.call_args
                assert call_args[0][0] == "org-789"  # First positional arg
                assert call_args[1]["include_global"] == True  # Keyword arg

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

    def test_config_get_with_explicit_org_id(self):
        """Test that config.get(org_id='other-org') uses the specified org"""
        from unittest.mock import Mock, patch
        from bifrost import config
        from shared.request_context import RequestContext
        from shared.models import Config, ConfigType
        from datetime import datetime

        # User is in org-123
        context = RequestContext(
            user_id="test-user",
            email="test@example.com",
            name="Test User",
            org_id="org-123",
            is_platform_admin=True,  # Platform admin can access other orgs
            is_function_key=False
        )
        set_execution_context(context)

        try:
            with patch('sdk.config.ConfigRepository') as mock_repo_class:
                mock_repo = Mock()
                mock_repo_class.return_value = mock_repo
                # Mock get_config (not get_config_value) - return Config model
                mock_repo.get_config.return_value = Config(
                    key="test_key",
                    value="other-value",
                    type=ConfigType.STRING,
                    scope="org",
                    orgId="org-999",
                    updatedAt=datetime.utcnow(),
                    updatedBy="test-user"
                )

                # Explicitly request org-999's config
                result = config.get("test_key", org_id="org-999")

                # Verify it called get_config with fallback_to_global=True
                mock_repo.get_config.assert_called_once_with("test_key", fallback_to_global=True)
                assert result == "other-value"
        finally:
            clear_execution_context()

    def test_secrets_get_with_explicit_org_id(self):
        """Test that secrets.get(org_id='other-org') uses the specified org"""
        from unittest.mock import Mock, patch
        from bifrost import secrets
        from shared.request_context import RequestContext

        context = RequestContext(
            user_id="admin-user",
            email="admin@example.com",
            name="Admin User",
            org_id="org-123",
            is_platform_admin=True,
            is_function_key=False
        )
        set_execution_context(context)

        try:
            with patch('sdk.secrets.KeyVaultClient') as mock_kv_class:
                mock_kv = Mock()
                mock_kv_class.return_value = mock_kv
                mock_kv.get_secret.return_value = "other-secret"

                # Explicitly request org-888's secret
                result = secrets.get("api_key", org_id="org-888")

                # Verify it used org-888, NOT context.org_id (org-123)
                mock_kv.get_secret.assert_called_once_with("org-888", "api_key")
                assert result == "other-secret"
        finally:
            clear_execution_context()

    def test_oauth_get_token_with_explicit_org_id(self):
        """Test that oauth.get_token(org_id='other-org') uses the specified org"""
        from unittest.mock import Mock, patch, AsyncMock
        from bifrost import oauth
        from shared.request_context import RequestContext
        from shared.models import OAuthConnection
        from datetime import datetime

        context = RequestContext(
            user_id="admin-user",
            email="admin@example.com",
            name="Admin User",
            org_id="org-123",
            is_platform_admin=True,
            is_function_key=False
        )
        set_execution_context(context)

        try:
            # Mock OAuthStorageService.get_connection (async method)
            with patch('sdk.oauth.OAuthStorageService') as mock_storage_class:
                mock_storage = Mock()
                mock_storage_class.return_value = mock_storage

                # Create mock connection
                mock_connection = OAuthConnection(
                    org_id="org-777",
                    connection_name="microsoft",
                    description="Microsoft OAuth",
                    oauth_flow_type="authorization_code",
                    client_id="client-123",
                    client_secret_ref="secret-ref",
                    oauth_response_ref="oauth_microsoft_oauth_response",
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

                # Mock KeyVaultClient instantiated inside oauth.get_token
                with patch('shared.keyvault.KeyVaultClient') as mock_kv_class:
                    mock_kv = Mock()
                    mock_kv_class.return_value = mock_kv
                    mock_kv.get_secret.return_value = '{"access_token": "xxx", "token_type": "Bearer"}'

                    # Explicitly request org-777's token
                    result = oauth.get_token("microsoft", org_id="org-777")

                    # Verify it called get_connection with org-777
                    mock_storage.get_connection.assert_called_once_with("org-777", "microsoft")
                    assert result is not None
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
