# Applications review

Status: Applications list, runner and preview UI Verified. Overall48 Verified/16 In progress.

## Organization filter and search (2026-09-07)

Current source shared ApplicationListSurface already uses RecordActionsMenu and responsive cards/table. Reconciliation continues for permissions, settings and V1/V2 action differences. Found Global scope selected null was converted to undefined, identical to All. API list_applications explicitly accepts scope=global; parent now passes that value. Nonadmin scope behavior unchanged. Search now has an explicit accessible name and concise mobile placeholder.

10 Applications tests44315 pass; scoped lint/full TypeScript86349 pass; diff check passes. Initial browser12002 failed a fixture selector expecting exact Global instead of its description-inclusive option accessible name. Corrected current matrix89556 running, first mobile case passes global/org/all request scope, results and search/empty state. All fixture API responses intercepted. Goal active.

Applications filter browser89556 passes4 current custom-purple light/dark320/1440 cases: global/org/all request scopes and records, slug search, empty search and no horizontal overflow. Parent inspected dark320 screenshot.10 Apps tests, scoped lint/full TypeScript pass. All processes terminal. SolutionDetail accepted this turn; overall45 Verified/19 In progress. Applications list remains in progress for settings/permission/current shared-action reconciliation. Goal active.

## Action menus and permissions (2026-09-07)

Previous goal turn made verified progress on SolutionDetail acceptance and Apps global-scope correction. Current applications-menu browser11481 passes4 custom-purple light/dark320/1440 cases, including desktop grid/table action parity, managed menu absence, keyboard opener/return focus, Delete cancellation and no horizontal overflow. Parent inspected populated dark320 menu/cards. Fresh no-admin-auth permission matrix89859 passes4 cases: organization apps visible; management menu, scope filter and admin layout toggles absent; search/refresh remain usable.

Original settings stage in11481 stopped because the list now seeds application detail data on hover/focus (detail-route-loaders.ts), so settings opens from cached data instead of the old forced loading fixture. Updated17267 exercises the actual warm menu path for save/delete/role selection; running. Does not count the obsolete loading assertion as a pass. All mutations intercepted; no real app changes. Coverage45 Verified/19 In progress. Goal active.

Current settings batch17267 passes12 actual-page custom-purple light/dark320/1440 cases: retained edit500/retry, deletion cancellation preserves draft then DELETE500/exact retry, and role lookup/selection/search recovery. Parent reviewed narrow dark save/delete/role-search screenshots. All writes synthetic/intercepted. Together with4 menu and4 fresh org-user cases,20 browser cases passed this turn. No source edits this turn; existing10 Apps tests and full TypeScript remain applicable. All processes terminal. Applications remains In progress for current list loading/cached-refresh and V1/V2 navigation reconciliation; count45 Verified/19 In progress. Goal active.

## List recovery and V1 route compatibility (2026-09-07)

Previous goal turn completed current Apps menus, permissions and settings browser reconciliation. Current list batch63568 passes8 custom-purple light/dark320/1440 cases: retained records through failed cached refresh, disabled pending retry and recovery; initial loading500/retry followed by genuine empty result. Parent inspected narrow dark cached failure. Initial-error script retains historical320 screenshot name for both widths, so the final file is desktop; assertions ran both widths.

Router/V1 compatibility8 tests46549 pass. Actual V1 fixture browser37290 passes8 published/preview light/dark320/1440 cases: route loading/reduced-motion spectrum, metadata500/retry, real bundled legacy dialog, command search, input/select and calendar no-overflow. Parent inspected dark320 preview calendar. No API entity mutations. Standalone actual-route fixture matrix started next. Count45 Verified/19 In progress; goal active.

/apps accepted after current list/overlay/permissions/filter recovery reconciliation above. Count46/64 UI Verified,18 In progress. Runner and preview remain separately tracked; current V2 route batch62713 running. Overall migration and release gates remain incomplete.

Standalone actual-route browser62713 passes8 published/preview light/dark320/1440 cases with intercepted mount-v1 bundle: initial entry failure, reload success, correct basename/theme/auth bootstrap and no platform navigation control. Parent inspected dark320 error. Synthetic bundle mounted through actual AppRouter/BundledAppShell rather than a standalone component harness.8 router/V1 tests and24 browser cases passed this turn. All processes terminal; diff check passes. Applications list accepted46/64 UI Verified;18 In progress. Runtime routes still require embedded-user and unavailable publish/deploy state reconciliation before acceptance. Overall goal active.

## Runtime error hierarchy and unavailable live apps (2026-09-07)

Previous goal turn accepted Applications list and verified V1/V2 runtime happy/error paths. BundleLoadFailure now places Reload app before a native Technical details disclosure. Full diagnostic remains available and scrollable, while narrow screens show the recovery action immediately.28 feedback/BundledAppShell/StandaloneV2 tests31937 pass; lint/full TypeScript59509 pass. Updated actual V2 published/preview browser46375 passes8 custom-brand320/1440 light/dark cases, including closed/open diagnostics and reload. Parent inspected dark320 collapsed error.

Unavailable-app browser fixture1782/55854 stayed on Opening application because applicationDetailLoader prepared an unavailable live bundle before AppRouter could render Not Published/Not Deployed. Current source now skips bundle prefetch/preparation for unpublished live routes; draft preview still prepares.9 loader/router tests14857 pass, including unpublished live skip versus preview preparation. Final lint/full TypeScript5426 and actual unavailable/embedded browser58158 running. No real app mutation. Count46 Verified/18 In progress; goal active.

Unavailable browser58158 passes16 fresh-session cases: embed/nonembed × V1/V2 × light/dark ×320/1440. Correct publish/deploy message, embed removes Back/Editor, V2 never offers in-platform editor; no horizontal overflow. Parent inspected dark320 embedded V1 and light320 regular V2 states. Final scoped lint/full TypeScript5426 pass; all processes terminal; diff check passes. Current pass37 tests and24 browser cases. Runtime route acceptance still needs mounted embedded-runtime/theme/navigation behavior reconciliation. Goal active46 Verified/18 In progress.

## Runtime route acceptance (2026-09-07)

Previous goal turn made verified progress on runtime error disclosure and unpublished live-loader guard. Mounted embedded fixture44615 passed8 published cases (V1/V2 light/dark320/1440) with interactive content and no host banner/navigation; V2 basename/theme checked. Its next preview assertion was wrong: App.tsx explicitly restricts preview to platform admins. Corrected preview-only10758 passes8 fresh embedded-user Access Denied cases. Parent inspected dark320 embedded V1. Synthetic modules through actual AppRouter/BundledAppShell; no entity mutations. Prior real V1 component fixture and V2 route recovery proofs retained.

Runner and preview routes accepted. Coverage48/64 UI Verified,16 In progress. Required whole-candidate/family/global/release gates still open. Next Agent fleet. All processes terminal; diff check passes. Goal active.
