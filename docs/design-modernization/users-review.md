# Users UI acceptance

Status: UI Verified for `/users` and `/users/:userId`. Parent acceptance on2026-09-07. Route UI acceptance does not close the global component, backend authorization or release gates.

## List composition and navigation

Desktop retains sortable tables, account identity and overflow actions. Mobile uses labeled cards, wrapping names/email, accessible selection, a native sort control and44px actions. The bulk bar follows the full list rather than a fixed-height container that covered controls. Menu icons and target sizes match the shared action pattern. Pagination remains server-driven.

Current browser94719 passes light/dark320/1440 custom-purple cases: cards versus table, no horizontal overflow, clipboard, selection/unselection, bulk bar bounds, overflow targets, sorting and pagination. Parent inspected mobile and desktop captures. Browser30627 passes initial/cached GET500 recovery while retaining records and selection. Direct-link browser19986 passes loading, GET500, retry to Edit,404 recovery and back navigation in all four cases. Focused route errors use a semantic border without the browser-default outline. Menu/bar tests52957 pass12; Users route tests71638 are included in19 passing permission/page tests.

## Create and edit

Create/Edit use bounded scrolling bodies and fixed footer actions, synchronous submission guards, pending inert fields and dismissal protection. Failures retain drafts and focus an inline error. Organization and role lookups have reusable UserLookupNotice loading/error/retry surfaces; access saves wait for successful data.

Create remembers successful user creation and completed role assignments. Retrying a partial failure sends only unfinished role operations, preserving the original registration link. Edit hydrates role assignments before saving and advances the completed role baseline as each request succeeds. Both use accessible44px role-removal controls with correctly sized, wrapping badge containers.

Browser87421 covers create request failure/draft retry;69537 covers creation plus role sequence r1/r2/r2 with only one user POST. Browser8499 covers actual detail role-read recovery and partial removal retry;41357 verifies final role chip hit targets. Browser76230 covers create organization/catalog errors,14426 covers edit organization errors. Each matrix uses light/dark320/1440 custom branding unless explicitly noted as a targeted320 follow-up. Parent inspected mobile errors, selections and footer composition. Create/Edit combined tests72120 pass15; later self-edit regression is recorded below.

## Registration links

UserAccountActionDialog is separate from RegistrationLinkDialog. Registration links retain copy access after a send failure; sending is guarded and cannot be dismissed while pending. Server detail and one recovery instruction remain inline. Retry sends the original URL; clipboard uses its absolute form. Existing-user generation says “Registration link ready”; creation retains “User Created”. State resets per registration URL.

Final registration browser29791 passes all four theme/width cases: pending protection, focused server error, copy and equal-payload retry. Browser54228 verifies the create-user partial-role flow still reaches its original link. Parent inspected dark320. Registration tests39104 pass6; Users tests3943 pass13 including callback rejection/retry. Initial fixture expected an absolute send payload; corrected to preserve the server response, without changing the API behavior.

## Bulk and single-account actions

Bulk move/replace require loaded catalogs, expose read retry and preserve intentional empty-role clearing only after lookup success. Shared dialog framing disables Cancel/Close, blocks Escape and makes fields inert while requests run. Inline submit errors focus and preserve choices. Partial results identify succeeded/failed counts and affected records.

Browser51054 covers role/status partial outcomes and pending guards. Browser20811 adds lookup failures/retry. Browser60978 verifies move lookup recovery, held500 failure, retained destination and identical retry. All four theme/width cases pass; parent inspected dark320 lookup, mutation and result states. Ten bulk tests69003 pass.

Reusable UserAccountActionDialog replaces automatically closing Disable/Delete actions. It guards duplicate requests and dismissal, shows focused server errors, retains retry, wraps long names and uses44px controls. Stable page-control focus restoration handles removed rows. Final browser54978 passes all four cases with explicit focus assertions; parent inspected clean dark320 Delete. Two held-operation unit cases79778 and13 Users tests34207 pass. Full TypeScript45563 passes.

## Permissions and final evidence

Both routes remain guarded by `requirePlatformAdmin` in App.tsx. Final denied browser23079 passes light/dark320/1440 on both routes with no Users data requests; parent inspected dark320. These are synthetic frontend permission checks, not proof of backend authorization. Fixture contexts do not save or overwrite the parent login. Initial permission fixtures omitted the shell profile/auth responses; they were corrected to provide valid isolated data.

Final self-account browser84891 passes all four theme/width cases: disabled selection/menu actions and access fields, no role selector, editable display name and name-only PATCH. It exposed a legacy/null-organization validation issue: name-only self edits now bypass organization validation because that field cannot be changed. Nine Edit tests55574 pass including this regression.

Full Users component/page suite37224 passes85 before the final self-only fix. Source lint/full TypeScript35588 passes for that change. Parent inspected light320 self editing. Earlier23254 passed mobile but used a button selector for the desktop row; corrected before final84891. Unreferenced UserRolesDialog remains in the independent component inventory; its presence is not silently treated as route evidence. Global full-suite/build, all remaining routes/components, V1/custom branding compatibility, final artifact review and delivery gates remain open.

Evidence scripts and captures are in `/tmp/bifrost-design-review/`; session-specific test outcomes and rejected intermediate candidates are retained in PROGRESS.md. All browser writes were intercepted synthetic fixtures; no real users, permissions or invitations were changed.
