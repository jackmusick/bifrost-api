"""
Unit Tests: Authentication Service (T061)

Tests the AuthenticationService class in isolation:
- Function key extraction (header + query param)
- Easy Auth principal decoding
- Priority order logic
- Principal dataclass creation
- Error handling
- Audit logging triggers
"""

import pytest
import json
import base64
from unittest.mock import Mock, patch, AsyncMock
import azure.functions as func


class TestAuthenticationService:
    """Unit tests for AuthenticationService"""

    @pytest.fixture
    def auth_service(self):
        """Create AuthenticationService instance"""
        from shared.auth import AuthenticationService
        return AuthenticationService()

    def create_request(
        self,
        headers: dict = None,
        params: dict = None,
        url: str = "http://localhost:7071/api/test"
    ) -> func.HttpRequest:
        """Helper to create mock HttpRequest"""
        # Build query string for URL
        if params:
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"{url}?{query_string}"

        return func.HttpRequest(
            method="POST",
            url=url,
            headers=headers or {},
            params=params or {},  # Pass params separately - Azure Functions doesn't parse from URL
            body=b'{}'
        )

    @pytest.mark.asyncio
    async def test_function_key_from_header(self, auth_service):
        """Test function key extraction from x-functions-key header"""
        req = self.create_request(headers={'x-functions-key': 'test_key_123'})

        with patch.object(auth_service, '_audit_function_key_usage', new_callable=AsyncMock):
            principal = await auth_service._authenticate_function_key(req)

        assert principal is not None
        assert principal.key_id == 'test_key_123'
        assert principal.key_name == 'default'

    @pytest.mark.asyncio
    async def test_function_key_from_query_param(self, auth_service):
        """Test function key extraction from code query parameter"""
        req = self.create_request(params={'code': 'query_key_456'})

        with patch.object(auth_service, '_audit_function_key_usage', new_callable=AsyncMock):
            principal = await auth_service._authenticate_function_key(req)

        assert principal is not None
        assert principal.key_id == 'query_key_456'

    @pytest.mark.asyncio
    async def test_function_key_header_priority_over_query(self, auth_service):
        """Test that header takes priority over query parameter"""
        req = self.create_request(
            headers={'x-functions-key': 'header_key'},
            params={'code': 'query_key'}
        )

        with patch.object(auth_service, '_audit_function_key_usage', new_callable=AsyncMock):
            principal = await auth_service._authenticate_function_key(req)

        assert principal.key_id == 'header_key'  # Header wins

    @pytest.mark.asyncio
    async def test_function_key_empty_string_ignored(self, auth_service):
        """Test that empty function key is treated as no key"""
        req = self.create_request(headers={'x-functions-key': ''})

        with patch.object(auth_service, '_audit_function_key_usage', new_callable=AsyncMock):
            principal = await auth_service._authenticate_function_key(req)

        assert principal is None

    @pytest.mark.asyncio
    async def test_function_key_whitespace_ignored(self, auth_service):
        """Test that whitespace-only function key is treated as no key"""
        req = self.create_request(headers={'x-functions-key': '   '})

        with patch.object(auth_service, '_audit_function_key_usage', new_callable=AsyncMock):
            principal = await auth_service._authenticate_function_key(req)

        assert principal is None

    @pytest.mark.asyncio
    async def test_function_key_trimmed(self, auth_service):
        """Test that function key is trimmed of whitespace"""
        req = self.create_request(headers={'x-functions-key': '  key_with_spaces  '})

        with patch.object(auth_service, '_audit_function_key_usage', new_callable=AsyncMock):
            principal = await auth_service._authenticate_function_key(req)

        assert principal.key_id == 'key_with_spaces'  # Trimmed

    @pytest.mark.asyncio
    async def test_function_key_case_insensitive_header(self, auth_service):
        """Test that function key header is case-insensitive"""
        # Test various case combinations
        test_cases = [
            'X-Functions-Key',
            'X-FUNCTIONS-KEY',
            'x-functions-key',
        ]

        for header_name in test_cases:
            req = self.create_request(headers={header_name: 'test_key'})

            with patch.object(auth_service, '_audit_function_key_usage', new_callable=AsyncMock):
                principal = await auth_service._authenticate_function_key(req)

            assert principal is not None, f"Failed for header: {header_name}"

    @pytest.mark.asyncio
    async def test_easy_auth_principal_decoding(self, auth_service):
        """Test Easy Auth principal decoding from Base64 JSON"""
        principal_data = {
            'userId': 'user-123',
            'userDetails': 'test@example.com',
            'identityProvider': 'aad',
            'userRoles': ['OrgUser', 'Admin']
        }

        principal_json = json.dumps(principal_data)
        principal_b64 = base64.b64encode(principal_json.encode()).decode()

        req = self.create_request(headers={'X-MS-CLIENT-PRINCIPAL': principal_b64})

        principal = await auth_service._authenticate_user(req)

        assert principal is not None
        assert principal.user_id == 'user-123'
        assert principal.email == 'test@example.com'
        assert principal.identity_provider == 'aad'
        assert 'OrgUser' in principal.roles
        assert 'Admin' in principal.roles

    @pytest.mark.asyncio
    async def test_easy_auth_missing_header_returns_none(self, auth_service):
        """Test that missing Easy Auth header returns None"""
        req = self.create_request(headers={})

        principal = await auth_service._authenticate_user(req)

        assert principal is None

    @pytest.mark.asyncio
    async def test_easy_auth_invalid_base64_raises_error(self, auth_service):
        """Test that invalid Base64 raises AuthenticationError"""
        from shared.auth import AuthenticationError

        req = self.create_request(headers={'X-MS-CLIENT-PRINCIPAL': 'not-valid-base64!!!'})

        with pytest.raises(AuthenticationError, match="Failed to decode"):
            await auth_service._authenticate_user(req)

    @pytest.mark.asyncio
    async def test_easy_auth_invalid_json_raises_error(self, auth_service):
        """Test that invalid JSON raises AuthenticationError"""
        from shared.auth import AuthenticationError

        # Valid Base64 but invalid JSON
        invalid_json_b64 = base64.b64encode(b"not json data").decode()

        req = self.create_request(headers={'X-MS-CLIENT-PRINCIPAL': invalid_json_b64})

        with pytest.raises(AuthenticationError, match="Failed to decode"):
            await auth_service._authenticate_user(req)

    @pytest.mark.asyncio
    async def test_easy_auth_missing_user_id_raises_error(self, auth_service):
        """Test that missing userId raises AuthenticationError"""
        from shared.auth import AuthenticationError

        # Principal without userId
        principal_data = {
            'userDetails': 'test@example.com',
            'identityProvider': 'aad'
        }
        principal_b64 = base64.b64encode(json.dumps(principal_data).encode()).decode()

        req = self.create_request(headers={'X-MS-CLIENT-PRINCIPAL': principal_b64})

        with pytest.raises(AuthenticationError, match="missing required field: userId"):
            await auth_service._authenticate_user(req)

    @pytest.mark.asyncio
    async def test_easy_auth_extracts_name_from_email(self, auth_service):
        """Test that user name is extracted from email if not provided"""
        principal_data = {
            'userId': 'user-123',
            'userDetails': 'john.doe@example.com',
            'identityProvider': 'aad',
            'userRoles': []
        }
        principal_b64 = base64.b64encode(json.dumps(principal_data).encode()).decode()

        req = self.create_request(headers={'X-MS-CLIENT-PRINCIPAL': principal_b64})

        principal = await auth_service._authenticate_user(req)

        assert principal.name == 'john.doe'  # Extracted from email

    @pytest.mark.asyncio
    async def test_tiered_auth_function_key_priority(self, auth_service):
        """Test that function key has priority over Easy Auth"""
        # Create request with BOTH function key and Easy Auth
        easy_auth_data = {'userId': 'user-123', 'userDetails': 'test@example.com'}
        easy_auth_b64 = base64.b64encode(json.dumps(easy_auth_data).encode()).decode()

        req = self.create_request(
            headers={
                'x-functions-key': 'function_key',
                'X-MS-CLIENT-PRINCIPAL': easy_auth_b64
            }
        )

        with patch.object(auth_service, '_audit_function_key_usage', new_callable=AsyncMock):
            principal = await auth_service.authenticate(req)

        # Should return FunctionKeyPrincipal (not UserPrincipal)
        from shared.auth import FunctionKeyPrincipal
        assert isinstance(principal, FunctionKeyPrincipal)

    @pytest.mark.asyncio
    async def test_tiered_auth_easy_auth_fallback(self, auth_service):
        """Test that Easy Auth is used when function key not present"""
        easy_auth_data = {'userId': 'user-123', 'userDetails': 'test@example.com'}
        easy_auth_b64 = base64.b64encode(json.dumps(easy_auth_data).encode()).decode()

        req = self.create_request(headers={'X-MS-CLIENT-PRINCIPAL': easy_auth_b64})

        principal = await auth_service.authenticate(req)

        # Should return UserPrincipal
        from shared.auth import UserPrincipal
        assert isinstance(principal, UserPrincipal)

    @pytest.mark.asyncio
    async def test_tiered_auth_no_auth_raises_error(self, auth_service):
        """Test that no authentication raises AuthenticationError"""
        from shared.auth import AuthenticationError
        import os

        req = self.create_request(headers={})

        # Simulate production environment (not local dev)
        with patch.dict(os.environ, {'WEBSITE_SITE_NAME': 'production-app'}):
            with pytest.raises(AuthenticationError, match="No valid authentication credentials"):
                await auth_service.authenticate(req)

    @pytest.mark.asyncio
    async def test_audit_function_key_usage_called(self, auth_service):
        """Test that function key usage triggers audit logging"""
        req = self.create_request(headers={'x-functions-key': 'test_key'})

        with patch.object(auth_service, '_audit_function_key_usage', new_callable=AsyncMock) as mock_audit:
            await auth_service._authenticate_function_key(req)

            # Verify audit was called
            mock_audit.assert_called_once()

    def test_function_key_principal_dataclass(self):
        """Test FunctionKeyPrincipal dataclass structure"""
        from shared.auth import FunctionKeyPrincipal

        principal = FunctionKeyPrincipal(key_id='key123', key_name='admin')

        assert principal.key_id == 'key123'
        assert principal.key_name == 'admin'
        assert principal.is_function_key is True
        assert str(principal) == 'FunctionKey(admin)'

    def test_user_principal_dataclass(self):
        """Test UserPrincipal dataclass structure"""
        from shared.auth import UserPrincipal

        principal = UserPrincipal(
            user_id='user-123',
            email='test@example.com',
            name='Test User',
            roles=['OrgUser', 'Admin'],
            identity_provider='aad'
        )

        assert principal.user_id == 'user-123'
        assert principal.email == 'test@example.com'
        assert principal.name == 'Test User'
        assert principal.roles == ['OrgUser', 'Admin']
        assert principal.identity_provider == 'aad'
        assert principal.is_function_key is False
        assert str(principal) == 'User(test@example.com)'

    def test_user_principal_has_role(self):
        """Test UserPrincipal.has_role() method"""
        from shared.auth import UserPrincipal

        principal = UserPrincipal(
            user_id='user-123',
            email='test@example.com',
            roles=['OrgUser', 'Admin']
        )

        assert principal.has_role('OrgUser')
        assert principal.has_role('Admin')
        assert not principal.has_role('PlatformAdmin')

    def test_get_current_principal_with_principal(self):
        """Test get_current_principal() returns principal from request"""
        from shared.auth import get_current_principal, FunctionKeyPrincipal

        req = Mock()
        req.principal = FunctionKeyPrincipal(key_id='key123')

        principal = get_current_principal(req)
        assert principal is not None
        assert principal.key_id == 'key123'

    def test_get_current_principal_no_principal(self):
        """Test get_current_principal() returns None when no principal"""
        from shared.auth import get_current_principal

        req = Mock(spec=[])  # No principal attribute

        principal = get_current_principal(req)
        assert principal is None

    def test_is_function_key_auth(self):
        """Test is_function_key_auth() helper"""
        from shared.auth import is_function_key_auth, FunctionKeyPrincipal

        req = Mock()
        req.principal = FunctionKeyPrincipal(key_id='key123')

        assert is_function_key_auth(req) is True

    def test_is_user_auth(self):
        """Test is_user_auth() helper"""
        from shared.auth import is_user_auth, UserPrincipal

        req = Mock()
        req.principal = UserPrincipal(user_id='user-123', email='test@example.com')

        assert is_user_auth(req) is True

    @pytest.mark.asyncio
    async def test_require_auth_decorator_success(self):
        """Test @require_auth decorator injects principal"""
        from shared.auth import require_auth, FunctionKeyPrincipal

        @require_auth
        async def test_handler(req: func.HttpRequest):
            # Check that principal was injected
            assert hasattr(req, 'principal')
            assert isinstance(req.principal, FunctionKeyPrincipal)
            return func.HttpResponse("Success", status_code=200)

        req = self.create_request(headers={'x-functions-key': 'test_key'})

        with patch('engine.shared.auth.AuthenticationService.authenticate') as mock_auth:
            mock_auth.return_value = FunctionKeyPrincipal(key_id='test_key')

            response = await test_handler(req)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_require_auth_decorator_auth_failure(self):
        """Test @require_auth decorator returns 403 on auth failure"""
        from shared.auth import require_auth, AuthenticationError

        @require_auth
        async def test_handler(req: func.HttpRequest):
            return func.HttpResponse("Success", status_code=200)

        req = self.create_request(headers={})

        with patch('engine.shared.auth.AuthenticationService.authenticate') as mock_auth:
            mock_auth.side_effect = AuthenticationError("No auth")

            response = await test_handler(req)
            assert response.status_code == 403
            assert b"Forbidden" in response.get_body()
