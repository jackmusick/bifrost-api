"""
Contract Test: Tiered Authentication (T041)

Tests the authentication priority order contract:
1. Function key (x-functions-key header OR code query param) - HIGHEST PRIORITY
2. Easy Auth (X-MS-CLIENT-PRINCIPAL header) - FALLBACK
3. None → 403 Forbidden

Verifies the authentication service implements correct priority logic.
"""

import pytest
import json
import base64
from unittest.mock import Mock, patch
import azure.functions as func


class TestTieredAuthenticationContract:
    """Contract tests for authentication priority order"""

    def create_request_with_auth(
        self,
        function_key_header: str = None,
        function_key_query: str = None,
        easy_auth_principal: dict = None
    ) -> func.HttpRequest:
        """Helper to create request with various auth combinations"""
        headers = {}
        url = "http://localhost:7071/api/test"

        # Add function key header
        if function_key_header:
            headers["x-functions-key"] = function_key_header

        # Add function key to query string
        if function_key_query:
            url = f"{url}?code={function_key_query}"

        # Add Easy Auth principal
        if easy_auth_principal:
            principal_json = json.dumps(easy_auth_principal)
            principal_b64 = base64.b64encode(principal_json.encode()).decode()
            headers["X-MS-CLIENT-PRINCIPAL"] = principal_b64

        return func.HttpRequest(
            method="POST",
            url=url,
            headers=headers,
            body=b'{}'
        )

    @pytest.mark.asyncio
    async def test_contract_priority_1_function_key_header(self):
        """
        CONTRACT: Function key in header = Priority 1 (highest)

        When x-functions-key header present, must authenticate as function key
        regardless of other auth methods present.
        """
        from engine.shared.auth import AuthenticationService, FunctionKeyPrincipal

        # Create request with function key header (+ Easy Auth to test priority)
        req = self.create_request_with_auth(
            function_key_header="key123",
            easy_auth_principal={"userId": "user1"}
        )

        auth_service = AuthenticationService()
        principal = await auth_service.authenticate(req)

        # CONTRACT: Must return FunctionKeyPrincipal
        assert isinstance(principal, FunctionKeyPrincipal)
        assert principal.key_id == "key123"

    @pytest.mark.asyncio
    async def test_contract_priority_2_function_key_query(self):
        """
        CONTRACT: Function key in query param = Priority 2

        When code query param present (no header), must authenticate as function key.
        Query param should have lower priority than header.
        """
        from engine.shared.auth import AuthenticationService, FunctionKeyPrincipal

        # Create request with function key in query only
        req = self.create_request_with_auth(function_key_query="query_key")

        auth_service = AuthenticationService()
        principal = await auth_service.authenticate(req)

        # CONTRACT: Must return FunctionKeyPrincipal
        assert isinstance(principal, FunctionKeyPrincipal)
        assert principal.key_id == "query_key"

    @pytest.mark.asyncio
    async def test_contract_priority_3_easy_auth(self):
        """
        CONTRACT: Easy Auth = Priority 3 (fallback)

        When X-MS-CLIENT-PRINCIPAL present (no function key), must authenticate
        as user principal.
        """
        from engine.shared.auth import AuthenticationService, UserPrincipal

        # Create request with Easy Auth only
        easy_auth = {
            "userId": "user123",
            "userDetails": "test@example.com",
            "identityProvider": "aad",
            "userRoles": ["OrgUser"]
        }
        req = self.create_request_with_auth(easy_auth_principal=easy_auth)

        auth_service = AuthenticationService()
        principal = await auth_service.authenticate(req)

        # CONTRACT: Must return UserPrincipal
        assert isinstance(principal, UserPrincipal)
        assert principal.user_id == "user123"
        assert principal.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_contract_no_auth_raises_error(self):
        """
        CONTRACT: No authentication = AuthenticationError

        When neither function key nor Easy Auth present, must raise
        AuthenticationError (to be converted to 403 by middleware).
        """
        from engine.shared.auth import AuthenticationService, AuthenticationError

        # Create request with NO authentication
        req = self.create_request_with_auth()

        auth_service = AuthenticationService()

        # CONTRACT: Must raise AuthenticationError
        with pytest.raises(AuthenticationError):
            await auth_service.authenticate(req)

    @pytest.mark.asyncio
    async def test_contract_function_key_header_beats_query(self):
        """
        CONTRACT: Function key header > query param

        When both header and query param present, header must win.
        """
        from engine.shared.auth import AuthenticationService, FunctionKeyPrincipal

        # Create request with BOTH header and query
        req = self.create_request_with_auth(
            function_key_header="header_key",
            function_key_query="query_key"
        )

        auth_service = AuthenticationService()
        principal = await auth_service.authenticate(req)

        # CONTRACT: Must use header key (not query key)
        assert isinstance(principal, FunctionKeyPrincipal)
        assert principal.key_id == "header_key"
        assert principal.key_id != "query_key"

    @pytest.mark.asyncio
    async def test_contract_function_key_beats_easy_auth(self):
        """
        CONTRACT: Function key > Easy Auth

        When both present, function key must take priority.
        """
        from engine.shared.auth import AuthenticationService, FunctionKeyPrincipal

        # Create request with BOTH function key and Easy Auth
        req = self.create_request_with_auth(
            function_key_header="key123",
            easy_auth_principal={"userId": "user123"}
        )

        auth_service = AuthenticationService()
        principal = await auth_service.authenticate(req)

        # CONTRACT: Must use function key (not Easy Auth)
        assert isinstance(principal, FunctionKeyPrincipal)
        assert principal.key_id == "key123"

    @pytest.mark.asyncio
    async def test_contract_function_key_principal_structure(self):
        """
        CONTRACT: FunctionKeyPrincipal must have specific structure

        FunctionKeyPrincipal must expose:
        - key_id: str (the function key value)
        - key_name: str (friendly name, default "default")
        - is_function_key: bool = True
        """
        from engine.shared.auth import AuthenticationService, FunctionKeyPrincipal

        req = self.create_request_with_auth(function_key_header="test_key")

        auth_service = AuthenticationService()
        principal = await auth_service.authenticate(req)

        # CONTRACT: Required attributes
        assert hasattr(principal, 'key_id')
        assert hasattr(principal, 'key_name')
        assert hasattr(principal, 'is_function_key')

        # CONTRACT: Correct types and values
        assert isinstance(principal.key_id, str)
        assert isinstance(principal.key_name, str)
        assert principal.is_function_key is True

    @pytest.mark.asyncio
    async def test_contract_user_principal_structure(self):
        """
        CONTRACT: UserPrincipal must have specific structure

        UserPrincipal must expose:
        - user_id: str
        - email: str
        - name: str (optional, from userDetails)
        - roles: List[str]
        - identity_provider: str
        - is_function_key: bool = False
        """
        from engine.shared.auth import AuthenticationService, UserPrincipal

        easy_auth = {
            "userId": "user123",
            "userDetails": "john@example.com",
            "identityProvider": "aad",
            "userRoles": ["OrgUser", "Admin"]
        }
        req = self.create_request_with_auth(easy_auth_principal=easy_auth)

        auth_service = AuthenticationService()
        principal = await auth_service.authenticate(req)

        # CONTRACT: Required attributes
        assert hasattr(principal, 'user_id')
        assert hasattr(principal, 'email')
        assert hasattr(principal, 'roles')
        assert hasattr(principal, 'identity_provider')
        assert hasattr(principal, 'is_function_key')

        # CONTRACT: Correct types and values
        assert isinstance(principal.user_id, str)
        assert isinstance(principal.email, str)
        assert isinstance(principal.roles, list)
        assert isinstance(principal.identity_provider, str)
        assert principal.is_function_key is False

        # CONTRACT: Correct data
        assert principal.user_id == "user123"
        assert principal.email == "john@example.com"
        assert "OrgUser" in principal.roles
        assert "Admin" in principal.roles

    @pytest.mark.asyncio
    async def test_contract_authentication_error_structure(self):
        """
        CONTRACT: AuthenticationError must be specific exception type

        Authentication failures must raise AuthenticationError (not generic Exception).
        """
        from engine.shared.auth import AuthenticationService, AuthenticationError

        req = self.create_request_with_auth()  # No auth

        auth_service = AuthenticationService()

        # CONTRACT: Must raise specific AuthenticationError type
        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.authenticate(req)

        # CONTRACT: Error message must be informative
        error_msg = str(exc_info.value)
        assert len(error_msg) > 0
        assert "authentication" in error_msg.lower() or "credentials" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_contract_empty_function_key_ignored(self):
        """
        CONTRACT: Empty function key should be treated as no auth

        Empty string function keys should fall through to next auth method.
        """
        from engine.shared.auth import AuthenticationService, UserPrincipal

        # Create request with empty function key but valid Easy Auth
        req = self.create_request_with_auth(
            function_key_header="",  # Empty
            easy_auth_principal={"userId": "user123", "userDetails": "test@example.com"}
        )

        auth_service = AuthenticationService()
        principal = await auth_service.authenticate(req)

        # CONTRACT: Should fall through to Easy Auth (not treat empty key as valid)
        assert isinstance(principal, UserPrincipal)

    @pytest.mark.asyncio
    async def test_contract_whitespace_function_key_ignored(self):
        """
        CONTRACT: Whitespace-only function key should be treated as no auth

        Keys that are only whitespace should fall through to next auth method.
        """
        from engine.shared.auth import AuthenticationService, UserPrincipal

        # Create request with whitespace function key but valid Easy Auth
        req = self.create_request_with_auth(
            function_key_header="   ",  # Whitespace
            easy_auth_principal={"userId": "user123", "userDetails": "test@example.com"}
        )

        auth_service = AuthenticationService()
        principal = await auth_service.authenticate(req)

        # CONTRACT: Should fall through to Easy Auth
        assert isinstance(principal, UserPrincipal)

    @pytest.mark.asyncio
    async def test_contract_case_insensitive_header_names(self):
        """
        CONTRACT: Header names should be case-insensitive

        HTTP headers are case-insensitive by spec. Auth should work with
        X-Functions-Key, x-functions-key, X-FUNCTIONS-KEY, etc.
        """
        from engine.shared.auth import AuthenticationService, FunctionKeyPrincipal

        # Azure Functions normalizes headers to lowercase, but test both
        req1 = func.HttpRequest(
            method="POST",
            url="http://localhost:7071/api/test",
            headers={"X-Functions-Key": "key123"},  # Title case
            body=b'{}'
        )

        req2 = func.HttpRequest(
            method="POST",
            url="http://localhost:7071/api/test",
            headers={"X-FUNCTIONS-KEY": "key456"},  # Upper case
            body=b'{}'
        )

        auth_service = AuthenticationService()

        # CONTRACT: Both should work
        principal1 = await auth_service.authenticate(req1)
        principal2 = await auth_service.authenticate(req2)

        assert isinstance(principal1, FunctionKeyPrincipal)
        assert isinstance(principal2, FunctionKeyPrincipal)
