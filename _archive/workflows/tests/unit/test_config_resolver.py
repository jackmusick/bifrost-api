"""
Unit Tests: Config Resolver

Tests the ConfigResolver class in isolation:
- Type detection and value parsing
- Secret reference resolution
- Fallback behavior for missing secrets
- Error handling for invalid values
"""

import pytest
from unittest.mock import Mock, patch


class TestConfigResolver:
    """Unit tests for ConfigResolver"""

    @pytest.fixture
    def mock_keyvault_client(self):
        """Create a mock KeyVaultClient"""
        return Mock()

    @pytest.fixture
    def config_resolver(self, mock_keyvault_client):
        """Create ConfigResolver with mocked KeyVault client"""
        from engine.shared.config_resolver import ConfigResolver

        with patch('engine.shared.config_resolver.KeyVaultClient', return_value=mock_keyvault_client):
            resolver = ConfigResolver()
            resolver.kv_client = mock_keyvault_client
            return resolver

    def test_parse_string_value(self, config_resolver):
        """Test parsing string configuration values"""
        result = config_resolver._parse_value("test-value", "string")
        assert result == "test-value"
        assert isinstance(result, str)

    def test_parse_int_value(self, config_resolver):
        """Test parsing integer configuration values"""
        result = config_resolver._parse_value("42", "int")
        assert result == 42
        assert isinstance(result, int)

    def test_parse_int_value_invalid(self, config_resolver):
        """Test error handling for invalid integer values"""
        with pytest.raises(ValueError, match="Could not parse"):
            config_resolver._parse_value("not-a-number", "int")

    def test_parse_bool_value_true(self, config_resolver):
        """Test parsing boolean true values"""
        true_values = ["true", "True", "TRUE", "yes", "1"]
        for value in true_values:
            result = config_resolver._parse_value(value, "bool")
            assert result is True

    def test_parse_bool_value_false(self, config_resolver):
        """Test parsing boolean false values"""
        false_values = ["false", "False", "FALSE", "no", "0"]
        for value in false_values:
            result = config_resolver._parse_value(value, "bool")
            assert result is False

    def test_parse_json_value(self, config_resolver):
        """Test parsing JSON configuration values"""
        json_str = '{"key": "value", "count": 42}'
        result = config_resolver._parse_value(json_str, "json")
        assert isinstance(result, dict)
        assert result["key"] == "value"
        assert result["count"] == 42

    def test_parse_json_value_array(self, config_resolver):
        """Test parsing JSON array values"""
        json_str = '["item1", "item2", "item3"]'
        result = config_resolver._parse_value(json_str, "json")
        assert isinstance(result, list)
        assert len(result) == 3

    def test_parse_json_value_invalid(self, config_resolver):
        """Test error handling for invalid JSON"""
        with pytest.raises(ValueError, match="Could not parse"):
            config_resolver._parse_value("{invalid-json", "json")

    def test_resolve_secret_ref(self, config_resolver, mock_keyvault_client):
        """Test resolving secret references"""
        mock_keyvault_client.get_secret.return_value = "secret-value-from-vault"

        result = config_resolver._resolve_secret_ref("org-123", "api-key", "api-key")

        assert result == "secret-value-from-vault"
        mock_keyvault_client.get_secret.assert_called_once_with("org-123", "api-key")

    def test_resolve_secret_ref_missing(self, config_resolver, mock_keyvault_client):
        """Test error handling for missing secret references"""
        mock_keyvault_client.get_secret.side_effect = KeyError("Secret not found")

        with pytest.raises(ValueError, match="not found"):
            config_resolver._resolve_secret_ref("org-123", "missing-key", "missing-key")

    def test_get_config_string_type(self, config_resolver):
        """Test getting string configuration"""
        config_data = {
            "timeout": {
                "value": "300",
                "type": "string"
            }
        }

        result = config_resolver.get_config("org-123", "timeout", config_data)

        assert result == "300"

    def test_get_config_int_type(self, config_resolver):
        """Test getting integer configuration"""
        config_data = {
            "max_retries": {
                "value": "5",
                "type": "int"
            }
        }

        result = config_resolver.get_config("org-123", "max_retries", config_data)

        assert result == 5
        assert isinstance(result, int)

    def test_get_config_bool_type(self, config_resolver):
        """Test getting boolean configuration"""
        config_data = {
            "enabled": {
                "value": "true",
                "type": "bool"
            }
        }

        result = config_resolver.get_config("org-123", "enabled", config_data)

        assert result is True

    def test_get_config_json_type(self, config_resolver):
        """Test getting JSON configuration"""
        config_data = {
            "settings": {
                "value": '{"key": "value"}',
                "type": "json"
            }
        }

        result = config_resolver.get_config("org-123", "settings", config_data)

        assert isinstance(result, dict)
        assert result["key"] == "value"

    def test_get_config_secret_ref_type(self, config_resolver, mock_keyvault_client):
        """Test getting secret reference configuration"""
        mock_keyvault_client.get_secret.return_value = "actual-secret-value"

        config_data = {
            "api_key": {
                "value": "api-key",
                "type": "secret_ref"
            }
        }

        result = config_resolver.get_config("org-123", "api_key", config_data)

        assert result == "actual-secret-value"
        mock_keyvault_client.get_secret.assert_called_once_with("org-123", "api-key")

    def test_get_config_default_value(self, config_resolver):
        """Test returning default value for missing config"""
        config_data = {}

        result = config_resolver.get_config("org-123", "missing_key", config_data, default="default-value")

        assert result == "default-value"

    def test_get_config_none_default(self, config_resolver):
        """Test returning None for missing config without default"""
        config_data = {}

        result = config_resolver.get_config("org-123", "missing_key", config_data, default=None)

        assert result is None

    def test_get_config_missing_no_default_raises(self, config_resolver):
        """Test that missing config without default raises KeyError"""
        config_data = {}

        with pytest.raises(KeyError, match="Configuration key"):
            config_resolver.get_config("org-123", "missing_key", config_data)

    def test_get_config_invalid_type_structure(self, config_resolver):
        """Test handling of malformed config entry (missing type)"""
        config_data = {
            "bad_config": {
                "value": "some-value"
                # Missing "type" field
            }
        }

        # Should treat as string when type is missing
        result = config_resolver.get_config("org-123", "bad_config", config_data)
        assert result == "some-value"

    def test_get_config_invalid_type_field(self, config_resolver):
        """Test handling of unknown config type"""
        config_data = {
            "unknown_type_config": {
                "value": "some-value",
                "type": "unknown_type"
            }
        }

        # Should fallback to string for unknown types
        result = config_resolver.get_config("org-123", "unknown_type_config", config_data)
        assert result == "some-value"

    def test_get_config_type_auto_detection_string(self, config_resolver):
        """Test auto-detection of string values"""
        # When config_data has just a string value (not a dict)
        config_data = {
            "simple_string": "just-a-string"
        }

        result = config_resolver.get_config("org-123", "simple_string", config_data)
        assert result == "just-a-string"

    def test_secret_resolution_logging(self, config_resolver, mock_keyvault_client, caplog):
        """Test that secret resolution is logged (without exposing values)"""
        import logging
        caplog.set_level(logging.INFO)

        mock_keyvault_client.get_secret.return_value = "secret-value"

        config_data = {
            "api_key": {
                "value": "api-key",
                "type": "secret_ref"
            }
        }

        config_resolver.get_config("org-123", "api_key", config_data)

        # Check that logging occurred without exposing secret value
        assert any("Resolving secret" in record.message for record in caplog.records)
        assert not any("secret-value" in record.message for record in caplog.records)

    def test_keyvault_client_not_initialized(self):
        """Test fallback behavior when Key Vault client is not available"""
        from engine.shared.config_resolver import ConfigResolver

        with patch('engine.shared.config_resolver.KeyVaultClient', side_effect=Exception("No vault URL")):
            resolver = ConfigResolver()

            # Should still work for non-secret configs
            config_data = {
                "timeout": {
                    "value": "300",
                    "type": "string"
                }
            }
            result = resolver.get_config("org-123", "timeout", config_data)
            assert result == "300"

            # But secret refs should fail gracefully
            config_data = {
                "api_key": {
                    "value": "api-key",
                    "type": "secret_ref"
                }
            }
            with pytest.raises(ValueError, match="Key Vault client not available"):
                resolver.get_config("org-123", "api_key", config_data)
