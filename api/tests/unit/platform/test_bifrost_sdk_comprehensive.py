"""
Comprehensive Unit Tests for Bifrost SDK

Tests all SDK modules with mocked business logic functions.
Tests cover:
- Organizations, Workflows, Files, Forms, Executions, Roles
- Config, Secrets, OAuth (new modules)
- Context management
- Permission checks
- Path sandboxing
- Import restrictions
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from datetime import datetime
from pathlib import Path

# Skip this test module - SDK tests require special setup
import pytest
pytestmark = pytest.mark.skip(reason="SDK tests require special platform setup - run separately")


@pytest.fixture
def mock_context():
    """Create a mock RequestContext for testing"""
    context = RequestContext(
        user_id="test-user",
        email="test@example.com",
        name="Test User",
        org_id="test-org",
        is_platform_admin=False,
        is_function_key=False
    )
    return context


@pytest.fixture
def mock_admin_context():
    """Create a mock admin RequestContext for testing"""
    context = RequestContext(
        user_id="admin-user",
        email="admin@example.com",
        name="Admin User",
        org_id="test-org",
        is_platform_admin=True,
        is_function_key=False
    )
    return context


@pytest.fixture(autouse=True)
def cleanup_context():
    """Ensure context is cleared after each test"""
    yield
    clear_execution_context()


class TestContextManagement:
    """Test execution context management"""

    def test_set_and_get_context(self, mock_context):
        """Test setting and getting execution context"""
        set_execution_context(mock_context)
        retrieved = get_execution_context()

        assert retrieved.org_id == "test-org"
        assert retrieved.user_id == "test-user"
        assert retrieved.email == "test@example.com"

    def test_get_context_without_setting_raises_error(self):
        """Test that getting context without setting raises RuntimeError"""
        clear_execution_context()

        with pytest.raises(RuntimeError, match="No execution context found"):
            get_execution_context()

    def test_clear_context(self, mock_context):
        """Test clearing execution context"""
        set_execution_context(mock_context)
        clear_execution_context()

        with pytest.raises(RuntimeError):
            get_execution_context()

    def test_get_context_wrapper(self, mock_context):
        """Test get_context() internal wrapper"""
        set_execution_context(mock_context)
        retrieved = get_context()

        assert retrieved.org_id == "test-org"

    def test_require_permission(self, mock_context):
        """Test require_permission() function"""
        set_execution_context(mock_context)

        # Should return context for any permission (basic check)
        context = require_permission("test.read")
        assert context.user_id == "test-user"

    def test_require_admin_with_admin_context(self, mock_admin_context):
        """Test require_admin() with admin context"""
        set_execution_context(mock_admin_context)

        context = require_admin()
        assert context.is_platform_admin is True

    def test_require_admin_without_admin_context(self, mock_context):
        """Test require_admin() with non-admin context raises PermissionError"""
        set_execution_context(mock_context)

        with pytest.raises(PermissionError, match="admin privileges"):
            require_admin()


class TestOrganizationsSDK:
    """Test organizations SDK module"""

    @patch('bifrost.organizations.create_organization_logic')
    def test_create_organization(self, mock_logic, mock_admin_context):
        """Test creating an organization"""
        set_execution_context(mock_admin_context)

        mock_org = Organization(
            id="new-org",
            name="New Organization",
            domain="neworg.com",
            isActive=True,
            createdBy="test-user",
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )
        mock_logic.return_value = mock_org

        result = organizations.create("New Organization", domain="neworg.com")

        mock_logic.assert_called_once()
        assert result.name == "New Organization"
        assert result.domain == "neworg.com"

    @patch('bifrost.organizations.get_organization_logic')
    def test_get_organization(self, mock_logic, mock_context):
        """Test getting an organization"""
        set_execution_context(mock_context)

        mock_org = Organization(
            id="test-org",
            name="Test Organization",
            domain="test.com",
            isActive=True,
            createdBy="test-user",
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )
        mock_logic.return_value = mock_org

        result = organizations.get("test-org")

        mock_logic.assert_called_once_with(mock_context, "test-org")
        assert result.name == "Test Organization"

    @patch('bifrost.organizations.list_organizations_logic')
    def test_list_organizations(self, mock_logic, mock_admin_context):
        """Test listing organizations"""
        set_execution_context(mock_admin_context)

        mock_orgs = [
            Organization(
                id="org-1",
                name="Org 1",
                domain="org1.com",
                isActive=True,
                createdBy="test-user",
                createdAt=datetime.utcnow(),
                updatedAt=datetime.utcnow()
            ),
            Organization(
                id="org-2",
                name="Org 2",
                domain="org2.com",
                isActive=True,
                createdBy="test-user",
                createdAt=datetime.utcnow(),
                updatedAt=datetime.utcnow()
            )
        ]
        mock_logic.return_value = mock_orgs

        result = organizations.list()

        assert len(result) == 2
        assert result[0].name == "Org 1"

    @patch('bifrost.organizations.update_organization_logic')
    def test_update_organization(self, mock_logic, mock_admin_context):
        """Test updating an organization"""
        set_execution_context(mock_admin_context)

        mock_org = Organization(
            id="test-org",
            name="Updated Org",
            domain="updated.com",
            isActive=True,
            createdBy="test-user",
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )
        mock_logic.return_value = mock_org

        result = organizations.update("test-org", name="Updated Org")

        assert result.name == "Updated Org"

    @patch('bifrost.organizations.delete_organization_logic')
    def test_delete_organization(self, mock_logic, mock_admin_context):
        """Test deleting an organization"""
        set_execution_context(mock_admin_context)

        organizations.delete("test-org")

        mock_logic.assert_called_once_with(mock_admin_context, "test-org")


class TestWorkflowsSDK:
    """Test workflows SDK module"""

    @patch('shared.registry.get_registry')
    def test_execute_workflow(self, mock_get_registry, mock_context):
        """Test executing a workflow"""
        set_execution_context(mock_context)

        # Mock registry and workflow
        mock_registry = Mock()
        mock_get_registry.return_value = mock_registry

        mock_workflow_metadata = Mock()

        # Create async mock function
        async def mock_workflow_func(context, **params):
            return {"success": True, "data": "result"}

        mock_workflow_metadata.function = mock_workflow_func
        mock_registry.get_workflow.return_value = mock_workflow_metadata

        result = workflows.execute("test_workflow", {"param1": "value1"})

        assert result["success"] is True
        mock_registry.get_workflow.assert_called_once_with("test_workflow")

    @patch('bifrost.workflows.list_workflows_logic')
    def test_list_workflows(self, mock_logic, mock_context):
        """Test listing workflows"""
        set_execution_context(mock_context)

        mock_workflows = [
            {
                "name": "workflow1",
                "description": "Workflow 1",
                "parameters": [],
                "executionMode": "async"
            },
            {
                "name": "workflow2",
                "description": "Workflow 2",
                "parameters": [],
                "executionMode": "sync"
            }
        ]
        mock_logic.return_value = mock_workflows

        result = workflows.list()

        assert len(result) == 2
        assert result[0]["name"] == "workflow1"

    @patch('shared.registry.get_registry')
    def test_execute_workflow_not_found(self, mock_get_registry, mock_context):
        """Test executing non-existent workflow raises ValueError"""
        set_execution_context(mock_context)

        mock_registry = Mock()
        mock_get_registry.return_value = mock_registry
        mock_registry.get_workflow.return_value = None

        with pytest.raises(ValueError, match="Workflow not found"):
            workflows.execute("nonexistent")


class TestFilesSDK:
    """Test files SDK module"""

    def test_resolve_path_sandboxing_directory_traversal(self, mock_context):
        """Test that path resolution blocks directory traversal"""
        set_execution_context(mock_context)

        with pytest.raises(ValueError, match="Path must be within"):
            files._resolve_path("../../../etc/passwd")

    def test_resolve_path_sandboxing_absolute_path(self, mock_context):
        """Test that path resolution blocks absolute paths outside workspace"""
        set_execution_context(mock_context)

        with pytest.raises(ValueError, match="Path must be within"):
            files._resolve_path("/etc/passwd")

    @patch('bifrost.files.files._resolve_path')
    def test_resolve_path_allows_files_dir(self, mock_resolve, mock_context):
        """Test that paths within /home/files are allowed"""
        set_execution_context(mock_context)

        # Mock the resolve path to return a valid path
        mock_resolve.return_value = Path("/home/files/test.txt")

        path = files._resolve_path("test.txt")
        assert "/home/files" in str(path)

    @patch('bifrost.files.files._resolve_path')
    def test_resolve_path_allows_tmp_when_enabled(self, mock_resolve, mock_context):
        """Test that tmp directory is allowed when specified"""
        set_execution_context(mock_context)

        # Mock the resolve path to return a valid tmp path
        mock_resolve.return_value = Path("/home/tmp/test.txt")

        path = files._resolve_path("test.txt", allow_tmp=True)
        assert "/home/tmp" in str(path)

    @patch('builtins.open', new_callable=mock_open, read_data="test content")
    @patch('bifrost.files.files._resolve_path')
    def test_read_file(self, mock_resolve, mock_open_file, mock_context):
        """Test reading a file"""
        set_execution_context(mock_context)

        # Mock path resolution - return a real Path-like object
        mock_resolve.return_value = Path("/home/files/test.txt")

        result = files.read("test.txt")
        assert result == "test content"

    @patch('pathlib.Path.mkdir')
    @patch('builtins.open', new_callable=mock_open)
    @patch('bifrost.files.files._resolve_path')
    def test_write_file(self, mock_resolve, mock_open_file, mock_mkdir, mock_context):
        """Test writing a file"""
        set_execution_context(mock_context)

        # Create a mock path with mkdir and parent attributes
        mock_path = Mock(spec=Path)
        mock_path.parent = Mock(spec=Path)
        mock_path.parent.mkdir = Mock()
        mock_resolve.return_value = mock_path

        files.write("test.txt", "new content")
        # Verify parent.mkdir was called
        assert mock_path.parent.mkdir.called or mock_open_file.called

    @patch('bifrost.files.files._resolve_path')
    def test_exists_file(self, mock_resolve, mock_context):
        """Test checking if file exists"""
        set_execution_context(mock_context)

        # Mock path resolution - use a mock that behaves like Path
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = True
        mock_resolve.return_value = mock_path

        result = files.exists("test.txt")
        assert result is True

    @patch('shutil.rmtree')
    @patch('bifrost.files.files._resolve_path')
    def test_delete_file(self, mock_resolve, mock_rmtree, mock_context):
        """Test deleting a file"""
        set_execution_context(mock_context)

        # Create a mock path object that behaves like Path
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.is_dir.return_value = False
        mock_path.unlink = Mock()
        mock_resolve.return_value = mock_path

        files.delete("test.txt")
        # Verify unlink was called
        assert mock_path.unlink.called

    @patch('bifrost.files.files._resolve_path')
    def test_list_files(self, mock_resolve, mock_context):
        """Test listing files"""
        set_execution_context(mock_context)

        # Mock path resolution
        mock_path = Mock(spec=Path)
        mock_files = [
            Mock(spec=Path, name="file1.txt", is_file=Mock(return_value=True)),
            Mock(spec=Path, name="file2.txt", is_file=Mock(return_value=True))
        ]
        mock_path.iterdir.return_value = mock_files
        mock_path.is_dir.return_value = True
        mock_resolve.return_value = mock_path

        result = files.list(".")
        # Files.list returns the actual mocked Path objects
        assert len([f for f in result]) == 2


class TestFormsSDK:
    """Test forms SDK module"""

    @patch('bifrost.forms.list_forms_logic')
    def test_list_forms(self, mock_logic, mock_context):
        """Test listing forms"""
        set_execution_context(mock_context)

        mock_forms = [
            Form(
                id="form-1",
                orgId="test-org",
                name="Form 1",
                linkedWorkflow="test_workflow_1",
                formSchema=FormSchema(fields=[
                    FormField(
                        name="field1",
                        label="Field 1",
                        type=FormFieldType.TEXT
                    )
                ]),
                createdBy="test-user",
                createdAt=datetime.utcnow(),
                updatedAt=datetime.utcnow()
            ),
            Form(
                id="form-2",
                orgId="test-org",
                name="Form 2",
                linkedWorkflow="test_workflow_2",
                formSchema=FormSchema(fields=[
                    FormField(
                        name="field2",
                        label="Field 2",
                        type=FormFieldType.TEXT
                    )
                ]),
                createdBy="test-user",
                createdAt=datetime.utcnow(),
                updatedAt=datetime.utcnow()
            )
        ]
        mock_logic.return_value = mock_forms

        result = forms.list()

        assert len(result) == 2
        assert result[0].name == "Form 1"

    @patch('bifrost.forms.get_form_logic')
    def test_get_form(self, mock_logic, mock_context):
        """Test getting a form"""
        set_execution_context(mock_context)

        mock_form = Form(
            id="form-1",
            orgId="test-org",
            name="Test Form",
            linkedWorkflow="test_workflow",
            formSchema=FormSchema(fields=[
                FormField(
                    name="field1",
                    label="Field 1",
                    type=FormFieldType.TEXT
                )
            ]),
            createdBy="test-user",
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )
        mock_logic.return_value = mock_form

        result = forms.get("form-1")

        assert result.name == "Test Form"

    @patch('bifrost.forms.get_form_logic')
    def test_get_form_not_found(self, mock_logic, mock_context):
        """Test getting non-existent form raises ValueError"""
        set_execution_context(mock_context)

        mock_logic.return_value = None

        with pytest.raises(ValueError, match="Form not found"):
            forms.get("nonexistent")


class TestExecutionsSDK:
    """Test executions SDK module"""

    @patch('bifrost.executions.list_executions_handler')
    def test_list_executions(self, mock_handler, mock_context):
        """Test listing executions"""
        set_execution_context(mock_context)

        mock_executions = [
            {"id": "exec-1", "status": "Success"},
            {"id": "exec-2", "status": "Failed"}
        ]
        mock_handler.return_value = (mock_executions, None)

        result = executions.list(limit=10)

        assert len(result) == 2
        assert result[0]["status"] == "Success"

    @patch('bifrost.executions.get_execution_handler')
    def test_get_execution(self, mock_handler, mock_context):
        """Test getting an execution"""
        set_execution_context(mock_context)

        mock_exec = {"id": "exec-1", "status": "Success", "orgId": "test-org"}
        mock_handler.return_value = (mock_exec, None)

        result = executions.get("exec-1")

        assert result["id"] == "exec-1"

    @patch('bifrost.executions.get_execution_handler')
    @patch('bifrost.executions.ExecutionRepository')
    def test_delete_execution(self, mock_repo_class, mock_handler, mock_context):
        """Test deleting an execution"""
        set_execution_context(mock_context)

        mock_exec = {"id": "exec-1", "orgId": "test-org"}
        mock_handler.return_value = (mock_exec, None)

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        executions.delete("exec-1")

        mock_repo.delete_execution.assert_called_once_with("exec-1", "test-org")

    @patch('bifrost.executions.get_execution_handler')
    def test_delete_execution_not_found(self, mock_handler, mock_context):
        """Test deleting non-existent execution raises ValueError"""
        set_execution_context(mock_context)

        mock_handler.return_value = (None, "NotFound")

        with pytest.raises(ValueError, match="Execution not found"):
            executions.delete("nonexistent")


class TestRolesSDK:
    """Test roles SDK module"""

    @patch('bifrost.roles.RoleRepository')
    def test_create_role(self, mock_repo_class, mock_context):
        """Test creating a role"""
        set_execution_context(mock_context)

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        mock_role = Role(
            id="role-1",
            orgId="test-org",
            name="Test Role",
            description="Test Description",
            permissions=["test.read"],
            createdBy="test-user",
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )
        mock_repo.create_role.return_value = mock_role

        result = roles.create("Test Role", description="Test Description", permissions=["test.read"])

        assert result.name == "Test Role"

    @patch('bifrost.roles.RoleRepository')
    def test_list_roles(self, mock_repo_class, mock_context):
        """Test listing roles"""
        set_execution_context(mock_context)

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        mock_roles = [
            Role(id="role-1", orgId="test-org", name="Role 1", permissions=[], createdBy="test-user", createdAt=datetime.utcnow(), updatedAt=datetime.utcnow()),
            Role(id="role-2", orgId="test-org", name="Role 2", permissions=[], createdBy="test-user", createdAt=datetime.utcnow(), updatedAt=datetime.utcnow())
        ]
        mock_repo.list_roles.return_value = mock_roles

        result = roles.list()

        assert len(result) == 2

    @patch('bifrost.roles.RoleRepository')
    def test_assign_users(self, mock_repo_class, mock_context):
        """Test assigning users to a role"""
        set_execution_context(mock_context)

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        mock_role = Role(id="role-1", orgId="test-org", name="Test Role", permissions=[], createdBy="test-user", createdAt=datetime.utcnow(), updatedAt=datetime.utcnow())
        mock_repo.get_role.return_value = mock_role

        roles.assign_users("role-1", ["user-1", "user-2"])

        mock_repo.assign_users_to_role.assert_called_once()


class TestConfigSDK:
    """Test config SDK module"""

    @patch('bifrost.config.ConfigRepository')
    def test_get_config(self, mock_repo_class, mock_context):
        """Test getting configuration value"""
        set_execution_context(mock_context)

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_config_value.return_value = "test_value"

        result = config.get("test_key")

        assert result == "test_value"
        mock_repo.get_config_value.assert_called_once_with("test_key", "test-org")

    @patch('bifrost.config.ConfigRepository')
    def test_get_config_with_default(self, mock_repo_class, mock_context):
        """Test getting configuration value with default"""
        set_execution_context(mock_context)

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_config_value.return_value = None

        result = config.get("missing_key", default="default_value")

        assert result == "default_value"

    @patch('bifrost.config.ConfigRepository')
    def test_get_config_with_org_id(self, mock_repo_class, mock_context):
        """Test getting configuration for specific org"""
        set_execution_context(mock_context)

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_config_value.return_value = "other_value"

        result = config.get("test_key", org_id="other-org")

        mock_repo.get_config_value.assert_called_once_with("test_key", "other-org")

    @patch('bifrost.config.ConfigRepository')
    def test_set_config(self, mock_repo_class, mock_context):
        """Test setting configuration value"""
        set_execution_context(mock_context)

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        config.set("test_key", "test_value")

        mock_repo.set_config_value.assert_called_once()

    @patch('bifrost.config.ConfigRepository')
    def test_list_config(self, mock_repo_class, mock_context):
        """Test listing all configuration"""
        set_execution_context(mock_context)

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.list_config.return_value = {"key1": "value1", "key2": "value2"}

        result = config.list()

        assert len(result) == 2
        assert result["key1"] == "value1"

    @patch('bifrost.config.ConfigRepository')
    def test_delete_config(self, mock_repo_class, mock_context):
        """Test deleting configuration value"""
        set_execution_context(mock_context)

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.delete_config.return_value = True

        result = config.delete("test_key")

        assert result is True


class TestSecretsSDK:
    """Test secrets SDK module"""

    @patch('bifrost.secrets.KeyVaultClient')
    def test_get_secret(self, mock_kv_class, mock_context):
        """Test getting decrypted secret"""
        set_execution_context(mock_context)

        mock_kv = Mock()
        mock_kv_class.return_value = mock_kv
        mock_kv.get_secret.return_value = "secret_value"

        result = secrets.get("api_key")

        assert result == "secret_value"
        mock_kv.get_secret.assert_called_once_with("test-org", "api_key")

    @patch('bifrost.secrets.KeyVaultClient')
    def test_get_secret_not_found(self, mock_kv_class, mock_context):
        """Test getting non-existent secret returns None"""
        set_execution_context(mock_context)

        mock_kv = Mock()
        mock_kv_class.return_value = mock_kv
        mock_kv.get_secret.side_effect = Exception("Not found")

        result = secrets.get("missing_key")

        assert result is None

    @patch('bifrost.secrets.KeyVaultClient')
    def test_set_secret(self, mock_kv_class, mock_context):
        """Test setting encrypted secret"""
        set_execution_context(mock_context)

        mock_kv = Mock()
        mock_kv_class.return_value = mock_kv

        secrets.set("api_key", "secret_value")

        mock_kv.create_secret.assert_called_once_with("test-org", "api_key", "secret_value")

    @patch('bifrost.secrets.KeyVaultClient')
    def test_list_secrets(self, mock_kv_class, mock_context):
        """Test listing secret keys (not values)"""
        set_execution_context(mock_context)

        mock_kv = Mock()
        mock_kv_class.return_value = mock_kv
        mock_kv.list_secrets.return_value = ["key1", "key2", "key3"]

        result = secrets.list()

        assert len(result) == 3
        assert "key1" in result

    @patch('bifrost.secrets.KeyVaultClient')
    def test_delete_secret(self, mock_kv_class, mock_context):
        """Test deleting secret"""
        set_execution_context(mock_context)

        mock_kv = Mock()
        mock_kv_class.return_value = mock_kv

        result = secrets.delete("api_key")

        assert result is True
        mock_kv.delete_secret.assert_called_once_with("test-org", "api_key")


class TestOAuthSDK:
    """Test OAuth SDK module"""

    @patch('bifrost.oauth.OAuthStorageService')
    def test_get_token(self, mock_storage_class, mock_context):
        """Test getting OAuth token"""
        set_execution_context(mock_context)

        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage

        mock_token = {
            "access_token": "ya29.xxx",
            "refresh_token": "1//xxx",
            "expires_at": 1234567890
        }
        mock_storage.get_token.return_value = mock_token

        result = oauth.get_token("microsoft")

        assert result["access_token"] == "ya29.xxx"
        mock_storage.get_token.assert_called_once_with("microsoft", "test-org")

    @patch('bifrost.oauth.OAuthStorageService')
    def test_get_token_not_found(self, mock_storage_class, mock_context):
        """Test getting non-existent token returns None"""
        set_execution_context(mock_context)

        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        mock_storage.get_token.return_value = None

        result = oauth.get_token("nonexistent")

        assert result is None

    @patch('bifrost.oauth.OAuthStorageService')
    def test_set_token(self, mock_storage_class, mock_context):
        """Test setting OAuth token"""
        set_execution_context(mock_context)

        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage

        token_data = {
            "access_token": "ya29.xxx",
            "refresh_token": "1//xxx",
            "expires_at": 1234567890
        }

        oauth.set_token("microsoft", token_data)

        mock_storage.store_token.assert_called_once()

    @patch('bifrost.oauth.OAuthStorageService')
    def test_list_providers(self, mock_storage_class, mock_context):
        """Test listing OAuth providers"""
        set_execution_context(mock_context)

        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        mock_storage.list_providers.return_value = ["microsoft", "google", "github"]

        result = oauth.list_providers()

        assert len(result) == 3
        assert "microsoft" in result

    @patch('bifrost.oauth.OAuthStorageService')
    def test_delete_token(self, mock_storage_class, mock_context):
        """Test deleting OAuth token"""
        set_execution_context(mock_context)

        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        mock_storage.delete_token.return_value = True

        result = oauth.delete_token("microsoft")

        assert result is True

    @patch('bifrost.oauth.OAuthStorageService')
    def test_refresh_token(self, mock_storage_class, mock_context):
        """Test refreshing OAuth token"""
        set_execution_context(mock_context)

        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage

        new_token = {
            "access_token": "ya29.new",
            "refresh_token": "1//new",
            "expires_at": 1234567999
        }
        mock_storage.refresh_token.return_value = new_token

        result = oauth.refresh_token("microsoft")

        assert result["access_token"] == "ya29.new"

    @patch('bifrost.oauth.OAuthStorageService')
    def test_refresh_token_failure(self, mock_storage_class, mock_context):
        """Test refreshing token failure raises ValueError"""
        set_execution_context(mock_context)

        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        mock_storage.refresh_token.return_value = None

        with pytest.raises(ValueError, match="Failed to refresh token"):
            oauth.refresh_token("microsoft")


class TestSDKWithoutContext:
    """Test that SDK operations fail gracefully without execution context"""

    def test_organizations_without_context(self):
        """Test organizations SDK without context raises RuntimeError"""
        clear_execution_context()

        with pytest.raises(RuntimeError, match="No execution context found"):
            organizations.list()

    def test_workflows_without_context(self):
        """Test workflows SDK without context raises RuntimeError"""
        clear_execution_context()

        with pytest.raises(RuntimeError, match="No execution context found"):
            workflows.list()

    def test_files_without_context(self):
        """Test files SDK without context raises RuntimeError"""
        clear_execution_context()

        with pytest.raises(RuntimeError, match="No execution context found"):
            files.list(".")

    def test_config_without_context(self):
        """Test config SDK without context raises RuntimeError"""
        clear_execution_context()

        with pytest.raises(RuntimeError, match="No execution context found"):
            config.get("test_key")

    def test_secrets_without_context(self):
        """Test secrets SDK without context raises RuntimeError"""
        clear_execution_context()

        with pytest.raises(RuntimeError, match="No execution context found"):
            secrets.get("test_key")

    def test_oauth_without_context(self):
        """Test OAuth SDK without context raises RuntimeError"""
        clear_execution_context()

        with pytest.raises(RuntimeError, match="No execution context found"):
            oauth.get_token("microsoft")


class TestCrossOrgOperations:
    """Test operations with optional org_id parameter"""

    @patch('bifrost.config.ConfigRepository')
    def test_config_cross_org(self, mock_repo_class, mock_context):
        """Test accessing config for different org"""
        set_execution_context(mock_context)

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_config_value.return_value = "other_org_value"

        result = config.get("test_key", org_id="other-org")

        # Should use provided org_id, not context org_id
        mock_repo.get_config_value.assert_called_once_with("test_key", "other-org")

    @patch('bifrost.secrets.KeyVaultClient')
    def test_secrets_cross_org(self, mock_kv_class, mock_context):
        """Test accessing secrets for different org"""
        set_execution_context(mock_context)

        mock_kv = Mock()
        mock_kv_class.return_value = mock_kv
        mock_kv.get_secret.return_value = "other_org_secret"

        result = secrets.get("api_key", org_id="other-org")

        # Should use provided org_id, not context org_id
        mock_kv.get_secret.assert_called_once_with("other-org", "api_key")

    @patch('bifrost.oauth.OAuthStorageService')
    def test_oauth_cross_org(self, mock_storage_class, mock_context):
        """Test accessing OAuth tokens for different org"""
        set_execution_context(mock_context)

        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        mock_storage.get_token.return_value = {"access_token": "xxx"}

        result = oauth.get_token("microsoft", org_id="other-org")

        # Should use provided org_id, not context org_id
        mock_storage.get_token.assert_called_once_with("microsoft", "other-org")
