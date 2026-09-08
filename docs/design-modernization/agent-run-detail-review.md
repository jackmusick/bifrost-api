# Agent run-detail reconciliation

Status: UI Verified. Overall52 Verified/12 In progress. Historical checkpoints below preserve the review trail; global candidate/release gates remain open.

Previous turn accepted tuning. Run-detail source initially treated failed run queries as Run not found with no retry; cached refresh failures were invisible. AgentRunDetailPage now uses shared family FleetReadError for initial and cached failures, keeps contextual back navigation on cold failure and execution content on cached failure. Actual missing-data state remains separate.

27 focused tests31344 pass. Current browser53185 passes4 custom-purple light/dark320/1440 cases: initial500 never claims Run not found, retry renders execution; cached500 retains execution and retry clears notice; no document overflow. Parent inspected dark320 cached notice/header. Scoped lint/full TypeScript77624 pending. All browser APIs intercepted; no real writes. Diff check passes.

Remaining: verdict notes (source currently only local state and omits note from POST), pending/failure/save behavior, rerun, metadata/parent-run/flag conversation recovery, raw/advanced/activity and delegation interactions, live streaming/status/reduced-motion reconciliation, permission and full composition. Route remains In progress; global release gates open.

Final scoped lint/full TypeScript77624 pass. All processes terminal. Parent dark320 cached notice/header inspection complete; goal active51/13.

## Verdict notes and retry (2026-09-08)

Previous turn made verified run-read recovery progress. Run-detail note originally initialized before async data arrived and was omitted from verdict POST. Notes now use per-run drafts with stored-note fallback, submit with verdict, and expose Save review note for edits without changing the verdict. Synchronous guard and disabled review fieldset block duplicate editing/submission while saving. New page-local RunVerdictFeedback provides saving status and focused retry without hiding the rest of execution. Success refreshes normal/infinite run lists; clearing a verdict clears its local note.

Initial tests23623/browser89602/TypeScript43141 caught a missing useRef import after an import-format mismatch in editing. Corrected import;28 tests12738 and4 current browser30866 custom-purple light/dark320/1440 pass: stored note, exact note-only POST, held pending, focused500/retry, retained draft, DELETE and cleared note/verdict. Parent inspected dark320 failure spacing. Final scoped lint/full TypeScript2348 running. No real writes; all mutation routes intercepted. Route remains In progress51/13 for rerun, metadata/conversation, activity/delegations and streaming. Global release gates remain open.

Final scoped lint/full TypeScript2348 pass. All processes terminal; goal active51/13. Next rerun/read metadata and execution activity reconciliation.

## Rerun lifecycle (2026-09-08)

Previous turn made verified verdict-note progress. Generalized page-local RunVerdictFeedback to RunActionFeedback; both verdict and rerun now share focused inline failure and pending feedback with action-specific copy. Removed rerun's transient-only error toast. Rerun has synchronous duplicate guard and disabled control when agent_id is absent, matching the handler's capability. Successful queued-run navigation and origin state preserved.

28 tests40288 pass; scoped lint/full TypeScript45614 pass. Browser77234 passes4 custom-purple light/dark320/1440 cases: held rerun pending/disabled,500/focused retry, exact POST/new-run navigation, native origin link back to original execution, and disabled orphan run. All rerun writes intercepted; no real executions created. Parent inspected dark320 retry presentation. No stale RunVerdictFeedback imports remain. All processes terminal; diff check passes. Route remains In progress51/13 for metadata/conversation, activity/delegations and streaming. Global release gates open.

## Activity controls and nested overflow (2026-09-08)

Previous turn made verified rerun progress. Extracted RunActivityHeader with full-width mobile mode controls and44px touch targets; desktop remains compact. Raw executor trace disclosure also44px. Initial28 page tests50739 passed; lint45293 caught an unused CardDescription import, removed. TypeScript8974 ended143; rerun9726 passed after terminal confirmation.

Rendered review found activity header apparently losing padding after raw trace expansion. Geometry traced it to the activity card horizontally scrolling20px, with scrollWidth1215 versus286 client width, from intrinsic timeline grid width and an unbroken projected result description. Fix constrains activity content/grid and Timeline's own column, wraps row prose anywhere, confines raw trace horizontal scrolling, and narrows mobile marker/indent to24/32px with correctly centered rail (desktop44/48 retained). Intermediate bounds failures32190/59348/61512/16432 were used to trace nested overflow, not accepted as proof.

Final browser1053 passes4 custom-purple light/dark320/1440 cases: both mode targets>=44px, Advanced raw disclosure, long input/result and card-level scrollWidth<=clientWidth with scrollLeft0, switching back hides technical trace. Diagnostic overflow arrays empty on all four. Parent inspected final dark320 header and narrower timeline: padding and messages stay inside card.42 Timeline/page tests44070 pass. Final scoped lint/full TypeScript86197 pending. Route remains In progress51/13 for metadata/conversation, delegation and realtime states. Global release gates open.

Final scoped lint/full TypeScript86197 pass. All processes terminal; goal active51/13.

## Agent and parent-run metadata recovery (2026-09-08)

Previous turn made verified activity bounds progress. AgentRunDetailPage now exposes independent initial/cached agent and parent-run errors through family FleetReadError notices while retaining execution content. Cached parent navigation remains a native parent-run link during refresh failure.

30 focused tests75222 pass. Browser3393 passes4 custom-purple light/dark320/1440 cases: agent/parent initial500, independent retries, correct parent href, cached500 retaining parent href and child execution, successful retries clear both notices. Parent inspected dark320 stacked notice spacing. Final scoped lint/full TypeScript32123 pending. No real writes; all fixture reads intercepted. Route remains In progress51/13 for conversation send/read recovery, delegation and realtime states. Global release gates open.

Final scoped lint/full TypeScript32123 pass. All processes terminal; diff check passes. Goal active51/13.

## Conversation read and send recovery (2026-09-08)

Previous turn made verified metadata recovery progress. Run-detail tuning conversation now distinguishes loading/error from empty success and provides independent read retry, retaining cached conversation when available. Send returns a promise and writes the returned conversation into its canonical query cache so replies appear immediately.

Shared ChatComposer now supports synchronous or asynchronous onSend, keeps entered text until success, guards duplicate submits synchronously, makes the textarea read-only while sending and retains/focuses text with inline failure feedback on rejection. Existing void callers remain supported. FlagConversation forwards the promise contract. No API changes.

48 run-page/composer/conversation tests68685 pass; scoped lint/full TypeScript88674 pass. Browser24863 passes4 custom-purple light/dark320/1440 cases: read500/retry without false empty composer, held send lock,500 retaining exact message, successful retry clearing input and rendering returned assistant message. All mutations intercepted. Parent inspected dark320 retained text/error composer. All processes terminal; diff check passes. Route remains In progress51/13 for delegation and realtime/state reconciliation. Shared composer is included in final candidate-wide verification scope; global release gates open.

## Delegated-run recovery and return context (2026-09-08)

Previous turn made verified conversation recovery progress. Timeline delegated rows now expose initial/cached detail failures with retry and retain cached child details. First browser90218 proved recovery but caught lost expanded state after child navigation. Parent page now records runActivity (run ID, expanded IDs and return activity) in the parent history entry before opening the child, and initializes its local maps from that state. Stored strings are filtered before use; existing contextual origin retained.

44 final Timeline/run-page tests14030 pass; scoped lint/full TypeScript31223 pass. Intermediate17840 timed out at initial disclosure before reaching the flow; changed browser fixture to fresh synthetic org-user authentication rather than persisted debug auth. Final29566 passes4 custom-purple light/dark320/1440 cases: child initial500/retry, cached500 retaining details/retry, child navigation/native return, restored parent expansion and no document overflow. Parent inspected final dark320 delegation capture. No real writes. All processes terminal; diff check passes. Route remains In progress51/13 for realtime/status/summary and final composition reconciliation; global release gates open.

## Per-run realtime stream (2026-09-08)

Previous turn made verified delegation progress. Source trace found run-detail using only agent-wide status invalidation; per-step events are published on agent-run:{id} and were not subscribed. Page now mounts existing useAgentRunStream and merges its buffered Zustand steps with fetched steps by ID, sorted by step_number, preferring persisted API records for duplicate IDs. Status/summary query invalidation remains. Existing stream hook now ignores a connection resolving after cleanup so it cannot attach obsolete listeners after navigation.

30 page tests1069 pass; scoped lint/full TypeScript21318 pass. Browser2726 passes4 fresh synthetic org-user/custom-purple light/dark320/1440 cases over Playwright's WebSocket transport: queued→running→completed, step-only tool/result events visible while API still has no steps, duplicate step event renders one activity, API persistence merges without duplicate activity, and final summary update renders without reload. Parent inspected dark320 final readable activity/controls. Context uses reduced motion; all events/data synthetic, so this proves frontend transport/render behavior, not actual executor/provider work. No real writes. All processes terminal; diff check passes.

Route remains In progress51/13 for failed/terminal error presentation, summary-regeneration permissions/recovery and final composition reconciliation. Global release gates open.

## Terminal status and summary permissions (2026-09-08)

Queued/running runs previously fell through to “Run failed.” Shared RunReviewPanel now gives active runs a status section and distinct labels for failed, timeout, cancelled and budget-exceeded outcomes. Cancelled runs without an error receive cancellation copy. Sidebar summary regeneration is admin-only and omitted when the failed-summary panel owns recovery; removed unreachable failed-sidebar copy and an inaccurate backend-idempotency comment. Status banner wraps and uses canonical control radius/reduced-motion overrides.

Initial browser proof caught intrinsic grid overflow from long unbroken error text. Shared panel now constrains its grid column, section minimum width and text wrapping. A subsequent fixture-only strict-locator failure was corrected to select the banner rather than both banner and placeholder. Final browser15026 passes four synthetic org-user/custom-purple/reduced-motion cases, light/dark at320/1440: queued/running without false failure, four terminal labels, long errors bounded to panel width, and non-admin regeneration permission. Parent inspected dark320 terminal-error and failed-summary screenshots. Final55 focused tests27762 pass; scoped ESLint/full TypeScript94289 pass; diff check passes. All processes terminal.

Route remains In progress51/13: admin summary regeneration pending/failure/retry and final composition reconciliation remain. No real writes or executor/provider work in these fixtures. Global candidate/release gates remain open.

## Shared summary regeneration recovery (2026-09-08)

Replaced duplicated panel/page request handlers with shared SummaryRegenerationControl. Preserves admin permission and existing summary-status visibility, adds synchronous duplicate-request guard, pending status, focused inline failure and retry. Success invalidates detail, ordinary run lists and paginated lists. Both hosts retain their existing test IDs. Control uses the canonical Button and44px minimum height; failed feedback wraps in narrow layouts.

55 panel/page tests18777 and2 request-guard/permission tests57404 pass. Browser62553 passes four synthetic admin/custom-purple light/dark320/1440 cases: both hosts held pending,500 response, focused recovery, successful retry, generating handoff and44px targets; exactly four intercepted writes per case. Parent inspected final dark320 panel and sidebar recovery screenshots. No real mutations. Earlier browser71246 passed behavior but parent identified the small target;62553 includes the correction. Scoped lint/full TypeScript58651 passed before adding paginated-list invalidation; final48490 pending. Inventory regenerated:64 routes,143 page modules,368 feature components,53 primitives.

51 Verified /13 In progress; run-detail remains open for final composition reconciliation. Global release/candidate gates remain open.

Final scoped ESLint/full TypeScript48490 pass. All processes terminal; diff check passes. Goal active51/13.

## Sidebar usage composition (2026-09-08)

Final composition source review found a five-column usage table in the narrow sidebar, with model names shortened to18 characters. Extracted RunAIUsageCard into the page folder. Each model now retains its full name with wrapping and a two-column definition list for Calls, Cost, Input tokens and Output tokens; server totals remain separately labeled. Existing per-model aggregation is preserved. Run metadata grid now uses a constrained value column and wraps long caller/model values.

30 page tests86008 and1 aggregation/server-total test81248 pass. Browser46256 passes four synthetic custom-purple light/dark320/1440 usage cases. Additional full composition capture2163 was deliberately stopped after identifying an incorrect fixture selector (Summary instead of Activity); corrected54590 passes all four with activity-mode return and screenshots. Parent inspected dark320 usage, dark320 header and dark1440 full composition. No real writes. TypeScript99084 caught missing generated totals fields in the new test fixture; corrected fixture, final16635 pending.

51 Verified /13 In progress. Before accepting run-detail, reconcile orphan-run agent navigation (source still constructs a link from a nullable agent ID) and final shared review control targets. Global candidate/release gates remain open.

Final scoped lint/full TypeScript16635 pass. All processes terminal; diff check passes. Goal active51/13.

## Final controls and route acceptance (2026-09-08)

Deleted-agent runs now preserve the stored agent name and show an unavailable explanation instead of an invalid agent-card link. Initial browser35107 caught another /agents/null link in breadcrumb fallback; fixed fallback to /agents with Back to agents copy, retaining explicit origin and valid parent navigation precedence. Parent-run href is built only with an available agent ID. Review buttons already use44px mobile targets and32px desktop targets; browser verifies rendered sizes without changing their compact desktop treatment.

Final browser81264 passes four synthetic custom-purple light/dark320/1440 cases: keyboard focus, review target sizes, deleted-agent explanation, no /agents/null links, disabled rerun and bounded layout. Parent inspected dark320 focus and unavailable-agent screenshots.56 focused tests25909 including deleted-agent regression pass; scoped lint/full TypeScript6016 pass; diff check passes. All processes terminal.

Accepted this route after reconciling the documented read/retry, verdict/note, rerun, metadata, conversation, delegation/return, streamed activity/status, summary permissions/recovery, raw/detail modes and full sidebar composition evidence.52 Verified /12 In progress. This is route UI acceptance, not proof of real executor/provider work or candidate-wide release readiness. Global shared-component, branding/V1, full test/build and exact-candidate release gates remain open. Next: AgentDetailPage, shared by create/edit routes and their Overview/Runs/Settings tabs.
