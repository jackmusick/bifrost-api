# Quickstart: OAuth Helper for Integrations and Workflows

**Date**: 2025-10-12
**Audience**: Developers implementing the OAuth helper feature

## Overview

This quickstart provides step-by-step instructions for implementing and testing the OAuth helper feature. Follow these steps in order to build a working OAuth connection management system.

## Prerequisites

-   Python 3.11 installed
-   Azure Functions Core Tools v4
-   Azurite running locally for Table Storage
-   Azure Key Vault access (or local emulator)
-   Postman or similar API testing tool

## Development Setup

### 1. Install Dependencies

```bash
# Navigate to project root
cd /Users/jack/GitHub/bifrost-integrations

# Install Python dependencies
pip install azure-functions azure-data-tables aiohttp pydantic cryptography pytest pytest-asyncio
```

### 2. Configure Local Environment

```bash
# Start Azurite (Azure Storage Emulator)
azurite --silent --location ./azurite --debug ./azurite/debug.log

# Set environment variables
export AZURE_STORAGE_CONNECTION_STRING="UseDevelopmentStorage=true"
export AZURE_KEY_VAULT_URL="https://your-keyvault.vault.azure.net/"
```

### 3. Generate Encryption Key

```python
# Run once to generate encryption key
from cryptography.fernet import Fernet

# Generate key
encryption_key = Fernet.generate_key().decode()
print(f"Encryption key: {encryption_key}")

# Store in Azure Key Vault with name: oauth-token-encryption-key
# For local dev, store in local.settings.json
```

## Implementation Steps

### Phase 1: Core Data Models (Test First)

**Step 1.1: Write Pydantic models**

Create `src/models/oauth_connection.py`:

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime, timedelta

class OAuthConnection(BaseModel):
    org_id: str
    connection_name: str = Field(..., pattern="^[a-zA-Z0-9_-]+$")
    oauth_flow_type: Literal["authorization_code", "client_credentials", "refresh_token"]
    client_id: str
    client_secret_ref: str
    authorization_url: str
    token_url: str
    scopes: str = ""
    redirect_uri: str

    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_at: Optional[datetime] = None

    status: Literal["not_connected", "waiting_callback", "testing", "completed", "failed"]
    status_message: Optional[str] = None
    last_refresh_at: Optional[datetime] = None
    last_test_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def is_expired(self) -> bool:
        if not self.expires_at:
            return True
        return datetime.utcnow() >= self.expires_at

    def expires_soon(self, hours: int = 4) -> bool:
        if not self.expires_at:
            return True
        threshold = datetime.utcnow() + timedelta(hours=hours)
        return self.expires_at <= threshold
```

**Step 1.2: Write contract test**

Create `tests/contract/test_oauth_connection_model.py`:

```python
import pytest
from datetime import datetime, timedelta
from src.models.oauth_connection import OAuthConnection

def test_oauth_connection_validation():
    """Test OAuth connection model validation"""
    connection = OAuthConnection(
        org_id="GLOBAL",
        connection_name="test_connection",
        oauth_flow_type="authorization_code",
        client_id="client123",
        client_secret_ref="test_connection_client_secret",
        authorization_url="https://provider.com/oauth/authorize",
        token_url="https://provider.com/oauth/token",
        scopes="user.read,mail.send",
        redirect_uri="/api/oauth/callback/test_connection",
        status="not_connected",
        created_by="admin"
    )

    assert connection.connection_name == "test_connection"
    assert connection.is_expired() == True  # No expires_at set

def test_expires_soon_logic():
    """Test token expiration logic"""
    connection = OAuthConnection(
        org_id="GLOBAL",
        connection_name="test",
        oauth_flow_type="client_credentials",
        client_id="test",
        client_secret_ref="test_client_secret",
        authorization_url="https://test.com/auth",
        token_url="https://test.com/token",
        redirect_uri="/api/oauth/callback/test",
        status="completed",
        created_by="admin",
        expires_at=datetime.utcnow() + timedelta(hours=3)
    )

    assert connection.expires_soon(hours=4) == True
    assert connection.expires_soon(hours=2) == False
```

Run test: `pytest tests/contract/test_oauth_connection_model.py -v`

### Phase 2: Table Storage Service (Test First)

**Step 2.1: Write service interface**

Create `src/services/oauth_storage_service.py`:

```python
from azure.data.tables.aio import TableServiceClient
from typing import Optional, List
from src.models.oauth_connection import OAuthConnection
from cryptography.fernet import Fernet

class OAuthStorageService:
    def __init__(self, connection_string: str, encryption_key: str):
        self.client = TableServiceClient.from_connection_string(connection_string)
        self.fernet = Fernet(encryption_key.encode())
        self.table_name = "OAuthConnections"

    async def create_connection(self, connection: OAuthConnection) -> OAuthConnection:
        """Create new OAuth connection in Table Storage"""
        pass  # Implement

    async def get_connection(self, org_id: str, connection_name: str) -> Optional[OAuthConnection]:
        """Get OAuth connection with fallback to GLOBAL"""
        pass  # Implement

    async def update_connection(self, connection: OAuthConnection) -> OAuthConnection:
        """Update existing OAuth connection"""
        pass  # Implement

    async def delete_connection(self, org_id: str, connection_name: str) -> bool:
        """Delete OAuth connection"""
        pass  # Implement

    async def list_connections(self, org_id: str, include_global: bool = True) -> List[OAuthConnection]:
        """List all OAuth connections for org"""
        pass  # Implement

    def _encrypt_token(self, token: str) -> str:
        """Encrypt token using Fernet"""
        return self.fernet.encrypt(token.encode()).decode()

    def _decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt token using Fernet"""
        return self.fernet.decrypt(encrypted_token.encode()).decode()
```

**Step 2.2: Write integration test**

Create `tests/integration/test_oauth_storage.py`:

```python
import pytest
import pytest_asyncio
from src.services.oauth_storage_service import OAuthStorageService
from src.models.oauth_connection import OAuthConnection

@pytest_asyncio.fixture
async def storage_service():
    """Create storage service with test encryption key"""
    from cryptography.fernet import Fernet
    key = Fernet.generate_key().decode()
    service = OAuthStorageService(
        connection_string="UseDevelopmentStorage=true",
        encryption_key=key
    )
    yield service
    # Cleanup: delete test data

@pytest.mark.asyncio
async def test_create_and_get_connection(storage_service):
    """Test creating and retrieving OAuth connection"""
    connection = OAuthConnection(
        org_id="GLOBAL",
        connection_name="integration_test",
        oauth_flow_type="client_credentials",
        client_id="test_client",
        client_secret_ref="integration_test_client_secret",
        authorization_url="https://test.com/auth",
        token_url="https://test.com/token",
        redirect_uri="/api/oauth/callback/integration_test",
        status="not_connected",
        created_by="test_user"
    )

    # Create
    created = await storage_service.create_connection(connection)
    assert created.connection_name == "integration_test"

    # Get
    retrieved = await storage_service.get_connection("GLOBAL", "integration_test")
    assert retrieved is not None
    assert retrieved.client_id == "test_client"
```

Run test: `pytest tests/integration/test_oauth_storage.py -v`

### Phase 3: OAuth Provider Client (Test First)

**Step 3.1: Write provider client**

Create `src/services/oauth_provider.py`:

```python
import aiohttp
from typing import Dict, Tuple

class OAuthProviderClient:
    def __init__(self, timeout: int = 10, max_retries: int = 3):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries

    async def exchange_code_for_token(
        self,
        token_url: str,
        code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str
    ) -> Tuple[bool, Dict]:
        """Exchange authorization code for access token"""
        pass  # Implement with retry logic

    async def refresh_access_token(
        self,
        token_url: str,
        refresh_token: str,
        client_id: str,
        client_secret: str
    ) -> Tuple[bool, Dict]:
        """Refresh access token using refresh token"""
        pass  # Implement with retry logic

    async def get_client_credentials_token(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        scopes: str
    ) -> Tuple[bool, Dict]:
        """Get token using client credentials flow"""
        pass  # Implement
```

**Step 3.2: Write integration test with mock OAuth server**

Create `tests/integration/test_oauth_provider.py` with mock OAuth server.

### Phase 4: Azure Functions Endpoints

**Step 4.1: Create OAuth connection**

Create `src/functions/oauth_api.py`:

```python
import azure.functions as func
from src.services.oauth_storage_service import OAuthStorageService
from src.models.oauth_connection import OAuthConnection
import json

async def create_oauth_connection(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/oauth/connections"""
    try:
        body = req.get_json()
        org_id = req.headers.get("X-Organization-Id", "GLOBAL")

        # Validate request
        connection = OAuthConnection(
            org_id=org_id,
            connection_name=body["connection_name"],
            oauth_flow_type=body["oauth_flow_type"],
            client_id=body["client_id"],
            client_secret_ref=f"{body['connection_name']}_client_secret",
            authorization_url=body["authorization_url"],
            token_url=body["token_url"],
            scopes=body.get("scopes", ""),
            redirect_uri=f"/api/oauth/callback/{body['connection_name']}",
            status="not_connected",
            created_by=req.headers.get("X-User-Id", "unknown")
        )

        # Store client secret in secret system
        await set_secret(connection.client_secret_ref, body["client_secret"])

        # Create connection
        storage = get_oauth_storage_service()
        created = await storage.create_connection(connection)

        return func.HttpResponse(
            body=json.dumps(created.dict(), default=str),
            status_code=201,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            body=json.dumps({"error": str(e)}),
            status_code=400,
            mimetype="application/json"
        )
```

**Step 4.2: Write contract test**

Create `tests/contract/test_oauth_api.py`:

```python
import pytest
from azure.functions import HttpRequest
from src.functions.oauth_api import create_oauth_connection

@pytest.mark.asyncio
async def test_create_oauth_connection_contract():
    """Test OAuth connection creation API contract"""
    req = HttpRequest(
        method="POST",
        url="/api/oauth/connections",
        body=json.dumps({
            "connection_name": "test_api",
            "oauth_flow_type": "client_credentials",
            "client_id": "test",
            "client_secret": "secret123",
            "authorization_url": "https://test.com/auth",
            "token_url": "https://test.com/token",
            "scopes": "read,write"
        }).encode(),
        headers={"X-Organization-Id": "ORG123"}
    )

    response = await create_oauth_connection(req)

    assert response.status_code == 201
    body = json.loads(response.get_body())
    assert body["connection_name"] == "test_api"
    assert body["status"] == "not_connected"
```

## Testing Strategy

### 1. Run Contract Tests First

```bash
# Test data models
pytest tests/contract/test_oauth_connection_model.py -v

# Test API contracts
pytest tests/contract/test_oauth_api.py -v
```

### 2. Run Integration Tests

```bash
# Ensure Azurite is running
azurite --silent &

# Test Table Storage integration
pytest tests/integration/test_oauth_storage.py -v

# Test OAuth provider integration
pytest tests/integration/test_oauth_provider.py -v

# Test end-to-end OAuth flow
pytest tests/integration/test_oauth_authorization_flow.py -v
```

### 3. Manual Testing with Postman

**Create connection**:

```bash
POST http://localhost:7071/api/oauth/connections
Headers:
  X-Organization-Id: GLOBAL
Body:
{
  "connection_name": "azure_csp_oauth",
  "oauth_flow_type": "client_credentials",
  "client_id": "your_client_id",
  "client_secret": "your_client_secret",
  "authorization_url": "https://login.microsoftonline.com/.../oauth2/v2.0/authorize",
  "token_url": "https://login.microsoftonline.com/.../oauth2/v2.0/token",
  "scopes": "https://graph.microsoft.com/.default"
}
```

**Initiate authorization** (for authorization_code flow):

```bash
POST http://localhost:7071/api/oauth/connections/azure_csp_oauth/authorize
Headers:
  X-Organization-Id: GLOBAL
```

**Get credentials**:

```bash
GET http://localhost:7071/api/oauth/credentials/azure_csp_oauth
Headers:
  X-Organization-Id: GLOBAL
```

## Workflow Integration Example

### Using OAuth in a Workflow

```python
# In your workflow code
from shared.oauth_helper import get_oauth_connection

async def my_workflow(context):
    # Get OAuth credentials
    credentials = await get_oauth_connection(context, "azure_csp_oauth")

    # Use credentials
    headers = {
        "Authorization": f"{credentials.token_type} {credentials.access_token}"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.example.com/data", headers=headers) as response:
            data = await response.json()
            return data
```

### Register Dependency (Optional)

```python
# Register that this workflow uses the OAuth connection
await register_oauth_dependency(
    workflow_id="my_workflow",
    connection_name="azure_csp_oauth",
    workflow_name="My Workflow"
)
```

## Troubleshooting

### Common Issues

**1. Token encryption errors**

-   Verify encryption key is valid Base64 Fernet key
-   Check key is stored in Key Vault: `oauth-token-encryption-key`

**2. Table Storage connection fails**

-   Ensure Azurite is running: `azurite --version`
-   Check connection string in environment

**3. OAuth callback not received**

-   Verify redirect URI registered with OAuth provider matches: `/api/oauth/callback/{connection_name}`
-   Check callback endpoint is publicly accessible

**4. Token refresh not working**

-   Verify refresh token was received from OAuth provider
-   Check token URL is correct
-   Ensure scheduled job is running every 30 minutes

## Next Steps

After completing the quickstart:

1. **Deploy to Azure**: Configure Azure Functions app with production settings
2. **Set up CI/CD**: Configure GitHub Actions for automated testing and deployment
3. **Add monitoring**: Set up Application Insights alerts for failed OAuth connections
4. **Document OAuth providers**: Create guides for common providers (Microsoft, Google, etc.)
5. **Build UI**: Create admin interface for managing OAuth connections

## Reference

-   **Spec**: [spec.md](./spec.md)
-   **Data Model**: [data-model.md](./data-model.md)
-   **API Contracts**: [contracts/oauth-api.openapi.yaml](./contracts/oauth-api.openapi.yaml)
-   **Research**: [research.md](./research.md)
-   **Plan**: [plan.md](./plan.md)
