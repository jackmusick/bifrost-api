# CosmosDB Migration Plan: Table Storage → CosmosDB

**Status**: Planning Phase
**Target**: Full migration from Azure Table Storage to Azure CosmosDB (Serverless)
**Timeline**: Phase 1 (MVP): ~7 days | Phase 2 (Real-Time): ~5 days | Phase 3 (Optimization): ~3 days
**Cost Impact**: Phase 1: ~$11/month | Phase 2: ~$13/month | Phase 3: Same (~$13/month)

---

## Executive Summary

Migrate Bifrost from Azure Table Storage to CosmosDB in three phases:

**Phase 1 - Migration MVP** (7 days):
- **Simpler architecture**: 6 writes per execution → 1 write (removes manual index management)
- **ACID transactions**: Fixes TODO comments about rollback logic
- **Rich SQL queries**: Multi-field filtering without manual indexes
- **Auto-cleanup**: TTL-based deletion of old executions (14-day retention)

**Phase 2 - Real-Time Logs** (5 days):
- **Real-time log streaming**: Logs appear in UI as workflow executes
- **SignalR integration**: Change Feed → SignalR → instant UI updates
- **Better debugging**: See variables and state changes in real-time

**Phase 3 - Dashboard Optimization** (3 days):
- **Pre-aggregated metrics**: Fast dashboard loads (<100ms)
- **Historical analytics**: Daily rollups for trend analysis
- **Efficient queries**: Avoid expensive cross-partition scans

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

### Target State: CosmosDB (Serverless, 3 containers)

```
Database: "bifrost"

Container 1: "entities"
- Partition Key: /scope (handles "GLOBAL" and "org-{uuid}")
- TTL: None (permanent data)
- Document types:
  • user, organization, role, form, oauth_connection, config, branding
  • metrics (daily aggregates - Phase 3)
- Estimated size: ~100MB (slow growth)

Container 2: "executions"
- Partition Key: /scope
- TTL: 1209600 seconds (14 days auto-delete)
- Document types: execution (metadata only - no logs/variables/result)
- Estimated size: ~500MB-1GB (steady state with TTL)
- Optimized indexing for time-series queries

Container 3: "execution_data" (Phase 2)
- Partition Key: /executionId
- TTL: 1209600 seconds (14 days auto-delete)
- Document types:
  • log (individual log entries)
  • variables (variable snapshots)
  • result (execution results, even large ones)
  • state (state snapshots)
- Enables real-time streaming via Change Feed
- Estimated size: ~1-2GB (steady state with TTL)

Blob Storage: "execution-data" (fallback only)
- Use only for results/logs exceeding CosmosDB 2MB document limit
- Most executions won't need blob storage anymore
```

**Total writes per execution:**
- Phase 1: 1 operation (execution metadata)
- Phase 2: 1 + ~10 logs + 1 result + variables = ~15 operations (but streamed in real-time!)

---

## Unified "scope" Field

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

---

## Document Schemas

### Container 1: "entities"

#### Execution Metadata (Phase 1)
```json
{
  "id": "exec-abc-123",
  "type": "execution",
  "scope": "org-123",  // Partition key
  "executionId": "exec-abc-123",
  "workflowName": "create_user",
  "formId": "form-xyz-456",
  "executedBy": "john@acme.com",
  "executedByName": "John Doe",
  "status": "Success",
  "inputData": {"email": "newuser@acme.com", "name": "New User"},
  "durationMs": 1234,
  "startedAt": "2025-01-26T10:00:00Z",
  "completedAt": "2025-01-26T10:00:01Z",
  "errorMessage": null,
  "ttl": 1209600  // Auto-delete after 14 days
}
```

#### Daily Metrics (Phase 3)
```json
{
  "id": "metrics-daily-2025-01-26",
  "type": "metrics",
  "scope": "org-123",
  "date": "2025-01-26",
  "totalExecutions": 1234,
  "successCount": 1100,
  "failedCount": 134,
  "timeoutCount": 0,
  "totalDurationMs": 4567890,
  "avgDurationMs": 3702,
  "workflows": {
    "create_user": {
      "count": 500,
      "successCount": 490,
      "failedCount": 10,
      "avgDurationMs": 1234
    }
  }
}
```

### Container 3: "execution_data" (Phase 2)

#### Log Entry (Streamed in Real-Time)
```json
{
  "id": "log-001",
  "executionId": "exec-abc-123",  // Partition key
  "type": "log",
  "timestamp": "2025-01-26T10:00:01.234Z",
  "level": "info",
  "message": "Processing user creation",
  "data": {"userId": "123"},
  "ttl": 1209600
}
```

#### Variable Snapshot
```json
{
  "id": "variables-snapshot-v5",
  "executionId": "exec-abc-123",  // Partition key
  "type": "variables",
  "timestamp": "2025-01-26T10:00:05.123Z",
  "version": 5,  // Increments with each update
  "variables": {
    "user": {"email": "new@example.com"},
    "config": {"retryCount": 3}
  },
  "ttl": 1209600
}
```

#### Result (In CosmosDB, Not Blob!)
```json
{
  "id": "result",
  "executionId": "exec-abc-123",  // Partition key
  "type": "result",
  "timestamp": "2025-01-26T10:00:10.000Z",
  "result": {
    "userId": "user-123",
    "status": "created",
    "details": { /* ...up to 2MB of data... */ }
  },
  "resultType": "json",
  "resultSize": 524288,
  "ttl": 1209600
}
```

---

## Real-Time Streaming Architecture (Phase 2)

### Workflow Engine → CosmosDB → Change Feed → SignalR → UI

```python
# 1. Workflow engine logs (during execution)
async def log_info(message: str, data: dict = None):
    """Write log to CosmosDB - triggers Change Feed automatically"""
    await cosmos_client.create_item(
        container="execution_data",
        partition_key=execution_id,
        body={
            "id": f"log-{uuid.uuid4()}",
            "executionId": execution_id,
            "type": "log",
            "timestamp": datetime.utcnow().isoformat(),
            "level": "info",
            "message": message,
            "data": data,
            "ttl": 1209600
        }
    )
```

```python
# 2. Change Feed processor (Azure Function)
@app.cosmos_db_trigger(
    database="bifrost",
    container="execution_data",
    lease_container="leases"
)
async def on_execution_data_changed(documents: List[Document]):
    """Push real-time updates to SignalR"""
    for doc in documents:
        execution_id = doc['executionId']

        if doc['type'] == 'log':
            # Push log to UI immediately
            await signalr_output.send({
                'target': 'executionLog',
                'arguments': [{
                    'executionId': execution_id,
                    'timestamp': doc['timestamp'],
                    'level': doc['level'],
                    'message': doc['message']
                }]
            })

        elif doc['type'] == 'variables':
            # Push variable update to UI
            await signalr_output.send({
                'target': 'executionVariables',
                'arguments': [{
                    'executionId': execution_id,
                    'variables': doc['variables']
                }]
            })
```

```typescript
// 3. UI (React) - Real-time updates
useEffect(() => {
  const connection = new HubConnectionBuilder()
    .withUrl('/api/signalr')
    .build()

  // Real-time log streaming
  connection.on('executionLog', (log) => {
    setLogs(prev => [...prev, log])  // Append instantly!
  })

  // Real-time variable updates
  connection.on('executionVariables', (vars) => {
    setVariables(vars.variables)  // Update instantly!
  })

  connection.start()
}, [])
```

---

## Dashboard Architecture (Phase 3)

### Problem: Expensive Live Queries

```sql
-- This is SLOW and EXPENSIVE (50K executions × 5 RU = 250K RUs per dashboard load!)
SELECT
  COUNT(1) as total,
  SUM(c.status = 'Success' ? 1 : 0) as successCount,
  SUM(c.status = 'Failed' ? 1 : 0) as failedCount
FROM c
WHERE c.scope = 'org-123'
  AND c.type = 'execution'
  AND c.startedAt >= '2024-12-27T00:00:00Z'
```

### Solution: Pre-Aggregated Metrics

#### Option A: Change Feed Aggregation (Real-Time)
```python
@app.cosmos_db_trigger(container="executions")
async def aggregate_metrics(documents: List[Document]):
    """Update daily metrics as executions complete"""
    for doc in documents:
        if doc['status'] in ['Success', 'Failed', 'Timeout']:
            date = doc['completedAt'][:10]  # "2025-01-26"
            scope = doc['scope']

            # Get today's metrics
            metrics_id = f"metrics-daily-{date}"
            metrics = await get_or_create_metrics(scope, metrics_id, date)

            # Increment counters
            metrics['totalExecutions'] += 1
            if doc['status'] == 'Success':
                metrics['successCount'] += 1
            elif doc['status'] == 'Failed':
                metrics['failedCount'] += 1

            # Update average duration (incremental)
            metrics['totalDurationMs'] += doc.get('durationMs', 0)
            metrics['avgDurationMs'] = metrics['totalDurationMs'] // metrics['totalExecutions']

            await cosmos_client.upsert_item(metrics)
```

#### Option B: Hourly Rollup (Batch)
```python
@app.timer_trigger(schedule="0 0 * * * *")  # Every hour
async def rollup_metrics(timer):
    """Roll up last hour's executions into daily metrics"""
    cutoff = datetime.utcnow() - timedelta(hours=1)

    # Query last hour's completed executions
    executions = await query_completed_executions(since=cutoff)

    # Group by (scope, date) and aggregate
    aggregated = aggregate_by_scope_and_date(executions)

    # Update daily metrics
    for (scope, date), stats in aggregated.items():
        await update_daily_metrics(scope, date, stats)
```

#### Fast Dashboard Query
```sql
-- Get last 30 days of metrics (30 documents, ~50 RU total!)
SELECT *
FROM c
WHERE c.scope = 'org-123'
  AND c.type = 'metrics'
  AND c.date >= '2024-12-27'
ORDER BY c.date DESC
```

**Cost savings:**
- Before: 250,000 RU per dashboard load
- After: 50 RU per dashboard load
- **5,000x reduction!**

---

## Migration Phases

### Phase 1: MVP Migration (Week 1 - 7 days)

**Goal**: Replace Table Storage with CosmosDB, keep core functionality identical.

**Day 1: Infrastructure**
- Create CosmosDB account (serverless)
- Create `entities` and `executions` containers
- Configure connection strings

**Days 2-3: Repository Layer**
- Create `shared/cosmos_storage.py` (CosmosDB wrapper)
- Create `shared/repositories/cosmos_*.py` repositories
- Port all entity repositories to CosmosDB

**Days 4-5: Handler Updates**
- Update imports to use Cosmos repositories
- Convert Table Storage queries to SQL
- Remove execution index management code

**Day 6: Local Development**
- Add CosmosDB emulator to docker-compose.yml
- Update ./test.sh to start emulator
- Create initialization script

**Day 7: Testing & Validation**
- Run full test suite
- Performance benchmarks
- Deploy to dev environment

**Deliverables:**
✅ All entities in CosmosDB
✅ All executions in CosmosDB (metadata only)
✅ Zero manual index management
✅ All endpoints return identical data
✅ Tests passing 100%

**Out of Scope (Phase 1):**
- ❌ Real-time log streaming (still use blob storage)
- ❌ SignalR integration
- ❌ Dashboard optimization (use live queries)

---

### Phase 2: Real-Time Logs (Week 2 - 5 days)

**Goal**: Stream logs to CosmosDB for real-time UI updates.

**Day 1: Container Setup**
- Create `execution_data` container (partition by executionId)
- Update indexing policies

**Day 2: Workflow Engine Integration**
- Update execution logger to write logs to CosmosDB
- Stream variables and state snapshots
- Store results in CosmosDB (if <2MB)

**Day 3: Change Feed Setup**
- Create Change Feed Azure Function
- Integrate SignalR bindings
- Test log streaming

**Day 4: UI Integration**
- Update React components for SignalR
- Real-time log viewer
- Real-time variable inspector

**Day 5: Testing**
- Integration tests for Change Feed
- UI testing for real-time updates
- Performance validation

**Deliverables:**
✅ Logs stream to CosmosDB
✅ Change Feed → SignalR working
✅ UI shows real-time logs during execution
✅ Variables update in real-time
✅ Blob storage only used for >2MB results

**Out of Scope (Phase 2):**
- ❌ Dashboard optimization (still uses live queries)

---

### Phase 3: Dashboard Optimization (Week 3 - 3 days)

**Goal**: Pre-aggregate metrics for fast dashboard queries.

**Day 1: Metrics Schema**
- Design daily metrics document schema
- Create aggregation logic
- Test incremental updates

**Day 2: Change Feed Aggregation**
- Implement metrics Change Feed processor
- Test real-time metric updates
- Validate accuracy

**Day 3: Dashboard Updates**
- Update dashboard to use pre-aggregated metrics
- Add historical trend charts
- Performance testing

**Deliverables:**
✅ Daily metrics pre-aggregated
✅ Dashboard loads in <100ms
✅ Historical trend analysis
✅ 5,000x query cost reduction

---

## Cost Analysis

### Phase 1: MVP Migration

**Assumptions:**
- 50,000 executions/month (~1,600/day)
- 100,000 execution queries/month
- 50,000 entity queries/month
- 6GB total storage

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
TOTAL Phase 1: ~$10.59/month
```

### Phase 2: Real-Time Logs

**Additional RU consumption:**
```
Log writes:      50K execs × 10 logs × 5 RU = 2.5M RUs
Variable writes: 50K execs × 5 updates × 5 RU = 1.25M RUs
Result writes:   50K × 50 RU = 2.5M RUs
Log reads:       100K × 10 RU = 1M RUs
────────────────────────────────────────────────────
Additional: ~7M RUs = $1.75/month
```

**Cost:**
```
Phase 1 RUs:    36M × $0.25/million     = $9.00/month
Phase 2 RUs:    7M × $0.25/million      = $1.75/month
Storage:        8GB × $0.25/GB          = $2.00/month
Blob (minimal): 1GB × $0.018/GB         = $0.02/month
────────────────────────────────────────────────────
TOTAL Phase 2: ~$12.77/month
```

### Phase 3: Dashboard Optimization

**Metrics aggregation:**
```
Metrics writes:  30 orgs × 1/day × 30 days × 10 RU = 9K RUs
Metrics reads:   1K dashboard loads × 50 RU = 50K RUs
Dashboard saved: -250K RU per load saved!
────────────────────────────────────────────────────
Net savings: ~250M RUs/month if dashboard loaded 1K times
```

**Cost (same as Phase 2):**
```
TOTAL Phase 3: ~$12.77/month (dashboard queries are now cheaper!)
```

### ROI Calculation

**Monthly cost increase:** $12.77/month (from $0.37/month)

**Value gained:**
- Developer time saved: ~5 hours/month (no index management)
- Better debugging: Real-time logs (priceless for complex workflows)
- Faster queries: Multi-field filtering without custom indexes
- At $100/hr: **$500/month savings**
- **ROI: 39x return on infrastructure cost**

---

## Success Criteria

### Phase 1 (MVP)
✅ All endpoints return identical data to Table Storage version
✅ Execution creation completes in <500ms
✅ Execution queries return in <100ms
✅ TTL cleanup removes 14-day-old executions automatically
✅ All tests pass (100% success rate)
✅ Zero TODO comments about rollback/atomicity
✅ No manual index management code remaining

### Phase 2 (Real-Time)
✅ Logs appear in UI within 100ms of being written
✅ Variables update in real-time during execution
✅ SignalR connection stable (no disconnects)
✅ Change Feed processing latency <1s
✅ UI responsive during heavy logging

### Phase 3 (Optimization)
✅ Dashboard loads in <100ms (vs 2-5s before)
✅ Historical metrics accurate (matches live queries)
✅ Metrics update within 1 hour of execution completion
✅ Query cost reduced by >90%

---

## Risk Assessment

### Low Risk
✅ **Blob storage preserved** - Zero risk to existing data
✅ **API endpoints unchanged** - No client-side changes needed
✅ **Gradual rollout** - Three phases, can pause at any point
✅ **Proven technology** - CosmosDB + SignalR are mature

### Medium Risk
⚠️ **Real-time log volume** (Phase 2) - Could spike RU consumption
⚠️ **Change Feed latency** (Phase 2) - Possible delays under load
⚠️ **Metrics accuracy** (Phase 3) - Aggregation logic must be correct

**Mitigation:**
- Phase 1: Validate core migration before proceeding
- Phase 2: Start with small executions, monitor RU consumption
- Phase 3: Dual-run metrics (live + aggregated) to validate accuracy
- Set cost alerts at $25/month threshold

---

## Rollback Plan

**Each phase has independent rollback:**

**Phase 1:** Keep Table Storage code for 30 days, feature flag to switch back
**Phase 2:** Disable Change Feed, fall back to blob-only logs
**Phase 3:** Disable metrics aggregation, use live queries

**Data safety:**
- No data deletion during migration
- Table Storage preserved for 90 days post-migration
- Blob storage unchanged (shared between old/new)

---

## Open Questions & Decisions

### Resolved
✅ **CRON schedules**: Just workflow metadata (no container needed)
✅ **Relationships table**: Keep for user-role, form-role mappings
✅ **Config storage**: Migrate to CosmosDB, keep Key Vault for secrets
✅ **Local emulator**: CosmosDB Linux emulator works on Docker
✅ **Real-time updates**: Phase 2 feature, optional
✅ **Dashboard optimization**: Phase 3 feature, optional
✅ **Logs in CosmosDB**: Yes! Partitioned by executionId for real-time streaming
✅ **Results in CosmosDB**: Yes! Up to 2MB, overflow to blob only if needed

---

## Next Steps

1. **Approve this plan** - Stakeholder review
2. **Prototype Phase 1** - Build one repository (executions) end-to-end
3. **Performance benchmark** - Validate query performance vs Table Storage
4. **Kickoff Phase 1** - 7-day sprint
5. **Evaluate** - Decide whether to proceed with Phase 2 & 3

---

**Prepared by**: Claude Code
**Date**: 2025-01-26
**Version**: 2.0 (Updated with Phase 2 & 3)
**Status**: Ready for Implementation
