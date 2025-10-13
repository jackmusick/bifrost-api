# Data Model: Azure Functions Docker Runtime Migration

**Feature**: 005-migrate-to-azure | **Date**: 2025-01-13

This document defines the data entities for GitHub workspace synchronization and manual editing features.

## Entities

### GitHubConnection

Stores GitHub repository connection configuration for workspace synchronization.

**Storage**: Azure Table Storage
**Partition Strategy**: `PartitionKey = "GITHUB_CONNECTIONS"` (single entity per org or global)
**Row Key Strategy**: `RowKey = OrgId` or `"GLOBAL"` for MSP-wide connection

| Field               | Type     | Required | Description                           | Validation                                                      |
| ------------------- | -------- | -------- | ------------------------------------- | --------------------------------------------------------------- |
| PartitionKey        | string   | Yes      | Always "GITHUB_CONNECTIONS"           | Fixed value                                                     |
| RowKey              | string   | Yes      | Organization ID or "GLOBAL"           | Non-empty                                                       |
| RepositoryUrl       | string   | Yes      | GitHub repository clone URL           | Must be valid HTTPS URL (e.g., https://github.com/org/repo.git) |
| RepositoryBranch    | string   | Yes      | Branch to sync                        | Default: "main", non-empty                                      |
| WebhookSecret       | string   | Yes      | HMAC secret for webhook verification  | Stored encrypted in Key Vault, reference only                   |
| WebhookUrl          | string   | Yes      | Webhook endpoint URL                  | Generated after connection creation                             |
| PersonalAccessToken | string   | Yes      | GitHub PAT for repo access            | Stored encrypted in Key Vault, reference only                   |
| IsEnabled           | boolean  | Yes      | Whether sync is active                | Default: true                                                   |
| LastSyncCommitSha   | string   | No       | Last successfully synced commit SHA   | Updated after each sync                                         |
| LastSyncTimestamp   | datetime | No       | Last successful sync timestamp        | ISO 8601 format                                                 |
| LastSyncDurationMs  | int      | No       | Duration of last sync in milliseconds | Performance tracking                                            |
| LastSyncStatus      | string   | No       | Status of last sync                   | Values: "success", "failed", "partial"                          |
| LastSyncError       | string   | No       | Error message if last sync failed     | Null if success                                                 |
| CreatedAt           | datetime | Yes      | Connection creation timestamp         | ISO 8601 format                                                 |
| CreatedBy           | string   | Yes      | User ID who created connection        | MSP user ID                                                     |
| UpdatedAt           | datetime | Yes      | Last update timestamp                 | ISO 8601 format                                                 |

**Relationships**:

-   One-to-many with GitHubSyncJob (one connection has many sync jobs)
-   Belongs to Organization (via RowKey) or GLOBAL (MSP-wide)

**State Transitions**:

```
[Created] → IsEnabled=true, LastSyncCommitSha=null
    ↓
[First Sync] → LastSyncCommitSha=<sha>, LastSyncStatus="success"
    ↓
[Subsequent Syncs] → Updates LastSync* fields on each webhook
    ↓
[Disabled] → IsEnabled=false (manual edits now allowed)
    ↓
[Re-enabled] → IsEnabled=true (manual edits blocked)
    ↓
[Deleted] → Entity removed, workspace files remain
```

**Validation Rules**:

-   RepositoryUrl must be accessible with PersonalAccessToken
-   WebhookSecret must be minimum 32 characters (generated)
-   PersonalAccessToken must have `repo` scope (read-only)
-   Cannot enable connection if repository is unreachable
-   Cannot create duplicate connections for same OrgId/GLOBAL

**Queries**:

```python
# Get connection for organization
get_entity(PartitionKey="GITHUB_CONNECTIONS", RowKey=org_id)

# Get global connection (fallback)
get_entity(PartitionKey="GITHUB_CONNECTIONS", RowKey="GLOBAL")

# List all connections (admin view)
query_entities(filter="PartitionKey eq 'GITHUB_CONNECTIONS'")

# List enabled connections (for webhook processing)
query_entities(filter="PartitionKey eq 'GITHUB_CONNECTIONS' and IsEnabled eq true")
```

---

### GitHubSyncJob

Tracks individual sync operations triggered by GitHub webhooks.

**Storage**: Azure Table Storage
**Partition Strategy**: `PartitionKey = "SYNC_JOBS"`
**Row Key Strategy**: `RowKey = commit_sha` (idempotency key)

| Field              | Type     | Required | Description                         | Validation                                            |
| ------------------ | -------- | -------- | ----------------------------------- | ----------------------------------------------------- |
| PartitionKey       | string   | Yes      | Always "SYNC_JOBS"                  | Fixed value                                           |
| RowKey             | string   | Yes      | Git commit SHA (40-char hex)        | Exactly 40 hexadecimal characters                     |
| OrgId              | string   | Yes      | Organization ID or "GLOBAL"         | References GitHubConnection.RowKey                    |
| RepositoryUrl      | string   | Yes      | GitHub repository URL               | Matches GitHubConnection.RepositoryUrl                |
| Branch             | string   | Yes      | Branch that was pushed              | e.g., "main", "develop"                               |
| CommitMessage      | string   | Yes      | Commit message from GitHub          | Truncated to 500 chars                                |
| CommitAuthor       | string   | Yes      | GitHub username                     | From webhook payload                                  |
| CommitTimestamp    | datetime | Yes      | Commit timestamp from GitHub        | ISO 8601 format                                       |
| Status             | string   | Yes      | Job status                          | Values: "queued", "processing", "completed", "failed" |
| QueuedAt           | datetime | Yes      | When webhook received               | ISO 8601 format                                       |
| StartedAt          | datetime | No       | When sync processing started        | ISO 8601 format                                       |
| CompletedAt        | datetime | No       | When sync completed/failed          | ISO 8601 format                                       |
| DurationMs         | int      | No       | Processing duration in milliseconds | CompletedAt - StartedAt                               |
| FilesAdded         | int      | No       | Number of files added               | From rsync diff                                       |
| FilesModified      | int      | No       | Number of files modified            | From rsync diff                                       |
| FilesDeleted       | int      | No       | Number of files deleted             | From rsync diff                                       |
| TotalFiles         | int      | No       | Total files in workspace after sync | From Azure Files listing                              |
| ErrorMessage       | string   | No       | Error message if failed             | Null if success                                       |
| ErrorStackTrace    | string   | No       | Stack trace if failed               | For debugging, truncated to 5000 chars                |
| RetryCount         | int      | Yes      | Number of retry attempts            | Default: 0, max: 3                                    |
| WebhookPayloadHash | string   | Yes      | SHA256 of webhook payload           | For duplicate detection                               |

**Relationships**:

-   Belongs to GitHubConnection (via OrgId)
-   One-to-many with WorkflowReloadEvent (sync triggers workflow reload)

**State Transitions**:

```
[Webhook Received] → Status="queued", QueuedAt=now
    ↓
[Dequeued] → Status="processing", StartedAt=now
    ↓
[Success] → Status="completed", CompletedAt=now, Files* populated
    OR
[Failure] → Status="failed", CompletedAt=now, ErrorMessage populated
    ↓
[Retry] → Status="queued", RetryCount++  (if RetryCount < 3)
```

**Validation Rules**:

-   RowKey (CommitSha) must be unique (idempotency)
-   Status transitions must follow state diagram
-   DurationMs must be positive
-   Files\* counts must be non-negative
-   RetryCount must not exceed 3

**Queries**:

```python
# Check if commit already processed (idempotency)
get_entity(PartitionKey="SYNC_JOBS", RowKey=commit_sha)

# Get recent sync jobs for organization
query_entities(
    filter=f"PartitionKey eq 'SYNC_JOBS' and OrgId eq '{org_id}'",
    select=["RowKey", "Status", "QueuedAt", "CompletedAt"],
    top=20,
    order_by="QueuedAt desc"
)

# Get failed jobs for retry
query_entities(
    filter="PartitionKey eq 'SYNC_JOBS' and Status eq 'failed' and RetryCount lt 3"
)

# Performance metrics (last 100 syncs)
query_entities(
    filter="PartitionKey eq 'SYNC_JOBS' and Status eq 'completed'",
    select=["DurationMs", "FilesAdded", "FilesModified", "FilesDeleted"],
    top=100,
    order_by="CompletedAt desc"
)
```

---

### WorkspaceFile (Virtual Entity)

Represents files in Azure Files `/workspace` share. Not stored in Table Storage - this is a logical entity for API contracts.

**Storage**: Azure Files share `workspaces`
**Access Pattern**: Direct file operations via azure-storage-file-share SDK

| Field        | Type         | Required | Description                        | Validation                        |
| ------------ | ------------ | -------- | ---------------------------------- | --------------------------------- |
| Path         | string       | Yes      | Relative path from /workspace root | Forward slashes, no leading slash |
| Content      | bytes/string | Yes      | File content                       | Max 10MB per spec assumptions     |
| ContentType  | string       | No       | MIME type                          | Inferred from extension           |
| Size         | int          | Yes      | File size in bytes                 | Positive integer                  |
| LastModified | datetime     | Yes      | Last modification timestamp        | ISO 8601 format                   |
| IsDirectory  | boolean      | Yes      | Whether this is a directory        | true/false                        |
| ETag         | string       | Yes      | Azure Files ETag for concurrency   | Used for conditional updates      |

**Operations**:

-   **List**: `ShareClient.list_directories_and_files()` (recursive walker)
-   **Read**: `FileClient.download_file()`
-   **Create**: `FileClient.upload_file()` (creates parent dirs if needed)
-   **Update**: `FileClient.upload_file()` (overwrites existing)
-   **Delete**: `FileClient.delete_file()`

**Validation Rules**:

-   Path must not contain `..` (directory traversal prevention)
-   Path must not start with `/` (relative paths only)
-   Content must be valid UTF-8 for text files (Python, YAML, JSON)
-   Size must not exceed 10MB (per spec assumption)
-   Filename must not contain invalid characters: `< > : " | ? * \`

**Access Control**:

-   When GitHubConnection.IsEnabled=true → Read-only (UI enforced)
-   When GitHubConnection.IsEnabled=false → Full CRUD (MSP users only)
-   ORG users: No access (workspace editing is MSP-only)

---

## Entity Relationship Diagram

```
┌─────────────────────┐
│  GitHubConnection   │
│  PK: "GITHUB_CONN"  │
│  RK: OrgId/GLOBAL   │
└──────────┬──────────┘
           │ 1
           │
           │ *
┌──────────┴──────────┐
│   GitHubSyncJob     │
│  PK: "SYNC_JOBS"    │
│  RK: CommitSha      │
└──────────┬──────────┘
           │ 1
           │
           │ * (triggers)
┌──────────┴──────────┐
│   WorkspaceFile     │
│  (Azure Files)      │
│  Path: /workspace/ │
└─────────────────────┘
```

---

## Data Access Patterns

### Pattern 1: Webhook Processing (GitHub → Azure Files)

1. Webhook received → Verify HMAC signature
2. Check GitHubSyncJob.RowKey=CommitSha → If exists and Status="completed", return 200 (idempotent)
3. Create GitHubSyncJob entity with Status="queued"
4. Queue sync job to Azure Queue
5. Worker picks up job → Update Status="processing"
6. Execute rsync logic → Update WorkspaceFile entities
7. Update GitHubSyncJob with Status="completed", Files\* counts
8. Reload workflows (trigger workflow engine reload)

### Pattern 2: Manual Editing (UI → Azure Files)

1. Check GitHubConnection.IsEnabled → If true, return 403 (read-only mode)
2. Validate user has MSP role (ORG users cannot edit)
3. Execute file operation (create/update/delete) on WorkspaceFile
4. Return success with updated file metadata
5. Reload workflows immediately (FR-015)

### Pattern 3: Download Workspace as ZIP (UI → Azure Files)

1. Check user has access to organization
2. List all WorkspaceFile entities in /workspace
3. Create in-memory ZIP with zipfile.ZipFile
4. Stream ZIP to HTTP response with Content-Disposition header
5. Return 200 with application/zip MIME type

### Pattern 4: Connection Status Check (UI → Table Storage)

1. Query GitHubConnection by OrgId (or fallback to GLOBAL)
2. If not found, return null (no connection)
3. Return connection details with IsEnabled, LastSync\* fields
4. UI shows "Connected to GitHub" or "Manual Mode" based on IsEnabled

---

## Migration Strategy

This feature adds new entities without modifying existing ones.

**New Tables**:

-   None (entities use existing Tables with new PartitionKeys)

**New Partitions**:

-   `GITHUB_CONNECTIONS` in existing Organizations/Config table
-   `SYNC_JOBS` in existing Logs/Jobs table

**New Azure Files Shares**:

-   `workspaces` (Hot tier, user-configurable quota)
-   `tmp` (Hot tier, user-configurable quota)

**Data Population**:

-   GitHubConnection: Created by administrators via UI (no seed data)
-   GitHubSyncJob: Populated automatically by webhooks (no seed data)
-   WorkspaceFile: Populated by first GitHub sync OR manual upload (no seed data)

**Backward Compatibility**:

-   Existing workflows continue to run (read from /workspace if mounted, otherwise from deployment package)
-   Existing Table Storage entities unchanged (different PartitionKeys)
-   Existing API endpoints unchanged (new endpoints added)

---

## Performance Considerations

### Table Storage Queries

**GitHubConnection queries**:

-   Single entity retrieval by OrgId: O(1), <5ms
-   List all connections (admin): O(N), ~10ms for 200 orgs

**GitHubSyncJob queries**:

-   Idempotency check by CommitSha: O(1), <5ms
-   Recent syncs for org: O(N), ~20ms for last 100 syncs
-   Failed jobs for retry: O(N), ~30ms (full table scan, rare operation)

**Optimization**:

-   Use `select` parameter to fetch only required fields
-   Use `top` parameter to limit results (pagination)
-   Cache GitHubConnection entities (5-minute TTL, low change frequency)

### Azure Files Operations

**WorkspaceFile operations**:

-   List files recursively: O(N), ~50ms for 1000 files (Hot tier, same region)
-   Read single file: O(1), ~10ms for 100KB file
-   Write single file: O(1), ~15ms for 100KB file
-   Delete single file: O(1), ~10ms

**Rsync sync operations**:

-   Full workspace sync (1000 files, 50% modified): ~30s
    -   Clone GitHub repo: ~5s (shallow clone)
    -   Build file trees: ~5s (local + Azure Files listing)
    -   Compute diff: ~1s (hash comparison)
    -   Apply changes: ~20s (500 uploads in parallel, 10 concurrent)

**ZIP download**:

-   Generate ZIP (50MB workspace): ~10s
    -   List files: ~50ms
    -   Download all files: ~5s (parallel downloads)
    -   ZIP compression: ~5s (in-memory)
-   Memory usage: ~100MB (50MB workspace + 50MB ZIP buffer)

**Optimization**:

-   Parallel file uploads (asyncio.gather, limit=10)
-   Parallel file downloads for ZIP (asyncio.gather, limit=20)
-   SHA256 hashing for content comparison (avoid re-uploading unchanged files)
-   Skip hidden files (.git/, .github/) in rsync

---

## Security Considerations

### Secret Storage

**Sensitive fields** (stored in Key Vault, not Table Storage):

-   GitHubConnection.WebhookSecret → Key Vault secret: `github-webhook-secret-{orgId}`
-   GitHubConnection.PersonalAccessToken → Key Vault secret: `github-pat-{orgId}`

**Table Storage entities** store Key Vault references only:

```python
GitHubConnection.WebhookSecretRef = "github-webhook-secret-orgabc123"
GitHubConnection.PersonalAccessTokenRef = "github-pat-orgabc123"
```

**Access pattern**:

```python
# Load secret from Key Vault at runtime
secret_client = SecretClient(vault_url, credential)
webhook_secret = secret_client.get_secret(connection.WebhookSecretRef).value
```

### Access Control

**GitHubConnection**:

-   Create/Update/Delete: MSP users only (admin role)
-   Read: MSP users only (view settings)
-   ORG users: No access

**GitHubSyncJob**:

-   Create: Webhook endpoint (HMAC-verified)
-   Read: MSP users only (view sync history)
-   Update: System only (sync worker)
-   ORG users: No access

**WorkspaceFile**:

-   Create/Update/Delete: MSP users only, IF GitHubConnection.IsEnabled=false
-   Read: MSP users only (view code)
-   ORG users: No access (workspace editing is MSP-only feature)

### HMAC Verification

**GitHub webhook signature**:

```python
# Verify X-Hub-Signature-256 header
signature = req.headers.get('X-Hub-Signature-256')  # "sha256=..."
body = req.get_body()
expected = hmac.new(webhook_secret.encode(), body, hashlib.sha256).hexdigest()

if not hmac.compare_digest(signature, f"sha256={expected}"):
    return HttpResponse("Unauthorized", status_code=401)
```

**Timing-attack resistance**:

-   Use `hmac.compare_digest()` (constant-time comparison)
-   Never log or return partial signature matches

---

## Example Entities

### GitHubConnection (GLOBAL)

```json
{
    "PartitionKey": "GITHUB_CONNECTIONS",
    "RowKey": "GLOBAL",
    "RepositoryUrl": "https://github.com/msp-org/workflows.git",
    "RepositoryBranch": "main",
    "WebhookSecretRef": "github-webhook-secret-global",
    "WebhookUrl": "https://functions.azurewebsites.net/api/github-webhook",
    "PersonalAccessTokenRef": "github-pat-global",
    "IsEnabled": true,
    "LastSyncCommitSha": "a1b2c3d4e5f6...",
    "LastSyncTimestamp": "2025-01-13T10:30:00Z",
    "LastSyncDurationMs": 25000,
    "LastSyncStatus": "success",
    "LastSyncError": null,
    "CreatedAt": "2025-01-10T08:00:00Z",
    "CreatedBy": "user-12345",
    "UpdatedAt": "2025-01-13T10:30:00Z"
}
```

### GitHubSyncJob (Completed)

```json
{
    "PartitionKey": "SYNC_JOBS",
    "RowKey": "a1b2c3d4e5f6789012345678901234567890abcd",
    "OrgId": "GLOBAL",
    "RepositoryUrl": "https://github.com/msp-org/workflows.git",
    "Branch": "main",
    "CommitMessage": "Add new workflow for ticket automation",
    "CommitAuthor": "dev-user",
    "CommitTimestamp": "2025-01-13T10:25:00Z",
    "Status": "completed",
    "QueuedAt": "2025-01-13T10:25:30Z",
    "StartedAt": "2025-01-13T10:25:35Z",
    "CompletedAt": "2025-01-13T10:26:00Z",
    "DurationMs": 25000,
    "FilesAdded": 2,
    "FilesModified": 5,
    "FilesDeleted": 1,
    "TotalFiles": 156,
    "ErrorMessage": null,
    "ErrorStackTrace": null,
    "RetryCount": 0,
    "WebhookPayloadHash": "sha256:9f3b2..."
}
```

### WorkspaceFile (Azure Files)

```python
# Not stored as entity - this is Azure Files SDK representation
{
  "Path": "workflows/tickets/create_ticket.py",
  "Content": b"import requests\n\ndef create_ticket(...",
  "ContentType": "text/x-python",
  "Size": 1024,
  "LastModified": "2025-01-13T10:26:00Z",
  "IsDirectory": false,
  "ETag": "\"0x8DCB1234567890\""
}
```
