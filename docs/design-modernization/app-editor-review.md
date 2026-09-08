# App editor acceptance

Status: UI Verified. This document describes the current candidate; historical experiments and superseded captures remain in PROGRESS.md.

## Current design

The app editor uses the shared Bifrost shell, semantic tenant colors and Monaco theme. Desktop keeps a 240px file/package sidebar beside the active workspace. Mobile switches between full-width tools and code/preview; the code editor stays mounted to retain its buffer. Header actions wrap, names truncate, and package content owns its scrolling. Responsive page margins match PageShell padding.

## Verified evidence

| Area | Evidence and limits |
| --- | --- |
| Existing-app lookup | Read-recovery browser79260: four light/dark320/1440 cases recover failed lookup without falsely showing app creation. |
| Code and preview | Browser68635: four light/dark320/1440 cases with custom purple/reduced motion. Real Monaco insertion, Ctrl+S, held save failure, equal retry payload, interactive loaded preview form and return to code. Parent inspected final loaded desktop/mobile captures. File PUTs intercepted. |
| Keyboard callback | AppCodeEditor regression19261 proves the registered command invokes the latest buffer callback without remounting Monaco. |
| Save recovery | Hook/layout tests44065 cover retained failed draft, duplicate saves and edits made during an outstanding save. |
| Packages | Browser60325: four theme/width cases covering failed read, keyboard add retry, retained failed removal, equal retry payload, visible44px removal controls and bounded panel geometry. DependencyPanel tests82549 pass9 cases; combined page/panel84223 passes14. |
| Publish request | Browser25704: four theme/width cases, retained message, pending dismissal guard, failed request and identical retry,44px actions. Page tests44055 pass5. No real publication. |
| Publish completion | Browser66410: four theme/width cases with synthetic WebSocket running/failed/completed notifications; app_published refreshes metadata and removes Publish. Tests93719 pass5. This verifies event handling, not backend build execution. |
| Managed apps | Browser49905: four light/dark320/1440 cases block Monaco edits and keyboard saves, hide Settings/Publish and package mutations, with zero attempted writes. Managed metadata was intercepted. |
| Legacy styles | Browser43913/23479 proves the bundle stylesheet expanded the host rail240→1192px and disabling it restored240px. Compiler layer correction plus bundle schema4 fixes old assets through the existing rebuild path. Browser21692 confirms240px before/after load. |
| V1 components | Browser4230 passes eight published/preview x theme/width cases: dialogs, command search, Select, controlled input, tabs, calendar bounds and reduced motion. Existing body portals and host providers remain in use. |
| Compiler contract | Real compiler/bundler tests3651 pass18, including authored CSS remaining outside generated utility layer. API quality25767 passes Pyright and Ruff. |

## Final acceptance

File switching now loads saved source through an explicit clean-state path, prompts before discarding a draft, preserves the buffer on cancellation and blocks switching while a save is pending. The asynchronous reload callback verifies the file is still current before applying its response. The page keys editor state by application id. Parent reviewed the implementation; the worker's focused layout/hook tests and lint pass, using the real hook rather than a duplicate test implementation.

Browser94559 passes all four theme/width cases for real Monaco clean load, cancellation, explicit discard and zero writes. Parent inspected the mobile dark and desktop light dialogs. Buttons retain the shared44px mobile/40px desktop density contract. Managed-notice browser25334 also passes four cases, with the corrected Alert icon/text layout personally inspected. Parent TypeScript36331 and page/integration lint pass.

The app-editor route is UI accepted. Final application-wide build, full required tests, exact-HEAD delivery gates and cross-route candidate checks remain open. Backend publication execution is owned by its existing job tests, not simulated UI notification evidence.

## Related dependency findings

The original graph/list findings are implemented in current source: responsive DependencyGraphDialog, semantic entity colors and reduced-motion edges, legend outside the canvas, and an extracted RelationshipFilterBanner with stacked mobile actions. These belong to the dependency/entity route acceptance, not the app-editor route. Short-screen graph density remains part of that review.

## Compatibility boundary

Generated inline-app utilities supplement the host design system in `bifrost-app-utilities`, below host components/utilities. Authored app CSS stays unlayered; this is not isolation of arbitrary authored global CSS. Schema4 refreshes old generated assets through the existing manifest path for draft and live inline apps. Standalone V2 asset ownership is unchanged. The synthetic debug fixture's generated assets were rebuilt during verification; its source files and release state were not changed by the intercepted save/publish checks.
