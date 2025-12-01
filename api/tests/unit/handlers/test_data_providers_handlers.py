"""
Unit tests for data_providers_handlers
Tests data provider discovery and option retrieval logic via unified engine
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from shared.handlers.data_providers_handlers import (
    get_data_provider_options_handler,
    list_data_providers_handler,
    validate_data_provider_inputs
)
from shared.context import ExecutionContext
from shared.models import ExecutionStatus


class TestGetDataProviderOptionsHandler:
    """Test get_data_provider_options_handler business logic"""

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
        """Test when provider doesn't exist"""
        context = Mock(spec=ExecutionContext)
        context.org_id = "org-123"

        with patch('shared.handlers.data_providers_handlers.load_data_provider') as mock_load:
            mock_load.return_value = None

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
        """Test successful provider execution through engine"""
        context = Mock(spec=ExecutionContext)
        context.org_id = "org-123"
        context.user_id = "user-123"
        context.email = "test@example.com"
        context.name = "Test User"
        context.organization = Mock()
        context.organization.id = "org-123"
        context._config = {}
        context.is_platform_admin = False

        mock_options = [
            {"label": "License 1", "value": "L1"},
            {"label": "License 2", "value": "L2"}
        ]

        # Create mock execution result
        mock_result = Mock()
        mock_result.status = ExecutionStatus.SUCCESS
        mock_result.result = mock_options
        mock_result.cached = False
        mock_result.cache_expires_at = "2025-01-01T00:00:00Z"

        # Create mock provider function and metadata
        mock_func = AsyncMock()
        mock_metadata = Mock()
        mock_metadata.cache_ttl_seconds = 300
        mock_metadata.parameters = []

        with patch('shared.handlers.data_providers_handlers.load_data_provider') as mock_load, \
             patch('shared.handlers.data_providers_handlers.execute', new_callable=AsyncMock) as mock_execute:

            mock_load.return_value = (mock_func, mock_metadata)
            mock_execute.return_value = mock_result

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

            # Verify engine was called with ExecutionRequest
            mock_execute.assert_called_once()
            request = mock_execute.call_args[0][0]
            assert request.name == "test_provider"
            assert request.transient is True
            assert request.no_cache is False

    @pytest.mark.asyncio
    async def test_provider_execution_invalid_return_type(self):
        """Test when provider returns non-list result"""
        context = Mock(spec=ExecutionContext)
        context.org_id = "org-123"
        context.user_id = "user-123"
        context.email = "test@example.com"
        context.name = "Test User"
        context.organization = Mock()
        context.organization.id = "org-123"
        context._config = {}
        context.is_platform_admin = False

        # Create mock execution result with dict instead of list
        mock_result = Mock()
        mock_result.status = ExecutionStatus.SUCCESS
        mock_result.result = {"not": "a list"}
        mock_result.cached = False
        mock_result.cache_expires_at = None

        mock_func = AsyncMock()
        mock_metadata = Mock()
        mock_metadata.cache_ttl_seconds = 300
        mock_metadata.parameters = []

        with patch('shared.handlers.data_providers_handlers.load_data_provider') as mock_load, \
             patch('shared.handlers.data_providers_handlers.execute', new_callable=AsyncMock) as mock_execute:

            mock_load.return_value = (mock_func, mock_metadata)
            mock_execute.return_value = mock_result

            response, status_code = await get_data_provider_options_handler(
                provider_name="test_provider",
                context=context,
                no_cache=False
            )

            assert status_code == 500
            assert response["error"] == "InternalError"
            assert "dict" in response["message"]

    @pytest.mark.asyncio
    async def test_provider_execution_failure(self):
        """Test when engine returns failed execution result"""
        context = Mock(spec=ExecutionContext)
        context.org_id = "org-123"
        context.user_id = "user-123"
        context.email = "test@example.com"
        context.name = "Test User"
        context.organization = Mock()
        context.organization.id = "org-123"
        context._config = {}
        context.is_platform_admin = False

        # Create mock failed execution result
        mock_result = Mock()
        mock_result.status = ExecutionStatus.FAILED
        mock_result.error_message = "Provider connection failed"
        mock_result.error_type = "ConnectionError"

        mock_func = AsyncMock()
        mock_metadata = Mock()
        mock_metadata.cache_ttl_seconds = 300
        mock_metadata.parameters = []

        with patch('shared.handlers.data_providers_handlers.load_data_provider') as mock_load, \
             patch('shared.handlers.data_providers_handlers.execute', new_callable=AsyncMock) as mock_execute:

            mock_load.return_value = (mock_func, mock_metadata)
            mock_execute.return_value = mock_result

            response, status_code = await get_data_provider_options_handler(
                provider_name="test_provider",
                context=context,
                no_cache=False
            )

            assert status_code == 500
            assert response["error"] == "InternalError"
            assert "Provider connection failed" in response["message"]

    @pytest.mark.asyncio
    async def test_engine_cache_hit(self):
        """Test cache hit via engine (cached=True in result)"""
        context = Mock(spec=ExecutionContext)
        context.org_id = "org-123"
        context.user_id = "user-123"
        context.email = "test@example.com"
        context.name = "Test User"
        context.organization = Mock()
        context.organization.id = "org-123"
        context._config = {}
        context.is_platform_admin = False

        mock_options = [{"label": "Cached", "value": "C"}]

        # Create mock cached execution result
        mock_result = Mock()
        mock_result.status = ExecutionStatus.SUCCESS
        mock_result.result = mock_options
        mock_result.cached = True
        mock_result.cache_expires_at = "2025-01-01T12:00:00Z"

        mock_func = AsyncMock()
        mock_metadata = Mock()
        mock_metadata.cache_ttl_seconds = 300
        mock_metadata.parameters = []

        with patch('shared.handlers.data_providers_handlers.load_data_provider') as mock_load, \
             patch('shared.handlers.data_providers_handlers.execute', new_callable=AsyncMock) as mock_execute:

            mock_load.return_value = (mock_func, mock_metadata)
            mock_execute.return_value = mock_result

            response, status_code = await get_data_provider_options_handler(
                provider_name="cached_provider",
                context=context,
                no_cache=False
            )

            assert status_code == 200
            assert response["cached"] is True
            assert response["options"] == mock_options
            assert response["cache_expires_at"] == "2025-01-01T12:00:00Z"

    @pytest.mark.asyncio
    async def test_no_cache_flag_passed_to_engine(self):
        """Test no_cache=True is passed to engine"""
        context = Mock(spec=ExecutionContext)
        context.org_id = "org-123"
        context.user_id = "user-123"
        context.email = "test@example.com"
        context.name = "Test User"
        context.organization = Mock()
        context.organization.id = "org-123"
        context._config = {}
        context.is_platform_admin = False

        mock_options = [{"label": "Fresh", "value": "F"}]

        mock_result = Mock()
        mock_result.status = ExecutionStatus.SUCCESS
        mock_result.result = mock_options
        mock_result.cached = False
        mock_result.cache_expires_at = "2025-01-01T00:00:00Z"

        mock_func = AsyncMock()
        mock_metadata = Mock()
        mock_metadata.cache_ttl_seconds = 300
        mock_metadata.parameters = []

        with patch('shared.handlers.data_providers_handlers.load_data_provider') as mock_load, \
             patch('shared.handlers.data_providers_handlers.execute', new_callable=AsyncMock) as mock_execute:

            mock_load.return_value = (mock_func, mock_metadata)
            mock_execute.return_value = mock_result

            response, status_code = await get_data_provider_options_handler(
                provider_name="test_provider",
                context=context,
                no_cache=True  # Bypass cache
            )

            assert status_code == 200
            # Verify no_cache was passed to engine
            request = mock_execute.call_args[0][0]
            assert request.no_cache is True

    @pytest.mark.asyncio
    async def test_inputs_passed_to_engine(self):
        """Test that inputs are passed to engine as parameters"""
        context = Mock(spec=ExecutionContext)
        context.org_id = "org-123"
        context.user_id = "user-123"
        context.email = "test@example.com"
        context.name = "Test User"
        context.organization = Mock()
        context.organization.id = "org-123"
        context._config = {}
        context.is_platform_admin = False

        mock_options = [{"label": "Result", "value": "R"}]
        inputs = {"filter": "active", "limit": 10}

        mock_result = Mock()
        mock_result.status = ExecutionStatus.SUCCESS
        mock_result.result = mock_options
        mock_result.cached = False
        mock_result.cache_expires_at = "2025-01-01T00:00:00Z"

        mock_func = AsyncMock()
        mock_metadata = Mock()
        mock_metadata.cache_ttl_seconds = 300
        mock_metadata.parameters = []

        with patch('shared.handlers.data_providers_handlers.load_data_provider') as mock_load, \
             patch('shared.handlers.data_providers_handlers.execute', new_callable=AsyncMock) as mock_execute:

            mock_load.return_value = (mock_func, mock_metadata)
            mock_execute.return_value = mock_result

            response, status_code = await get_data_provider_options_handler(
                provider_name="test_provider",
                context=context,
                no_cache=False,
                inputs=inputs
            )

            assert status_code == 200
            # Verify inputs were passed as parameters
            request = mock_execute.call_args[0][0]
            assert request.parameters == inputs

    @pytest.mark.asyncio
    async def test_load_failure_returns_error(self):
        """Test that load failure returns 500 error"""
        context = Mock(spec=ExecutionContext)
        context.org_id = "org-123"

        with patch('shared.handlers.data_providers_handlers.load_data_provider') as mock_load:
            mock_load.side_effect = SyntaxError("Invalid syntax at line 10")

            response, status_code = await get_data_provider_options_handler(
                provider_name="test_provider",
                context=context,
                no_cache=False
            )

            assert status_code == 500
            assert response["error"] == "DataProviderLoadError"
            assert "Invalid syntax" in response["message"]

    @pytest.mark.asyncio
    async def test_validation_error_missing_required_param(self):
        """Test validation error when required parameter is missing"""
        context = Mock(spec=ExecutionContext)
        context.org_id = "org-123"

        mock_func = AsyncMock()
        mock_metadata = Mock()
        mock_metadata.cache_ttl_seconds = 300

        # Define a required parameter
        param = Mock()
        param.name = "required_field"
        param.required = True
        mock_metadata.parameters = [param]

        with patch('shared.handlers.data_providers_handlers.load_data_provider') as mock_load:
            mock_load.return_value = (mock_func, mock_metadata)

            # Call without the required parameter
            response, status_code = await get_data_provider_options_handler(
                provider_name="test_provider",
                context=context,
                no_cache=False,
                inputs={}  # Missing required_field
            )

            assert status_code == 400
            assert response["error"] == "BadRequest"
            assert "required_field" in str(response["details"])


class TestListDataProvidersHandler:
    """Test list_data_providers_handler business logic"""

    @pytest.mark.asyncio
    async def test_list_empty_providers(self):
        """Test list when no providers are registered"""
        with patch('shared.handlers.data_providers_handlers.scan_all_data_providers') as mock_scan:
            mock_scan.return_value = []

            response, status_code = await list_data_providers_handler()

            assert status_code == 200
            assert response["providers"] == []

    @pytest.mark.asyncio
    async def test_list_multiple_providers(self):
        """Test list with multiple providers"""
        with patch('shared.handlers.data_providers_handlers.scan_all_data_providers') as mock_scan:
            provider1 = Mock()
            provider1.name = "get_licenses"
            provider1.description = "Get M365 licenses"
            provider1.category = "m365"
            provider1.cache_ttl_seconds = 300
            provider1.parameters = []

            provider2 = Mock()
            provider2.name = "get_devices"
            provider2.description = "Get connected devices"
            provider2.category = "intune"
            provider2.cache_ttl_seconds = 600
            provider2.parameters = []

            mock_scan.return_value = [provider1, provider2]

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
        with patch('shared.handlers.data_providers_handlers.scan_all_data_providers') as mock_scan:
            provider = Mock()
            provider.name = "test_provider"
            provider.description = "Test provider"
            provider.category = "test"
            provider.cache_ttl_seconds = 300
            provider.parameters = []

            mock_scan.return_value = [provider]

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
    async def test_list_provider_with_parameters(self):
        """Test list includes parameter definitions"""
        with patch('shared.handlers.data_providers_handlers.scan_all_data_providers') as mock_scan:
            param = Mock()
            param.name = "filter"
            param.type = "string"
            param.required = True
            param.label = "Filter"
            param.default_value = None
            param.help_text = "Filter results"

            provider = Mock()
            provider.name = "parameterized_provider"
            provider.description = "Provider with params"
            provider.category = "test"
            provider.cache_ttl_seconds = 300
            provider.parameters = [param]

            mock_scan.return_value = [provider]

            response, status_code = await list_data_providers_handler()

            assert status_code == 200
            provider_data = response["providers"][0]
            assert len(provider_data["parameters"]) == 1
            assert provider_data["parameters"][0]["name"] == "filter"
            assert provider_data["parameters"][0]["type"] == "string"
            assert provider_data["parameters"][0]["required"] is True


class TestValidateDataProviderInputs:
    """Test validate_data_provider_inputs function"""

    def test_no_parameters_no_inputs(self):
        """Test with no parameters defined and no inputs"""
        provider_metadata = Mock()
        provider_metadata.parameters = []

        errors = validate_data_provider_inputs(provider_metadata, None)
        assert errors == []

    def test_no_parameters_with_inputs(self):
        """Test with no parameters defined but inputs provided (allowed for forward compat)"""
        provider_metadata = Mock()
        provider_metadata.parameters = []

        errors = validate_data_provider_inputs(provider_metadata, {"extra": "value"})
        assert errors == []

    def test_required_parameter_present(self):
        """Test with required parameter present"""
        param = Mock()
        param.name = "required_field"
        param.required = True

        provider_metadata = Mock()
        provider_metadata.parameters = [param]

        errors = validate_data_provider_inputs(provider_metadata, {"required_field": "value"})
        assert errors == []

    def test_required_parameter_missing(self):
        """Test with required parameter missing"""
        param = Mock()
        param.name = "required_field"
        param.required = True

        provider_metadata = Mock()
        provider_metadata.parameters = [param]

        errors = validate_data_provider_inputs(provider_metadata, {})
        assert len(errors) == 1
        assert "required_field" in errors[0]

    def test_optional_parameter_missing(self):
        """Test with optional parameter missing (allowed)"""
        param = Mock()
        param.name = "optional_field"
        param.required = False

        provider_metadata = Mock()
        provider_metadata.parameters = [param]

        errors = validate_data_provider_inputs(provider_metadata, {})
        assert errors == []

    def test_multiple_required_missing(self):
        """Test with multiple required parameters missing"""
        param1 = Mock()
        param1.name = "field1"
        param1.required = True

        param2 = Mock()
        param2.name = "field2"
        param2.required = True

        provider_metadata = Mock()
        provider_metadata.parameters = [param1, param2]

        errors = validate_data_provider_inputs(provider_metadata, {})
        assert len(errors) == 2
        assert any("field1" in e for e in errors)
        assert any("field2" in e for e in errors)

    def test_extra_inputs_allowed(self):
        """Test that extra inputs are allowed (forward compatibility)"""
        param = Mock()
        param.name = "defined_field"
        param.required = True

        provider_metadata = Mock()
        provider_metadata.parameters = [param]

        errors = validate_data_provider_inputs(
            provider_metadata,
            {"defined_field": "value", "extra_field": "extra"}
        )
        assert errors == []
