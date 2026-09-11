# Durable Workflow Completion and Execution Lease Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure every admitted workflow reaches a durable terminal PostgreSQL state even if its transient Redis records expire, while cheaply recreating a compact Redis lease for every execution that is still running.

**Architecture:** The process-pool parent receives a compact `ActiveExecution` snapshot when it dispatches a child, stores that snapshot on `ExecutionInfo`, and recreates a one-hour Redis lease immediately and every ten minutes through a single pipeline. Completion reads the lease as a fast path and falls back to the existing PostgreSQL execution row; PostgreSQL receives only the existing start and terminal writes, never heartbeat writes.

**Tech Stack:** Python 3.14, FastAPI worker services, Redis asyncio pipelines, SQLAlchemy async sessions, pytest, Dockerized Bifrost test stack.

---

## File Map

- Modify `api/src/core/cache/keys.py`: define the active-execution key and TTL.
- Modify `api/src/core/redis_client.py`: define the compact lease schema and provide read access for completion processing.
- Modify `api/src/services/execution/process_pool.py`: retain completion metadata, create and sparsely refresh active leases, and preserve sync state on every result path.
- Modify `api/src/jobs/consumers/workflow_execution.py`: pass compact metadata at dispatch and recover completion from PostgreSQL when Redis is absent.
- Modify `api/src/core/cache/invalidation.py`: delete the active lease during terminal cleanup.
- Modify `api/tests/unit/core/test_redis_client.py`: cover lease reads and missing leases.
- Modify `api/tests/unit/execution/test_process_pool.py`: cover lease recreation, batching, refresh cadence, and real/synthetic result metadata.
- Modify `api/tests/unit/jobs/consumers/test_workflow_execution_session.py`: cover success and failure after Redis metadata loss.
- Modify `api/tests/e2e/api/test_executions.py`: prove a live delayed workflow completes after both tracking keys are deleted.

### Task 1: Define the compact active-execution lease

**Files:**
- Modify: `api/src/core/cache/keys.py`
- Modify: `api/src/core/redis_client.py`
- Modify: `api/tests/unit/core/test_redis_client.py`

- [ ] **Step 1: Write failing Redis lease read tests**

Add tests that exercise the wished-for public API without waiting for TTL expiry:

```python
@pytest.mark.asyncio
async def test_get_active_execution_returns_compact_lease():
    client = RedisClient()
    redis = AsyncMock()
    redis.get.return_value = json.dumps({
        "execution_id": "exec-1",
        "workflow_id": "workflow-1",
        "workflow_name": "scan",
        "org_id": "org-1",
        "user_id": "user-1",
        "user_name": "Operator",
        "user_email": "operator@example.com",
        "sync": False,
        "event": None,
    })
    client._redis = redis

    lease = await client.get_active_execution("exec-1")

    assert lease is not None
    assert lease["workflow_name"] == "scan"
    redis.get.assert_awaited_once_with(active_execution_key("exec-1"))


@pytest.mark.asyncio
async def test_get_active_execution_returns_none_when_lease_is_missing():
    client = RedisClient()
    redis = AsyncMock()
    redis.get.return_value = None
    client._redis = redis

    assert await client.get_active_execution("exec-1") is None
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
./test.sh tests/unit/core/test_redis_client.py -q
```

Expected: collection or assertion failure because `active_execution_key` and `RedisClient.get_active_execution()` do not exist.

- [ ] **Step 3: Add the key, schema, and read method**

Add a key helper and constants:

```python
def active_execution_key(execution_id: str) -> str:
    """Compact parent-owned lease for an actively running execution."""
    return f"bifrost:exec:{execution_id}:active"


TTL_ACTIVE_EXECUTION = 3600
```

Define the compact Redis payload in `redis_client.py`:

```python
class ActiveExecution(TypedDict):
    execution_id: str
    workflow_id: str | None
    workflow_name: str
    org_id: str | None
    user_id: str | None
    user_name: str
    user_email: str | None
    sync: bool
    event: dict[str, Any] | None
```

Implement `get_active_execution()` by reading `active_execution_key(execution_id)`, returning `None` for a missing key, and JSON-decoding a present value. Do not make it fall back to the legacy pending key.

- [ ] **Step 4: Run the focused Redis tests and verify GREEN**

Run:

```bash
./test.sh tests/unit/core/test_redis_client.py -q
```

Expected: all tests in the file pass.

- [ ] **Step 5: Commit the lease contract**

```bash
git add api/src/core/cache/keys.py api/src/core/redis_client.py api/tests/unit/core/test_redis_client.py
git commit -m "feat(execution): define active execution lease"
```

### Task 2: Make the process-pool parent create and recreate leases

**Files:**
- Modify: `api/src/services/execution/process_pool.py`
- Modify: `api/tests/unit/execution/test_process_pool.py`

- [ ] **Step 1: Add failing tests for compact storage and batched recreation**

Create a `_active_execution()` test helper containing only the nine compact fields. Add tests with two BUSY handles and one KILLED handle that assert:

```python
await pool._refresh_active_execution_leases()

redis.pipeline.assert_called_once_with(transaction=False)
assert pipeline.setex.call_count == 2
pipeline.setex.assert_any_call(
    active_execution_key("exec-1"),
    TTL_ACTIVE_EXECUTION,
    json.dumps(_active_execution("exec-1")),
)
pipeline.execute.assert_awaited_once()
```

Also assert the serialized value has no `parameters`, `startup`, `form_inputs`, or `embed` keys. Because `SETEX` is unconditional, this test proves an absent key is recreated rather than merely touched.

Add a cadence test that calls one heartbeat iteration with monotonic time below and above the ten-minute boundary and asserts lease refresh runs only at or after the boundary.

- [ ] **Step 2: Run the process-pool tests and verify RED**

Run:

```bash
./test.sh tests/unit/execution/test_process_pool.py -q
```

Expected: failures because `ExecutionInfo` has no active metadata and `_refresh_active_execution_leases()` does not exist.

- [ ] **Step 3: Retain compact metadata on each active handle**

Change `ExecutionInfo` and the required production dispatch boundary:

```python
@dataclass
class ExecutionInfo:
    execution_id: str
    started_at: datetime
    timeout_seconds: int
    active_execution: ActiveExecution
```

Add `active_execution: ActiveExecution` as a required argument immediately
after `context` in `route_execution()` and `_dispatch_to_child()`. Update every
unit-test construction and route call with explicit compact metadata. Do not
add a default or synthesize identity data.

- [ ] **Step 4: Implement immediate creation and sparse batched refresh**

Add:

```python
ACTIVE_EXECUTION_REFRESH_SECONDS = 10 * 60

async def _refresh_active_execution_leases(self) -> None:
    active = [
        handle.current_execution
        for handle in self.processes.values()
        if handle.state is ProcessState.BUSY and handle.current_execution is not None
    ]
    if not active:
        return
    redis_client = await self._get_redis()
    pipeline = redis_client.pipeline(transaction=False)
    for execution in active:
        pipeline.setex(
            active_execution_key(execution.execution_id),
            TTL_ACTIVE_EXECUTION,
            json.dumps(execution.active_execution),
        )
    await pipeline.execute()
```

Create the lease immediately after assigning `handle.current_execution`, before sending work to the child. A lease-write failure must be logged and must not prevent the already-admitted child from running. Track a monotonic last-refresh timestamp and invoke the batch refresh from the existing heartbeat loop only every ten minutes; continue publishing the worker-health heartbeat every ten seconds.

- [ ] **Step 5: Add failing tests for sync state on every result path**

For a real result, timeout, cancellation, crash, and orphan callback, construct
`ExecutionInfo(active_execution=_active_execution("exec-1") | {"sync": True})`,
invoke the relevant method, and assert the callback payload contains
`"sync": True`.

- [ ] **Step 6: Run the new result tests and verify RED**

Run:

```bash
./test.sh tests/unit/execution/test_process_pool.py -q
```

Expected: callback assertions fail because result payloads do not yet carry `sync`.

- [ ] **Step 7: Attach sync transport state before every callback**

Use one helper so real and synthetic paths cannot drift:

```python
def _attach_transport_metadata(
    result: dict[str, Any], execution: ExecutionInfo
) -> dict[str, Any]:
    return {**result, "sync": execution.active_execution["sync"]}
```

Call it from `_handle_result`, `_report_timeout`, `_report_cancellation`, `_report_crash`, and `_report_orphan` before invoking `on_result`.

- [ ] **Step 8: Run the process-pool tests and verify GREEN**

Run:

```bash
./test.sh tests/unit/execution/test_process_pool.py -q
```

Expected: all process-pool tests pass.

- [ ] **Step 9: Commit parent-owned lease management**

```bash
git add api/src/services/execution/process_pool.py api/tests/unit/execution/test_process_pool.py
git commit -m "feat(execution): recreate leases for active workers"
```

### Task 3: Make terminal persistence independent of Redis

**Files:**
- Modify: `api/src/jobs/consumers/workflow_execution.py`
- Modify: `api/tests/unit/jobs/consumers/test_workflow_execution_session.py`
- Modify: `api/tests/e2e/api/test_executions.py`

- [ ] **Step 1: Add failing success and failure recovery tests**

For each terminal path, configure `get_active_execution()` to return `None`, configure the durable session query to return an `Execution` row plus user email, and assert `update_execution()` is awaited with the incoming terminal status and the same session. The success test must retain result, variables, execution context, metrics, ROI, and duration. The failure test must retain error type, error message, and duration.

The durable fixture should resemble:

```python
execution = MagicMock(
    workflow_id=UUID("00000000-0000-0000-0000-000000000001"),
    workflow_name="long_scan",
    organization_id=UUID("00000000-0000-0000-0000-000000000002"),
    executed_by=UUID("00000000-0000-0000-0000-000000000003"),
    executed_by_name="Test User",
)
row_result = MagicMock()
row_result.one_or_none.return_value = (execution, "test@example.com")
durable_session.execute.return_value = row_result
consumer._redis_client.get_active_execution.return_value = None
```

Assert the fallback path reconciles event delivery by `execution_id`, while the lease-backed non-event path avoids that extra query.

Add the live regression at the same failure-first stage. Use the existing
delayed async workflow fixture, start a five-second execution, poll until the
API reports `Running` and `active_execution_key(execution_id)` exists, then
delete both the active lease and legacy pending key through the real test Redis
service. Poll the execution endpoint and assert:

```python
assert execution["status"] == "Success"
assert execution["result"] == {"status": "completed", "delayed": 5}
```

- [ ] **Step 2: Run consumer tests and verify RED**

Run:

```bash
./test.sh tests/unit/jobs/consumers/test_workflow_execution_session.py -q
./test.sh tests/e2e/api/test_executions.py::TestAsyncExecution::test_running_execution_completes_after_redis_tracking_loss -q
```

Expected: the unit test shows the early return prevents `update_execution()`;
the live execution remains `Running` rather than reaching `Success`.

- [ ] **Step 3: Add compact metadata at dispatch**

Immediately before `route_execution`, build:

```python
active_execution: ActiveExecution = {
    "execution_id": execution_id,
    "workflow_id": workflow_id,
    "workflow_name": workflow_name,
    "org_id": org_id,
    "user_id": user_id,
    "user_name": user_name,
    "user_email": user_email,
    "sync": is_sync,
    "event": (
        {"id": event_data.get("id"), "type": event_data.get("type")}
        if event_data is not None
        else None
    ),
}
await self._pool.route_execution(
    execution_id=execution_id,
    context=context_data,
    active_execution=active_execution,
)
```

Remove the pre-dispatch update that enriches the pending record solely for result handling; the pending record is no longer completion authority.

- [ ] **Step 4: Implement lease-first, PostgreSQL-authoritative metadata loading**

Add a private loader that catches Redis read errors, then queries `Execution` with an outer join to `User` only when the lease is absent. Return both the metadata and a boolean indicating that event delivery must be reconciled defensively:

```python
async def _load_completion_metadata(
    self,
    execution_id: str,
    session: AsyncSession,
) -> tuple[ActiveExecution | None, bool]:
    try:
        lease = await self._redis_client.get_active_execution(execution_id)
    except Exception:
        logger.warning("Could not read active execution lease for %s", execution_id, exc_info=True)
        lease = None
    if lease is not None:
        return lease, lease["event"] is not None

    result = await session.execute(
        select(Execution, User.email)
        .outerjoin(User, Execution.executed_by == User.id)
        .where(Execution.id == UUID(execution_id))
    )
    row = result.one_or_none()
    if row is None:
        return None, False
    execution, user_email = row
    return {
        "execution_id": execution_id,
        "workflow_id": str(execution.workflow_id) if execution.workflow_id else None,
        "workflow_name": execution.workflow_name,
        "org_id": str(execution.organization_id) if execution.organization_id else None,
        "user_id": str(execution.executed_by) if execution.executed_by else None,
        "user_name": execution.executed_by_name,
        "user_email": user_email or "",
        "sync": False,
        "event": None,
    }, True
```

Use `result["sync"]` as the authoritative transport bit after loading metadata. If both the lease and database row are absent, log an error and return because there is no durable execution to update. Do not create a replacement row.

- [ ] **Step 5: Refactor success and failure through the loader**

Open the existing durable session before loading metadata. Remove both early returns based on `get_pending_execution()`. Preserve the current transaction order: terminal execution update and buffered writes commit first; sync result push happens second; aggregate metrics and pub/sub fan-out remain derived work afterward.

Call `update_delivery_from_execution()` when the compact lease marks an event execution or when the database fallback was required. The latter is intentionally defensive and is a no-op for ordinary executions.

- [ ] **Step 6: Run consumer tests and verify GREEN**

Run:

```bash
./test.sh tests/unit/jobs/consumers/test_workflow_execution_session.py -q
./test.sh tests/e2e/api/test_executions.py::TestAsyncExecution::test_running_execution_completes_after_redis_tracking_loss -q
```

Expected: all consumer tests pass and the live workflow reaches `Success`
after its Redis tracking records are explicitly deleted.

- [ ] **Step 7: Commit durable terminal recovery**

```bash
git add api/src/jobs/consumers/workflow_execution.py api/tests/unit/jobs/consumers/test_workflow_execution_session.py api/tests/e2e/api/test_executions.py
git commit -m "fix(execution): persist results after Redis state loss"
```

### Task 4: Clean up leases and verify the complete boundary

**Files:**
- Modify: `api/src/core/cache/invalidation.py`
- Modify: `api/tests/unit/cache/test_invalidation.py`

- [ ] **Step 1: Write a failing terminal-cleanup assertion**

Extend the existing cache invalidation test with an exact key assertion:

```python
redis.delete.assert_awaited_once_with(
    pending_changes_key(execution_id),
    execution_logs_stream_key(execution_id),
    active_execution_key(execution_id),
)
```

- [ ] **Step 2: Run the cleanup test and verify RED**

Run:

```bash
./test.sh tests/unit/cache/test_invalidation.py -q
```

Expected: the delete call is missing `active_execution_key(execution_id)`.

- [ ] **Step 3: Delete the compact lease during terminal cleanup**

Extend `cleanup_execution_cache()`:

```python
await r.delete(
    pending_changes_key(execution_id),
    execution_logs_stream_key(execution_id),
    active_execution_key(execution_id),
)
```

Keep legacy pending deletion in the consumer until its existing dispatch lifecycle is separately redesigned.

- [ ] **Step 4: Run focused unit and E2E verification**

Run:

```bash
./test.sh tests/unit/core/test_redis_client.py tests/unit/execution/test_process_pool.py tests/unit/jobs/consumers/test_workflow_execution_session.py -q
./test.sh tests/e2e/api/test_executions.py::TestAsyncExecution::test_running_execution_completes_after_redis_tracking_loss -q
./test.sh quality api
```

Expected: all selected tests pass and API lint/type checks exit zero.

- [ ] **Step 5: Commit cleanup coverage**

```bash
git add api/src/core/cache/invalidation.py api/tests/unit/cache/test_invalidation.py
git commit -m "fix(execution): clean up active leases"
```

### Task 5: Final candidate verification

**Files:**
- Verify all files listed above.

- [ ] **Step 1: Review the candidate diff and invariants**

Run:

```bash
git diff origin/main...HEAD --check
git diff --stat origin/main...HEAD
rg -n "get_pending_execution\(execution_id\)" api/src/jobs/consumers/workflow_execution.py
git status --short
```

Expected: no whitespace errors; result handlers no longer depend on the pending dispatch record; the worktree is clean.

- [ ] **Step 2: Rebase onto current upstream if needed**

Fetch and compare `HEAD` with `origin/main`. If upstream advanced, rebase the branch, rerun the targeted tests, and commit any conflict resolution before the broad gate.

- [ ] **Step 3: Run the required clean-commit PR gate**

Run:

```bash
./test.sh pre-pr
```

Expected: the complete locally reproducible PR suite passes for the exact clean `HEAD` SHA reported by the command.

- [ ] **Step 4: Report exact evidence**

Record the candidate SHA, targeted unit and E2E commands, API quality result, and `pre-pr` result. Report any unrun external-only checks as owned by GitHub rather than implying they ran locally.
