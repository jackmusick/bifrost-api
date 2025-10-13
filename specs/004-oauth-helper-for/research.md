# Research: OAuth Helper for Integrations and Workflows

**Date**: 2025-10-12
**Phase**: 0 (Research & Design Decisions)

## Overview

This document consolidates research findings and design decisions for implementing the OAuth helper feature. All decisions are made to align with constitutional principles and established platform patterns.

## Key Research Areas

### 1. OAuth 2.0 Flow Implementation

**Decision**: Implement three OAuth 2.0 flows - Authorization Code, Client Credentials, and Refresh Token

**Rationale**:
- **Authorization Code Flow**: Required for user-facing OAuth (Microsoft 365, Google, etc.) where end-user grants permission
- **Client Credentials Flow**: Required for service-to-service OAuth (Azure CSP, monitoring APIs) with no user interaction
- **Refresh Token Flow**: Essential for automatic token refresh without user re-authorization

**Implementation approach**:
- Use `aiohttp` for async HTTP calls to OAuth providers
- Store authorization URLs, token URLs, client credentials in Table Storage
- Support standard OAuth 2.0 parameters: `client_id`, `client_secret`, `scope`, `redirect_uri`, `state`
- Handle PKCE (Proof Key for Code Exchange) for enhanced security when supported

**Alternatives considered**:
- Using `authlib` library: Rejected because it adds unnecessary dependency for straightforward HTTP calls
- Supporting OAuth 1.0: Rejected as it's deprecated and not used by modern services
- Supporting device code flow: Deferred to future phase as not needed for initial use cases

### 2. Token Storage via Existing Config System

**Decision**: Store OAuth connections as regular configs using existing `Config` table with `secret_ref` type for sensitive data

**Rationale**:
- Platform consistency: OAuth connections ARE configs, use existing config infrastructure
- Leverages existing config system: `get_config()` with `Type="secret_ref"` automatically resolves from Key Vault
- Unified approach: All platform configs (including OAuth) managed the same way
- Org-scoping: Config system already handles org-specific → GLOBAL fallback
- No new tables needed: Reuse `Config` table with `config:oauth_{connection_name}_*` keys

**Config storage pattern**:

OAuth connections stored as multiple config entries in `Config` table:

```
Config Table:
PartitionKey: OrgId or "GLOBAL"
RowKey: "config:oauth_{connection_name}_client_secret"
Value: "keyvault-secret-name-for-client-secret"
Type: "secret_ref"

PartitionKey: OrgId or "GLOBAL"
RowKey: "config:oauth_{connection_name}_tokens"
Value: "keyvault-secret-name-for-tokens"
Type: "secret_ref"

PartitionKey: OrgId or "GLOBAL"
RowKey: "config:oauth_{connection_name}_metadata"
Value: JSON string with oauth_flow_type, authorization_url, token_url, scopes, etc.
Type: "json"
```

**Example for azure_csp_oauth connection**:
```
config:oauth_azure_csp_oauth_client_secret  (Type: secret_ref)
config:oauth_azure_csp_oauth_tokens         (Type: secret_ref)
config:oauth_azure_csp_oauth_metadata       (Type: json)
```

**OAuth tokens format** (stored as JSON in Key Vault secret, referenced by config):
```json
{
  "access_token": "ya29.a0AfH6...",
  "refresh_token": "1//0gKx...",
  "token_type": "Bearer",
  "expires_at": "2025-10-12T15:30:00Z"
}
```

**Implementation approach**:
```python
# On connection creation
await set_config_secret(org_id, f"oauth_{connection_name}_client_secret", client_secret)

# On OAuth callback/refresh
tokens_json = json.dumps({
    "access_token": access_token,
    "refresh_token": refresh_token,
    "expires_at": expires_at.isoformat(),
    "token_type": "Bearer"
})
await set_config_secret(org_id, f"oauth_{connection_name}_tokens", tokens_json)

# Store metadata as json config
metadata_json = json.dumps({
    "oauth_flow_type": "authorization_code",
    "client_id": "...",
    "authorization_url": "...",
    "token_url": "...",
    "scopes": "...",
    "status": "completed",
    "expires_at": expires_at.isoformat()  # Duplicate for quick expiry checks
})
await set_config(org_id, f"oauth_{connection_name}_metadata", metadata_json, type="json")

# In workflow - get OAuth credentials
config_data = await load_org_config(org_id)  # Loads all configs including GLOBAL fallback
tokens_json = config_resolver.get_config(org_id, f"oauth_{connection_name}_tokens", config_data)
tokens = json.loads(tokens_json)
access_token = tokens["access_token"]
```

**Benefits**:
- **Zero new infrastructure**: Reuses existing `Config` table, `get_config()`, Key Vault integration
- **Consistent pattern**: OAuth configs work exactly like other platform configs
- **Automatic org-scoping**: Config fallback logic already implemented
- **Simple workflow access**: `get_config('oauth_connection_name_tokens')` just works
- **No separate OAuth tables**: Everything in `Config` table with `oauth_` prefix

**OAuthConnections table still needed** for:
- Connection status tracking (not_connected, waiting_callback, testing, completed, failed)
- OAuth-specific metadata (redirect_uri, last_refresh_at, last_test_at)
- Faster queries for "find all OAuth connections" vs scanning Config table

**Alternatives considered**:
- Separate OAuthConnections table with encrypted fields: Rejected because doesn't leverage existing config system
- Store everything in Config table only: Possible but makes OAuth-specific queries slower

### 3. Callback URL Routing

**Decision**: Use unique callback URLs with connection identifier in path: `/api/oauth/callback/{connection_name}`

**Rationale**:
- Enables routing callback to correct connection configuration
- Avoids state parameter conflicts when multiple connections use same provider
- Simplifies callback handler logic (extract connection from URL path)
- Provides clear URL for administrators to register with OAuth providers

**Implementation approach**:
- Azure Function HTTP trigger: `POST /api/oauth/callback/{connection_name}`
- Extract `connection_name` from route parameter
- Query Table Storage for connection config
- Validate state parameter (CSRF protection)
- Exchange authorization code for tokens
- Store tokens and update status to "testing"
- Run connection test
- Update status to "completed" or "failed"

**Alternatives considered**:
- Single callback URL with state parameter routing: Rejected due to complexity managing state mappings
- Query parameter routing (`/api/oauth/callback?connection=X`): Rejected as less RESTful and harder to secure

### 4. Token Refresh Strategy

**Decision**: Azure Functions Timer trigger runs every 30 minutes, refreshes tokens expiring within 4 hours

**Rationale**:
- Specification requirement: Scheduled job runs every 30 minutes
- Specification requirement: Refresh when tokens expire within 4 hours
- Constitutional requirement: Use Azure Functions (no external schedulers)
- Performance requirement: Meets SC-003 (99% refresh success before expiration)

**Implementation approach**:
```python
@app.timer_trigger(schedule="0 */30 * * * *")  # Every 30 minutes
async def oauth_refresh_timer(timer: func.TimerRequest):
    # Query all OAuth connections
    connections = await get_all_oauth_connections()

    # Filter: expires_at < now + 4 hours AND has refresh_token
    expiring_soon = [c for c in connections if should_refresh(c)]

    # Refresh in parallel (asyncio.gather)
    results = await asyncio.gather(*[refresh_connection(c) for c in expiring_soon])

    # Log results to Application Insights
```

**Refresh logic**:
- Check `expires_at` timestamp
- If `expires_at < now + 4 hours`:
  - For authorization code flow: Use refresh token to get new access token
  - For client credentials flow: Request new token with client credentials
  - Update stored tokens and `expires_at`
  - Update `last_refresh_at` timestamp
  - Maintain status as "completed"
- If refresh fails:
  - Update status to "failed" with error message
  - Log to Application Insights for alerting

**Alternatives considered**:
- Refresh on credential access: Rejected because workflows would experience latency during refresh
- Shorter refresh window (< 4 hours): Rejected as user specified 4 hours
- Longer schedule interval (> 30 minutes): Rejected as user specified 30 minutes

### 5. Workflow Dependency Detection

**Decision**: Implement webhook/API endpoint for workflows to register OAuth dependencies, maintain dependency table

**Rationale**:
- Specification requirement (FR-020): Detect which workflows reference specific OAuth connections
- Specification requirement (FR-017): Warn and cascade disable when deleting connections
- Current limitation: Workflow metadata doesn't expose script content
- Future-proof: Enables workflow impact analysis and dependency tracking

**Implementation approach**:

**Table Storage schema**:
```
Table: WorkflowOAuthDependencies
PartitionKey: connection_name (enables fast "which workflows use this connection" queries)
RowKey: workflow_id
Fields:
  - connection_name (string)
  - workflow_id (string)
  - org_id (string)
  - registered_at (datetime)
```

**Dual index**:
```
Table: WorkflowOAuthDependencies_ByWorkflow
PartitionKey: workflow_id (enables fast "which connections does this workflow use" queries)
RowKey: connection_name
Fields: [same as above]
```

**Registration approach**:
- Workflow explicitly registers dependency: `register_oauth_dependency(connection_name)`
- Called during workflow initialization or first `get_oauth_connection()` call
- Stored in dual-indexed tables for bidirectional lookup
- Tombstone on workflow deletion

**Deletion flow**:
1. Admin attempts delete connection
2. Query `WorkflowOAuthDependencies` with `PartitionKey = connection_name`
3. Display list of dependent workflows
4. Require confirmation
5. If confirmed:
   - Delete connection
   - Mark workflows as disabled in `WorkflowDisableState` table
   - Update workflow metadata (if API supports)

**Alternatives considered**:
- Static code analysis: Rejected because workflow scripts not accessible via /metadata endpoint
- Runtime detection only: Rejected because workflows would fail before we know they're affected
- Manual tracking: Rejected because error-prone and doesn't scale

### 6. Workflow Disable State Management

**Decision**: Create `WorkflowDisableState` table to track disabled workflows, integrate with workflow execution engine

**Rationale**:
- Specification requirement (FR-021): Allow administrators to disable and re-enable workflows
- Specification requirement: Workflows disabled due to OAuth connection deletion need clear status
- Constitutional requirement: Store state in Table Storage
- Separation of concerns: Workflow disable state is independent of workflow metadata

**Implementation approach**:

**Table Storage schema**:
```
Table: WorkflowDisableState
PartitionKey: org_id or "GLOBAL"
RowKey: workflow_id
Fields:
  - workflow_id (string)
  - org_id (string)
  - is_disabled (boolean)
  - disabled_reason (string: "oauth_connection_deleted", "manual", etc.)
  - disabled_at (datetime)
  - disabled_by (string, user ID)
  - related_oauth_connection (string, optional, connection name that triggered disable)
```

**Workflow execution check**:
```python
async def execute_workflow(workflow_id, org_id, context):
    # Check if workflow is disabled
    disable_state = await get_workflow_disable_state(org_id, workflow_id)
    if disable_state and disable_state.is_disabled:
        raise WorkflowDisabledException(f"Workflow disabled: {disable_state.disabled_reason}")

    # Continue with execution...
```

**UI integration**:
- Workflows page displays disable status and reason
- Toggle button to enable/disable workflows
- Filter to show only enabled/disabled workflows

**Alternatives considered**:
- Storing disable state in workflow metadata: Rejected because metadata is managed by workflow engine, not OAuth system
- Delete workflows instead of disable: Rejected because workflows might be recoverable
- No disable state, just fail at runtime: Rejected because provides poor user experience

### 7. OAuth Provider HTTP Client

**Decision**: Build custom async OAuth HTTP client using `aiohttp` with retry logic and timeout handling

**Rationale**:
- Constitutional requirement: Use async/await for all I/O operations
- Performance requirement: Token refresh must complete in <2 seconds
- Reliability requirement: 99% refresh success requires retry logic for transient failures
- Simplicity: OAuth 2.0 HTTP calls are straightforward, no need for heavy library

**Implementation approach**:
```python
class OAuthProviderClient:
    def __init__(self, timeout: int = 10, max_retries: int = 3):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout))
        self.max_retries = max_retries

    async def exchange_code_for_token(self, token_url, code, client_id, client_secret, redirect_uri):
        """Exchange authorization code for access token."""
        # POST request with retry logic
        # Parse JSON response
        # Return tokens

    async def refresh_access_token(self, token_url, refresh_token, client_id, client_secret):
        """Refresh access token using refresh token."""
        # POST request with retry logic
        # Handle expired refresh token error
        # Return new tokens

    async def get_client_credentials_token(self, token_url, client_id, client_secret, scopes):
        """Get token using client credentials flow."""
        # POST request with retry logic
        # Return token
```

**Error handling**:
- Retry transient errors (500, 503, network timeout) up to 3 times with exponential backoff
- Fail immediately on client errors (400, 401, 403)
- Log all errors to Application Insights
- Update connection status with descriptive error message

**Alternatives considered**:
- Using `requests` library: Rejected because synchronous, blocks event loop
- Using `authlib`: Rejected as overkill for simple HTTP calls
- No retry logic: Rejected because fails reliability requirement

### 8. Connection Testing

**Decision**: Test OAuth connections by making lightweight API call to provider's health/profile endpoint after receiving tokens

**Rationale**:
- Specification requirement (FR-007): Test connections after receiving credentials
- Specification requirement: Status "testing" → "completed" or "failed"
- Validation: Ensure tokens are valid before marking connection as ready
- User feedback: Provide clear success/failure status

**Implementation approach**:
```python
async def test_oauth_connection(connection):
    """Test OAuth connection by calling provider's test endpoint."""
    test_endpoints = {
        "microsoft": "https://graph.microsoft.com/v1.0/me",
        "google": "https://www.googleapis.com/oauth2/v1/userinfo",
        "generic": None  # No test for custom providers
    }

    # Detect provider from authorization_url or token_url
    provider = detect_provider(connection)
    test_url = test_endpoints.get(provider)

    if test_url:
        # Make authenticated request
        headers = {"Authorization": f"Bearer {connection.access_token}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(test_url, headers=headers, timeout=5) as response:
                if response.status == 200:
                    return True, "Connection test successful"
                else:
                    return False, f"Connection test failed: HTTP {response.status}"
    else:
        # Skip test for unknown providers
        return True, "Connection created (test skipped for custom provider)"
```

**Alternatives considered**:
- No testing: Rejected because user won't know if connection works until workflow fails
- Test on every credential retrieval: Rejected due to performance overhead
- Comprehensive API test: Rejected because varies by provider and adds complexity

## Technology Best Practices

### Python Azure Functions

- **Startup performance**: Load encryption key from Key Vault once on cold start, cache in memory
- **Async patterns**: Use `asyncio.gather()` for parallel token refresh operations
- **Connection pooling**: Reuse `aiohttp.ClientSession` across function invocations
- **Error handling**: Catch and log all exceptions, return user-friendly error messages
- **Logging**: Use structured logging with Application Insights for observability

### Azure Table Storage

- **Partition strategy**: Use OrgId for org-scoped data, "GLOBAL" for MSP-level data
- **Row key design**: Use meaningful identifiers (connection_name) for point queries
- **Query optimization**: Avoid table scans; use partition key + row key queries (<10ms)
- **Dual indexing**: Maintain bidirectional lookup tables for workflow dependencies
- **Batch operations**: Use batch insert/update for efficiency (up to 100 entities)

### OAuth Security

- **State parameter**: Always include state parameter for CSRF protection
- **PKCE**: Implement PKCE for public clients (future enhancement)
- **Token encryption**: Encrypt all tokens at rest using Fernet (AES-128)
- **Secure transmission**: Always use HTTPS for OAuth flows
- **Token scope**: Request minimum necessary scopes
- **Expiration handling**: Never use expired tokens, always refresh proactively

### Testing Strategy

- **Mock OAuth provider**: Create test OAuth server for integration tests
- **Encryption testing**: Test encryption/decryption with various token formats
- **Async testing**: Use `pytest-asyncio` for async function tests
- **Table Storage testing**: Use Azurite for local Table Storage testing
- **Contract testing**: Validate API request/response schemas
- **Integration testing**: Test end-to-end OAuth flows with mock providers

## Summary

All research completed with no unresolved questions. Design decisions align with constitutional principles:
- ✅ Azure-first (Functions, Table Storage, Key Vault)
- ✅ Table Storage only (no SQL databases)
- ✅ Python 3.11 with async/await
- ✅ Test-first development (contract + integration tests)
- ✅ Org-scoped with global fallback (matches config pattern)

Ready to proceed to Phase 1 (Data Model & Contracts).
