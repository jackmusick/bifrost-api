# Durable Workflow Completion and Execution Tracking Heartbeat

## Problem

Workflow dispatch stores completion metadata in
`bifrost:exec:{execution_id}:pending` with a fixed one-hour TTL. The TTL starts
when the API enqueues the workflow. Once the worker starts, Bifrost creates a
durable PostgreSQL execution row in `Running` state, but the success and failure
callbacks still require the Redis pending record before they will update that
row.

A workflow may run for up to 24 hours, or without a timeout. If its pending
record expires or Redis loses the key, the child continues running and reports
its result, but the callback discards that result. Execution history therefore
remains `Running` until a later cleanup may incorrectly classify it as timed
out.

## Invariant

After an execution has a PostgreSQL row, loss or expiry of transient Redis
state must never prevent Bifrost from recording its terminal result.

The process-pool parent owns the durable execution lifecycle. It records the
transition to `Running`, retains the minimum completion metadata needed while
the child is active, and records the terminal outcome returned by the child.
The child owns only execution of user code. Redis transports and caches state;
it is never the source of truth for whether admitted work is still running or
has finished.

## Design

### Recreate a compact active-execution lease

The process-pool parent already owns the authoritative in-memory set of active
children. Each active handle will retain a compact completion snapshot:
workflow identity, organization identity, initiating user identity and email,
display name, event-delivery presence, and the synchronous transport bit. It
will not retain parameters, startup data, form inputs, embed data, or other
potentially large workflow payloads.

On a sparse interval independent of the ten-second worker-health heartbeat,
the parent will batch `SET ... EX` commands for active executions into one
Redis pipeline per worker replica. `SET`, rather than `EXPIRE`, deliberately
recreates a missing lease after expiry, eviction, or Redis restart while the
child is still active. A ten-minute refresh interval leaves ample margin inside
the one-hour lease TTL without producing constant Redis traffic.

Once a child completes, crashes, times out, or is cancelled, its handle leaves
the active set and the parent stops recreating its lease. Normal terminal
cleanup deletes the lease promptly. PostgreSQL receives no heartbeat writes.

The existing pending-dispatch and retained-context keys keep their current
lifecycle. They may contain large inputs and are not duplicated into parent
memory merely to make them recreatable. The compact active lease is the
parent-owned record used for completion after dispatch.

### Recover completion from PostgreSQL

Success and failure processing will read the compact active lease first and
treat it as a fast-path, not an authority. The existing pending record returns
to its intended role as dispatch-only state. When the active lease is not
available or readable, the consumer will load the durable execution row and
reconstruct the metadata needed for the terminal commit and notifications:
workflow identity, organization, initiating user, and display name. The
initiating user's email will be loaded for failure event emission.

The callback will always persist the terminal status and result when the
durable execution row exists. Event-delivery reconciliation can use
`execution_id` directly; on the fallback path it will run without relying on
the original Redis event payload and remain a no-op for non-event executions.

If neither Redis metadata nor a PostgreSQL row exists, the consumer will emit a
high-signal error because it has no durable execution to update. It will not
invent a replacement row from a partial result.

### Preserve synchronous completion semantics

Whether a caller is waiting synchronously is transport state and is not stored
on the execution row. The process pool retains that boolean in the compact
active lease and with the active handle, then attaches it to real and synthetic
results before invoking the result callback. Consequently, Redis metadata loss
cannot prevent a synchronous caller from receiving its terminal result.

## Error Handling

Redis read or lease-refresh failures are logged with the execution identifier.
A refresh failure does not affect the child process, and completion falls back
to PostgreSQL. PostgreSQL failure remains an authoritative completion failure
and continues through the existing result-callback error path.

The heartbeat refresh does not extend queued work indefinitely. It begins only
after the parent admits a child, so existing queue expiry and cleanup behavior
is unchanged.

## Testing

Tests use explicit key loss rather than wall-clock waits:

1. Construct active and inactive process handles, execute one lease refresh,
   and assert that only active executions are written through one Redis
   pipeline with a fresh TTL.
2. Begin with no lease key, run a refresh for an active handle, and assert that
   the compact lease is recreated without large workflow inputs.
3. Return no Redis lease to success processing, provide a durable execution
   row, and assert that the terminal result is committed and published.
4. Repeat the missing-record test for failure processing.
5. Verify that real and synthetic process-pool results retain the synchronous
   transport bit.
6. Run the focused consumer and process-pool unit tests, the affected execution
   tests, and API quality checks. Before a PR is opened, commit the exact
   candidate on current `origin/main` and run `./test.sh pre-pr`.

No test sleeps for the production TTL. Expiry is modeled by making the Redis
lookup return no record, which is the exact boundary the production callback
observes after one hour.
