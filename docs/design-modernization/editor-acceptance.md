# Editor acceptance consolidation

Current status: Core editor shell and streaming UI evidence is reconciled in the final section below; app-editor routes are accepted in app-editor-review.md. Earlier progress entries are chronological and retain the status at the time. Whole-candidate release gates remain separate.

Date: 2026-09-07

This note consolidates the current acceptance evidence for the live editor route only. It is a record of what has been proven in the current worktree and the surrounding progress notes, not a claim that the broader editor migration is complete.

## What is already proven

- First-open file read failure is handled and surfaces user-visible feedback.
- Retry after the read failure opens the file content successfully.
- The mobile `run-editor-file` event path keeps the editor in the files/tools shell and leaves the UI in the pressed Run state it actually renders.
- Prior lifecycle coverage already exists for mobile pane switching, close behavior, dirty-close handling, and keyboard/file-tab interaction.

## Evidence

### Current browser acceptance run

Scratch script:

- `/tmp/bifrost-design-review/editor-read-run-acceptance.cjs`

Verified runs:

- `light 320 editor first-load failure recovery and run-editor-file path passed`
- `light 1440 editor first-load failure recovery and run-editor-file path passed`
- `dark 320 editor first-load failure recovery and run-editor-file path passed`
- `dark 1440 editor first-load failure recovery and run-editor-file path passed`

Captured screenshots:

- `/tmp/bifrost-design-review/editor-read-failure-light-320.png`
- `/tmp/bifrost-design-review/editor-read-failure-light-1440.png`
- `/tmp/bifrost-design-review/editor-read-failure-dark-320.png`
- `/tmp/bifrost-design-review/editor-read-failure-dark-1440.png`
- `/tmp/bifrost-design-review/editor-read-retry-light-320.png`
- `/tmp/bifrost-design-review/editor-read-retry-light-1440.png`
- `/tmp/bifrost-design-review/editor-read-retry-dark-320.png`
- `/tmp/bifrost-design-review/editor-read-retry-dark-1440.png`
- `/tmp/bifrost-design-review/editor-run-mobile-light-320.png`
- `/tmp/bifrost-design-review/editor-run-mobile-dark-320.png`
- `/tmp/bifrost-design-review/editor-run-desktop-light-1440.png`
- `/tmp/bifrost-design-review/editor-run-desktop-dark-1440.png`

Observed contracts in that run:

- A synthetic `500` on `/api/files/editor/content?path=workflows%2Fdesign_review.py` produced the expected failure toast text.
- The second read returned editor content and the Monaco view rendered the file.
- The mobile `run-editor-file` dispatch left `Files & Tools` pressed and `Run` active. This verifies the shell transition only; it does not claim a real workflow execution.
- No browser page errors were reported in the scripted run.

### Prior lifecycle and shell evidence already recorded in progress

The current `docs/design-modernization/PROGRESS.md` checkpoint already records:

- `EditorLayout.test.tsx`: mobile pane switching and close behavior checks
- `FileTabs.test.tsx`: keyboard selection, close flows, and missing-file conflict handling
- Browser checks for one Monaco instance, reduced motion, and mobile tools/code/output switching

That earlier evidence is still useful because it covers the shell and tab lifecycle around the same route family. It does not replace the current read/retry/run-path run above.

### Earlier editor lifecycle and source-control evidence already reconciled in progress

These checkpoints are already present in `docs/design-modernization/PROGRESS.md` and the matching scratch scripts. They are the supporting proof for the broader live editor UI, separate from the latest read/retry/run acceptance run.

- `editor-tabs-integration-check.cjs` and the `FileTabs`/`EditorLayout` test set prove the real editor shell loads an existing file, keeps tabs at touch size, preserves content through the mobile Files & Tools ↔ Code switch, and avoids document overflow.
- `editor-close-long-check.cjs` proves the unsaved close dialog stays readable on long file lists, keeps the save action disabled while saving, and returns focus to Keep editing when dismissed.
- `editor-unsaved-focus-check.cjs` and `editor-last-tab-focus-matrix.cjs` prove dirty-close focus restoration, discard behavior, last-tab return to Files & Tools on mobile, and desktop return to the sidebar toggle.
- `editor-conflict-close-check.cjs` proves missing-file conflict close goes through the same pending-close guard, keeps the draft when cancelled, preserves pending reorder/new-file entries, and restores focus to the conflict trigger.
- `editor-save-conflict-check.cjs` and `editor-conflict-write-check.cjs` prove save-conflict and conditional-write flows keep the dialog open on failure, allow retry, and only clear conflict state after the synthetic save succeeds.
- `editor-git-status-check.cjs` proves loading and retry for Git status errors, with setup/configure fallback and a real retry action.
- `editor-source-control-check.cjs` and `editor-source-control-recovery-check.cjs` prove source-control records, retry behavior, preserved records after refresh failure, and the reachable commit-history layout.
- `editor-commits-check.cjs`, `editor-change-records-check.cjs`, and `editor-abort-check.cjs` cover the component-level commit/change/abort surfaces that feed the same source-control experience.

Progress-note checkpoints around those runs add the source-level summary:

- `docs/design-modernization/PROGRESS.md:976-982` records the first real file-tab integration proof: `editor-file-tabs-check.cjs` and `editor-tabs-integration-check.cjs`.
- `docs/design-modernization/PROGRESS.md:996` and `docs/design-modernization/PROGRESS.md:1042-1046` record dirty-close, unsaved-focus, and last-tab focus recovery.
- `docs/design-modernization/PROGRESS.md:1089-1108` and `docs/design-modernization/PROGRESS.md:1117-1119` record the commit-history, change-record, source-control and source-control-recovery checkpoints.
- `docs/design-modernization/PROGRESS.md:1169` records Git status loading/failure/retry at the host level.
- `docs/design-modernization/PROGRESS.md:1239-1248` records the save-conflict and conditional-write recovery checkpoints.

These runs are synthetic and browser-driven. They prove the live UI states and recovery paths, not real remote Git/file mutations.

## Current source summary

The source inspected for this acceptance batch already contains the key hooks:

- `client/src/components/editor/FileTabs.tsx` handles read errors, clears loading state, and keeps the file-selection flow intact after a failed open.
- `client/src/components/editor/EditorLayout.tsx` listens for `run-editor-file` and routes the view differently on mobile and desktop.
- `client/src/components/editor/EditorLayout.test.tsx` and `client/src/components/editor/FileTabs.test.tsx` already cover the lifecycle behaviors that were previously unstable.

The source-control and dirty-close progression above also aligns with the current source in the same editor family: FileTabs owns selection, close confirmation, and conflict presentation; EditorLayout owns the shell return path and mobile files/tools routing. No new source change was required for this note.

No source edits were required for the acceptance run in this batch.

## Remaining gap

- Parent screenshot review is still the last step.
- The broader editor migration work remains open outside this bounded acceptance note; this document only records the live read/retry/run evidence and the already-reconciled lifecycle/source-control coverage that is in place.

## Parent Run-panel review and metadata recovery

Parent rejected the old read/run screenshots as complete acceptance: they show a blank Run panel and stale failure toasts. Later populated-form work exists, but current source also lacked workflow metadata read recovery. RunPanel now shows retry feedback on initial/cached failures and a refresh state when an entity-marked workflow has no metadata match. Loading spinner respects reduced motion. useWorkflowsMetadata now exposes isFetching and hasData (its data wrapper exists even before a successful read). RunPanel uses actual query availability to avoid treating a failed initial read as cached data or displaying script execution controls; its execute callback also guards this state. Cached workflow parameters remain available on refresh errors.

Initial browser12477 passed behavior assertions but parent screenshot exposed the misleading cached-data/script fallback, prompting the hook correction. Final editor-run-metadata-check.cjs62044 passes four320/1440 light/dark full-editor cases with custom blue branding and reduced motion: metadata500 retry to a populated five-field workflow form, intercepted execution500 with retained values and explicit retry to Started. Parent inspected final light320 metadata recovery and dark320 populated form. No real workflow runs occurred. Four RunPanel tests86450 cover initial recovery, retained cached controls and execution retry. Full TypeScript8449 and scoped lint72068 pass. Earlier TypeScript66188 failed because the hook lacked isFetching; fixed by exposing query state and removing the redundant RunPanel cast.

Editor route remains In progress. Next: reconcile the entire current editor/app-editor interface against lifecycle/source-control/dependency/publish evidence and review current rendered states; the old blank-run captures cannot serve as acceptance. Global counts remain20/64 routes Verified.

## Current parent shell and streaming review

The core editor is a global shell, not a separate route entry. Current shell47126 passes four custom-purple light/dark320/1440 cases with real file opening, pane switching through normal clicks, focus trapping/return and exact custom brand values. Current streaming82397 passes four metadata failure/recovery, populated form, retained execution submission failure/retry, subscribed application WebSocket logs, terminal completion and final result-preview cases. Final light320 completion/result screenshot inspected by parent. No real execution was started.

Fixed the real stale Workflow badge by subscribing StatusBar to the current file's membership in workflowsByPath; real-store regression67573 and scoped lint/full TypeScript93812 passed. Earlier75149 had a missing result fixture and is superseded by82397 for completion/result acceptance. These current checks supplement the prior lifecycle/source-control evidence above; they do not claim whole-application delivery or increment the route count.
