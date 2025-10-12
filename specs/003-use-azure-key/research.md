# Azure Key Vault Integration Research

**Research Date**: 2025-10-12
**Feature**: Azure Key Vault Integration for Secret Management
**Status**: Complete

## Research Summary

This document provides comprehensive research findings for implementing Azure Key Vault integration in a Python Azure Functions project. Research covers authentication patterns, secret management, local development alternatives, health checks, and error handling based on official Microsoft documentation and Azure SDK best practices.

## Key Decisions

### 1. Authentication Pattern

**Decision**: Use `DefaultAzureCredential` for both production and local development

**Rationale**:
- Unified authentication approach across environments
- Production: Automatically uses managed identity
- Local: Automatically tries Azure CLI (`az login`), Visual Studio, etc.
- No environment-specific code needed

**Implementation**:
```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
vault_url = os.environ.get("AZURE_KEY_VAULT_URL")
client = SecretClient(vault_url=vault_url, credential=credential)
```

### 2. Secret Naming Convention

**Decision**: `{org_id}--{secret-name}` for org-scoped, `GLOBAL--{secret-name}` for platform-wide

**Rationale**:
- Microsoft recommended pattern for multi-tenant Key Vault
- Clear visual separation with double-dash
- Supports org-specific overrides with global fallback
- Compatible with Key Vault naming restrictions (alphanumeric and hyphens only)

**Examples**:
- Org-scoped: `org-abc123--msgraph-client-secret`
- Platform-wide: `GLOBAL--smtp-password`

### 3. Secret Caching Strategy

**Decision**: In-memory cache with 1-hour TTL

**Rationale**:
- Reduces Key Vault API calls (limit: 4,000 ops per 10 seconds)
- Minimizes latency after initial load (<100ms target)
- Balances freshness with performance (1 hour = reasonable rotation window)
- Microsoft recommends "at least 8 hours" but 1 hour provides better rotation support

**Performance**:
- First access: ~50-100ms (Key Vault network call)
- Cached access: <1ms (in-memory lookup)

### 4. Local Development Fallback

**Decision**: Three-tier fallback strategy

1. **Primary**: Azure Key Vault with developer credentials (`az login`)
2. **Fallback**: Environment variables in `local.settings.json`
3. **Alternative**: `.env` file (with `.gitignore`)

**Rationale**:
- Dev/prod parity when possible (use actual Key Vault)
- Practical fallback when Key Vault unavailable
- No local secrets required for basic development

**Local env var pattern**:
- Org-scoped: `{ORG_ID}__{SECRET_KEY}` (e.g., `ORG123__API_KEY`)
- Platform-wide: `GLOBAL__{SECRET_KEY}` (e.g., `GLOBAL__SMTP_PASSWORD`)

### 5. Health Check Implementation

**Decision**: Use `list_properties_of_secrets()` for non-intrusive health check

**Rationale**:
- Verifies connectivity and authentication without retrieving secret values
- Requires only `secrets/list` permission (read-only)
- Doesn't create audit log entries for secret access
- Fast operation (returns iterator immediately)

**Implementation**:
```python
try:
    secrets = client.list_properties_of_secrets()
    next(iter(secrets), None)  # Trigger API call
    return {"status": "healthy", "message": "Connected"}
except ClientAuthenticationError:
    return {"status": "unhealthy", "message": "Auth failed"}
```

### 6. Error Handling Strategy

**Decision**: Comprehensive error handling with actionable messages

**Key exceptions**:
- `ResourceNotFoundError` (404): Secret doesn't exist
- `ClientAuthenticationError` (401): Authentication failed
- `HttpResponseError` (403): Permission denied
- `ServiceRequestError`: Network/connection errors
- `HttpResponseError` (429): Rate limit exceeded

**Rationale**:
- Clear, actionable error messages for operators
- No secret values exposed in errors or logs
- SDK handles automatic retries for transient failures

### 7. Retry Strategy

**Decision**: Use Azure SDK built-in retry policy with custom configuration

**Configuration**:
- Total retries: 5 attempts
- Backoff factor: 0.8 (exponential backoff)
- Max backoff: 120 seconds
- Retry on: 408, 429, 500, 502, 503, 504 status codes

**Retry timing**: ~25 seconds total across all retries

## Alternatives Considered

| Decision Area | Alternative Considered | Why Rejected |
|--------------|----------------------|--------------|
| **Auth - Local** | InteractiveBrowserCredential | Slower than CLI, requires browser on every token refresh |
| **Auth - Local** | Service Principal with env vars | Defeats purpose of Key Vault, managing secrets for dev |
| **Secret Naming** | Separate Key Vaults per org | High cost, management overhead, only for high isolation needs |
| **Secret Naming** | Tags for tenant identification | Can't query by tags, not accessible in retrieval logic |
| **Caching** | No caching | High latency, risk of throttling with high-volume workflows |
| **Caching** | Redis/distributed cache | Adds complexity, not needed for single-process Functions |
| **Caching** | 8+ hour cache (MS recommendation) | Too long for secret rotation scenarios, 1 hour is safer |
| **Health Check** | Create/delete test secret | Intrusive, creates audit logs, requires write permissions |
| **Health Check** | Retrieve known secret | Generates audit logs, requires maintaining dedicated secret |
| **Local Dev** | Local Key Vault emulator | Doesn't exist (unlike Azurite for storage) |
| **Local Dev** | Docker Compose secrets | Overkill for local development |

## Implementation Patterns

### Secret Retrieval with Org/Global Fallback

```python
async def get_secret_with_fallback(
    client: SecretClient,
    org_id: str,
    secret_key: str
) -> str:
    # Try org-scoped secret first
    org_secret_name = f"{org_id}--{secret_key}"
    try:
        secret = client.get_secret(org_secret_name)
        return secret.value
    except ResourceNotFoundError:
        pass

    # Try global secret
    global_secret_name = f"GLOBAL--{secret_key}"
    try:
        secret = client.get_secret(global_secret_name)
        return secret.value
    except ResourceNotFoundError:
        raise KeyError(
            f"Secret '{secret_key}' not found for org '{org_id}'. "
            f"Tried: {org_secret_name}, {global_secret_name}"
        )
```

### Secret Caching Layer

```python
class SecretCache:
    def __init__(self, client: SecretClient, cache_duration: int = 3600):
        self.client = client
        self._cache: Dict[str, Tuple[str, float]] = {}
        self._cache_duration = cache_duration

    def get_secret(self, secret_name: str) -> str:
        # Check cache
        if secret_name in self._cache:
            cached_value, cached_time = self._cache[secret_name]
            if time.time() - cached_time < self._cache_duration:
                return cached_value

        # Fetch from Key Vault
        secret = self.client.get_secret(secret_name)
        value = secret.value

        # Update cache
        self._cache[secret_name] = (value, time.time())
        return value
```

### Local Development Fallback

```python
def get_secret_with_local_fallback(
    org_id: str,
    secret_key: str,
    client: SecretClient = None
) -> str:
    # Try Key Vault if client provided
    if client:
        try:
            secret_name = f"{org_id}--{secret_key}"
            return client.get_secret(secret_name).value
        except Exception as e:
            logger.warning(f"Key Vault unavailable: {e}, using local fallback")

    # Try local env var (org-scoped)
    local_var = f"{org_id.upper().replace('-', '_')}__{secret_key.upper().replace('-', '_')}"
    if local_value := os.environ.get(local_var):
        return local_value

    # Try local env var (global)
    global_var = f"GLOBAL__{secret_key.upper().replace('-', '_')}"
    if local_value := os.environ.get(global_var):
        return local_value

    raise KeyError(f"Secret '{secret_key}' not found in Key Vault or local config")
```

## Security Best Practices

1. **Never log secret values** - Only log secret names and access patterns
2. **Mask secrets in UI** - Show plaintext only immediately after creation/update
3. **Use managed identity** - No credentials in configuration
4. **Implement caching** - Reduce Key Vault API calls to avoid throttling
5. **Handle errors gracefully** - Provide actionable guidance without exposing secrets
6. **Use RBAC over Access Policies** - More granular, auditable permissions
7. **Enable soft-delete** - Secrets recoverable for 90 days after deletion
8. **Enable purge protection** - Prevent permanent deletion during retention period

## Performance Characteristics

| Operation | First Access | Cached Access | Notes |
|-----------|-------------|---------------|-------|
| Secret retrieval | 50-100ms | <1ms | Network call vs in-memory |
| Health check | 50-100ms | N/A | Always fresh check |
| Authentication | 100-200ms | Automatic | Token cached by SDK |
| List secrets | 100-200ms | N/A | For UI dropdown |

## References

- [Azure Key Vault Python SDK](https://learn.microsoft.com/en-us/python/api/overview/azure/keyvault-secrets-readme)
- [Azure Identity Python SDK](https://learn.microsoft.com/en-us/python/api/overview/azure/identity-readme)
- [DefaultAzureCredential Chain](https://learn.microsoft.com/en-us/azure/developer/python/sdk/authentication/credential-chains)
- [Multi-tenant Key Vault Patterns](https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/service/key-vault)
- [Key Vault Best Practices](https://learn.microsoft.com/en-us/azure/key-vault/general/best-practices)
- [Secrets Management Best Practices](https://learn.microsoft.com/en-us/azure/key-vault/secrets/secrets-best-practices)

## Next Steps

1. Generate data model for secret entities
2. Define API contracts for secret management endpoints
3. Create quickstart guide for local Key Vault setup
4. Break down implementation into tasks
