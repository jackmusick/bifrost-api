"""
Integration Test: Authentication Flow (T039)

Tests the tiered authentication system:
1. Function key authentication (x-functions-key header or code query param)
2. Easy Auth (X-MS-CLIENT-PRINCIPAL header)
3. 403 if neither present

Verifies priority order and org context loading with each auth method.
"""

import pytest
import json
import base64
from unittest.mock import Mock, patch, AsyncMock
import azure.functions as func


@pytest.mark.asyncio
class TestAuthenticationFlow:
    """Test tiered authentication priority and org context loading"""

    @pytest.fixture
    def mock_org_entity(self):
        """Mock organization entity from Table Storage"""
        return {
            'PartitionKey': 'GLOBAL',
            'RowKey': 'org:test-org-123',
            'Name': 'Test Organization',
            'TenantId': 'tenant-456',
            'IsActive': True
        }

    @pytest.fixture
    def mock_config_entities(self):
        """Mock configuration entities"""
        return [
            {
                'PartitionKey': 'test-org-123',
                'RowKey': 'config:api_endpoint',
                'Value': 'https://api.example.com',
                'Type': 'string'
            },
            {
                'PartitionKey': 'test-org-123',
                'RowKey': 'config:features',
                'Value': '{"automation": true, "reporting": false}',
                'Type': 'json'
            }
        ]

    def create_mock_request(
        self,
        org_id: str = "test-org-123",
        function_key: str = None,
        easy_auth_principal: dict = None,
        method: str = "POST",
        url: str = "http://localhost:7071/api/workflows/test"
    ) -> func.HttpRequest:
        """Create mock HttpRequest with authentication headers"""
        headers = {"X-Organization-Id": org_id}

        # Add function key if provided (header takes precedence)
        if function_key:
            headers["x-functions-key"] = function_key

        # Add Easy Auth principal if provided
        if easy_auth_principal:
            principal_json = json.dumps(easy_auth_principal)
            principal_b64 = base64.b64encode(principal_json.encode()).decode()
            headers["X-MS-CLIENT-PRINCIPAL"] = principal_b64

        return func.HttpRequest(
            method=method,
            url=url,
            headers=headers,
            body=b'{"workflow": "test"}'
        )

    @pytest.mark.asyncio
    async def test_function_key_authentication_success(
        self, mock_org_entity, mock_config_entities
    ):
        """
        Test function key authentication (priority 1)

        When x-functions-key header is present, should authenticate as
        FunctionKeyPrincipal and load org context.
        """
        from shared.auth import AuthenticationService, FunctionKeyPrincipal

        # Create request with function key
        req = self.create_mock_request(function_key="test_key_12345")

        with patch('shared.storage.get_organization', return_value=mock_org_entity):
            with patch('shared.storage.get_org_config', return_value=mock_config_entities):
                auth_service = AuthenticationService()
                principal = await auth_service.authenticate(req)

        # Assert function key principal created
        assert isinstance(principal, FunctionKeyPrincipal)
        assert principal.key_id == "test_key_12345"
        assert principal.key_name == "default"  # Default when not in config

    @pytest.mark.asyncio
    async def test_easy_auth_authentication_success(
        self, mock_org_entity, mock_config_entities
    ):
        """
        Test Easy Auth authentication (priority 2)

        When X-MS-CLIENT-PRINCIPAL present (no function key), should
        authenticate as UserPrincipal.
        """
        from shared.auth import AuthenticationService, UserPrincipal

        # Create Easy Auth principal
        easy_auth_data = {
            "userId": "user-789",
            "userDetails": "john.doe@example.com",
            "identityProvider": "aad",
            "userRoles": ["OrgUser"]
        }

        req = self.create_mock_request(easy_auth_principal=easy_auth_data)

        with patch('shared.storage.get_organization', return_value=mock_org_entity):
            with patch('shared.storage.get_org_config', return_value=mock_config_entities):
                auth_service = AuthenticationService()
                principal = await auth_service.authenticate(req)

        # Assert user principal created
        assert isinstance(principal, UserPrincipal)
        assert principal.user_id == "user-789"
        assert principal.email == "john.doe@example.com"
        assert "OrgUser" in principal.roles

    @pytest.mark.asyncio
    async def test_function_key_takes_priority_over_easy_auth(self):
        """
        Test authentication priority: function key > Easy Auth

        When both are present, function key should win.
        """
        from shared.auth import AuthenticationService, FunctionKeyPrincipal

        # Create request with BOTH function key and Easy Auth
        easy_auth_data = {"userId": "user-789", "userDetails": "john@example.com"}
        req = self.create_mock_request(
            function_key="test_key_12345",
            easy_auth_principal=easy_auth_data
        )

        auth_service = AuthenticationService()
        principal = await auth_service.authenticate(req)

        # Assert function key won (priority 1)
        assert isinstance(principal, FunctionKeyPrincipal)
        assert principal.key_id == "test_key_12345"

    @pytest.mark.asyncio
    async def test_authentication_failure_returns_403(self):
        """
        Test authentication failure: no function key, no Easy Auth

        Should raise AuthenticationError (to be converted to 403 by middleware).
        """
        from shared.auth import AuthenticationService, AuthenticationError
        import os

        # Create request with NO authentication
        req = func.HttpRequest(
            method="POST",
            url="http://localhost:7071/api/workflows/test",
            headers={"X-Organization-Id": "test-org-123"},
            body=b'{}'
        )

        auth_service = AuthenticationService()

        # Simulate production environment to trigger auth error
        with patch.dict(os.environ, {'WEBSITE_SITE_NAME': 'production-app'}):
            with pytest.raises(AuthenticationError) as exc_info:
                await auth_service.authenticate(req)

            assert "Authentication required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_function_key_from_query_parameter(self):
        """
        Test function key authentication via query parameter

        Function key can be provided as ?code=KEY (Azure Functions standard).
        """
        from shared.auth import AuthenticationService, FunctionKeyPrincipal

        # Create request with function key in query string
        req = func.HttpRequest(
            method="POST",
            url="http://localhost:7071/api/workflows/test?code=query_key_789",
            headers={"X-Organization-Id": "test-org-123"},
            params={"code": "query_key_789"},  # Azure Functions parses params separately
            body=b'{}'
        )

        auth_service = AuthenticationService()
        principal = await auth_service.authenticate(req)

        # Assert function key principal created from query param
        assert isinstance(principal, FunctionKeyPrincipal)
        assert principal.key_id == "query_key_789"

    @pytest.mark.asyncio
    async def test_function_key_header_takes_priority_over_query(self):
        """
        Test function key priority: header > query parameter

        When both present, header should win.
        """
        from shared.auth import AuthenticationService, FunctionKeyPrincipal

        # Create request with function key in BOTH header and query
        req = func.HttpRequest(
            method="POST",
            url="http://localhost:7071/api/workflows/test?code=query_key",
            headers={
                "X-Organization-Id": "test-org-123",
                "x-functions-key": "header_key"
            },
            params={"code": "query_key"},  # Azure Functions parses params separately
            body=b'{}'
        )

        auth_service = AuthenticationService()
        principal = await auth_service.authenticate(req)

        # Assert header key won
        assert principal.key_id == "header_key"

    @pytest.mark.asyncio
    async def test_org_context_loaded_with_function_key_auth(
        self, mock_org_entity, mock_config_entities
    ):
        """
        Test that OrganizationContext is properly loaded with function key auth

        Even with function key (bypassing user auth), org validation should occur.
        """
        from shared.middleware import load_organization_context
        from shared.context import OrganizationContext

        # Create request with function key
        req = self.create_mock_request(function_key="test_key")

        with patch('shared.storage.get_organization', return_value=mock_org_entity):
            with patch('shared.storage.get_org_config', return_value=mock_config_entities):
                context = await load_organization_context("test-org-123", req)

        # Assert context loaded correctly
        assert isinstance(context, OrganizationContext)
        assert context.org.org_id == "test-org-123"
        assert context.org.name == "Test Organization"
        assert context.has_config("api_endpoint")
        assert context._config["api_endpoint"] == "https://api.example.com"
        assert context._config["features"]["automation"] is True

    @pytest.mark.asyncio
    async def test_invalid_easy_auth_principal_format(self):
        """
        Test handling of malformed X-MS-CLIENT-PRINCIPAL header

        Should raise AuthenticationError if header is not valid Base64 JSON.
        """
        from shared.auth import AuthenticationService, AuthenticationError

        # Create request with invalid Base64
        req = func.HttpRequest(
            method="POST",
            url="http://localhost:7071/api/workflows/test",
            headers={
                "X-Organization-Id": "test-org-123",
                "X-MS-CLIENT-PRINCIPAL": "not-valid-base64!!!"
            },
            body=b'{}'
        )

        auth_service = AuthenticationService()

        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.authenticate(req)

        assert "Failed to decode" in str(exc_info.value) or "No valid authentication" in str(exc_info.value)
