# Platform settings review — 2026-09-08

The two Settings routes are UI Verified after the final reconciliation below. All12 registered panels remain in scope: Models, Embeddings, Chat Instructions, Memory, Default MCP Instructions, Usage & Pricing, MCP, GitHub, Authentication, Workflow Keys, Branding, Maintenance.

## Navigation checkpoint

Current source lazily mounts visited panels and preserves their drafts while hiding inactive controls. Unknown URLs canonicalize to Models; browser history expands the destination section. Parent added this after finding that prior subsection navigation unmounted drafts. Seven Settings tests37226 and scoped lint77087 pass. Browser57835 passes light/dark320x480 and1440x900 canonical URL recovery, draft retention, history navigation, mobile/desktop inverse controls and page bounds. Parent inspected dark320 retained instructions and light1440 Settings navigation/editor composition. All fixtures synthetic.

Existing panel-specific rendered work is recorded in PROGRESS.md and scripts under /tmp/bifrost-design-review; those checkpoints must be reconciled with current source, not discarded or assumed complete. Current all-panel failed-read sweep is underway. Security account work is tracked separately in account-settings-review.md.

Ledger correction: Dashboard is already Verified. The two open `/` entries are Layout and ContentLayout, not dashboard pages. Current total is58 Verified/6 In progress after account-settings acceptance.

## Failed-read sweep

Initial55304 fixture incorrectly failed the auth-refresh endpoint and captured loading/login states; rejected. Corrected55001 completes48 cases (12 panels × light/dark ×320/1440), explicitly waiting for Settings and checking the destination URL. No page-width overflow or page errors. Most panels expose explicit retry; Branding uses the required successful shell-brand fixture, so its configuration failure is not proven by this sweep. Workflow Keys lacks read feedback and needs repair: current source ignores keys/metadata errors, can show false empty/orphaned states, replaces cached rows while refreshing, and still has toast-only mutations with auto-closing revoke. Assigned bounded implementation; it remains unaccepted.

Parent inspected narrow Workflow Keys and wide MCP error screenshots. Navigation tests and current render evidence do not complete all panel interaction gates. Previous panel-specific checks remain useful and will be reconciled without blanket reimplementation.

## Pricing panel review

Terra refined shared PricingEditDialog/PricingDeleteDialog with bounded scrolling bodies, fixed headers/actions, focused persistent failures and canonical destructive styling. Existing field readiness/payloads and completed-delete fallback remain intact. Focused pricing dialog/page tests and scoped lint pass. Parent browser60608 passes four light/dark320/1440 read retry, populated long model/rates, create/edit/delete pending locks, retained failures/exact retries, saved-row focus and successful deletion fallback. All writes intercepted with synthetic pricing records. Parent inspected dark320 edit failure and light1440 deletion failure. Supplemental16253 captures complete rate rows. Pricing panel accepted subject to final shared-family/release gates; Settings route remains open.

## Workflow Keys repair checkpoint

Agent extracted WorkflowKeysList and create/reveal/revoke dialogs and wired independent key/metadata recovery and cached row retention. Parent73470 passed reads/create/reveal/copy then caught missing focus after the programmatically opened reveal closes. Parent screenshot review also caught fixed-height badges clipping wrapped names and excessive empty error-region padding. Sent those fixes back; success revoke now needs a stable heading fallback because Create may be disabled during list invalidation. Parent corrected services/workflowKeys.ts to display string API error detail with readable fallback instead of `[object Object]`. No live keys created/revoked. Final workflow-key tests/browser acceptance remain pending.

## Workflow Keys browser acceptance checkpoint

Final parent browser82021 passes all four light/dark320/1440 cases: independent reads/retries, no false empty or orphan state, retained cached rows, create/reveal/copy failures and exact retries, revoke pending dismissal locks, Cancel row focus and successful-revoke heading focus. Parent inspected dark desktop records and narrow create failure, plus light narrow wrapped workflow badge and revoke failure. Six focused tests and scoped lint pass. Full TypeScript57473 caught an unsupported AlertDialog pointer handler; removal and final typecheck remain pending. All writes were intercepted synthetic fixtures.

## GitHub evidence reconciliation

Read-only reconciliation confirmed prior four-case light/dark320/1440 browser evidence for config read/cached refresh, token validation and draft retry, long repository/branch selectors, create pending/failure/draft/focus, and disconnect pending/failure/exact retry/focus. Source review found no blocking GitHub flow defect. Existing native private-repository checkbox is a remaining primitive consistency refinement; its label already supplies a touch-sized target.

## Current reconciliation — follow-up

TypeScript96712 passes after removing the unsupported AlertDialog pointer callback. GitHub checkbox now uses the canonical primitive; parent41770 confirmed checked state changes and create failure/draft recovery in four cases. However, parent image inspection at320x480 found the dialog footer below the viewport: prior900px-height evidence did not establish short-screen usability. Bounded fixed-header/footer repair is underway. Removed duplicate create error toast; the dialog already renders the mutation failure. GitHub acceptance remains pending this concrete repair.

Existing current-source/evidence reconciliation found no new blocker in Models, Embeddings, Chat Instructions, Memory, Default MCP Instructions, Authentication, Branding, Maintenance or MCP. The source still exposes existing Maintenance scheduler-guided timeout behavior and MCP manifest placeholder; those are preserved product behavior, not new migration scope. Branding failure proof and final parent panel acceptance remain to be reconciled.

## GitHub short-screen repair verified

Parent38682 passes four light/dark320x480 and1440x900 cases with explicit whole-dialog viewport bounds, canonical checkbox changes, pending locks, focused inline failure, retained drafts and Cancel opener focus. Parent inspected dark320 failure: header and both actions stay visible while fields scroll. Duplicate failure toast removed; success feedback preserved. Focused dialog test and scoped lint pass. This resolves the concrete GitHub short-screen blocker.

## Branding recovery and shell lifetime

Parent8982 four initial failure/retry cases pass, with dark320 failed-read and recovered draft images inspected. Extended39238/58903 exposed a real shell integration bug: OrgScopeContext set brandingLoaded false on every refresh, causing App to unmount the current route and discard unsaved fields. Parent retained existing loaded branding while refreshing (initial state still gates first load). Context regression6268 passes. Final73887 passes all four light/dark320x480/1440x900 initial error/retry and synthetic logo-upload/post-upload read failure/retry cases, preserving unsaved application name and primary color and disabling saves during invalid reads. All writes intercepted. Five Branding/GitHub dialog tests68667 pass; final scoped lint/full TypeScript11956 pending.

## Panel reconciliation

All12 panels now have source and rendered evidence: Models provider/profile/assignment recovery; Embeddings reindex pending/failure/retry; Chat Instructions retained drafts/save recovery; Memory toggle/cleanup states; Default MCP Instructions scope/save recovery; Pricing current create/edit/delete; MCP read/details/activation/create/delete/OAuth; GitHub config/token/repo/branch/create/disconnect with current short-screen repair; Authentication OAuth/preference recovery; Workflow Keys current read/create/reveal/copy/revoke; Branding current read/recovery and custom palette preview; Maintenance results/queue/timeout/polling lifecycle. Prior browser scripts are enumerated in PROGRESS.md; this reconciliation supplements them rather than discarding their evidence. Existing MCP manifest placeholder and Maintenance scheduler-guided timeout behavior remain product limitations. Final shared-family, V1, full-suite and release/deployed-candidate gates remain separate.

## Final route acceptance

Final scoped lint/full TypeScript11956 pass. Parent accepts both Settings routes against the reconciled12-panel evidence above. Current route total60 Verified/4 In progress. Open route entries are Layout, ContentLayout, Chat and Chat Artifacts. Shared-family, V1/custom branding, full-suite/build and release/deployed-candidate gates remain open.
