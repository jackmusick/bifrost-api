"""
Unit tests for inline secret creation in org_config_handlers
Tests the new functionality for creating secrets when posting config with type=secret_ref
"""

import json
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock

import azure.functions as func

from shared.handlers.org_config_handlers import set_config_handler
from shared.secret_naming import SecretNameTooLongError, InvalidSecretComponentError


class TestInlineSecretCreation:
    """Test inline secret creation when setting config with type=secret_ref"""

    @pytest.mark.asyncio
    async def test_create_new_secret_inline(self):
        """Test creating a new secret inline when value is not a secret reference"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="user-123", scope="test-org")
        mock_req.get_json.return_value = {
            "key": "api_key",
            "value": "my-actual-secret-value-xyz",  # Raw secret value to create
            "type": "secret_ref",
            "description": "Test API key"
        }

        with patch('shared.handlers.org_config_handlers.ConfigRepository') as MockRepo, \
             patch('shared.handlers.org_config_handlers.KeyVaultClient') as MockKV, \
             patch('shared.handlers.org_config_handlers.generate_secret_name') as mock_gen:

            # Setup mocks
            mock_repo = MockRepo.return_value
            mock_repo.get_config = AsyncMock(return_value=None )  # New config

            mock_kv = MockKV.return_value
            mock_kv._client = MagicMock()  # Mock the Key Vault client

            # Mock generate_secret_name to return a predictable value
            generated_name = "bifrost-test-org-api-key-12345678-1234-1234-1234-123456789012"
            mock_gen.return_value = generated_name

            # Mock the config that gets saved
            from shared.models import Config, ConfigType
            from datetime import datetime
            saved_config = Config(
                key="api_key",
                value=generated_name,  # Should be the generated secret name
                type=ConfigType.SECRET_REF,
                scope="org",
                orgId="test-org",
                description="Test API key",
                updatedAt=datetime.utcnow(),
                updatedBy="user-123"
            )
            mock_repo.set_config = AsyncMock(return_value=saved_config)

            # Execute
            response = await set_config_handler(mock_req)

            # Verify
            assert response.status_code == 201  # New config

            # Verify secret was generated with correct parameters
            mock_gen.assert_called_once_with(
                scope="test-org",
                name_component="api_key"
            )

            # Verify secret was stored in Key Vault
            mock_kv._client.set_secret.assert_called_once_with(
                generated_name,
                "my-actual-secret-value-xyz"
            )

            # Verify config was stored with the generated secret name as value
            mock_repo.set_config.assert_called_once_with(
                key="api_key",
                value=generated_name,  # Not the raw secret value
                config_type=ConfigType.SECRET_REF,
                description="Test API key",
                updated_by="user-123"
            )

    @pytest.mark.asyncio
    async def test_reference_existing_secret(self):
        """Test referencing an existing secret (value is already a secret reference)"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="user-123", scope="test-org")

        # Legacy format secret reference
        existing_secret_name = "test-org--my-existing-secret"
        mock_req.get_json.return_value = {
            "key": "database_password",
            "secretRef": existing_secret_name,  # Reference to existing secret
            "type": "secret_ref",
            "description": "DB password"
        }

        with patch('shared.handlers.org_config_handlers.ConfigRepository') as MockRepo, \
             patch('shared.handlers.org_config_handlers.KeyVaultClient') as MockKV:

            # Setup mocks
            mock_repo = MockRepo.return_value
            mock_repo.get_config = AsyncMock(return_value=None )  # New config

            mock_kv = MockKV.return_value
            mock_kv._client = MagicMock()

            # Mock the config that gets saved
            from shared.models import Config, ConfigType
            from datetime import datetime
            saved_config = Config(
                key="database_password",
                value=existing_secret_name,  # Should be the existing reference
                type=ConfigType.SECRET_REF,
                scope="org",
                orgId="test-org",
                description="DB password",
                updatedAt=datetime.utcnow(),
                updatedBy="user-123"
            )
            mock_repo.set_config = AsyncMock(return_value=saved_config)

            # Execute
            response = await set_config_handler(mock_req)

            # Verify
            assert response.status_code == 201

            # Verify NO secret was created in Key Vault
            mock_kv._client.set_secret.assert_not_called()

            # Verify config was stored with the existing secret reference
            mock_repo.set_config.assert_called_once_with(
                key="database_password",
                value=existing_secret_name,
                config_type=ConfigType.SECRET_REF,
                description="DB password",
                updated_by="user-123"
            )

    @pytest.mark.asyncio
    async def test_reference_bifrost_format_secret(self):
        """Test referencing an existing secret in new bifrost format"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="user-123", scope="test-org")

        # New bifrost format secret reference (dash-separated, lowercase)
        existing_secret_name = "bifrost-test-org-smtp-password-a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        mock_req.get_json.return_value = {
            "key": "smtp_password",
            "secretRef": existing_secret_name,  # Reference to existing secret (bifrost format)
            "type": "secret_ref",
            "description": "SMTP password"
        }

        with patch('shared.handlers.org_config_handlers.ConfigRepository') as MockRepo, \
             patch('shared.handlers.org_config_handlers.KeyVaultClient') as MockKV:

            # Setup mocks
            mock_repo = MockRepo.return_value
            mock_repo.get_config = AsyncMock(return_value=None)

            mock_kv = MockKV.return_value
            mock_kv._client = MagicMock()

            # Mock the config that gets saved
            from shared.models import Config, ConfigType
            from datetime import datetime
            saved_config = Config(
                key="smtp_password",
                value=existing_secret_name,
                type=ConfigType.SECRET_REF,
                scope="org",
                orgId="test-org",
                description="SMTP password",
                updatedAt=datetime.utcnow(),
                updatedBy="user-123"
            )
            mock_repo.set_config = AsyncMock(return_value=saved_config)

            # Execute
            response = await set_config_handler(mock_req)

            # Verify
            assert response.status_code == 201

            # Verify NO secret was created in Key Vault
            mock_kv._client.set_secret.assert_not_called()

    @pytest.mark.asyncio
    async def test_secret_name_too_long_error(self):
        """Test error handling when generated secret name exceeds max length"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="user-123", scope="test-org")
        mock_req.get_json.return_value = {
            "key": "a" * 100,  # Very long key
            "value": "secret-value",
            "type": "secret_ref",
            "description": "Test"
        }

        with patch('shared.handlers.org_config_handlers.ConfigRepository') as MockRepo, \
             patch('shared.handlers.org_config_handlers.KeyVaultClient') as MockKV, \
             patch('shared.handlers.org_config_handlers.generate_secret_name') as mock_gen:

            # Setup mocks
            mock_repo = MockRepo.return_value
            mock_repo.get_config = AsyncMock(return_value=None)

            # Mock KeyVaultClient to have a valid client
            mock_kv_instance = MockKV.return_value
            mock_kv_instance._client = Mock()

            # Mock generate_secret_name to raise SecretNameTooLongError
            mock_gen.side_effect = SecretNameTooLongError("Generated secret name is 150 characters, exceeds maximum of 127")

            # Execute
            response = await set_config_handler(mock_req)

            # Verify
            assert response.status_code == 400
            data = json.loads(response.get_body())
            assert data["error"] == "ValidationError"
            assert "exceeds maximum of 127" in data["message"]

    @pytest.mark.asyncio
    async def test_invalid_secret_component_error(self):
        """Test error handling when secret name contains invalid characters"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="user-123", scope="@@@")  # Invalid scope
        mock_req.get_json.return_value = {
            "key": "test_key",
            "value": "secret-value",
            "type": "secret_ref",
            "description": "Test"
        }

        with patch('shared.handlers.org_config_handlers.ConfigRepository') as MockRepo, \
             patch('shared.handlers.org_config_handlers.KeyVaultClient') as MockKV, \
             patch('shared.handlers.org_config_handlers.generate_secret_name') as mock_gen:

            # Setup mocks
            mock_repo = MockRepo.return_value
            mock_repo.get_config = AsyncMock(return_value=None)

            # Mock KeyVaultClient to have a valid client
            mock_kv_instance = MockKV.return_value
            mock_kv_instance._client = Mock()

            # Mock generate_secret_name to raise InvalidSecretComponentError
            mock_gen.side_effect = InvalidSecretComponentError("Scope '@@@' contains only invalid characters")

            # Execute
            response = await set_config_handler(mock_req)

            # Verify
            assert response.status_code == 400
            data = json.loads(response.get_body())
            assert data["error"] == "ValidationError"
            assert "invalid characters" in data["message"]

    @pytest.mark.asyncio
    async def test_keyvault_not_available_error(self):
        """Test error handling when Key Vault is not available"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="user-123", scope="test-org")
        mock_req.get_json.return_value = {
            "key": "api_key",
            "value": "secret-value",
            "type": "secret_ref",
            "description": "Test"
        }

        with patch('shared.handlers.org_config_handlers.ConfigRepository') as MockRepo, \
             patch('shared.handlers.org_config_handlers.KeyVaultClient') as MockKV, \
             patch('shared.handlers.org_config_handlers.generate_secret_name') as mock_gen:

            # Setup mocks
            mock_repo = MockRepo.return_value
            mock_repo.get_config = AsyncMock(return_value=None)

            mock_kv = MockKV.return_value
            mock_kv._client = None  # Key Vault not initialized

            mock_gen.return_value = "bifrost-test-org-api-key-12345678-1234-1234-1234-123456789012"

            # Execute
            response = await set_config_handler(mock_req)

            # Verify
            assert response.status_code == 503
            data = json.loads(response.get_body())
            assert data["error"] == "ServiceUnavailable"
            assert "Key Vault is not available" in data["message"]

    @pytest.mark.asyncio
    async def test_update_existing_secret_creates_new_version(self):
        """Test updating an existing secret config creates a new version (reuses secret name)"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="user-123", scope="test-org")

        existing_secret_name = "bifrost-test-org-api-key-existing-uuid"
        mock_req.get_json.return_value = {
            "key": "api_key",
            "value": "new-secret-value-here",  # New value, not a reference
            "type": "secret_ref",
            "description": "Updated API key"
        }

        with patch('shared.handlers.org_config_handlers.ConfigRepository') as MockRepo, \
             patch('shared.handlers.org_config_handlers.KeyVaultClient') as MockKV:

            # Setup mocks
            mock_repo = MockRepo.return_value

            # Mock existing config with a secret reference
            from shared.models import Config, ConfigType
            from datetime import datetime
            existing_config = Config(
                key="api_key",
                value=existing_secret_name,  # Existing secret name
                type=ConfigType.SECRET_REF,
                scope="org",
                orgId="test-org",
                description="Old description",
                updatedAt=datetime.utcnow(),
                updatedBy="old-user"
            )
            mock_repo.get_config = AsyncMock(return_value=existing_config)

            mock_kv = MockKV.return_value
            mock_kv._client = MagicMock()

            # Mock the config that gets saved
            updated_config = Config(
                key="api_key",
                value=existing_secret_name,  # Should keep same secret name
                type=ConfigType.SECRET_REF,
                scope="org",
                orgId="test-org",
                description="Updated API key",
                updatedAt=datetime.utcnow(),
                updatedBy="user-123"
            )
            mock_repo.set_config = AsyncMock(return_value=updated_config)

            # Execute
            response = await set_config_handler(mock_req)

            # Verify
            assert response.status_code == 200  # Updating existing config

            # Verify secret was updated with the SAME name (creates new version)
            mock_kv._client.set_secret.assert_called_once_with(
                existing_secret_name,  # Same secret name
                "new-secret-value-here"  # New value
            )

            # Verify config was saved with the SAME secret name
            mock_repo.set_config.assert_called_once_with(
                key="api_key",
                value=existing_secret_name,  # Not a new name
                config_type=ConfigType.SECRET_REF,
                description="Updated API key",
                updated_by="user-123"
            )

    @pytest.mark.asyncio
    async def test_non_secret_ref_type_unchanged(self):
        """Test that non-secret_ref types are handled normally (no secret creation)"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="user-123", scope="test-org")
        mock_req.get_json.return_value = {
            "key": "feature_flag",
            "value": "true",
            "type": "bool",  # Not secret_ref
            "description": "Feature flag"
        }

        with patch('shared.handlers.org_config_handlers.ConfigRepository') as MockRepo, \
             patch('shared.handlers.org_config_handlers.KeyVaultClient') as MockKV:

            # Setup mocks
            mock_repo = MockRepo.return_value
            mock_repo.get_config = AsyncMock(return_value=None)

            mock_kv = MockKV.return_value
            mock_kv._client = MagicMock()

            # Mock the config that gets saved
            from shared.models import Config, ConfigType
            from datetime import datetime
            saved_config = Config(
                key="feature_flag",
                value="true",
                type=ConfigType.BOOL,
                scope="org",
                orgId="test-org",
                description="Feature flag",
                updatedAt=datetime.utcnow(),
                updatedBy="user-123"
            )
            mock_repo.set_config = AsyncMock(return_value=saved_config)

            # Execute
            response = await set_config_handler(mock_req)

            # Verify
            assert response.status_code == 201

            # Verify NO secret was created
            mock_kv._client.set_secret.assert_not_called()

            # Verify config was stored with the original value
            mock_repo.set_config.assert_called_once_with(
                key="feature_flag",
                value="true",  # Original value unchanged
                config_type=ConfigType.BOOL,
                description="Feature flag",
                updated_by="user-123"
            )
