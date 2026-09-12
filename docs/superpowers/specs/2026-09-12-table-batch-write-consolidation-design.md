# Table Batch Write Consolidation Design

Issue: #734

## Purpose

Bifrost must have one canonical HTTP endpoint and one implementation for
inserting or upserting document batches. The unreleased `POST
/api/tables/{table}/documents/bulk-upsert` route was added as a narrow metadata
ingestion optimization after v1.3.0. No released client depends on it, so it
will be removed rather than retained as a compatibility alias.

The released Python SDK methods `tables.insert_batch()` and
`tables.upsert_batch()` will keep their signatures and documented behavior.
The unreleased `tables.bulk_upsert()` convenience method will remain available
but will call the canonical batch endpoint.

This change does not resume the SharePoint campaign, change a deployed
Solution, enable fleet refresh, or deploy Bifrost.

## Existing Contracts

The canonical route is currently:

```text
POST /api/tables/{table}/documents/batch
```

Its released request contains `documents` and `upsert`. Existing clients must
continue to work without sending any new fields.

Released behavior that remains stable:

- `upsert=false` inserts documents and permits omitted IDs;
- `upsert=true` merges submitted top-level JSON keys into an existing document
  when an ID is present and continues to generate an ID and insert when a raw
  REST request omits it; the released SDK already requires IDs for
  `upsert_batch()`;
- table auto-creation remains an SDK concern after a 404;
- policy denials reject the complete request and report every denied row;
- successful results are returned in submission order, including generated
  IDs;
- attribution overrides retain their existing authorization rules;
- successful writes continue to publish document-change notifications;
- the response retains `inserted`, `errors`, and `documents`.

The unreleased `tables.bulk_upsert()` contract is explicit-ID, full-document
replacement with bounded conflict retries and a count-only SDK result.

## Canonical Request

`DocumentBatchCreate` will retain `upsert` and add optional fields:

```python
write_mode: Literal["insert", "merge_upsert", "replace_upsert"] | None = None
return_documents: bool = True
```

The server normalizes the request as follows:

| Wire input | Effective mode |
| --- | --- |
| `write_mode` omitted, `upsert=false` | `insert` |
| `write_mode` omitted, `upsert=true` | `merge_upsert` |
| `write_mode="insert"` | `insert` |
| `write_mode="merge_upsert"` | `merge_upsert` |
| `write_mode="replace_upsert"` | `replace_upsert` |

Sending `upsert=true` with an explicit `write_mode` other than
`merge_upsert` is rejected as contradictory. The old field remains only as the
backward-compatible wire spelling; new SDK code sends `write_mode`.

Explicit `write_mode="merge_upsert"` and `write_mode="replace_upsert"` require
a non-empty explicit ID for every document. The backward-compatible
`upsert=true` spelling and `insert` continue to generate UUID IDs when omitted.

`return_documents=false` suppresses document bodies in the response but does
not suppress policy checks, validation, attribution, or notifications. The
response shape remains `DocumentBatchCreateResponse`; its `documents` list is
empty and `inserted` carries the successful count. `tables.bulk_upsert()` maps
that count to `BulkUpsertResult.count`.

## Request Bounds

The canonical endpoint accepts at most 1,000 documents per HTTP request. The
current SDK methods validate this before sending so new callers receive a
local, actionable error. The server enforces the same limit for every client.

This is the one intentional tightening of the old implicit contract. The old
route exposed no meaningful safe upper bound and performed work proportional
to an attacker-controlled list. Silently chunking in the SDK is not acceptable
because it would destroy request-wide policy-denial and transaction semantics.
Requests larger than 1,000 must be explicitly chunked by the caller, with each
chunk treated as its own transaction.

## Shared Set-Based Engine

Batch write business logic will move out of the HTTP handler into one focused
service module. Both released SDK modes and replacement mode call this engine.
The HTTP handler remains responsible for table resolution, Solution ownership,
request normalization, commit, response serialization, and post-commit event
publication.

The engine performs these phases:

1. Assign IDs for insert rows that omitted them and reject duplicate explicit
   IDs within the request.
2. Load all existing explicit IDs in one `(table_id, id IN (...)) FOR UPDATE`
   query ordered by ID.
3. Resolve policies once, evaluate each row against its pre-image or candidate,
   and reject the complete request if any row is denied.
4. Execute one PostgreSQL insert statement for the accepted rows:
   - `insert`: `ON CONFLICT DO NOTHING`, with conflicts returned as per-row
     errors rather than causing repeated statements;
   - `merge_upsert`: `data = documents.data || excluded.data`;
   - `replace_upsert`: `data = excluded.data`.
5. Use the preflight ID set to prevent a concurrent insert from unexpectedly
   entering an update branch. A detected race rolls back the request and
   returns 409, preserving the bounded retry behavior of `bulk_upsert()`.
6. Return successful rows in submission order when requested.

Updates preserve original `created_by` and `created_at`; inserts use submitted
attribution. Every successful update sets `updated_by` and `updated_at`.

No per-row `SELECT`, `flush`, or `refresh` loop remains.

## Transactions, Errors, and Notifications

Policy denials and infrastructure/database failures are request-atomic. Insert
conflicts retain the existing batch response concept: conflicting rows appear
in `errors`, while non-conflicting inserts succeed in the same transaction.
Duplicate IDs in the request are rejected before the write because their
submission-order result is ambiguous.

Document-change notifications are part of the canonical platform write
contract. Replacement mode will not inherit the specialized route's silent
event suppression. The handler constructs old/new row snapshots from the
preflight and returned rows and publishes one existing-format notification per
successful document using the route's existing transaction timing. This keeps
subscriptions coherent without creating another ingestion-specific behavior.

If notification throughput later proves insufficient, it should be solved as
a platform event-delivery batching or outbox concern, not by introducing a
second table-write endpoint.

## Removed Surface

The change removes:

- `POST /api/tables/{table}/documents/bulk-upsert`;
- `DocumentBulkUpsertRequest`, `DocumentBulkUpsertItem`, and
  `DocumentBulkUpsertResponse` from the server contract;
- the separate `DocumentRepository.bulk_upsert()` implementation;
- route-specific tests and generated OpenAPI entries.

`tables.bulk_upsert()` remains a Python convenience method because it describes
useful replacement/count-only semantics. It sends `write_mode="replace_upsert"`
and `return_documents=false` to `/documents/batch` and preserves its bounded
409 retries.

No compatibility route is retained. The route landed after v1.3.0 and no
release tag contains it.

`POST /documents/batch-delete` remains the canonical delete operation. It does
not overlap the insert/upsert endpoint and is outside this consolidation; its
unbounded per-row implementation is a separately identified audit finding.

## Authorization and Isolation

Every mode uses the same table resolution, organization scope, Solution
ownership, and row-policy pipeline. Replacement mode does not receive a
privileged bypass merely because its first caller was an ingestion workflow.
Ordinary callers may use it only when normal create/update policies grant the
corresponding operation. Attribution overrides remain restricted to the engine
and platform administrators.

All reads and writes include `table_id`; IDs remain unique only within a table.

## Validation

Tests will cover:

- unchanged SDK request/response behavior for released `insert_batch()` and
  `upsert_batch()` calls;
- SDK `bulk_upsert()` using `/documents/batch`, with no request to the removed
  URL;
- insert with generated and explicit IDs;
- merge-upsert versus replacement semantics;
- count-only versus document-return responses;
- duplicate IDs, existing-ID insert conflicts, and concurrent-insert 409;
- request size 1,000 accepted and 1,001 rejected in SDK and server;
- create/update policy combinations and all-or-nothing policy denial;
- attribution preservation and override authorization;
- notification publication for insert and update in every mode;
- organization/table and Solution isolation;
- one existing-row preflight query and one set-based write for a 1,000-row
  request, with no per-row database statement loop;
- OpenAPI, SDK signature, DTO parity, contract fingerprint, and generated skill
  appendix freshness.

Targeted tests and API quality checks run during implementation. Before a PR is
opened, the exact clean candidate must contain current `origin/main` and pass
`./test.sh pre-pr`.

## Deployment and Rollback

There is no database migration. Server and bundled SDK ship together in the
next release. Because the removed route has never shipped, deployment requires
no compatibility window.

Rollback restores the preceding server and SDK together. The SharePoint
campaign remains on hold throughout; no caller should rely on the new batch
mode until the release containing this consolidation is deployed.
