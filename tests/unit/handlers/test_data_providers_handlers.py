"""
Unit tests for data_providers_handlers
Tests data provider discovery and option retrieval logic
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from shared.handlers.data_providers_handlers import (
    get_data_provider_options_handler,
    list_data_providers_handler,
    compute_cache_key,
    _cache
)
from shared.context import ExecutionContext


class TestGetDataProviderOptionsHandler:
    """Test get_data_provider_options_handler business logic"""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear cache before each test"""
        _cache.clear()
        yield
        _cache.clear()

    @pytest.mark.asyncio
    async def test_missing_provider_name(self):
        """Test with missing provider name"""
        context = Mock(spec=ExecutionContext)
        context.org_id = "org-123"

        response, status_code = await get_data_provider_options_handler(
            provider_name=None,
            context=context,
            no_cache=False
        )

        assert status_code == 400
        assert response["error"] == "BadRequest"
        assert "providerName is required" in response["message"]

    @pytest.mark.asyncio
    async def test_empty_provider_name(self):
        """Test with empty provider name"""
        context = Mock(spec=ExecutionContext)
        context.org_id = "org-123"

        response, status_code = await get_data_provider_options_handler(
            provider_name="",
            context=context,
            no_cache=False
        )

        assert status_code == 400
        assert response["error"] == "BadRequest"

    @pytest.mark.asyncio
    async def test_provider_not_found(self):
        """Test when provider doesn't exist in registry"""
        context = Mock(spec=ExecutionContext)
        context.org_id = "org-123"

        with patch('shared.handlers.data_providers_handlers.get_registry') as mock_reg:
            registry = mock_reg.return_value
            registry.get_data_provider.return_value = None

            response, status_code = await get_data_provider_options_handler(
                provider_name="nonexistent",
                context=context,
                no_cache=False
            )

            assert status_code == 404
            assert response["error"] == "NotFound"
            assert "nonexistent" in response["message"]

    @pytest.mark.asyncio
    async def test_provider_execution_success(self):
        """Test successful provider execution and caching"""
        context = Mock(spec=ExecutionContext)
        context.org_id = "org-123"

        mock_options = [
            {"label": "License 1", "value": "L1"},
            {"label": "License 2", "value": "L2"}
        ]

        with patch('shared.handlers.data_providers_handlers.get_registry') as mock_reg:
            registry = mock_reg.return_value
            provider_metadata = Mock()
            provider_metadata.function = AsyncMock(return_value=mock_options)
            provider_metadata.cache_ttl_seconds = 300
            provider_metadata.parameters = []  # Empty parameters list
            registry.get_data_provider.return_value = provider_metadata

            response, status_code = await get_data_provider_options_handler(
                provider_name="test_provider",
                context=context,
                no_cache=False
            )

            assert status_code == 200
            assert response["provider"] == "test_provider"
            assert response["options"] == mock_options
            assert response["cached"] is False
            assert response["cache_expires_at"] is not None

            # Verify provider was called
            provider_metadata.function.assert_called_once_with(context)

    @pytest.mark.asyncio
    async def test_provider_execution_invalid_return_type(self):
        """Test when provider returns non-list result"""
        context = Mock(spec=ExecutionContext)
        context.org_id = "org-123"

        with patch('shared.handlers.data_providers_handlers.get_registry') as mock_reg:
            registry = mock_reg.return_value
            provider_metadata = Mock()
            provider_metadata.function = AsyncMock(return_value={"not": "a list"})
            provider_metadata.cache_ttl_seconds = 300
            provider_metadata.parameters = []  # Empty parameters list
            registry.get_data_provider.return_value = provider_metadata

            response, status_code = await get_data_provider_options_handler(
                provider_name="test_provider",
                context=context,
                no_cache=False
            )

            assert status_code == 500
            assert response["error"] == "InternalError"
            assert "dict" in response["message"]

    @pytest.mark.asyncio
    async def test_provider_execution_exception(self):
        """Test when provider raises an exception"""
        context = Mock(spec=ExecutionContext)
        context.org_id = "org-123"

        with patch('shared.handlers.data_providers_handlers.get_registry') as mock_reg:
            registry = mock_reg.return_value
            provider_metadata = Mock()
            provider_metadata.function = AsyncMock(
                side_effect=Exception("Provider connection failed")
            )
            provider_metadata.cache_ttl_seconds = 300
            provider_metadata.parameters = []  # Empty parameters list
            registry.get_data_provider.return_value = provider_metadata

            response, status_code = await get_data_provider_options_handler(
                provider_name="test_provider",
                context=context,
                no_cache=False
            )

            assert status_code == 500
            assert response["error"] == "InternalError"
            assert "Provider connection failed" in response["message"]

    @pytest.mark.asyncio
    async def test_cache_hit_not_expired(self):
        """Test cache hit when TTL not expired"""
        context = Mock(spec=ExecutionContext)
        context.org_id = "org-123"

        mock_options = [{"label": "Cached", "value": "C"}]
        expires_at = datetime.utcnow() + timedelta(seconds=300)

        # Pre-populate cache
        cache_key = "org-123:cached_provider"
        _cache[cache_key] = {
            'data': mock_options,
            'expires_at': expires_at
        }

        with patch('shared.handlers.data_providers_handlers.get_registry') as mock_reg:
            registry = mock_reg.return_value
            provider_metadata = Mock()
            provider_metadata.function = AsyncMock()  # Should NOT be called
            provider_metadata.cache_ttl_seconds = 300
            provider_metadata.parameters = []  # Empty parameters list
            registry.get_data_provider.return_value = provider_metadata

            response, status_code = await get_data_provider_options_handler(
                provider_name="cached_provider",
                context=context,
                no_cache=False
            )

            assert status_code == 200
            assert response["cached"] is True
            assert response["options"] == mock_options
            # Provider should NOT have been called
            provider_metadata.function.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_expired(self):
        """Test cache miss when TTL expired"""
        context = Mock(spec=ExecutionContext)
        context.org_id = "org-123"

        old_options = [{"label": "Old", "value": "O"}]
        new_options = [{"label": "New", "value": "N"}]
        expires_at = datetime.utcnow() - timedelta(seconds=10)  # Already expired

        # Pre-populate cache with expired entry
        cache_key = "org-123:test_provider"
        _cache[cache_key] = {
            'data': old_options,
            'expires_at': expires_at
        }

        with patch('shared.handlers.data_providers_handlers.get_registry') as mock_reg:
            registry = mock_reg.return_value
            provider_metadata = Mock()
            provider_metadata.function = AsyncMock(return_value=new_options)
            provider_metadata.cache_ttl_seconds = 300
            provider_metadata.parameters = []  # Empty parameters list
            registry.get_data_provider.return_value = provider_metadata

            response, status_code = await get_data_provider_options_handler(
                provider_name="test_provider",
                context=context,
                no_cache=False
            )

            assert status_code == 200
            assert response["cached"] is False
            assert response["options"] == new_options
            # Provider should have been called (cache expired)
            provider_metadata.function.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_cache_flag_bypass(self):
        """Test no_cache=True bypasses cache"""
        context = Mock(spec=ExecutionContext)
        context.org_id = "org-123"

        cached_options = [{"label": "Cached", "value": "C"}]
        new_options = [{"label": "Fresh", "value": "F"}]
        expires_at = datetime.utcnow() + timedelta(seconds=300)

        # Pre-populate cache
        cache_key = "org-123:test_provider"
        _cache[cache_key] = {
            'data': cached_options,
            'expires_at': expires_at
        }

        with patch('shared.handlers.data_providers_handlers.get_registry') as mock_reg:
            registry = mock_reg.return_value
            provider_metadata = Mock()
            provider_metadata.function = AsyncMock(return_value=new_options)
            provider_metadata.cache_ttl_seconds = 300
            provider_metadata.parameters = []  # Empty parameters list
            registry.get_data_provider.return_value = provider_metadata

            response, status_code = await get_data_provider_options_handler(
                provider_name="test_provider",
                context=context,
                no_cache=True  # Bypass cache
            )

            assert status_code == 200
            assert response["cached"] is False
            assert response["options"] == new_options
            # Provider should have been called despite cache being valid
            provider_metadata.function.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_separate_org_contexts(self):
        """Test cache is segregated by organization"""
        org1_context = Mock(spec=ExecutionContext)
        org1_context.org_id = "org-1"

        org2_context = Mock(spec=ExecutionContext)
        org2_context.org_id = "org-2"

        org1_options = [{"label": "Org1", "value": "O1"}]
        org2_options = [{"label": "Org2", "value": "O2"}]

        with patch('shared.handlers.data_providers_handlers.get_registry') as mock_reg:
            registry = mock_reg.return_value

            # First call for org1
            provider_metadata = Mock()
            provider_metadata.function = AsyncMock(return_value=org1_options)
            provider_metadata.cache_ttl_seconds = 300
            provider_metadata.parameters = []  # Empty parameters list
            registry.get_data_provider.return_value = provider_metadata

            response1, status1 = await get_data_provider_options_handler(
                provider_name="shared_provider",
                context=org1_context,
                no_cache=False
            )

            assert response1["options"] == org1_options

            # Second call for org2 with same provider name
            provider_metadata.function = AsyncMock(return_value=org2_options)

            response2, status2 = await get_data_provider_options_handler(
                provider_name="shared_provider",
                context=org2_context,
                no_cache=False
            )

            assert response2["options"] == org2_options
            assert response1["options"] != response2["options"]

    @pytest.mark.asyncio
    async def test_cache_ttl_calculation(self):
        """Test cache expiration time is correctly calculated"""
        context = Mock(spec=ExecutionContext)
        context.org_id = "org-123"

        mock_options = [{"label": "Test", "value": "T"}]

        with patch('shared.handlers.data_providers_handlers.get_registry') as mock_reg:
            registry = mock_reg.return_value
            provider_metadata = Mock()
            provider_metadata.function = AsyncMock(return_value=mock_options)
            provider_metadata.cache_ttl_seconds = 600  # 10 minutes
            provider_metadata.parameters = []  # Empty parameters list

            registry.get_data_provider.return_value = provider_metadata

            response, status_code = await get_data_provider_options_handler(
                provider_name="test_provider",
                context=context,
                no_cache=False
            )
            after_call = datetime.utcnow()

            # Parse the ISO format timestamp
            cache_expires_str = response["cache_expires_at"].rstrip('Z')
            cache_expires = datetime.fromisoformat(cache_expires_str)

            # Should be approximately 600 seconds in future
            time_to_expire = (cache_expires - after_call).total_seconds()
            assert 590 <= time_to_expire <= 610  # Allow small variation


class TestListDataProvidersHandler:
    """Test list_data_providers_handler business logic"""

    @pytest.mark.asyncio
    async def test_list_empty_providers(self):
        """Test list when no providers are registered"""
        with patch('shared.handlers.data_providers_handlers.get_registry') as mock_reg:
            registry = mock_reg.return_value
            registry.get_all_data_providers.return_value = []

            response, status_code = await list_data_providers_handler()

            assert status_code == 200
            assert response["providers"] == []

    @pytest.mark.asyncio
    async def test_list_multiple_providers(self):
        """Test list with multiple providers"""
        with patch('shared.handlers.data_providers_handlers.get_registry') as mock_reg:
            registry = mock_reg.return_value

            provider1 = Mock()
            provider1.name = "get_licenses"
            provider1.description = "Get M365 licenses"
            provider1.category = "m365"
            provider1.cache_ttl_seconds = 300
            provider1.parameters = []  # Empty parameters list

            provider2 = Mock()
            provider2.name = "get_devices"
            provider2.description = "Get connected devices"
            provider2.category = "intune"
            provider2.cache_ttl_seconds = 600
            provider2.parameters = []  # Empty parameters list

            registry.get_all_data_providers.return_value = [provider1, provider2]

            response, status_code = await list_data_providers_handler()

            assert status_code == 200
            assert len(response["providers"]) == 2

            providers = response["providers"]
            assert providers[0]["name"] == "get_licenses"
            assert providers[0]["description"] == "Get M365 licenses"
            assert providers[0]["category"] == "m365"
            assert providers[0]["cache_ttl_seconds"] == 300

            assert providers[1]["name"] == "get_devices"
            assert providers[1]["description"] == "Get connected devices"
            assert providers[1]["category"] == "intune"
            assert providers[1]["cache_ttl_seconds"] == 600

    @pytest.mark.asyncio
    async def test_list_provider_format(self):
        """Test provider response format matches specification"""
        with patch('shared.handlers.data_providers_handlers.get_registry') as mock_reg:
            registry = mock_reg.return_value

            provider = Mock()
            provider.name = "test_provider"
            provider.description = "Test provider"
            provider.category = "test"
            provider.cache_ttl_seconds = 300
            provider.parameters = []  # Empty parameters list

            registry.get_all_data_providers.return_value = [provider]

            response, status_code = await list_data_providers_handler()

            assert status_code == 200
            assert "providers" in response
            assert isinstance(response["providers"], list)

            provider_data = response["providers"][0]
            assert "name" in provider_data
            assert "description" in provider_data
            assert "category" in provider_data
            assert "cache_ttl_seconds" in provider_data
            assert "parameters" in provider_data

    @pytest.mark.asyncio
    async def test_list_always_returns_200(self):
        """Test list always returns 200 regardless of provider count"""
        with patch('shared.handlers.data_providers_handlers.get_registry') as mock_reg:
            registry = mock_reg.return_value

            # Test with empty list
            registry.get_all_data_providers.return_value = []
            response1, status1 = await list_data_providers_handler()
            assert status1 == 200

            # Test with providers
            provider = Mock()
            provider.name = "test"
            provider.description = "Test"
            provider.category = "test"
            provider.cache_ttl_seconds = 300
            provider.parameters = []  # Empty parameters list
            registry.get_all_data_providers.return_value = [provider]

            response2, status2 = await list_data_providers_handler()
            assert status2 == 200


class TestComputeCacheKey:
    """T023: Unit test for cache key computation with input hash"""

    def test_cache_key_without_inputs_and_org(self):
        """Test cache key format without inputs or org_id (backward compatible)"""
        key = compute_cache_key("my_provider")

        assert key == "my_provider"

    def test_cache_key_with_org_no_inputs(self):
        """Test cache key format with org_id but no inputs"""
        key = compute_cache_key("my_provider", org_id="org-123")

        assert key == "org-123:my_provider"

    def test_cache_key_with_inputs_no_org(self):
        """
        T023: Test cache key includes input hash when inputs provided

        Expected format: {provider_name}:{input_hash}
        Input hash should be first 16 characters of SHA-256 of sorted JSON
        """
        inputs = {"token": "ghp_abc123", "org": "my-org"}
        key = compute_cache_key("get_repos", inputs=inputs)

        # Should have format: provider_name:hash
        assert ":" in key
        parts = key.split(":")
        assert parts[0] == "get_repos"
        assert len(parts[1]) == 16  # Hash is 16 characters

    def test_cache_key_with_inputs_and_org(self):
        """
        T023: Test cache key with both inputs and org_id

        Expected format: {org_id}:{provider_name}:{input_hash}
        """
        inputs = {"param1": "value1", "param2": "value2"}
        key = compute_cache_key("my_provider", inputs=inputs, org_id="org-456")

        # Should have format: org_id:provider_name:hash
        parts = key.split(":")
        assert len(parts) == 3
        assert parts[0] == "org-456"
        assert parts[1] == "my_provider"
        assert len(parts[2]) == 16  # Hash is 16 characters

    def test_cache_key_deterministic(self):
        """
        T023: Test that cache key is deterministic for same inputs

        Expected behavior:
        - Same inputs (different order) should produce same hash
        - JSON keys are sorted for deterministic hashing
        """
        inputs1 = {"b": "2", "a": "1", "c": "3"}
        inputs2 = {"a": "1", "c": "3", "b": "2"}
        inputs3 = {"c": "3", "a": "1", "b": "2"}

        key1 = compute_cache_key("provider", inputs=inputs1, org_id="org")
        key2 = compute_cache_key("provider", inputs=inputs2, org_id="org")
        key3 = compute_cache_key("provider", inputs=inputs3, org_id="org")

        # All keys should be identical (deterministic)
        assert key1 == key2
        assert key2 == key3

    def test_cache_key_different_inputs_different_hash(self):
        """
        T023: Test that different inputs produce different cache keys

        Expected behavior:
        - Different input values should produce different hashes
        - Cache isolation between different input sets
        """
        key1 = compute_cache_key("provider", inputs={"token": "abc123"}, org_id="org")
        key2 = compute_cache_key("provider", inputs={"token": "xyz789"}, org_id="org")

        # Keys should be different
        assert key1 != key2

        # Provider and org parts should match
        assert key1.split(":")[0] == key2.split(":")[0]  # org
        assert key1.split(":")[1] == key2.split(":")[1]  # provider

        # Hash parts should differ
        assert key1.split(":")[2] != key2.split(":")[2]

    def test_cache_key_empty_inputs_dict(self):
        """
        Test cache key with empty inputs dict (edge case)

        Expected behavior:
        - Empty dict is treated as "no inputs" (Python truthiness)
        - Falls back to backward-compatible format without hash
        """
        key = compute_cache_key("provider", inputs={}, org_id="org")

        # Empty dict should be treated like no inputs (backward compatible)
        assert key == "org:provider"

    def test_cache_key_complex_input_types(self):
        """Test cache key with complex input values (nested dicts, lists, etc.)"""
        inputs = {
            "string": "value",
            "number": 42,
            "bool": True,
            "list": [1, 2, 3],
            "nested": {"key": "val"}
        }

        key = compute_cache_key("provider", inputs=inputs, org_id="org")

        # Should handle complex JSON-serializable inputs
        parts = key.split(":")
        assert len(parts) == 3
        assert parts[0] == "org"
        assert parts[1] == "provider"
        assert len(parts[2]) == 16

    def test_cache_key_input_value_changes(self):
        """
        T023: Test that changing input values changes cache key

        Expected behavior:
        - Same parameter name, different value = different cache key
        - Ensures proper cache isolation
        """
        base_inputs = {"repo": "owner/repo1", "token": "abc"}
        updated_inputs = {"repo": "owner/repo2", "token": "abc"}

        key1 = compute_cache_key("get_branches", inputs=base_inputs)
        key2 = compute_cache_key("get_branches", inputs=updated_inputs)

        assert key1 != key2  # Different cache keys

    def test_cache_key_additional_parameter(self):
        """
        T023: Test that adding a parameter changes cache key

        Expected behavior:
        - Adding new parameter should change hash
        """
        inputs1 = {"token": "abc"}
        inputs2 = {"token": "abc", "filter": "active"}

        key1 = compute_cache_key("provider", inputs=inputs1)
        key2 = compute_cache_key("provider", inputs=inputs2)

        assert key1 != key2  # Different cache keys
