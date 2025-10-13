# Data Model: OAuth Helper for Integrations and Workflows

**Date**: 2025-10-12
**Phase**: 1 (Data Model & Contracts)

## Overview

This document defines all data entities, their storage schemas, validation rules, and relationships for the OAuth helper feature.

## Storage Strategy

All data stored in Azure Table Storage following constitutional principles:
- **Partition Key**: OrgId for org-scoped entities, "GLOBAL" for MSP-level entities
- **Row Key**: Entity identifier (connection_name, workflow_id, etc.)
- **Dual Indexing**: Used for bidirectional lookups (workflow↔connection dependencies)

## Entity Definitions

### 1. OAuth Connection Configuration

**Purpose**: Stores OAuth connection configuration and current token state

**Table**: `OAuthConnections`

**Storage Schema**:
```python
PartitionKey: str  # OrgId or "GLOBAL"
RowKey: str        # connection_name (unique within partition)

# Connection Configuration
connection_name: str           # Display name and identifier
oauth_flow_type: str          # "authorization_code" | "client_credentials" | "refresh_token"
client_id: str                # OAuth client ID (unencrypted - not sensitive)
client_secret_ref: str        # Reference to secret: "{connection_name}_client_secret"
oauth_response_ref: str       # Reference to secret: "{connection_name}_oauth_response"
authorization_url: str        # OAuth provider authorization endpoint
token_url: str                # OAuth provider token endpoint
scopes: str                   # Comma-separated list of requested scopes
redirect_uri: str             # Callback URL: "/api/oauth/callback/{connection_name}"

# OAuth Response Metadata (for quick access, actual tokens in secrets)
token_type: str               # Usually "Bearer"
expires_at: str               # ISO 8601 datetime when access token expires (copied from secret)

# Connection Status
status: str                   # "not_connected" | "waiting_callback" | "testing" | "completed" | "failed"
status_message: str           # Descriptive message (especially for failures)
last_refresh_at: str          # ISO 8601 datetime of last successful token refresh
last_test_at: str             # ISO 8601 datetime of last connection test

# Metadata
created_at: str               # ISO 8601 datetime
created_by: str               # User ID who created connection
updated_at: str               # ISO 8601 datetime
```

**Pydantic Model**:
```python
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class OAuthConnection(BaseModel):
    # Partition/Row Keys
    org_id: str = Field(..., description="Organization ID or 'GLOBAL'")
    connection_name: str = Field(..., min_length=1, max_length=100, pattern="^[a-zA-Z0-9_-]+$")

    # Configuration
    oauth_flow_type: Literal["authorization_code", "client_credentials", "refresh_token"]
    client_id: str = Field(..., min_length=1)
    client_secret_ref: str  # Auto-generated: f"{connection_name}_client_secret"
    oauth_response_ref: str  # Auto-generated: f"{connection_name}_oauth_response"
    authorization_url: str = Field(..., regex="^https://")
    token_url: str = Field(..., regex="^https://")
    scopes: str = Field(default="", description="Comma-separated scopes")
    redirect_uri: str  # Auto-generated: f"/api/oauth/callback/{connection_name}"

    # Tokens (loaded from secret system when needed)
    access_token: Optional[str] = None  # Not stored in Table Storage
    refresh_token: Optional[str] = None  # Not stored in Table Storage
    token_type: str = "Bearer"
    expires_at: Optional[datetime] = None  # Copied from secret for quick expiry checks

    # Status
    status: Literal["not_connected", "waiting_callback", "testing", "completed", "failed"]
    status_message: Optional[str] = None
    last_refresh_at: Optional[datetime] = None
    last_test_at: Optional[datetime] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def is_expired(self) -> bool:
        """Check if access token is expired."""
        if not self.expires_at:
            return True
        return datetime.utcnow() >= self.expires_at

    def expires_soon(self, hours: int = 4) -> bool:
        """Check if access token expires within specified hours."""
        if not self.expires_at:
            return True
        threshold = datetime.utcnow() + timedelta(hours=hours)
        return self.expires_at <= threshold
```

**Validation Rules**:
- `connection_name`: Alphanumeric, underscores, hyphens only (unique within partition)
- `oauth_flow_type`: Must be one of three supported flow types
- `authorization_url`, `token_url`: Must be HTTPS URLs
- `scopes`: Optional, comma-separated list
- `status`: Must transition through valid states (see state machine below)
- `expires_at`: Must be future datetime when status is "completed"

**State Machine**:
```
not_connected → waiting_callback → testing → completed
                                           ↓
                                         failed
                                           ↑
                                    [any state on error]
```

**Access Patterns**:
- Get by name: `PartitionKey = OrgId, RowKey = connection_name` (point query, <10ms)
- List all for org: `PartitionKey = OrgId` (partition scan)
- List global: `PartitionKey = "GLOBAL"` (partition scan)
- Find expiring: Scan all + filter `expires_at < now + 4 hours` (scheduled job only)

---

### 2. Workflow OAuth Dependency (Primary Index)

**Purpose**: Track which workflows use which OAuth connections (enables "find workflows using connection X")

**Table**: `WorkflowOAuthDependencies`

**Storage Schema**:
```python
PartitionKey: str  # connection_name (enables fast lookup by connection)
RowKey: str        # workflow_id

connection_name: str
workflow_id: str
org_id: str              # Which org this workflow belongs to
workflow_name: str       # Display name for UI
registered_at: str       # ISO 8601 datetime when dependency registered
last_accessed_at: str    # ISO 8601 datetime when workflow last retrieved credentials
```

**Pydantic Model**:
```python
class WorkflowOAuthDependency(BaseModel):
    connection_name: str = Field(..., min_length=1)
    workflow_id: str = Field(..., min_length=1)
    org_id: str
    workflow_name: str = Field(default="")
    registered_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed_at: Optional[datetime] = None
```

**Access Patterns**:
- Find workflows using connection: `PartitionKey = connection_name` (partition scan)
- Check specific dependency: `PartitionKey = connection_name, RowKey = workflow_id` (point query)

---

### 3. Workflow OAuth Dependency (Reverse Index)

**Purpose**: Track which OAuth connections a workflow uses (enables "find connections used by workflow X")

**Table**: `WorkflowOAuthDependencies_ByWorkflow`

**Storage Schema**:
```python
PartitionKey: str  # workflow_id (enables fast lookup by workflow)
RowKey: str        # connection_name

# Same fields as primary index
connection_name: str
workflow_id: str
org_id: str
workflow_name: str
registered_at: str
last_accessed_at: str
```

**Pydantic Model**: Same as `WorkflowOAuthDependency`

**Access Patterns**:
- Find connections used by workflow: `PartitionKey = workflow_id` (partition scan)
- Check specific dependency: `PartitionKey = workflow_id, RowKey = connection_name` (point query)

**Dual Index Maintenance**:
- On register: Insert into both `WorkflowOAuthDependencies` and `WorkflowOAuthDependencies_ByWorkflow`
- On unregister: Delete from both tables
- Keep both indexes synchronized

---

### 4. Workflow Disable State

**Purpose**: Track disabled workflows and reason for disabling

**Table**: `WorkflowDisableState`

**Storage Schema**:
```python
PartitionKey: str  # org_id or "GLOBAL"
RowKey: str        # workflow_id

workflow_id: str
org_id: str
is_disabled: bool            # True if disabled, False if enabled
disabled_reason: str         # "oauth_connection_deleted" | "manual" | "other"
disabled_at: str             # ISO 8601 datetime when disabled
disabled_by: str             # User ID who disabled (or "system")
related_oauth_connection: str  # Optional: connection name that triggered disable
enabled_at: str              # ISO 8601 datetime when re-enabled (if applicable)
enabled_by: str              # User ID who re-enabled
```

**Pydantic Model**:
```python
class WorkflowDisableState(BaseModel):
    workflow_id: str = Field(..., min_length=1)
    org_id: str
    is_disabled: bool = True
    disabled_reason: Literal["oauth_connection_deleted", "manual", "other"]
    disabled_at: datetime = Field(default_factory=datetime.utcnow)
    disabled_by: str
    related_oauth_connection: Optional[str] = None
    enabled_at: Optional[datetime] = None
    enabled_by: Optional[str] = None
```

**Validation Rules**:
- `workflow_id`: Required, non-empty
- `disabled_reason`: Must be one of valid reasons
- `disabled_by`: Required, user ID or "system"
- `related_oauth_connection`: Required if `disabled_reason == "oauth_connection_deleted"`

**Access Patterns**:
- Check if workflow disabled: `PartitionKey = org_id, RowKey = workflow_id` (point query)
- List all disabled workflows: `PartitionKey = org_id` + filter `is_disabled == True` (partition scan)
- Find workflows disabled by connection: Scan + filter `related_oauth_connection == connection_name`

---

### 5. OAuth Callback Event (Audit Log)

**Purpose**: Log all OAuth callback events for debugging and audit

**Table**: `OAuthCallbackEvents`

**Storage Schema**:
```python
PartitionKey: str  # connection_name (groups events by connection)
RowKey: str        # timestamp_uuid (sortable, unique)

connection_name: str
callback_timestamp: str      # ISO 8601 datetime
event_id: str                # UUID for unique identification
org_id: str                  # Which org initiated callback
authorization_code: str      # OAuth authorization code (optional, for debugging)
state_parameter: str         # OAuth state parameter
state_valid: bool            # Whether state validation passed
exchange_success: bool       # Whether token exchange succeeded
error_message: str           # Error message if exchange failed
tokens_received: bool        # Whether tokens were received
test_result: str             # "success" | "failed" | "skipped"
final_status: str            # Final connection status after processing
processing_duration_ms: int  # How long callback processing took
```

**Pydantic Model**:
```python
class OAuthCallbackEvent(BaseModel):
    connection_name: str
    callback_timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    org_id: str
    authorization_code: Optional[str] = None  # Don't log in production
    state_parameter: str
    state_valid: bool
    exchange_success: bool
    error_message: Optional[str] = None
    tokens_received: bool
    test_result: Literal["success", "failed", "skipped"]
    final_status: str
    processing_duration_ms: int
```

**Access Patterns**:
- Get callbacks for connection: `PartitionKey = connection_name` (partition scan, ordered by RowKey)
- Get specific callback: `PartitionKey = connection_name, RowKey = timestamp_uuid` (point query)

**Retention**: Consider adding TTL (Time To Live) to auto-delete old events after 90 days

---

## Relationships

```
OAuthConnection (1) ←→ (many) WorkflowOAuthDependency
  ↓
  One connection can be used by many workflows
  One workflow can use many connections (tracked via dual index)

OAuthConnection (1) ←→ (many) OAuthCallbackEvent
  ↓
  One connection has many callback events (audit trail)

WorkflowOAuthDependency (1) → (0..1) WorkflowDisableState
  ↓
  When connection deleted, workflows are disabled
  Disable state references the connection that triggered disable
```

## Secret Storage Details

**Sensitive Data Storage**: ALL sensitive OAuth data stored via existing secret system

**Secret References**:
- `client_secret_ref`: Points to `{connection_name}_client_secret` in secret system
- `oauth_response_ref`: Points to `{connection_name}_oauth_response` in secret system

**OAuth Response Secret Format** (JSON string):
```json
{
  "access_token": "ya29.a0AfH6...",
  "refresh_token": "1//0gKx...",
  "token_type": "Bearer",
  "expires_at": "2025-10-12T15:30:00Z",
  "scopes": "user.read,mail.send"
}
```

**Secret Operations**:
```python
# Store client secret (on connection creation)
await set_secret(f"{connection_name}_client_secret", client_secret, org_id)

# Store OAuth response (on callback or refresh)
oauth_data = {
    "access_token": access_token,
    "refresh_token": refresh_token,
    "token_type": "Bearer",
    "expires_at": expires_at.isoformat(),
    "scopes": scopes
}
await set_secret(f"{connection_name}_oauth_response", json.dumps(oauth_data), org_id)

# Retrieve OAuth credentials (in workflow)
oauth_json = await get_secret(f"{connection_name}_oauth_response", org_id)
oauth_data = json.loads(oauth_json)
access_token = oauth_data["access_token"]
```

**Benefits**:
- Encryption handled by existing secret system (Azure Key Vault backend)
- Org-scoping automatically managed by secret system
- No separate encryption key management needed
- Consistent with platform pattern for all sensitive data

## Validation Summary

| Entity | Key Validations |
|--------|----------------|
| OAuthConnection | connection_name format, HTTPS URLs, valid flow type, status transitions |
| WorkflowOAuthDependency | Non-empty IDs, dual-index consistency |
| WorkflowDisableState | Valid reason, disabled_by required, related_connection required if oauth_deleted |
| OAuthCallbackEvent | Valid UUIDs, boolean flags, consistent state |

## Performance Considerations

**Query Performance**:
- All primary lookups are point queries: <10ms latency
- Partition scans (list operations) typically <50ms for <100 entities
- Dual indexing enables fast bidirectional lookups without table scans

**Write Performance**:
- Single entity writes: <20ms
- Dual-index writes (2 entities): <40ms
- Batch operations for token refresh: Process up to 100 connections in parallel

**Storage Costs**:
- Estimated 100 OAuth connections: ~$0.01/month
- Estimated 1000 callback events/month: ~$0.01/month
- Estimated 500 workflow dependencies: ~$0.01/month
- Total: <$0.05/month for Table Storage

## Migration Strategy

**Initial Setup**:
1. Tables auto-created on first write (Azure Table Storage feature)
2. No schema migrations needed (schemaless storage)
3. Encryption key created in Key Vault during deployment

**Future Schema Changes**:
- Add fields: No migration needed, new fields optional
- Remove fields: No migration needed, ignore old fields on read
- Rename fields: Write both old and new fields during transition period

## Summary

Data model complete with:
- ✅ 5 entities defined with full schemas
- ✅ Pydantic models for type safety
- ✅ Validation rules documented
- ✅ Access patterns optimized for <10ms queries
- ✅ Dual indexing for bidirectional lookups
- ✅ Encryption strategy defined
- ✅ Relationships mapped
- ✅ Constitutional compliance (Table Storage only, org-scoped partitioning)

Ready to proceed to API contract generation.
