# UI acceptance coverage plan

Current as of 2026-09-10 for the design-system modernization worktree. This document is the active acceptance plan and status checkpoint. Detailed historical audit notes live in the route/action inventories linked below.

The current ledger is **56 targeted browser journeys passed** across targeted iteration runs: Dashboard, SECURITY-02 real recovery login, SECURITY-03 password change, non-user role assignment, and the form builder rebind/reorder/delete-field persistence cases are included. The form builder journey also verifies deactivation and the retained Disabled card after reload.

The acceptance denominator is route families and primary settings panels, plus shared UI primitives where a primitive failure would break multiple routes. It is not every possible click, filter, sort, validation branch, or provider-specific callback. Lower-layer component/backend/contract tests remain the right level for validation matrices, failed-save retries, formatting branches, provider adapters, and edge cases that do not need a full rendered route.

Current inventories:

- [Acceptance closure matrix](acceptance-closure-matrix.md): route-family denominator, primary browser proof, lower-layer proof, external limits, and finite required gaps.
- [Remaining acceptance reconciliation](remaining-acceptance-reconciliation.md): concise closure list and decisions after the current pass set.
- [Core experiences](core-acceptance-inventory.md): Home, Dashboard, chat, execution history, apps, agents, forms, and workflows.
- [Administration and data](admin-data-acceptance-inventory.md): organizations, users, roles, config, files, tables, knowledge, solutions, diagnostics, audit, and reports.
- [Connected resources](resources-acceptance-inventory.md): integrations, events, entity management, MCP, and resource ownership patterns.
- [Settings](settings-acceptance-inventory.md): platform settings and account settings panels.
- [Access and shell](access-shell-acceptance-inventory.md): auth, public routes, protected routes, layout, navigation, menu, and shared shell controls.

Completion conditions for this acceptance phase:

1. Keep all implemented primary journeys passing together; the final targeted form builder case passed.
2. Complete source and documentation review, then commit and push without merging the review branch into main.
3. A clean current-main/pre-PR run validates the ledger without relying on dirty-worktree-only evidence.
4. Nightly coverage runs successfully on the agreed stack.
5. Desktop/mobile visual review assesses the redesigned flows and screenshots.
6. The remaining gaps listed in the closure matrix are either closed, explicitly moved to lower-layer proof, or marked as external/provider limits.

Primary browser coverage now includes real local journeys for Home collection/catalog/launch behavior, Dashboard metrics/refresh/drilldown, workflow metadata and execution entry, history/detail/realtime/scheduling, forms browse/runtime/designer persistence, public/embed forms, apps editor/preview/runtime, agents fleet/create/review/tuning-apply persistence, chat persistence, config lifecycle, tables/files/knowledge/resource management, organizations/users/roles, solutions lifecycle/export/runtime, integrations mapping/cards, generic event/webhook delivery, MCP management/settings/catalog, AI chat instructions, AI pricing, operational reports, account profile/security/password, and shell/shared navigation behaviors listed in the inventories.

Explicit local limits remain: real third-party OAuth/provider callbacks, secure credential runner behavior, external model quality, external assistant installation, and exhaustive every-permutation UI coverage. These are outside the local acceptance denominator unless a deterministic fixture exists.
