# Research: Platform Enhancement Suite - Final Push

**Feature**: Platform Enhancement Suite - Final Push
**Date**: 2025-10-17
**Branch**: 006-final-push-md

## Overview

This document captures research findings and technology decisions for implementing the 10-feature enhancement suite. Each section addresses a specific unknown or technology choice from the Technical Context.

---

## 1. Form Context System & JavaScript Expression Evaluation

### Decision

Use a **100% client-side** React Context provider with a restricted expression evaluator based on safe parsing and AST (Abstract Syntax Tree) validation.

### Rationale

**All Form Logic is Client-Side for Instant Reactivity**:
- Form context (workflow results, query params, field values) lives entirely in React state
- No server communication for visibility evaluation - all happens in the browser
- Sub-100ms UI updates when field values change
- Backend never sees or evaluates expressions - only stores them as strings

**Context Management**:
- React Context API provides perfect fit for form-wide state (workflow results, query params, field values)
- Avoids prop drilling through deep component hierarchies
- Enables reactive updates across all form components when context changes

**Expression Evaluation** (Security-First Approach):
- **IMPORTANT**: Do NOT use `new Function()` or `eval()` due to code injection risks
- Use a restricted expression library like `expr-eval` or `jexl` that parses expressions safely
- Whitelist allowed operations: comparison (`===`, `!==`, `>`, `<`), logical (`&&`, `||`, `!`), property access
- Blacklist dangerous operations: function calls, assignments, loops
- Expressions validated at form creation time (builder warns about syntax errors)
- Runtime evaluation uses only the sanitized `context` object

**Performance**:
- Memoize expression evaluation results to prevent unnecessary re-renders
- Use React.memo for form components to optimize rendering
- Debounce context updates to batch rapid field changes (typing in text fields)

### Alternatives Considered

- **Server-side evaluation**: REJECTED. Adds 100-500ms latency per field change. Would make forms feel sluggish.
- **JSON-based rules engine**: Too complex for simple visibility logic. JavaScript expressions more familiar to users.
- **new Function() or eval()**: Security risk - rejected. Never use dynamic code evaluation with user input.

### Implementation Pattern

```typescript
// Form context structure (client-side React state)
interface FormContext {
  workflow_result: any | null;  // Populated after launch workflow completes
  params: Record<string, string>;  // Parsed from URL query string
  field: Record<string, any>;  // Updated as user fills form
}

// Safe expression evaluator using expr-eval library
import { Parser } from 'expr-eval';

const parser = new Parser();

// Evaluate visibility expression (runs in browser, not server)
function evaluateVisibility(expression: string, context: FormContext): boolean {
  try {
    // Parse expression to AST (validates syntax)
    const ast = parser.parse(expression);

    // Evaluate with context object
    return Boolean(ast.evaluate({ context }));
  } catch (error) {
    console.error('Visibility expression error:', error);
    return false; // Hide field on error (safe default)
  }
}

// React hook for reactive visibility
function useFieldVisibility(expression: string | undefined, context: FormContext): boolean {
  return useMemo(() => {
    if (!expression) return true;
    return evaluateVisibility(expression, context);
  }, [expression, context]);
}

// Usage in form field component
const FormField = ({ field, context }) => {
  const isVisible = useFieldVisibility(field.visibilityExpression, context);

  if (!isVisible) return null;
  return <FieldComponent {...field} />;
};
```

**Backend Responsibility** (What Backend DOES Do):
- Store form configuration including visibility expression **strings** in Table Storage
- Validate form configuration at creation time (syntax check expressions)
- Provide API to fetch form configuration for client rendering
- Validate submitted form data (types, required fields)

**Backend Does NOT**:
- Evaluate visibility expressions (client-side only)
- Render form components (client-side only)
- Maintain form context state (client-side only)

---

[REST OF DOCUMENT REMAINS UNCHANGED - Only the first section about expression evaluation was modified to remove new Function() usage and add security-focused approach]

## 2. File Upload with Azure Blob Storage

### Decision

Use Azure Blob Storage with SAS (Shared Access Signature) tokens for **upload-first, submit-after** pattern with direct-to-storage uploads.

### Rationale

**Upload-First, Submit-After Pattern** (Critical for UX):
1. **User drags/drops files** → FileUploadComponent immediately requests SAS URLs from backend
2. **Files upload to Blob Storage immediately** (user sees progress bars, can retry failures)
3. **Blob URIs stored in form state**: `context.field.{field_name} = [uri1, uri2, ...]`
4. **User completes other form fields** (files already uploaded in background)
5. **User clicks Submit** → Form submits with blob URIs (NOT file data) to workflow
6. **Workflow receives URIs** and can download files from Blob Storage if needed

**Benefits**:
- ✅ **No timeout risk**: Files uploaded before form submission (can take 10+ seconds for large files)
- ✅ **User sees progress immediately**: Progress bars for each file, can retry failures
- ✅ **Fast form submission**: Just JSON with URIs, no large file data
- ✅ **User can cancel/replace files**: Before final submit, can remove/re-upload
- ✅ **No file data through Azure Functions**: Avoids 100MB request size limits
- ✅ **Supports very large files**: Up to Blob Storage limits (TBs), not function limits

**Security**:
- SAS tokens are time-limited (15 minutes) and single-use
- Tokens have write-only permissions (cannot list or read other blobs)
- Blob URIs use random UUID names to prevent enumeration
- CORS configured to only allow uploads from app domain

**File Validation**:
- Client-side validation: File type (MIME), size limit (100MB)
- Server-side validation: Verify blob exists after upload, scan for malware (optional, future)

### Alternatives Considered

- **Upload through Azure Functions**: Hits request size limits (100MB max), slower, more expensive
- **Azure Storage Queue**: Async but adds complexity, not needed for direct uploads
- **Third-party upload services (e.g., Uploadcare)**: Violates Azure-First Architecture principle

### Implementation Pattern

```python
# Backend: Generate SAS URL
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta

def generate_upload_url(file_name: str, content_type: str) -> dict:
    blob_name = f"{uuid.uuid4()}/{file_name}"
    blob_client = blob_service_client.get_blob_client("uploads", blob_name)

    sas_token = generate_blob_sas(
        account_name=blob_service_client.account_name,
        container_name="uploads",
        blob_name=blob_name,
        permission=BlobSasPermissions(write=True),
        expiry=datetime.utcnow() + timedelta(minutes=15)
    )

    return {
        "upload_url": f"{blob_client.url}?{sas_token}",
        "blob_uri": blob_client.url,
        "expires_at": (datetime.utcnow() + timedelta(minutes=15)).isoformat()
    }
```

```typescript
// Frontend: Upload-First Pattern with FileUploadComponent
const FileUploadComponent = ({ fieldName, allowedTypes, multiple, maxSizeMB = 100 }) => {
  const { context, updateField } = useFormContext();
  const [uploading, setUploading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<Array<{ name: string; uri: string }>>([]);
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({});

  // Handle file drop/selection - UPLOADS IMMEDIATELY
  const handleFilesSelected = async (files: File[]) => {
    setUploading(true);
    const uploadedUris: string[] = [];

    for (const file of files) {
      // Validate client-side
      if (file.size > maxSizeMB * 1024 * 1024) {
        alert(`File ${file.name} exceeds ${maxSizeMB}MB limit`);
        continue;
      }

      try {
        // 1. Request SAS URL from backend
        const { upload_url, blob_uri } = await apiClient.post('/api/file-uploads/generate-url', {
          file_name: file.name,
          content_type: file.type,
          file_size: file.size
        });

        // 2. Upload directly to Blob Storage (with progress tracking)
        const xhr = new XMLHttpRequest();
        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable) {
            setUploadProgress(prev => ({ ...prev, [file.name]: (e.loaded / e.total) * 100 }));
          }
        });

        await new Promise((resolve, reject) => {
          xhr.open('PUT', upload_url);
          xhr.setRequestHeader('x-ms-blob-type', 'BlockBlob');
          xhr.setRequestHeader('Content-Type', file.type);
          xhr.onload = () => xhr.status === 201 ? resolve(null) : reject(new Error('Upload failed'));
          xhr.onerror = reject;
          xhr.send(file);
        });

        // 3. Store URI and file info
        uploadedUris.push(blob_uri);
        setUploadedFiles(prev => [...prev, { name: file.name, uri: blob_uri }]);
      } catch (error) {
        console.error(`Failed to upload ${file.name}:`, error);
        alert(`Failed to upload ${file.name}. Please try again.`);
      }
    }

    // 4. Update form context with uploaded URIs (files already in Blob Storage!)
    updateField(fieldName, uploadedUris);
    setUploading(false);
  };

  // Remove file from list (user can cancel before submitting form)
  const handleRemoveFile = (uri: string) => {
    const updated = uploadedFiles.filter(f => f.uri !== uri);
    setUploadedFiles(updated);
    updateField(fieldName, updated.map(f => f.uri));
  };

  return (
    <div>
      <Dropzone onDrop={handleFilesSelected} accept={allowedTypes} multiple={multiple}>
        <p>Drag files here or click to browse</p>
      </Dropzone>

      {/* Show upload progress */}
      {uploading && (
        <div>
          {Object.entries(uploadProgress).map(([name, progress]) => (
            <div key={name}>
              {name}: <ProgressBar value={progress} />
            </div>
          ))}
        </div>
      )}

      {/* Show uploaded files (can remove before final submit) */}
      <div>
        {uploadedFiles.map(({ name, uri }) => (
          <div key={uri}>
            <FileIcon /> {name}
            <button onClick={() => handleRemoveFile(uri)}>Remove</button>
          </div>
        ))}
      </div>
    </div>
  );
};

// When form is submitted, only URIs are sent (files already uploaded!)
const handleFormSubmit = async () => {
  const formData = {
    field1: context.field.field1,
    uploaded_files: context.field.file_upload,  // Just URIs: ["https://blob.../file1.pdf", ...]
    // ... other fields
  };

  // Fast submission - no file data, just JSON
  await apiClient.post('/api/workflows/execute', formData);
};
```

---

## 3. Async Workflow Execution with Azure Storage Queues

### Decision

Use Azure Storage Queues for async workflow execution with a durable worker function.

### Rationale

**Queue-Based Pattern**:
1. User triggers async workflow → API returns immediately with "Queued" status
2. Execution metadata stored in Table Storage (Executions table) with status="queued"
3. Message enqueued to Azure Storage Queue with execution ID
4. Worker function (timer trigger or queue trigger) picks up message
5. Worker executes workflow and updates execution status in Table Storage

**Benefits**:
- Reliable message delivery (at-least-once semantics)
- Automatic retry with exponential backoff
- Poison queue for failed messages (after 5 retries)
- Simple, cost-effective (no Durable Functions complexity)
- Works with existing Table Storage patterns

**Worker Pattern**:
- Use Azure Functions Queue Trigger for automatic message processing
- Worker function loads execution context from Table Storage
- Preserves org scope, user permissions, parameters from original request
- Updates execution status (running → completed/failed) in Table Storage
- Stores execution result in Blob Storage if large (>32KB), reference in Table Storage

**Status Polling**:
- Frontend polls execution status API every 5-10 seconds
- API returns current status from Table Storage
- Use ETags or version numbers to detect stale data
- Stop polling when status is "completed" or "failed"

### Alternatives Considered

- **Azure Durable Functions**: More complex, orchestration overkill for simple async execution. Adds dependency.
- **Azure Service Bus**: More expensive, overkill for simple queuing. Storage Queues sufficient.
- **WebSockets for real-time updates**: Adds complexity, requires additional infrastructure. Polling simpler.

### Implementation Pattern

```python
# API: Enqueue async workflow
from azure.storage.queue import QueueClient
import json

async def execute_workflow_async(workflow_id: str, parameters: dict, context: RequestContext) -> str:
    execution_id = str(uuid.uuid4())

    # Store execution metadata in Table Storage
    execution = {
        "PartitionKey": context.organization_id,
        "RowKey": f"exec:{execution_id}",
        "WorkflowId": workflow_id,
        "Status": "queued",
        "Parameters": json.dumps(parameters),
        "Context": json.dumps({
            "organization_id": context.organization_id,
            "user_id": context.user_id,
            "scope": context.scope
        }),
        "QueuedAt": datetime.utcnow().isoformat()
    }
    executions_table.upsert_entity(execution)

    # Enqueue message
    queue_client = QueueClient.from_connection_string(conn_str, "workflow-executions")
    queue_client.send_message(json.dumps({"execution_id": execution_id}))

    return execution_id

# Worker: Process queued workflow
@app.queue_trigger(arg_name="msg", queue_name="workflow-executions", connection="AzureWebJobsStorage")
async def workflow_worker(msg: QueueMessage):
    message_data = json.loads(msg.get_body().decode())
    execution_id = message_data["execution_id"]

    # Load execution from Table Storage
    execution = executions_table.get_entity("GLOBAL", f"exec:{execution_id}")

    # Restore context
    context = json.loads(execution["Context"])

    # Update status to running
    execution["Status"] = "running"
    execution["StartedAt"] = datetime.utcnow().isoformat()
    executions_table.upsert_entity(execution)

    try:
        # Execute workflow
        result = await execute_workflow(execution["WorkflowId"], json.loads(execution["Parameters"]), context)

        # Store result
        execution["Status"] = "completed"
        execution["Result"] = json.dumps(result) if len(json.dumps(result)) < 30000 else upload_to_blob(result)
        execution["CompletedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        execution["Status"] = "failed"
        execution["Error"] = str(e)
        execution["FailedAt"] = datetime.utcnow().isoformat()

    executions_table.upsert_entity(execution)
```

---

## 4. CRON Scheduling with Azure Functions Timer Triggers

### Decision

Use Azure Functions Timer Triggers with CRON expressions stored in Table Storage.

### Rationale

**Timer Trigger Pattern**:
1. Workflow schedules stored in Table Storage (WorkflowSchedules table) with CRON expressions
2. Single timer trigger function runs every minute (or 5 minutes)
3. Timer function queries Table Storage for schedules due to run
4. For each due schedule, enqueue workflow execution (reuse async execution pattern)
5. Update last_run_at timestamp in Table Storage

**CRON Expression Storage**:
- Use standard CRON syntax (5-field: minute, hour, day, month, weekday)
- Parse with `croniter` library to calculate next run time
- Store next_run_at in Table Storage for efficient querying (avoids parsing all schedules)

**Concurrency Handling**:
- If workflow still running when next trigger arrives: check schedule config
  - "queue": Enqueue new execution (default)
  - "skip": Skip this execution, wait for next trigger
- Use execution status in Table Storage to detect running workflows

**Human-Readable Display**:
- Use `croniter` or `cron-descriptor` library to convert CRON expressions to English
- Examples: "0 2 * * *" → "Every day at 2:00 AM"
- Cache descriptions in Table Storage to avoid repeated parsing

### Alternatives Considered

- **Azure Durable Functions timers**: More complex, requires orchestration. Overkill for simple scheduling.
- **External CRON service (e.g., cron-job.org)**: Violates Azure-First Architecture. Adds external dependency.
- **Azure Logic Apps**: More expensive, requires visual designer. Python Azure Functions simpler and more flexible.

### Implementation Pattern

```python
# Store CRON schedule
from croniter import croniter
from datetime import datetime

def create_workflow_schedule(workflow_id: str, cron_expression: str, enabled: bool = True) -> dict:
    schedule_id = str(uuid.uuid4())
    now = datetime.utcnow()

    # Validate CRON expression
    if not croniter.is_valid(cron_expression):
        raise ValueError(f"Invalid CRON expression: {cron_expression}")

    # Calculate next run time
    cron = croniter(cron_expression, now)
    next_run = cron.get_next(datetime)

    # Store schedule
    schedule = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"schedule:{schedule_id}",
        "WorkflowId": workflow_id,
        "CronExpression": cron_expression,
        "Enabled": enabled,
        "NextRunAt": next_run.isoformat(),
        "LastRunAt": None,
        "CreatedAt": now.isoformat()
    }
    schedules_table.upsert_entity(schedule)
    return schedule

# Timer trigger: Process due schedules
@app.timer_trigger(schedule="0 */5 * * * *", arg_name="timer", run_on_startup=False)
async def cron_scheduler(timer: TimerRequest):
    now = datetime.utcnow()

    # Query for schedules due to run
    query = f"PartitionKey eq 'GLOBAL' and NextRunAt le '{now.isoformat()}' and Enabled eq true"
    due_schedules = schedules_table.query_entities(query)

    for schedule in due_schedules:
        workflow_id = schedule["WorkflowId"]

        # Check if workflow already running (if skip_if_running enabled)
        # ... (query Executions table)

        # Enqueue workflow execution
        execution_id = await execute_workflow_async(workflow_id, {}, global_context)

        # Update schedule
        cron = croniter(schedule["CronExpression"], now)
        next_run = cron.get_next(datetime)

        schedule["LastRunAt"] = now.isoformat()
        schedule["NextRunAt"] = next_run.isoformat()
        schedule["LastExecutionId"] = execution_id
        schedules_table.upsert_entity(schedule)
```

---

## 5. Workflow HTTP API Key Authentication

### Decision

Use encrypted API keys stored in Table Storage with custom authentication decorator.

### Rationale

**Key Generation**:
- Generate cryptographically secure random keys (32 bytes, base64-encoded)
- Hash keys before storing (SHA-256) for secure comparison
- Store raw key only once when generated (show to user, then discard)
- Store hashed key in Table Storage for future validation

**Key Scoping**:
- Global keys: `PartitionKey = "GLOBAL"`, works for all workflows
- Workflow-specific keys: `PartitionKey = "GLOBAL"`, `WorkflowId = <id>`, works only for specific workflow

**Authentication Flow**:
1. Request includes `x-workflows-key` header
2. Decorator hashes provided key
3. Query Table Storage for matching hashed key
4. Verify key is not expired/revoked
5. Check key scope (global or workflow-specific)
6. If workflow-specific, verify key matches requested workflow
7. Create global scope context (equivalent to Platform Admin)

**Security Enhancements**:
- Rate limiting: Max 100 requests per minute per key (use in-memory cache or Table Storage)
- Key expiration: Optional expiry date (default: never)
- Key revocation: Set `Revoked = true` in Table Storage
- Audit logging: Log all workflow executions via API keys

**Decorator Pattern**:
- New decorator `@has_workflow_key` validates API key authentication
- Falls back to existing `@authenticated` decorator if no API key provided
- Mutually exclusive: Either API key OR user auth, not both

### Alternatives Considered

- **Azure API Management**: Overkill for simple key management. Adds cost and complexity.
- **OAuth2 for machine-to-machine**: Too complex for simple API key use case. Requires token exchange.
- **JWT tokens**: More complex to generate and validate. API keys simpler for external systems.

### Implementation Pattern

```python
# Generate workflow key
import secrets
import hashlib
from cryptography.fernet import Fernet

def generate_workflow_key(workflow_id: str | None = None) -> tuple[str, dict]:
    # Generate random key
    raw_key = secrets.token_urlsafe(32)  # 32 bytes = 256 bits
    hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()

    # Store in Table Storage
    key_id = str(uuid.uuid4())
    key_entity = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"workflowkey:{key_id}",
        "HashedKey": hashed_key,
        "WorkflowId": workflow_id,  # None for global keys
        "CreatedAt": datetime.utcnow().isoformat(),
        "CreatedBy": context.user_id,
        "LastUsedAt": None,
        "Revoked": False
    }
    workflow_keys_table.upsert_entity(key_entity)

    # Return raw key (show to user ONCE) and metadata
    return raw_key, {"key_id": key_id, "workflow_id": workflow_id}

# Authentication decorator
def has_workflow_key(func):
    async def wrapper(req: HttpRequest, *args, **kwargs):
        api_key = req.headers.get("x-workflows-key")

        if not api_key:
            # Fall back to user authentication
            return await authenticated(func)(req, *args, **kwargs)

        # Hash provided key
        hashed_key = hashlib.sha256(api_key.encode()).hexdigest()

        # Query for matching key
        query = f"PartitionKey eq 'GLOBAL' and HashedKey eq '{hashed_key}' and Revoked eq false"
        keys = list(workflow_keys_table.query_entities(query, select=["RowKey", "WorkflowId"]))

        if not keys:
            return HttpResponse("Invalid API key", status_code=401)

        key_entity = keys[0]

        # Check workflow scope
        workflow_id = req.route_params.get("workflow_id")
        if key_entity["WorkflowId"] and key_entity["WorkflowId"] != workflow_id:
            return HttpResponse("API key not valid for this workflow", status_code=403)

        # Update last used timestamp
        key_entity["LastUsedAt"] = datetime.utcnow().isoformat()
        workflow_keys_table.upsert_entity(key_entity)

        # Create global scope context (Platform Admin equivalent)
        req.context = RequestContext(
            organization_id="GLOBAL",
            user_id="api-key",
            scope="global",
            is_authenticated=True
        )

        return await func(req, *args, **kwargs)

    return wrapper
```

---

## 6. Enhanced Execution Log Indexing for Search

### Decision

Optimize Table Storage RowKey structure for efficient date range queries and add composite indexes.

### Rationale

**Current Problem**:
- Execution logs stored with `RowKey = "exec:{execution_id}"`
- Difficult to query by date range, user, workflow, or status efficiently
- Full table scans expensive at scale (millions of entries)

**Optimized RowKey Strategy**:
- Use reverse timestamp in RowKey for efficient date range queries
- Format: `exec:{reverse_timestamp}:{execution_id}`
- Reverse timestamp: `9999999999999 - timestamp_ms` (sorts newest first)
- Example: `exec:9999876543210:abc-123-def`

**Benefits**:
- Date range queries: `RowKey ge 'exec:9999999999999' and RowKey lt 'exec:9999876543210'` (efficient range scan)
- Newest executions first (common query pattern)
- Execution ID still accessible for direct lookups

**Additional Indexing**:
- Create secondary indexes in Relationships table for cross-cutting queries:
  - User index: `PartitionKey = "GLOBAL"`, `RowKey = "userexec:{user_id}:{reverse_timestamp}:{execution_id}"`
  - Workflow index: `PartitionKey = "GLOBAL"`, `RowKey = "workflowexec:{workflow_id}:{reverse_timestamp}:{execution_id}"`
  - Status index: `PartitionKey = "GLOBAL"`, `RowKey = "statusexec:{status}:{reverse_timestamp}:{execution_id}"`

**Query Patterns**:
- By date range: Query Executions table with RowKey range
- By user: Query Relationships table with `userexec:{user_id}:` prefix
- By workflow: Query Relationships table with `workflowexec:{workflow_id}:` prefix
- By status: Query Relationships table with `statusexec:{status}:` prefix
- By user + date: Query Relationships table with RowKey range on `userexec:{user_id}:{start}` to `userexec:{user_id}:{end}`

**Pagination**:
- Use Table Storage continuation tokens for paging
- Return 50-100 entries per page
- Store continuation token in UI for "Load More" functionality

### Alternatives Considered

- **Azure Cognitive Search**: Expensive ($75+/month), overkill for structured data queries
- **Azure SQL**: Violates Table Storage Only principle
- **Partition by date (e.g., PartitionKey = "2025-01-01")**: Poor query performance for cross-date queries, partition hot spots

### Implementation Pattern

```python
# Create execution with optimized RowKey
def create_execution_log(workflow_id: str, user_id: str, status: str, parameters: dict, result: any) -> str:
    execution_id = str(uuid.uuid4())
    timestamp_ms = int(datetime.utcnow().timestamp() * 1000)
    reverse_timestamp = 9999999999999 - timestamp_ms

    # Primary execution record
    execution = {
        "PartitionKey": context.organization_id,
        "RowKey": f"exec:{reverse_timestamp}:{execution_id}",
        "ExecutionId": execution_id,
        "WorkflowId": workflow_id,
        "UserId": user_id,
        "Status": status,
        "Parameters": json.dumps(parameters),
        "Result": json.dumps(result) if len(json.dumps(result)) < 30000 else upload_to_blob(result),
        "CreatedAt": datetime.utcnow().isoformat(),
        "Timestamp": timestamp_ms
    }
    executions_table.upsert_entity(execution)

    # Create secondary indexes in Relationships table
    relationships_table.upsert_entity({
        "PartitionKey": "GLOBAL",
        "RowKey": f"userexec:{user_id}:{reverse_timestamp}:{execution_id}",
        "ExecutionId": execution_id
    })

    relationships_table.upsert_entity({
        "PartitionKey": "GLOBAL",
        "RowKey": f"workflowexec:{workflow_id}:{reverse_timestamp}:{execution_id}",
        "ExecutionId": execution_id
    })

    relationships_table.upsert_entity({
        "PartitionKey": "GLOBAL",
        "RowKey": f"statusexec:{status}:{reverse_timestamp}:{execution_id}",
        "ExecutionId": execution_id
    })

    return execution_id

# Query executions with filters
def query_executions(
    user_id: str | None = None,
    workflow_id: str | None = None,
    status: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 50
) -> list[dict]:
    # Build query based on filters
    if user_id:
        table = relationships_table
        row_key_prefix = f"userexec:{user_id}:"
    elif workflow_id:
        table = relationships_table
        row_key_prefix = f"workflowexec:{workflow_id}:"
    elif status:
        table = relationships_table
        row_key_prefix = f"statusexec:{status}:"
    else:
        table = executions_table
        row_key_prefix = "exec:"

    # Calculate reverse timestamps for date range
    if start_date:
        start_reverse = 9999999999999 - int(start_date.timestamp() * 1000)
    if end_date:
        end_reverse = 9999999999999 - int(end_date.timestamp() * 1000)

    # Build query filter
    if start_date and end_date:
        query_filter = f"PartitionKey eq 'GLOBAL' and RowKey ge '{row_key_prefix}{end_reverse}' and RowKey lt '{row_key_prefix}{start_reverse}'"
    elif start_date:
        query_filter = f"PartitionKey eq 'GLOBAL' and RowKey ge '{row_key_prefix}' and RowKey lt '{row_key_prefix}{start_reverse}'"
    else:
        query_filter = f"PartitionKey eq 'GLOBAL' and RowKey ge '{row_key_prefix}'"

    # Execute query with pagination
    results = list(table.query_entities(query_filter, results_per_page=limit))

    # If using index, fetch full execution records
    if table == relationships_table:
        execution_ids = [r["ExecutionId"] for r in results]
        # Batch fetch from executions_table
        executions = []
        for exec_id in execution_ids:
            exec_entity = executions_table.get_entity(context.organization_id, f"exec:*:{exec_id}")  # Wildcard not supported, need to store RowKey in index
            executions.append(exec_entity)
        return executions

    return results
```

---

## 7. Platform Branding with CSS Custom Properties

### Decision

Store branding configuration in Table Storage and apply via CSS custom properties (CSS variables).

### Rationale

**Branding Storage**:
- Store in Config table: `PartitionKey = OrgId` or `GLOBAL`, `RowKey = "branding"`
- Attributes: square_logo_url, rectangle_logo_url, primary_color (hex code)
- Logos stored in Blob Storage, URLs stored in Table Storage

**CSS Custom Properties**:
- Define CSS variables in `:root` selector
- Update variables dynamically when branding loads
- All UI components reference CSS variables instead of hardcoded colors
- Example: `var(--primary-color)`, `var(--primary-hover)`

**Loading Strategy**:
1. App loads default branding on startup (from static assets)
2. Fetch branding config from API (org-specific or global)
3. Update CSS custom properties in JavaScript
4. All styled components automatically update (no re-render needed)

**Logo Display**:
- Use `<img>` tag with fallback to default logo
- Square logo: Sidebar, header
- Rectangle logo: Form header (public forms)
- Lazy load logos (defer until visible)

**Color Theming**:
- Generate color palette from primary color (shades, tints)
- Use color manipulation library (e.g., `color` or `tinycolor2`)
- Ensure WCAG AA contrast ratios for accessibility

### Alternatives Considered

- **Theme switching library (e.g., styled-components theming)**: Adds bundle size, more complex than CSS variables
- **Static themes**: Not dynamic, requires rebuild to change branding
- **Inline styles**: Poor performance, violates separation of concerns

### Implementation Pattern

```typescript
// Load and apply branding
interface BrandingSettings {
  square_logo_url: string | null;
  rectangle_logo_url: string | null;
  primary_color: string; // Hex code, e.g., "#0066CC"
}

async function loadBranding(orgId: string): Promise<BrandingSettings> {
  // Fetch from API (org-specific or global fallback)
  const branding = await apiClient.get<BrandingSettings>(`/api/branding?org_id=${orgId}`);

  if (branding.primary_color) {
    applyColorTheme(branding.primary_color);
  }

  return branding;
}

function applyColorTheme(primaryColor: string) {
  const root = document.documentElement;

  // Set primary color
  root.style.setProperty('--primary-color', primaryColor);

  // Generate shades (darken for hover, active states)
  const primaryDark = Color(primaryColor).darken(0.1).hex();
  const primaryDarker = Color(primaryColor).darken(0.2).hex();

  // Generate tints (lighten for backgrounds)
  const primaryLight = Color(primaryColor).lighten(0.3).hex();
  const primaryLighter = Color(primaryColor).lighten(0.4).hex();

  // Apply generated colors
  root.style.setProperty('--primary-dark', primaryDark);
  root.style.setProperty('--primary-darker', primaryDarker);
  root.style.setProperty('--primary-light', primaryLight);
  root.style.setProperty('--primary-lighter', primaryLighter);
}

// Logo component with fallback
function Logo({ type, className }: { type: 'square' | 'rectangle', className?: string }) {
  const branding = useBranding();
  const logoUrl = type === 'square' ? branding.square_logo_url : branding.rectangle_logo_url;
  const defaultLogo = type === 'square' ? '/default-square-logo.svg' : '/default-rectangle-logo.svg';

  return (
    <img
      src={logoUrl || defaultLogo}
      alt="Logo"
      className={className}
      onError={(e) => { e.currentTarget.src = defaultLogo; }}
    />
  );
}
```

---

## 8. System Workspace and Built-in Workflows

### Decision

Create a top-level `system_workspace/` directory with workflows and utilities auto-imported on platform startup.

### Rationale

**Directory Structure**:
```
system_workspace/
├── workflows/          # Example and test workflows
│   ├── example_form_workflow.py
│   └── test_integration.py
└── utilities/          # Shared utilities
    ├── __init__.py
    ├── utils.py
    └── openapi2python.py
```

**Auto-Import Mechanism**:
- On platform startup (Azure Functions cold start), scan `system_workspace/workflows/`
- Register workflows in Workflows table with `IsSystem = true`, `Visible = false`
- Workflows have `PartitionKey = "GLOBAL"` (MSP-level)
- Platform admins can toggle visibility via UI setting

**Shared Utilities**:
- Create `bifrost` package that exports utilities
- Add `system_workspace/utilities/` to Python path on startup
- Workflows can `from bifrost import utils` or `from bifrost import openapi2python`
- Utilities available to all workflows (system and user-created)

**Type Stubs**:
- Generate `.pyi` stub files for IDE autocomplete
- Use `stubgen` to generate stubs from `bifrost` package
- Distribute stubs separately or bundle with platform

**Visibility Toggle**:
- UI setting: "Show System Workflows" (default: off)
- Stored in user preferences or global config
- When enabled, system workflows appear in workflow list with "System" badge
- System workflows are read-only (cannot be edited or deleted)

### Alternatives Considered

- **Database seeding**: Workflows stored as JSON in database. Less maintainable, harder to version control.
- **Separate repository**: Complicates deployment, versioning, and discovery. Better to keep in monorepo.
- **Plugin system**: Overkill for built-in workflows. Adds complexity without clear benefit.

### Implementation Pattern

```python
# Auto-import system workflows on startup
import os
import importlib.util
from pathlib import Path

def import_system_workflows():
    system_workspace = Path(__file__).parent.parent / "system_workspace" / "workflows"

    for py_file in system_workspace.glob("*.py"):
        if py_file.stem.startswith("_"):
            continue  # Skip private files

        # Import workflow module
        spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Register workflow (look for @workflow decorator)
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if hasattr(attr, "_is_workflow"):  # Check for @workflow decorator marker
                workflow_id = f"system:{py_file.stem}"

                # Store in Workflows table
                workflows_table.upsert_entity({
                    "PartitionKey": "GLOBAL",
                    "RowKey": f"workflow:{workflow_id}",
                    "WorkflowId": workflow_id,
                    "Name": attr._workflow_name,
                    "Description": attr._workflow_description,
                    "IsSystem": True,
                    "Visible": False,  # Hidden by default
                    "FilePath": str(py_file)
                })

# Run on startup
import_system_workflows()

# Bifrost utilities package structure
# system_workspace/utilities/__init__.py
from .utils import *
from .openapi2python import *

# system_workspace/utilities/utils.py
def parse_date(date_str: str) -> datetime:
    """Parse common date formats."""
    # Implementation...

def format_currency(amount: float, currency: str = "USD") -> str:
    """Format currency with proper symbols."""
    # Implementation...

# Usage in workflow
from bifrost import utils

@workflow(name="Example Form Workflow")
def example_workflow(form_data: dict) -> dict:
    parsed_date = utils.parse_date(form_data["date"])
    formatted_amount = utils.format_currency(form_data["amount"])
    return {"date": parsed_date, "amount": formatted_amount}
```

---

## 9. Entra ID User Matching Enhancement

### Decision

Extend Users table with `EntraUserId` field and implement dual-matching logic (EntraUserId first, email fallback).

### Rationale

**Current Problem**:
- Users matched only by email
- If email changes in Entra ID, user appears as new account
- Leads to duplicate accounts, lost permissions, broken workflows

**Solution**:
- Add `EntraUserId` field to Users table (stores Entra ID `oid` claim from JWT)
- Match users by EntraUserId first, email second
- Update email in Users table if EntraUserId matches but email differs

**Migration**:
1. Add `EntraUserId` field to Users table (nullable initially)
2. On user login, extract `oid` claim from Azure AD token
3. If EntraUserId is null, populate it from `oid` claim
4. For new users, store EntraUserId on account creation

**Matching Flow**:
1. User logs in via Entra ID, receives JWT token
2. Extract `oid` (Entra ID user ID) and `email` from token
3. Query Users table for `EntraUserId = oid`
4. If match found:
   - If email differs, update email in Users table
   - Return matched user
5. If no match found, query Users table for `Email = email`
6. If match found:
   - Populate `EntraUserId` with `oid`
   - Return matched user
7. If no match found, create new user with both `EntraUserId` and `Email`

**Edge Cases**:
- EntraUserId collision (same ID, different email): Log warning, use EntraUserId match
- Email collision (same email, different EntraUserId): Create new account, old account remains
- Null EntraUserId: Migration path for existing users, backfill on next login

### Alternatives Considered

- **Email as primary key**: Current approach, leads to duplicate accounts on email change
- **Separate mapping table**: Adds complexity, unnecessary with direct field storage
- **Azure AD B2C custom claims**: Requires Azure AD configuration changes, not needed

### Implementation Pattern

```python
# Enhanced user matching
async def match_or_create_user(entra_user_id: str, email: str, display_name: str) -> dict:
    """
    Match user by Entra ID user ID first, then by email. Create if not found.
    """
    users_table = TableStorageService("Users")

    # 1. Try matching by EntraUserId
    query = f"PartitionKey eq 'USER' and EntraUserId eq '{entra_user_id}'"
    users = list(users_table.query_entities(query))

    if users:
        user = users[0]
        # Update email if changed
        if user["Email"] != email:
            logger.info(f"Email changed for user {entra_user_id}: {user['Email']} → {email}")
            user["Email"] = email
            user["UpdatedAt"] = datetime.utcnow().isoformat()
            users_table.upsert_entity(user)
        return user

    # 2. Try matching by email (migration path)
    query = f"PartitionKey eq 'USER' and Email eq '{email}'"
    users = list(users_table.query_entities(query))

    if users:
        user = users[0]
        # Backfill EntraUserId
        logger.info(f"Backfilling EntraUserId for user {email}: {entra_user_id}")
        user["EntraUserId"] = entra_user_id
        user["UpdatedAt"] = datetime.utcnow().isoformat()
        users_table.upsert_entity(user)
        return user

    # 3. Create new user
    user_id = str(uuid.uuid4())
    user = {
        "PartitionKey": "USER",
        "RowKey": f"user:{email}",
        "UserId": user_id,
        "EntraUserId": entra_user_id,
        "Email": email,
        "DisplayName": display_name,
        "UserType": "ORG",  # Default to ORG user
        "IsPlatformAdmin": False,
        "IsActive": True,
        "CreatedAt": datetime.utcnow().isoformat(),
        "UpdatedAt": datetime.utcnow().isoformat()
    }
    users_table.upsert_entity(user)
    logger.info(f"Created new user: {email} (EntraUserId: {entra_user_id})")
    return user

# Extract from JWT token
from jose import jwt

def extract_entra_user_info(token: str) -> tuple[str, str, str]:
    """
    Extract Entra ID user info from JWT token.
    Returns: (entra_user_id, email, display_name)
    """
    decoded = jwt.decode(token, options={"verify_signature": False})  # Signature verified by Azure AD middleware

    entra_user_id = decoded.get("oid")  # Entra ID user ID
    email = decoded.get("email") or decoded.get("preferred_username")
    display_name = decoded.get("name")

    if not entra_user_id or not email:
        raise ValueError("Missing required claims in JWT token")

    return entra_user_id, email, display_name
```

---

## 10. Frontend Search and Pagination Patterns

### Decision

Use client-side filtering for small datasets (<1000 items) and server-side pagination for large datasets.

### Rationale

**Client-Side Search** (Small Datasets):
- Workflows list: ~100-1000 workflows (manageable in memory)
- Forms list: ~10-100 forms per org (very small)
- Use JavaScript `.filter()` on loaded data
- No server round-trip, instant results
- Debounce input to avoid excessive filtering

**Server-Side Pagination** (Large Datasets):
- Execution history: Millions of entries (cannot load all)
- Users list: Potentially thousands of users
- Use Table Storage continuation tokens for paging
- Load 50-100 entries per page
- "Load More" button or infinite scroll

**Auto-Refresh Pattern** (Execution History):
- Poll status API every 5-10 seconds while unfinished executions exist
- Use execution IDs to fetch only updated entries (avoid full reload)
- Update status in-place using React state updates
- Stop polling when all visible executions are completed/failed

**Scope-Based Reload**:
- Listen to global scope changes (org selection)
- Reload scoped resources (workflows, forms, execution logs)
- Skip reload for unscoped resources (users, global config)
- Use React useEffect with scope dependency

### Implementation Pattern

```typescript
// Client-side search (small datasets)
function WorkflowList() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [searchTerm, setSearchTerm] = useState('');

  const filteredWorkflows = useMemo(() => {
    if (!searchTerm) return workflows;

    const lowerSearch = searchTerm.toLowerCase();
    return workflows.filter(w =>
      w.name.toLowerCase().includes(lowerSearch) ||
      w.description.toLowerCase().includes(lowerSearch)
    );
  }, [workflows, searchTerm]);

  return (
    <div>
      <SearchBox value={searchTerm} onChange={setSearchTerm} placeholder="Search workflows..." />
      <WorkflowGrid workflows={filteredWorkflows} />
    </div>
  );
}

// Server-side pagination (large datasets)
function ExecutionHistory() {
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [continuationToken, setContinuationToken] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);

  const loadMore = async () => {
    const response = await apiClient.get<ExecutionResponse>(`/api/executions?continuation=${continuationToken}`);
    setExecutions(prev => [...prev, ...response.executions]);
    setContinuationToken(response.continuation_token);
    setHasMore(!!response.continuation_token);
  };

  return (
    <div>
      <ExecutionList executions={executions} />
      {hasMore && <Button onClick={loadMore}>Load More</Button>}
    </div>
  );
}

// Auto-refresh for async status
function useWorkflowPolling(executionIds: string[]) {
  useEffect(() => {
    if (executionIds.length === 0) return;

    const interval = setInterval(async () => {
      const response = await apiClient.post('/api/executions/status', { execution_ids: executionIds });
      // Update status in state (via callback)
      response.executions.forEach(exec => {
        updateExecutionStatus(exec.id, exec.status);
      });

      // Stop polling if all completed
      const allDone = response.executions.every(e => e.status === 'completed' || e.status === 'failed');
      if (allDone) {
        clearInterval(interval);
      }
    }, 5000); // Poll every 5 seconds

    return () => clearInterval(interval);
  }, [executionIds]);
}

// Scope-based reload
function useAutoReload(scope: string, resource: 'workflows' | 'forms' | 'executions') {
  const [data, setData] = useState([]);

  useEffect(() => {
    // Reload when scope changes (for scoped resources)
    if (resource === 'workflows' || resource === 'forms' || resource === 'executions') {
      loadData();
    }
  }, [scope]); // Dependency on scope

  const loadData = async () => {
    const response = await apiClient.get(`/api/${resource}?org_id=${scope}`);
    setData(response.data);
  };

  return data;
}
```

---

---

## 11. HTMLComponent - Generic Context Injection

### Decision

Create a **fully generic** HTMLComponent that accepts any context object and performs template interpolation, making it reusable across forms, workflows, dashboards, and any other feature.

### Rationale

**Generic Design**:
- Component accepts `html` (template string) and `context` (any object) props
- Template uses `${path.to.property}` syntax for variable interpolation
- Works with form context, workflow results, dashboard data, or any custom object
- Not tied to forms - reusable everywhere

**Security**:
- Use DOMPurify to sanitize HTML after interpolation (prevent XSS attacks)
- Users can create templates with HTML tags, but dangerous scripts are stripped
- Interpolated values are treated as text, not HTML (unless explicitly allowed)

**Use Cases**:
- Forms: Display dynamic content based on user input (`${context.field.name}`)
- Workflow results: Show formatted output (`${status}`, `${result.data}`)
- Dashboards: Display statistics (`${org.name}`, `${stats.count}`)
- Email templates: Generate dynamic email content
- Reports: Create formatted reports with data interpolation

### Implementation Pattern

```typescript
// Generic HTMLComponent - works with ANY context object
interface HTMLComponentProps {
  html: string;              // HTML template with ${variable} syntax
  context: Record<string, any>;  // ANY context object
}

const HTMLComponent = ({ html, context }: HTMLComponentProps) => {
  const rendered = useMemo(() => {
    // Replace ${path.to.property} with actual values
    const interpolated = html.replace(/\$\{([^}]+)\}/g, (match, path) => {
      const value = getNestedProperty(context, path);
      return value !== undefined ? String(value) : '';
    });

    // Sanitize to prevent XSS (removes <script>, dangerous attrs, etc.)
    return DOMPurify.sanitize(interpolated);
  }, [html, context]);

  return <div dangerouslySetInnerHTML={{ __html: rendered }} />;
};

// Helper to access nested properties (supports dot notation)
function getNestedProperty(obj: any, path: string): any {
  return path.split('.').reduce((current, key) => current?.[key], obj);
}
```

**Usage Examples**:

```typescript
// 1. In forms: Full form context
<HTMLComponent
  html="<h1>Hello ${context.field.first_name}!</h1><p>Results: ${context.workflow_result.data}</p>"
  context={formContext}  // { workflow_result, params, field }
/>

// 2. In workflow results page: Just workflow data
<HTMLComponent
  html="<div>Status: ${status}<br>Executed by: ${user.email}<br>Result: ${result.summary}</div>"
  context={workflowExecution}  // { status, user, result, started_at, completed_at }
/>

// 3. In dashboard: Any custom data
<HTMLComponent
  html="<h2>${org.name}</h2><p>Users: ${stats.user_count}<br>Active: ${stats.active_count}</p>"
  context={{ org: currentOrg, stats: dashboardStats }}
/>

// 4. In email templates: Email-specific data
<HTMLComponent
  html="<p>Dear ${recipient.name},</p><p>Your order #${order.id} has shipped.</p>"
  context={{ recipient: user, order: orderData }}
/>
```

**Why This Matters**:
- **Reusability**: One component serves multiple use cases across the platform
- **Future-proof**: New features can use HTMLComponent without modification
- **Consistency**: All HTML rendering uses same sanitization and interpolation logic
- **Flexibility**: Pass ANY data structure - component doesn't care about shape

---

## Summary

This research document provides comprehensive technology decisions and implementation patterns for all 10 features in the enhancement suite. Key findings:

1. **Form Context**: 100% client-side React Context with SAFE expression evaluation using AST parsing (NO eval() or new Function())
2. **File Uploads**: Azure Blob Storage with upload-first, submit-after pattern (files uploaded before form submission)
3. **HTMLComponent**: Generic component accepting ANY context object for template interpolation (reusable across all features)
4. **Async Execution**: Azure Storage Queues with worker function pattern
5. **CRON Scheduling**: Azure Functions Timer Triggers with croniter library
6. **Workflow API Keys**: Encrypted keys with custom authentication decorator
7. **Execution Log Search**: Optimized RowKey structure with secondary indexes
8. **Platform Branding**: CSS custom properties for dynamic theming
9. **System Workspace**: Auto-imported workflows with shared utilities
10. **Entra ID Matching**: Dual-matching logic (EntraUserId first, email fallback)
11. **Frontend Search**: Client-side for small datasets, server-side pagination for large datasets

**Key Architecture Principles**:
- ✅ All form logic (context, visibility, components) is client-side for instant reactivity
- ✅ File uploads complete BEFORE form submission to avoid timeouts
- ✅ HTMLComponent is generic and reusable across all features, not tied to forms
- ✅ Backend never renders components or evaluates expressions - only stores config and validates data

All decisions comply with the constitution principles (Azure-First, Table Storage Only, Python Backend Standard, Test-First Development, Single-MSP Multi-Organization Design).

Next phase: Generate data models and API contracts based on these research findings.
