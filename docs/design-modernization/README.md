# Bifrost interface modernization

Latest hands-on review: [September 8 corrections](review-corrections-2026-09-08.md), including shell persistence, table interactions, mapping density, graph framing, and branding reset persistence.

This directory tracks the migration of the platform interface to the Bifrost design system. All 64 route entries and 578 tracked modules/components have passed UI review; shared-contract reconciliation is complete. Final delivery checks remain in progress. See [progress](PROGRESS.md) for the current checkpoint and [coverage](coverage.md) for the remaining work. The [review queue](REVIEW-QUEUE.md) separates implementation batches, existing work awaiting acceptance, and final delivery gates.

The [page scrolling contract and route audit](scrolling.md) define desktop bounded content, compact tables, mobile flow, and verification limits.

## Design authority

[DESIGN.md](../../DESIGN.md) describes the product contract. The source design system is the sibling `design-system` repository, with the initial token snapshot taken from commit `11da72e`. The platform vendors those tokens in `client/src/styles/bifrost-tokens.css` and maps them to existing component variables in `client/src/index.css`.

The platform retains the established component APIs while changing their presentation. Existing imports, refs, slots, compound controls, dialogs and keyboard behavior remain part of the compatibility contract. The catalog is a visual and composition reference; its sample components are not replacements for richer platform APIs.

## Applying the system

| Purpose | Use |
| --- | --- |
| Interface text and controls | Inter, through `font-sans` |
| Page titles and identity | Prompt, through `font-display` |
| Code, paths and technical values | JetBrains Mono, through `font-mono` |
| Primary actions and selected navigation | `primary` and `primary-foreground` |
| Execution activity | `--bf-activity-gradient` |
| Persistent spectrum seam | `--bf-bridge` or `--bf-bridge-vertical` |
| Outcome or severity | Semantic success, warning, danger and info tokens |
| Controls, surfaces and feature overlays | `--bf-radius-control`, `--bf-radius-surface`, `--bf-radius-feature` |

Fonts are hosted locally under `client/public/fonts`; their licenses and source information live there. Adding a font request to an external service is unnecessary.

Use the shared `ListPageHeader` and `ListToolbar` for list-page composition. Keep task-specific controls in each page and preserve permission checks, query behavior and dialogs. A shared header does not complete a page review: rows, empty states, filters, bulk operations and small-screen overflow still need examination.

Use existing UI primitives for menus, dialogs and other focus-managed overlays. Give icon controls accessible names and make actions reachable without hover. Constrain scrolling only where a workspace needs it; ordinary forms should grow with their content on phones.

## Branding and motion

`brand-palette.ts` derives the default or tenant palette and checks action contrast. `branding.ts` owns the generated theme stylesheet. Consumers should use variables rather than hard-coded teal, spectrum stops or utility overrides. Custom brands receive a tonal activity gradient; outcome colors remain semantic.

Motion should explain state changes. Respect reduced motion for activity, navigation, disclosure and editor effects. A running indicator must stop when the underlying operation stops. Keep the existing execution and platform-job transports as the source of truth.

Monaco themes are registered through `monaco-theme.ts`; they follow theme and tenant changes without replacing the editor engine. Responsive workspace layouts must keep a single mounted code editor and preserve its buffer while panels are hidden.

## V1 apps

See [V1 compatibility](v1-compatibility.md) before changing included exports. Legacy inline apps inherit host styling, so primitives require consumer checks as well as platform checks. The [fixture guide](fixtures.md) describes the real debug app used to exercise included components.

## Review and verification

`inventory.json` is the editable coverage ledger. Run `python3 scripts/design-inventory.py` to regenerate the Markdown view and discover newly added source files; existing evidence fields are retained. Record actual route, theme, width, state and interaction evidence. Do not mark a route complete because its parent layout changed or a unit test passed.

The isolated worktree preview is available over NetBird at:

[Open the modernization preview](http://bifrost-debug-design-system-modernization-0-38.netbird.cloud)

Use the repository's `./debug.sh` and `./test.sh` workflows. Focused tests support each implementation pass; rendered checks establish visual behavior. TypeScript, lint, production build and the exact-candidate pre-PR gate remain required for final delivery. Credentials belong in the local debug tooling, never in this documentation.

### Component ownership for record views

History pages coordinate queries, filtering, pagination and mutations. Record components receive typed data and explicit action callbacks; they own presentation and accessible controls:

- `pages/ExecutionHistory/components/ExecutionRecord.tsx`: workflow run identity, status, metadata and cancellation actions. The parent supplies organization visibility and optimistic status.
- `pages/ExecutionHistory/components/LogRecord.tsx`: full mobile log message and execution link; `LogLevel` also supplies the desktop severity treatment.
- `components/agents/AgentRunRecord.tsx`: agent run summary, review metadata and rerun action. It receives the return-navigation state and pending state from the parent.

These are implementation components, not new V1 runtime exports. Keep page-specific state out of them and preserve existing public component contracts. Extract further meaningful sections locally before considering whether their contracts warrant shared ownership.

`components/execution/ExecutionAiUsage.tsx` owns AI usage grouping and disclosure for the execution inspector. Its local `UsageValues` component renders labelled token/cost values consistently for totals and individual model records. Group keys include both provider and model; the parent sidebar owns execution-state visibility. This is an internal component extraction with no V1 export changes.

`ExecutionMetadata` owns execution identity/timestamp presentation and its local definition-row/time components. `ExecutionContextHelp` owns the context reference popover. Both live alongside `ExecutionSidebar`, keeping the sidebar focused on which sections apply to the execution rather than the markup of each section.

`InputDisplayToolbar` owns full-payload copying, feedback/retry, and view controls for `PrettyInputDisplay`. The parent owns view selection and shape rendering; the toolbar uses the shared clipboard helper and associates copy outcomes with their input snapshot.

`JsonValuePreview` owns the bounded JSON fallback, syntax tokens, and keyboard-scrollable preview region used by `PrettyInputDisplay`. Syntax colors reference active theme/brand variables directly, so the renderer does not require a separate theme provider or hardcoded dark palette.

`editor/EditorUploadStatus` owns upload progress, cancellation feedback, failure inspection and dismissal presentation. `StatusBar` connects it to the existing upload store; the component receives typed state and callbacks and does not perform uploads itself.

`editor/UnsavedTabsDialog` presents pending unsaved file closes. `FileTabs` owns the target-path snapshot and resolves current indices only when discarding; the dialog owns no save or tab-store mutations.

`editor/EditorFileStatus` owns the file-details popover, stable save-status label, workflow badge and cursor presentation. `StatusBar` supplies current editor state. Full paths remain available by touch or keyboard without forcing the entire path into the compact bar.

`editor/EditorCloseDialog` presents editor-wide close consequences for unsaved files and active uploads together. `EditorLayout` supplies live state across all tabs, blocks closing while a save is reported in progress, and owns cancellation/close actions. Keep editing restores focus to the initiating close button.

`FileTabs` also owns close behavior initiated from a missing-file conflict menu. Its optional `onEmpty` callback lets each host choose an appropriate keyboard-focus destination when the final tab closes.

`editor/PackageInstallForm` owns the accessible Python package form, native Enter submission, and pending presentation. `editor/InstalledPackageList` owns installed/update records and loading/error/empty presentation. `PackagePanel` retains package API calls and stream orchestration and supplies typed data and callbacks.

`editor/EditorSearchForm` owns labelled search controls and native keyboard submission. `editor/SearchResultItem` owns full-path/line/snippet presentation and safe literal highlighting. `SearchPanel` retains requests, submitted-query snapshots, error recovery and file opening; regex snippets remain readable without re-executing server regexes in the browser.

Search result selection reuses an existing editor buffer and requests the result line through the editor’s reveal API. Hosts can provide `SearchPanel.onResultOpened` to bring the code pane into view; new-file read failure retains results and exposes a retry.

`editor/CommitHistorySection` owns commit disclosure, history states and local `CommitRecord` composition. SourceControlPanel supplies API data and retry. Records retain full messages/authors, textual pushed/local status, short SHA and visible timestamp; this component does not perform Git operations.

`editor/SourceControlFileRecords` provides changed-file and conflict-file records with a shared local file-identity component. The host owns diff, discard and resolution behavior. Records preserve complete paths, use native buttons, expose version selection through pressed state, and accept a busy guard.

`editor/SourceControlStatus` provides the branch/fetch header and merge-status banner. SourceControlPanel owns operations and supplies busy state; selecting conflict versions is described separately from applying the completed merge. The parent uses one scroll area for merge status, changes and commit history.

`editor/SourceControlActions` owns commit-message entry and commit/sync/merge action presentation. The host supplies operation callbacks and busy state. Conflict mode exposes only the guarded merge action; normal commit mode supports native Enter submission, with incoming/outgoing counts and visible sync-blocking guidance.

`editor/SourceControlPrompts` owns missing-reference cleanup and pending-deletion confirmation presentation. The deletion list exposes every entity with full names/paths in a keyboard-scrollable region; host callbacks remain separate for confirm/dismiss, and pending state disables both actions while exposing readable status.

`editor/SourceControlSetupState` owns Git status loading, initial failure/retry, configuration guidance and repository initialization presentation. The host supplies query state and operation callbacks. A terminal status-query failure must expose retry instead of an indefinite loader; initialized panels retain their cached content when a status refresh fails.

`editor/SourceDiscardDialog` owns bulk-discard confirmation, pending dismissal guards and inline retryable failure. Its parent snapshots the reviewed files when opening it; confirmation receives that same file set even if working changes refresh. The host owns the Git operation and rejects on failure. A visible bulk action complements the desktop context menu, with focus restored to the Changes disclosure on close.

Individual-file discard uses the same `SourceDiscardDialog` and host operation as bulk discard, with a one-file snapshot and singular copy. Cancellation restores the originating control; if success removes that control, focus falls back to the Changes disclosure.

`editor/SourceOperationDialog` shares asynchronous confirmation behavior between merge abort and discard: pending submission/dismissal guards, persistent errors, readable pending status, and host-owned operations that reject on failure. `SourceDiscardDialog` supplies the captured file list. Merge abort supplies its pre-pull restoration explanation; cancellation returns focus to Abort merge and success falls back to the persistent fetch control.

`editor/SourceChangesSection` composes working-change records, conflict choices, commit/sync actions, prompts and discard confirmation. It owns disclosure and confirmation snapshots; SourceControlPanel supplies data and operation callbacks. Refresh errors appear before the action area, while known records remain readable and retry remains available.

Working-change refresh failure disables commit/sync/merge-completion and discard actions. Cleanup/deletion prompts retain dismissal while withholding confirmation; cached file inspection and refresh retry remain usable. `SourceOperationDialog.unavailableReason` blocks confirmation while preserving cancellation, including a discard dialog already open when freshness is lost. Local conflict version choices remain available; applying them waits for a successful refresh.

`editor/SyncDiffControls` supplies the wrapping file header and semantic local/remote resolution controls. `SyncDiffView` measures its own container: conflict comparisons use two panes only at720px or wider, and otherwise use a unified comparison. Remote is the original/left model; local is modified/right. The mobile editor treats a diff as active content even without a file tab and returns to Files & Tools when the last comparison closes.

Comparison failures retain `DiffPreviewState` file identity with error/onRetry rather than closing the view. Each asynchronous diff response is applied only while its original pending preview is still active, preventing closed/replaced requests from reopening or overwriting another comparison. CodeEditor prioritizes an active comparison over unrelated file-loading state.

`hooks/useComparisonLayout` shares container-based split/unified layout across sync and save-conflict comparisons. `ConflictDiffView` composes server/local comparison labels and44px version actions with SourceOperationDialog; failed resolution leaves the selected choice available for retry. CodeEditor propagates resolution failures to that dialog.

`lib/resolve-editor-conflict` submits the reviewed conflict's `current_etag` with the chosen version. Completion updates only the matching path/conflict identity, records the returned etag and normalized content, and preserves edits made during the request. Rejections leave the conflict available for recovery; selecting another tab cannot redirect the completion.

`lib/uuid` supplies UUID v4 correlation identifiers through randomUUID or getRandomValues, including private HTTP origins where randomUUID is unavailable. Source-control job creation and Git hooks use it. Chat message IDs delegate to the shared helper while retaining their historical non-UUID fallback when all browser crypto is absent; that fallback is never used for job IDs.

`dependencies/DependencyGraphSurface` owns graph loading, initial failure, stale refresh, retry and empty presentation. DependencyGraphDialog composes the surface with its legend; EntityManagement supplies query error/fetching/refetch state. Cached nodes remain mounted during refresh or failure, and the canvas fills available dialog space instead of enforcing a minimum that can clip on mobile.

`dependencies/DependencyGraphViewport` refits initialized graph nodes when React Flow's measured canvas dimensions change. Ordinary pan/zoom does not trigger refitting. The adjustment is immediate, including reduced-motion mode. Graph controls and the mobile legend disclosure have44px targets; long entity headings wrap without forcing horizontal overflow.

`dependencies/DependencyGraphControls` places native design-system zoom and Fit graph buttons in a toolbar below the canvas. A shared ReactFlowProvider connects the toolbar and graph; controls cannot cover node names. Their actions use immediate transitions, and obsolete floating-control CSS has been removed.

`entity-management/RelationshipFilterBanner` owns relationship context, graph/clear actions, loading, initial failure and stale-result retry feedback. EntityManagement always restricts relationship mode to graph IDs, including while graph data is unavailable, and refreshes the graph with the page refresh action. Initial lookup failure does not imply an empty dependency set. Mobile entity management uses page scrolling so a tall banner cannot collapse its record list; EntityCard wraps full names and metadata with 44px dependency/delete actions.

`entity-management/EntityAssignmentPanel` composes organization/access destinations and an explicit review dialog. Native Apply buttons and drag-and-drop use the same captured list of entity names; empty selection disables buttons, pending changes block dismissal/repeated submission, and failures retain the review for retry. `DropTargets` shares its responsive target presentation internally. `hooks/useAssignEntityRole` uses additive role endpoints for workflows/forms/agents/apps, preserving existing bindings; the page then applies role-based access. Organization and access handlers report aggregate failures instead of closing the review after a partial update.

`entity-management/EntityListToolbar` owns the search/select-all row, filter slot, explicit sort field/direction, and bulk-selection actions. It names hidden selections outside the current view, disables selection mutations while updates run, and returns focus to search after clearing. Sort remains usable in relationship mode. `FilterPopover` retains searchable groups while using group-prefixed option identities, current-filter annotations, viewport-constrained width/height, and44px options in both desktop and mobile layouts.

`entity-management/EntityCollectionStatus` reports each collection's loading, refresh, initial failure and cached failure, with a per-source retry. Other collections remain usable; incomplete data never produces a confirmed-empty claim. Surface containers in entity management consume `--bf-surface-pad` (20px default,16px compact,28px spacious) rather than ad hoc12px padding. This governs content inset; touch targets remain44px independently of surface density.

Spacing ownership: verify the rendered route shell before adding or removing gutters. Standard platform pages receive16/24/32px outer padding from their shell; full-width routes may own that inset themselves. ExecutionDetails owns it and now aligns its header/body at16/24/32px. Framed content surfaces consume the density token; row spacing, editor chrome and intentional empty-state breathing room require separate review rather than a blanket padding replacement.

`forms/FormPrivateLinkPanel` owns the private-link explanation, full-width selectable URL, copy feedback and open action. FormShareDialog owns one density-token outer inset; its three tab sections no longer add redundant frame/padding. Tab labels wrap within equal-width44px-or-larger targets. Link actions occupy two columns on narrow screens and use intrinsic sizing at wider widths.

`execution/ExecutionPageHeader` separates history/ID utilities from execution identity/status and primary actions. Editor/Rerun or Editor/Cancel share equal columns when space is constrained. A container query moves actions beside the identity only when the header itself has enough width, accounting for the sidebar. All action targets are44px; workflow names wrap unbroken text. The host supplies status content and only the actions permitted by execution state/user access; embedded execution presentation stays on its existing path.

`forms/HmacSecretList` separates load failure from confirmed emptiness, preserves cached records during refresh/failure, and provides named retry, activation and deletion controls. Secret metadata cards use the density surface inset, wrapping names and semantic active status rather than hard-coded green rails. FormEmbedSection retains all requests and dialog state; non-OK lookup responses now surface as errors.

`forms/HmacSecretReveal` owns the one-time value display and clipboard state. It wraps the full value, selects it on keyboard focus for manual copying, and uses44px named copy/dismiss actions. Failed or rejected clipboard operations keep the value visible with recovery guidance; success is announced only after completion. The host keys it by created-secret identity. Embed-code copying now also uses the shared secure/insecure-context clipboard helper.

`forms/HmacSecretDeleteDialog` keeps deletion review mounted until the request succeeds, provides inline retry and blocks dismissal during pending work. FormEmbedSection shares one synchronous mutation guard across create/toggle/delete and reports pending ownership to FormShareDialog, which blocks tab switches and close requests. Creation fields and Cancel remain disabled during POST; a failed creation retains the draft. Successful deletion removes the known deleted record before refreshing.

`forms/HmacSecretCreateForm` owns the controlled creation fields and inline retry presentation. The host retains request ownership and the draft across failures. Labels use unique IDs, the optional secret is masked, and fields/actions have 44px targets. Pending creation disables editing and cancellation; errors preserve the entered values.

`forms/FormEmbedCodePanel` is shared by website and HMAC embedding. It separates the 44px copy action from wrapping code, consumes foreground/surface/density tokens in both themes, and supports keyboard selection for manual copying. Clipboard failure stays inline; confirmation belongs to the exact snippet copied and disappears when embed options change.

`forms/FormEmbedOptions` owns the controlled appearance fields shared with the generated website snippet. A full-width theme selector and wrapping, fully clickable switch labels replace the compressed three-column arrangement. Choices remain local to the copied iframe code and do not update publication settings.

`forms/FormWebsiteRestrictions` owns the controlled disclosure, origin field, help and save feedback. The disclosure and retry use44px minimum targets; feedback is connected to the field for assistive technology. Failed autosave offers an explicit retry without clearing the draft. The host retains parsing, debounce and publication requests.

`forms/FormSharingToggle` groups publication and spam-protection labels with full-row click targets and full-width descriptions. It preserves accessible switch names and connects descriptive text; pending spam saves are announced. Publication stays disabled after a settings-load failure, until a successful reload supplies the current state.

`forms/FormPublicationReviewDialog` owns capability review and publish/rotate/disable confirmation. It stays open while requests run and on failure, announces pending/error states, blocks pending dismissal and uses44px actions. Rotation/disabling use destructive styling; capability warnings use the semantic warning token. Host requests share a synchronous duplicate guard and close review only after mutation success.

Publication capability review keeps prose left-aligned at mobile widths and uses the density surface inset. The host Rotate trigger, review Cancel and confirmation actions retain44px targets at desktop and mobile widths.

`forms/FormConfirmationEditor` composes the existing Tiptap editor and confirmation renderer with controlled edit/preview tabs,44px navigation/update controls and density-based preview padding. Both views remain mounted to preserve the editor instance. Failed saves retain the draft and offer inline retry; the host guards duplicate saves and blocks sharing navigation/close during the pending request. Editing can continue while the captured draft saves.

`FormShareDialog` keys its internal session by form ID. Confirmation drafts, publication review, request guards and HMAC state belong to that session; switching to another form creates fresh state, so delayed responses from the old session cannot overwrite the new form’s editor. The public component API stays the same.

Confirmation refresh compares the current draft against the saved baseline before replacing it. Unsaved edits survive publication refreshes, and confirmation data from a refresh started before a newer save completes is ignored. Saved baseline state still updates after successful confirmation saves, so Update correctly reflects remaining local changes.

Publication, origin and spam-protection writes share one synchronous guard. During a settings write, publication/spam/rotation controls and sharing navigation are disabled; the origin draft remains editable. A successful origin save schedules any newer draft next. Failed saves require explicit retry or an edit, avoiding repeated automatic requests. A successful spam update acknowledges the origin values included in that request.

Origin refresh also respects the saved baseline: dirty origins remain in the field when publication metadata reloads, the disclosure stays open, and autosave resumes for the remaining draft. Completed origin/spam writes advance the baseline so an older refresh cannot supersede their acknowledged origin values.

Closing sharing with a published form’s unsaved origin draft flushes the pending save immediately. Close proceeds only after success; failure retains the dialog and retry. A form-session lifetime guard and origin edit revision prevent the delayed close callback from closing a different session or dismissing newer edits.

If an origin flush triggered by Close fails, sharing selects Website Embed, opens restrictions and requests focus on Retry saving. That focus request is separate from ordinary autosave failures, which do not interrupt the editor.

`layout/ListLoadError` gives list and lookup failures an explicit retry action. Pass whether cached data exists and keep those records visible below the notice; do not show an empty-state claim for a failed initial read. The query owner supplies retry and pending state. Workflows, Forms, Solutions and the app-editor lookup consume this component.

Inputs use a 44px mobile target and the `--bf-control-height` density token on desktop (40px comfortable, 32px compact). Keep the canonical outlined surface and 6px control radius when changing sizing. A size change must not restore legacy filled/pill styling. Page-local overrides should express an actual density or composition requirement.

List action consistency: use the record name as a native navigation link, with one named overflow-menu trigger for secondary actions such as Edit and Delete. Keep that same interaction model in desktop rows and mobile records. Avoid a separate arrow/Open button that duplicates the name or row navigation. Selection remains independent of navigation. Menus must stop row-click propagation, expose keyboard-accessible actions, and return focus on dismissal; destructive actions still require their existing confirmation. Task-specific primary actions need an explicit reason to be inline. Review this pattern across sibling pages as well as checking width and touch targets.

### Markdown in product fields

Use `MarkdownContent` from `@/components/common/MarkdownContent` for generated or user-authored Markdown displayed in a field. Its default compact mode inherits the product typography: every Markdown heading renders as a restrained, body-sized section heading; paragraphs, lists, tables, links and code retain their meaning with consistent spacing. It does not apply document-sized typography or add a card around the field.

```tsx
<MarkdownContent content={run.answered} />
<MarkdownContent content={run.asked} variant="preview" />
```

Use `preview` inside list rows, titles and clickable cards. It renders inline text and emphasis without nested block layouts or interactive links, so row navigation and truncation keep working. It parses the original Markdown before rendering; do not slice Markdown source before passing it in.

Agent action narratives use `DidNarrative`, which composes the same renderer with verified action references. Its extension processes parsed text, preserving ordinary Markdown links and literal code. Keep editable text, raw logs, JSON/code inspection, and copied source as their original values. Chat's streaming/code-block presentation remains a separate specialized surface.
