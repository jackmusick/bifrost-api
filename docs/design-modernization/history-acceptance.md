# History UI acceptance

This review covers `/history`: workflow records, agent history, logs, filters,
pagination, cancellation, and cleanup. Execution details have a separate verified
route record. The core editor is a global shell, not another History route.

## Layout and interaction evidence

- Workflow records use full-width mobile cards with labelled metadata and native
  detail links; desktop keeps the table. Earlier `history-records-check.cjs` and
  `history-mobile-filters-check.cjs` passes are recorded in PROGRESS.md. Current
  density matrix48235 passes six light/dark/custom-purple320/1440 cases. Parent
  reviewed the complete mobile record and desktop error layout.
- Initial loading, HTTP failure, retry, true empty, populated recovery and long
  content pass61971/48235. Search and Filters share a mobile row; status and log
  severity use mobile selectors. Natural page height prevents nested table-body
  collapse on600px screens (95553). Desktop log width refinement37635 reviewed.
- Workflow cancellation shares ExecutionCancelAction across desktop/mobile.
  Four custom-purple320/1440x600 light/dark cases84819 prove scheduled/running
  failure, retained confirmation, pending protection, retry, focused error bounds,
  successful status update. Existing409 refresh and optimistic cancellation tests
  remain. Parent inspected dark320 running and light1440 scheduled errors.
- Cleanup is a page-local responsive dialog with fixed controls and scrollable
  records.41000 proves read/save failure and retry in four variants;38971 proves
  final mobile name/status stacking. Parent inspected the dark mobile dialog.
  The trigger now follows the API's admin-only boundary; its24-hour explanation
  matches the current endpoint. Backend cleanup behavior was not changed.
- Agent history preserves cached rows, offers focused rerun retry and retains the
  history return destination.46591 proves four custom-purple theme/width recovery
  cases with desktop table/action bounds;33479 additionally proves next-page
  failure/retry/previous-page recovery. Native desktop name links and44px rerun
  controls match mobile navigation. Parent inspected the final desktop table and
  mobile error. Existing agent-history/detail composition evidence is recorded
  in the agent-history records/navigation checkpoints in PROGRESS.md.
- Log history10788/95553 proves loading/error/empty, refresh of the selected log
  query, retained cached logs, next-page failure/back navigation, critical/custom
  severity and readable long messages in four variants. Mobile messages use14px;
  desktop gives messages a three-line preview with full text/detail access.
  Earlier log-record keyboard/drawer and pagination tests remain applicable.

## Filter contract

The workflow selector previously did not affect log requests. The optional
`workflow_id` parameter now flows from the URL/selector through LogsView/useLogs
and the API router to an exact execution workflow-ID predicate. Workflow changes
reset pagination. Optional `global_only` distinguishes Global from All; that scope
also participates in the pagination reset key. Existing partial-name filtering,
organization UUID filtering and admin permissions remain unchanged.

Workflow browser84683 passes all four bookmarked selection/change/clear cases.
Global/All browser87942 passes all four scope/filter cases; parent inspected dark320. Backend7518
passes11 repository tests including exact-ID and global-only predicates; API
quality54137 passes. Types were regenerated from the current API. Frontend73224
passes24 History/log tests and60489 passes7 log tests after the scope addition.
Full client TypeScript84253 and scoped lint pass.

## Verification limits

The browser fixtures use intercepted reads and mutations, not real cancellation,
cleanup or rerun jobs. They verify UI requests, response handling and navigation;
existing backend execution protocols are preserved. Route UI acceptance is
separate from the pending whole-application production build, full suite,
exact-HEAD review, commit/push and delivery gates. Temporary browser artifacts
live under `/tmp/bifrost-design-review`; named passes are recorded in PROGRESS.md.
