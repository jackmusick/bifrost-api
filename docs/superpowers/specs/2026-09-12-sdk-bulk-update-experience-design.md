# SDK Bulk Update Experience Design

Date: 2026-09-12

## Goal

Make the common administrative action—rebuilding every outdated App against
the current SDK—obvious on both Apps and Solutions, while retaining the recent
selection-mode standard for administrators who want a subset.

## Interaction

The Apps toolbar shows `Update all SDKs (N)` whenever its organization scope
contains actionable Apps. This action does not require selection and ignores
text search, so typing into search cannot silently change its scope. It respects
the organization filter. The server still revalidates every submitted App and
reports stale, current, unavailable, or conflicting entries as skipped.

`Select` enters the established card-selection mode. Actionable cards become
whole-card toggles with a visible check state; non-actionable cards remain
visible but unavailable for selection. `Select all` means all visible actionable
cards after organization and text filtering. The primary selection action is
`Update selected (N)` and `Done` exits selection mode. Table view uses a select-
all checkbox plus row checkboxes with the same eligibility and scope rules.

The Solutions toolbar follows the same model. `Update all SDKs (N)` targets all
actionable Solution-managed Apps in the selected organization scope while
ignoring text search. Selection mode selects actionable Solutions, not their
individual Apps; `Update selected (N)` updates all actionable Apps belonging to
those Solutions. Each actionable Solution card also exposes a direct update
action, and Solution detail retains its existing scoped update action.

## Execution and feedback

Bulk actions enqueue normal per-App `application.sdk_update` PlatformJobs.
They do not build in the HTTP request and do not create a batch worker. One
Solutions batch request resolves all selected Solutions and their Apps with
bounded queries, avoiding one HTTP request per Solution. Accepted App IDs are
passed to the existing WebSocket job-state tracker, so every card/row switches
to its animated `Updating SDK` badge. A toast reports queued and skipped counts;
durable phase progress and failures remain in Notifications.

Buttons are disabled while their enqueue request is pending. If nothing is
actionable, Update All is absent and selection controls cannot select an entry.
Submitting an empty selected set is impossible. Partial acceptance is success
with skipped-count disclosure; request failure leaves the selection intact for
retry.

## Validation

Backend tests cover one-request multi-Solution enqueue, scope/eligibility,
deduplication, and bounded App loading. Component tests cover Update All scope,
search-independent scope, selection mode, full-card and Select All behavior,
disabled entries, pending state, partial results, and accepted-job tracking.
Playwright captures Apps and Solutions Update All plus the animated per-App job
state using the real rendered pages and WebSocket transport.
