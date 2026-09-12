# Table Invalidation and V2 SDK Update Design

Date: 2026-09-12

## Purpose

Fix the realtime regression introduced when canonical table batch writes began
publishing one Redis and WebSocket notification per successful row, and add the
minimum operational controls needed to identify and update standalone V2 apps
whose bundled Bifrost web SDK is stale.

This work has two connected outcomes:

1. Batch table mutations publish one lightweight invalidation per committed
   request instead of one row payload per mutation.
2. Bifrost records which SDK built each V2 app, retains independent-app source,
   surfaces update availability, and can rebuild an app in place through the
   existing platform-job scheduler.

It does not introduce a dynamically loaded SDK, automatically upgrade deployed
apps, mutate Git-authored source, or add a second background-job system.

## Existing Behavior and Root Cause

`POST /api/tables/{table}/documents/batch` performs a set-based PostgreSQL
write, commits, then loops over every successful row and calls
`publish_document_change`. Each call enters `ConnectionManager.broadcast`,
opens a new `get_redis()` context, pings Redis, publishes one payload, and
closes the client. Measurements from the affected workload found approximately
35 ms per fresh-connection publish versus approximately 1 ms with a reused
connection. The per-row wire contract also causes every subscribed API process
and browser to evaluate and process every row.

Standalone V2 apps import `bifrost` as a real package. The server-side build
injects a generated SDK tarball into a temporary Vite workspace, so the SDK is
compiled into the app's `dist`. The tarball contains three identifiers:

- a package version derived from the running Bifrost version;
- a SHA-256 content fingerprint of the compiled SDK bundle;
- a manually maintained SDK/server wire-contract version.

Those identifiers are not currently recorded on `Application`. Independent
App deploy source is staged for `application.deploy` and deleted after the job.
Solution deploy source is retained as an immutable Solution source artifact.

## Table Batch Invalidation

### Wire contract

Successful batch insert, merge-upsert, replace-upsert, and batch-delete
requests publish exactly one message after their database transaction commits:

```json
{
  "type": "table_invalidated",
  "table_id": "<uuid>"
}
```

The event intentionally carries no document IDs, row bodies, counts, or policy
pre-images. It reveals only that a table to which the connection is already
authorized has changed. The next read remains subject to normal table scope,
row policies, and subscription filters.

Single-document insert, update, upsert, and delete endpoints retain granular
`document_change` events. Batch endpoints do not also publish granular events.

### Server fanout

The table WebSocket dispatcher recognizes `table_invalidated` after confirming
that the connection still has an active subscription for the table. It forwards
one invalidation frame without loading policies or evaluating individual rows.
Policy-change events retain their existing authorization re-evaluation.

### Web SDK behavior

`tables.subscribe` exposes `table_invalidated` in its event union. `useTable`
re-queries its current page and total when it receives an invalidation.
`useInfiniteTable` re-queries the currently loaded window. Each hook coalesces
an invalidation received while a refresh is in flight into at most one
subsequent refresh, preventing overlapping query storms while guaranteeing
that a change arriving during a refresh is not lost.

An older SDK ignores the unknown event and may remain stale until reload or
WebSocket reconnection. Its HTTP mutation still succeeds. This compatibility
outcome is accepted; the server does not preserve per-row fanout for legacy
clients.

Because an older SDK no longer maintains its documented live state after a
batch mutation, this change increments the web SDK contract version and records
the decision in `sdk-contract.json`. It does not affect the separate CLI/API
contract version.

## SDK Build Identity and Update Status

### Persisted provenance

Add nullable, server-owned build metadata to `Application` for
`standalone_v2` apps:

- `sdk_package_version`;
- `sdk_fingerprint`;
- `sdk_contract_version`;
- `sdk_built_at`.

Inline V1 apps leave the fields null because their platform surface is
injected at runtime. Existing V2 rows also begin null because their compiled
SDK cannot be identified reliably after the fact.

Every source-backed V2 build path stamps provenance from the exact tarball used
for compilation: independent App deploy, Solution deploy, Solution install,
and git-connected Solution sync. A prebuilt-only bundle without trustworthy
SDK metadata remains unknown rather than being guessed.

SDK identity is build metadata and must not be serialized into portable app or
Solution manifests. App source must not pin an instance-specific `bifrost`
package dependency.

### Derived status

The API derives status by comparing the app's recorded values with the current
instance SDK, whose fingerprint is already exposed by `/api/version`:

- `not_applicable`: inline V1;
- `unknown`: V2 with null or incomplete provenance;
- `current`: fingerprint matches;
- `update_available`: fingerprint differs;
- `update_required`: reserved for a future explicit minimum supported SDK
  contract; this spike does not invent that minimum.

The UI may render `unknown` and `update_available` with the same actionable
badge while retaining the distinction in the API. A Solution derives its badge
from its contained apps: any actionable V2 app makes an SDK update available.
A stored `sdk_update_available` boolean is rejected because it would become
stale whenever the platform SDK changes and would lose provenance.

## Retained Independent-App Source

Independent V2 deploys already upload a validated source zip and build into a
versioned deployment artifact. Before activating a successful build, copy the
immutable sanitized source alongside the deployment instead of deleting the
only durable copy. Source persistence is part of deployment success: if it
fails, the new artifact is not activated.

```text
_application_artifacts/<app-id>/deployments/<deployment-id>/source.zip
```

The source archive excludes `.env` files, `node_modules`, generated build
directories, and editor/OS debris using the same canonical packaging rules as
deploy. It is private build input, never a publicly served asset or an editable
platform source tree. Local Git remains canonical.

Source reads and exports require the same administrative authorization as App
deploy. Deleting an App removes its retained source. Superseded deployment
source follows the same retention decision as its versioned compiled artifact.
Existing independent apps report source unavailable until their next
source-backed deploy.

Solution-owned apps continue to use the existing immutable Solution source
artifact. Git-connected installs rebuild the last successfully applied stored
artifact; an SDK rebuild never fetches a newer Git commit and never changes
source ownership.

All standalone V2 apps, including Solution-owned apps, converge on versioned
dist paths selected by `Application.active_deployment_id`. Existing
Solution-owned apps may continue serving their legacy unversioned dist until
their first successful deploy or SDK rebuild creates and atomically selects a
versioned artifact. Subsequent deploys and rebuilds upload a complete new
artifact before changing the pointer and clean incomplete artifacts on failure.

## In-Place SDK Rebuild

### Operation

An SDK update is an app-only rebuild, not a source edit and not a full Solution
reconciliation. It:

1. authorizes the caller and resolves retained source;
2. enqueues a durable platform job with an application resource lock and
   active-operation deduplication;
3. materializes the exact retained source in a temporary directory;
4. injects the current instance SDK tarball using the existing
   `SolutionAppBuilder` mechanism;
5. compiles and uploads a new versioned dist artifact;
6. atomically activates it and stamps SDK provenance;
7. cleans incomplete artifacts on failure.

For a Solution-owned app, the operation changes only that app's compiled
artifact and Application build metadata. It does not reconcile or mutate any
other Solution entity. Solution deploy and SDK rebuild must share a locking
boundary that prevents them from activating competing builds.

If retained source is unavailable, the endpoint returns an actionable conflict
requiring a normal source-backed deploy. Prebuilt-only Solution apps have the
same restriction.

### Platform jobs and resource policy

Register a distinct `application.sdk_update` platform-job definition so job
history and operator intent remain clear. Extract and reuse the focused source
resolution, compilation, upload, activation, provenance, and cleanup
primitives from `application.deploy`; do not duplicate a second build
implementation. Status, progress, notification projection, cancellation,
deduplication, and observation use the shared `PlatformJob` system.

Scheduler replicas already run App deploys in isolated child processes. The
current `application.deploy` policy requires 512 MiB of memory headroom. Before
changing that floor, benchmark representative small and large apps and record
wall time plus the scheduler's start/peak cgroup working-set samples. A
historical estimate of roughly 200 MiB is not treated as sufficient evidence.

Batch SDK updates enqueue bounded per-app durable jobs; they do not compile
inside an HTTP request or add a new worker container. Scheduler admission and
available replicas control concurrency.

## User and CLI Experience

App list/detail responses include SDK provenance, derived status, source
availability, and any active update job. App list/detail UI surfaces an
`SDK update available` badge and an `Update SDK` action when retained source
exists. Solutions surface aggregate status and allow updating one contained app
or all actionable contained apps.

The CLI provides status and enqueue commands over the same REST endpoints:

```text
bifrost apps sdk status
bifrost apps sdk update <app>
bifrost apps sdk update --all
bifrost solutions sdk status
bifrost solutions sdk update <solution>
```

The CLI polls the shared platform-job endpoint with an overall wait deadline,
matching existing deploy behavior. `--all` first reports the selected instance,
scope, actionable app count, unavailable-source count, and estimated queue
work; it then enqueues jobs and reports their IDs. It never downloads and
re-uploads source when the platform already retains it.

`bifrost solution export` remains the complete manual source recovery path.
`bifrost solution pull` remains manifest-only. A normal `solution deploy`
continues to perform full Solution reconciliation and is not silently used for
an SDK-only update.

## Repository Guidance

Add an identical section to `AGENTS.md` and `CLAUDE.md` documenting:

- `client/src/lib/app-sdk/` is the web SDK source of truth;
- app source never pins the instance SDK or commits `node_modules`;
- the platform injects the SDK at build time and every V2 build path must stamp
  provenance;
- wire-surface changes update `wire-surface.ts` and its snapshot;
- breaking wire changes increment `sdk-contract.json` with history;
- SDK-only rebuilds use retained immutable source and never modify Git source,
  manifests, or other Solution entities;
- App and Solution SDK update work must use shared platform jobs.

## Validation

The spike must include focused tests for:

- one invalidation publish for large insert/upsert and delete batches;
- no granular batch notifications;
- post-commit publication and no event on rollback/failure;
- WebSocket forwarding without row-policy fanout;
- `useTable` and `useInfiniteTable` refresh/coalescing behavior;
- old-event granular behavior remaining intact;
- web SDK wire-surface and contract-version tripwires;
- nullable migration and V1 not-applicable status;
- current, unknown, and update-available derivation;
- provenance stamping on every server-built V2 path;
- independent source retention, authorization, integrity, and deletion;
- retained-source and Solution-source rebuilds;
- git-connected source ownership and deploy/update locking;
- missing-source actionable failure;
- enqueue deduplication, job visibility, progress, cancellation, and cleanup;
- CLI status, single update, batch update, and wait-timeout behavior;
- API DTO parity, CLI contract fingerprint decision, generated web types, and
  generated skill appendices affected by the new surfaces.

Benchmark App builds through the real scheduler host with representative source
sizes. Record peak cgroup delta and wall time before changing memory policy.

During implementation, run targeted tests and quality checks. Before opening or
queueing a PR, commit the exact candidate on current `origin/main` and run
`./test.sh pre-pr`.

## Rollout

The migration is additive and nullable. Existing V2 apps become visible as
unknown but are not rebuilt automatically. New deployments retain source and
stamp provenance. Operators may update apps individually or in bounded batches.

Deploy the invalidation-aware web SDK and server together. Older compiled apps
may show stale table data after batch mutations until reload or rebuild; this is
an accepted, documented compatibility consequence. No fleet SDK update runs as
part of the platform rollout.

Implementation is split into two independently verifiable phases on the same
spike branch: table invalidation first, then SDK provenance/source/update. The
second phase consumes the contract version produced by the first but does not
block verifying or reviewing the database-performance fix independently.
