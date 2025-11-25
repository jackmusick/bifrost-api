"""Tests for config.get() SECRET_REF resolution from Key Vault"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from bifrost.config import config
from shared.models import Config, ConfigType


class TestConfigSecretResolution:
    """Test config.get() resolves SECRET_REF types from Key Vault"""

    @pytest.mark.asyncio
    async def test_get_secret_ref_resolves_from_keyvault(self):
        """SECRET_REF type should return resolved secret, not reference"""
        with patch('bifrost.config.get_context') as mock_get_context, \
             patch('bifrost.config.ConfigRepository') as MockRepo:

            # Setup mock context with ConfigResolver
            mock_context = Mock()
            mock_context.scope = "test-org"
            mock_resolver = AsyncMock()
            mock_resolver.get_config = AsyncMock(return_value="actual-secret-value")
            mock_context._config_resolver = mock_resolver
            mock_get_context.return_value = mock_context

            # Setup mock repository returning SECRET_REF config
            mock_repo = MockRepo.return_value
            mock_cfg = Config(
                key="api_key",
                value="bifrost-test-org-api-key-12345",  # Reference name
                type=ConfigType.SECRET_REF,
                scope="org",
                orgId="test-org",
                updatedAt=datetime.utcnow(),
                updatedBy="test"
            )
            mock_repo.get_config = AsyncMock(return_value=mock_cfg)

            # Execute
            result = await config.get("api_key")

            # Verify - should return resolved secret, not reference
            assert result == "actual-secret-value"
            mock_resolver.get_config.assert_called_once()

            # Verify ConfigResolver was called with correct parameters
            call_args = mock_resolver.get_config.call_args
            assert call_args.kwargs["org_id"] == "test-org"
            assert call_args.kwargs["key"] == "api_key"
            assert call_args.kwargs["config_data"]["api_key"]["type"] == "secret_ref"

    @pytest.mark.asyncio
    async def test_get_string_type_returns_value(self):
        """STRING type should return string value via ConfigResolver"""
        with patch('bifrost.config.get_context') as mock_get_context, \
             patch('bifrost.config.ConfigRepository') as MockRepo:

            mock_context = Mock()
            mock_context.scope = "test-org"
            mock_resolver = AsyncMock()
            mock_resolver.get_config = AsyncMock(return_value="https://api.example.com")
            mock_context._config_resolver = mock_resolver
            mock_get_context.return_value = mock_context

            mock_repo = MockRepo.return_value
            mock_cfg = Config(
                key="api_url",
                value="https://api.example.com",
                type=ConfigType.STRING,
                scope="org",
                orgId="test-org",
                updatedAt=datetime.utcnow(),
                updatedBy="test"
            )
            mock_repo.get_config = AsyncMock(return_value=mock_cfg)

            result = await config.get("api_url")

            assert result == "https://api.example.com"

    @pytest.mark.asyncio
    async def test_get_int_type_returns_parsed_value(self):
        """INT type should return parsed integer"""
        with patch('bifrost.config.get_context') as mock_get_context, \
             patch('bifrost.config.ConfigRepository') as MockRepo:

            mock_context = Mock()
            mock_context.scope = "test-org"
            mock_resolver = AsyncMock()
            mock_resolver.get_config = AsyncMock(return_value=42)
            mock_context._config_resolver = mock_resolver
            mock_get_context.return_value = mock_context

            mock_repo = MockRepo.return_value
            mock_cfg = Config(
                key="timeout",
                value="42",
                type=ConfigType.INT,
                scope="org",
                orgId="test-org",
                updatedAt=datetime.utcnow(),
                updatedBy="test"
            )
            mock_repo.get_config = AsyncMock(return_value=mock_cfg)

            result = await config.get("timeout")

            assert result == 42
            assert isinstance(result, int)

    @pytest.mark.asyncio
    async def test_get_bool_type_returns_parsed_value(self):
        """BOOL type should return parsed boolean"""
        with patch('bifrost.config.get_context') as mock_get_context, \
             patch('bifrost.config.ConfigRepository') as MockRepo:

            mock_context = Mock()
            mock_context.scope = "test-org"
            mock_resolver = AsyncMock()
            mock_resolver.get_config = AsyncMock(return_value=True)
            mock_context._config_resolver = mock_resolver
            mock_get_context.return_value = mock_context

            mock_repo = MockRepo.return_value
            mock_cfg = Config(
                key="feature_enabled",
                value="true",
                type=ConfigType.BOOL,
                scope="org",
                orgId="test-org",
                updatedAt=datetime.utcnow(),
                updatedBy="test"
            )
            mock_repo.get_config = AsyncMock(return_value=mock_cfg)

            result = await config.get("feature_enabled")

            assert result is True
            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_get_json_type_returns_parsed_value(self):
        """JSON type should return parsed JSON object"""
        with patch('bifrost.config.get_context') as mock_get_context, \
             patch('bifrost.config.ConfigRepository') as MockRepo:

            mock_context = Mock()
            mock_context.scope = "test-org"
            mock_resolver = AsyncMock()
            mock_resolver.get_config = AsyncMock(return_value={"key": "value", "count": 5})
            mock_context._config_resolver = mock_resolver
            mock_get_context.return_value = mock_context

            mock_repo = MockRepo.return_value
            mock_cfg = Config(
                key="settings",
                value='{"key": "value", "count": 5}',
                type=ConfigType.JSON,
                scope="org",
                orgId="test-org",
                updatedAt=datetime.utcnow(),
                updatedBy="test"
            )
            mock_repo.get_config = AsyncMock(return_value=mock_cfg)

            result = await config.get("settings")

            assert result == {"key": "value", "count": 5}
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_keyvault_error_raises_runtime_error(self):
        """Key Vault resolution failure should raise RuntimeError"""
        with patch('bifrost.config.get_context') as mock_get_context, \
             patch('bifrost.config.ConfigRepository') as MockRepo:

            mock_context = Mock()
            mock_context.scope = "test-org"
            mock_resolver = AsyncMock()
            mock_resolver.get_config = AsyncMock(
                side_effect=ValueError("Secret not found in Key Vault")
            )
            mock_context._config_resolver = mock_resolver
            mock_get_context.return_value = mock_context

            mock_repo = MockRepo.return_value
            mock_cfg = Config(
                key="api_key",
                value="bifrost-missing-secret",
                type=ConfigType.SECRET_REF,
                scope="org",
                orgId="test-org",
                updatedAt=datetime.utcnow(),
                updatedBy="test"
            )
            mock_repo.get_config = AsyncMock(return_value=mock_cfg)

            with pytest.raises(RuntimeError) as exc_info:
                await config.get("api_key")

            assert "Failed to resolve config 'api_key'" in str(exc_info.value)
            assert "Secret not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_returns_default_when_not_found(self):
        """Should return default when config not found"""
        with patch('bifrost.config.get_context') as mock_get_context, \
             patch('bifrost.config.ConfigRepository') as MockRepo:

            mock_context = Mock()
            mock_context.scope = "test-org"
            mock_get_context.return_value = mock_context

            mock_repo = MockRepo.return_value
            mock_repo.get_config = AsyncMock(return_value=None)

            result = await config.get("missing_key", default="fallback")

            assert result == "fallback"

    @pytest.mark.asyncio
    async def test_get_returns_none_when_not_found_no_default(self):
        """Should return None when config not found and no default provided"""
        with patch('bifrost.config.get_context') as mock_get_context, \
             patch('bifrost.config.ConfigRepository') as MockRepo:

            mock_context = Mock()
            mock_context.scope = "test-org"
            mock_get_context.return_value = mock_context

            mock_repo = MockRepo.return_value
            mock_repo.get_config = AsyncMock(return_value=None)

            result = await config.get("missing_key")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_uses_fallback_to_global(self):
        """Should use fallback_to_global=True when querying config"""
        with patch('bifrost.config.get_context') as mock_get_context, \
             patch('bifrost.config.ConfigRepository') as MockRepo:

            mock_context = Mock()
            mock_context.scope = "test-org"
            mock_resolver = AsyncMock()
            mock_resolver.get_config = AsyncMock(return_value="value")
            mock_context._config_resolver = mock_resolver
            mock_get_context.return_value = mock_context

            mock_repo = MockRepo.return_value
            mock_cfg = Config(
                key="global_setting",
                value="value",
                type=ConfigType.STRING,
                scope="GLOBAL",
                orgId=None,
                updatedAt=datetime.utcnow(),
                updatedBy="test"
            )
            mock_repo.get_config = AsyncMock(return_value=mock_cfg)

            await config.get("global_setting")

            # Verify fallback_to_global was True
            mock_repo.get_config.assert_called_once_with("global_setting", fallback_to_global=True)
