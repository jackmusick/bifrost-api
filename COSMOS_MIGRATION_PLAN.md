# CosmosDB Migration Plan: Table Storage → CosmosDB

**Status**: Planning Phase
**Target**: Full migration from Azure Table Storage to Azure CosmosDB (Serverless)
**Timeline**: ~5-7 days development
**Cost Impact**: ~$20-30/month (from ~$0.37/month)

---

## Executive Summary

Migrate Bifrost from Azure Table Storage to CosmosDB to achieve:
- **Simpler architecture**: 6 writes per execution → 1 write (removes manual index management)
- **ACID transactions**: Fixes TODO comments about rollback logic
- **Rich SQL queries**: Multi-field filtering without manual indexes
- **Auto-cleanup**: TTL-based deletion of old executions (14-day retention)
- **Real-time updates**: Change Feed for dashboard (bonus feature)

---

## Architecture Changes

### Current State: Table Storage (3 tables)

```
Table 1: "Config"
- OAuth tokens, secrets, API keys, configuration
- Partition: org_id or "GLOBAL"

Table 2: "Entities"
- Users, Orgs, Roles, Forms, Executions, OAuth, Branding
- Partition: org_id or "GLOBAL"
- RowKey patterns: org:{id}, user:{email}, role:{id}, form:{id}, execution:{reverse_ts}_{id}

Table 3: "Relationships"
- Execution indexes: userexec:{user_id}:{exec_id}, workflowexec:{workflow}:{org}:{exec_id}
- Other indexes: userrole:{user_id}:{role_id}, formrole:{form_id}:{role_id}
- Partition: Always "GLOBAL"

Total writes per execution: 6 operations
1. Primary record (Entities)
2. User index (Relationships)
3. Workflow index (Relationships)
4. Form index (Relationships, if applicable)
5. Status index (Relationships)
6. Update on completion (Primary + 4 indexes = 5 updates)
```

### Target State: CosmosDB (Serverless, 2 containers)

```
Database: "bifrost"

Container 1: "entities"
- Partition Key: /scope (handles "GLOBAL" and "org-{uuid}")
- TTL: None (permanent data)
- Document types: user, organization, role, form, oauth_connection, config, branding
- Estimated size: ~100MB (slow growth)

Container 2: "executions"
- Partition Key: /scope
- TTL: 1209600 seconds (14 days auto-delete)
- Document types: execution
- Estimated size: ~2-5GB (steady state with TTL)
- Optimized indexing for time-series queries

Blob Storage: "execution-data" (unchanged)
- Results (>32KB)
- Logs (always)
- Variables (always)
- Snapshots (always)
- Lifecycle: Delete after 14 days (matches TTL)

Total writes per execution: 1 operation
- Single document write to CosmosDB (all fields auto-indexed)
```

---

## Document Schema Design

### Unified "scope" Field

All documents use a single `scope` field instead of separate `orgId`/`isGlobal`:

```json
{
  "scope": "GLOBAL"  // or "org-{uuid}"
}
```

**Entities that can be GLOBAL or org-scoped:**
- Users (platform admins = GLOBAL, org users = org-{uuid})
- Forms (global forms = GLOBAL, org-specific = org-{uuid})
- Executions (cross-org workflows = GLOBAL, org workflows = org-{uuid})
- OAuth connections (platform OAuth = GLOBAL, org OAuth = org-{uuid})
- Config (platform config = GLOBAL, org config = org-{uuid})

**Entities always scoped to org:**
- Roles (always org-{uuid})
- Branding (always org-{uuid})

**Entities always GLOBAL:**
- Organizations (always GLOBAL, scope = own ID for consistency)

### Container 1: "entities" Documents

#### User Document
```json
{
  "id": "user-admin@example.com",
  "type": "user",
  "scope": "GLOBAL",  // Partition key
  "email": "admin@example.com",
  "displayName": "Admin User",
  "userType": "PLATFORM",
  "isPlatformAdmin": true,
  "isActive": true,
  "lastLogin": "2025-01-26T10:00:00Z",
  "createdAt": "2024-01-01T00:00:00Z",
  "entraUserId": "azure-ad-oid-123",
  "lastEntraIdSync": "2025-01-26T10:00:00Z"
}
```

#### Organization Document
```json
{
  "id": "org-123",
  "type": "organization",
  "scope": "org-123",  // Partition key = own ID
  "name": "Acme Corp",
  "domain": "acme.com",
  "isActive": true,
  "createdAt": "2024-01-15T00:00:00Z",
  "createdBy": "admin@example.com",
  "updatedAt": "2025-01-26T10:00:00Z"
}
```

#### Role Document
```json
{
  "id": "role-abc-123",
  "type": "role",
  "scope": "org-123",  // Partition key (roles are org-scoped)
  "name": "Technician",
  "description": "Field technician role",
  "isActive": true,
  "createdBy": "admin@acme.com",
  "createdAt": "2024-02-01T00:00:00Z",
  "updatedAt": "2025-01-26T10:00:00Z"
}
```

#### Form Document
```json
{
  "id": "form-xyz-456",
  "type": "form",
  "scope": "GLOBAL",  // Can be GLOBAL or org-{uuid}
  "name": "User Onboarding",
  "description": "Standard user onboarding form",
  "linkedWorkflow": "onboard_user",
  "formSchema": {
    "fields": [
      {
        "name": "email",
        "label": "Email Address",
        "type": "email",
        "required": true
      }
    ]
  },
  "isActive": true,
  "isGlobal": true,
  "accessLevel": "role_based",
  "createdBy": "admin@example.com",
  "createdAt": "2024-03-01T00:00:00Z",
  "updatedAt": "2025-01-26T10:00:00Z",
  "launchWorkflowId": null,
  "allowedQueryParams": ["userId"],
  "defaultLaunchParams": {}
}
```

#### Config Document
```json
{
  "id": "config-msgraph-client-secret",
  "type": "config",
  "scope": "GLOBAL",  // Can be GLOBAL or org-{uuid}
  "key": "msgraph_client_secret",
  "value": null,  // Not stored for secret_ref type
  "secretRef": "kv-secret-msgraph-client-secret",  // Points to Key Vault
  "configType": "secret_ref",
  "description": "Microsoft Graph API client secret",
  "updatedAt": "2025-01-26T10:00:00Z",
  "updatedBy": "admin@example.com"
}
```

#### OAuth Connection Document
```json
{
  "id": "oauth-msgraph",
  "type": "oauth_connection",
  "scope": "GLOBAL",  // Can be GLOBAL or org-{uuid}
  "connectionName": "msgraph",
  "description": "Microsoft Graph API connection",
  "oauthFlowType": "authorization_code",
  "clientId": "abc-123-def",
  "clientSecretRef": "oauth_msgraph_client_secret",
  "oauthResponseRef": "oauth_msgraph_oauth_response",
  "authorizationUrl": "https://login.microsoftonline.com/.../authorize",
  "tokenUrl": "https://login.microsoftonline.com/.../token",
  "scopes": "User.Read Mail.Send",
  "redirectUri": "/api/oauth/callback/msgraph",
  "tokenType": "Bearer",
  "expiresAt": "2025-01-26T11:00:00Z",
  "status": "completed",
  "statusMessage": "Connected successfully",
  "lastRefreshAt": "2025-01-26T10:00:00Z",
  "lastTestAt": "2025-01-26T09:00:00Z",
  "createdAt": "2024-04-01T00:00:00Z",
  "createdBy": "admin@example.com",
  "updatedAt": "2025-01-26T10:00:00Z"
}
```

#### Branding Document
```json
{
  "id": "branding-org-123",
  "type": "branding",
  "scope": "org-123",  // Always org-scoped
  "squareLogoUrl": "https://storage.../logo-square.png",
  "rectangleLogoUrl": "https://storage.../logo-rect.png",
  "primaryColor": "#FF5733",
  "updatedBy": "admin@acme.com",
  "updatedAt": "2025-01-26T10:00:00Z"
}
```

### Container 2: "executions" Documents

#### Execution Document (Small Result - Inline)
```json
{
  "id": "exec-abc-123",
  "type": "execution",
  "scope": "org-123",  // Partition key
  "executionId": "exec-abc-123",  // Same as id
  "workflowName": "create_user",
  "formId": "form-xyz-456",
  "executedBy": "john@acme.com",
  "executedByName": "John Doe",
  "status": "Success",
  "inputData": {
    "email": "newuser@acme.com",
    "name": "New User"
  },
  "result": {  // Inline (native JSON object, not string!)
    "userId": "user-123",
    "status": "created"
  },
  "resultType": "json",
  "resultInBlob": false,
  "resultSize": 1024,
  "errorMessage": null,
  "durationMs": 1234,
  "startedAt": "2025-01-26T10:00:00Z",
  "completedAt": "2025-01-26T10:00:01Z",
  "logs": null,  // Always in blob
  "logsBlobPath": "exec-abc-123/logs.json",
  "variables": null,  // Always in blob
  "variablesBlobPath": "exec-abc-123/variables.json",
  "ttl": 1209600,  // Auto-delete after 14 days
  "_ts": 1706266800  // CosmosDB auto-timestamp
}
```

#### Execution Document (Large Result - In Blob)
```json
{
  "id": "exec-def-456",
  "type": "execution",
  "scope": "org-123",
  "executionId": "exec-def-456",
  "workflowName": "generate_report",
  "formId": null,
  "executedBy": "jane@acme.com",
  "executedByName": "Jane Smith",
  "status": "Success",
  "inputData": {
    "reportType": "monthly",
    "month": "2025-01"
  },
  "result": null,  // NOT stored inline (>32KB)
  "resultType": "html",
  "resultInBlob": true,
  "resultSize": 524288,  // 512KB
  "resultBlobPath": "exec-def-456/result.html",
  "errorMessage": null,
  "durationMs": 45000,
  "startedAt": "2025-01-26T10:00:00Z",
  "completedAt": "2025-01-26T10:00:45Z",
  "logsBlobPath": "exec-def-456/logs.json",
  "variablesBlobPath": "exec-def-456/variables.json",
  "snapshotBlobPath": "exec-def-456/snapshot.json",
  "ttl": 1209600
}
```

---

## Blob Storage Pattern (Preserved Exactly)

### Current Behavior (No Changes)

**Result Storage Logic** (shared/execution_logger.py):
```python
BLOB_THRESHOLD_BYTES = 32_768  # 32KB

if result is not None:
    result_json = json.dumps(result) if isinstance(result, dict) else result
    result_size = len(result_json.encode('utf-8'))

    if result_size > BLOB_THRESHOLD_BYTES:  # > 32KB
        blob_service.upload_result(execution_id, result)
        result_in_blob = True
        result = None  # Don't store inline in DB
    else:
        result_in_blob = False  # Store inline in DB
```

**Blob Upload** (shared/blob_storage.py):
```python
def upload_result(execution_id: str, result: dict | str) -> str:
    """
    Determines file extension based on content type:
    - dict → result.json (with JSON.dumps, indent=2)
    - str starting with '<' → result.html
    - str (other) → result.txt

    Uploads to: executions/{execution_id}/result.{ext}
    """
```

**Always in Blob** (no size check):
- Logs → `{execution_id}/logs.json`
- Variables → `{execution_id}/variables.json`
- Snapshots → `{execution_id}/snapshot.json`

**Blob Retrieval**:
```python
def get_result(execution_id: str) -> dict | str | None:
    """
    Tries extensions in order: .json, .html, .txt
    Returns parsed JSON (dict) or raw string
    """
```

### Migration: Zero Changes to Blob Logic

✅ **32KB threshold** - unchanged
✅ **Content type detection** - same HTML detection logic
✅ **Blob path format** - `{id}/result.{ext}`
✅ **Retrieval order** - .json → .html → .txt
✅ **Logs/variables/snapshots** - always in blob
✅ **`resultInBlob` flag** - preserved in CosmosDB document
✅ **`resultType` metadata** - preserved (json/html/text)

**Only difference**: CosmosDB stores `result` as native JSON object (not JSON string)

---

## Query Pattern Comparison

### Current: Table Storage

```python
# User's executions (requires index table)
filter = f"PartitionKey eq 'GLOBAL' and RowKey ge 'userexec:{user_id}:' and RowKey lt 'userexec:{user_id}~'"
user_execs = await relationships_table.query(filter)

# Failed executions for workflow (requires multiple queries + in-memory filter)
workflow_filter = f"PartitionKey eq 'GLOBAL' and RowKey ge 'workflowexec:{workflow}:' ..."
workflow_execs = await relationships_table.query(workflow_filter)
failed = [e for e in workflow_execs if e['Status'] == 'Failed']

# Dashboard metrics (requires scanning + aggregation in code)
all_execs = await entities_table.query(f"PartitionKey eq '{org_id}' and RowKey ge 'execution:' ...")
success_count = sum(1 for e in all_execs if e['Status'] == 'Success')
```

### Target: CosmosDB

```sql
-- User's executions (single query, no indexes!)
SELECT * FROM c
WHERE c.scope = 'org-123'
  AND c.type = 'execution'
  AND c.executedBy = 'user@example.com'
ORDER BY c.startedAt DESC

-- Failed executions for workflow (single query with multiple filters)
SELECT * FROM c
WHERE c.scope = 'org-123'
  AND c.type = 'execution'
  AND c.status = 'Failed'
  AND c.workflowName = 'create_user'
  AND c.startedAt > '2025-01-20'
ORDER BY c.startedAt DESC

-- Dashboard metrics (aggregation in query)
SELECT
  COUNT(1) as total,
  SUM(c.status = 'Success' ? 1 : 0) as successCount,
  SUM(c.status = 'Failed' ? 1 : 0) as failedCount,
  AVG(c.durationMs) as avgDuration
FROM c
WHERE c.scope = 'org-123'
  AND c.type = 'execution'
  AND c.startedAt > '2025-01-19'
```

---

## Indexing Strategy

### Container: "entities"

```json
{
  "indexingMode": "consistent",
  "automatic": true,
  "includedPaths": [
    {"path": "/*"}
  ],
  "excludedPaths": [
    {"path": "/formSchema/*"},  // Don't index large nested schemas
    {"path": "/_etag/?"}
  ]
}
```

**Auto-indexed fields:**
- `scope` (partition key, always indexed)
- `type` (for filtering by entity type)
- `email`, `displayName`, `name`, `isActive`, etc. (all top-level fields)

### Container: "executions"

```json
{
  "indexingMode": "consistent",
  "automatic": true,
  "includedPaths": [
    {"path": "/scope/*"},
    {"path": "/type/*"},
    {"path": "/status/*"},
    {"path": "/workflowName/*"},
    {"path": "/executedBy/*"},
    {"path": "/startedAt/*"},
    {"path": "/completedAt/*"},
    {"path": "/formId/*"}
  ],
  "excludedPaths": [
    {"path": "/inputData/*"},  // Don't index large input objects
    {"path": "/result/*"},     // Don't index result (often large or in blob)
    {"path": "/variables/*"},  // Don't index (always in blob anyway)
    {"path": "/_etag/?"}
  ]
}
```

**Optimized for time-series queries:**
- Status filtering (Success, Failed, Running, etc.)
- Workflow filtering
- User filtering
- Date range queries
- Form submission queries

---

## Migration Steps

### Phase 1: Infrastructure Setup (Day 1)

**1. Create CosmosDB Account**
```bash
az cosmosdb create \
  --name bifrost-cosmos \
  --resource-group bifrost-rg \
  --locations regionName=EastUS \
  --capabilities EnableServerless
```

**2. Create Database**
```bash
az cosmosdb sql database create \
  --account-name bifrost-cosmos \
  --name bifrost
```

**3. Create Containers**
```bash
# Container 1: entities (permanent)
az cosmosdb sql container create \
  --account-name bifrost-cosmos \
  --database-name bifrost \
  --name entities \
  --partition-key-path "/scope"

# Container 2: executions (14-day TTL)
az cosmosdb sql container create \
  --account-name bifrost-cosmos \
  --database-name bifrost \
  --name executions \
  --partition-key-path "/scope" \
  --ttl 1209600
```

**4. Configure Connection Strings**
```bash
# Add to local.settings.json and Azure App Settings
CosmosDBConnection="AccountEndpoint=https://bifrost-cosmos.documents.azure.com:443/;AccountKey=..."
```

### Phase 2: Repository Layer (Days 2-3)

**1. Create CosmosDB Service Layer**
- File: `shared/cosmos_storage.py`
- Wrapper around Azure CosmosDB SDK
- Methods: `create_item`, `read_item`, `query_items`, `replace_item`, `delete_item`
- Context-aware (auto-applies scope from ExecutionContext)

**2. Create CosmosDB Repository Base**
- File: `shared/repositories/cosmos_base.py`
- Base class similar to current `BaseRepository`
- Methods: `create`, `get_by_id`, `query`, `update`, `delete`

**3. Implement Entity Repositories**
- `CosmosUserRepository`
- `CosmosOrganizationRepository`
- `CosmosRoleRepository`
- `CosmosFormRepository`
- `CosmosConfigRepository`
- `CosmosOAuthRepository`
- `CosmosBrandingRepository`

**4. Implement Execution Repository**
- File: `shared/repositories/cosmos_executions.py`
- Key difference: No index management! Single document writes
- Methods: `create_execution`, `update_execution`, `get_execution`, `query_executions`

**5. Update ExecutionLogger**
- File: `shared/execution_logger.py`
- Change: `self.repository = CosmosExecutionRepository()` (was `ExecutionRepository`)
- **No changes to blob logic** - stays identical

### Phase 3: Handler Updates (Days 4-5)

**1. Update Repository Imports**
- Search/replace: `from shared.repositories.xxx import YyyRepository`
- Replace with: `from shared.repositories.cosmos_xxx import CosmosYyyRepository`

**2. Update Handler Functions**
- No logic changes, just use new repositories
- Example: `users_handlers.py`, `forms_handlers.py`, etc.

**3. Remove Index Management Code**
- Delete: `shared/repositories/executions.py` index logic (5 index writes)
- Delete: Relationship table queries for executions
- Keep: Relationship table for user-role, form-role mappings

**4. Update Queries**
- Convert Table Storage filter syntax to CosmosDB SQL
- Example: `PartitionKey eq 'org-123' and Status eq 'Failed'`
- Becomes: `WHERE c.scope = 'org-123' AND c.status = 'Failed'`

### Phase 4: Testing (Day 5)

**1. Update Test Fixtures**
- Create CosmosDB emulator setup in docker-compose.yml
- Update `tests/conftest.py` to initialize CosmosDB containers
- Update seed data scripts

**2. Update Integration Tests**
- Change: Test setup to use CosmosDB
- Update: Execution creation/query tests
- Add: TTL validation tests

**3. Run Full Test Suite**
```bash
cd api
./test.sh  # Should start CosmosDB emulator + run all tests
```

### Phase 5: Local Development Setup (Day 6)

**1. Update docker-compose.yml**
```yaml
services:
  azurite:
    image: mcr.microsoft.com/azure-storage/azurite
    ports:
      - "10000:10000"  # Blob
      - "10001:10001"  # Queue
      - "10002:10002"  # Table

  cosmos-emulator:
    image: mcr.microsoft.com/cosmosdb/linux/azure-cosmos-emulator
    ports:
      - "8081:8081"
      - "10251:10251"
      - "10252:10252"
      - "10253:10253"
      - "10254:10254"
    environment:
      - AZURE_COSMOS_EMULATOR_PARTITION_COUNT=10
      - AZURE_COSMOS_EMULATOR_ENABLE_DATA_PERSISTENCE=true
    volumes:
      - cosmos-data:/tmp/cosmos
```

**2. Update ./test.sh**
```bash
#!/bin/bash

# Start dependencies
docker compose up -d azurite cosmos-emulator

# Wait for Cosmos emulator (~30s startup)
echo "Waiting for Cosmos emulator..."
timeout 60 bash -c 'until curl -k https://localhost:8081 2>/dev/null; do sleep 1; done'

# Set environment variables
export AzureWebJobsStorage="UseDevelopmentStorage=true"
export CosmosDBConnection="AccountEndpoint=https://localhost:8081/;AccountKey=C2y6yDjf5/R+ob0N8A7Cgv..."

# Initialize CosmosDB (create database + containers)
python -m shared.init_cosmos

# Run tests
pytest "$@"
```

**3. Create Initialization Script**
- File: `shared/init_cosmos.py`
- Creates database and containers if not exist
- Sets up indexing policies

### Phase 6: Deployment (Day 7)

**1. Update Infrastructure (Bicep/ARM)**
- Add CosmosDB account resource
- Add connection string to App Settings
- Keep Table Storage (for gradual migration if needed)

**2. Deploy to Development Environment**
- Create CosmosDB account
- Run database initialization
- Deploy updated Function App

**3. Seed Initial Data**
```bash
python seed_data_cosmos.py  # New script for CosmosDB
```

**4. Validation**
- Run smoke tests
- Check dashboard queries
- Verify execution creation
- Test TTL cleanup (create old execution, wait 14 days)

**5. Remove Table Storage Code**
- Delete old repository files
- Remove Table Storage initialization
- Clean up unused imports

---

## Rollback Plan

**If issues arise during migration:**

1. **Keep both implementations for 30 days**
   - Old: `shared/repositories/*.py` (Table Storage)
   - New: `shared/repositories/cosmos_*.py` (CosmosDB)
   - Easy to switch back via imports

2. **Feature flag approach**
   ```python
   USE_COSMOS = os.getenv("USE_COSMOS_DB", "true") == "true"

   if USE_COSMOS:
       from shared.repositories.cosmos_executions import CosmosExecutionRepository as ExecutionRepository
   else:
       from shared.repositories.executions import ExecutionRepository
   ```

3. **Data safety**
   - No data deletion during migration (Table Storage stays intact)
   - Can replay from Table Storage to CosmosDB if needed
   - Blob storage unchanged (shared between both)

---

## Testing Strategy

### Unit Tests
- Mock CosmosDB client (similar to current Table Storage mocks)
- Test repository CRUD operations
- Test query building and filtering
- Test TTL handling

### Integration Tests
- Use CosmosDB emulator (docker)
- Test execution lifecycle (create → update → query → TTL delete)
- Test cross-entity queries (user + executions)
- Test Change Feed triggers

### Performance Tests
- Benchmark query performance (Table Storage vs CosmosDB)
- Test RU consumption for common operations
- Validate 14-day TTL cleanup works correctly

### Migration Tests
- Convert existing Table Storage test data to CosmosDB format
- Verify all endpoints return same results
- Test backward compatibility of API responses

---

## Cost Analysis

### Current: Table Storage
```
Storage:        6GB × $0.045/GB         = $0.27/month
Transactions:   200K × $0.036/million   = $0.007/month
Blob Storage:   5GB × $0.018/GB         = $0.09/month
────────────────────────────────────────────────────
TOTAL: ~$0.37/month
```

### Target: CosmosDB Serverless

**Assumptions:**
- 50,000 executions/month (~1,600/day)
- 100,000 execution queries/month
- 50,000 entity queries/month (users, forms, etc.)
- 6GB total storage (entities + 14 days of executions)

**RU Calculation:**
```
Execution writes:     50K × 700 RU     = 35M RUs
Execution queries:    100K × 10 RU     = 1M RUs
Entity queries:       50K × 2 RU       = 0.1M RUs
────────────────────────────────────────────────────
TOTAL: ~36M RUs/month
```

**Cost:**
```
RUs:            36M × $0.25/million     = $9.00/month
Storage:        6GB × $0.25/GB          = $1.50/month
Blob Storage:   5GB × $0.018/GB         = $0.09/month
────────────────────────────────────────────────────
TOTAL: ~$10.59/month
```

**Cost increase:** $10.22/month (+2,762%)

**Value proposition:**
- Developer time saved: ~2-3 hours/month (no index management)
- At $100/hr: $200-300/month savings
- **ROI: 20-30x** return on infrastructure cost

---

## Risk Assessment

### Low Risk
✅ **Blob storage unchanged** - Zero risk to existing result/log storage
✅ **API endpoints unchanged** - No client-side changes needed
✅ **Gradual migration** - Can keep Table Storage as fallback
✅ **Proven technology** - CosmosDB is mature, well-documented

### Medium Risk
⚠️ **Query performance** - Need to validate CosmosDB queries are fast enough
⚠️ **RU consumption** - Monitor costs don't exceed estimates
⚠️ **TTL timing** - Ensure 14-day cleanup works reliably

**Mitigation:**
- Performance testing before production deployment
- Set up cost alerts in Azure ($20/month threshold)
- Test TTL with accelerated timeline (1 hour TTL in dev)

### High Risk (None)
- No data loss risk (Table Storage preserved)
- No breaking API changes
- Rollback plan available

---

## Success Criteria

### Functional
✅ All endpoints return identical data to Table Storage version
✅ Execution creation completes in <500ms (same as current)
✅ Execution queries return in <100ms (same or faster)
✅ TTL cleanup removes 14-day-old executions automatically
✅ All tests pass (100% success rate)

### Non-Functional
✅ Monthly cost stays under $25
✅ RU consumption stays under 50M/month
✅ No manual index management code remaining
✅ Zero TODO comments about rollback/atomicity
✅ Change Feed dashboard updates working (bonus feature)

---

## Post-Migration Cleanup

### Code Cleanup
- [ ] Delete `shared/repositories/executions.py` (old Table Storage version)
- [ ] Delete execution-related code from `shared/repositories/base.py`
- [ ] Remove `Relationships` table initialization for executions
- [ ] Clean up imports (remove Table Storage execution repository)

### Documentation Updates
- [ ] Update README with CosmosDB setup instructions
- [ ] Update local development guide (Cosmos emulator)
- [ ] Document query patterns (SQL vs Table Storage filters)
- [ ] Update cost estimates in project docs

### Monitoring
- [ ] Set up CosmosDB metrics dashboard (RU consumption, latency)
- [ ] Configure cost alerts ($20/month threshold)
- [ ] Monitor TTL cleanup (track execution counts over time)
- [ ] Add logging for Change Feed processing

---

## Open Questions

1. **CRON schedules**: Confirmed they're just workflow metadata (no container needed)
2. **Relationships table**: Keep for user-role, form-role mappings (not migrating to CosmosDB)
3. **Config storage**: Migrate to CosmosDB, keep Key Vault for secrets
4. **Local emulator**: CosmosDB Linux emulator works on Docker
5. **Real-time updates**: Change Feed is a bonus feature (not required for MVP)

---

## Next Steps

1. **Review this plan** - Get stakeholder approval
2. **Set up dev environment** - Install CosmosDB emulator locally
3. **Create prototype** - Build CosmosExecutionRepository and test
4. **Performance benchmark** - Compare Table Storage vs CosmosDB queries
5. **Begin migration** - Follow 7-day timeline above

---

**Prepared by**: Claude Code
**Date**: 2025-01-26
**Status**: Ready for Implementation
