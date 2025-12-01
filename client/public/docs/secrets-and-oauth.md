# Secrets and OAuth Guide

This guide covers secure credential management, OAuth integration, and secret handling in the Bifrost Integrations platform.

## Table of Contents

- [Overview](#overview)
- [Secret Management](#secret-management)
- [OAuth Integration](#oauth-integration)
- [Key Vault Integration](#key-vault-integration)
- [Security Best Practices](#security-best-practices)
- [Troubleshooting](#troubleshooting)

---

## Overview

Bifrost Integrations provides enterprise-grade security for managing sensitive credentials and OAuth connections:

- **Azure Key Vault Integration**: Secure storage for secrets and certificates
- **OAuth Flow Management**: Automated OAuth 2.0 handling for external services
- **Organization-Scoped Secrets**: Complete isolation of credentials between organizations
- **Automatic Token Refresh**: Seamless token management for long-running workflows
- **Audit Logging**: Complete audit trail of all secret access

### Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│  • Workflows request secrets                                │
│  • Context API abstracts secret access                      │
│  • Automatic token refresh                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Security Layer                           │
│  • Organization scoping                                     │
│  • Access control and auditing                              │
│  • Request logging and monitoring                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Key Vault Layer                          │
│  • Azure Key Vault storage                                  │
│  • Encryption at rest                                       │
│  • Key rotation and management                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Secret Management

### Organization-Scoped Secrets

All secrets are scoped to organizations using the pattern: `{org_id}--{secret_name}`

```python
# Secret naming convention
secret_name = f"{context.org_id}--api_key"
# Example: "test-org-active--microsoft_graph_api_key"
```

### Accessing Secrets in Workflows

```python
@workflow(name="secret_example")
async def secret_example(context: OrganizationContext):
    """Example of accessing secrets in workflows."""

    # Get API key from Key Vault
    api_key = await context.get_secret("my_api_key")
    # Actually retrieves: {org_id}--my_api_key

    # Get database connection string
    db_connection = await context.get_secret("database_connection")

    # Get OAuth client secret
    oauth_secret = await context.get_secret("oauth_client_secret")

    # Use secrets securely
    headers = {"Authorization": f"Bearer {api_key}"}

    # Never log secrets
    context.log("info", "Making API call", {
        "endpoint": "/users",
        "has_auth": bool(api_key)  # ✅ Safe: boolean only
    })
    # ❌ Never do this:
    # context.log("info", "API key", {"key": api_key})

    return {"api_call_successful": True}
```

### Configuration with Secret References

Configuration can reference secrets for automatic resolution:

```json
{
  "organization_id": "org-abc",
  "configuration": {
    "api_settings": {
      "base_url": "https://api.example.com",
      "api_key": {
        "secret_ref": "api_key"  # References {org_id}--api_key
      },
      "timeout": 30
    },
    "database": {
      "connection_string": {
        "secret_ref": "database_connection"
      }
    }
  }
}
```

Access in workflows:

```python
async def config_with_secrets(context: OrganizationContext):
    # Secret references are automatically resolved
    api_key = context.get_config("api_settings.api_key")  # Fetches from Key Vault
    db_connection = context.get_config("database.connection_string")

    return {
        "has_api_key": bool(api_key),
        "has_db_connection": bool(db_connection)
    }
```

### Managing Secrets via API

#### Store a Secret

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org-active" \
  -H "x-functions-key: test" \
  -d '{
    "secret_name": "my_api_key",
    "secret_value": "sk-1234567890abcdef",
    "description": "API key for external service"
  }' \
  http://localhost:7071/api/admin/secrets
```

#### List Secrets

```bash
curl -X GET \
  -H "X-Organization-Id: test-org-active" \
  -H "x-functions-key: test" \
  http://localhost:7071/api/admin/secrets
```

Response:

```json
{
	"secrets": [
		{
			"name": "my_api_key",
			"description": "API key for external service",
			"created_at": "2024-01-01T12:00:00Z",
			"last_accessed": "2024-01-01T14:30:00Z",
			"expires_at": null
		}
	]
}
```

#### Update a Secret

```bash
curl -X PUT \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org-active" \
  -H "x-functions-key: test" \
  -d '{
    "secret_value": "sk-new-key-1234567890",
    "description": "Updated API key for external service"
  }' \
  http://localhost:7071/api/admin/secrets/my_api_key
```

#### Delete a Secret

```bash
curl -X DELETE \
  -H "X-Organization-Id: test-org-active" \
  -H "x-functions-key: test" \
  http://localhost:7071/api/admin/secrets/my_api_key
```

---

## OAuth Integration

### Supported OAuth Providers

The platform supports OAuth 2.0 integration with various providers:

- **Microsoft Graph / Azure AD**
- **Google Workspace**
- **HaloPSA**
- **Custom OAuth 2.0 providers**

### OAuth Connection Management

#### Configure OAuth Connection

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org-active" \
  -H "x-functions-key: test" \
  -d '{
    "provider_name": "HaloPSA",
    "client_id": "your-halo-client-id",
    "client_secret": "your-halo-client-secret",
    "redirect_uri": "https://your-domain.com/oauth/callback",
    "scopes": ["tickets:read", "tickets:write", "clients:read"],
    "additional_config": {
      "api_base_url": "https://your-halo-instance.halopsa.com"
    }
  }' \
  http://localhost:7071/api/admin/oauth/configure
```

#### Initiate OAuth Flow

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org-active" \
  -H "x-functions-key: test" \
  -d '{
    "provider_name": "HaloPSA"
  }' \
  http://localhost:7071/api/admin/oauth/authorize
```

Response:

```json
{
	"authorization_url": "https://your-halo-instance.halopsa.com/oauth/authorize?response_type=code&client_id=your-halo-client-id&redirect_uri=https://your-domain.com/oauth/callback&scope=tickets:read+tickets:write+clients:read&state=abc123",
	"state": "abc123"
}
```

#### OAuth Callback Handler

The platform handles OAuth callbacks automatically:

```python
# OAuth callback endpoint
async def oauth_callback(request):
    """Handle OAuth callback from provider."""

    # Verify state parameter
    state = request.query_params.get("state")
    if not validate_oauth_state(state):
        raise ValidationError("Invalid OAuth state")

    # Exchange authorization code for tokens
    code = request.query_params.get("code")
    tokens = await exchange_code_for_tokens(provider_name, code)

    # Store tokens securely
    await store_oauth_tokens(org_id, provider_name, tokens)

    # Redirect to success page
    return RedirectResponse("/oauth/success")
```

### Using OAuth in Workflows

```python
@workflow(name="halo_ticket_sync")
async def halo_ticket_sync(context: OrganizationContext):
    """Sync tickets from HaloPSA using OAuth."""

    # Get OAuth credentials (automatically handles token refresh)
    halo_creds = await context.get_oauth_connection("HaloPSA")

    # Check if connection is valid
    if not halo_creds.is_valid():
        raise IntegrationError(
            "HaloPSA OAuth connection not configured",
            integration="HaloPSA"
        )

    # Use credentials for API calls
    headers = {
        "Authorization": halo_creds.get_auth_header(),
        "Content-Type": "application/json"
    }

    # Get tickets from HaloPSA
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{halo_creds.api_base_url}/tickets",
            headers=headers
        ) as response:
            if response.status == 200:
                tickets = await response.json()

                context.log("info", f"Retrieved {len(tickets)} tickets from HaloPSA")

                # Process tickets
                processed_tickets = []
                for ticket in tickets:
                    processed = await process_ticket(context, ticket)
                    processed_tickets.append(processed)

                return {
                    "synced_tickets": len(processed_tickets),
                    "tickets": processed_tickets
                }
            else:
                raise IntegrationError(
                    f"Failed to fetch tickets from HaloPSA: {response.status}",
                    integration="HaloPSA",
                    status_code=response.status
                )
```

### Automatic Token Refresh

The platform automatically handles OAuth token refresh:

```python
class OAuthCredentials:
    """Manages OAuth credentials with automatic refresh."""

    def __init__(self, tokens, provider_config):
        self.access_token = tokens["access_token"]
        self.refresh_token = tokens["refresh_token"]
        self.expires_at = tokens["expires_at"]
        self.provider_config = provider_config

    def is_expired(self):
        """Check if access token is expired."""
        return datetime.utcnow() >= self.expires_at

    async def get_auth_header(self):
        """Get authorization header, refreshing if necessary."""
        if self.is_expired():
            await self.refresh_token()

        return f"Bearer {self.access_token}"

    async def refresh_token(self):
        """Refresh the access token."""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.provider_config["token_url"],
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": self.provider_config["client_id"],
                    "client_secret": self.provider_config["client_secret"]
                }
            ) as response:
                if response.status == 200:
                    token_data = await response.json()
                    self.access_token = token_data["access_token"]
                    self.refresh_token = token_data.get("refresh_token", self.refresh_token)
                    self.expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])

                    # Store updated tokens
                    await store_updated_tokens(self)
                else:
                    raise IntegrationError(
                        "Failed to refresh OAuth token",
                        integration=self.provider_config["name"],
                        status_code=response.status
                    )
```

---

## Key Vault Integration

### Azure Key Vault Setup

#### 1. Create Key Vault

```bash
# Create Key Vault
az keyvault create \
  --name "bifrost-integrations-kv" \
  --resource-group "bifrost-rg" \
  --location "eastus" \
  --enable-soft-delete true \
  --enable-purge-protection true
```

#### 2. Configure Access Policies

```bash
# Get managed identity of the Azure Function
FUNCTION_IDENTITY=$(az functionapp identity show \
  --name "bifrost-functions" \
  --resource-group "bifrost-rg" \
  --query "principalId" -o tsv)

# Grant access to Key Vault
az keyvault set-policy \
  --name "bifrost-integrations-kv" \
  --object-id $FUNCTION_IDENTITY \
  --secret-permissions get list set delete
```

#### 3. Configure Application Settings

```bash
# Set Key Vault URI in function app settings
az functionapp config appsettings set \
  --name "bifrost-functions" \
  --resource-group "bifrost-rg" \
  --settings "KEY_VAULT_URI=https://bifrost-integrations-kv.vault.azure.net/"
```

### Key Vault Client Implementation

```python
# /workspace/integrations/keyvault_client.py
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from engine.shared.error_handling import IntegrationError

class KeyVaultClient:
    """Azure Key Vault client for secret management."""

    def __init__(self, key_vault_uri: str):
        self.key_vault_uri = key_vault_uri
        self.credential = DefaultAzureCredential()
        self.client = SecretClient(
            vault_url=key_vault_uri,
            credential=self.credential
        )

    async def get_secret(self, secret_name: str) -> str:
        """Get secret from Key Vault."""
        try:
            secret = await self.client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            raise IntegrationError(
                integration="keyvault",
                message=f"Failed to get secret {secret_name}: {str(e)}"
            )

    async def set_secret(self, secret_name: str, secret_value: str) -> None:
        """Set secret in Key Vault."""
        try:
            await self.client.set_secret(secret_name, secret_value)
        except Exception as e:
            raise IntegrationError(
                integration="keyvault",
                message=f"Failed to set secret {secret_name}: {str(e)}"
            )

    async def delete_secret(self, secret_name: str) -> None:
        """Delete secret from Key Vault."""
        try:
            await self.client.begin_delete_secret(secret_name)
        except Exception as e:
            raise IntegrationError(
                integration="keyvault",
                message=f"Failed to delete secret {secret_name}: {str(e)}"
            )

    async def list_secrets(self, organization_id: str) -> list:
        """List all secrets for an organization."""
        try:
            secrets = []
            secret_properties = self.client.list_properties_of_secrets()

            # Filter secrets by organization prefix
            org_prefix = f"{organization_id}--"

            async for secret_prop in secret_properties:
                if secret_prop.name.startswith(org_prefix):
                    # Remove organization prefix for display
                    display_name = secret_prop.name[len(org_prefix):]

                    secrets.append({
                        "name": display_name,
                        "full_name": secret_prop.name,
                        "created_on": secret_prop.created_on,
                        "updated_on": secret_prop.updated_on,
                        "expires_on": secret_prop.expires_on,
                        "recovery_level": secret_prop.recovery_level
                    })

            return secrets

        except Exception as e:
            raise IntegrationError(
                integration="keyvault",
                message=f"Failed to list secrets: {str(e)}"
            )
```

### Secret Rotation

#### Automatic Secret Rotation

```python
# /workspace/utils/secret_rotation.py
import asyncio
from datetime import datetime, timedelta

class SecretRotationManager:
    """Manages automatic secret rotation."""

    def __init__(self, keyvault_client):
        self.keyvault_client = keyvault_client

    async def rotate_secret_if_needed(self, org_id: str, secret_name: str, rotation_days: int = 90):
        """Rotate secret if it's older than rotation_days."""

        full_secret_name = f"{org_id}--{secret_name}"

        try:
            # Get secret properties
            secret = await self.keyvault_client.get_secret(full_secret_name)

            # Check if secret needs rotation
            if secret.properties.created_on:
                age_days = (datetime.utcnow() - secret.properties.created_on).days

                if age_days >= rotation_days:
                    await self.rotate_secret(org_id, secret_name)
                    return True

            return False

        except Exception as e:
            # Secret doesn't exist or other error
            return False

    async def rotate_secret(self, org_id: str, secret_name: str):
        """Rotate a secret with a new value."""

        # Generate new secret value
        new_value = await self.generate_new_secret_value(secret_name)

        # Store new secret
        full_secret_name = f"{org_id}--{secret_name}"
        await self.keyvault_client.set_secret(full_secret_name, new_value)

        # Log rotation
        context.log("info", f"Secret rotated: {secret_name}", {
            "organization_id": org_id,
            "rotation_date": datetime.utcnow().isoformat()
        })

    async def generate_new_secret_value(self, secret_name: str) -> str:
        """Generate a new secret value based on the secret type."""

        if "api_key" in secret_name:
            # Generate API key
            return f"sk-{generate_random_string(32)}"

        elif "password" in secret_name:
            # Generate secure password
            return generate_secure_password(16)

        elif "certificate" in secret_name:
            # Generate certificate (simplified)
            return await self.generate_certificate()

        else:
            # Generate random string
            return generate_random_string(32)

# Scheduled task for secret rotation
@workflow(
    name="rotate_secrets",
    description="Rotate old secrets automatically",
    execution_mode="scheduled",
    schedule="0 2 * * 0"  # Weekly on Sunday at 2 AM
)
async def rotate_secrets(context: OrganizationContext):
    """Scheduled workflow to rotate old secrets."""

    keyvault_client = KeyVaultClient(context.get_config("key_vault_uri"))
    rotation_manager = SecretRotationManager(keyvault_client)

    # Get all secrets for organization
    secrets = await keyvault_client.list_secrets(context.org_id)

    rotated_count = 0
    for secret in secrets:
        if await rotation_manager.rotate_secret_if_needed(
            context.org_id,
            secret["name"],
            rotation_days=90
        ):
            rotated_count += 1

    context.log("info", f"Secret rotation completed", {
        "total_secrets": len(secrets),
        "rotated_secrets": rotated_count
    })

    return {
        "total_secrets": len(secrets),
        "rotated_secrets": rotated_count
    }
```

---

## Security Best Practices

### 1. Secret Naming Conventions

Use consistent, descriptive naming:

```python
# ✅ Good naming conventions
"{org_id}--microsoft_graph_api_key"
"{org_id}--halopsa_client_secret"
"{org_id}--database_connection_string"
"{org_id}--smtp_password"

# ❌ Bad naming conventions
"{org_id}--key1"
"{org_id}--secret"
"{org_id}--abc123"
```

### 2. Principle of Least Privilege

Grant minimum required permissions:

```bash
# ✅ Good: Specific permissions
az keyvault set-policy \
  --name "bifrost-kv" \
  --object-id $FUNCTION_IDENTITY \
  --secret-permissions get list

# ❌ Bad: Excessive permissions
az keyvault set-policy \
  --name "bifrost-kv" \
  --object-id $FUNCTION_IDENTITY \
  --secret-permissions get list set delete backup restore purge
```

### 3. Secret Access Auditing

Monitor and audit all secret access:

```python
async def get_secret_with_audit(context: OrganizationContext, secret_name: str):
    """Get secret with comprehensive audit logging."""

    # Log access attempt
    context.log("info", "Secret access requested", {
        "secret_name": secret_name,
        "user_id": context.caller.user_id,
        "workflow": context.execution_id
    })

    try:
        # Get secret
        secret_value = await context.get_secret(secret_name)

        # Log successful access
        context.log("info", "Secret access successful", {
            "secret_name": secret_name,
            "user_id": context.caller.user_id
        })

        return secret_value

    except Exception as e:
        # Log failed access
        context.log("error", "Secret access failed", {
            "secret_name": secret_name,
            "user_id": context.caller.user_id,
            "error": str(e)
        })

        raise
```

### 4. Secure Secret Transmission

Never transmit secrets in URLs or query parameters:

```python
# ✅ Good: Use POST body with HTTPS
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"secret_value": "sk-123456"}' \
  https://api.example.com/secrets

# ❌ Bad: Secret in URL
curl https://api.example.com/secrets?value=sk-123456
```

### 5. Secret Versioning

Use secret versioning for safe updates:

```python
async def update_secret_safely(context: OrganizationContext, secret_name: str, new_value: str):
    """Update secret with versioning and rollback capability."""

    # Store current value as backup
    try:
        current_value = await context.get_secret(secret_name)
        backup_name = f"{secret_name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        await context.set_secret(backup_name, current_value)

        # Set new value
        await context.set_secret(secret_name, new_value)

        context.log("info", f"Secret updated: {secret_name}", {
            "backup_name": backup_name
        })

        return {"success": True, "backup_name": backup_name}

    except Exception as e:
        context.log("error", f"Failed to update secret: {secret_name}", {
            "error": str(e)
        })
        raise
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: Key Vault Access Denied

**Error**: `Key Vault access denied for secret 'my-secret'`

**Solutions**:

1. Check managed identity permissions:

```bash
az keyvault show --name "your-keyvault" --query "properties.accessPolicies"
```

2. Grant proper permissions:

```bash
az keyvault set-policy \
  --name "your-keyvault" \
  --object-id $FUNCTION_IDENTITY \
  --secret-permissions get list
```

3. Verify Key Vault URI configuration:

```bash
az functionapp config appsettings list \
  --name "your-function-app" \
  --query "[?name=='KEY_VAULT_URI'].value"
```

#### Issue 2: OAuth Token Expired

**Error**: `OAuth token expired for provider 'HaloPSA'`

**Solutions**:

1. Check refresh token validity:

```python
halo_creds = await context.get_oauth_connection("HaloPSA")
if not halo_creds.refresh_token:
    # Need to re-authenticate
    await reinitiate_oauth_flow("HaloPSA")
```

2. Manually refresh connection:

```bash
curl -X POST \
  -H "X-Organization-Id: test-org-active" \
  -H "x-functions-key: test" \
  -d '{"provider_name": "HaloPSA"}' \
  http://localhost:7071/api/admin/oauth/refresh
```

#### Issue 3: Secret Not Found

**Error**: `Secret 'my-secret' not found in Key Vault`

**Solutions**:

1. Check secret naming:

```python
# Secrets are org-scoped
full_name = f"{context.org_id}--my-secret"
```

2. List available secrets:

```bash
curl -X GET \
  -H "X-Organization-Id: test-org-active" \
  -H "x-functions-key: test" \
  http://localhost:7071/api/admin/secrets
```

3. Create missing secret:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org-active" \
  -H "x-functions-key: test" \
  -d '{
    "secret_name": "my_secret",
    "secret_value": "your-secret-value"
  }' \
  http://localhost:7071/api/admin/secrets
```

#### Issue 4: OAuth Configuration Invalid

**Error**: `Invalid OAuth configuration for provider`

**Solutions**:

1. Verify OAuth settings:

```bash
curl -X GET \
  -H "X-Organization-Id: test-org-active" \
  -H "x-functions-key: test" \
  http://localhost:7071/api/admin/oauth/config/HaloPSA
```

2. Update configuration:

```bash
curl -X PUT \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org-active" \
  -H "x-functions-key: test" \
  -d '{
    "client_id": "new-client-id",
    "client_secret": "new-client-secret"
  }' \
  http://localhost:7071/api/admin/oauth/config/HaloPSA
```

### Debugging Tools

#### Secret Access Test

```python
@workflow(name="test_secret_access")
async def test_secret_access(context: OrganizationContext):
    """Test secret access and configuration."""

    test_results = {
        "keyvault_access": False,
        "secret_access": {},
        "oauth_connections": {}
    }

    # Test Key Vault access
    try:
        test_secret = await context.get_secret("test_secret")
        test_results["keyvault_access"] = True
    except Exception as e:
        test_results["keyvault_error"] = str(e)

    # Test specific secrets
    test_secrets = ["api_key", "database_connection", "oauth_client_secret"]
    for secret_name in test_secrets:
        try:
            value = await context.get_secret(secret_name)
            test_results["secret_access"][secret_name] = "✅ Accessible"
        except Exception as e:
            test_results["secret_access"][secret_name] = f"❌ {str(e)}"

    # Test OAuth connections
    test_providers = ["HaloPSA", "MicrosoftGraph"]
    for provider in test_providers:
        try:
            creds = await context.get_oauth_connection(provider)
            test_results["oauth_connections"][provider] = "✅ Connected"
        except Exception as e:
            test_results["oauth_connections"][provider] = f"❌ {str(e)}"

    return test_results
```

This comprehensive secrets and OAuth management system ensures that Bifrost Integrations maintains enterprise-grade security while providing seamless integration with external services.
