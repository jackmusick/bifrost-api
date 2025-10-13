"""
Integration Tests for OAuth Credentials Access (User Story 3)
Tests credential retrieval for workflow consumption
"""

import pytest
import pytest_asyncio
import json
from datetime import datetime, timedelta
from shared.storage import TableStorageService
from services.oauth_storage_service import OAuthStorageService
from models.oauth_connection import CreateOAuthConnectionRequest


@pytest.fixture
def oauth_service():
    """Get OAuth storage service"""
    return OAuthStorageService()


@pytest.fixture
def config_service():
    """Get Config table service"""
    return TableStorageService("Config")


@pytest_asyncio.fixture
async def sample_oauth_connection(oauth_service, config_service):
    """Create a sample OAuth connection with tokens"""
    # Create connection
    request = CreateOAuthConnectionRequest(
        connection_name="test_oauth_cred",
        oauth_flow_type="authorization_code",
        client_id="test_client_123",
        client_secret="test_secret_456",
        authorization_url="https://oauth.provider.com/authorize",
        token_url="https://oauth.provider.com/token",
        scopes="read,write"
    )

    connection = await oauth_service.create_connection(
        org_id="test-org-credentials",
        request=request,
        created_by="test@example.com"
    )

    # Store OAuth tokens
    expires_at = datetime.utcnow() + timedelta(hours=1)
    await oauth_service.store_tokens(
        org_id="test-org-credentials",
        connection_name="test_oauth_cred",
        access_token="test_access_token_abc123",
        refresh_token="test_refresh_token_xyz789",
        expires_at=expires_at,
        token_type="Bearer",
        updated_by="system"
    )

    yield connection

    # Cleanup
    await oauth_service.delete_connection("test-org-credentials", "test_oauth_cred")


@pytest_asyncio.fixture
async def sample_global_oauth_connection(oauth_service, config_service):
    """Create a sample GLOBAL OAuth connection"""
    request = CreateOAuthConnectionRequest(
        connection_name="global_oauth_cred",
        oauth_flow_type="client_credentials",
        client_id="global_client_789",
        client_secret="global_secret_012",
        authorization_url="https://global.oauth.com/authorize",
        token_url="https://global.oauth.com/token",
        scopes="api.access"
    )

    connection = await oauth_service.create_connection(
        org_id="GLOBAL",
        request=request,
        created_by="admin@example.com"
    )

    # Store tokens
    expires_at = datetime.utcnow() + timedelta(hours=2)
    await oauth_service.store_tokens(
        org_id="GLOBAL",
        connection_name="global_oauth_cred",
        access_token="global_access_token_def456",
        refresh_token="global_refresh_token_uvw345",
        expires_at=expires_at,
        token_type="Bearer",
        updated_by="system"
    )

    yield connection

    # Cleanup
    await oauth_service.delete_connection("GLOBAL", "global_oauth_cred")


class TestOAuthCredentialRetrieval:
    """Test OAuth credential retrieval for workflows"""

    @pytest.mark.asyncio
    async def test_get_credentials_for_org_connection(self, oauth_service, config_service, sample_oauth_connection):
        """Should retrieve credentials for org-specific connection"""
        # Get the connection
        connection = await oauth_service.get_connection(
            org_id="test-org-credentials",
            connection_name="test_oauth_cred"
        )

        assert connection is not None
        assert connection.connection_name == "test_oauth_cred"
        assert connection.status == "completed"
        assert connection.expires_at is not None

        # Get the OAuth response from Config table
        oauth_response_key = f"config:oauth_{connection.connection_name}_oauth_response"
        oauth_response_config = config_service.get_entity(
            "test-org-credentials",
            oauth_response_key
        )

        assert oauth_response_config is not None
        assert oauth_response_config["Type"] == "secret_ref"
        assert oauth_response_config["Value"] == "test-org-credentials--oauth-test_oauth_cred-response"

    @pytest.mark.asyncio
    async def test_get_credentials_with_org_fallback_to_global(self, oauth_service, sample_global_oauth_connection):
        """Should fallback to GLOBAL connection when org-specific not found"""
        # Try to get connection from org that doesn't have it
        connection = await oauth_service.get_connection(
            org_id="different-org-123",
            connection_name="global_oauth_cred"
        )

        assert connection is not None
        assert connection.connection_name == "global_oauth_cred"
        assert connection.org_id == "GLOBAL"
        assert connection.status == "completed"

    @pytest.mark.asyncio
    async def test_get_credentials_not_found(self, oauth_service):
        """Should return None when connection doesn't exist"""
        connection = await oauth_service.get_connection(
            org_id="test-org-credentials",
            connection_name="nonexistent_connection"
        )

        assert connection is None

    @pytest.mark.asyncio
    async def test_get_credentials_not_connected_status(self, oauth_service):
        """Should handle connections that haven't completed OAuth flow"""
        # Create connection without completing OAuth flow
        request = CreateOAuthConnectionRequest(
            connection_name="pending_oauth_cred",
            oauth_flow_type="authorization_code",
            client_id="pending_client",
            client_secret="pending_secret",
            authorization_url="https://pending.oauth.com/authorize",
            token_url="https://pending.oauth.com/token",
            scopes="read"
        )

        connection = await oauth_service.create_connection(
            org_id="test-org-credentials",
            request=request,
            created_by="test@example.com"
        )

        assert connection.status == "not_connected"
        assert connection.expires_at is None

        # Cleanup
        await oauth_service.delete_connection("test-org-credentials", "pending_oauth_cred")

    @pytest.mark.asyncio
    async def test_credentials_expiration_check(self, oauth_service, sample_oauth_connection):
        """Should check if credentials are expired"""
        connection = await oauth_service.get_connection(
            org_id="test-org-credentials",
            connection_name="test_oauth_cred"
        )

        assert connection is not None
        assert not connection.is_expired()  # Should not be expired (1 hour TTL)
        assert not connection.expires_soon(hours=4)  # Should not expire within 4 hours

    @pytest.mark.asyncio
    async def test_credentials_expires_soon_check(self, oauth_service):
        """Should detect when credentials expire soon"""
        # Create connection with short-lived token
        request = CreateOAuthConnectionRequest(
            connection_name="short_lived_cred",
            oauth_flow_type="authorization_code",
            client_id="short_client",
            client_secret="short_secret",
            authorization_url="https://short.oauth.com/authorize",
            token_url="https://short.oauth.com/token",
            scopes="read"
        )

        connection = await oauth_service.create_connection(
            org_id="test-org-credentials",
            request=request,
            created_by="test@example.com"
        )

        # Store tokens expiring in 2 hours
        expires_at = datetime.utcnow() + timedelta(hours=2)
        await oauth_service.store_tokens(
            org_id="test-org-credentials",
            connection_name="short_lived_cred",
            access_token="short_access_token",
            refresh_token="short_refresh_token",
            expires_at=expires_at,
            token_type="Bearer",
            updated_by="system"
        )

        connection = await oauth_service.get_connection(
            org_id="test-org-credentials",
            connection_name="short_lived_cred"
        )

        assert connection.expires_soon(hours=4)  # Should expire within 4 hours
        assert not connection.is_expired()  # But not yet expired

        # Cleanup
        await oauth_service.delete_connection("test-org-credentials", "short_lived_cred")


class TestOAuthCredentialSecurity:
    """Test security aspects of credential retrieval"""

    @pytest.mark.asyncio
    async def test_client_secret_stored_as_secret_ref(self, oauth_service, config_service, sample_oauth_connection):
        """Client secret should be stored as secret_ref in Config table"""
        client_secret_key = f"config:oauth_{sample_oauth_connection.connection_name}_client_secret"
        client_secret_config = config_service.get_entity(
            "test-org-credentials",
            client_secret_key
        )

        assert client_secret_config is not None
        assert client_secret_config["Type"] == "secret_ref"
        # Value should be Key Vault secret name, not actual secret
        assert client_secret_config["Value"].startswith("test-org-credentials--oauth-")
        assert "test_secret_456" not in client_secret_config["Value"]

    @pytest.mark.asyncio
    async def test_oauth_tokens_stored_as_secret_ref(self, oauth_service, config_service, sample_oauth_connection):
        """OAuth tokens should be stored as secret_ref in Config table"""
        oauth_response_key = f"config:oauth_{sample_oauth_connection.connection_name}_oauth_response"
        oauth_response_config = config_service.get_entity(
            "test-org-credentials",
            oauth_response_key
        )

        assert oauth_response_config is not None
        assert oauth_response_config["Type"] == "secret_ref"
        # Value should be Key Vault secret name, not actual tokens
        assert oauth_response_config["Value"].startswith("test-org-credentials--oauth-")
        assert "test_access_token" not in oauth_response_config["Value"]

    @pytest.mark.asyncio
    async def test_metadata_stored_as_json(self, oauth_service, config_service, sample_oauth_connection):
        """Metadata should be stored as json in Config table"""
        metadata_key = f"config:oauth_{sample_oauth_connection.connection_name}_metadata"
        metadata_config = config_service.get_entity(
            "test-org-credentials",
            metadata_key
        )

        assert metadata_config is not None
        assert metadata_config["Type"] == "json"

        # Parse and verify metadata
        metadata = json.loads(metadata_config["Value"])
        assert metadata["client_id"] == "test_client_123"
        assert metadata["scopes"] == "read,write"
        assert "client_secret" not in metadata  # Secret should NOT be in metadata


class TestOAuthWorkflowIntegration:
    """Test OAuth integration patterns for workflows"""

    @pytest.mark.asyncio
    async def test_workflow_retrieves_active_connection(self, oauth_service, sample_oauth_connection):
        """Simulate workflow retrieving OAuth credentials"""
        # This is how a workflow would get credentials
        connection = await oauth_service.get_connection(
            org_id="test-org-credentials",
            connection_name="test_oauth_cred"
        )

        assert connection is not None
        assert connection.status == "completed"

        # Workflow would then use the oauth_response_ref to get actual tokens from Key Vault
        assert connection.oauth_response_ref == "oauth_test_oauth_cred_oauth_response"
        assert connection.client_secret_ref == "oauth_test_oauth_cred_client_secret"

    @pytest.mark.asyncio
    async def test_workflow_checks_expiration_before_use(self, oauth_service, sample_oauth_connection):
        """Workflow should check if credentials are expired before using"""
        connection = await oauth_service.get_connection(
            org_id="test-org-credentials",
            connection_name="test_oauth_cred"
        )

        assert connection is not None

        # Workflow checks expiration
        if connection.is_expired():
            # Would trigger refresh flow
            assert False, "Credentials should not be expired"

        if connection.expires_soon(hours=4):
            # Could proactively refresh
            pass  # This is expected for testing

        # Use credentials
        assert connection.status == "completed"

    @pytest.mark.asyncio
    async def test_workflow_handles_not_connected_gracefully(self, oauth_service):
        """Workflow should handle connections that haven't been authorized"""
        # Create connection without OAuth flow
        request = CreateOAuthConnectionRequest(
            connection_name="unauthorized_cred",
            oauth_flow_type="authorization_code",
            client_id="unauth_client",
            client_secret="unauth_secret",
            authorization_url="https://unauth.oauth.com/authorize",
            token_url="https://unauth.oauth.com/token"
        )

        connection = await oauth_service.create_connection(
            org_id="test-org-credentials",
            request=request,
            created_by="test@example.com"
        )

        # Workflow retrieves it
        retrieved = await oauth_service.get_connection(
            org_id="test-org-credentials",
            connection_name="unauthorized_cred"
        )

        # Should gracefully handle not_connected status
        assert retrieved.status == "not_connected"
        # Workflow would return error to user

        # Cleanup
        await oauth_service.delete_connection("test-org-credentials", "unauthorized_cred")
