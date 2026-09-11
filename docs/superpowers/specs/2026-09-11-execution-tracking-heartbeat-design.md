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

## Design

### Refresh active execution state

The process-pool parent already owns the authoritative in-memory set of active
children and emits a heartbeat every ten seconds. During that heartbeat it will
refresh the TTL of each active execution's existing Redis keys:

- pending execution metadata;
- retained execution context; and
- buffered SDK changes, when that key exists.

Refreshing uses `EXPIRE`, not recreation. A missing key remains missing so the
heartbeat cannot fabricate incomplete context. Once a child completes,
crashes, times out, or is cancelled, its handle leaves the active set and the
parent stops refreshing its keys. Normal terminal cleanup remains responsible
for deleting the keys promptly.

### Recover completion from PostgreSQL

Success and failure processing will treat Redis metadata as a fast-path, not an
authority. When the pending record is missing or cannot be read, the consumer
will load the durable execution row and reconstruct the metadata needed for the
terminal commit and notifications: workflow identity, organization, initiating
user, and display name. The initiating user's email will be loaded for failure
event emission.

The callback will always persist the terminal status and result when the
durable execution row exists. Event-delivery reconciliation can use
`execution_id` directly; on the fallback path it will run without relying on
the original Redis event payload and remain a no-op for non-event executions.

If neither Redis metadata nor a PostgreSQL row exists, the consumer will emit a
high-signal error because it has no durable execution to update. It will not
invent a replacement row from a partial result.

### Preserve synchronous completion semantics

Whether a caller is waiting synchronously is transport state and is not stored
on the execution row. The process pool will retain that boolean with the active
child and attach it to real and synthetic results before invoking the result
callback. Consequently, Redis metadata loss cannot prevent a synchronous
caller from receiving its terminal result.

## Error Handling

Redis read or heartbeat failures are logged with the execution identifier. A
heartbeat failure does not affect the child process, and completion falls back
to PostgreSQL. PostgreSQL failure remains an authoritative completion failure
and continues through the existing result-callback error path.

The heartbeat refresh does not extend queued work indefinitely. It begins only
after the parent admits a child, so existing queue expiry and cleanup behavior
is unchanged.

## Testing

Tests use explicit key loss rather than wall-clock waits:

1. Construct active and inactive process handles, execute one heartbeat refresh,
   and assert that only active execution keys receive renewed TTLs.
2. Return no pending Redis record to success processing, provide a durable
   execution row, and assert that the terminal result is committed and
   published.
3. Repeat the missing-record test for failure processing.
4. Verify that real and synthetic process-pool results retain the synchronous
   transport bit.
5. Run the focused consumer and process-pool unit tests, the affected execution
   tests, and API quality checks. Before a PR is opened, commit the exact
   candidate on current `origin/main` and run `./test.sh pre-pr`.

No test sleeps for the production TTL. Expiry is modeled by making the Redis
lookup return no record, which is the exact boundary the production callback
observes after one hour.
