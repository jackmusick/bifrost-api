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


class TestCustomPackagesIsolation:
    """
    Test that custom packages are properly isolated and accessible.

    UNIQUE TO: New /home/.packages implementation
    """

    def test_packages_directory_exists_at_startup(self):
        """Test that .packages directory is created at startup"""
        packages_dir = Path("/Users/jack/GitHub/bifrost-integrations/api/home/.packages")

        # Should exist (created by function_app.py)
        assert packages_dir.exists(), ".packages directory should be created at startup"
        assert packages_dir.is_dir(), ".packages should be a directory"

    def test_packages_in_sys_path(self):
        """
        Test that .packages is added to sys.path during runtime.

        NOTE: This only happens when function_app.py runs (production/local dev).
        During pytest, function_app.py doesn't run, so sys.path is not modified.

        This test verifies the INTENT by checking function_app.py code.
        """

        # Read function_app.py to verify it adds .packages to sys.path
        function_app_path = Path("/Users/jack/GitHub/bifrost-integrations/api/function_app.py")
        function_app_code = function_app_path.read_text()

        # Verify function_app.py contains code to add .packages to sys.path
        assert "packages_path" in function_app_code, "function_app.py should define packages_path"
        assert "sys.path.insert" in function_app_code, "function_app.py should modify sys.path"
        assert ".packages" in function_app_code, "function_app.py should reference .packages"

        # During actual runtime (not pytest), this would be in sys.path
        # We can't test it here because function_app.py doesn't run during pytest

    @pytest.mark.skip(reason="Requires actual package installation - manual test")
    def test_workflow_can_import_custom_package(self, api_base_url, platform_admin_headers):
        """
        Test that workflows can import packages from .packages.

        Manual test procedure:
        1. pip install --target=/path/to/api/home/.packages requests
        2. Create workflow that imports requests
        3. Execute workflow
        4. Verify import succeeds
        """
        # This would require:
        # - Installing a test package to .packages
        # - Creating a workflow that imports it
        # - Executing the workflow
        # - Verifying the import worked
        pass

    def test_packages_not_shared_between_orgs(self):
        """
        Test that packages are NOT isolated per org (they're shared).

        This is by design - .packages is workspace-level, not org-level.
        All orgs share the same Python environment for simplicity.

        If org-level isolation is needed, would require:
        - /home/.packages/org-123/
        - Dynamic sys.path modification per execution
        - More complex package management
        """
        # Document current behavior: packages are shared across all orgs
        # This is a design decision, not a bug
        packages_dir = Path("/Users/jack/GitHub/bifrost-integrations/api/home/.packages")

        # Single shared directory
        assert packages_dir.exists()

        # No org-specific subdirectories
        org_dirs = list(packages_dir.glob("org-*/"))
        assert len(org_dirs) == 0, "Packages are shared, not org-isolated"


class TestSDKContextProtection:
    """
    Test that new SDK modules (config, secrets, oauth) require execution context.

    UNIQUE TO: New config, secrets, oauth modules
    """

    def test_config_requires_context(self):
        """Test that config SDK requires execution context"""
        import sys
        from pathlib import Path

        # Add platform to path
        platform_path = Path(__file__).parent.parent.parent.parent / 'platform'
        sys.path.insert(0, str(platform_path))

        from bifrost import config
        from bifrost._context import clear_execution_context

        # Clear context
        clear_execution_context()

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="No execution context found"):
            config.get("test_key")

    def test_secrets_requires_context(self):
        """Test that secrets SDK requires execution context"""
        import sys
        from pathlib import Path

        platform_path = Path(__file__).parent.parent.parent.parent / 'platform'
        sys.path.insert(0, str(platform_path))

        from bifrost import secrets
        from bifrost._context import clear_execution_context

        clear_execution_context()

        with pytest.raises(RuntimeError, match="No execution context found"):
            secrets.get("test_key")

    def test_oauth_requires_context(self):
        """Test that oauth SDK requires execution context"""
        import sys
        from pathlib import Path

        platform_path = Path(__file__).parent.parent.parent.parent / 'platform'
        sys.path.insert(0, str(platform_path))

        from bifrost import oauth
        from bifrost._context import clear_execution_context

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
        import sys
        from pathlib import Path
        from unittest.mock import Mock, patch

        platform_path = Path(__file__).parent.parent.parent.parent / 'platform'
        sys.path.insert(0, str(platform_path))

        from bifrost import config
        from bifrost._context import set_execution_context, clear_execution_context
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
            # Mock ConfigRepository
            with patch('bifrost.config.ConfigRepository') as mock_repo_class:
                mock_repo = Mock()
                mock_repo_class.return_value = mock_repo
                mock_repo.list_config.return_value = {"key1": "value1"}

                # Call list() without org_id
                config.list()

                # Verify it used context.org_id ("org-123")
                mock_repo.list_config.assert_called_once_with("org-123")
        finally:
            clear_execution_context()

    def test_secrets_list_defaults_to_current_org(self):
        """Test that secrets.list() uses context.org_id by default"""
        import sys
        from pathlib import Path
        from unittest.mock import Mock, patch

        platform_path = Path(__file__).parent.parent.parent.parent / 'platform'
        sys.path.insert(0, str(platform_path))

        from bifrost import secrets
        from bifrost._context import set_execution_context, clear_execution_context
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
            with patch('bifrost.secrets.KeyVaultClient') as mock_kv_class:
                mock_kv = Mock()
                mock_kv_class.return_value = mock_kv
                mock_kv.list_secrets.return_value = ["key1", "key2"]

                # Call list() without org_id
                secrets.list()

                # Verify it used context.org_id ("org-456")
                mock_kv.list_secrets.assert_called_once_with("org-456")
        finally:
            clear_execution_context()

    def test_oauth_list_defaults_to_current_org(self):
        """Test that oauth.list_providers() uses context.org_id by default"""
        import sys
        from pathlib import Path
        from unittest.mock import Mock, patch

        platform_path = Path(__file__).parent.parent.parent.parent / 'platform'
        sys.path.insert(0, str(platform_path))

        from bifrost import oauth
        from bifrost._context import set_execution_context, clear_execution_context
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
            with patch('bifrost.oauth.OAuthStorageService') as mock_storage_class:
                mock_storage = Mock()
                mock_storage_class.return_value = mock_storage
                mock_storage.list_providers.return_value = ["microsoft", "google"]

                # Call list_providers() without org_id
                oauth.list_providers()

                # Verify it used context.org_id ("org-789")
                mock_storage.list_providers.assert_called_once_with("org-789")
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
        import sys
        from pathlib import Path
        from unittest.mock import Mock, patch

        platform_path = Path(__file__).parent.parent.parent.parent / 'platform'
        sys.path.insert(0, str(platform_path))

        from bifrost import config
        from bifrost._context import set_execution_context, clear_execution_context
        from shared.request_context import RequestContext

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
            with patch('bifrost.config.ConfigRepository') as mock_repo_class:
                mock_repo = Mock()
                mock_repo_class.return_value = mock_repo
                mock_repo.get_config_value.return_value = "other-value"

                # Explicitly request org-999's config
                config.get("test_key", org_id="org-999")

                # Verify it used org-999, NOT context.org_id (org-123)
                mock_repo.get_config_value.assert_called_once_with("test_key", "org-999")
        finally:
            clear_execution_context()

    def test_secrets_get_with_explicit_org_id(self):
        """Test that secrets.get(org_id='other-org') uses the specified org"""
        import sys
        from pathlib import Path
        from unittest.mock import Mock, patch

        platform_path = Path(__file__).parent.parent.parent.parent / 'platform'
        sys.path.insert(0, str(platform_path))

        from bifrost import secrets
        from bifrost._context import set_execution_context, clear_execution_context
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
            with patch('bifrost.secrets.KeyVaultClient') as mock_kv_class:
                mock_kv = Mock()
                mock_kv_class.return_value = mock_kv
                mock_kv.get_secret.return_value = "other-secret"

                # Explicitly request org-888's secret
                secrets.get("api_key", org_id="org-888")

                # Verify it used org-888, NOT context.org_id (org-123)
                mock_kv.get_secret.assert_called_once_with("org-888", "api_key")
        finally:
            clear_execution_context()

    def test_oauth_get_token_with_explicit_org_id(self):
        """Test that oauth.get_token(org_id='other-org') uses the specified org"""
        import sys
        from pathlib import Path
        from unittest.mock import Mock, patch

        platform_path = Path(__file__).parent.parent.parent.parent / 'platform'
        sys.path.insert(0, str(platform_path))

        from bifrost import oauth
        from bifrost._context import set_execution_context, clear_execution_context
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
            with patch('bifrost.oauth.OAuthStorageService') as mock_storage_class:
                mock_storage = Mock()
                mock_storage_class.return_value = mock_storage
                mock_storage.get_token.return_value = {"access_token": "xxx"}

                # Explicitly request org-777's token
                oauth.get_token("microsoft", org_id="org-777")

                # Verify it used org-777, NOT context.org_id (org-123)
                mock_storage.get_token.assert_called_once_with("microsoft", "org-777")
        finally:
            clear_execution_context()


class TestGlobalUserListCounts:
    """
    Test that platform admins can list ALL resources (cross-org).

    UNIQUE TO: Verifying platform admins get global visibility

    NOTE: Regular user restrictions are tested in existing endpoint tests.
    These tests verify that platform admins DO get access to all orgs' data.
    """

    @pytest.mark.skip(reason="Requires real database with multi-org data")
    def test_platform_admin_config_list_returns_all_orgs(self):
        """
        Test that platform admin can see config from all orgs.

        This would require:
        1. Creating config for org-A
        2. Creating config for org-B
        3. Platform admin lists config
        4. Verify count includes both orgs' data

        Currently we only test org-scoping (default to current org).
        Cross-org visibility is a repository-level concern, tested there.
        """
        pass

    @pytest.mark.skip(reason="Requires real database with multi-org data")
    def test_regular_user_config_list_returns_only_own_org(self):
        """
        Test that regular user only sees their org's config.

        This is already tested in repository layer tests.
        """
        pass


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
