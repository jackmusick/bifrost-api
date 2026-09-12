# Bifrost product design modernization

Status: in progress. No page is complete until its individual coverage record is verified.

## Authorized scope

Replace the platform's existing visual design with the Bifrost Design System and review every page and component from a senior product-design perspective. Preserve familiar navigation, terminology, domain behavior, permissions, runtime integrations and data. Improve hierarchy, consistency, responsive behavior, accessible interaction, purposeful motion and craft.

Priority families: workflow and agent executions; form execution and designer; all lists; dependencies; the complete code-editor workspace. Remaining authenticated, public, embedded, settings, diagnostics and reporting surfaces receive individual review as well.

Canonical design source: `gobifrost/design-system`, commit `11da72e` (local `/home/jack/GitHub/design-system`). Product baseline: `0598020e3`. Working branch: `codex/design-system-modernization`.

## Compatibility constraints

V1 included components are public APIs. Preserve their export names, props, composition, refs, events and accessible behavior. Keep host runtime and app-code-platform resolution stable. Test representative legacy app usage, not just platform imports. Do not replace the richer existing components with narrower catalog APIs. New visual roles must respect custom branding and app mounting/portal boundaries.

Keep Monaco and React Flow behavior unless a concrete defect requires a bounded change. Keep existing network, execution and platform-job transports. Synthetic fixtures are for evidence, never production runtime replacements.

## Mobile acceptance criteria

Mobile review must establish that each page is easy to understand and operate, beyond preventing overflow. Choose a presentation that fits the task: labelled records for data lists where tables lose meaning, clear primary actions, readable metadata, accessible sorting/filtering and reachable bulk actions. Preserve access to the complete data and desktop capabilities. Keep tables where comparison requires them only with a deliberate narrow-screen interaction.

Inspect visual hierarchy and actual task completion at narrow widths and short heights. A screenshot that fits and a 44px button alone do not establish completion. Review grouped-button selected, hover and focus treatments against canonical branding in both themes. Current shared and route controls have been reviewed against those tokens, and the editor's hard-coded green Validate action was removed. The exact historical button group reported by the user could not be identified from the available context; do not claim that specific screenshot was reproduced. Remaining green source accents belong to status or entity categories, not grouped-button selection.

## Delivery sequence

1. Generate complete route/page/primitive/feature inventory and evidence ledger; trace V1 contracts; capture baseline in an isolated debug stack.
2. Establish theme and branding foundations: default Bifrost colors, custom-brand accessible action colors, brand-derived activity gradient, semantic states and reduced motion.
3. Modernize shared shell and primitive internals while preserving consumer APIs.
4. Design and verify execution, form and editor reference experiences early; promote reusable structures.
5. Review and modernize every remaining page family, including overlays, permissions and narrow layouts.
6. Reconcile all coverage rows, remove competing legacy styling, run scoped and full required checks, and provide the reviewable NetBird preview.

## Evidence and completion

Track every source in `coverage.md` and `inventory.json`. Pending is the default; inherited token changes alone do not establish individual page completion. Record baseline and final screenshots, desktop/tablet/mobile, light/dark, default/custom branding, keyboard/focus, reduced motion, loading/empty/error/success, long-content/overflow and applicable permission states. Keep known defects separate from preserved behavior.

Use Docker and the repo's `debug.sh` / `test.sh` workflows. Before opening a PR, commit the exact candidate, reconcile current origin/main and pass `./test.sh pre-pr`. Do not claim platform deployment or live integration without performing and verifying it.

## Component structure

Extract meaningful UI sections into actual React components, including page-local components under the page's components folder. Route components should compose those sections and coordinate state. Reuse across routes is not a prerequisite for extraction. Avoid leaving new record layouts, filter groups and action sections as large inline JSX blocks. Preserve stable shared and V1 APIs; promote a page-local component to shared ownership when multiple consumers need its contract. User explicitly clarified this requirement during implementation.
