# UI acceptance coverage: implementation plan

Prepared 2026-09-09 against `5253e00cd`. This is a source audit and proposed
implementation backlog, not a passing test report. No suites were run for this
audit. Existing browser evidence below describes assertions in source, not a
claim that the entire file or area is complete.

Implementation has started. The executable bindings are now in
`client/e2e/acceptance-ledger.json`; the runner emits
`client/playwright-results/acceptance.md` with the revision, whole-run outcome,
and individual desktop/mobile cases. Read that generated report for current
results. The original findings below describe the starting point, not the
current contents of specs that have since been strengthened.

### First implementation batch

Eighteen named journeys now have test bindings: assigned form submission on
desktop/mobile, forbidden form access, form browsing, metadata and field edits,
execution back navigation, rerun, cancellation and the log drawer, app editor
file persistence on desktop/mobile, V1 component/workflow compatibility,
private member agent creation, deterministic fleet browsing and inactive filtering, organization lifecycle, bulk user movement,
integration mappings and real webhook delivery inspection. Binding a journey
does not imply it passed; the generated report is the evidence.

Tests use real Bifrost APIs, storage and workers. The editor's pinned third-party
Monaco assets are supplied locally in the browser runner, including worker
delivery. The V1 fixture exercises input/button/workflow hooks and preview plus
published navigation; it is not full Covi Portal compatibility proof.

A passing agent save test's screenshot exposed an irrelevant roles-load warning
for a member-owned private agent. The repair enables role fetching only for
role-based access; component tests cover both private suppression and retention
of genuine role-loading errors. The browser journey also checks that reopening
the private agent does not show this warning.

### Follow-up source audit

The parallel source review found reusable coverage and these remaining gaps.
These are source findings, not results of running the listed suites:

| Area | Existing evidence to reuse | Remaining behavior to prove |
| --- | --- | --- |
| Home | `home.admin.spec.ts` creates, edits, reloads and deletes a collection through the UI | Member/private authority, favorites and each resource launch type |
| Auth and permissions | Real MFA login and protected redirects in `auth.unauth.spec.ts` | Replace loose/conditional assertions in `permissions.user.spec.ts`; verify identity expiry separately from a route-specific denial |
| Agents | Real private creation; `agents-start-chat.admin.spec.ts` opens a conversation URL | Deterministic fleet search/view switching; assert persisted conversation state after launch |
| Chat | `chat-attachments.admin.spec.ts` exercises UI using intercepted chat/model/artifact responses | Real Bifrost conversation/message persistence with only the external provider controlled |
| Config | Scroll checks and specialized AI configuration UI tests | Generic typed-value create/edit/reload/delete |
| Tables | Policy editors and real SDK data access in synthetic apps | Table and record CRUD through the management UI |
| Files | `files-explorer.admin.spec.ts` creates a share, uploads, previews and tests access | Rename/move/delete through the explorer |
| Roles | `roles.detail.admin.spec.ts` assigns/unassigns users and navigates to their detail | Role entity create/edit/delete and remaining assignment tabs |
| Integrations/events | Card/logo edits, real mapping edits and webhook delivery inspection | UI source/subscription creation, configuration, auto-map and lifecycle actions; controlled external connection checks |
| Entity management | Entity logo tests concern apps and agents, not this workspace | Actual assign/reassign/unassign actions on `/entity-management` |
| MCP | Instructions and authenticated MCP API calls | Server/connection management through the UI |
| Settings | AI model/profile UI interception; controlled preferred-SSO flow | Persisted settings changes, reset/revoke operations and remaining tabs |

The complete route/action inventory and launch gate remain outstanding. This
batch is not a platform-wide coverage percentage.

## Intended outcome

Every supported page has an explicit inventory of user actions. Important
journeys run automatically against an isolated Bifrost stack, with known data,
real persistence, role boundaries, and narrow-screen checks. A review report
shows what passed, failed, was not run, and remains unimplemented. Human review
can then concentrate on design quality and genuinely external integrations.

The existing 478 frontend test files and 56 browser spec files are a useful
foundation, but file counts cannot measure this outcome. Some browser tests
only prove that a heading renders; some silently avoid the action if no data
exists. These must not count as completed acceptance journeys.

## Findings that change the plan

| Existing source | What it actually proves | Required improvement |
| --- | --- | --- |
| `forms.user.spec.ts`, “should be able to submit assigned forms” | Opens the forms page; conditionally opens submission UI | Seed an assigned form, fill it, submit, and assert the workflow result. Missing fixtures must fail setup. |
| `permissions.user.spec.ts`, “should see own organization data only” | Main content is visible | Seed allowed and forbidden resources; assert exact visibility and direct-route denial. |
| `executions.admin.spec.ts`, rerun test | Includes `expect(true).toBe(true)` | Click rerun, verify populated input and a new execution with the expected result. |
| `organizations.admin.spec.ts`, create test | Opens the creation form | Submit through the UI and verify the new organization after reload. |
| `users.bulk.spec.ts` | Selects users, submits move, sees a toast | Verify all selected users moved and unselected users did not, including after reload. |
| `event-source-graph.admin.spec.ts` | Useful retry and resubscribe UI wiring with intercepted responses | Add a real local webhook → event → workflow → delivery journey. Keep Graph boundary tests separately identified. |
| `home.admin.spec.ts` | Creates a collection, reloads it, edits and removes it; checks dialog scrolling | Extend this stronger pattern to other management screens and member/private scope cases. |
| `executions-realtime.admin.spec.ts` | Starts real work and asserts streamed log updates and completion | Extend to reconnect/back navigation, cancel, failure, and result-first drawer/full-page consistency. |

Spec filenames in this document are relative to `client/e2e/`.

## Page and capability backlog

P0 is the first blocking acceptance set. P1 is required for launch of the
redesign. P2 is extended discovery beyond the minimum launch set. These are
implementation priorities, not permission to ignore known failures.

“Candidate” means a related spec was located but its complete assertions have
not been audited here. “Gap” means no dedicated action proof was established
by this audit; it does not imply an absence of component or backend tests.

| Area / routes | Current browser evidence | Acceptance work still required | Priority |
| --- | --- | --- | --- |
| Sign-in, protected routes, invite/setup, callbacks | `auth.unauth.spec.ts`; invite completion in `users.admin.spec.ts`; preferred-SSO candidate | Signed-out redirect without denial flash; expired session recovery; valid session with route 401/403 stays signed in; return URL; invite registration becomes active | P0 |
| Home and collections `/` | Real collection create/reload/edit/delete in `home.admin.spec.ts` | Open each resource type; favorites persistence; private/shared visibility and edit authority; empty collections; search and collection switching | P0 |
| Dashboard `/dashboard` | Home test navigates there | Assert metrics against seeded records, filters and drill-down destinations; loading/error/empty states | P1 |
| Workflow list and execute `/workflows`, `/workflows/:name/execute` | `workflows.admin.spec.ts` largely navigation/visibility | Find known workflow, edit/save supported metadata and scope, execute with inputs, open result; second-page actions | P0 |
| History and execution `/history`, `/history/:id` | Real streaming, picker geometry, responsive bounds | Actual filter results and pagination; drawer/full-page Result/Input/Logs; rerun; cancel; failure; browser back/reconnect; no page shift or empty result gap | P0 |
| Forms and designer `/forms`, `/forms/new`, `/forms/:id/edit`, `/execute/:id` | Mostly shell checks; mobile add-field/preview in `design-foundations.admin.spec.ts` | Create/save/reopen; edit/reorder/delete fields; validation and dynamic options; assign scope/roles; submit as member; cancel edits; responsive designer | P0 |
| Public/embedded forms | `forms-public.unauth.spec.ts` has targeted signed/public form journeys | Preserve and audit existing submission/HMAC/security assertions; add supported field types and denied/expired capability states without duplicating backend contract tests | P0 |
| Apps list, editor, preview and runtime | Preview/publish journey in `apps-preview.admin.spec.ts`; migration/replace candidates | UI create/edit/save/publish; navigation and refresh in published app; file switching with unsaved edits; failed save/recovery; mobile launch | P0 |
| V1 app compatibility | `apps-preview-migration.admin.spec.ts` candidate | Dedicated frozen V1 fixture exercising actual included components, workflow calls, forms, tables, navigation and theme isolation; separate Covi Portal acceptance fixture with sanitized data | P0 |
| Agents list/create/settings `/agents`, `/agents/new`, `/agents/:id` | Fleet mostly smoke; start-chat candidate; selected detail checks | Create as member with private default, save instructions/tools/channels, reload, publish/share with role rules, activate/deactivate, launch chat; no creation-status error | P0 |
| Agent runs/review/tune | `agents-detail-runs`, `agents-review-verdict`, `agents-tuning` candidates | Real run lifecycle and detail/drawer; delegated activity; authorized review actions; save/apply supported tuning actions; validate disabled states intentionally | P1 |
| Chat and artifacts `/chat`, `/chat/:id`, `/chat/artifacts` | `chat-attachments.admin.spec.ts` has substantial intercepted chat/transport responses | Real Bifrost conversation/run persistence with deterministic provider at external boundary; send/stream/stop/reopen; attachment and artifact retrieval; mobile composer reachability | P0 |
| Organizations `/organizations` | Real status edit; creation only opens UI | UI create/edit/status/delete where supported, saved instructions, search/pagination, exact row actions and scope effects | P1 |
| Users `/users`, `/users/:id` | Invite registration; bulk move toast; row navigation | Admin UI create/invite/edit/disable, role assignment, bulk persistence, cancel/destructive confirmations, pagination | P1 |
| Roles `/roles`, `/roles/:id/:tab` | Real user assignment/unassignment in `roles.detail.admin.spec.ts` | Create/edit/delete; enumerate every actual consumer tab; assign/unassign and persist each supported resource type; pagination; resulting user access | P1 |
| Config `/config` | Scroll geometry in `desktop-scroll.admin.spec.ts` | Create/edit/delete typed and long values, secret masking, scope filtering, mobile value inspection, cancel and failed-save recovery | P1 |
| Tables `/tables`, `/tables/:id` | Actual wheel-scroll assertions, including record reachability | Table and record CRUD; JSON edit/validation; filter/search/page actions; reach last row/action on desktop and mobile | P1 |
| Files `/files` | Real share creation/upload/preview in `files-explorer.admin.spec.ts`; policy candidates | Folder/file rename/move/delete/download; execute Test Access and inspect result; access enforcement; cleanup; mobile tree and breadcrumbs | P1 |
| Integrations `/integrations`, `/integrations/:id` | Real description/logo persistence, select mode, table navigation; intercepted OAuth authorize | UI creation; schema/config edit; mapping search/add/edit/delete/auto-map and persistence; bulk action result; connect/disconnect state; card/table action parity | P1 |
| Event sources and event detail | Graph retry/resubscribe UI interception | Real source/subscription create/edit/disable/delete; webhook submission; event detail, delivery and retry outcomes; scheduled variant with controlled trigger | P1 |
| Entity management `/entity-management` | Prior review notes include intercepted UI fixtures; dedicated persistence proof is a gap | Load provider entities, search/filter, assign/reassign/unassign, bulk action persistence, failed provider recovery, diagram and overflow menu reachability | P1 |
| MCP servers and connections | Dedicated action proof is a gap | Create/edit server and connection, scopes and tool discovery, denied access, disconnect/delete; deterministic local MCP endpoint | P1 |
| Knowledge `/knowledge` | `memory.admin.spec.ts` is a candidate, not blanket knowledge coverage | Inventory actual knowledge and memory actions; upload/search/delete and processing/failure states where supported | P1 |
| Solutions `/solutions`, `/solutions/:id` | Several lifecycle/files/runtime/backup specs are candidates | Audit existing assertions before adding; prove UI install/import, inspect dependencies, update/export/uninstall and failure recovery for supported actions | P1 |
| Audit `/audit` | Real denial generated by fetch and filtered in UI | Other filters, clear, pagination, details/links; expected audit record from a UI mutation | P1 |
| Diagnostics `/diagnostics` | Scheduler diagnostics candidate | Refresh, inspect a known failed job/event, supported recovery action and resulting status | P1 |
| Reports `/reports/roi`, `/reports/usage` | Dedicated action proof is a gap | Date/scope filters, seeded totals, drill-down/export where offered, empty and error states | P1 |
| Settings: AI tabs | `ai-model-settings.admin.spec.ts` candidate | Audit provider/model save and assignment; cover embeddings/chat/memory/instructions/usage separately, persisted edits and failed request recovery | P1 |
| Settings: connections/security | Preferred SSO/custom-claims candidates | MCP, GitHub, SSO and workflow-keys tabs separately; configuration persistence, secret handling in UI, remove/revoke; controlled callback cases | P1 |
| Settings: branding/maintenance | Theme contrast uses intercepted branding; terminology candidate | Save/reload/reset default primary color and gradient; uploaded logo; all supported maintenance actions; test global changes with isolation | P1 |
| User settings | Dedicated action proof is a gap | Basic info, security, connections, preferences, developer tabs separately; persistence; password/MFA/passkey enrollment and removal using test browser authenticators where possible | P1 |
| Shared navigation, cards, tables, dialogs, pickers | Focus/contrast/mobile tests; History picker and desktop scroll regressions | Consumer registry for each actual variant; action parity, pagination invariants, keyboard/focus, overflow/clipping and responsive contracts below | P0 |

## What each acceptance test must prove

1. **Known starting state.** Seed named records through real platform APIs.
   Check every setup response; assert fixtures exist. Never pass because a
   required button or row happens to be missing.
2. **Action through the browser.** Click, type, choose, save, execute or cancel
   using accessible roles and labels. API setup is legitimate; an API mutation
   followed by a page load does not prove the UI mutation works.
3. **Observable outcome.** Assert the specific resource/result in the UI.
   For mutations, reload or reopen to prove persistence. For permissions,
   verify both the authorized outcome and forbidden resource/direct-route
   behavior. A success toast alone is insufficient.
4. **Recovery and isolation.** Keep focused tests for failed saves, retry and
   cancel; assert no unintended mutation. Clean up owned fixtures, including
   after failure. Avoid shared global settings across concurrent tests.
5. **Appropriate depth.** One main connected journey per capability, with
   combinatorial validation rules in component/backend tests. Add browser
   regression cases for actual integration and interaction failures.

## Shared UI contracts: catch whole classes of regressions

- **Tables and cards:** inventory every list consumer and its actual variant.
  Seed enough rows to paginate. Assert changed row identities, stable
  filters/header/footer during delayed requests, correct counts and shared
  pagination presentation. Exercise row/card open, overflow actions and bulk
  selection separately. Verify actions affect the intended resource.
- **Scrolling:** short desktop lists use their content height; long lists have
  a reachable last row/action inside the intended scrolling body, with controls
  stationary. Drive wheel/keyboard scrolling rather than only reading CSS.
  Mobile uses the intended natural page flow and exposes equivalent actions.
- **Pickers:** use long labels, search and select a real option, assert the
  selected result. Test popup width independent of trigger width, viewport
  collision, focus/Escape and placement above editor/dialog overlays.
- **Dialogs:** one intended scrolling region, reachable footer, no clipped
  selected chips, focus restoration, cancel retains old data, save persists.
- **Streaming:** new messages arrive without refresh, result remains reachable,
  completion persists through back/reload, cancellation works, no layout shift
  from changing status/action widths. Test loss/recovery of transport explicitly.
- **Responsive/visual:** core journeys at desktop and 390px; layout stress at
  320px, short desktop height and wide monitor. Capture stable populated and
  empty/loading/error states for key templates in light/dark and custom
  branding. Screenshot diffs supplement functional assertions and require
  deliberate baseline review; never blindly accept all updates.

Do not run every route × role × viewport × theme combination. Cover shared
contracts systematically, then test the distinct page compositions and access
boundaries that could break independently. Add a second browser engine for
critical journeys after measuring harness compatibility; current projects use
Desktop Chrome, with some tests explicitly resizing their viewport.

## Connected fixture pack

Implement a reusable fixture builder with per-test namespaces and cleanup.
Provide an explicit persistent review mode for the debug stack, using the same
resource definitions. Automated tests must not reset or depend on the user's
review stack. Review mode updates only its own named resources and writes an
index of links and expected actions; it preserves unrelated fixtures.

Use two organizations, platform admin and member accounts, roles, private and
shared resources, long labels, and enough records for pagination. Connect:

`integration + mapping → local webhook → event → workflow → execution/result`

`Home collection → app/form/agent → workflow or conversation → history`

Include success, failure and cancellable work. Use deterministic local data and
fake external provider responses at the provider boundary while keeping Bifrost
API/storage/worker/transport real. Label simulated connection states clearly.
Real OAuth consent, external adapters and live model output get separate,
explicit acceptance checks; they cannot silently stand in for deterministic
CI coverage. Existing docs screenshot seeders are not adequate fixtures: some
are no-ops or ignore creation failures.

## Delivery batches and gates

1. **Make the first critical chain trustworthy.** Build fixture ownership and
   the coverage ledger. Replace weak form-submit and rerun checks with real
   journeys; cover session recovery/route denial, Home launch, execution
   drawer/full-page/back and mobile. Preserve existing app/public-form smoke.
2. **Complete user-facing and administration coverage.** Finish remaining P0
   journeys, then work through P1 rows in bounded groups: identity/scope;
   integration/entity/event dependencies; editors/files/tables; remaining
   settings/solutions/reports. Harden existing specs before duplicating them.
   Convert previous manual regression discoveries into durable tests.
3. **Close the launch audit.** Validate the ledger against every route, settings
   tab and offered action. Run all product browser tests on the release
   candidate plus the repository pre-PR gate. Review desktop/mobile screenshots
   and explicitly record external checks and any accepted limitations.

Keep the existing infrastructure:

- During implementation: `./test.sh client e2e <spec>` and relevant component
  tests; one test-stack command at a time.
- Required critical browser gate: `./test.sh client smoke` selects `@smoke`.
  Expand it with a measured set of real P0 journeys. Current tags cover only a
  small subset, not all management pages.
- Full product browser suite: `./test.sh client nightly`. The existing nightly
  workflow already runs this and uploads diagnostics. Expand coverage through
  that path rather than building a parallel runner.
- Before opening/queueing a PR: exact clean, current candidate must pass
  `./test.sh pre-pr`. This includes critical browser smoke, not the entire
  nightly browser suite. A redesign launch also needs the full browser run.
- Keep zero retries. Investigate failed runs with trace/video/screenshots and
  service logs; fix the product or test isolation rather than retry for green.

Estimate subsequent batches using measured test runtime, fixture effort and
product defects discovered. Seeding review data is only one part of the work;
file counts alone are not a useful estimate.

## Report the user should receive

Build a checked-in journey ledger with stable IDs, route/tab, action, priority,
role, fixture, spec/test title and proof type (real platform, external boundary
stub, UI interception). Validate that referenced specs/titles exist and that
routes/actions have an entry or an explicit reviewed exclusion.

Join the ledger to Playwright JSON results by stable journey ID and project.
Report the commit and environment, then separate:

- **Implemented and passed on this candidate**
- **Failed**, linked to trace/screenshot and owned repair
- **Implemented but not run on this candidate**
- **Missing automation**
- **External/manual acceptance outstanding**

Do not call a page “covered” because one journey passes. Do not include mock-only
UI assertions in the real-persistence total. Report mobile completion separately.
Counts and percentages must use the inventoried required journeys as the
denominator, with exclusions visible.

Example report format (illustrative rows, not current test results):

| Journey | Desktop | Mobile | Evidence / remaining gap |
| --- | --- | --- | --- |
| FORM-01: assigned member submits a saved form | Not run | Not run | Required: persisted form → real workflow result |
| EXEC-03: reopen completed execution with browser back | Not implemented | Not implemented | Required: completed status and preserved result |
| INTEGRATION-02: edit organization mapping | Not implemented | Not implemented | Required: mapping survives reload and is used by event workflow |

Launch confidence means all required journeys are implemented and green for
the candidate, known failures are resolved, visual checks are reviewed, and
external limitations are explicit. It is not a promise that automation can
prove every possible interaction or future third-party behavior.
