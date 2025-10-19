"""Unit tests for secret management handlers.

Tests business logic in shared/handlers/secrets_handlers.py in isolation,
mocking all external dependencies (KeyVault, Table Storage, RequestContext).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from shared.handlers.secrets_handlers import (
    handle_list_secrets,
    handle_create_secret,
    handle_update_secret,
    handle_delete_secret,
    SecretHandlerError,
    SecretNotFoundError,
    SecretAlreadyExistsError,
    SecretHasDependenciesError,
)
from shared.models import (
    SecretCreateRequest,
    SecretListResponse,
    SecretResponse,
    SecretUpdateRequest,
)
from shared.request_context import RequestContext


@pytest.fixture
def mock_kv_manager():
    """Create a mock KeyVaultClient."""
    manager = AsyncMock()
    manager.list_secrets = MagicMock()
    manager.create_secret = MagicMock()
    manager.update_secret = MagicMock()
    manager.delete_secret = MagicMock()
    return manager


@pytest.fixture
def mock_request_context():
    """Create a mock RequestContext."""
    return RequestContext(
        user_id="test-user-id",
        email="test@example.com",
        name="Test User",
        org_id="test-org-id",
        is_platform_admin=True,
        is_function_key=False,
    )


@pytest.fixture
def mock_check_key_vault_available():
    """Mock check_key_vault_available to return available."""
    with patch("shared.handlers.secrets_handlers.check_key_vault_available") as mock:
        mock.return_value = (True, None)
        yield mock


class TestHandleListSecrets:
    """Tests for handle_list_secrets."""

    @pytest.mark.asyncio
    async def test_list_secrets_success(self, mock_kv_manager, mock_check_key_vault_available):
        """Test successfully listing secrets."""
        secret_names = ["org-123--api-key", "GLOBAL--smtp-password"]
        mock_kv_manager.list_secrets.return_value = secret_names

        response = await handle_list_secrets(mock_kv_manager, org_id="org-123")

        assert isinstance(response, SecretListResponse)
        assert response.secrets == secret_names
        assert response.orgId == "org-123"
        assert response.count == 2
        mock_kv_manager.list_secrets.assert_called_once_with(org_id="org-123")

    @pytest.mark.asyncio
    async def test_list_secrets_no_org_filter(self, mock_kv_manager, mock_check_key_vault_available):
        """Test listing secrets without org filter."""
        secret_names = ["org-123--api-key", "GLOBAL--smtp-password", "org-456--db-pass"]
        mock_kv_manager.list_secrets.return_value = secret_names

        response = await handle_list_secrets(mock_kv_manager, org_id=None)

        assert response.secrets == secret_names
        assert response.orgId is None
        assert response.count == 3
        mock_kv_manager.list_secrets.assert_called_once_with(org_id=None)

    @pytest.mark.asyncio
    async def test_list_secrets_empty(self, mock_kv_manager, mock_check_key_vault_available):
        """Test listing when no secrets exist."""
        mock_kv_manager.list_secrets.return_value = []

        response = await handle_list_secrets(mock_kv_manager)

        assert response.secrets == []
        assert response.count == 0

    @pytest.mark.asyncio
    async def test_list_secrets_key_vault_unavailable(self, mock_kv_manager):
        """Test error when Key Vault is unavailable."""
        with patch("shared.handlers.secrets_handlers.check_key_vault_available") as mock:
            mock.return_value = (False, "Key Vault error")

            with pytest.raises(SecretHandlerError, match="Key Vault is not available"):
                await handle_list_secrets(mock_kv_manager)

    @pytest.mark.asyncio
    async def test_list_secrets_kv_manager_none_after_check(self, mock_check_key_vault_available):
        """Test error when kv_manager is None despite availability check."""
        with pytest.raises(AssertionError):
            await handle_list_secrets(None)


class TestHandleCreateSecret:
    """Tests for handle_create_secret."""

    @pytest.mark.asyncio
    async def test_create_secret_success(self, mock_kv_manager, mock_check_key_vault_available):
        """Test successfully creating a secret."""
        create_request = SecretCreateRequest(
            orgId="org-123",
            secretKey="api-key",
            value="secret-value",
        )
        mock_kv_manager.list_secrets.return_value = []

        response = await handle_create_secret(
            mock_kv_manager, create_request, "user-123"
        )

        assert isinstance(response, SecretResponse)
        assert response.name == "org-123--api-key"
        assert response.orgId == "org-123"
        assert response.secretKey == "api-key"
        assert response.value == "secret-value"
        assert response.message == "Secret created successfully"
        mock_kv_manager.create_secret.assert_called_once_with(
            org_id="org-123",
            secret_key="api-key",
            value="secret-value",
        )

    @pytest.mark.asyncio
    async def test_create_secret_global_scope(self, mock_kv_manager, mock_check_key_vault_available):
        """Test creating a GLOBAL scoped secret."""
        create_request = SecretCreateRequest(
            orgId="GLOBAL",
            secretKey="smtp-password",
            value="secure-value",
        )
        mock_kv_manager.list_secrets.return_value = []

        response = await handle_create_secret(
            mock_kv_manager, create_request, "user-123"
        )

        assert response.name == "GLOBAL--smtp-password"
        assert response.orgId == "GLOBAL"

    @pytest.mark.asyncio
    async def test_create_secret_already_exists(
        self, mock_kv_manager, mock_check_key_vault_available
    ):
        """Test error when secret already exists."""
        create_request = SecretCreateRequest(
            orgId="org-123",
            secretKey="api-key",
            value="secret-value",
        )
        mock_kv_manager.list_secrets.return_value = ["org-123--api-key"]

        with pytest.raises(SecretAlreadyExistsError, match="already exists"):
            await handle_create_secret(mock_kv_manager, create_request, "user-123")

        # Should not call create if it exists
        mock_kv_manager.create_secret.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_secret_key_vault_unavailable(self, mock_kv_manager):
        """Test error when Key Vault is unavailable."""
        with patch("shared.handlers.secrets_handlers.check_key_vault_available") as mock:
            mock.return_value = (False, "Key Vault error")
            create_request = SecretCreateRequest(
                orgId="org-123",
                secretKey="api-key",
                value="secret-value",
            )

            with pytest.raises(SecretHandlerError, match="Key Vault is not available"):
                await handle_create_secret(
                    mock_kv_manager, create_request, "user-123"
                )

    @pytest.mark.asyncio
    async def test_create_secret_check_fails_but_continue(
        self, mock_kv_manager, mock_check_key_vault_available
    ):
        """Test that creation continues if existence check fails."""
        create_request = SecretCreateRequest(
            orgId="org-123",
            secretKey="api-key",
            value="secret-value",
        )
        mock_kv_manager.list_secrets.side_effect = Exception("Listing failed")

        response = await handle_create_secret(
            mock_kv_manager, create_request, "user-123"
        )

        # Should still create despite check failure
        assert response.name == "org-123--api-key"
        mock_kv_manager.create_secret.assert_called_once()


class TestHandleUpdateSecret:
    """Tests for handle_update_secret."""

    @pytest.mark.asyncio
    async def test_update_secret_success(self, mock_kv_manager, mock_check_key_vault_available):
        """Test successfully updating a secret."""
        update_request = SecretUpdateRequest(value="new-value")

        response = await handle_update_secret(
            mock_kv_manager,
            "org-123--api-key",
            update_request,
            "user-123",
        )

        assert isinstance(response, SecretResponse)
        assert response.name == "org-123--api-key"
        assert response.value == "new-value"
        assert response.message == "Secret updated successfully"
        mock_kv_manager.update_secret.assert_called_once_with(
            org_id="org-123",
            secret_key="api-key",
            value="new-value",
        )

    @pytest.mark.asyncio
    async def test_update_secret_global_scope(self, mock_kv_manager, mock_check_key_vault_available):
        """Test updating a GLOBAL scoped secret."""
        update_request = SecretUpdateRequest(value="new-value")

        response = await handle_update_secret(
            mock_kv_manager,
            "GLOBAL--smtp-password",
            update_request,
            "user-123",
        )

        assert response.orgId == "GLOBAL"
        assert response.secretKey == "smtp-password"

    @pytest.mark.asyncio
    async def test_update_secret_invalid_name_format(
        self, mock_kv_manager, mock_check_key_vault_available
    ):
        """Test error with invalid secret name format."""
        update_request = SecretUpdateRequest(value="new-value")

        with pytest.raises(SecretHandlerError, match="Invalid secret name format"):
            await handle_update_secret(
                mock_kv_manager,
                "invalid-name",
                update_request,
                "user-123",
            )

    @pytest.mark.asyncio
    async def test_update_secret_empty_name(
        self, mock_kv_manager, mock_check_key_vault_available
    ):
        """Test error with empty secret name."""
        update_request = SecretUpdateRequest(value="new-value")

        with pytest.raises(SecretHandlerError, match="Invalid secret name format"):
            await handle_update_secret(
                mock_kv_manager,
                "",
                update_request,
                "user-123",
            )

    @pytest.mark.asyncio
    async def test_update_secret_not_found(
        self, mock_kv_manager, mock_check_key_vault_available
    ):
        """Test error when secret not found."""
        update_request = SecretUpdateRequest(value="new-value")
        mock_kv_manager.update_secret.side_effect = Exception("Secret not found")

        with pytest.raises(SecretNotFoundError, match="not found"):
            await handle_update_secret(
                mock_kv_manager,
                "org-123--api-key",
                update_request,
                "user-123",
            )

    @pytest.mark.asyncio
    async def test_update_secret_key_vault_unavailable(self, mock_kv_manager):
        """Test error when Key Vault is unavailable."""
        with patch("shared.handlers.secrets_handlers.check_key_vault_available") as mock:
            mock.return_value = (False, "Key Vault error")
            update_request = SecretUpdateRequest(value="new-value")

            with pytest.raises(SecretHandlerError):
                await handle_update_secret(
                    mock_kv_manager,
                    "org-123--api-key",
                    update_request,
                    "user-123",
                )


class TestHandleDeleteSecret:
    """Tests for handle_delete_secret."""

    @pytest.mark.asyncio
    async def test_delete_secret_success(
        self, mock_kv_manager, mock_request_context, mock_check_key_vault_available
    ):
        """Test successfully deleting a secret."""
        with patch(
            "shared.handlers.secrets_handlers._find_secret_dependencies",
            return_value=[],
        ):
            response = await handle_delete_secret(
                mock_kv_manager,
                "org-123--api-key",
                mock_request_context,
                "user-123",
            )

            assert isinstance(response, SecretResponse)
            assert response.name == "org-123--api-key"
            assert response.value is None  # Never show value after deletion
            assert response.message == "Secret deleted successfully"
            mock_kv_manager.delete_secret.assert_called_once_with(
                org_id="org-123",
                secret_key="api-key",
            )

    @pytest.mark.asyncio
    async def test_delete_secret_global_scope(
        self, mock_kv_manager, mock_request_context, mock_check_key_vault_available
    ):
        """Test deleting a GLOBAL scoped secret."""
        with patch(
            "shared.handlers.secrets_handlers._find_secret_dependencies",
            return_value=[],
        ):
            response = await handle_delete_secret(
                mock_kv_manager,
                "GLOBAL--smtp-password",
                mock_request_context,
                "user-123",
            )

            assert response.orgId == "GLOBAL"
            assert response.secretKey == "smtp-password"

    @pytest.mark.asyncio
    async def test_delete_secret_has_dependencies(
        self, mock_kv_manager, mock_request_context, mock_check_key_vault_available
    ):
        """Test error when secret has dependencies."""
        dependencies = [
            {"type": "config", "key": "smtp-config", "scope": "org-123"}
        ]

        with patch(
            "shared.handlers.secrets_handlers._find_secret_dependencies",
            return_value=dependencies,
        ):
            with pytest.raises(SecretHasDependenciesError) as exc_info:
                await handle_delete_secret(
                    mock_kv_manager,
                    "org-123--api-key",
                    mock_request_context,
                    "user-123",
                )

            assert exc_info.value.dependencies == dependencies
            # Should not delete if dependencies exist
            mock_kv_manager.delete_secret.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_secret_invalid_name_format(
        self, mock_kv_manager, mock_request_context, mock_check_key_vault_available
    ):
        """Test error with invalid secret name format."""
        with pytest.raises(SecretHandlerError, match="Invalid secret name format"):
            await handle_delete_secret(
                mock_kv_manager,
                "invalid-name",
                mock_request_context,
                "user-123",
            )

    @pytest.mark.asyncio
    async def test_delete_secret_not_found(
        self, mock_kv_manager, mock_request_context, mock_check_key_vault_available
    ):
        """Test error when secret not found."""
        mock_kv_manager.delete_secret.side_effect = Exception("Secret not found")

        with patch(
            "shared.handlers.secrets_handlers._find_secret_dependencies",
            return_value=[],
        ):
            with pytest.raises(SecretNotFoundError, match="not found"):
                await handle_delete_secret(
                    mock_kv_manager,
                    "org-123--api-key",
                    mock_request_context,
                    "user-123",
                )

    @pytest.mark.asyncio
    async def test_delete_secret_key_vault_unavailable(self, mock_request_context):
        """Test error when Key Vault is unavailable."""
        with patch("shared.handlers.secrets_handlers.check_key_vault_available") as mock:
            mock.return_value = (False, "Key Vault error")

            with pytest.raises(SecretHandlerError):
                await handle_delete_secret(
                    None,
                    "org-123--api-key",
                    mock_request_context,
                    "user-123",
                )

    @pytest.mark.asyncio
    async def test_delete_secret_multiple_dependencies(
        self, mock_kv_manager, mock_request_context, mock_check_key_vault_available
    ):
        """Test deletion with multiple dependencies."""
        dependencies = [
            {"type": "config", "key": "smtp-config", "scope": "org-123"},
            {"type": "config", "key": "backup-config", "scope": "GLOBAL"},
        ]

        with patch(
            "shared.handlers.secrets_handlers._find_secret_dependencies",
            return_value=dependencies,
        ):
            with pytest.raises(SecretHasDependenciesError) as exc_info:
                await handle_delete_secret(
                    mock_kv_manager,
                    "GLOBAL--smtp-password",
                    mock_request_context,
                    "user-123",
                )

            assert len(exc_info.value.dependencies) == 2


class TestSecretExceptions:
    """Tests for custom exception classes."""

    def test_secret_handler_error(self):
        """Test SecretHandlerError exception."""
        error = SecretHandlerError("Test error")
        assert str(error) == "Test error"

    def test_secret_not_found_error(self):
        """Test SecretNotFoundError exception."""
        error = SecretNotFoundError("Secret not found")
        assert str(error) == "Secret not found"

    def test_secret_already_exists_error(self):
        """Test SecretAlreadyExistsError exception."""
        error = SecretAlreadyExistsError("Secret already exists")
        assert str(error) == "Secret already exists"

    def test_secret_has_dependencies_error_without_dependencies(self):
        """Test SecretHasDependenciesError without dependencies."""
        error = SecretHasDependenciesError("Has dependencies")
        assert str(error) == "Has dependencies"
        assert error.dependencies == []

    def test_secret_has_dependencies_error_with_dependencies(self):
        """Test SecretHasDependenciesError with dependencies."""
        dependencies = [
            {"type": "config", "key": "test", "scope": "org-123"}
        ]
        error = SecretHasDependenciesError("Has dependencies", dependencies)
        assert error.dependencies == dependencies


class TestFindSecretDependencies:
    """Tests for _find_secret_dependencies helper function."""

    def test_find_no_dependencies(self, mock_request_context):
        """Test when no dependencies exist."""
        from shared.handlers.secrets_handlers import _find_secret_dependencies

        with patch("shared.handlers.secrets_handlers.get_table_service") as mock_svc:
            mock_table = MagicMock()
            mock_table.query_entities.return_value = []
            mock_svc.return_value = mock_table

            dependencies = _find_secret_dependencies(
                mock_request_context, "org-123--api-key", "org-123"
            )

            assert dependencies == []

    def test_find_global_dependencies(self, mock_request_context):
        """Test finding GLOBAL scoped dependencies."""
        from shared.handlers.secrets_handlers import _find_secret_dependencies

        with patch("shared.handlers.secrets_handlers.get_table_service") as mock_svc:
            mock_table = MagicMock()
            mock_table.query_entities.return_value = [
                {
                    "RowKey": "config:smtp-config",
                    "Type": "SECRET_REF",
                    "Value": "GLOBAL--smtp-password",
                }
            ]
            mock_svc.return_value = mock_table

            dependencies = _find_secret_dependencies(
                mock_request_context, "GLOBAL--smtp-password", "GLOBAL"
            )

            # Should find one dependency
            assert len(dependencies) == 1
            assert dependencies[0]["key"] == "smtp-config"
            assert dependencies[0]["scope"] == "GLOBAL"

    def test_find_org_specific_dependencies(self, mock_request_context):
        """Test finding org-specific dependencies."""
        from shared.handlers.secrets_handlers import _find_secret_dependencies

        with patch("shared.handlers.secrets_handlers.get_table_service") as mock_svc:
            # Create separate mocks for GLOBAL and org-specific calls
            global_mock = MagicMock()
            global_mock.query_entities.return_value = []  # No GLOBAL dependencies

            org_mock = MagicMock()
            org_mock.query_entities.return_value = [
                {
                    "RowKey": "config:api-config",
                    "Type": "SECRET_REF",
                    "Value": "org-123--api-key",
                }
            ]

            # Return different mocks based on call order
            mock_svc.side_effect = [global_mock, org_mock]

            dependencies = _find_secret_dependencies(
                mock_request_context, "org-123--api-key", "org-123"
            )

            assert len(dependencies) == 1
            assert dependencies[0]["key"] == "api-config"
            assert dependencies[0]["scope"] == "org-123"

    def test_find_dependencies_handles_errors(self, mock_request_context):
        """Test that errors during dependency checking are handled gracefully."""
        from shared.handlers.secrets_handlers import _find_secret_dependencies

        with patch("shared.handlers.secrets_handlers.get_table_service") as mock_svc:
            mock_svc.side_effect = Exception("Table Storage error")

            # Should not raise, just return empty list
            dependencies = _find_secret_dependencies(
                mock_request_context, "org-123--api-key", "org-123"
            )

            assert dependencies == []
