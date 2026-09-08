# Agent detail/create review

Current status: Both agent create and edit routes are UI Verified; see the final acceptance section below. Earlier progress entries are chronological and retain the status at the time. Whole-candidate release gates remain separate.

## Page read recovery and create-tab handling (2026-09-08)

52 Verified /12 In progress. AgentDetailPage shares create/edit routes. Source previously ignored loading/read errors and could render Unknown agent plus empty edit settings. Added explicit in-page cold loading/error/missing states and a cached FleetReadError retry while retaining loaded settings. Create mode now always selects Settings even with ?tab=runs. The existing agentDetailLoader still owns initial route-load errors via RouteLoadError; no loader behavior changed.

15 focused tests22756 pass, including cold-page recovery, cached settings retention and create-tab URL regression; scoped lint/full TypeScript32953 pass. Initial browser fixtures65188/91443 incorrectly expected in-page recovery before the loader;94672/33410/10752 exposed incomplete namespace/profile/connection fixtures, not API response failures.71487 reached Settings but used an exact heading selector that omitted its Paused badge. Corrected fixtures/selector and advanced browser clock past the60s query stale time, explicitly transitioning visibility for cached refresh. Final69284 passes four synthetic custom-purple light/dark320/1440 cases: initial loader500/reload retry and cached page500/inline retry retaining heading/settings. Parent inspected dark320 cached notice spacing. No real writes. Synthetic auth produces expected logo401s; this fixture does not verify logo loading.

Both agent create/edit routes remain In progress for action recovery, settings form behavior, Overview/Runs composition, overlays, logo/auth and complete responsive/branding review. All processes terminal; diff check passes. Global candidate/release gates remain open.

## Delete action recovery (2026-09-08)

Extracted page-local AgentDeleteDialog. Previous AlertDialogAction closed immediately while mutateAsync was pending and rejection was not caught locally. New dialog catches failure, retains context, disables actions/dismissal during the request, guards repeated submissions synchronously and navigates only after successful deletion. Failure exposes Retry delete. Preserved delete scope/copy and existing mutation service.

15 page tests62919 and1 failed-delete/retry/navigation test81754 pass. Browser88148 passes four synthetic light/dark320/1440 cases with held request, disabled Cancel/Delete, Escape ignored while pending,500 retaining dialog/page and successful retry navigation. Parent inspected dark320 recovery. Target correction added44px minimums;73821 caught shared desktop Cancel min-height override, corrected with explicit desktop minimum. Final61267 browser and scoped lint/full TypeScript95737 pending. All deletes intercepted; no real agents removed.

52 Verified /12 In progress; actions pause/start-chat, Settings/Overview/Runs and full agent-route acceptance remain open.

Final browser95893 passes all four cases including44px targets after using lg:min-h-11 to match the shared Cancel breakpoint. Parent inspected final dark320 screenshot. TypeScript95737 caught a test-only unsupported Testing Library exact option; removed it, final4879 pending. Browser61267 was intermediate sizing failure, not accepted proof.

Final scoped lint/full TypeScript4879 pass. All processes terminal; diff check passes. Goal active52/12.

## Activate/pause and start-chat recovery (2026-09-08)

AgentDetailPage now guards header action requests synchronously, disables status/chat/delete while an action is pending and uses existing page-local RunActionFeedback for pending/focused inline failure/retry. Status failure stores the intended active value for retry. Starting chat also checks active state before submitting and retains success navigation. Existing service invalidation/toasts preserved.

15 page tests28103 and scoped lint/full TypeScript48279 pass. Browser68954 passes four synthetic org-user/custom-purple light/dark320/1440 cases: Activate held pending with locked delete/status,500/inline retry, exact true status update and active UI; chat held pending locking status/chat,500/inline retry, exact channel/agent body and successful /chat/new-chat navigation. Two intercepted PUTs and two intercepted chat POSTs per case. Parent inspected dark320 focused retry. No real mutations; fixture proves navigation URL, not destination conversation rendering.

52 Verified /12 In progress. Header composition still needs review (narrow action row wraps delete onto its own line). Settings form, Overview/Runs, overlays and logo permission/rendering remain open. All processes terminal; diff check passes.

## Header gutter reconciliation (2026-09-08)

Removed duplicate p-4/sm:p-7 from the normal and cold-state AgentDetailPage wrappers. Shared Layout already provides route gutters; the extra padding reduced320px content to256px and forced the delete action onto a separate line. With canonical shell gutters retained, chat/activate/delete fit on one row without reducing targets.

Browser33944 passes four synthetic custom-purple light/dark320/1440 cases, measuring aligned action y-coordinates,44px mobile target heights and document bounds. Parent inspected final dark320 header, actions and tabs. Class-only change; prior page type/unit checks remain applicable, no extra implementation-mirroring tests added. No real mutations. All processes terminal; diff check passes.

52 Verified /12 In progress. Next Settings work: onSubmit rejection is not caught locally, and reactive useForm values can reset drafts on refreshed agent data. Resolve with explicit save/recovery/draft behavior and rendered verification before route acceptance. Overview/Runs and full overlays/logo review remain open.

## Settings draft preservation and save recovery (2026-09-08)

AgentSettingsTab no longer feeds refreshed agent values directly into useForm's reactive values reset. It subscribes to dirtyFields and resets refreshed defaults with keepDirtyValues for the same agent; switching agent identity resets normally. Save now guards duplicate submissions, locks form fields while pending, catches failure locally and retains the draft with Retry save. Successful save resets the submitted values as the clean baseline. The error receives focus/scroll so it is visible when inserted above the footer. Save spinner honors reduced motion.

Initial12 tests19339 passed; lint5013 rejected passing a ref-reading callback to handleSubmit during render, corrected by constructing/submitting it in the event handler.13 tests69244 and scoped lint/full TypeScript57414 passed. Browser54357 passed four refresh/save cases, but parent screenshot review found new error below viewport. Added error focus/scroll; final browser66009 passes four synthetic org-user/custom-purple light/dark320/1440 cases: dirty name survives background refresh while pristine description updates, fields/save locked during held PUT,500 retains exact draft, focused inline failure and successful retry updates heading. Parent inspected final dark320 feedback after synthetic toast expiry. No real mutations. Final focused tests41427 and lint/full TypeScript44559 pending.

52 Verified /12 In progress. Create-mode save, tab/navigation draft semantics, settings overlays/permissions and Overview/Runs remain open.

Final13 focused tests41427 and scoped lint/full TypeScript44559 pass. All processes terminal; diff check passes. Goal active52/12.

## Creation and Settings tab retention (2026-09-08)

AgentDetailPage now retains a visited Settings panel with hidden semantics while other tabs render, preserving unsaved form state across tab changes. Settings remains lazy until first visited; create/edit identities are keyed separately. Initial effect-based visited bookkeeping was rejected by lint6722; replaced with guarded render-time state adjustment.

28 page/settings tests56144 passed before that adjustment; final76697 pending. Scoped lint/full TypeScript31337 pass. Browser67226 was stopped after confirming incomplete MCP list fixtures; corrected69764 passes four synthetic org-user/custom-purple light/dark320/1440 cases: /agents/new?tab=runs selects Settings, empty submit validates without a POST, filled create request locks inputs,500 retains name/focused failure, retry creates/navigates, then edit Settings→Runs hides the form and returning retains unsaved draft. Two intercepted POSTs per case, no real creation. Final63583 repeats with capture after transient toast expiry for parent review.

52 Verified /12 In progress. Overlays/permissions, remaining Settings composition, Overview/Runs state reconciliation and logo review remain open; global candidate/release checks remain open.

Final28 tests76697 and four browser63583 cases pass. Parent inspected final dark320 persistent create-error capture after toast expiry. All processes terminal; diff check passes. Goal active52/12.

## Tool selection draft and long-label layout (2026-09-08)

Programmatic form selection updates now use typed setDraftValue, passing shouldDirty:true so refreshed defaults preserve tool selections/removals. Tool combobox has a stable Tools accessible name,44px minimum height and viewport-constrained popover width. Selected tool/delegation chips have constrained widths and automatic height with wrapping.

13 settings tests30240 and scoped lint/full TypeScript84969 pass. Browser80167 used the display name where the option renders its system identifier; corrected6227 passed interaction but parent screenshot exposed whole-form horizontal scroll/clipping. Added form-level width/scroll-left assertions and selected-label constraints;19480 passed bounds but parent found fixed Badge height clipping wrapped lines. Final7685 passes four synthetic custom-purple light/dark320/1440 cases including popover viewport bounds, selection, Escape focus return, refresh preserving tool draft, form-level bounds and badge vertical bounds. Parent inspected final dark320 readable long label/preserved gutters. No real writes. All processes terminal; diff check passes.

52 Verified /12 In progress. Remaining selector review includes removal target/semantics, role/delegation overlays and data-read recovery; complete Settings permissions, Overview/Runs and logo review remain open.

## Selector option read recovery (2026-09-08)

Added reusable SettingsResourceNotice for agent/tool/role option loading and errors, with independent retry and explicit cached-data versus initial-failure copy. AgentSettingsTab now consumes query loading/error/fetching/update-time/refetch state, instead of only data. Empty-command copy distinguishes failed reads from no matches. Existing saved values are untouched by option loading.

13 settings tests97630 and scoped lint/full TypeScript22839 pass. Initial browser14248 passes four synthetic custom-purple light/dark320/1440 cases: three independent initial500 notices/retries and saved tool selection visible after recovery. Parent inspected dark320 notice spacing. Extended browser38375 passes all four with clock advanced beyond option stale times, independent cached500 notices retaining tool selections/options, and successful retry clearing notices. No real writes; all requests intercepted. All processes terminal; diff check passes.

52 Verified /12 In progress. Remaining: selector removal semantics/targets, role/delegation overlay interactions and complete Settings permissions/knowledge/MCP/model state review, Overview/Runs, logo. Global gates remain open.

## Tool/delegate removal semantics (2026-09-08)

Moved selected tool/delegated-agent chips outside their combobox buttons. Triggers now show selection counts with singular/plural copy; selected labels remain fully visible below. Replaced nested span role=button removal controls with native buttons, removed custom Enter/Space handling, added44px minimum targets and focus return to each selector. Existing selected values, refresh preservation and removal behavior retained.

13 tests96727 and scoped lint/full TypeScript38686 passed initial extraction. Browser72232 passes four synthetic light/dark320/1440 cases for tool popover bounds/selection/refresh and native Space tool removal, delegation selection/Enter removal. Added explicit selector focus return; final browser73002 passes all four with focus assertions and13 tests49373 pass. Parent inspected dark320 delegated selected-chip layout; corrected singular-count copy after capture. Final TypeScript63079 pending. No real writes.

52 Verified /12 In progress. Role control targets/overlay behavior, remaining Settings permissions/data/model/MCP/knowledge states, Overview/Runs and logo review remain open.

Final scoped lint/full TypeScript63079 pass. All processes terminal; diff check passes. Goal active52/12.

## Role selector controls (2026-09-08)

Assigned-role trigger now has44px minimum height. Selected role badges wrap/grow for full labels; removal uses44px native controls and returns keyboard focus to the role selector. Role access values and submission semantics unchanged.

13 settings tests98991, scoped lint/full TypeScript62110 and four synthetic custom-purple light/dark320/1440 browser cases66839 pass: role selection, popover viewport bounds, Escape focus return, long-label form bounds,44px removal and Space returning focus to the selector. Parent inspected dark320 selected-role layout. No real writes. All processes terminal; diff check passes.

52 Verified /12 In progress. Permission/read-only state, model/knowledge/MCP sections, Overview/Runs and logo remain open. Shared selected-chip markup can now be consolidated while preserving the verified behaviors.

## Solution-managed permission presentation (2026-09-08)

Confirmed API assert_not_solution_managed guards on agent update/delete/logo mutations. Settings controls now use a disabled fieldset for solution-managed agents, while banner and option-read notices remain outside it so retry remains available. Page disables pause/delete, guards status mutation and replaces editable LogoDropZone with existing EntityLogo for managed records. Active-agent chat remains available. No authorization API changes.

29 page/settings tests64701 including explicit managed-field assertions pass. Scoped source lint/full TypeScript6737 pass; new test lint separately checked. Browser21098 passes four synthetic org-user/custom-purple light/dark320/1440 cases: disabled name/prompt/tool/save/status/delete, no upload control, enabled chat and independent role-read retry despite read-only settings. Parent inspected dark320 managed banner/fields. No real writes.

52 Verified /12 In progress. Remaining agent-specific review: model/knowledge/MCP sections and permissions, Overview/Runs, mutable logo behavior and final full composition. Shared selected-chip extraction remains useful cleanup. Global candidate/release gates open.

## Knowledge-source recovery (2026-09-08)

Knowledge namespaces now expose loading/error/cached state through SettingsResourceNotice and independent retry outside the managed/pending fieldset. Knowledge MultiCombobox uses loading and failed-read empty copy; saved namespace values remain rendered as selectable/removable entries when absent from option data. Auto-enabled-tool hint wraps on narrow screens.

Initial14 tests40639 passed. Browser71964 caught saved-option logic mistakenly applied to Channels; restored CHANNELS options and moved logic to the correct knowledge_sources field. Final67560 passes four synthetic custom-purple light/dark320/1440 cases: initial500 with saved namespace visible, retry, cached500 retaining selection, retry and long-label whole-form bounds. Parent inspected dark320 saved namespace/hint layout.14 final tests70568 pass. Scoped lint/full TypeScript34047 pending. No real writes.

52 Verified /12 In progress. MCP connection list/server/detail loading currently ignores errors and can claim no connections/no tools; review that next. Model section, Overview/Runs and mutable logo behavior remain open.

Final scoped lint/full TypeScript34047 pass. All processes terminal; diff check passes. Goal active52/12.

## MCP section extraction and read recovery (2026-09-08)

Extracted AgentMCPConnectionsPanel from the settings form. Connection list, server metadata and per-connection tool catalogs now expose independent loading/error/retry states. Initial connection failure no longer claims no connections; catalog failure no longer claims no tools. Existing grants remain checked during lookup failures. Cached list errors also surface for empty lists. Row labels wrap and have44px minimum height; shared SettingsResourceNotice retry labels wrap rather than widening narrow panels.

14 settings tests78734 pass. Initial lint3617 found extraction's unused Checkbox import, removed. One redundant root ESLint invocation failed to locate client config; correct client invocation65588 pending with full TypeScript. Browser5214 passed initial flow; final28905 passes four synthetic org-user/custom-purple light/dark320/1440 cases after wrapped retry labels: list500→retry, server500→retry, catalog500→retry, retained grant, no false empty catalog and whole-form bounds. Parent inspected dark320 catalog failure. No real writes.

52 Verified /12 In progress. MCP still needs cached/catalog/empty composition and managed-agent retry reconciliation (its nested read controls inherit the managed fieldset disabled state). Model section, Overview/Runs and mutable logo behavior remain open.

Final scoped lint/full TypeScript65588 pass. All processes terminal; diff check passes. Goal active52/12.

## Managed MCP retries (2026-09-08)

Moved the MCP grant section between Tools & Knowledge and Model, outside disabled edit fieldsets. AgentMCPConnectionsPanel now accepts disabled for grants, forwarding it to native checkboxes and guarding toggle handlers. Read retry buttons remain usable for managed agents and during form saves. Settings retains disabled fieldsets for other editable fields.

14 settings tests18694 and scoped lint/full TypeScript51318 pass. Browser21051 passes four synthetic managed-agent/custom-purple light/dark320/1440 cases: initial list/server/catalog failures with successful independent retry, retained checked/disabled grant and bounded form. Parent inspected dark320 recovered MCP section with wrapped server/tool names. No real writes. All processes terminal; diff check passes.

52 Verified /12 In progress. MCP cached/empty/catalog composition and editable grant persistence still need final reconciliation; Model, Overview/Runs and mutable logo remain open.

## MCP final state reconciliation (2026-09-08)

Browser mcp-final-current.cjs completed all four custom-purple light/dark320/1440 cases: simultaneous cached list/server/catalog failures retain catalog and grant selection; independent retries preserve an unchecked draft; mocked agent PUT persists mcp_connection_ids=[] exactly once; successful empty connection response shows the genuine empty state. Parent inspected mcp-cached-dark-320.png and mcp-empty-dark-320.png. No real writes. No additional source changes for this verification.

52 Verified /12 In progress. MCP state coverage is reconciled; agent Model permissions/read states, Overview/Runs composition and editable logo remain open. Model selector currently calls platform-admin-only endpoints even for org users; investigating supported behavior before changing it.

## Agent model permissions (2026-09-08)

Confirmed /api/admin/ai has RequirePlatformAdmin at the router boundary. Agent Settings now shows a read-only assignment summary for organization users and preserves llm_profile_id when other fields save. Admin selector and creation remain available. Overview now enables its admin profile-name query only for platform admins; other users retain the existing selected/default fallback label. Did not substitute chat-only profile data for the broader agent model catalog.

Browser model-permissions-current.cjs passes four synthetic custom-purple light/dark320/1440 cases: no admin model requests or create/select controls for org users; existing saved profile survives mocked PUT; Overview makes no admin profile request. Parent inspected model-permission-dark-320.png. No real writes. Initial15 settings tests passed. Combined run caught an uncleared mock history in the new Overview assertion; corrected fixture isolation. Final29-test run72675 and scoped lint/full TypeScript85344 pending at this note.

52 Verified /12 In progress. MCP complete for reviewed states. Agent Model admin read/create overlays, Overview/Runs full composition and mutable logo behavior still need reconciliation; route count unchanged. Broader candidate/release gates remain open.

Final29 tests72675 and scoped lint/full TypeScript85344 pass. Final test-fixture lint92985 passes. All browser/check processes terminal; diff check passes. Goal remains active52/12.

## Overview rendered state review (2026-09-08)

Browser overview-current.cjs verifies independent statistics/recent-runs cold failures and retry, cached failures retaining data, true empty states and long populated summaries in four custom-purple light/dark320/1440 cases. Parent screenshot review found desktop sidebar children shrinking inside their scroll area, clipping the review action. Added flex-shrink:0 to direct sidebar children in the existing desktop workspace media rule. Final63962 passes including per-card scrollHeight bounds; parent inspected review-card screenshots at dark320/light1440 and the populated desktop layout. Mobile full-page screenshots only capture the current nested scroll viewport, so they are not evidence of every offscreen section. No real writes. Counts remain52/12.

The wider audit at1024x720 exposed a deeper Overview defect: fixed-height columns could collapse Recent activity and make Retry recent runs unreachable (browser60151 pointer interception, terminal failure). Replaced the Overview-only bounded workspace with normal page scrolling, retaining Runs behavior. Moved the Overview two-column split to xl so statistics have enough width at1024; previously labels and values broke midword. Final20712 passed six theme/width cases before the breakpoint adjustment; focused final69777 passes both1024x720 themes afterward. Parent inspected final light1024 statistics layout and desktop/mobile review-card contents. Final Overview/detail tests55245 and scoped lint/full TypeScript19233 pending. This supersedes the earlier sidebar-only shrink fix.

## Admin model dialog reconciliation (2026-09-08)

Terra implemented the bounded ModelProfileSelector/test changes and parent reviewed source and rendered behavior. Create uses a synchronous latch and a real form with stopPropagation to prevent portal submit bubbling into the surrounding agent form. Pending mutation prevents dismissal; failed creation retains entries, focuses the persistent error and scrolls it into view. Missing saved profile metadata now says Assigned profile unavailable; existing filtered saved profile remains visible. Decorative radii use canonical tokens. Parent removed proposed background-read autofocus to avoid stealing focus while editing.

Initial admin browser65842 failed because its organizations fixture returned an object rather than an array; fixed synthetic fixture, then43259 passed all four light/dark320/1440 read-retry/create-error-retry flows. Final29436 adds focused persistent error, screenshot after toast expiry and zero outer agent PUT assertions; four cases pass. Parent inspected dark320 error with retained long provider name and reachable Create action. No real writes. Agent reports10 focused selector tests and lint pass. Parent29 Overview/detail tests26536 pass after updating the old bounded-Overview expectation. Final lint/full TypeScript status follows.

52 Verified /12 In progress. Agent Runs mutation recovery and sheet states, mutable logo and final route reconciliation remain open. Shared ModelSettings consumers still need route-level acceptance; no broad completion claimed.

Scoped lint/full TypeScript19233 and final scoped lint23719 pass. Touched TSX files formatted. All browser/check processes terminal; diff check passes. Next focus: AgentRunsTab inline verdict/note pending/error/retry and RunSheet reads, then mutable agent logo. Goal active52/12.

## Runs list review-save feedback (2026-09-08)

Promoted RunActionFeedback to components/agents with a compatibility re-export at the existing page path. Retry uses explicit type=button and44px minimum height. AgentRunsTab now guards review submissions synchronously, locks inline note/verdict controls while saving, keeps failures per run, retries the exact failed verdict/note, and invalidates detail plus both list query families on success. RunCard accepts reusable disabled/feedback props. Existing note blur/Enter save behavior and mutation payloads remain intact.

Initial focused test found multiple status regions (queue banner plus saving); narrowed the new assertion to the saving feedback.31 tests30585 and scoped lint/full TypeScript76098 pass before per-run failure retention; final31 tests72930 and scoped lint/full TypeScript68629 pending. Browser40277 passes four synthetic custom-purple light/dark320/1440 cases: held note POST locks inputs/verdicts,500 retains draft and focuses inline error, retry posts exact note and unlocks on success. Parent inspected dark320 and light1440 failed-save composition. Final51451 repeats after per-run error retention. No real writes.

52 Verified /12 In progress. RunSheet still returns no UI before detail loads, ignores detail/conversation errors, and keeps its note only in local state; review that boundary next, then mutable logo and final agent route acceptance. Global gates remain open.

Final31 tests72930 and scoped lint/full TypeScript68629 pass. Final51451 browser passes all four cases. All processes terminal; diff check passes. Goal active52/12; next is the RunSheet read/save boundary.

## Review sheet loading and read recovery (2026-09-08)

Extracted AgentRunSheet controller from AgentRunsTab. Shared RunReviewSheet now opens immediately for missing detail data, showing loading or a padded retry state. Detail and tuning-conversation queries have independent retry feedback; cached data stays available. Conversation read failure/loading no longer masquerades as Thinking or an empty conversation. A separate disabled prop locks the cached conversation composer without displaying a send spinner. Parent browser review corrected initial retry padding and verified mobile error composition.

Browser36111 initially failed because loaded sheets take their accessible name from the run title; corrected the fixture locator.25740 passed four custom-purple light/dark320/1440 cold detail/conversation retry cases. Expanded72184 caught missing opener focus after close; added shared useDialogReturnFocus to both sheet content branches. Final78696 passes all four including close→run-card focus restoration. Parent inspected dark320 detail/conversation errors and light1440 detail recovery surface. No real writes.

34 final focused tests45991 pass (Runs, sheet, FlagConversation). Earlier scoped TypeScript95211 passed.25292 terminated143 with no diagnostic; confirmed terminal, restarted26180, still pending at this entry. Diff check passes.

52 Verified /12 In progress. RunSheet note persistence, draft identity and review/chat mutation recovery remain open; cached read composition still needs browser coverage. Then mutable logo and final agent route reconciliation. Goal remains active.

Final scoped lint/full TypeScript26180 and final sheet lint87331 pass. All checks/browser processes terminal. Goal active52/12; continue with sheet note/review/chat persistence and cached reads.

## Review sheet note and chat persistence (2026-09-08)

AgentRunSheet now initializes notes from the API, stores drafts by run ID, saves verdict/note with pending lock and exact failed-payload retry, and updates detail/list caches on success. Shared sheet renders Save review note for an edited note with a verdict, or instructs the user to choose Good/Wrong. Review controls and close button lock while saving. Feedback/actions use consistent internal gutters. The generated API response type is used at the legacy service boundary; generated string verdict is narrowed to up/down/null.

Chat now returns the mutation promise to the shared ChatComposer. Failure keeps the composed text and success clears it and refreshes the conversation. Earlier synchronous callback caused premature clearing. Parent source review and browser41542 pass all four synthetic custom-purple light/dark320/1440 cases: existing note loads, held save locks controls/close,500 retains/focuses error and retries exact note; held chat send,500 retains text, retry succeeds and refreshed message appears. Final71000 repeats after feedback padding. Parent inspected dark320 note and chat failures. No real writes.

34 tests78722 and final49791 pass. TypeScript21404 found omitted verdict_note in legacy service type; switched to generated response.80269 exposed generated verdict's string type and terminated143; narrowed to supported values and restarted40268 after confirmed terminal. Final lint/TypeScript40268 pending at this note. Diff check passes.

52 Verified /12 In progress. Cached sheet reads, switching/reopening draft identity and final Runs composition remain for acceptance, followed by mutable logo and agent route reconciliation. Global gates remain open.

Final scoped lint/full TypeScript40268 pass. All processes terminal.34 focused tests and four final browser cases pass; diff check passes. Goal active52/12. Next: cached sheet reads and draft identity, then mutable logo/final agent reconciliation.

## Cached sheet state, logo editing, and create-route acceptance (2026-09-08)

Cached sheet browser90413 verifies draft isolation when switching/reopening two runs and retained message/draft during simultaneous detail/conversation failure. Parent screenshot review found fixed mobile content could hide the second retry; narrow/short sheets now scroll as one surface. Final74264 passes four theme/width cases, retries conversation first while detail remains failed, then restores both reads. Parent inspected dark320 with both errors and saved message visible.34 tests82939 and scoped TypeScript50668 pass.

AgentLogoEditor now opens a128px upload surface from the48px header logo, fixing the clipped44px remove target. Managed agents retain their static logo. LogoDropZone now uses separate native upload/remove buttons inside a group, preserving drag/drop and upload locking.24 final logo/page tests18549 pass, including real keyboard activation. Scoped lint/full TypeScript3114 pass. Browser81589 and final16679 verify upload/delete held failures and successes, bounded remove target and close focus in four themes/widths. Final touch-context rerun20576 pending; parent inspected dark320 dialog after toast expiry. No real writes.

Create route /agents/new is UI Verified based on cumulative settings/create evidence above and final current-code3491 four light/dark320/1440 validation/pending/failure/retry/navigation/draft cases. Parent inspected current dark320 create-error composition. Authoritative count53 Verified /11 In progress. Edit route remains open for final Runs filter/list/overlay composition reconciliation; platform-wide shared-component, full-suite and delivery gates remain open.

Final touch-context logo20576 passes all four cases. Parent inspected dark320 with visible44px removal control and unobscured Done action. All processes terminal; diff check passes. Inventory regenerated:64 routes,146 page modules,53 primitives,372 feature components;53 Verified/11 In progress. Next: final agent Runs list/filter/collection composition, then remaining10 non-agent routes and global gates.

## Final Runs collection and edit-route acceptance (2026-09-08)

Removed the Runs fixed-height workspace after parent screenshot review found short desktops left too little room for run content. Runs now uses ordinary page scrolling. Final collection browser23643 and pagination67141 passed light/dark at320x480,1024x720 and1440x900: initial read retry,12 readable cards, empty search/clear focus, verdict filter, retained first page during failed next-page load, and successful retry. Metadata browser log records all six cases passing key-load retry, long-key selection, exact serialized filter request, removal and focus restoration; its process handle was already expired when polled after context recovery. Parent inspected final dark320 metadata and light1024 pagination-error captures in addition to the earlier collection captures. Synthetic intercepted API traffic only.

45 focused detail/Runs/filter tests74158 and scoped lint/full TypeScript59757 pass. The obsolete fixed-workspace class assertion was removed. /agents/:id is UI Verified on cumulative evidence in this file, bringing the route ledger to54 Verified/10 In progress. This does not close shared-family, V1, branding, full-suite, release or deployed-candidate gates.
