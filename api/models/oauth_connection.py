"""
Pydantic models for OAuth connections
Request/response validation and serialization for OAuth helper feature
"""

from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ==================== PUBLIC API ====================

__all__ = [
    # Request models
    'CreateOAuthConnectionRequest',
    'UpdateOAuthConnectionRequest',

    # Response models
    'OAuthConnectionSummary',
    'OAuthConnectionDetail',
    'OAuthConnection',

    # Credentials models
    'OAuthCredentials',
    'OAuthCredentialsResponse',
]


# ==================== ENUMS ====================

# OAuth flow types (as string literals for validation)
OAuthFlowType = Literal["authorization_code", "client_credentials", "refresh_token"]

# OAuth connection status
OAuthStatus = Literal["not_connected", "waiting_callback", "testing", "completed", "failed"]


# ==================== REQUEST MODELS ====================

class CreateOAuthConnectionRequest(BaseModel):
    """
    Request model for creating a new OAuth connection
    POST /api/oauth/connections
    """
    connection_name: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9_-]+$",
        min_length=1,
        max_length=100,
        description="Unique connection identifier (alphanumeric, underscores, hyphens)"
    )
    description: str | None = Field(
        None,
        max_length=500,
        description="Optional description of this OAuth connection"
    )
    oauth_flow_type: OAuthFlowType = Field(
        ...,
        description="OAuth 2.0 flow type"
    )
    client_id: str = Field(
        ...,
        min_length=1,
        description="OAuth client ID (not sensitive)"
    )
    client_secret: str | None = Field(
        None,
        description="OAuth client secret (optional for PKCE flow, will be stored securely in Key Vault)"
    )

    @classmethod
    def model_validate(cls, obj):
        # Convert empty string to None for optional fields
        if isinstance(obj, dict):
            if obj.get('client_secret') == '':
                obj['client_secret'] = None
        return super().model_validate(obj)
    authorization_url: str = Field(
        ...,
        pattern=r"^https://",
        description="OAuth authorization endpoint URL (must be HTTPS)"
    )
    token_url: str = Field(
        ...,
        pattern=r"^https://",
        description="OAuth token endpoint URL (must be HTTPS)"
    )
    scopes: str = Field(
        default="",
        description="Comma-separated list of OAuth scopes to request"
    )


class UpdateOAuthConnectionRequest(BaseModel):
    """
    Request model for updating an OAuth connection
    PUT /api/oauth/connections/{connection_name}
    """
    client_id: str | None = Field(None, min_length=1)
    client_secret: str | None = Field(None, min_length=1)
    authorization_url: str | None = Field(None, pattern=r"^https://")
    token_url: str | None = Field(None, pattern=r"^https://")
    scopes: str | None = None


# ==================== RESPONSE MODELS ====================

class OAuthConnectionSummary(BaseModel):
    """
    Summary model for OAuth connections (used in list responses)
    GET /api/oauth/connections

    Does not include sensitive fields or detailed configuration
    """
    connection_name: str
    description: str | None = None
    oauth_flow_type: OAuthFlowType
    status: OAuthStatus
    status_message: str | None = None
    expires_at: datetime | None = Field(
        None,
        description="When the current access token expires"
    )
    last_refresh_at: datetime | None = Field(
        None,
        description="Last successful token refresh"
    )
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OAuthConnectionDetail(BaseModel):
    """
    Detailed model for OAuth connections (used in get/update responses)
    GET /api/oauth/connections/{connection_name}

    Includes configuration details but masks sensitive fields
    """
    connection_name: str
    description: str | None = None
    oauth_flow_type: OAuthFlowType
    client_id: str = Field(
        ...,
        description="OAuth client ID (safe to expose)"
    )
    authorization_url: str
    token_url: str
    scopes: str
    redirect_uri: str = Field(
        ...,
        description="Callback URL for OAuth authorization"
    )

    # Status information
    status: OAuthStatus
    status_message: str | None = None
    expires_at: datetime | None = None
    last_refresh_at: datetime | None = None
    last_test_at: datetime | None = None

    # Metadata
    created_at: datetime
    created_by: str
    updated_at: datetime

    # NOTE: client_secret, access_token, refresh_token are NOT included
    # These are stored securely and never exposed in API responses

    model_config = ConfigDict(from_attributes=True)


# ==================== INTERNAL/STORAGE MODEL ====================

class OAuthConnection(BaseModel):
    """
    Internal model representing full OAuth connection data
    Used for storage operations and business logic

    Includes references to secrets (not the actual secret values)
    """
    # Partition/Row Keys for Table Storage
    org_id: str = Field(..., description="Organization ID or 'GLOBAL'")
    connection_name: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9_-]+$",
        min_length=1,
        max_length=100
    )

    # OAuth Configuration
    description: str | None = Field(None, max_length=500)
    oauth_flow_type: OAuthFlowType
    client_id: str
    client_secret_ref: str = Field(
        ...,
        description="Reference to client secret in Config table (oauth_{name}_client_secret)"
    )
    oauth_response_ref: str = Field(
        ...,
        description="Reference to OAuth response in Config table (oauth_{name}_oauth_response)"
    )
    authorization_url: str = Field(..., pattern=r"^https://")
    token_url: str = Field(..., pattern=r"^https://")
    scopes: str = ""
    redirect_uri: str = Field(
        ...,
        description="Callback URL: /api/oauth/callback/{connection_name}"
    )

    # Token metadata (not the actual tokens - those are in Config/KeyVault)
    token_type: str = "Bearer"
    expires_at: datetime | None = Field(
        None,
        description="When the current access token expires (copied from secret for quick checks)"
    )

    # Status tracking
    status: OAuthStatus
    status_message: str | None = None
    last_refresh_at: datetime | None = None
    last_test_at: datetime | None = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Helper methods

    def is_expired(self) -> bool:
        """
        Check if the current access token is expired

        Returns:
            True if token is expired or expires_at is not set
        """
        if not self.expires_at:
            return True
        return datetime.utcnow() >= self.expires_at

    def expires_soon(self, hours: int = 4) -> bool:
        """
        Check if the access token expires within the specified number of hours

        Args:
            hours: Number of hours to check (default: 4)

        Returns:
            True if token expires within the specified hours or is already expired
        """
        if not self.expires_at:
            return True
        threshold = datetime.utcnow() + timedelta(hours=hours)
        return self.expires_at <= threshold

    def to_summary(self) -> OAuthConnectionSummary:
        """Convert to summary response model"""
        return OAuthConnectionSummary(
            connection_name=self.connection_name,
            description=self.description,
            oauth_flow_type=self.oauth_flow_type,
            status=self.status,
            status_message=self.status_message,
            expires_at=self.expires_at,
            last_refresh_at=self.last_refresh_at,
            created_at=self.created_at
        )

    def to_detail(self) -> OAuthConnectionDetail:
        """Convert to detail response model (masks secrets)"""
        return OAuthConnectionDetail(
            connection_name=self.connection_name,
            description=self.description,
            oauth_flow_type=self.oauth_flow_type,
            client_id=self.client_id,
            authorization_url=self.authorization_url,
            token_url=self.token_url,
            scopes=self.scopes,
            redirect_uri=self.redirect_uri,
            status=self.status,
            status_message=self.status_message,
            expires_at=self.expires_at,
            last_refresh_at=self.last_refresh_at,
            last_test_at=self.last_test_at,
            created_at=self.created_at,
            created_by=self.created_by,
            updated_at=self.updated_at
        )

    model_config = ConfigDict(from_attributes=True)


# ==================== CREDENTIALS MODELS (USER STORY 3) ====================

class OAuthCredentials(BaseModel):
    """
    OAuth credentials model for workflow consumption
    GET /api/oauth/credentials/{connection_name}

    Contains actual access token and refresh token for use in API calls
    This model is only exposed to authenticated workflow contexts
    """
    connection_name: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Connection identifier"
    )
    access_token: str = Field(
        ...,
        min_length=1,
        description="Current OAuth access token"
    )
    token_type: str = Field(
        default="Bearer",
        description="Token type (usually Bearer)"
    )
    expires_at: str = Field(
        ...,
        description="ISO 8601 timestamp when token expires"
    )
    refresh_token: str | None = Field(
        None,
        description="Refresh token if available"
    )
    scopes: str = Field(
        default="",
        description="Space-separated list of granted scopes"
    )

    model_config = ConfigDict(from_attributes=True)


class OAuthCredentialsResponse(BaseModel):
    """
    Response wrapper for OAuth credentials endpoint
    Includes connection status and metadata
    """
    connection_name: str
    credentials: OAuthCredentials | None = Field(
        None,
        description="Credentials if connection is active, None if not connected"
    )
    status: OAuthStatus = Field(
        ...,
        description="Current connection status"
    )
    expires_at: str | None = Field(
        None,
        description="ISO 8601 timestamp when token expires"
    )

    model_config = ConfigDict(from_attributes=True)
