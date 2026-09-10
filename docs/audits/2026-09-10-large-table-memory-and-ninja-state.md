# Large table response memory and Ninja state audit

Issue: [#721](https://github.com/gobifrost/bifrost/issues/721)

## Scope and production safety

The production instance was inspected read-only. No workflow, table, deployment,
Kubernetes object, or production row was mutated. The Ninja proposal is based on
the guarded source version
`sha256:1191c1e9a2cb7efa798fa949c5d56c470f29484895aa47ded93dc39dd3e444a0`.

## Platform finding

`AllocationTrimMiddleware` synchronously ran `gc.collect()` and `malloc_trim()`
after every table-document request or response of at least 64 KiB. The benchmark
below shows stable settled memory under all three strategies. The middleware was
therefore paying stop-the-world latency on every qualifying response without
preventing demonstrated monotonic growth.

The committed change removes the middleware. It does not change:

- `MALLOC_ARENA_MAX=2` in `k8s/configmap.yaml`;
- bounded, one-file-at-a-time AST parsing in maintenance preflight;
- targeted `trim_malloc()` after application bundle builds.

### Production-shaped benchmark

The workload creates 1,500 deterministic Ninja-state-shaped rows and repeatedly
queries three 500-row pages (1,228,960 response bytes per round) while probing
`/health`. The host-side sampler reads the API process RSS plus cgroup
`memory.current`, anonymous-memory counters, active file cache, and the
`anon + active_file` working-set proxy every 100 ms. Settled measurements exclude
the first two warmup rounds.

| Strategy | Page latency, median / max | `/health` max | Peak RSS | Settled RSS growth | Peak working set | Settled working-set growth | Materially monotonic |
|---|---:|---:|---:|---:|---:|---:|---|
| Synchronous `gc.collect()` + `malloc_trim()` | 740 / 1,306 ms | 1,162 ms | 346.5 MiB | +0.27 MiB | 318.6 MiB | +0.27 MiB | No |
| Coalesced `malloc_trim()` in a thread, no explicit GC | 58.6 / 645 ms | 623 ms | 346.3 MiB | +3.14 MiB | 318.9 MiB | +3.14 MiB | No |
| Normal request teardown, no request-triggered maintenance | 90.3 / 764 ms | 759 ms | 348.3 MiB | +2.03 MiB | 317.1 MiB | +2.02 MiB | No |

The no-maintenance run passed the regression's 2-second page bound and 500 ms
health p99 bound. Its 764 ms page / 759 ms health observation was one isolated
outlier; the percentile contract detects the repeated stalls caused by the
forced-GC baseline without treating a single host-scheduling outlier as a
regression. The forced-GC baseline stalled repeatedly, with a 740 ms median page.
The production `py-spy` evidence is stronger still: 16.4 of 20 sampled seconds
were in the explicit `gc.collect()` call. The trim-only experiment removed that
collection but still produced a 623 ms process-wide health stall while
`malloc_trim()` ran outside the event-loop thread. With normal request teardown,
request-triggered collector and allocator-maintenance time is exactly zero.

### Memory classification

- **Live Python references:** the stable API footprint is represented by the
  approximately 315-317 MiB cgroup working set after warmup. It does not rise
  round over round.
- **Collectible cycles:** forcing a full collection on every response did not
  produce meaningfully lower settled memory. There is no evidence of a growing
  cycle backlog in this workload.
- **Allocator-retained, reusable pages:** normal teardown settled only about
  2-3 MiB above its first measured round. The trim-only strategy reached a
  similar plateau but still caused a process-wide request/health stall. That is
  reusable allocator capacity, not a leak worth reclaiming per request.
- **Monotonic cgroup growth:** neither RSS, `memory.current`, nor the working-set
  proxy grew materially or monotonically after warmup.

The benchmark therefore does not justify request-triggered `malloc_trim()`, even
off the event loop. If future production evidence demonstrates pressure-driven
trimming is required, it should be a rate-limited process-level mechanism with
duration/call metrics, not a table-response callback.

## Ninja state inventory

The live table has 1,418 rows. Compact JSON measurement produced:

- document JSON including Bifrost metadata: 1,135,688 bytes;
- document `data` JSON: 751,947 bytes;
- proposed durable `data` JSON after one full-replacement scan: approximately
  508,507 bytes;
- proposed full document JSON: approximately 892,248 bytes.

The proposal removes about 32% of state-data bytes and 21% of the complete table
response. Bifrost document metadata alone remains large enough that 500-row pages
must still be treated as large responses; field pruning is not the platform fix.

Approximate field bytes include each JSON key and value across all rows.

| Field | Approx. bytes | Consumer / reason | Derivable during scan? | Persist across quiet hours? | Recommendation |
|---|---:|---|---|---|---|
| `current_ip_since` | 75,154 | IP dwell and stationary timing | No | Yes | Keep |
| `off_all_sites_since` | 71,128 | Long-absence timing | No | Yes | Keep |
| `updated_at` | 66,646 | Duplicate scan timestamp | Yes; document metadata also has `updated_at` | No | Remove |
| `last_seen` | 65,228 | Last successful observation; future offline continuity | No if a device disappears from the feed | Yes | Keep |
| `last_classification` | 52,292 | Future transition dedupe / quiet-hours continuity | Yes for current scan, not prior notification state | Yes if notifications are added | Keep until notification ownership is resolved |
| `node_class` | 47,694 | Expected-always-on classification and display | Yes while device is returned | Yes for missing/offline devices | Keep |
| `system_name` | 40,697 | Device identity and delayed card copy | Yes while device is returned | Yes for delayed notification | Keep |
| `current_ip` | 39,575 | Change detection and site inference | Current value yes; prior value no | Yes | Keep |
| `ip_changed_this_run` | 38,286 | Builds the current execution's notable list | Yes | No | Remove; all 1,418 live values were false |
| `home_location_id` | 30,340 | Organization/site grouping and home-site key | Yes while device is returned | Yes | Keep |
| `home_matched` | 28,086 | Current classification detail | Yes from registry + current IP | No | Remove |
| `matched_site` | 27,851 | Current classification/card detail | Yes from registry + current IP | Only as part of an explicit pending notification | Remove from core state |
| `baseline_ip` | 25,524 | Dwell-learned site fingerprints | No | Yes | Keep |
| `stationary` | 25,524 | Gates dwell learning and absence classification | Yes from baseline/current timing | No | Remove; use `baseline_ip` as persisted dwell qualification |
| `matched_org` | 24,970 | Current classification detail | Yes from registry | No | Remove |
| `ninja_org_id` | 24,007 | Organization grouping and site key | Yes while device is returned | Yes | Keep |
| `device_id` | 22,151 | Ninja identity/dashboard link | The table document ID is identical on all 1,418 rows | Yes via document ID | Remove duplicate data field |
| `prev_ip` | 19,852 | Transition context in delayed notifications | Can be computed before overwrite, not after | Yes | Keep |

`updated_at == last_seen` and `str(device_id) == document.id` for every live row.
`baseline_ip` and `prev_ip` were null on every row because the table had only one
observed scan generation; this does not make them unnecessary for later temporal
behavior.

### Missing state ownership

The inspected workflow computes and persists only; it explicitly does not send
Teams messages and has no quiet-hours implementation. The table currently has no
online/offline timestamp from Ninja, expected-always-on decision, pending
transition, last-notified transition, Teams message ID, or Teams card state.
Those fields should not be invented in this change. If a delivery workflow is
added, it should persist only a compact pending-notification snapshot and stable
message identifier needed to survive quiet hours.

## Ninja execution results

The scan workflow already returns a summary plus notable devices, not the full
device collection or persisted state. The observed successful result was 812
bytes, of which the two notable devices used 540 bytes. The fingerprint results
ranged from 1,548 to 2,740 bytes; their inspectable registry contained 17-22 IP
entries and used 1,292-1,677 bytes. These PostgreSQL results are not material
response amplification.

The guarded proposal removes per-page payload re-serialization and verbose page
attempt structures from returned timings. It retains the small fingerprint
registry because inspecting that registry is the workflow's stated purpose.

## Guarded, undeployed Ninja proposal

Proposed source:
[`721-ninja-site-tracker.proposed.py`](fixtures/721-ninja-site-tracker.proposed.py)

Changes in the proposal:

- persist only the eleven fields marked Keep above;
- derive dwell qualification from `baseline_ip` rather than persisted
  `stationary`;
- replace 200-row `tables.upsert_batch()` calls with at most 1,000-row
  `tables.bulk_upsert()` calls;
- use full-replacement semantics so removed keys actually leave existing rows;
- use the set-based, count-only API path, avoiding per-row writes, realtime
  publication, and echoed document collections;
- return compact state row/query counts instead of per-page payload diagnostics.

The observed execution actors (`jack@gocovi.com` and `michael@gocovi.com`) are
active superusers, satisfying the current `tables.bulk_upsert()` privilege
boundary. Before any approved deployment, verify that this remains true, then
re-read the source version and deploy only with the current opaque version:

```bash
BIFROST_API_URL=https://bifrost.gocovi.com \
  bifrost files stat workflows/ninja_site_tracker.py --json

BIFROST_API_URL=https://bifrost.gocovi.com \
  bifrost files write workflows/ninja_site_tracker.py \
  --from-file docs/audits/fixtures/721-ninja-site-tracker.proposed.py \
  --expected-version sha256:1191c1e9a2cb7efa798fa949c5d56c470f29484895aa47ded93dc39dd3e444a0
```

The second command is documented for a future explicitly approved deployment;
it was not run during this audit.

## Sales Hunter: separate contributing load

`sh_process_ticket_findings` is not needed to reproduce the Ninja table stall.
A single large Ninja page deterministically exercised the synchronous middleware.
Sales Hunter does, however, materially amplify general API allocation and write
load:

1. each ticket writes legacy and signal findings one row at a time;
2. each ticket then rebuilds the entire client aggregate;
3. the rebuild reads up to 1,000 legacy findings, 1,000 signal findings, and
   1,000 opportunities into Python collections;
4. it rewrites every current opportunity and every inventory document through
   `upsert_batch`, whose API implementation performs per-row work and echoes the
   written documents;
5. concurrent events for one client duplicate the whole rebuild.

This explains the observed burst of more than 1,000 `client-app-inventory`
upserts in ten minutes. It increases object churn and can magnify any global GC
pause, but it is not the root cause fixed by removing request-path collection.

Recommended follow-up, kept out of #721's implementation scope:

- immediately move aggregate writes to bounded `tables.bulk_upsert()` calls;
- coalesce concurrent rebuilds by client so only one authoritative rebuild runs
  for a client generation;
- then replace full aggregate reconstruction with an incremental rebuild of the
  normalized keys touched by the ticket, preserving protected opportunity state;
- add request/write-count and retained-memory measurements for a concurrent
  ticket-event fixture.
