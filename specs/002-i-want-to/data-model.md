# Data Model: Workflow Engine and User Code Separation

**Feature**: 002-i-want-to
**Date**: 2025-10-12
**Status**: Complete

## Overview

This feature primarily involves code reorganization and security mechanisms rather than new data entities. Existing data models are reused with minor extensions for audit logging.

## Existing Entities (No Changes)

### Organizations
**Table**: `Organizations`
**Purpose**: Stores client organization records
**Usage**: Unchanged - org context loading continues to use existing schema

| Field | Type | Description |
|-------|------|-------------|
| PartitionKey | string | "ORG" |
| RowKey | string | Organization ID (GUID) |
| Name | string | Organization display name |
| TenantId | string | Microsoft 365 tenant ID (optional) |
| IsActive | bool | Whether org is active |
| CreatedAt | datetime | Creation timestamp |
| CreatedBy | string | User who created org |
| UpdatedAt | datetime | Last update timestamp |

### Users
**Table**: `Users`
**Purpose**: Stores platform and organization users
**Usage**: Unchanged - authentication continues to use existing schema

| Field | Type | Description |
|-------|------|-------------|
| PartitionKey | string | "USER" |
| RowKey | string | User ID (email) |
| Email | string | User email address |
| DisplayName | string | User display name |
| UserType | string | "PLATFORM" or "ORG" |
| IsPlatformAdmin | bool | Whether user is platform admin |
| IsActive | bool | Whether user is active |
| LastLogin | datetime | Last login timestamp |
| CreatedAt | datetime | Creation timestamp |

### OrgConfig
**Table**: `OrgConfig`
**Purpose**: Stores organization-specific and global configuration
**Usage**: Unchanged - workspace code accesses config through context object

| Field | Type | Description |
|-------|------|-------------|
| PartitionKey | string | Organization ID or "GLOBAL" |
| RowKey | string | "config:{key}" |
| Value | string | Configuration value |
| Type | string | "string", "int", "bool", "json", "secret_ref" |
| Description | string | Config description (optional) |
| UpdatedAt | datetime | Last update timestamp |
| UpdatedBy | string | User who last updated |

## New Entities

### AuditLog (NEW)
**Table**: `AuditLog`
**Purpose**: Structured audit trail for privileged operations (function key usage, cross-org access)
**Partitioning Strategy**: By date for efficient time-range queries

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| PartitionKey | string | Date in format "YYYY-MM-DD" | Yes |
| RowKey | string | `{reverse_timestamp}_{event_id}` | Yes |
| EventType | string | "function_key_access", "cross_org_access", "engine_violation_attempt" | Yes |
| Timestamp | datetime | Event timestamp (UTC) | Yes |
| KeyId | string | Function key ID (if applicable) | No |
| KeyName | string | Function key name (if applicable) | No |
| UserId | string | User ID (if applicable) | No |
| OrgId | string | Target organization ID | No |
| Endpoint | string | API endpoint accessed | Yes |
| Method | string | HTTP method (GET, POST, etc.) | Yes |
| RemoteAddr | string | Client IP address | Yes |
| UserAgent | string | Client user agent | Yes |
| StatusCode | int | HTTP response status code | Yes |
| Details | string | JSON with additional context | No |

**Indexes**:
- Primary: PartitionKey (date) + RowKey (reverse timestamp + ID) - enables efficient time-range queries
- Query patterns:
  - All events for date: `PartitionKey eq '2025-10-12'`
  - Events in date range: `PartitionKey ge '2025-10-01' and PartitionKey le '2025-10-31'`
  - Specific event type: `PartitionKey eq '2025-10-12' and EventType eq 'function_key_access'`

**Retention**: 90 days (implement TTL via background cleanup job)

**Example Entities**:

```json
{
  "PartitionKey": "2025-10-12",
  "RowKey": "9999999999999_abc123-def456",
  "EventType": "function_key_access",
  "Timestamp": "2025-10-12T14:30:45.123Z",
  "KeyId": "default",
  "KeyName": "ci-cd-pipeline",
  "OrgId": "test-org-1",
  "Endpoint": "/api/workflows/user-onboarding",
  "Method": "POST",
  "RemoteAddr": "203.0.113.42",
  "UserAgent": "curl/7.68.0",
  "StatusCode": 200,
  "Details": "{\"duration_ms\": 234, \"workflow_result\": \"success\"}"
}
```

```json
{
  "PartitionKey": "2025-10-12",
  "RowKey": "9999999998888_xyz789-uvw012",
  "EventType": "cross_org_access",
  "Timestamp": "2025-10-12T15:45:12.567Z",
  "UserId": "jack@gocovi.com",
  "OrgId": "client-org-789",
  "Endpoint": "/api/workflows/metadata",
  "Method": "GET",
  "RemoteAddr": "198.51.100.15",
  "UserAgent": "Mozilla/5.0 ...",
  "StatusCode": 200,
  "Details": "{\"user_type\": \"PLATFORM\", \"is_platform_admin\": true, \"reason\": \"support_ticket_12345\"}"
}
```

## Runtime Objects (Not Persisted)

### WorkspaceImportRestrictor
**Type**: Python object (in-memory)
**Purpose**: Meta path finder that blocks workspace→engine imports
**Lifecycle**: Created at Azure Functions startup, exists for function app lifetime

**Properties**:
- `BLOCKED_PREFIXES`: Tuple of blocked import prefixes (`engine.`, `shared.`)
- `ALLOWED_SHARED_EXPORTS`: Set of whitelisted shared modules
- `workspace_paths`: List of absolute paths considered workspace code

**Methods**:
- `find_spec(fullname, path, target)`: Called by Python import system, returns None (allow) or raises ImportError (block)

### FunctionKeyPrincipal
**Type**: Python dataclass (in-memory)
**Purpose**: Represents authenticated principal via function key
**Lifecycle**: Created per request, exists for request lifetime

**Properties**:
- `auth_type`: "function_key"
- `key_id`: Function key identifier
- `key_name`: Friendly key name

### UserPrincipal
**Type**: Python dataclass (in-memory)
**Purpose**: Represents authenticated user via Easy Auth
**Lifecycle**: Created per request, exists for request lifetime

**Properties**:
- `auth_type`: "user"
- `user_id`: User ID from Entra ID
- `email`: User email address
- `name`: User display name
- `identity_provider`: "aad"
- `roles`: List of assigned roles

## State Transitions

### Audit Log Lifecycle

```
[Event Occurs]
    ↓
[Create AuditLog entity with current date PartitionKey]
    ↓
[Insert into AuditLog table]
    ↓
[Log to Application Insights (real-time monitoring)]
    ↓
[TTL Cleanup after 90 days]
```

### Import Restriction Lifecycle

```
[Azure Function Starts]
    ↓
[Install WorkspaceImportRestrictor on sys.meta_path]
    ↓
[Workspace Code Imports Module]
    ↓
[find_spec() checks import name]
    ↓
[If blocked + from workspace → raise ImportError]
[If allowed → return None, continue import]
```

### Authentication Flow

```
[HTTP Request Arrives]
    ↓
[Extract x-functions-key header/param]
    ↓ (if present)
[Create FunctionKeyPrincipal] → [Log audit event] → [Attach to request]
    ↓ (if not present)
[Extract x-ms-client-principal header]
    ↓ (if present)
[Decode Base64 → Parse JSON] → [Create UserPrincipal] → [Attach to request]
    ↓ (if not present)
[Return 403 Forbidden]
```

## Validation Rules

### AuditLog Constraints

- `PartitionKey`: Must match format `YYYY-MM-DD`
- `RowKey`: Must be unique (reverse timestamp ensures chronological sorting)
- `EventType`: Must be one of predefined event types
- `Timestamp`: Must be valid ISO 8601 datetime
- `RemoteAddr`: Should be valid IP address (IPv4 or IPv6)
- `StatusCode`: Must be valid HTTP status code (100-599)

### Runtime Validation

**Import Restrictions**:
- Workspace path must be absolute
- Blocked prefixes must not overlap with allowed exports
- Import name must be fully qualified module path

**Authentication**:
- Function key: No format validation (Azure validates)
- X-MS-CLIENT-PRINCIPAL: Must be valid Base64-encoded JSON with userId field
- Organization ID: Must exist in Organizations table and have IsActive=true

## Relationships

```
AuditLog
  ├── References: Organizations (OrgId → RowKey)
  ├── References: Users (UserId → RowKey)
  └── Queried by: Date range, Event type, Organization, User

WorkspaceImportRestrictor
  ├── Protects: /engine/* modules
  ├── Allows: /workspace/* modules
  └── Whitelists: shared.decorators, shared.context, shared.error_handling, shared.models

FunctionKeyPrincipal / UserPrincipal
  ├── Attached to: HttpRequest.principal
  ├── Used by: OrganizationContext loading
  └── Logged in: AuditLog table
```

## Migration Notes

**No database migrations required**. This feature:
- Reuses existing Organizations, Users, OrgConfig tables
- Adds new AuditLog table (create on first use, non-blocking)
- Does not modify existing table schemas
- Does not require data migration

**AuditLog Table Creation**:
```python
# In shared/init_tables.py or equivalent
from azure.data.tables import TableServiceClient

def ensure_audit_log_table():
    """Create AuditLog table if it doesn't exist."""
    service = TableServiceClient.from_connection_string(CONNECTION_STRING)
    try:
        service.create_table("AuditLog")
    except ResourceExistsError:
        pass  # Table already exists
```

## Summary

This feature introduces minimal new data entities:
- **AuditLog table**: Structured audit trail for privileged operations
- **Runtime objects**: In-memory Python objects for authentication and import restrictions

Existing entity schemas (Organizations, Users, OrgConfig) remain unchanged. No data migration required.
