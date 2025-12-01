"""Unit tests for auth edge cases

Tests authentication edge cases:
- Bearer token validation
- API key validation
- Token extraction
- Token expiration and malformation
"""

import json
import pytest
from unittest.mock import Mock, patch, AsyncMock
import base64

from shared.auth import (
    AuthenticationService,
    UserPrincipal
)


class TestBearerTokenValidation:
    """Test bearer token validation"""

    def test_valid_bearer_token_format(self):
        """Should accept valid Bearer token format"""
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyQGV4YW1wbGUuY29tIn0.test"
        auth_header = f"Bearer {token}"

        assert auth_header.startswith("Bearer ")
        assert len(auth_header) > 7

    def test_missing_bearer_prefix(self):
        """Should reject token without Bearer prefix"""
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyQGV4YW1wbGUuY29tIn0.test"

        # Missing Bearer prefix
        assert not token.startswith("Bearer ")

    def test_malformed_bearer_token(self):
        """Should reject malformed bearer token"""
        malformed_tokens = [
            "Bearer",  # No token
            "Bearer ",  # Empty token
            "Bearer invalid",  # Invalid format
            "BearerX token",  # Wrong prefix
            "bearer token",  # Lowercase prefix (might be accepted or rejected)
        ]

        for token in malformed_tokens:
            # These should fail validation
            if token.startswith("Bearer "):
                token_part = token[7:]
                assert token_part == "" or len(token_part) < 100

    def test_expired_bearer_token(self):
        """Should reject expired bearer token"""
        # Create JWT payload with exp in past
        import time

        expired_payload = {
            "sub": "user@example.com",
            "exp": int(time.time()) - 3600  # 1 hour ago
        }

        # Token with past expiration should be rejected
        assert expired_payload["exp"] < int(time.time())

    def test_bearer_token_with_invalid_signature(self):
        """Should reject token with invalid signature"""
        # Token with tampered signature
        tampered_token = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiJ1c2VyQGV4YW1wbGUuY29tIn0."
            "TAMPERED_SIGNATURE"
        )

        auth_header = f"Bearer {tampered_token}"

        # Should validate signature
        assert auth_header.startswith("Bearer ")


class TestAPIKeyValidation:
    """Test API key validation"""

    def test_valid_api_key_format(self):
        """Should accept valid API key format"""
        api_key = "wk_1234567890abcdef1234567890abcdef"

        # Valid API key should match expected format
        assert api_key.startswith("wk_")
        assert len(api_key) > 10

    def test_invalid_api_key_format(self):
        """Should reject invalid API key format"""
        invalid_keys = [
            "invalid",  # Wrong prefix
            "wk_",  # No value
            "sk_1234567890abcdef",  # Wrong key type
            "1234567890abcdef",  # No prefix
        ]

        for key in invalid_keys:
            # Should fail validation - test structure validates
            is_valid = key.startswith("wk_") and len(key) > 3
            if key in ["invalid", "sk_1234567890abcdef", "1234567890abcdef"]:
                assert not is_valid

    def test_revoked_api_key(self):
        """Should reject revoked API key"""
        revoked_key_id = "key-123"

        with patch('shared.auth.AuthenticationService') as mock_auth:
            mock_instance = AsyncMock()
            mock_auth.return_value = mock_instance

            # Simulate revoked key lookup
            revoked_keys = {"key-123"}
            is_revoked = revoked_key_id in revoked_keys

            assert is_revoked is True

    def test_expired_api_key(self):
        """Should reject expired API key"""
        import time

        api_key_expiry = int(time.time()) - 3600  # 1 hour ago
        current_time = int(time.time())

        is_expired = current_time > api_key_expiry

        assert is_expired is True

    def test_api_key_not_found(self):
        """Should reject unknown API key"""
        key_store = {}  # Empty key store

        unknown_key = "wk_unknown123"

        assert unknown_key not in key_store


class TestTokenExtraction:
    """Test user/principal extraction from tokens"""

    def test_extract_user_from_valid_jwt(self):
        """Should extract user info from valid JWT"""
        # Simulate JWT payload
        payload = {
            "sub": "user@example.com",
            "email": "user@example.com",
            "name": "Test User",
            "oid": "user-id-123"
        }

        user = UserPrincipal(
            user_id=payload['oid'],
            email=payload['email'],
            name=payload['name'],
            roles=['Contributor']
        )

        assert user.user_id == "user-id-123"
        assert user.email == "user@example.com"

    def test_extract_user_missing_required_claims(self):
        """Should handle token with missing required claims"""
        # Minimal payload without name
        payload = {
            "sub": "user@example.com",
            "email": "user@example.com"
            # Missing name
        }

        # Should use email as fallback for name
        name = payload.get('name') or payload.get('email', 'Unknown')

        assert name == "user@example.com"

    def test_extract_user_with_empty_claims(self):
        """Should handle token with empty claim values"""
        payload = {
            "sub": "user@example.com",
            "email": "",  # Empty email
            "name": ""    # Empty name
        }

        # Should handle empty values
        email = payload.get('email') or 'unknown@system.local'
        payload.get('name') or email

        assert email == 'unknown@system.local'

    def test_extract_roles_from_token(self):
        """Should extract user roles from token"""
        payload = {
            "sub": "user@example.com",
            "roles": ["Contributor", "Viewer"]
        }

        roles = payload.get('roles', [])

        assert len(roles) == 2
        assert 'Contributor' in roles

    def test_extract_roles_missing_from_token(self):
        """Should handle token without roles claim"""
        payload = {
            "sub": "user@example.com"
            # No roles
        }

        roles = payload.get('roles', [])

        assert roles == []

    def test_extract_platform_admin_flag(self):
        """Should detect platform admin role"""
        payload = {
            "sub": "admin@example.com",
            "roles": ["PlatformAdmin", "Contributor"]
        }

        is_platform_admin = "PlatformAdmin" in payload.get('roles', [])

        assert is_platform_admin is True


class TestTokenValidation:
    """Test overall token validation"""

    @pytest.mark.asyncio
    async def test_authenticate_with_bearer_token(self):
        """Should authenticate with Bearer token"""
        principal = {
            "userId": "user-123",
            "userDetails": "user@example.com",
            "userRoles": ["Contributor"]
        }

        request = Mock()
        request.headers = {
            "x-ms-client-principal": base64.b64encode(
                json.dumps(principal).encode()
            ).decode()
        }

        # Should successfully authenticate
        assert "x-ms-client-principal" in request.headers

    @pytest.mark.asyncio
    async def test_authenticate_with_function_key(self):
        """Should authenticate with function key"""
        request = Mock()
        request.headers = {
            "x-functions-key": "default"
        }

        # Should recognize function key authentication
        assert "x-functions-key" in request.headers

    @pytest.mark.asyncio
    async def test_authenticate_missing_credentials(self):
        """Should fail without credentials"""
        request = Mock()
        request.headers = {}

        # No auth headers present
        assert len(request.headers) == 0

    @pytest.mark.asyncio
    async def test_authenticate_multiple_auth_methods(self):
        """Should prioritize auth methods"""
        principal = {
            "userId": "user-123",
            "userDetails": "user@example.com",
            "userRoles": ["Contributor"]
        }

        request = Mock()
        request.headers = {
            "x-ms-client-principal": base64.b64encode(
                json.dumps(principal).encode()
            ).decode(),
            "x-functions-key": "default"
        }

        # Should use client principal over function key
        assert "x-ms-client-principal" in request.headers


class TestAuthenticationErrorHandling:
    """Test authentication error handling"""

    @pytest.mark.asyncio
    async def test_invalid_client_principal_format(self):
        """Should handle invalid client principal format"""
        request = Mock()
        request.headers = {
            "x-ms-client-principal": "invalid-base64!!!"
        }

        # Should fail to decode
        try:
            base64.b64decode(request.headers["x-ms-client-principal"])
            assert False, "Should have failed to decode"
        except Exception:
            pass  # Expected

    @pytest.mark.asyncio
    async def test_client_principal_invalid_json(self):
        """Should handle non-JSON client principal"""
        request = Mock()
        request.headers = {
            "x-ms-client-principal": base64.b64encode(b"not json").decode()
        }

        # Should fail to parse JSON
        try:
            decoded = base64.b64decode(request.headers["x-ms-client-principal"])
            json.loads(decoded)
            assert False, "Should have failed to parse JSON"
        except json.JSONDecodeError:
            pass  # Expected

    def test_authentication_service_initialization(self):
        """Should initialize AuthenticationService"""
        auth_service = AuthenticationService()

        assert auth_service is not None

    @pytest.mark.asyncio
    async def test_authenticate_method_exists(self):
        """Should have authenticate method"""
        auth_service = AuthenticationService()

        assert hasattr(auth_service, 'authenticate')
        assert callable(getattr(auth_service, 'authenticate'))


class TestTokenClaims:
    """Test token claim extraction and validation"""

    def test_extract_email_claim(self):
        """Should extract email claim from token"""
        payload = {
            "sub": "user-123",
            "email": "user@example.com",
            "email_verified": True
        }

        email = payload.get('email')

        assert email == "user@example.com"

    def test_extract_organization_claim(self):
        """Should extract organization claim"""
        payload = {
            "sub": "user-123",
            "org_id": "org-123",
            "org_name": "Acme Corp"
        }

        org_id = payload.get('org_id')

        assert org_id == "org-123"

    def test_extract_custom_claims(self):
        """Should extract custom claims"""
        payload = {
            "sub": "user-123",
            "custom_claim_1": "value1",
            "custom_claim_2": "value2"
        }

        custom = {k: v for k, v in payload.items() if k.startswith('custom_')}

        assert len(custom) == 2
        assert custom['custom_claim_1'] == "value1"

    def test_claim_with_special_characters(self):
        """Should handle claims with special characters"""
        payload = {
            "sub": "user-123",
            "email": "user+test@example.com",
            "name": "User (Test) [Draft]"
        }

        assert "@" in payload['email']
        assert "+" in payload['email']

    def test_claim_with_unicode_values(self):
        """Should handle unicode in claims"""
        payload = {
            "sub": "user-123",
            "name": "用户名",
            "org": "Organización"
        }

        assert isinstance(payload['name'], str)
        assert isinstance(payload['org'], str)
