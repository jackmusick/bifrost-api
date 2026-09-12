# Parallel implementation and review

The migration remains open until every route, component, compatibility requirement and delivery gate has evidence. An implementation handoff is not acceptance.

## Current batch

| Owner | Exclusive implementation files | Stage |
| --- | --- | --- |
| Terra: captured_data_filter | Events.tsx and page-local list components/tests | Refine parent-reviewed mobile composition; read/delete recovery and rendered proof |
| Terra: run_review_sheet | Integrations.tsx, Integrations/IntegrationList.tsx and tests | Actual-route rendered selection/read/delete acceptance; full TypeScript check |
| Terra: agent_fleet_stats | Live editor FileTabs and shell files as needed; excludes AppCodeEditor | First-open file read recovery and mobile run-editor-file proof with intercepted execution |
| Parent | AppCodeEditor save recovery, RoleDetail acceptance evidence, screenshots and ledger | Personally inspect design; 16/64 routes accepted for UI, 48 in progress |

## Review gates for each handoff

1. Review source and consumer contracts, including behavior changed unintentionally.
2. Resolve design-system inconsistencies and unsupported product claims.
3. Run scoped behavioral tests and lint in the implementation batch.
4. Parent runs actual rendered components with long content, narrow/wide sizes, light/dark themes and relevant failure/keyboard states.
5. Parent runs a combined TypeScript check after integrating the batch, reviews screenshots and records limitations in the coverage ledger.

Browser fixtures may run in parallel using independently logged-in sessions: admin, execution and forms each own a separate auth file; the parent exclusively owns auth.json. Never copy a rotating session across workers or call logout/revoke. Each context saves its own session in finally. Agents gather functional evidence and screenshots; the parent personally reviews visual design and signs off routes. Implementation and disjoint component tests run in parallel. No agents commit, push, edit the coverage ledger or run full builds. The parent owns those integration boundaries.

## Next allocation

After each current handoff reaches review, reuse its slot for a bounded remaining feature group. Prioritize agent review/tuning and chat, then user/entity management and dependency/solution surfaces. Assign exact files before starting; never overlap write ownership. Keep final route acceptance separate from first-pass file coverage.

All previously required main reconciliation, production build, V1 compatibility, branding, complete route/state review and exact-HEAD pre-PR gates remain open.

## Throughput and reporting correction (2026-09-07)

The user explicitly requested cheaper Terra implementation in parallel with parent review. Three existing Terra slots are active with exclusive ownership. Scratch-fixture syntax checks do not prove runtime correctness; parent source review must reject invalid module boundaries, mismatched props, stale mock-stage routing and authentication mutations before browser execution.

After this bounded batch, allocate work by complete page groups rather than repeatedly restyling individual records:

1. Workflow execution/history and agents/review/tuning.
2. Forms/designer/runtime and editor/app editor/dependencies.
3. Organizations/users/roles and remaining list/detail/settings surfaces.
4. Authentication, shared shell, custom branding and V1/V2 compatibility acceptance.

Each next assignment must name exclusive source files, concrete known gaps and its acceptance scenarios. Agents own implementation and scoped checks; parent owns integration and screenshot acceptance. Reuse existing rendered evidence where current shared/source contracts remain valid; rerun affected checks when changes invalidate it. Do not broaden a completed check without a specific unresolved requirement or defect.

Report first-pass inventory separately from accepted routes and final delivery gates. The current baseline is 351/351 feature records in progress, zero pending, and 11/64 routes signed off for UI migration. This is not a completion percentage. Final main reconciliation, build, required tests and exact-HEAD pre-PR remain required.
