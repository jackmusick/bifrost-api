# Files review

Status: UI Verified for /files. Coverage41 Verified/23 In progress. Global release gates remain open.

Prior evidence is preserved in PROGRESS.md under folder browsing, share navigation, preview/access, uploads/new shares, access testing, deletion and breadcrumb/solution-file checkpoints. Those tests and captures cover the feature behavior; this acceptance pass reconciles the current parent composition and any remaining gaps.

## Current composition and actions (2026-09-07)

Previous goal turn made progress by accepting Tables. Current Files source still used the old page heading and enabled a three-column explorer at1024 with18rem/24rem fixed side panes. Browser96695 passed320 then failed ordinary pointer interaction at1024: the grid intercepted a folder click. Changed Files to shared ListPageHeader (Prompt), and moved explorer side panes into existing Shares/Preview/Access drawers below1440. At1440 and above the panes are16rem/20rem, leaving more room for filenames. Header wrapping uses the same breakpoint.

FolderListing desktop previously exposed Preview/Download/Delete icon buttons and no visible folder actions, whereas mobile had an overflow. New reusable FileEntryActions serves both card and table records through RecordActionsMenu, preserving writable/read-only choices, pending download state, callback paths and desktop context menus. Folder actions are now visibly discoverable on desktop. Test download interaction updated to the menu; read-only menu regression now runs in both layouts.

Initial34 tests24832 and lint/full TypeScript79559 pass for heading/panes. Final35 tests72405 and scoped lint/full TypeScript29244 pass after shared action extraction. Browser55744 first failed a bad width assertion against the naturally-sized notes.txt button; corrected to measure the name cell/container. Layout97197 passes8 custom-purple light/dark320/1024/1280/1440 deep-path, keyboard navigation, useful filename width, Prompt font and responsive inverse cases. Parent inspected dark1024 and identified remaining toolbar crowding; adjusted its breakpoint. Final layout92584 is running at this entry.

Action/read-only browser5883 passes12 light/dark320/1024/1440 share selection, initial read failure/retry, card/table inverse, long paths, folder/file overflow choices, download500/retry with actual download filename and keyboard folder navigation. All file structures/downloads synthetic intercepted. No actual file or policy mutation.

Remaining: final screenshot review after toolbar wrapping; consolidate current preview/access/policy/share/upload/delete fixtures against changed menu affordances, scope/solution/non-admin modes, and complete route acceptance. Core code editor is a separate shell and remains under its own acceptance document. No blocker; goal active.

Final layout92584 passes all8 cases after toolbar breakpoint change. Parent inspected dark1024 and light1440: unobstructed listing, distinct toolbar rows and useful central column. All parent handles terminal. Route remains In progress; no additional route accepted from this composition-only pass.

## Files preview/access and mutation recovery (2026-09-07)

Previous turn was progress: layout and reusable file actions improved. Current files-access-current.cjs plus files-delete-current.cjs76427 pass14 browser cases. Preview/access covers light/dark320/1024/1440, real Files route with synthetic file/policy data: preview500 retry,6000-character truncation, download500/retry/filename, keyboard Preview/Access tabs below1440, separate desktop panes, populated long rules and error retry. Delete covers file/policy light/dark320x480/1440 with current overflow menus: cancel/no mutation, pending/Escape protection, identical retry payload, removal and explorer return focus. Parent inspected dark1024 Access drawer.

NewShareDialog now focuses and scrolls its inline error. files-share-current.cjs10400 passes four light/dark320x480/1440 validation/reserved-name/pending/focused-error/retry/draft-reset cases. Parent inspected dark320 short dialog; actions remain visible.

Full Files suite98586 exposed a stale lg:flex-1 class assertion after the prior toolbar breakpoint change. Updated assertion; final40346 passes all93 tests across14 files. Scoped lint passes; full TypeScript21864 running at this entry. No real file/share/policy mutations. Current auth contexts closed serially.

Important evidence reconciliation: old file-preview-check.cjs now tests Chat artifacts, and file-upload-check.cjs now tests form uploads; filenames were reused. Do not treat those scripts as current Files proof. Files preview is covered by files-access-current.cjs; reconstruct the Files upload transport fixture from useFileUpload and SDK before acceptance. Remaining route gaps: upload exact retry sequence, current policy editor/rules, scope/solution/non-admin matrix and consolidation. Coverage40 Verified/24 In progress. Goal active, no blocker.

TypeScript21864 exposed unsupported testing-library exact:true in the prior FolderListing test edit. First correction used the wrong working-directory prefix and made no edit;45973 began before the corrected file and returned the same diagnostic. Source locator is now corrected; final54575 running. Files upload transport fixture rebuilt as files-upload-current.cjs, intercepting structure, signed URL, PUT and complete-upload. Initial80312 passed header then failed an obsolete folder control label. Corrected fixture41300 running across header/folder light/dark320/1440, asserting exact a,b,b,c retry sequence and global/gallery destination. No actual uploads.

Final full TypeScript54575 passes. Rebuilt Files upload41300 passes all8 cases; parent inspected dark320 folder error with retained first file and visible retry. All parent handles terminal. Files remains In progress for policy/rules and scope/solution/non-admin acceptance; overall40/64 verified.

## File policy/scope acceptance checks (2026-09-07)

Previous goal turn made progress. FilePolicyEditor now uses synchronous mutation protection across save/delete plus focused/scrolled server/structured validation errors. Sixteen FilePolicyEditor/PolicyEditorModal tests82456 and scoped lint/full TypeScript15969 pass. First browser88825 passes4 policy load/save-retry cases and6 solution-scoped navigation/read-only cases320/1024/1440 light/dark. Updated policy/reference68682 passes8 light/dark320/1440 cases including focused error and reachable Save, real Monaco, identical payload retry, reference JSON toggle, overflow and keyboard focus restoration. Parent inspected dark320 policy error. Permission22172 passes4 fresh synthetic non-admin route-denial cases with no file data reads. Scope90573 passes4 current global/organization explorer cases: late Alpha folder response cannot replace selected Beta file list. No real file/policy mutations.

Nested PolicyRulesManager source audit found remaining shared-family inconsistencies: mobile cards use separate Edit/Delete buttons, desktop uses icon pair; needs shared overflow action component. Loading/saving/deleting spinners omit motion-reduce. Form pending state currently does not disable all editable fields. No route accepted from this partial check. Files remains In progress;40 Verified/24 In progress. This shared rules manager is also consumed by Tables, so its completion belongs in the independent component-family ledger and must be reconciled before whole migration acceptance.

Next: render nested rules manager from actual Files Manage rules entry, align action menus and pending/recovery behavior, check its create/edit/delete and overlay stack; then consolidate Files route evidence. All parent handles terminal; diff check passes. Goal active, no blocker.

## Shared policy-rules modernization (2026-09-07)

Previous goal turn made progress. New PolicyRuleActions is reused by PolicyRuleSurface and desktop PolicyRulesManager rows, using RecordActionsMenu and preserving built-in read-only behavior. Pending save disables every field and dismissal, uses synchronous duplicate protection, validates JSON object shape and focuses/scolls retained save errors with room for Save. All manager loading/save/delete spinners respect reduced motion. Delete now uses a controlled Button rather than automatic-closing AlertDialogAction, guards pending Escape/Cancel/duplicates, and retains a focused inline error for retry. Existing409 in-use flow remains.

Updated tests use overflow menus instead of obsolete direct edit/delete buttons. Initial15 tests60379 and scoped lint/full TypeScript87035 pass after edit/menu changes; final15 tests82873 pass after delete recovery. Lint11619 found unused AlertDialogAction after replacement; removed. Final lint/full TypeScript71199 running.

Actual Files nested-manager browser41053 passes4 light/dark320/1440 edit cases: built-in menu absent, current overflow, locked fields/pending Escape, focused error, Save in viewport, identical payload retry returns to manager. Delete92378 passes4 same-size/theme cases: current menu, pending cancel/Escape, focused server error and retry returning to manager. Parent inspected dark320 edit and delete failure screenshots. All requests synthetic intercepted; no real rules changed. Browser delete log inherits edit wording but checks DELETE requests.

Inventory134 page modules/362 feature components/53 primitives. Overall40 Verified/24 In progress. Remaining nested-rule acceptance: create/JSON validation,409 usage conflict, return-focus and late usage-read response isolation. Files stays In progress until these shared-manager states are reconciled. No blocker, goal active.

Final lint/full TypeScript71199 passes. Parent dark320 delete screenshot exposed legacy destructive color overrides reducing label contrast. Removed those classes in favor of the canonical destructive Button variant and44px height. Final delete browser28030 running; no logic change.

Final delete browser28030 passes all4 cases. Parent inspected corrected dark320 screenshot with readable destructive label. All parent handles terminal; diff check passes.

## Files final interaction checks (2026-09-07)

Previous turn was progress. PolicyRulesManager now restores focus to New rule after form/delete/in-use overlays, bounds the in-use dialog90dvh with long-path wrapping, and ignores usage responses from earlier edit sessions via revision. Initial15 tests63143 and scoped lint/full TypeScript65164 pass. Added meaningful late-response regression; final16 tests74675 pass. Final lint/full TypeScript55379 running.

Browser87197 passes8 nested create/in-use light/dark320/1440 cases through actual Files: invalid/non-object JSON makes no requests, held POST pending protection, retained server-error draft/retry and return focus; DELETE409 exposes usage paths, preserves record and restores focus after Close. Parent inspected dark320 creation error and in-use screenshots. All mutations intercepted. These complete the remaining Files nested-manager interaction matrix together with the preceding edit/delete/read/reference/permission/scope/solution/upload checks. Final route acceptance awaits authoritative TypeScript55379 result. No blocker; goal active.

Next page family: Knowledge. Existing Knowledge.tsx has canonical header/menu/mobile layout and prior HTTP delete recovery. Existing knowledge-flow/mobile/drawer/recovery-check.cjs and config-knowledge-verify.cjs; inspect script contents before reuse because earlier generic filenames were overwritten. Route still In progress. Preserve drawer/edit/scope/filter/pagination behavior and review rendered composition before accepting.

Final full TypeScript55379 passes. Files route UI acceptance consolidated from the complete evidence above: /files now Verified. Coverage41 Verified/23 In progress. All parent handles terminal; no blocker. Next Knowledge.

## Contained Files workspace redesign (2026-09-11)

Replaced the disconnected browser/policy panes with one workspace. Shares and
folders form a compact, lazy-loaded left directory; files use a searchable native
list with a primary open button and sibling overflow menu. Full-width selection
persists on hover and does not color descendants. Branch indentation belongs to
contents, so selection and hover align with the workspace edges.

The new reusable `FilesInspector` attaches to the right on desktop. At intermediate
widths share navigation collapses; on phones inspection replaces only the directory
area. Escape/close restores focus, background directory controls are inert on
phones, and transitions respect reduced motion. Preview and Access remain explicit
tabs. Folder Details opens access directly. Scope, breadcrumbs, upload, and policy
search each have one consistent place. Access-policy editing/testing, download,
delete recovery, and embedded solution read-only behavior remain supported.

The folder/share Upload action now commits its destination and opens the native
file chooser; previously it only navigated there. File extension icons do not imply
metadata the API does not supply (no invented size/date columns).

Review data: the debug Global share `ui-review-files` contains synthetic Markdown,
JSON, CSV, and nested folders. Reviewed live at 1440, 1100, and 390 pixels, including
preview, folder access, policy listing, and workspace containment. A first confirmation
attempt met a cold debug application load before the login form appeared; a separate
probe confirmed login readiness, then the review completed with no page errors.

Verification:
- `./test.sh client unit -- src/components/files`: 16 files, 101 tests passed.
- `./test.sh client unit -- FilesExplorer.test.tsx FilesInspector.test.tsx PoliciesView.test.tsx`: 23 tests passed after interaction refinements.
- `./test.sh client e2e e2e/files-explorer.admin.spec.ts e2e/files-management-acceptance.admin.spec.ts e2e/solution-files-link.admin.spec.ts`: 5 passed including setup; upload/preview/access, mobile navigation, download/delete, and embedded solution files.
- A targeted Files Explorer E2E confirmation covers the corrected menu upload and mobile focus restoration (result recorded below).
- TypeScript and lint checked for this batch; lint has an existing console warning in `e2e/support/seed-review-pack.ts`.
- Impeccable static detector returned no findings for the changed Files surfaces.

This is scoped Files verification. The full platform/backend suites and pre-PR gate
were not rerun for this design iteration. No merge or production deployment.

Final confirmation: `./test.sh client e2e e2e/files-explorer.admin.spec.ts`
passed all 3 tests including setup. The menu upload opens the native chooser and
uploads to the selected share; the inspector remains inside the workspace at
1440/1100/390, and closing it on mobile returns focus to the file. Final client
`npm run tsc` passed; `npm run lint` passed with only the existing seed-review-pack
console warning noted above.

## Access workflow and alignment follow-up (2026-09-11)

The scope control and share tree now share a 17rem column; Shares and breadcrumbs
share a 56px desktop toolbar height. At wide desktop widths the tree remains
visible with the expanded access tools. Smaller workspaces prioritize inspection.

Access Policies is a directory of policy attachments, not a second shares list.
Selecting a folder preserves the active tab and filters attachments to that folder
and descendants, with path-boundary matching. Explanatory empty states point to
Folder Details for inherited access. Explicit Upload still switches to Files and
opens the chooser in the selected destination.

Effective Access explains the nearest governing policy, resolves referenced rule
names/descriptions/actions, and opens the source policy. User-specific decisions
remain in Test Access; a policy summary does not imply that every user is allowed.
The embedded test panel reports read/write/delete/list outcomes and uses the
organization display name rather than a scope UUID.

Manage Policy and Test Access now run inside the attached inspector, with Back to
Access preserving the previous tab. Policy editing starts with a readable rule list:
add shared rules/templates, remove rules, or switch to Advanced for full YAML/JSON.
Unknown/custom conditions remain in the document. Unresolved shared rules are not
presented as allowing everyone. Source context explains when changes affect an
inherited policy and other paths. Exact source/list selections edit that exact
attachment. Pending policy mutations block inspector dismissal and navigation.

Compatibility wrappers remain for existing dialog consumers. Advanced Shared Rules
still uses the shared rule-definition manager and its existing internal dialogs;
that is distinct from editing this file/folder's policy attachment.

Verification:
- All Files component tests: `./test.sh client unit -- src/components/files` — 109 tests across 16 files passed.
- Final affected components after mobile/copy/mode-guard corrections: `./test.sh client unit -- TestAccessModal.test.tsx FilePolicyEditor.test.tsx FilesExplorer.test.tsx` — 36 passed.
- Browser review on debug data checked aligned headers, persistent policy navigation, resolved shared rules, four access decisions, embedded editing, and mobile containment. A narrow header discovered in review was corrected by separating descriptive copy from fixed-width actions.
- `npm run tsc` and `npm run lint` passed; lint retains the pre-existing console warning in `e2e/support/seed-review-pack.ts`.
- Static design detector reported no findings in the changed Files components.
- Live-service E2E results recorded below. Full platform/backend suites and the pre-PR gate were not run for this scoped UI iteration.

Final E2E: `./test.sh client e2e e2e/files-explorer.admin.spec.ts e2e/files-management-acceptance.admin.spec.ts e2e/solution-files-link.admin.spec.ts`
passed all 5 tests including setup. The Files journey now checks in-workspace
Test Access decisions, returning to the Access tab, persistent policy mode while
navigating, and opening the embedded policy editor. Follow-up copy/mobile layout
checks ran against the live debug build, with targeted component tests above.
Folder New Policy explicitly targets the selected folder with a trailing path
boundary, not its parent; `./test.sh client unit -- FilesExplorer.test.tsx` covers
that target selection.

## Policy inspector hierarchy refinement (2026-09-11)

Moved Back to Access to a left-aligned navigation row in both access tools; aligned
plain, accent-colored title icons with their titles. Replaced the Rules/Advanced
button pair with a labeled Advanced switch. Add Template and Add Shared Rule now
share an equal-width row at desktop and phone widths. Rule actions and shared-rule
markers have accent color; supporting descriptions remain muted.

Manage Shared Rules now identifies a reusable rule library and explains how to
add its rules to the current policy. Removed implementation commentary about
confirmation dialogs. The shared-rule picker refreshes when opened, including
when the library was initially empty, so newly created rules can be selected.
Advanced editing and existing save/delete/retry behavior remain available.

Checked rendered desktop/mobile alignment, equal-row selectors, Advanced switching,
policy/source navigation, and access tests against debug fixtures. Targeted tests:
`./test.sh client unit -- FilePolicyEditor.test.tsx PolicyEditorModal.test.tsx TestAccessModal.test.tsx`.
This polish used scoped component and live-browser checks; the full E2E suite was
not rerun. TypeScript and scoped lint checked separately.

### Inherited access and shared library

The Files inspector edits the selected file/folder explicitly. If it has no local
policy, inherited access is a separate read-only summary with a source link.
Opening that link deliberately edits the source; saving a local policy replaces
the inherited policy for that path without changing its ancestor. Root policies
are never described as inheriting themselves. Legacy modal callers retain their
existing governing-policy selection behavior.

The Shared Rule Library has an independent blue background/border, a real heading,
and a separate icon close control. Both add pickers use the shared searchable
Combobox with readable labels and descriptions, preserving exact reference names.
Shared rules refresh on interaction and library visibility changes.

Validation: 54 scoped component tests passed across the editor, policy panel,
access tester, access summary, and Files workspace. Desktop (1440px) and mobile
(390px) browser checks exercised inherited/source navigation, library controls,
search filtering, and overflow. No live policy was saved during visual review.
TypeScript and scoped ESLint passed. The full E2E suite was not rerun for this pass.

### Direct Access and Test tabs

Access now opens the selected path's policy editor directly. Testing lives in a
sibling Test tab, including policy/test tools opened from context actions. Source
policy navigation still returns to the original file's Access tab. Inherited
permissions use the label “Read-Only”; solution-managed files retain their
read-only access summary. Mutation-in-progress guards also cover tab navigation.

Verification: 27 scoped tests in FilesExplorer.test.tsx and
PolicyEditorModal.test.tsx; the Files explorer desktop/mobile Playwright spec;
live debug desktop/mobile navigation and visual inspection; TypeScript and scoped
ESLint. Full test suites and the pre-PR gate were not rerun for this refinement.
