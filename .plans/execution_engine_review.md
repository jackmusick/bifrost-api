# Execution Engine Review: `api/shared/engine.py`

**Date:** 2025-12-05  
**Reviewer:** opencode (AI assistant)  
**Context:** Trusted user code, scaling across containers, strict real‑time log ordering, desire for cancellable timeouts.

---

## 1. Context & Goals

- **Trust model:** Fully trusted tenant code (no sandbox).
- **Scaling:** Should scale with system resources; multiple containers possible.
- **Log ordering:** Must be strict, real‑time, UI sorts by `sequence`.
- **Timeouts & cancellation:** Should be enforced; ideal is ability to kill stuck/hung executions.
- **Current architecture:**
  - Threads via `asyncio.to_thread` with per‑thread `asyncio.run`.
  - In‑process in‑memory cache for data providers.
  - Root logger set to DEBUG to capture user logs; filtering by basename/workspace.
  - Variable capture via `sys.settrace`.
  - Log streaming via background threads and WebPubSub broadcaster.

---

## 2. Issues & Risks

### 2.1. Per‑process in‑memory cache
- **Not shared** across workers/containers → inconsistent cache hits under horizontal scaling.
- **Not durable** across restarts (deploy, crash, autoscale).
- **No size bounds, eviction, or stampede protection**; races possible.

### 2.2. Timeouts & cancellation
- **No enforced timeout** – `to_thread` future is not wrapped in `asyncio.wait_for`.
- **Cannot kill stuck threads** – Python threads cannot be safely terminated; only cooperative cancellation is possible.
- **No cancellation flag** – no mechanism for a user to request stop or for the engine to signal “time’s up.”

### 2.3. Log ordering & streaming
- **Per‑log‑line thread** can interleave delivery order; UI must sort by `sequence`.
- **Failures are silent** – broadcaster/DB append errors are swallowed, logs can be lost.
- **Root logger set to DEBUG** persists after execution, causing cross‑talk and noise.

### 2.4. Log scope & filtering
- **Basename/pathname filtering** is brittle – multi‑file workflows can be missed or over‑captured.
- **Attaching handler to root logger** risks capturing unrelated logs (aiohttp, third‑party SDKs).

### 2.5. Process‑wide logging monkey‑patch
- `sys.modules['logging']` is temporarily replaced **process‑wide**; concurrent script executions can see the swapped module, leading to misrouted logs.

### 2.6. Globals injection for extra parameters
- Extra parameters are injected into `func.__globals__`; concurrent executions of the same function can read transient globals (data race).
- Clean‑up occurs, but a race window exists.

### 2.7. Variable capture via `sys.settrace`
- **Per‑thread, expensive** – can limit throughput.
- **Limited scope** – only traces the decorated function or script’s `main()`; spawned async tasks are not traced.
- **No opt‑out** – tracing is always on.

### 2.8. No hard resource controls
- No CPU/memory guardrails; threads can block indefinitely; hung C extensions cannot be preempted.

### 2.9. Script return value
- `_script_to_callable` returns a fixed dict `{"status": "completed", "message": ...}` instead of the script’s `main()` return value (workflows can return arbitrary values; scripts cannot).

### 2.10. Statuses & retries
- All non‑`UserError` exceptions → `FAILED`; no explicit `TIMED_OUT` or `CANCELLED` statuses.
- Retries are left to workflow authors (no engine‑level retry/backoff).

---

## 3. Recommendations (Prioritized)

### 3.1. Redis‑backed cache for data providers
- **Key:** `org_id:name:param_hash` (SHA‑256 of sorted JSON params).
- **TTL:** Use Redis `SETEX` with configurable TTL.
- **Stampede protection:** Optional `SETNX` lock with short TTL to deduplicate concurrent calculations.
- **Benefits:** Multi‑worker consistency, durability, eviction, observability, future‑proof for horizontal scaling.

### 3.2. Timeouts and cancellation
#### **Option A – Threads (cooperative cancellation)**
- Wrap `asyncio.to_thread` future in `asyncio.wait_for`; on timeout raise `asyncio.TimeoutError` and mark execution `TIMED_OUT`.
- Introduce a per‑execution cancellation flag (Redis/DB); add `context.check_cancelled()` helper that raises `CancellationError`.
- **Limitation:** Blocked threads (e.g., `time.sleep`, CPU‑bound loops) cannot be killed; they will run to completion.

#### **Option B – Processes (hard‑stop)**
- Run each execution in a worker **process** (pool or per‑execution).
- Parent enforces timeout with `wait_for` and can `terminate()`/`kill()` the child process on expiry.
- **Cost:** Per‑process DB connections, IPC overhead, serialization of inputs/outputs.
- **Benefit:** True hard‑stop for stuck/hung work.

**Suggested path:** Start with **Option A** (threads + cooperative cancellation) and add **Option B** as an opt‑in execution mode for workflows that need guaranteed stoppability.

### 3.3. Log ordering & delivery
- Keep per‑execution monotonic `sequence` (already good).
- **Avoid thread‑per‑log** – use a per‑execution queue or single sender to preserve emission order.
- **Surface broadcast/persist failures** – log errors, optionally buffer and flush at end.
- **Ensure UI sorts by `sequence`** (already does).

### 3.4. Log scope without root DEBUG
- **Do not change root logger level.** Attach a handler with DEBUG level to a **per‑execution logger** (e.g., `workflow.{execution_id}`) or the workflow module’s logger.
- **Filter by logger name or module path prefix** (workspace directory) rather than basename.

### 3.5. Remove process‑wide logging monkey‑patch
- **Do not replace `sys.modules['logging']`.** Use a script‑specific logger (`script.{name}`) with an attached handler.
- If intercepting `import logging` is required, use a per‑thread import hook, not a global swap.

### 3.6. Avoid globals injection for extra parameters
- If the function accepts `**kwargs`, pass extras there.
- Otherwise, store extras in `context.parameters` and include them in captured variables for transparency.
- **Stop mutating `func.__globals__`** to eliminate race risk.

### 3.7. Tracing controls
- Keep `sys.settrace` but **make it configurable/optional** (e.g., `enable_tracing=True/False`).
- **Document limitation:** spawned async tasks are not traced unless wrapped.
- Consider lighter‑weight capture for common cases (return value + selected locals) to reduce overhead.

### 3.8. Statuses & UX
- Add explicit statuses: `SUCCESS`, `COMPLETED_WITH_ERRORS`, `FAILED`, `TIMED_OUT`, `CANCELLED`.
- On timeout/cancel, include a clear error message and partial logs/variables.

### 3.9. Script return values
- In `_script_to_callable`, return `await main()` (or capture its return) instead of a fixed dict, providing parity with workflows.

### 3.10. Backpressure & concurrency
- **Bound concurrency** (thread pool size or process pool size) to prevent unbounded resource consumption.
- **Add metrics** for queue length, active executions, timeouts.
- If using processes, cap pool size to CPU cores.

---

## 4. FAQ

### Why does the per‑process cache matter even for single‑container users?
- **Future‑proofing:** Moving to Redis now avoids inconsistency when you later add workers/containers.
- **Durability:** Survives restarts, preventing cache‑warming spikes.
- **Observability & control:** Redis provides TTL eviction, size limits, and stampede protection.

### Threads vs. Processes – what can we actually kill?
- **Threads:** Cannot be safely killed; only cooperative cancellation via periodic checks.
- **Processes:** Can be terminated (`SIGTERM`/`SIGKILL`), giving true hard‑stop capability at the cost of per‑process DB connections and IPC.

### Is the current log filtering enough?
- **Basename filtering** may miss logs from imported modules in the same workspace; better to filter by **module path prefix** (e.g., `/workspace/`).
- **Root logger attachment** risks capturing unrelated logs; scoped per‑execution logger is safer.

### Will removing `sys.modules['logging']` monkey‑patch break script logging?
- No – scripts can still use `logging.info()` because the default root logger will propagate to our attached handler. The script logger (`script.{name}`) ensures logs are tagged and captured.

---

## 5. Concrete Next Steps (Thread‑Model, Low/Medium Effort)

1. **Replace in‑memory cache with Redis:**
   - Implement `redis_cache.get(key)`, `redis_cache.setex(key, ttl, value)`.
   - Optional stampede lock using `SETNX` with short TTL.

2. **Add timeouts & cooperative cancellation:**
   - Wrap `asyncio.to_thread` in `asyncio.wait_for`.
   - Add `TIMED_OUT` status.
   - Store cancellation flag in Redis (`exec:{id}:cancel`); expose `context.check_cancelled()`.

3. **Rework logging capture:**
   - Stop setting root logger to DEBUG.
   - Attach handler to per‑execution or module logger.
   - Replace thread‑per‑log with a per‑execution queue/single sender.
   - Surface broadcast/DB append errors.

4. **Remove `sys.modules['logging']` monkey‑patch:**
   - Use script‑specific logger + handler.

5. **Stop globals injection:**
   - Pass extras via kwargs or `context.parameters`.

6. **Make tracing optional:**
   - Add `enable_tracing` flag to `ExecutionRequest`.

7. **Script return values:**
   - Return `await main()` in `_script_to_callable`.

8. **Add concurrency limits:**
   - Bound thread pool size (e.g., `max_workers` config).

---

## 6. If Hard Cancellation Is Required (Process‑Model)

- **Move to process‑pool execution:** Use `concurrent.futures.ProcessPoolExecutor` or spawn a child process per execution.
- **Re‑establish DB connections** in each worker process (cannot share connections across processes).
- **Pass inputs/outputs** via pickling, IPC queue, or Redis/DB.
- **Parent monitors timeout** and `terminate()`s child on expiry.
- **Logs & status** must be communicated back via IPC/Redis/DB.

This is a larger architectural change but provides the “magical world” ability to kill stuck executions.

---

## 7. Files to Review Adjacent to `engine.py`

- `shared/context.py` – ExecutionContext, cancellation flag storage.
- `shared/errors.py` – WorkflowExecutionException, UserError, WorkflowError.
- `src/repositories/execution_logs.py` – Log persistence.
- `bifrost/_context.py` – SDK context management.
- `shared/async_storage.py` – Possibly Redis client.
- `shared/rabbitmq.py` – For future queue‑based scaling.

---

## 8. Summary

The engine is well‑structured for trusted, scalable execution but has several areas where reliability, observability, and resource control can be improved. The highest‑impact changes are:

1. **Redis cache** for data‑provider consistency.
2. **Timeout enforcement** + cooperative cancellation.
3. **Log‑capture refinements** (no root DEBUG, no global monkey‑patch).
4. **Optional tracing** + safer extra‑parameter handling.

These changes will make the engine more robust for multi‑container scaling and provide a better UX for timeout/cancellation, while preserving the current “code‑first Power Automate” experience.