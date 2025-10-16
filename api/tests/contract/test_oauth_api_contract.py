"""
Contract tests for OAuth API models
Tests Pydantic validation rules for OAuth connection request/response models
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

# Import OAuth models for testing
from models.oauth_connection import (
    CreateOAuthConnectionRequest,
    OAuthConnection,
    OAuthConnectionDetail,
    OAuthConnectionSummary,
)


class TestCreateOAuthConnectionRequest:
    """Test validation for CreateOAuthConnectionRequest model - T014"""

    def test_valid_authorization_code_flow(self):
        """Test valid request for authorization code flow"""
        request = CreateOAuthConnectionRequest(
            connection_name="azure_csp_oauth",
            oauth_flow_type="authorization_code",
            client_id="abc123",
            client_secret="secret456",
            authorization_url="https://login.microsoftonline.com/oauth2/v2.0/authorize",
            token_url="https://login.microsoftonline.com/oauth2/v2.0/token",
            scopes="https://graph.microsoft.com/.default"
        )

        assert request.connection_name == "azure_csp_oauth"
        assert request.oauth_flow_type == "authorization_code"
        assert request.client_id == "abc123"
        assert request.client_secret == "secret456"
        assert request.scopes == "https://graph.microsoft.com/.default"

    def test_valid_client_credentials_flow(self):
        """Test valid request for client credentials flow"""
        request = CreateOAuthConnectionRequest(
            connection_name="service_api",
            oauth_flow_type="client_credentials",
            client_id="service123",
            client_secret="secret789",
            authorization_url="https://auth.example.com/authorize",
            token_url="https://auth.example.com/token",
            scopes="api.read,api.write"
        )

        assert request.oauth_flow_type == "client_credentials"

    def test_invalid_connection_name_with_spaces(self):
        """Test that connection names with spaces are rejected"""

        with pytest.raises(ValidationError) as exc_info:
            CreateOAuthConnectionRequest(
                connection_name="invalid name",
                oauth_flow_type="authorization_code",
                client_id="abc123",
                client_secret="secret",
                authorization_url="https://auth.com/authorize",
                token_url="https://auth.com/token"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("connection_name",) for e in errors)

    def test_invalid_connection_name_with_special_chars(self):
        """Test that connection names with special characters are rejected"""

        with pytest.raises(ValidationError) as exc_info:
            CreateOAuthConnectionRequest(
                connection_name="invalid@name!",
                oauth_flow_type="authorization_code",
                client_id="abc123",
                client_secret="secret",
                authorization_url="https://auth.com/authorize",
                token_url="https://auth.com/token"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("connection_name",) for e in errors)

    def test_valid_connection_name_with_underscores_hyphens(self):
        """Test that connection names with underscores and hyphens are allowed"""

        request = CreateOAuthConnectionRequest(
            connection_name="valid_connection-name_123",
            oauth_flow_type="authorization_code",
            client_id="abc123",
            client_secret="secret",
            authorization_url="https://auth.com/authorize",
            token_url="https://auth.com/token"
        )

        assert request.connection_name == "valid_connection-name_123"

    def test_invalid_oauth_flow_type(self):
        """Test that invalid OAuth flow types are rejected"""

        with pytest.raises(ValidationError) as exc_info:
            CreateOAuthConnectionRequest(
                connection_name="test_connection",
                oauth_flow_type="invalid_flow",
                client_id="abc123",
                client_secret="secret",
                authorization_url="https://auth.com/authorize",
                token_url="https://auth.com/token"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("oauth_flow_type",) for e in errors)

    def test_authorization_url_must_be_https(self):
        """Test that authorization URL must use HTTPS"""

        with pytest.raises(ValidationError) as exc_info:
            CreateOAuthConnectionRequest(
                connection_name="test_connection",
                oauth_flow_type="authorization_code",
                client_id="abc123",
                client_secret="secret",
                authorization_url="http://insecure.com/authorize",  # HTTP not allowed
                token_url="https://auth.com/token"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("authorization_url",) for e in errors)

    def test_token_url_must_be_https(self):
        """Test that token URL must use HTTPS"""

        with pytest.raises(ValidationError) as exc_info:
            CreateOAuthConnectionRequest(
                connection_name="test_connection",
                oauth_flow_type="authorization_code",
                client_id="abc123",
                client_secret="secret",
                authorization_url="https://auth.com/authorize",
                token_url="http://insecure.com/token"  # HTTP not allowed
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("token_url",) for e in errors)

    def test_missing_required_fields(self):
        """Test that all required fields must be present"""

        with pytest.raises(ValidationError) as exc_info:
            CreateOAuthConnectionRequest(
                connection_name="test"
                # Missing: oauth_flow_type, client_id, client_secret, URLs
            )

        errors = exc_info.value.errors()
        required_fields = {"oauth_flow_type", "client_id",
                          "authorization_url", "token_url"}
        missing_fields = {e["loc"][0] for e in errors if e["type"] == "missing"}
        assert required_fields.issubset(missing_fields)
        # client_secret is optional (for PKCE flow)

    def test_scopes_optional_defaults_to_empty(self):
        """Test that scopes field is optional and defaults to empty string"""

        request = CreateOAuthConnectionRequest(
            connection_name="test",
            oauth_flow_type="client_credentials",
            client_id="abc",
            client_secret="secret",
            authorization_url="https://auth.com/authorize",
            token_url="https://auth.com/token"
        )

        assert request.scopes == ""


class TestOAuthConnectionSummary:
    """Test OAuthConnectionSummary response model - T015"""

    def test_valid_summary_response(self):
        """Test valid OAuth connection summary for list response"""

        summary = OAuthConnectionSummary(
            connection_name="azure_csp_oauth",
            oauth_flow_type="authorization_code",
            status="completed",
            expires_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        )

        assert summary.connection_name == "azure_csp_oauth"
        assert summary.status == "completed"
        assert isinstance(summary.expires_at, datetime)

    def test_valid_status_values(self):
        """Test that all valid status values are accepted"""

        valid_statuses = ["not_connected", "waiting_callback", "testing", "completed", "failed"]

        for status in valid_statuses:
            summary = OAuthConnectionSummary(
                connection_name="test",
                oauth_flow_type="authorization_code",
                status=status,
                created_at=datetime.utcnow()
            )
            assert summary.status == status

    def test_invalid_status_rejected(self):
        """Test that invalid status values are rejected"""

        with pytest.raises(ValidationError) as exc_info:
            OAuthConnectionSummary(
                connection_name="test",
                oauth_flow_type="authorization_code",
                status="invalid_status",
                created_at=datetime.utcnow()
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("status",) for e in errors)


class TestOAuthConnectionDetail:
    """Test OAuthConnectionDetail response model - T016"""

    def test_valid_detail_response(self):
        """Test valid OAuth connection detail response"""

        detail = OAuthConnectionDetail(
            connection_name="azure_csp_oauth",
            oauth_flow_type="authorization_code",
            client_id="abc123",
            authorization_url="https://auth.com/authorize",
            token_url="https://auth.com/token",
            scopes="api.read",
            redirect_uri="/api/oauth/callback/azure_csp_oauth",
            status="completed",
            status_message="Connection active",
            expires_at=datetime.utcnow(),
            last_refresh_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            created_by="user-123",
            updated_at=datetime.utcnow()
        )

        assert detail.connection_name == "azure_csp_oauth"
        assert detail.client_id == "abc123"
        # client_secret should NOT be in detail response
        assert not hasattr(detail, 'client_secret')

    def test_detail_does_not_expose_secrets(self):
        """Test that detail response does not expose sensitive fields"""

        detail = OAuthConnectionDetail(
            connection_name="test",
            oauth_flow_type="client_credentials",
            client_id="abc",
            authorization_url="https://auth.com/authorize",
            token_url="https://auth.com/token",
            scopes="",
            redirect_uri="/api/oauth/callback/test",
            status="completed",
            created_at=datetime.utcnow(),
            created_by="user",
            updated_at=datetime.utcnow()
        )

        detail_dict = detail.model_dump()

        # These fields should NOT be in the response
        assert "client_secret" not in detail_dict
        assert "access_token" not in detail_dict
        assert "refresh_token" not in detail_dict

    def test_detail_serialization_to_json(self):
        """Test that detail can be serialized to JSON mode"""

        detail = OAuthConnectionDetail(
            connection_name="test",
            oauth_flow_type="client_credentials",
            client_id="abc",
            authorization_url="https://auth.com/authorize",
            token_url="https://auth.com/token",
            scopes="",
            redirect_uri="/api/oauth/callback/test",
            status="completed",
            created_at=datetime.utcnow(),
            created_by="user",
            updated_at=datetime.utcnow()
        )

        detail_dict = detail.model_dump(mode="json")
        assert isinstance(detail_dict["created_at"], str)  # datetime -> ISO string
        assert isinstance(detail_dict["updated_at"], str)


class TestOAuthConnection:
    """Test internal OAuthConnection model - storage representation"""

    def test_is_expired_method(self):
        """Test is_expired() method returns True when expires_at is past"""
        from datetime import timedelta

        # Token expired 1 hour ago
        expired_connection = OAuthConnection(
            org_id="GLOBAL",
            connection_name="test",
            oauth_flow_type="client_credentials",
            client_id="abc",
            client_secret_ref="test_client_secret",
            oauth_response_ref="test_oauth_response",
            authorization_url="https://auth.com/authorize",
            token_url="https://auth.com/token",
            redirect_uri="/api/oauth/callback/test",
            status="completed",
            created_by="user",
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )

        assert expired_connection.is_expired()

    def test_expires_soon_method(self):
        """Test expires_soon() method with custom hours threshold"""
        from datetime import timedelta

        # Token expires in 3 hours
        connection = OAuthConnection(
            org_id="GLOBAL",
            connection_name="test",
            oauth_flow_type="client_credentials",
            client_id="abc",
            client_secret_ref="test_client_secret",
            oauth_response_ref="test_oauth_response",
            authorization_url="https://auth.com/authorize",
            token_url="https://auth.com/token",
            redirect_uri="/api/oauth/callback/test",
            status="completed",
            created_by="user",
            expires_at=datetime.utcnow() + timedelta(hours=3)
        )

        # With 4 hour threshold, should return True (expires within 4 hours)
        assert connection.expires_soon(hours=4)

        # With 2 hour threshold, should return False (does not expire within 2 hours)
        assert not connection.expires_soon(hours=2)
