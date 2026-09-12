# List page review — second pass

Scope reviewed: Organizations, Users, Roles, Tables, Integrations, Knowledge, Config, Events, Solutions.

What changed in this pass:

- Added the shared list-shell wrappers `ListPageHeader` and `ListToolbar`.
- Normalized the page chrome across the nine owned list pages without changing data flow, permissions, dialogs, or terminology.
- Fixed the most concrete mobile/accessibility issues found in the current captures:
  - `Tables` now has a labeled primary action instead of an icon-only `+`.
  - `Organizations` now uses a semantic success treatment for the active state instead of a loud primary-fill badge.
  - `Users`, `Roles`, and `Tables` now give long names room to truncate with `min-w-0` instead of forcing the row to fight its container.
  - `Tables` carries a labeled scroll region for the horizontally scrollable list.

Evidence-backed remaining gaps:

- The list pages are still a mixed set of table, card, and bulk-action surfaces by design. `Tables`, `Config`, `Knowledge`, and `Events` still rely on dense table layouts because they expose real metadata and row actions that should not be hidden behind a generic mobile replacement.
- `Solutions`, `Integrations`, and `Knowledge` still use page-specific bulk/filter controls. They now wrap more cleanly, but they are intentionally not collapsed into a single framework component because the controls are domain-specific.
- `Workflows`, `Forms`, `FleetPage`, and `Applications` remain outside this batch.

Verification:

- Ran targeted client unit tests for the affected page specs.
- Ran a TypeScript no-emit pass for the client.
- Reviewed the current list-pass captures at 390px and 1440px for the owned list pages.
