# Workflows UI acceptance

Status: UI Verified for `/workflows`. Parent acceptance on 2026-09-07. Solution Detail, the core editor, execution routes and release-wide gates remain separate scopes.

## List composition and actions

WorkflowListSurface uses native history links for names and View history, shared overflow menus for secondary actions, and type-specific primary execution labels. Permission and solution-management guards remain. Parent rejected the initial cramped four-column table; desktop now groups identity, type/scope/status and full description beside a dedicated action column. Mobile uses cards. Existing resize evidence covers desktop table preference surviving mobile card layout and returning to desktop.

Browser72739 passed custom-purple light/dark320/1440x700 history link destinations, endpoint/missing-file actions, Escape focus return, full descriptions and overflow checks. Parent reviewed desktop table and mobile menu. Earlier workflows-acceptance-check.cjs covers populated/search/type/category states and computed custom-brand comparison. Current list/page tests95684 pass12 tests, including duplicate-name editor source selection by workflow ID.

## Filters and reads

The toolbar counts all9 filter dimensions and clears them together. Filtered emptiness does not suggest configuring a new workflow. Refresh and read retries prevent duplicate requests; cached records survive failed refreshes. Browser2458 covers initial/cached failures, pending retries, type/category emptiness and clear-all across four theme/width cases.

Sidebar names wrap, selected filters expose aria-pressed, control radii use design tokens and touch actions are44px. Failed usage queries have scoped retry, retain cached entities and show unavailable counts rather than false zero counts.14 tests26749 and four browser63106 cases cover combined endpoint/orphaned filters, mutually exclusive form/app/agent query parameters, counts, clear-all and usage error recovery. Parent inspected dark320 names, selected states and final error/count correction2520.

Browser63244 covers Global/organization scope query parameters, clear-all, failed editor reads preserving the list and primary execution destinations at320/1440 in both themes. Organization scope has an accessible name and execution URLs encode names.

## Settings and endpoint recovery

WorkflowEditDialog retains drafts through save failures, focuses inline recovery, protects dismissal and locks tab contents during saving. It uses90dvh bounds and a fixed footer. Six dialog tests10445 and final four-case browser38241 cover held save failure, retained draft, equal-payload retry and focus. Parent removed the browser-default error focus outline after reviewing mobile.

Endpoint controls have associated labels,44px method controls and aria-pressed. The mode trigger shows a readable selected label while descriptions remain in the menu. Key reads distinguish loading/error/empty states and prevent generation during unresolved reads. Four browser70775 cases cover key-read retry and method selection retained through settings save failure/retry.

Key generation has a synchronous operation guard, pending dismissal/save protection and visible status. A successful revoke followed by failed creation clears the old key and explains how to restore API access; retry only creates. The server's required revoke-then-create contract is preserved. Mutation notifications are suppressed only in this dialog to avoid duplicate toasts covering the mobile footer. Eight dialog tests53136 and four browser68705 cases verify partial-failure recovery, focus, old-key removal and create-only retry. Parent reviewed the corrected dark320 footer/error presentation.

## Missing-file recovery and editor entry

OrphanedWorkflowDialog keeps metadata/dependencies in a scrolling body with a visible Close footer. Pending replace/recreate/deactivate actions prevent duplicate calls and dismissal. Focused error retries repeat the failed action and preserve replacement selection. Dependency reads have explicit loading/error/retry. Replacement path/function values wrap within the picker rather than leaking rich option content.

Three dialog tests2563, four recreate browser37319 cases and eight replacement/deactivation browser81500 cases cover long dependencies, read retry, pending guards, focus, equal-payload retries and320/1440 light/dark layouts. Parent reviewed corrected replacement and dependency states.

Editor entry selects metadata by workflow ID when available, avoiding duplicate-name source mismatches. Four browser35679 cases recover from a failed file read to the requested file tab and Monaco content. Parent reviewed light320 editor entry. Core editor editing/save/debug behavior has its own acceptance scope.

## Validation boundaries

Scoped lint checks pass for changed files; full combined TypeScript13504 passes after Organizations source settled. Diff checks pass. Browser records, API failures, key mutations and editor file contents were intercepted synthetic fixtures; no real keys, workflows or source files were changed or executed by these browser checks. Prior authenticated layout access and platform-admin route guards remain in App.tsx. Route UI acceptance does not claim full132-page, shared-family, backend authorization or release acceptance.
