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
    _cache
)
from shared.request_context import RequestContext


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
        context = Mock(spec=RequestContext)
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
        context = Mock(spec=RequestContext)
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
        context = Mock(spec=RequestContext)
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
        context = Mock(spec=RequestContext)
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
        context = Mock(spec=RequestContext)
        context.org_id = "org-123"

        with patch('shared.handlers.data_providers_handlers.get_registry') as mock_reg:
            registry = mock_reg.return_value
            provider_metadata = Mock()
            provider_metadata.function = AsyncMock(return_value={"not": "a list"})
            provider_metadata.cache_ttl_seconds = 300
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
        context = Mock(spec=RequestContext)
        context.org_id = "org-123"

        with patch('shared.handlers.data_providers_handlers.get_registry') as mock_reg:
            registry = mock_reg.return_value
            provider_metadata = Mock()
            provider_metadata.function = AsyncMock(
                side_effect=Exception("Provider connection failed")
            )
            provider_metadata.cache_ttl_seconds = 300
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
        context = Mock(spec=RequestContext)
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
        context = Mock(spec=RequestContext)
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
        context = Mock(spec=RequestContext)
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
        org1_context = Mock(spec=RequestContext)
        org1_context.org_id = "org-1"

        org2_context = Mock(spec=RequestContext)
        org2_context.org_id = "org-2"

        org1_options = [{"label": "Org1", "value": "O1"}]
        org2_options = [{"label": "Org2", "value": "O2"}]

        with patch('shared.handlers.data_providers_handlers.get_registry') as mock_reg:
            registry = mock_reg.return_value

            # First call for org1
            provider_metadata = Mock()
            provider_metadata.function = AsyncMock(return_value=org1_options)
            provider_metadata.cache_ttl_seconds = 300
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
        context = Mock(spec=RequestContext)
        context.org_id = "org-123"

        mock_options = [{"label": "Test", "value": "T"}]

        with patch('shared.handlers.data_providers_handlers.get_registry') as mock_reg:
            registry = mock_reg.return_value
            provider_metadata = Mock()
            provider_metadata.function = AsyncMock(return_value=mock_options)
            provider_metadata.cache_ttl_seconds = 600  # 10 minutes

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

            provider2 = Mock()
            provider2.name = "get_devices"
            provider2.description = "Get connected devices"
            provider2.category = "intune"
            provider2.cache_ttl_seconds = 600

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
            registry.get_all_data_providers.return_value = [provider]

            response2, status2 = await list_data_providers_handler()
            assert status2 == 200
