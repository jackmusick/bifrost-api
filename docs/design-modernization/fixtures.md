# Design modernization fixtures

This folder captures the synthetic review scenario used for isolated debug
verification.

## Contents

- `fixtures/design_review_workflow.py` - source for the synthetic workflow that
  logs, waits briefly, then returns either a success payload or a deliberate
  failure.
- `fixtures/design_review_form_schema.json` - schema payload used to create the
  representative form.
- `fixtures/commands.md` - reproducible CLI commands for registering the
  workflow, creating the form, and running success/failure executions.

## Notes

- These fixtures are synthetic and harmless.
- They are documentation only; the live entities are created through the CLI
  against the seeded debug stack.
- No tokens, passwords, or external service references are included here.

### Additional isolated outcome evidence

- Cancelled run: `0e87e3ce-c0eb-4503-92a0-c84243ece024` (`DR-cancel-ui`).
- Failed run: `fb897cc6-5f37-42e0-b758-f59ca7d28734` (`DR-fail-ui`, should_fail=true).

Both were submitted through the workflow launch page and used only the synthetic design_review workflow.

### Entity relationship recovery (2026-09-06)

`/tmp/bifrost-design-review/relationship-filter-check.cjs` exercises the real `/entity-management` host with intercepted workflow/form/agent/app/dependency reads. Light/dark at320/1440 with reduced motion: initial lookup failure hides unrelated records without false empty claims; retry restores related record; page refresh failure retains it; retry then Clear restores full list. Checks banner and record overflow,44px actions and record action viewport visibility after scrolling. Screenshots: `relationship-error-{theme}-{width}.png` and `relationship-stale-{theme}-{width}.png` in the same directory. Dark320 screenshots inspected; first pass exposed collapsed mobile record-list height, corrected and rerendered. Synthetic query responses; does not prove live dependency API behavior or organization/access writes. Drag/keyboard/touch assignment still pending.

### Entity assignment review (2026-09-06)

`/tmp/bifrost-design-review/entity-assignment-check.cjs` exercises real EntityManagement with intercepted workflow/org/role/collection reads and all fixture writes intercepted. Light/dark320/1440 reduced motion: select by named checkbox, keyboard Apply organization, verify snapshot names and no pre-confirm write, reject PATCH, retry, verify focus restoration, cancel clear roles without write, confirm clear-role payload, add specific role through POST before role_based PATCH. Checks44px review buttons and horizontal overflow. Screenshots `entity-assignment-error-{theme}-{width}.png` and `entity-assignment-{theme}-{width}.png`; light/dark320 inspected. Actual backend authorization/role persistence not exercised. Focused hook test covers the four entity endpoint/body mappings; focused target test covers drag registration and busy gating.

### Entity toolbar and filters (2026-09-06)

`/tmp/bifrost-design-review/entity-toolbar-check.cjs` exercises real EntityManagement with intercepted collection reads. Light/dark320/1440, reduced motion: mixed select-all after individual selection; search hides a selected record and exposes hidden-selection count; Clear search restores focus; explicit date sort and descending order reorder actual records; keyboard-open filters; duplicate Workflows labels in type/organization groups remain distinct; organization selection filters records; Escape restores trigger focus; Clear all filters restores records; Clear selection updates summary. Measures44px options and buttons, viewport-constrained popover and toolbar overflow, plus sort/direction alignment. Screenshots `entity-filters-{theme}-{width}.png` and `entity-toolbar-{theme}-{width}.png` in the same directory. Dark320 screenshots reviewed. No backend mutations or live filtering API proof implied; filtering is client-side against fixture collections.

### Entity collection availability and surface spacing (2026-09-06)

`/tmp/bifrost-design-review/entity-collections-check.cjs` uses intercepted workflow/form reads in the actual host. Light/dark320/1440 reduced-motion cases hold forms while rendering workflows, fail forms without claiming empty, retry forms, fail refreshed workflows while retaining both collections, and recover again. Asserts44px retry, no status overflow, computed card padding20px default and16px compact. Screenshots `entity-collections-error-{theme}-{width}.png` and `entity-collections-stale-{theme}-{width}.png`; dark320 inspected before/after padding correction. No live backend failure contract or mutations exercised.

### Execution page gutter alignment (2026-09-06)

`/tmp/bifrost-design-review/execution-spacing-check.cjs before|after` opens the existing seeded execution at `/history/b7bbbe3a-1749-4adb-9324-97e72163e92b` without writes. Measures actual main/header/body padding and captures light/dark320/1440. Main is0px on this route; before mobile body24px versus header16px; after body/header16px, desktop32px retained. Screenshots `execution-spacing-{before|after}-{theme}-{width}.png`. Dark320 after inspected; this proves gutter alignment only, not whole execution page completion.

### Form sharing spacing (2026-09-06)

`/tmp/bifrost-design-review/form-share-spacing-check.cjs before|after` mounts actual FormShareDialog with an unbroken long form name and intercepted failed `/api/forms/spacing*` reads. Light/dark320/1440 reduced motion; private link and website load-error tabs. After checks tab/button44px targets, viewport containment, private URL field width>190px and copy/open row alignment. Screenshots `form-share-{private|website}-{before|after}-{theme}-{width}.png`. Dark320 private before/after inspected. No publication changes, external navigation, real clipboard or HMAC secret operations exercised by this fixture.

### Execution header action alignment (2026-09-06)

`/tmp/bifrost-design-review/execution-header-check.cjs` opens seeded completed execution, asserts44px actions, equal-width Editor/Rerun at320px, same-row alignment and page-gutter alignment; opens/dismisses Rerun confirmation without executing. Light/dark320/1440. `execution-header-running-check.cjs` intercepts execution/workflow GETs to supply a long unbroken name and Running state, then checks Editor/Cancel alignment and cancel review without submitting. Light/dark320/768/1440; tablet actions must sit below title when container is narrow. Screenshots `execution-header-{theme}-{width}.png` and `execution-header-running-{theme}-{width}.png`. Dark mobile/desktop and tablet screenshots inspected. No actual execution/cancellation or editor navigation performed.

### HMAC secret metadata recovery (2026-09-06)

`/tmp/bifrost-design-review/hmac-list-check.cjs` mounts actual FormShareDialog/HMAC tab with synthetic metadata and intercepted reads/PATCH. Light/dark320/1440: initial500, no false empty, retry, long-name record and44px actions, simulated deactivation followed by failed refresh retains cached record, retry displays inactive status. Screenshots `hmac-list-{theme}-{width}.png` and `hmac-stale-{theme}-{width}.png`; dark320 stale inspected. No real secret material retrieved or changed. The form-spacing fixture's earlier glob did not cover subpaths; it now uses the same root/subpath regex. Earlier website error screenshots reflected nonexistent-form read failures, not the intended intercepted500.

### One-time HMAC reveal and clipboard recovery (2026-09-06)

`/tmp/bifrost-design-review/hmac-reveal-check.cjs` drives actual FormShareDialog/HMAC create form with intercepted synthetic POST/GET and stubbed clipboard. Light/dark320/1440: create synthetic value, verify full wrapped text, keyboard focus selects it, reject async clipboard and legacy fallback, retain reveal/error, retry with successful stub, announce success, dismiss. Asserts44px controls and no horizontal overflow. Screenshots `hmac-reveal-{theme}-{width}.png`; dark320 inspected. Synthetic display text only; no real secret or actual clipboard change.

### HMAC deletion and create pending ownership (2026-09-06)

`/tmp/bifrost-design-review/hmac-delete-check.cjs` exercises synthetic metadata with held DELETE→500→retry204. Checks pending confirm/Cancel and tab guards, Escape retention, inline error/named target,44px controls, retry and resulting empty list in light/dark320/1440. Screenshots `hmac-delete-error-{theme}-{width}.png`; dark320 inspected. Underlying sharing tabs are aria-hidden by the confirmation modal; pending tab assertion intentionally includes hidden elements.

`/tmp/bifrost-design-review/hmac-create-pending-check.cjs` holds a synthetic POST then returns500; checks fields/Cancel/tabs disabled, outer close/Escape does not reach the host close callback, one request only, then retained name draft and usable Cancel. No real secrets or raw secret values are involved in either fixture.

The HMAC create pending fixture now checks the extracted form’s inline failure message, retained name, enabled Retry creation, and 44px input/button targets. Screenshots `hmac-create-error-{theme}-{width}.png` scroll the error into view so the mobile recovery controls can be inspected. Requests remain intercepted; no live secrets are created.

`/tmp/bifrost-design-review/embed-code-check.cjs` and `website-embed-code-check.cjs` mount FormShareDialog in HMAC and synthetic published website states. Each covers light/dark320/1440, keyboard selection, 44px copy target,20px source padding, overflow containment, rejected clipboard plus failed fallback, and successful retry with exact copied text. Screenshots `embed-code-{theme}-{width}.png` and `website-embed-code-{theme}-{width}.png`. Publication reads are intercepted and no live mutation is performed.

`/tmp/bifrost-design-review/embed-options-check.cjs` mounts the actual sharing dialog with synthetic published metadata. Light/dark320/1440 assertions cover theme selector/option44px targets, full-label Show Header toggling, keyboard Transparent Background toggling, matching generated iframe parameters and options containment. Screenshots `embed-options-{theme}-{width}.png`; light320 inspected. Requests are intercepted, with non-GET requests rejected by the fixture.

`/tmp/bifrost-design-review/website-restrictions-check.cjs` mounts the actual sharing dialog with synthetic published metadata. Light/dark320/1440: keyboard disclosure, long-origin autosave PUT failure, retained draft,44px retry, identical parsed retry payload, success status and collapse/reopen preservation. All requests intercepted; no live publication writes. Screenshots `website-restrictions-{theme}-{width}.png`, dark320 inspected.

`/tmp/bifrost-design-review/sharing-toggle-check.cjs` mounts actual FormShareDialog with synthetic published reads. Light/dark320/1440 checks publication label review/Cancel without writes,44px label targets, keyboard spam toggle, held PUT pending/disabled announcement, failed response restoring checked state and no dialog overflow. Screenshots `sharing-toggle-{theme}-{width}.png`, dark320 inspected. No live publication changes.

`/tmp/bifrost-design-review/publication-review-check.cjs` mounts FormShareDialog with synthetic published metadata. Light/dark320/1440: DELETE held then500, pending Cancel/confirm and underlying tabs disabled, Escape cannot dismiss, inline error retained,44px actions, retry204 closes review and refreshed metadata shows unpublished. Screenshots `publication-review-{theme}-{width}.png`. All requests intercepted; no actual publication changes.

`/tmp/bifrost-design-review/publish-review-check.cjs` and `rotate-review-check.cjs` extend publication recovery to PUT publish and POST rotate-key. Each covers light/dark320/1440, held first mutation then500, preserved review, pending guards, retry success and refreshed published state. Publish includes long capability names/warning; rotation checks changed synthetic key in the generated iframe. Final checks include20px dialog padding and44px rotation trigger. Screenshots `{publish|rotate}-review-{theme}-{width}.png`. Every request is intercepted; no live changes.

`/tmp/bifrost-design-review/confirmation-editor-check.cjs` mounts FormShareDialog with actual Tiptap editor and synthetic publication/form reads. Light/dark320/1440: editing, preview/back preserves draft,44px tabs/update, held PATCH pending/outer-tab guard and parent close-callback suppression,500 retained draft/inline retry, successful retry disables unchanged Update. Screenshots `confirmation-editor-{theme}-{width}.png`. All form requests intercepted; no live changes.

`/tmp/bifrost-design-review/sharing-form-identity-check.cjs` mounts actual FormShareDialog/Tiptap, holds first-form metadata, rerenders with a second form ID, edits its confirmation, then releases and awaits the first response. Light/dark320/1440 asserts second private URL, preserved unsaved draft and enabled Update. Screenshots `sharing-form-identity-{theme}-{width}.png`. Only intercepted synthetic reads; no writes.

`/tmp/bifrost-design-review/rotation-draft-check.cjs` extends rotate review verification by editing a real confirmation draft first, then verifying that the post-rotation refresh updates the synthetic iframe key while preserving the draft and enabled Update action. Light/dark320/1440, intercepted mutation failure/retry; no live changes.

`/tmp/bifrost-design-review/sharing-settings-order-check.cjs` verifies serialized origin/spam writes in actual FormShareDialog, light/dark320/1440. Held first origin PUT, edit latest origin, assert no second request beyond debounce; release then latest-origin save; subsequent spam change carries latest origin and new spam value. Conflicting switches/rotation disabled while held. Requests intercepted; no live publication changes. Existing website-restrictions fixture also rerun for failure/retry behavior.

`/tmp/bifrost-design-review/origin-refresh-check.cjs` mounts actual sharing UI with synthetic published state, edits an origin and rotates before autosave. It asserts the refreshed empty server origin list does not erase/collapse the draft, followed by PUT of that draft and saved status. Light/dark320/1440; all requests intercepted, no live publication changes.

Production build artifact: `/tmp/bifrost-design-review/production-dist-20260906`, copied from the isolated client container after a successful Vite build. `production-smoke.cjs` and `production-https-smoke.cjs` serve that artifact via browser request interception and relay API traffic to the preview. They do not deploy it. Current runtime checks are failing/incomplete (private WebSocket rejection; HTTPS startup/relay teardown), and must not be cited as clean production or realtime verification. Error output is sanitized after a temporary-session teardown incident; its refresh token was revoked and storage file removed.

Preferred production smoke: run Vite preview inside the existing client container (`docker exec -it bifrost-debug-377ed48d-client-1 ./node_modules/.bin/vite preview --host 0.0.0.0 --port 4173 --strictPort`), then `/tmp/bifrost-design-review/production-server-smoke.cjs`. Uses direct built assets and real proxy transports at the NetBird peer port4173, without request interception. Light/dark320/1440 Workflows startup:53 built assets,0 page errors in all4. Screenshots `production-server-{theme}-{width}.png`, dark320 inspected. Temporary server stopped after verification; main preview remains active. This supersedes the failed interception smoke as startup evidence, while full route/V1/realtime acceptance remains pending.

`/tmp/bifrost-design-review/sharing-close-flush-check.cjs` verifies actual FormShareDialog parent callback ownership at light/dark320/1440: Close immediately after origin edit, held PUT, failed save retains draft/retry without close callback, second close flush succeeds and calls parent once. All writes intercepted and exact origin payload retained.

`/tmp/bifrost-design-review/sharing-close-recovery-check.cjs` extends close-flush evidence across tabs: edit origins then switch to Private Link before Close; failed intercepted PUT must select Website Embed and focus Retry saving. Draft retained and successful second close flush calls parent once. Light/dark320/1440 screenshots `sharing-close-recovery-{theme}-{width}.png`.

### Table detail route fixtures

`/tmp/bifrost-design-review/table-detail-check.cjs before|current` renders synthetic long-name table data at320/768/1440 in both themes. Current mode checks desktop cell alignment, document overflow and44px filter controls. Captures: `table-detail-{before,current,filters}-{theme}-{width}.png`.

`table-detail-interactions.cjs` verifies page-local search with reachable pagination, server-query filter payload, mounted filter draft retention, close focus, keyboard JSON disclosure, pending deletion dismissal guard,500 deletion retry and cached query failure/retry. Width320 uses700px height; other widths900px. All table API requests are intercepted. Custom branding and complete editor/permission acceptance are not established by this fixture.

`/tmp/bifrost-design-review/table-detail-states.cjs` covers held initial loading,500/403/404 table failures, solution back links, document query failure/retry and confirmed empty pages at320/1440 in both themes. Intercepts purple branding and compares actual CSS primary/activity-gradient values against the tenant palette. Captures `table-detail-loading-*` and `table-detail-empty-branded-*`.

`/tmp/bifrost-design-review/document-dialog-route-check.cjs` opens create/edit from the actual table route and exercises real Monaco in light/dark at320x600/1440x900. Invalid/non-object JSON cannot submit; held save disables controls and dismissal;500 retains the JSON and retry sends the identical POST/PATCH payload. All writes intercepted. Captures `document-dialog-{current,error}-{create,edit}-{theme}-{width}.png`. This does not establish all tenant palettes, zoom/density or V1 acceptance.

### App entry and legacy component verification

`/tmp/bifrost-design-review/app-route-check.cjs` visits real published and preview legacy-component apps in light/dark at320/1440. It holds initial metadata, asserts named opening status and static reduced-motion seam, returns500, then allows the actual metadata/bundle request after retry. It operates Dialog, CommandDialog search, Input, Select and CalendarPicker tab through the V1 runtime. Purple branding is intercepted; no app writes occur. Captures `app-route-{loading,error,v1}-{published,preview}-{theme}-{width}.png`. This establishes specific route/component behavior, not the complete V1/V2 contract.

`/tmp/bifrost-design-review/bundle-feedback-check.cjs` mounts actual BundleFeedback exports in the authenticated host at320/1440x700 in light/dark. It checks long error wrapping, reload callback, all7 build diagnostics with keyboard disclosure, independent dismissal callbacks,44px controls and no page overflow. Captures `bundle-load-failure-{theme}-{width}.png` and `bundle-notices-{theme}-{width}.png`. Component-level evidence only; transport-triggered notice lifecycle and custom-brand states are pending.

`/tmp/bifrost-design-review/bundle-runtime-check.cjs` operates the real V1 preview fixture and injects synthetic updates into its subscribed client websocket dispatcher. It checks draft preservation across build error/dismiss/reappearance, successful same-entry recovery and failed import. It does not trigger server rebuilds or validate server event delivery. Captures `bundle-runtime-import-error-{theme}-{width}.png`.

`/tmp/bifrost-design-review/app-header-check.cjs` extends app-route verification with long-name bounds,44px header buttons, no header overflow and account-menu keyboard focus return for real published/preview V1 apps in light/dark320/1440 under purple branding. Captures `app-header-{published,preview}-{theme}-{width}.png`.

### Durable cold-runtime regression

Run `docs/design-modernization/fixtures/bundle-cold-check.cjs` with Node after installing client dependencies. Set `BIFROST_REVIEW_URL` to the isolated development preview and `BIFROST_REVIEW_AUTH` to a Playwright storage-state file for that preview. Optional `BIFROST_REVIEW_OUTPUT` controls screenshot output; default `/tmp/bifrost-design-review`. The script refreshes the supplied storage-state file as it proceeds. Never commit that authentication file.

The fixture mounts the actual BundledAppShell without route preloading, fulfills a synthetic inline ES-module bundle, then fails a later import. It checks preserved unsaved state, successful-update recovery and migration-notice dismissal persistence in both themes at320/1440. Draft-channel connection is stubbed and client callback dispatch is synthetic; no real app is edited or rebuilt.
