# Organizations UI acceptance

Status: UI Verified for `/organizations`. Parent acceptance on 2026-09-07. Global shared-family, backend authorization and release gates remain separate.

## Composition and list behavior

Desktop uses a table with editable names and overflow actions; mobile uses labeled cards with wrapping names/domains/IDs. Provider and active/inactive states use semantic tokens. Provider disable remains protected. The toolbar preserves search and inactive filtering, with44px mobile actions.

Current custom-purple light/dark320/1440 list browser9928 passed mobile cards versus desktop table, no page overflow, provider disable protection, inactive filtering and disable-dialog cancellation. Parent inspected light320 and dark1440 captures. The first run96901 stopped on an obsolete fixture title; corrected to the current “Disable organization?” title before the passing run.

Browser70994 passed four current custom-brand/theme/width cases with30 records: loading, initial failure/retry, no false empty state, last-record action reachability, search by domain, clear-search focus, cached-record retention during refresh failure, preserved search and create/cancel. Earlier list-action-audit.md evidence confirms name/action consistency across the platform.

## Create and edit recovery

Create/edit bodies scroll within bounded dialogs and keep footer actions visible. Failed mutations retain drafts, focus an inline recovery alert and offer explicit retry. Hook error toasts are disabled for these forms to prevent duplicate errors. Synchronous guards and pending inert states protect against duplicate submission, editing and dismissal during saves.

Menu-driven rename restores focus using stable organization IDs rather than stale names. The focused error uses a semantic border without a browser-default white outline. Interactive buttons retain normal focus styling. MutationRetryAlert is a reusable page-local component.

Parent rejected the first candidate's editable pending fields, BODY focus after rename and strong error outline. Corrected browser52058 passed four light/dark320/1440x600 cases: held POST/PATCH failures, inert edit tabs, Escape protection, retained drafts, focused/visible inline errors, hit-testable footer actions, explicit retries and focus within the edited record after rename. Parent inspected corrected dark320.

## Embedded Instructions

The Instructions tab reuses the scoped RequiredInstructionsSettings component. Browser53882 passed four current custom-brand cases covering initial read failure/retry, readonly editor while saving, preserved draft through failure and equal-payload explicit retry. Parent reviewed dark320 error presentation and reachable scrolling content.

Initial instruction fixtures28481/66709 returned503 for PUT and unexpectedly succeeded through authFetch's intentional idempotent transient-error retry. Corrected fixtures use500 to exercise the user-visible failure state; no product bug was inferred from those initial fixture failures.

## Validation and boundaries

Final10 Organizations tests7353 and full TypeScript74094 pass; agent scoped ESLint passed. Tests include create/edit recovery, pending locks, rename focus, provider protections and disable-confirmation retry retention. Final diff check passes.

All browser organization/instruction reads and mutations used intercepted synthetic fixtures. No real organizations or instruction settings were changed. Route UI acceptance does not imply completion of all132 pages,357 feature components,53 primitives or release-wide gates.
