# Table Batch Invalidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Replace per-row realtime publication for table batch writes and deletes with one table invalidation event per successful mutating request, while preserving granular events for single-row operations.

**Architecture:** Batch routes commit their database changes, then publish `{type: "table_invalidated", table_id}` once when at least one row changed. The websocket layer forwards that event only to active subscribers without loading row policies because the payload contains no row data. Web SDK hooks recognize the invalidation and coalesce authoritative snapshot refreshes; older SDKs ignore the unknown event and retain their existing snapshot until another refresh.

**Tech Stack:** FastAPI, Python async pubsub/Redis, React hooks, TypeScript, Vitest, pytest.

---

### Task 1: Define and publish one batch invalidation

**Files:**
- Modify: `api/tests/unit/policies/test_pubsub.py`
- Modify: `api/tests/unit/test_table_bulk_upsert_route.py`
- Modify: `api/src/core/pubsub.py`
- Modify: `api/src/routers/tables.py`

**Step 1: Write failing tests**

- Add a pubsub unit test asserting `publish_table_invalidated("table-id")` publishes once to `table:table-id` with exactly `{"type": "table_invalidated", "table_id": "table-id"}`.
- Replace the batch-write route expectation of one `publish_document_change` call per row with one `publish_table_invalidated` call after commit.
- Cover a no-op conflict-only insert request and assert it emits no invalidation.
- Add batch-delete coverage asserting multiple successful deletions emit one invalidation after commit and a no-op delete emits none.

**Step 2: Run tests to verify they fail**

Run: `./test.sh tests/unit/policies/test_pubsub.py tests/unit/test_table_bulk_upsert_route.py -v`

Expected: failure because `publish_table_invalidated` does not exist and batch routes still publish per-row changes.

**Step 3: Implement the minimal server change**

- Add `publish_table_invalidated(table_id: str)` beside the existing pubsub helpers.
- Import it in `tables.py`.
- Remove event-body construction and per-row publishing from `batch_documents`; after a successful commit publish once only when `ordered_documents` is non-empty.
- Move batch-delete notification after the commit, remove retained `old_row` data used only for publication, and publish once only when `deleted > 0`.
- Leave all single-document route calls to `publish_document_change` unchanged.

**Step 4: Run tests to verify they pass**

Run: `./test.sh tests/unit/policies/test_pubsub.py tests/unit/test_table_bulk_upsert_route.py -v`

Expected: all selected tests pass.

**Step 5: Commit**

```bash
git add api/src/core/pubsub.py api/src/routers/tables.py api/tests/unit/policies/test_pubsub.py api/tests/unit/test_table_bulk_upsert_route.py
git commit -m "perf: invalidate tables once per batch mutation"
```

### Task 2: Forward invalidations through subscribed websockets

**Files:**
- Modify: `api/tests/unit/routers/test_websocket.py` (or the existing websocket-table unit test file found by `rg`)
- Modify: `api/src/routers/websocket.py`

**Step 1: Write failing websocket tests**

- For an active table subscription, assert `_handle_table_message` forwards `{"type": "table_invalidated", "table_id": table_id}` exactly once.
- Assert it does not call `_load_policies_for_table`; invalidation carries no row data and therefore needs no row visibility calculation.
- For a websocket without an active subscription, assert nothing is sent.

**Step 2: Run the focused test and verify failure**

Run the exact discovered test file with `./test.sh <test-file> -v`.

Expected: active subscribers receive nothing because the current handler ignores unknown event types.

**Step 3: Implement forwarding**

- In `_handle_table_message`, after confirming the subscription exists and before the `document_change` branch, forward the canonical two-field invalidation payload and return.
- Do not load policies, include row data, or change policy-change and document-change behavior.

**Step 4: Run the focused test and verify success**

Run the same exact test command.

Expected: all selected tests pass.

**Step 5: Commit**

```bash
git add api/src/routers/websocket.py <test-file>
git commit -m "feat: forward table invalidation events"
```

### Task 3: Refresh Web SDK table hooks on invalidation

**Files:**
- Modify: `client/src/lib/app-sdk/tables.ts`
- Modify: `client/src/lib/app-sdk/ws-client.ts`
- Modify: `client/src/lib/app-sdk/use-table.ts`
- Modify: `client/src/lib/app-sdk/use-table.test.tsx`
- Modify: `client/src/lib/app-sdk/use-infinite-table.ts`
- Modify: `client/src/lib/app-sdk/use-infinite-table.test.tsx`
- Modify: `client/src/lib/app-sdk/ws-client.test.ts`

**Step 1: Write failing SDK tests**

- Assert the websocket client accepts and dispatches `table_invalidated` messages.
- Assert `useTable` refetches its current page when invalidated and replaces rows/total from the authoritative result.
- Assert `useInfiniteTable` refetches the currently loaded window when invalidated.
- In both hooks, deliver multiple invalidations while the first refresh is pending and assert refresh calls are coalesced: one in flight and at most one trailing refresh, so the final state includes changes that arrived during the first refresh.

**Step 2: Run the focused tests and verify failure**

Run: `./test.sh client unit src/lib/app-sdk/use-table.test.tsx src/lib/app-sdk/use-infinite-table.test.tsx src/lib/app-sdk/ws-client.test.ts`

Expected: invalidation frames are unsupported and do not trigger refreshes.

**Step 3: Implement SDK handling**

- Add `{type: "table_invalidated"; table_id: string}` to `TableChangeEvent` and `TableChangeMessage`.
- In each hook's subscription callback, route invalidations to its existing authoritative snapshot loader rather than `applyPagedEvent`/`applyEvent`.
- Add a small per-hook in-flight/dirty coalescer scoped to the subscription effect. If an invalidation arrives during a refresh, mark it dirty and perform one more refresh after the current one settles. Surface refresh errors through existing hook error state.
- Preserve reconnect refresh behavior and granular document-change handling.

**Step 4: Run the focused tests and verify success**

Run the same exact client unit command.

Expected: all selected tests pass.

**Step 5: Commit**

```bash
git add client/src/lib/app-sdk/tables.ts client/src/lib/app-sdk/ws-client.ts client/src/lib/app-sdk/use-table.ts client/src/lib/app-sdk/use-table.test.tsx client/src/lib/app-sdk/use-infinite-table.ts client/src/lib/app-sdk/use-infinite-table.test.tsx client/src/lib/app-sdk/ws-client.test.ts
git commit -m "feat: refresh table hooks after batch invalidation"
```

### Task 4: Version the changed SDK realtime contract

**Files:**
- Modify: `client/src/lib/app-sdk/wire-surface.ts`
- Modify: `client/src/lib/app-sdk/sdk-contract.json`
- Modify: `client/src/lib/app-sdk/sdk-contract.test.ts`

**Step 1: Update the declared wire surface and run the tripwire**

- Add the invalidation frame to the table-change wire surface.
- Run: `./test.sh client unit src/lib/app-sdk/sdk-contract.test.ts`
- Expected: snapshot hash failure, proving the contract tripwire detects the change.

**Step 2: Record the contract decision**

- Bump `sdk-contract.json` from version 1 to version 2.
- Add a dated history entry explaining that batch mutations now send table invalidation frames and compatible hooks must refetch.
- Refresh the expected wire-surface snapshot hash.
- The API image copies `client/src/lib/app-sdk` into its packaged SDK source during its Docker build; do not create or hand-maintain a second checked-in copy.

**Step 3: Verify client and packaged contracts**

Run:

```bash
./test.sh client unit src/lib/app-sdk/sdk-contract.test.ts
./test.sh tests/unit/test_sdk_package.py tests/unit/test_sdk_package_fingerprint.py -v
```

Expected: all selected tests pass and the API package reports contract version 2.

**Step 4: Commit**

```bash
git add client/src/lib/app-sdk
git commit -m "feat: version table invalidation SDK contract"
```

### Task 5: Verify the complete notification slice

**Files:**
- Modify tests only if an uncovered live-boundary defect is exposed.

**Step 1: Run backend boundary coverage**

Run:

```bash
./test.sh tests/e2e/api/test_tables_batch.py tests/e2e/platform/test_subscriptions.py -v
./test.sh quality api
```

Expected: batch API behavior, websocket subscriptions, Python lint, and Python types pass.

**Step 2: Run client boundary coverage**

Run:

```bash
(cd client && npm run tsc && npm run lint)
./test.sh client unit src/lib/app-sdk/use-table.test.tsx src/lib/app-sdk/use-infinite-table.test.tsx src/lib/app-sdk/ws-client.test.ts src/lib/app-sdk/sdk-contract.test.ts
```

Expected: TypeScript types, lint, and all changed SDK behavior pass.

**Step 3: Review the diff for scope**

Run: `git diff origin/main...HEAD --stat && git status --short`

Confirm no single-row event behavior changed and no row payload appears in invalidation events.

**Step 4: Commit any test-only corrections**

If verification required corrections, commit only those corrections with a focused message. Otherwise leave the verified commits unchanged.
