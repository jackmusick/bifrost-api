# Data Model: Platform Enhancement Suite

## Entity Definitions

### 1. FormContext (Runtime Object)
- **Type**: Runtime JavaScript/TypeScript Object
- **Attributes**:
  - `workflow_result` (any | null): Results from launch workflow
  - `params` (Record<string, string>): Query parameters
  - `field` (Record<string, any>): Field values by field name
- **Not Stored**: Exists only during form interaction

### 2. WorkflowKey
- **Table**: `WorkflowKeys`
- **Partition Key**: "GLOBAL"
- **Row Key**: `workflowkey:{key_id}`
- **Attributes**:
  - `HashedKey` (string): Hashed API key for security
  - `WorkflowId` (string | null): Specific workflow or null for global key
  - `CreatedAt` (datetime): Key creation timestamp
  - `CreatedBy` (string): User ID who created the key
  - `LastUsedAt` (datetime | null): Timestamp of last usage
  - `Revoked` (boolean): Whether key is invalidated

### 3. AsyncExecution
- **Table**: `Executions`
- **Partition Key**: Organization ID
- **Row Key**: `exec:{reverse_timestamp}:{execution_id}`
- **Attributes**:
  - `ExecutionId` (string): Unique identifier
  - `WorkflowId` (string): Workflow being executed
  - `UserId` (string): User triggering execution
  - `Status` (string): "queued", "running", "completed", "failed"
  - `Parameters` (string/JSON): Execution parameters
  - `Context` (string/JSON): Execution context (org, user, scope)
  - `Result` (string/JSON | null): Execution results
  - `Error` (string | null): Error details for failed executions
  - `QueuedAt` (datetime)
  - `StartedAt` (datetime | null)
  - `CompletedAt` (datetime | null)

### 4. CronSchedule
- **Table**: `Schedules`
- **Partition Key**: "GLOBAL"
- **Row Key**: `schedule:{schedule_id}`
- **Attributes**:
  - `WorkflowId` (string): Workflow to execute
  - `CronExpression` (string): Standard 5-field CRON expression
  - `Enabled` (boolean): Whether schedule is active
  - `NextRunAt` (datetime): Calculated next execution time
  - `LastRunAt` (datetime | null): Last execution timestamp
  - `CreatedAt` (datetime)
  - `CreatedBy` (string): User who created schedule

### 5. BrandingSettings
- **Table**: `Config`
- **Partition Key**: Organization ID or "GLOBAL"
- **Row Key**: "branding"
- **Attributes**:
  - `SquareLogoUrl` (string | null): Sidebar logo URL
  - `RectangleLogoUrl` (string | null): Form header logo URL
  - `PrimaryColor` (string | null): Hex color code
  - `CreatedAt` (datetime)
  - `UpdatedBy` (string): User who last modified branding

### 6. FileUpload
- **Table**: `Forms`
- **Metadata Fields**:
  - `FileUrls` (string[]): Blob Storage URIs
  - `FileNames` (string[]): Original file names
  - `FileSizes` (number[]): File sizes
  - `FileTypes` (string[]): MIME types
- **Blob Storage**:
  - Container: `uploads`
  - Blob Names: Random UUIDs for security
  - SAS Token: Write-only, 15-minute expiration

### 7. EntraIdMapping
- **Table**: `Users`
- **Extends**: Existing Users table
- **Additional Fields**:
  - `EntraUserId` (string | null): Entra ID user identifier
  - `LastEntraIdSync` (datetime | null): Last sync timestamp