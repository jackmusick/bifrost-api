# Entity, agent activity, Files, and report follow-up

User-approved direction, 2026-09-11:

- Entity Management becomes a resource comparison workspace. Related resources are a tree list, with explicit uses/used-by relationships from the existing dependency endpoint. Bulk organization/access changes are reviewed before applying. The separate diagram is no longer required.
- Agent activity retains the top-level asked/did/answered summary and metadata. A compact expandable hierarchy selects a call for a right-hand inspector (refined after the initial below-list implementation). Selecting a child must not change or widen the main summary. Main-agent usage stays accessible independently of activity selection; descendant usage is not implied by main-run totals.
- Files opens on usable share entries, reserves the main space for browsing, and opens preview/access in a drawer on demand at desktop and mobile sizes.
- Report filters should take less vertical space. Sub-cent AI cost must remain visible rather than rounding to zero.

## Report constructor error investigation

The reported `import_decimal.default is not a constructor` references Recharts' optimized dev dependency, which uses decimal.js-light through Vite/Rolldown interop. The currently served bundle executes successfully in fresh Chromium sessions through both the internal debug client and the public NetBird URL. Both real and demo report charts rendered. No dependency/config change was made based on an unconfirmed cache hypothesis. Reproduction in the user's existing tab remains requested; this is not recorded as a proven source fix.

## Focused evidence

- Entity role data: workflow and agent list responses now include real assigned `role_ids`. Workflow assignments use a batch query; delegated agent summaries eager-load roles. Generated client types were refreshed.
- Backend tests: the two list-role regression tests, workflow role replacement test, and CLI contract fingerprint checks passed (5 tests). DTO parity passed (62 tests). `./test.sh quality api` passed.
- Files/report/Entity component checks passed: 17 files / 68 tests. Agent timeline and run-page checks passed: 2 files / 49 tests. These include recursive expansion, individual collapse after Expand all, live updates to selected nested output, and changing selection after restoring navigation.
- Files and operational report browser journeys passed in `./test.sh client e2e e2e/entity-management-acceptance.admin.spec.ts e2e/agents-detail-runs.admin.spec.ts e2e/operational-reports-acceptance.admin.spec.ts e2e/files-management-acceptance.admin.spec.ts`. That initial combined run exposed Entity test selectors and agent interaction issues; it was not an all-green run.
- Agent browser verification: `./test.sh client e2e e2e/agents-detail-runs.admin.spec.ts` passed (8 tests including setup), covering nested selection, grandchild navigation/back, drawer activity, preserved context, and mobile layout.
- Entity's corrected browser journey passed in the targeted Entity/agent run: two selected apps are assigned, reassigned, and returned to Global, while an unselected app stays unchanged. Its acceptance-ledger title was updated with the journey.
- Rendered Entity tree/edit drawer, Files browsing/access, and selected agent details at desktop and 390-pixel widths. ROI and Usage demo charts rendered at both widths without page errors or document horizontal overflow.
- Client type checking passed. Full client lint passed with the existing `seed-review-pack.ts` console warning; final changed-agent lint passed without warnings. Production client builds ran as part of the browser-test harness.
- Broad lint exposed a Playwright fixture callback named `use`, incorrectly treated as React's hook inside try/finally. Renamed it to `provideSolution`; fixture behavior and cleanup remain identical.

This document is a scoped review record, not evidence that the final candidate has passed pre-PR or been merged.

## Inspector and inline-relationship refinement — 2026-09-11

- History's Agents view now uses the shared pagination footer even for a single nonempty page. Search, agent, organization (admin), status, and date-range controls use existing server filters; pagination changes the data rows while retaining the toolbar/footer. Mobile filters use the existing disclosure pattern.
- Agent activity keeps asked/did/answered and main-run usage independent of selected calls. A compact Name/Status/Duration hierarchy replaces the separate Type column; type remains in the icon's accessible description. Selected calls open in a nonmodal right inspector on desktop and a full-width modal on mobile. Closing returns focus to the originating row without moving the page.
- Workflow identifiers no longer collapse to “Completed an action.” The inspector retrieves the linked execution's workflow display name and result when available, while retaining the recorded input/result fallback and execution link. Final responses render full Markdown, including headings and tables, without an empty Task section.
- Advanced changes activity-local payload/trace visibility. Metadata has its own disclosure and main-run usage remains available independently. The main header uses the agent name; the complete original request remains in the summary.
- Navigation restoration is consumed once. Returning from a child restores selection and expansion, but later closing and collapsing the tree does not reopen the inspector.
- Entity Management removes the nested toolbar card and separate relationship-focus banner/action. Expanding a resource loads its related resources inline in the existing list. Rows are denser, with resource type beside the title. Bulk selection uses actual visible composite keys, including related descendants, and preserves selections outside the current view. Empty relationship results and loading failures have inline feedback and retry.
- Desktop (1440px) and mobile (390px) screenshots were reviewed for History, workflow/response inspectors, and inline Entity relationships. The debug browser batch reported no page errors or document horizontal overflow.

Verification:

- Focused Vitest: 9 files / 81 tests passed (Timeline, activity transformation, full run page, History agents, Entity tree/assignment/toolbar/types/page). Timeline's final state-marker correction then passed its 18 tests again.
- `./test.sh client e2e e2e/agents-detail-runs.admin.spec.ts e2e/entity-management-acceptance.admin.spec.ts e2e/history-pickers.admin.spec.ts`: 10 passed including setup, zero retries. Earlier attempts exposed the inspector-covered Advanced test action and the real repeated-restoration bug; both were corrected before this passing run.
- Client type checking passed. Full lint identified a ref-read-during-render error in the restoration marker; using React state corrected it and the affected files pass lint. The existing review-seed console warning remains.
- The browser run includes a production client build. The final ref-to-state lint correction was verified with focused component tests and type checking.

This remains an unmerged debug-stack iteration; no full pre-PR gate is claimed.
