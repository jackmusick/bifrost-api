# Data Model: Browser-Based Code Editor

**Feature**: Browser-Based Code Editor
**Date**: 2025-10-23
**Status**: Completed

This document defines all entities used in the browser-based code editor feature.

## Storage Overview

- **Azure Table Storage**: Session locks
- **Azure File Share**: File contents at `/home/repo`
- **Azure Blob Storage**: Large execution logs (>32KB)

## Entities

### 1. WorkspaceSession (Table Storage)

**Purpose**: Prevent concurrent access to the same workspace by multiple users.

**Table**: `WorkspaceSessions`

**Partition Strategy**: `PartitionKey = OrgId` (org-scoped for multi-tenancy)

**Entity Schema**:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| PartitionKey | string | Organization ID | `org_123` |
| RowKey | string | User ID + workspace identifier | `user_456_workspace` |
| UserId | string | ID of user holding the lock | `user_456` |
| UserEmail | string | Email for display in "locked by" messages | `john@example.com` |
| AcquiredAt | datetime | When lock was first acquired | `2025-10-23T14:30:00Z` |
| LastHeartbeat | datetime | Last heartbeat update | `2025-10-23T14:35:00Z` |
| ExpiresAt | datetime | When lock expires (LastHeartbeat + 5min) | `2025-10-23T14:40:00Z` |
| SessionId | string (UUID) | Unique session identifier | `550e8400-e29b-41d4-a716-446655440000` |

**Validation Rules**:
- ExpiresAt MUST be LastHeartbeat + 5 minutes
- LastHeartbeat MUST be updated at least every 30 seconds
- SessionId MUST be unique per lock acquisition

**State Transitions**:
1. **Unlocked** → **Locked**: User opens editor, creates entity
2. **Locked** → **Locked**: Heartbeat updates LastHeartbeat
3. **Locked** → **Unlocked**: User closes editor (deletes entity) or lock expires

**Access Patterns**:
- Get lock by org + user: `PartitionKey=OrgId, RowKey=UserId_workspace`
- Check if workspace locked: Get entity, check ExpiresAt > now
- Cleanup expired locks: Query where ExpiresAt < now, delete

---

### 2. FileMetadata (Response Model Only)

**Purpose**: Represent file/folder metadata in API responses (not stored in Table Storage).

**Note**: File content is stored in Azure File Share at `/home/orgs/{OrgId}/repo/`. This entity is just the API response model.

**Response Schema**:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| path | string | Relative path from /home/repo | `workflows/sync_users.py` |
| name | string | File or folder name | `sync_users.py` |
| type | enum | "file" or "folder" | `file` |
| size | integer | Size in bytes (null for folders) | `4096` |
| extension | string | File extension (null for folders) | `.py` |
| modified | datetime | Last modified timestamp | `2025-10-23T14:30:00Z` |
| isReadOnly | boolean | Whether file is read-only | `false` |

**Validation Rules**:
- path MUST NOT start with `/` or contain `..` (prevent directory traversal)
- type MUST be "file" or "folder"
- size MUST be null if type is "folder"
- extension MUST match last part of name after final `.`

---

### 3. FileContent (Request/Response Model)

**Purpose**: Transfer file content between client and server.

**Request Schema** (for writes):

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| path | string | Relative path from /home/repo | `workflows/sync_users.py` |
| content | string | File content | `import bifrost\n\ndef run(context):...` |
| encoding | string | Content encoding (default: utf-8) | `utf-8` |

**Response Schema** (for reads):

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| path | string | Relative path from /home/repo | `workflows/sync_users.py` |
| content | string | File content | `import bifrost\n\ndef run(context):...` |
| encoding | string | Content encoding | `utf-8` |
| size | integer | Content size in bytes | `4096` |
| etag | string | ETag for change detection | `"abc123"` |
| modified | datetime | Last modified timestamp | `2025-10-23T14:30:00Z` |

**Validation Rules**:
- content MUST be valid UTF-8 (or specified encoding)
- size MUST match actual content length
- etag MUST be returned for change detection

---

### 4. SearchResult (Response Model)

**Purpose**: Represent a single search match in file contents.

**Response Schema**:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| filePath | string | Relative path to file containing match | `workflows/sync_users.py` |
| line | integer | Line number (1-indexed) | `42` |
| column | integer | Column number (0-indexed) | `15` |
| matchText | string | The matched text | `def run` |
| contextBefore | string | Line before match (optional) | `# Main workflow entry point` |
| contextAfter | string | Line after match (optional) | `context.info("Starting sync")` |

**Validation Rules**:
- line MUST be >= 1
- column MUST be >= 0
- matchText MUST NOT be empty
- contextBefore and contextAfter MAY be null

---

### 5. SearchRequest (Request Model)

**Purpose**: Search query from client.

**Request Schema**:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| query | string | Search text | `def run` |
| caseSensitive | boolean | Case-sensitive matching | `false` |
| regex | boolean | Treat query as regex | `false` |
| filePattern | string | Glob pattern for files to search (optional) | `**/*.py` |
| maxResults | integer | Maximum results to return (default: 1000) | `100` |

**Validation Rules**:
- query MUST NOT be empty
- maxResults MUST be between 1 and 10000
- If regex=true, query MUST be valid regex pattern

---

### 6. SearchResponse (Response Model)

**Purpose**: Search results from server.

**Response Schema**:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| query | string | Original search query | `def run` |
| totalMatches | integer | Total matches found | `42` |
| filesSearched | integer | Number of files searched | `150` |
| results | array[SearchResult] | Array of search results | `[...]` |
| truncated | boolean | Whether results were truncated | `false` |
| searchTimeMs | integer | Search duration in milliseconds | `234` |

**Validation Rules**:
- totalMatches >= results.length
- truncated = true if totalMatches > maxResults
- searchTimeMs MUST be >= 0

---

### 7. ExecutionRequest (Request Model)

**Purpose**: Request to execute a workflow, data provider, or Python script.

**Request Schema**:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| filePath | string | Path to file to execute | `workflows/sync_users.py` |
| fileType | enum | "workflow", "data_provider", or "script" | `workflow` |
| parameters | object | Input parameters (key-value pairs) | `{"orgId": "org_123"}` |
| orgId | string | Organization context | `org_123` |

**Validation Rules**:
- filePath MUST exist and be executable
- fileType MUST match file's actual type
- parameters MUST match file's expected inputs (for workflows/data providers)
- orgId MUST be valid organization

---

### 8. ExecutionResponse (Response Model)

**Purpose**: Response after starting execution.

**Response Schema**:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| executionId | string (UUID) | Unique execution identifier | `550e8400-e29b-41d4-a716-446655440000` |
| filePath | string | Path to file being executed | `workflows/sync_users.py` |
| status | enum | "queued", "running", "completed", "failed" | `running` |
| startedAt | datetime | When execution started | `2025-10-23T14:30:00Z` |
| logsUrl | string | SSE endpoint for log streaming | `/api/editor/execute/{id}/logs` |

**Validation Rules**:
- executionId MUST be unique
- status initial value is "queued" or "running"
- logsUrl MUST be valid SSE endpoint path

---

### 9. LogLine (SSE Event Model)

**Purpose**: Single log line streamed via Server-Sent Events.

**Event Schema**:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| timestamp | datetime | When log was generated | `2025-10-23T14:30:01.234Z` |
| level | enum | "DEBUG", "INFO", "WARNING", "ERROR" | `INFO` |
| message | string | Log message | `Starting user sync` |
| source | string | Log source (logger name) | `bifrost.workflows.sync_users` |

**Validation Rules**:
- timestamp MUST be in ISO 8601 format
- level MUST be valid log level
- message MUST NOT be empty

---

### 10. EditorState (Frontend State Model)

**Purpose**: Client-side state for editor (not persisted to backend in MVP).

**State Schema**:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| openFile | FileMetadata | null | Currently open file | `{path: "workflows/sync.py", ...}` |
| cursorPosition | object | Line and column | `{line: 42, column: 15}` |
| unsavedChanges | boolean | Whether file has unsaved edits | `true` |
| selectedLanguage | string | Current syntax language | `python` |
| layoutMode | enum | "fullscreen" or "minimized" | `fullscreen` |
| sidebarPanel | enum | "files", "search", or "run" | `files` |
| terminalHeight | integer | Terminal panel height in pixels | `300` |

**State Transitions**:
- Open file: openFile = FileMetadata, unsavedChanges = false
- Edit content: unsavedChanges = true
- Save: unsavedChanges = false
- Minimize: layoutMode = "minimized"
- Restore: layoutMode = "fullscreen"

---

## Entity Relationships

```
WorkspaceSession (Table Storage)
  ├─ Scoped by: OrgId (PartitionKey)
  └─ Locked by: UserId (part of RowKey)

FileMetadata (File Share)
  ├─ Stored in: /home/orgs/{OrgId}/repo/{path}
  └─ Accessed by: Users with editor:access permission

SearchResult
  ├─ References: FileMetadata (via filePath)
  └─ Generated from: File contents on demand

ExecutionRequest
  ├─ References: FileMetadata (via filePath)
  ├─ Scoped by: OrgId
  └─ Creates: ExecutionResponse

ExecutionResponse
  ├─ Tracked by: ExecutionId (UUID)
  └─ Streams: LogLine events via SSE

EditorState (Frontend only)
  ├─ References: FileMetadata (openFile)
  └─ Persisted: In browser state (not backend)
```

---

## Pydantic Models (Python Backend)

These entities will be added to `api/shared/models.py`:

```python
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

class WorkspaceSession(BaseModel):
    """Workspace lock entity in Table Storage"""
    PartitionKey: str  # OrgId
    RowKey: str        # f"{UserId}_workspace"
    UserId: str
    UserEmail: str
    AcquiredAt: datetime
    LastHeartbeat: datetime
    ExpiresAt: datetime
    SessionId: str

class FileType(str, Enum):
    FILE = "file"
    FOLDER = "folder"

class FileMetadata(BaseModel):
    """File or folder metadata"""
    path: str
    name: str
    type: FileType
    size: Optional[int] = None
    extension: Optional[str] = None
    modified: datetime
    isReadOnly: bool = False

class FileContentRequest(BaseModel):
    """Request to write file content"""
    path: str
    content: str
    encoding: str = "utf-8"

class FileContentResponse(BaseModel):
    """Response with file content"""
    path: str
    content: str
    encoding: str
    size: int
    etag: str
    modified: datetime

class SearchRequest(BaseModel):
    """Search query"""
    query: str = Field(..., min_length=1)
    caseSensitive: bool = False
    regex: bool = False
    filePattern: Optional[str] = "**/*"
    maxResults: int = Field(default=1000, ge=1, le=10000)

class SearchResult(BaseModel):
    """Single search match"""
    filePath: str
    line: int = Field(..., ge=1)
    column: int = Field(..., ge=0)
    matchText: str
    contextBefore: Optional[str] = None
    contextAfter: Optional[str] = None

class SearchResponse(BaseModel):
    """Search results"""
    query: str
    totalMatches: int
    filesSearched: int
    results: List[SearchResult]
    truncated: bool
    searchTimeMs: int

class ExecutionType(str, Enum):
    WORKFLOW = "workflow"
    DATA_PROVIDER = "data_provider"
    SCRIPT = "script"

class ExecutionRequest(BaseModel):
    """Request to execute file"""
    filePath: str
    fileType: ExecutionType
    parameters: Dict[str, Any] = {}
    orgId: str

class ExecutionStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class ExecutionResponse(BaseModel):
    """Execution start response"""
    executionId: str
    filePath: str
    status: ExecutionStatus
    startedAt: datetime
    logsUrl: str

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

class LogLine(BaseModel):
    """Single log line for SSE streaming"""
    timestamp: datetime
    level: LogLevel
    message: str
    source: str
```

---

## TypeScript Interfaces (Frontend)

These interfaces will be generated from the OpenAPI spec via `npm run generate:types`, but for reference:

```typescript
// Generated from OpenAPI spec
export interface WorkspaceSession {
  PartitionKey: string;
  RowKey: string;
  UserId: string;
  UserEmail: string;
  AcquiredAt: string;
  LastHeartbeat: string;
  ExpiresAt: string;
  SessionId: string;
}

export type FileType = "file" | "folder";

export interface FileMetadata {
  path: string;
  name: string;
  type: FileType;
  size?: number;
  extension?: string;
  modified: string;
  isReadOnly: boolean;
}

export interface FileContentRequest {
  path: string;
  content: string;
  encoding?: string;
}

export interface FileContentResponse {
  path: string;
  content: string;
  encoding: string;
  size: number;
  etag: string;
  modified: string;
}

export interface SearchRequest {
  query: string;
  caseSensitive?: boolean;
  regex?: boolean;
  filePattern?: string;
  maxResults?: number;
}

export interface SearchResult {
  filePath: string;
  line: number;
  column: number;
  matchText: string;
  contextBefore?: string;
  contextAfter?: string;
}

export interface SearchResponse {
  query: string;
  totalMatches: number;
  filesSearched: number;
  results: SearchResult[];
  truncated: boolean;
  searchTimeMs: number;
}

export type ExecutionType = "workflow" | "data_provider" | "script";

export interface ExecutionRequest {
  filePath: string;
  fileType: ExecutionType;
  parameters?: Record<string, any>;
  orgId: string;
}

export type ExecutionStatus = "queued" | "running" | "completed" | "failed";

export interface ExecutionResponse {
  executionId: string;
  filePath: string;
  status: ExecutionStatus;
  startedAt: string;
  logsUrl: string;
}

export type LogLevel = "DEBUG" | "INFO" | "WARNING" | "ERROR";

export interface LogLine {
  timestamp: string;
  level: LogLevel;
  message: string;
  source: string;
}

// Frontend-only state (not from API)
export type LayoutMode = "fullscreen" | "minimized";
export type SidebarPanel = "files" | "search" | "run";

export interface EditorState {
  openFile: FileMetadata | null;
  cursorPosition: { line: number; column: number };
  unsavedChanges: boolean;
  selectedLanguage: string;
  layoutMode: LayoutMode;
  sidebarPanel: SidebarPanel;
  terminalHeight: number;
}
```

---

**Status**: Data model complete. All entities defined with validation rules and relationships.

**Next Step**: Generate API contracts in `/contracts/` directory.
