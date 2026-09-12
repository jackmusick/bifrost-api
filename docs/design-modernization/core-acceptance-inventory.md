# Core acceptance inventory

This inventory covers the remaining core UI routes requested for design-modernization acceptance planning. It reconciles current source actions with existing proof. It does not promote the current journey ledger targeted journeys to complete acceptance; those remain separate candidate work and should not be duplicated here.

Evidence strength terms used here:

- **Real backend browser**: committed Playwright under `client/e2e` that uses the project authenticated fixtures/API setup and drives the rendered app.
- **Component or mocked API**: Vitest/RTL/component tests or browser fixtures with intercepted routes/modules. Useful for state and layout proof, but not persisted backend lifecycle proof.
- **Backend/API**: Python endpoint/runtime tests. Useful for persistence, execution and authorization proof, but not UI proof.
- **Design ledger**: `docs/design-modernization/*` records from modernization review. These are route reconciliation notes and often describe synthetic/intercepted browser matrices; they are not a substitute for committed real-backend acceptance specs unless explicitly tied to one.

## Home and collections

Current UI source:

- `client/src/pages/Home.tsx` reads `/api/home`, mutates collection preference at `/api/home/preferences`, creates collections with `/api/home/collections`, updates and deletes `/api/home/collections/{id}`, searches resources, filters by organization, manages pinned and custom collections, and navigates launched resources through `openResource`.
- Home component sources under `client/src/pages/Home/components/` cover collection editing, collection strips, resource cards/lists, catalog filtering and empty/loading states.

Concrete UI actions to accept:

- Search and organization-filter catalog resources.
- Favorite/pin a known resource and reload to verify persistence.
- Create a collection with name/icon/scope, add a resource, reload and verify exact membership, then delete it.
- Launch a known app, form or agent resource from Home and verify navigation resolves to the resource href supplied by `/api/home`.
- Verify empty collection and lookup-loading behavior remains usable on mobile.

Existing evidence:

- Real backend browser: `client/e2e/home.admin.spec.ts` — `creates a collection with an icon and resource, persists after reload, then removes it`. This is the strongest Home collection lifecycle proof because it drives the rendered UI and reloads.
- Real backend browser: `client/e2e/home-launch-acceptance.admin.spec.ts` — `HOME-01 persists favorite state and opens a known agent resource`. This covers favorite persistence and one launch target.
- Component/mocked API: `client/src/pages/Home.test.tsx` plus `client/src/pages/Home/components/CatalogFilters.test.tsx`, `client/src/pages/Home/components/CollectionEditor.test.tsx`, `client/src/pages/Home/components/CollectionIconPicker.test.tsx`, `client/src/pages/Home/components/CollectionStrip.test.tsx`, `client/src/pages/Home/components/HomeCatalogOverview.test.tsx`, `client/src/pages/Home/components/ResourceCard.test.tsx`, and `client/src/pages/Home/components/ResourceList.test.tsx` cover rendering and local interaction contracts.
- Backend/API: `api/tests/e2e/api/test_home.py` is the endpoint-level backing surface for Home data and collection operations.
- Design ledger: `docs/design-modernization/home-execution.md` records Home navigation, collection scope consistency, empty collections and lookup-loading follow-up.

Explicit gaps:

- Real backend browser proof exists for agent launch, but not for app and form resource launch from Home.
- Home search/filter proof is mostly component-level unless covered indirectly inside the collection specs.
- Collection permission/scope denial cases are not a dedicated real-browser acceptance path.

## Dashboard

Current UI source:

- `client/src/pages/Dashboard.tsx` reads platform metrics through `client/src/hooks/useDashboardMetrics.ts`, execution trend data through `client/src/hooks/useExecutionTimeSeries.ts`, `/api/agents`, and `/api/applications`; it renders stat cards, execution trends, recent activity and a `Refresh dashboard` action.
- Dashboard component sources under `client/src/components/dashboard/` own stat card and executions-over-time presentation.

Concrete UI actions to accept:

- Load dashboard with real authenticated data and verify primary cards render from backend values.
- Refresh dashboard and verify the UI exits fetching state without layout shift or stale error presentation.
- Open any dashboard-linked resource/action if present in the current rendered state.

Existing evidence:

- Component/mocked API: `client/src/components/dashboard/DashboardStatCards.test.tsx` and `client/src/components/dashboard/ExecutionsOverTimeCard.test.tsx` cover presentation behavior.
- Backend/API: execution, agent and application endpoint tests provide backing data confidence, but not Dashboard composition.

Explicit gaps:

- No exact committed `client/e2e` Dashboard acceptance spec was found in the audited set.
- Dashboard lacks real backend browser proof for refresh, empty/error states and route-linked actions.

## Chat and artifacts

Current UI source:

- `client/src/pages/Chat.tsx` wraps the current chat route and setup states.
- `client/src/pages/ChatArtifacts.tsx` exposes the persistent artifact library route.
- `client/src/components/chat/` owns conversation layout, composer, attachment upload/preview, profile/model selection, streaming state and artifact display.

Concrete UI actions to accept:

- Start or open a conversation, select profile/model, send a message and verify the assistant response/state transition.
- Upload a file attachment, verify preview, then send with the selected profile.
- Browse persistent artifacts and verify artifact details match the seeded conversation/artifact.
- Recover from conversation read/send failures while preserving draft text.

Existing evidence:

- Intercepted browser UI: `client/e2e/chat-attachments.admin.spec.ts` — `uploads a file with the selected profile and previews it`; `browses the persistent artifact library`. The upload goes through the real attachment endpoint, but model profiles, chat runs/state, websocket responses, and artifact-library responses are intercepted. This proves UI wiring, not durable conversation or artifact-library persistence.
- Real backend browser through another route: `client/e2e/agents-start-chat.admin.spec.ts` — `Start chat button creates a conversation and navigates to /chat` proves the agent detail start-chat handoff reaches Chat.
- Component/mocked API: `client/src/pages/Chat.test.tsx`, `client/src/pages/ChatArtifacts.test.tsx`, `client/src/components/chat/*.test.tsx`, `client/src/services/chatAttachments.test.ts`, `client/src/services/chatModels.test.ts`, `client/src/services/chatRuns.test.ts`, `client/src/hooks/useChatStream.test.tsx`, `client/src/lib/chat-runtime.test.ts`, `client/src/lib/chat-utils.test.ts`, and `client/src/stores/chatStore.test.ts` cover local chat/composer/store/streaming behavior.
- Backend/API: `api/tests/e2e/api/test_chat.py` includes conversation create/list/get/delete and attachment/artifact authorization tests; `api/tests/e2e/api/test_agent_workflow_tool_execution.py` includes `test_chat_handler_executes_global_agent_workflow_in_caller_org`.
- Design ledger: `docs/design-modernization/chat-review.md` records composer/header/artifact evidence and brand-new conversation transition.

Explicit gaps:

- The committed chat browser spec covers attachment and artifact flows, but does not prove a full real-provider assistant response lifecycle.
- Failure recovery, draft retention and streaming details are stronger in component/synthetic evidence than in real backend browser acceptance.

## History and execution

Current UI source:

- `client/src/pages/ExecutionHistory.tsx` renders `/history`, workflow/agent execution tabs, search/filter controls, log-level and run-status filters, grouped execution records, compact row actions, drawer details and navigation to full execution details.
- `client/src/pages/ExecutionDetails.tsx` renders `/history/:executionId`, supports rerun, cancel, live execution updates/logs, result/input/log panes and back navigation.
- `client/src/pages/ExecuteWorkflow.tsx` executes a workflow and navigates to `/history` or `/history/{execution_id}`.
- `client/src/pages/ExecuteForms.tsx` lists executable forms and navigates to `/execute/{formId}`.

Concrete UI actions to accept:

- Browse history, filter workflow/agent executions, filter by log/status and open row drawer.
- Open a full execution details page and verify input/result/logs match the selected execution.
- Start a workflow execution from `/workflows/:name/execute` and verify navigation to the created execution.
- Cancel a running/scheduled execution and verify the terminal cancelled state.
- Schedule execution and verify scheduled/completed/cancelled status transitions.

Existing evidence:

- Real backend browser: `client/e2e/executions.admin.spec.ts` — `should display execution history page`, `should cap wide layouts and fit narrow viewports`, `[EXEC-04 desktop] History log row opens drawer with Result/Input/Logs and full-page link for the same execution`, `[EXEC-03 mobile] cancellation of a running execution reaches a cancelled state`, plus additional bracketed execution acceptance cases in the same file.
- Real backend browser: `client/e2e/executions-realtime.admin.spec.ts` — `streams logs and status updates live into the details page`.
- Real backend browser: `client/e2e/scheduled-execution.spec.ts` — `cancel a scheduled run from the row menu`, `schedule with short delay and watch the badge flip to Completed`, `schedule a run from the workflow execute page`.
- Real backend browser: `client/e2e/history-pickers.admin.spec.ts` — `History search pickers expand beyond compact triggers and fit mobile`.
- Component/mocked API: `client/src/pages/ExecutionHistory.test.tsx`, `client/src/pages/ExecutionDetails.test.tsx`, `client/src/pages/ExecuteWorkflow.test.tsx`, `client/src/pages/ExecuteForms.test.tsx`, `client/src/components/execution/*.test.tsx`, `client/src/pages/ExecutionHistory/components/*.test.tsx`, `client/src/hooks/executionHistoryCache.test.ts` and `client/src/hooks/useExecutionStream.ts` tests cover layout, panels, cache and stream plumbing.
- Backend/API: `api/tests/e2e/api/test_executions.py`, `api/tests/e2e/api/test_executions_query_params.py`, `api/tests/e2e/api/test_cancel_scheduled_execution.py`, `api/tests/e2e/api/test_workflow_scheduled_execution.py`, `api/tests/e2e/api/test_form_scheduled_execution.py`, `api/tests/e2e/platform/test_execution_history_pagination.py`, and `api/tests/e2e/test_execution_logs_list_endpoint.py` cover execution persistence, query validation, pagination, scheduling/cancel and logs endpoint behavior.
- Design ledger: `docs/design-modernization/history-acceptance.md` records layout, interaction and filter contracts.

Explicit gaps:

- History has strong browser proof for common execution lifecycle actions, but not every filter combination across workflow/agent tabs.
- Rerun exact-input persistence has UI source support in `client/src/pages/ExecutionDetails.tsx`; its strongest proof appears mixed with details/component/runtime coverage rather than as a standalone real backend browser acceptance title.

## Apps, V1 editor and runtime

Current UI source:

- `client/src/pages/Applications.tsx` lists apps, toggles grid/table layout, searches, refreshes, deletes and routes to edit/preview/published runtime.
- `client/src/pages/AppCodeEditorPage.tsx` creates/edits apps, opens embed/settings dialogs, publishes, edits advanced settings and navigates after creation.
- `client/src/pages/AppRouter.tsx` loads published and preview app routes, handles loading/error/not-found/not-published states, and mounts V1/V2 runtime shells.
- Runtime/editor internals live under `client/src/components/app-code-editor/`, `client/src/components/jsx-app/`, `client/src/lib/app-code-runtime.ts`, `client/src/lib/bifrost-runtime.ts`, and `client/src/lib/app-code-platform/`.

Concrete UI actions to accept:

- Search/list apps, switch layout, refresh, open edit, preview and published routes.
- Create or edit app metadata/source, publish, and verify notification/completion feedback.
- Replace an app path through Advanced settings and verify persisted route change.
- Load V1 runtime published and preview routes, verify migration/runtime compatibility, unavailable-state disclosure and embedded-user behavior.

Existing evidence:

- Real backend browser: `client/e2e/apps-editor-acceptance.admin.spec.ts` — `[APP-01] editor save/file switching persists the selected file after reload — desktop` and mobile variant under the viewport describe validate editor file persistence after reload.
- Real backend browser: `client/e2e/apps-replace.admin.spec.ts` — `replaces an app's path via the Advanced section`.
- Real backend browser: `client/e2e/apps-publish-notification.admin.spec.ts` — `queues in the dialog and reports completion through notifications`.
- Real backend browser/runtime fixture mix: `client/e2e/apps-preview.admin.spec.ts` — `hot-reloads preview on push, navigates pages, and publishes to live`; `client/e2e/apps-preview-migration.admin.spec.ts` — `[V1-01] legacy components execute workflows and preserve preview and published navigation — desktop`. These seed source through the API and route through the real app shell; design-review browser matrices also note synthetic/intercepted runtime bundles for some state coverage.
- Component/mocked API: `client/src/pages/Applications.test.tsx`, `client/src/pages/AppCodeEditorPage.test.tsx`, `client/src/pages/AppRouter.test.tsx`, `client/src/components/app-code-editor/*.test.*`, `client/src/components/jsx-app/*.test.tsx`, `client/src/lib/app-code-runtime.test.ts`, `client/src/lib/app-code-platform/useWorkflowMutation.test.tsx`, `client/src/lib/app-code-platform/useWorkflowQuery.test.ts`, and `client/src/lib/app-sdk/execution-stream.test.ts` cover editor/runtime units.
- Backend/API: `api/tests/e2e/api/test_applications.py`, `api/tests/e2e/platform/test_cli_apps.py`, `api/tests/e2e/platform/test_cli_apps_replace.py`, `api/tests/e2e/platform/test_solution_deploy_execution.py`, and `api/tests/e2e/platform/test_solution_connection_runtime.py` cover app persistence, CLI deploy/replace and solution runtime backing contracts.
- Design ledger: `docs/design-modernization/applications-review.md` records organization filter/search, action menus, V1 route compatibility, runtime error hierarchy, unavailable live apps and embedded runtime acceptance; it explicitly notes synthetic modules/intercepts for some browser matrices.

Explicit gaps:

- Applications list CRUD/search/layout has component and design-ledger proof, but fewer standalone real backend browser titles than editor/runtime paths.
- Runtime acceptance relies partly on synthetic/intercepted bundle fixtures; real deployed V1/V2 bundle coverage should be read separately before claiming full release acceptance.
- Embedded-user and unavailable published/deployed states were reconciled in ledger notes, but should not be duplicated unless a remaining route-specific gap is intentionally targeted.

## Agents

Current UI source:

- `client/src/pages/agents/` owns fleet, detail/create, run detail, review, and tuning routes.
- `client/src/components/agents/` owns fleet cards/tables, settings, tool/delegate/MCP/knowledge/role/model sections, run activity, summary/review controls, chat handoff and tuning workbench components.

Concrete UI actions to accept:

- Browse fleet, search, filter inactive, switch grid/table and open the same detail from both layouts.
- Create an agent and retain the Settings tab in create mode.
- Edit settings, roles, model, tools/delegates, knowledge and MCP sections with permission/error recovery.
- Start chat from detail and verify conversation navigation.
- Open runs, expand delegated traces, inspect advanced/raw data, save review/verdict notes and verify run detail recovery paths.
- Open tuning workbench and verify disabled/pending proposal controls until backed behavior is complete.

Existing evidence:

- Real backend browser: `client/e2e/agents-fleet.admin.spec.ts` — `[AGENT-FILTER-01 desktop] inactive agents appear only when requested`; `[AGENT-BROWSE-01 desktop] search finds a seeded agent and grid and table open the same detail`.
- Mixed browser evidence (real agent shell; intercepted run history/detail fixtures): `client/e2e/agents-detail-runs.admin.spec.ts` — `groups run activity, expands delegated traces, and reserves raw data for Advanced`; `uses the same human activity view in the Runs drawer`; `shows agent detail with tabs and Runs view`; `Settings tab is the only active tab in create mode`; `does not reserve an empty scrollbar lane for sparse recent activity`; `keeps Overview context fixed and View all runs navigates`; `keeps run context fixed on desktop and falls back to page scrolling`.
- Real backend browser: `client/e2e/agents-start-chat.admin.spec.ts` — `Start chat button creates a conversation and navigates to /chat`.
- Real backend browser: `client/e2e/agents-review-verdict.admin.spec.ts` — `AGENT-REVIEW-01 saves a note and resolves a flagged run after reload`; it creates a real chat conversation/run, waits for the run to complete, marks it `down` through `/api/agent-runs/{runId}/verdict`, saves a review note, reloads, marks the run good, and verifies the review queue shows `Nothing to review`.
- Real backend browser: `client/e2e/agents-tuning.admin.spec.ts` — `tuning workbench renders with correct structure and disabled CTAs`.
- Mixed browser proof: `client/e2e/agents-tuning-apply.admin.spec.ts` — `applies an edited proposal through the real API and persists the live prompt`; it uses local browser route fixtures for flagged-run/proposal setup, then lets `/api/agents/{agentId}/tuning-session/apply` hit the real backend and verifies `GET /api/agents/{agentId}` returns the edited prompt. This was pending at this inventory update.
- Real backend browser: `client/e2e/agents-owner-budget-hidden.user.spec.ts` — `budget fields are not visible to non-admin users`.
- Real backend browser: `client/e2e/agent-create-acceptance.user.spec.ts` — `[AGENT-01 desktop] member creates private agent and reopens persisted settings`.
- Component/mocked API: broad coverage exists in `client/src/pages/agents/*.test.tsx` and `client/src/components/agents/*.test.tsx` for detail, runs, settings subsections, tuning and fleet composition.
- Backend/API: `api/tests/e2e/api/test_agents.py` includes `test_agent`; `api/tests/e2e/platform/test_cli_agents.py` covers CLI/platform agent paths; chat/workflow tool execution is covered by `api/tests/e2e/api/test_agent_workflow_tool_execution.py`.
- Design ledger: `docs/design-modernization/agent-fleet-review.md`, `agent-detail-review.md`, `agent-run-detail-review.md`, and `agent-tuning-review.md` record extensive state reconciliation. Several entries explicitly say writes were intercepted or no real executions/provider work occurred.

Explicit gaps:

- Agent fleet and run browsing have strong browser proof; many edit/save/recovery paths are strongest in component or synthetic/intercepted browser evidence.
- Tuning apply has mixed browser proof for edited prompt persistence through the real apply endpoint, plus backend proof in `api/tests/unit/test_consolidated_tuning.py` and `api/tests/e2e/api/test_agent_management_m1.py` for prompt history and verdict clearing. The browser apply spec was still pending its parent-run result at this inventory update.
- Proposal generation/regeneration and dry-run still rely on component/backend proof because the real proposal endpoint calls the tuning model. A fully real browser apply-with-verdict-clearing journey is feasible by creating a real agent run and marking it down through `/api/agent-runs/{runId}/verdict`, as `agents-review-verdict.admin.spec.ts` demonstrates; it is a finite follow-up, not an unavailable-public-endpoint blocker.
- Run summary regeneration remains backend/component proof unless a targeted browser journey is added later.

## Forms, designer and runtime

Current UI source:

- `client/src/pages/Forms.tsx` lists forms, switches layout, searches, refreshes, creates, edits, runs and deletes/forms archival actions.
- `client/src/pages/FormBuilder.tsx` edits form metadata, fields, workflow binding, info/context/share dialogs, preview tab and test-launch workflow dialog.
- `client/src/pages/RunForm.tsx` renders authenticated form execution.
- `client/src/pages/ExecuteForms.tsx` lists executable forms and navigates to form runtime.
- Form rendering/designer/list/sharing components live under `client/src/components/forms/`.

Concrete UI actions to accept:

- Search/open a seeded form from the list and verify route navigation.
- Create or edit form metadata, save, reload/reopen and verify persisted exact values.
- Add a configured field in designer, save, reopen and verify field type/label/options/settings persist.
- Submit an assigned form as a member and verify workflow result.
- Verify unassigned role-based form access denial.
- Load public/embedded/HMAC forms and verify host scrolling, session isolation and ancestor blocking.

Existing evidence:

- Real backend browser: `client/e2e/forms.admin.spec.ts` — `[FORM-BROWSE-01 desktop] admin searches and opens a seeded form`.
- Real backend browser: `client/e2e/forms-acceptance.admin.spec.ts` — `[FORM-02 desktop] designer saves and reopens form metadata`.
- Real backend browser: `client/e2e/form-fields-acceptance.admin.spec.ts` — `[FORM-03 desktop] designer adds and persists a configured form field`.
- Real backend browser: `client/e2e/forms.user.spec.ts` — `[FORM-01 mobile] member submits assigned form and sees workflow result`; `[FORM-ACCESS-01 desktop] member cannot see or open an unassigned role-based form`.
- Real/public browser: `client/e2e/forms-public.unauth.spec.ts` covers public iframe/HMAC paths including `keeps the host page fixed while opening consecutive form dropdowns`, `shows only the signed session's execution result after an HMAC submission`, and `blocks a disallowed browser ancestor on the final document`.
- Real backend browser: `client/e2e/design-foundations.admin.spec.ts` — `a mobile designer can add a field by tapping the palette and inspect its preview @smoke`.
- Real backend browser: `client/e2e/solution-runtime-contract.admin.spec.ts` — `runtime resources resolve and solution forms expose sharing`.
- Component/mocked API: `client/src/pages/Forms.test.tsx`, `FormBuilder.test.tsx`, `RunForm.test.tsx`, `ExecuteForms.test.tsx`, and `client/src/components/forms/*.test.tsx` cover list, designer and runtime composition.
- Backend/API: `api/tests/e2e/api/test_forms.py`, `api/tests/e2e/api/test_form_scheduled_execution.py`, `api/tests/e2e/platform/test_cli_forms.py`, `api/tests/e2e/platform/test_solution_deploy_execution.py`, and `api/tests/e2e/platform/test_solution_connection_runtime.py` cover backend form lifecycle, scheduling and solution-backed sharing/runtime contracts.
- Design ledger: `docs/design-modernization/form-edit-acceptance.md` and `form-runtime-review.md` record designer and runtime follow-up with explicit route status.

Explicit gaps:

- Forms have the strongest real-browser acceptance coverage among these core routes for list, designer persistence, member runtime and public runtime.
- Remaining gaps are mostly cross-field matrix breadth, destructive delete/archive UI acceptance and deeper workflow-binding/test-launch failure states.

## Workflows and editor

Current UI source:

- `client/src/pages/Workflows.tsx` lists workflows, toggles grid/table layout, filters organization/type, searches, refreshes, opens details and navigates to execution.
- Workflow cards/tables/details/settings components live under `client/src/components/workflows/`.
- Editor controls for source/file/package/register/upload/deactivation flows live under `client/src/components/editor/` and shared code editor components.

Concrete UI actions to accept:

- Load workflow list, switch layout, search/filter and clear filters.
- Open a workflow detail/card/table row and verify execute action is present.
- Navigate to execute page and run/schedule a workflow, then verify created execution in History.
- Recover from settings/endpoint/missing-file errors and enter editor when source is available.
- Register/upload/deactivate workflow from editor controls where permitted.

Existing evidence:

- Real backend browser: `client/e2e/workflows.admin.spec.ts` — `should display workflows page`; `should show workflow cards or table rows`; `should show workflow details when clicked`; `should show execute button on workflows`; `should navigate to execute page when clicking execute`; `should show platform workflows`; `should filter workflows`.
- Real backend browser through execution: `client/e2e/scheduled-execution.spec.ts` — `schedule a run from the workflow execute page` and related scheduled execution lifecycle cases.
- Component/mocked API: `client/src/pages/Workflows.test.tsx`, `client/src/components/workflows/*.test.tsx`, and `client/src/components/editor/*.test.tsx` cover list/details/editor controls, upload status, package install/register/deactivation dialogs and file/status UI.
- Backend/API: `api/tests/e2e/api/test_workflows.py`, `api/tests/e2e/api/test_workflow_scheduled_execution.py`, `api/tests/e2e/api/test_endpoint_execution.py`, `api/tests/e2e/api/test_embed_workflow_execution.py`, `api/tests/e2e/api/test_scope_execution.py`, `api/tests/e2e/platform/test_cli_workflows.py`, `api/tests/e2e/platform/test_solution_deploy_execution.py`, and `api/tests/e2e/platform/test_get_workflow_for_execution_global_repo.py` cover workflow execution, scheduling, endpoint/embed/scope behavior, CLI workflow paths and solution deployment/runtime resolution.
- Design ledger: `docs/design-modernization/workflows-review.md` records list composition/actions, filters/reads, settings and endpoint recovery, missing-file recovery and editor entry. It explicitly says browser records/API failures/key mutations/editor file contents were intercepted synthetic fixtures and route acceptance does not claim full release acceptance.

Explicit gaps:

- Workflow browse/execute navigation has committed real-browser proof; editor mutation flows are mostly component or synthetic/intercepted ledger proof.
- No new acceptance should duplicate the existing workflow browse tests unless it adds persistence or an uncovered editor/runtime lifecycle.
- Source-file editor acceptance needs exact persisted file-content verification before being considered real backend lifecycle proof.

## Current acceptance reconciliation — 2026-09-10

This update supersedes historical gap statements above only for the specific actions listed. The ledger stood at 47 passing targeted journeys before the latest solution/review-fixture browser run. `solution-lifecycle.admin.spec.ts` and `review-pack-acceptance.admin.spec.ts` both passed in the seventh parent run, bringing the current passing targeted count to 49. `chat-instructions-acceptance.admin.spec.ts` and `ai-pricing-acceptance.admin.spec.ts` had already passed before this update. `agents-tuning-apply.admin.spec.ts` is checked in as mixed browser proof with local setup interception and a real apply request, but its parent browser result was still pending when this document was corrected.

| Surface                   | Current durable journey                                                                                                                                                                                                                               | Remaining distinction                                                                                                                                                              |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Home resource catalog     | `home-catalog-acceptance.admin.spec.ts`: real app/form catalog, type/org/search filtering and exact launch destinations                                                                                                                               | Agent launch/favorite and collection CRUD remain separate existing journeys                                                                                                        |
| Home collection authority | `home-collection-access.user.spec.ts`: member private ownership, shared resource filtering, admin/member edit authority                                                                                                                               | Does not imply all collection editor validation states were browser-tested                                                                                                         |
| Chat persistence          | `chat-persistence.admin.spec.ts`: real persisted user/assistant messages, local external model fixture, browser reload                                                                                                                                | Attachments and failure/recovery use separate component/intercepted boundary tests                                                                                                 |
| Chat instructions         | `chat-instructions-acceptance.admin.spec.ts`: edits `/settings/ai-chat`, saves through `/api/admin/ai/behavior`, verifies API readback, reloads, and restores the original prompt                                                                     | Does not cover chat send/streaming; that remains in chat persistence/runtime specs                                                                                                 |
| AI pricing                | `ai-pricing-acceptance.admin.spec.ts`: creates a unique provider/model rate, verifies rendered/API prices, edits, reloads, deletes, and verifies 404 on repeat delete                                                                                 | Does not cover billing reports or model execution cost calculation                                                                                                                 |
| Workflow metadata         | `workflows.admin.spec.ts`: search, display name/description/timeout/economics save and reopen, execution navigation                                                                                                                                   | Actual execution/rerun/scheduling remains in execution specs; editor source mutations are separate                                                                                 |
| Solution lifecycle        | `solution-lifecycle.admin.spec.ts`: installs a local zip fixture, uninstalls, reactivates, permanently deletes through the UI, and verifies state via current solution APIs                                                                           | Backup/export/download remains covered by `solution-backup-export.admin.spec.ts`; this journey intentionally avoids duplicating it                                                 |
| Connected review pack     | `review-pack-acceptance.admin.spec.ts`: ensures the same review namespace twice without duplicate IDs/subscriptions/collections, launches seeded Home form, sends local webhook, and verifies workflow results include the seeded integration mapping | It proves the generic local webhook plus workflow mapping lookup path; a credential-backed provider adapter remains outside this local fixture                                     |
| Agent review              | `agents-review-verdict.admin.spec.ts`: creates a real chat run, marks it down through `/api/agent-runs/{runId}/verdict`, saves review note, reloads, marks good, and verifies empty queue                                                             | Tuning proposal generation/dry-run remains separate because proposal generation invokes the tuning model                                                                           |
| Agent tuning apply        | `agents-tuning-apply.admin.spec.ts`: local browser fixtures provide one flagged run and proposal; Apply posts to the real backend and API readback verifies the edited `system_prompt`                                                                | Pending parent browser result; because flagged runs can be created by chat execution plus verdict API, a fully real browser verdict-clearing journey is feasible if still required |

The seven original workflow page-load/conditional tests were replaced, not retained as seven additional acceptance journeys. The replacement exposed display-name search omission and now passes with that product repair. Run-layout fixtures in `agents-detail-runs.admin.spec.ts` are explicitly intercepted and cannot substantiate real run persistence.

### Finite remaining primary core gaps

- Dashboard still lacks a committed real-backend browser acceptance journey for authenticated metric composition and refresh recovery.
- Workflow editor source mutation still needs exact persisted file-content browser proof, separate from workflow list/detail and execution scheduling coverage.
- Agent settings edits for roles, model, tools/delegates, knowledge and MCP remain mostly component or intercepted proof unless a route-specific persistence journey is added.
- Agent tuning still needs either a fully real browser proposal/apply/verdict-clearing path using chat execution plus verdict API, or an explicit decision that backend apply persistence plus mixed browser apply is enough for this release.
- Form builder remaining gaps are persisted reorder/delete and launch-workflow/default binding through the rendered builder; runtime submission is already browser-proven.

### Redundant smoke disposition

`agents-backfill.admin.spec.ts` was deleted because it conditionally accepted either an absent button or a cancel-only dialog based on incidental data, supplying no unique persistence signal. `SummaryBackfillButton.test.tsx` explicitly covers eligibility, scope estimates, start/retry, progress/terminal state, cancel/retry and dismissal; `test_backfill_summaries.py` covers real enqueue/job persistence and authorization. These layers remain required by the final gate. Removed the similarly permissive Users organization smoke; `users.bulk.spec.ts` verifies exact persisted organization assignment for selected and unselected users. No required action was dropped from the inventory.
