# Nightly acceptance audit — 2026-09-10

Candidate: `f8cd43a8c66dbb259c497efc2c22c62fb0df9560`, clean throughout the run.

Command: `./test.sh client nightly --workers=2`

Result: **105 passed, 22 failed, 1 skipped, 0 flaky**, 128 selected cases,
592.9 seconds. This is a failed gate, not launch approval. The skipped case
is included below and requires resolution; it is not counted as accepted.
The complete HTML/JSON, first-failure screenshots, videos and traces were
retained locally under `/tmp/bifrost-nightly-f8cd43a8c-evidence/` before any
subsequent test run. These local artifacts are not committed to Git.

All rows below remain owned repair work until the exposing conditions pass.
Source review distinguishes obsolete selectors from product layout and fixture
isolation problems; a successful isolated rerun alone does not close a
concurrency or order-dependent failure.

| Spec | Case | Project | Observed status |
| --- | --- | --- | --- |
| `agents-detail-runs.admin.spec.ts` | groups run activity, expands delegated traces, and reserves raw data for Advanced | platform-admin | failed |
| `agents-detail-runs.admin.spec.ts` | keeps Overview context fixed and View all runs navigates | platform-admin | failed |
| `agents-detail-runs.admin.spec.ts` | keeps run context fixed on desktop and falls back to page scrolling | platform-admin | failed |
| `apps-publish-notification.admin.spec.ts` | queues in the dialog and reports completion through notifications | platform-admin | timedOut |
| `chat-attachments.admin.spec.ts` | browses the persistent artifact library | platform-admin | failed |
| `desktop-scroll.admin.spec.ts` | document records accept wheel scrolling at 1100px, filters true | platform-admin | failed |
| `entity-logos.admin.spec.ts` | uploads via the app settings dialog and renders on the card | platform-admin | failed |
| `entity-logos.admin.spec.ts` | uploads via the drop zone and renders on the fleet card | platform-admin | timedOut |
| `event-source-graph.admin.spec.ts` | shows Graph context and recreates the provider subscription | platform-admin | failed |
| `memory.admin.spec.ts` | enables and manages private memory | platform-admin | failed |
| `per-mapping-oauth.admin.spec.ts` | mapping table renders on integration detail page | platform-admin | failed |
| `per-mapping-oauth.admin.spec.ts` | Connect button on mapping row opens authorize URL | platform-admin | skipped |
| `policy-rules-manager.admin.spec.ts` | open manager, create rule, edit, see built-in badge, attempt in-use delete | platform-admin | timedOut |
| `policy-rules-reference.admin.spec.ts` | Files policy editor shows the rule in Insert reference dropdown | platform-admin | timedOut |
| `policy-rules-reference.admin.spec.ts` | Tables policy editor shows the rule in Insert reference dropdown | platform-admin | timedOut |
| `roles.detail.admin.spec.ts` | card → users chip → drawer → assigned → unassign | platform-admin | failed |
| `scheduler-diagnostics.admin.spec.ts` | shows capacity guidance and opens per-run logs | platform-admin | failed |
| `solution-backup-export.admin.spec.ts` | queues a scheduler-owned backup export and downloads it when completed | platform-admin | failed |
| `solution-files-link.admin.spec.ts` | Files chip appears in Contents and opens the embedded file browser | platform-admin | failed |
| `users.admin.spec.ts` | admin invites user and user registers via magic link | platform-admin | timedOut |
| `agents-owner-budget-hidden.user.spec.ts` | budget fields are not visible to non-admin users | org-user | timedOut |
| `forms.user.spec.ts` | [FORM-ACCESS-01 desktop] member cannot see or open an unassigned role-based form | org-user | failed |
| `scheduled-execution.spec.ts` | schedule a run from the workflow execute page | chromium | timedOut |

## Initial diagnosis and repair grouping

- Notification completion rendered correctly; the publish test searched the
  title wrapper instead of its named notification article.
- Graph events and scheduler schedules retain desktop/mobile representations;
  broad text selectors matched both. Use visible semantic links/rows.
- Role pagination now uses the shared `List pagination` navigation. Preserve
  assignment/unassignment behavior while asserting the current footer.
- Backup export's `Config values` substring also matched the secret-values
  checkbox. Match the intended label rather than another field's description.
- Agent Overview uses the common bounded Page content region. Its old test
  assumes a separate inner Recent activity scroller. Filter overflow at short
  desktop heights still needs functional verification and potential repair.
- The artifact touch-target measurement was taken during a layout transition;
  assert settled geometry with a condition, not a fixed sleep or looser target.
- Memory setup uses an obsolete embedding-config payload and outdated settings
  routes. Repair fixture setup and retain real memory persistence proof.
- Form-access setup failed with `Workflow already registered` under the full
  suite. Resolve workflow registration/discovery ownership before closing it.
- Remaining logo, policy editor, solution file browser, invitation and schedule
  failures need source/trace diagnosis. They are not dismissed as unrelated.

A separate explicit compilation of all `client/e2e/**/*.ts` found nine errors
in three files (docs seeders' APIResponse type, scheduled-execution's Page import,
and the V2 runtime fixture's window declaration). The repair is separate from
browser outcomes; normal source-only client compilation had not covered them.

## First verified repair subset

The following targeted run passed all seven selected tests (including setup)
with two workers, zero retries, zero skips, and zero failures:

```sh
./test.sh client e2e e2e/apps-publish-notification.admin.spec.ts e2e/event-source-graph.admin.spec.ts e2e/scheduler-diagnostics.admin.spec.ts e2e/solution-backup-export.admin.spec.ts e2e/roles.detail.admin.spec.ts --workers=2
```

This verifies the five selector/footer repairs while preserving real publish,
assignment/unassignment, scheduler inspection, and backup export/download
outcomes. Graph provider traffic remains intercepted by its existing test.
Explicit TypeScript compilation of every `client/e2e/**/*.ts` now passes after
the three type fixes; ESLint passed for all eight modified browser/helper files.
These are targeted iteration results. All remaining failures are still owned,
and the full nightly must pass again on the final clean candidate.

## Second verified repair subset

Four more original failures have targeted repairs; full-suite revalidation remains pending:

- Short desktop document pages previously compressed records to roughly 30px with filters open. At desktop heights up to 700px, the bounded content workspace now scrolls filters, records and pagination together; the header/search remain fixed. Taller desktops retain the independent records pane. Eight width/height/filter combinations now assert wheel scrolling and a readable last-record value in the viewport. The 1100×600 filtered screenshot was reviewed directly.
- Member form cases share a registered workflow fixture. Keep that group in default mode so fully-parallel test scheduling does not register it repeatedly within the same worker. All three cases passed together with two workers.
- Artifact touch targets retain the 44px minimum and wait for settled geometry. The video fixture now serves a real, tiny synthetic MP4 instead of invalid header bytes that triggered the native player error. This remains intercepted artifact UI evidence, not real chat persistence.
- The member budget test now seeds and cleans up a private agent owned by that member. The former admin-owned agent allowed running, but not editing, so Settings was correctly absent.

```sh
./test.sh client e2e --screenshots e2e/desktop-scroll.admin.spec.ts e2e/forms.user.spec.ts e2e/chat-attachments.admin.spec.ts e2e/agents-owner-budget-hidden.user.spec.ts --workers=2
# 19 passed, zero skipped/flaky/failed; includes setup.
./test.sh client e2e e2e/desktop-scroll.admin.spec.ts --grep 'document records accept wheel scrolling' --workers=2
# 9 passed including setup, after adding explicit readable-record screenshot/assertion.
./test.sh client unit src/pages/TableDetail.test.tsx src/components/tables/DocumentRecordList.test.tsx
# 1 file / 7 passed: only TableDetail.test.tsx exists and matched this command.
```

Client source TypeScript, changed-browser-spec TypeScript and scoped ESLint passed. These results close targeted repairs for nine of the original 22 failing cases across the first two subsets; 13 original failures and the serial-dependent skipped case still require repair/verification. Additional inventory gaps remain separate from these historical nightly failures.

## Third repair iteration and runner isolation

A consolidated 28-test iteration selected agent detail, logos, memory, policy/mapping, solution files, users, scheduling and the new real-chat journey. It finished with **20 passed, 7 failed, 1 serial-dependent test not run**, zero retries. Log: `/tmp/bifrost-nightly-repairs-fourth.log`.

New passing historical repairs in that run: delegated activity navigation/mobile expansion, Overview bounded scrolling, app and agent logo upload/list rendering, memory settings/instructions plus real MCP memory save/remove, table policy reference insertion, solution-scoped Files navigation, and workflow scheduling from the execution form. The logo tests now name their list-row assertions accurately. The solution Files journey also opens the seeded folder and verifies its file, rather than merely finding a browser container.

Five original nightly failures remained after these targeted passes: agent run-list short-height layout, per-mapping OAuth, policy manager, file policy reference, and invitation registration. The dependent OAuth popup case remains unverified. This iteration also exposed an unanchored Create-user selector matching the Created column and a missing streaming protocol in the local AI fixture used by the new chat test. Subsequent fixes are not counted as passing until their next run finishes.

An earlier attempt (`/tmp/bifrost-nightly-repairs-third.log`) failed in setup with `ENOTFOUND api`, before its 20 product tests ran: an overlapping agent test command reset the same Docker stack. The conflicting runner was stopped. `test.sh` now acquires a shared stack lock before dispatch for browser, backend, lifecycle, quality and pre-PR commands; read-only status/help and host-only client unit tests remain available. `scripts/lib/test_stack_lock_test.sh` proves conflicting browser/backend/reset/pre-PR commands fail before mutating the stack, and the pre-PR repository checks include it. The existing pytest orphan-runner guard is retained.

The app-logo callback now invalidates list/detail/Home logo metadata, because a cached `logo_url: null` suppresses the image endpoint even after a version bump. A component test verifies actual query invalidation while preserving an unsaved settings draft. The latest component run passed 30 tests across AppInfoDialog, AgentRunsTab and AgentDetailPage. The local AI fixture's JSON and SSE protocol checks passed two backend unit tests; real chat still needs its browser result.

### Targeted repair closure and new persisted journeys

Fifth iteration: **18 passed, 5 failed, zero skipped**, including repaired
agent short-height scrolling, invitation registration and both per-mapping OAuth
cases. Sixth iteration: **4 passed, 3 failed, zero skipped**, including both policy
reference cases and the complete workflow API-key lifecycle.

The eighth iteration (`/tmp/bifrost-acceptance-eighth.log`) selected the remaining
policy manager case and the new chat/document journeys: **4 passed**, including
setup; zero failures, skips or retries. The seventh run first established that
real document creation worked, but exposed duplicate assertions across hidden
card/table layouts and conversation previews. The corrected tests select table
cells and a named assistant-message article, and match the built-in badge exactly.
Document JSON is pasted through the browser clipboard into the labelled Monaco
textbox, avoiding synthetic typing that inserted an extra closing brace.

All 22 original nightly failures now have subsequent targeted passing evidence.
This does not certify the combined suite or final candidate. The new local-provider
chat, table/document lifecycle and workflow-key lifecycle are bound in the ledger
(26 journeys total); `inventoryComplete` remains false. Parent reviewed the final
chat screenshot: persisted user/assistant text and composer are visible without
clipping at 1280×720. This is desktop chat evidence, not a mobile sign-off.

The assistant-message component passed its targeted tests. New MCP settings unit
coverage initially had two assertion failures and remains under repair. Account
passkey, MCP settings, branding UI persistence and operational reports are pending
parent execution; authored tests are not counted as passing coverage.

### Settings and resources acceptance iteration

`/tmp/bifrost-settings-resources-second.log`: **4 passed, 3 failed, zero skipped**
(including setup). Passkey registration/reload/removal uses a test-owned account,
Chromium virtual authenticator, real WebAuthn verification and persisted credential
queries. Entity Management assigns/reassigns/unassigns a selected app and verifies
an unselected app stays global. Both are now ledger-bound (28 journeys).

Branding's actual UI color/terminology save/reload/reset also passed. Parent
reviewed its desktop screenshot and the Entity Management screenshot. Branding
showed a blue action despite the reset preview; this may be an unfinished color
transition. A new assertion now requires the actual
primary action to settle to the default theme color after reset. That strengthened
assertion is pending, so this journey is not yet added to the ledger.

Knowledge created its document (201 plus visible saved row), but Playwright's
response-body capture did not finish; the revised test verifies persisted content
through a separate API read. MCP fixture creation incorrectly used a nonexistent
`mcp` agent channel and has been corrected to `chat`. Reports seeded a real
execution and chat usage, then failed on the obsolete chart title “Executions Over
Time”; the current control is the Execution time-window selector. These repairs
remain pending browser verification.

The MCP settings picker also exposed a product defect: admin configuration used
the globally filtered runtime inventory. Its REST inventory now allows platform
admins to inspect blocked tools and configure while MCP is disabled. Runtime
callers retain filtering, including superusers outside configuration mode; a
non-admin cannot request this bypass. All **33 tool-access unit tests** and **4
settings-router boundary tests** passed. Live settings acceptance is still pending.

New page-level units passed: MCP **4**, Usage Reports **3**, GitHub **3**. GitHub's
browser journey is explicitly intercepted at `/api/github/*`; no live GitHub
configuration or provider authentication is claimed. Source TypeScript/scoped
frontend lint and strict TypeScript for the current settings/resource specs passed.

### Settings/resource third run

`/tmp/bifrost-settings-resources-third.log`: **5 passed, 5 failed, zero skipped**
(including setup). Branding now also proves the actual primary action settles to
the default color after reset; the earlier blue screenshot was transient. Files
proves downloaded bytes and deletion, Home catalog proves app/form launch and
search/type/org filtering, and SSO proves provider configuration/edit/removal and
preferred-provider persistence without an external login. These four journeys are
now bound: **32 ledger journeys**, with inventory completion still false.

The remaining failures were an obsolete GitHub heading role, Knowledge rich-text
paragraph serialization compared byte-for-byte against input, MCP Connect also
matching Disconnect, MCP tool-description text matching another tool's identifier,
and the dashboard time window being a radio control rather than a combobox. The
fourth run verifies those corrected contracts and the new collection-authority
journey. No new passes are assumed before that run completes.

API Pyright/Ruff passed after the MCP inventory and fixture changes: zero errors
or warnings. Local provider fixture unit tests passed **7/7**, including OAuth
code exchange, refresh compatibility and existing chat response behavior.

Files scope correction: the current explorer does not offer rename/move controls.
The launch inventory's rename/move requirement is not a supported current UI action;
API/editor rename contracts remain separately tested. The new explorer journey
covers its actual download/delete actions without inventing new UI capabilities.

### Settings/resources fifth iteration

`/tmp/bifrost-settings-resources-fifth.log`: 5 passed (including setup), 3 failed. Knowledge document CRUD, Home collection ownership/access, populated operational reports, and GitHub settings with intercepted external responses passed. The ledger now binds 36 journeys; inventory remains incomplete. Remaining failures: MCP OAuth callback used stale API public URL, MCP picker exit animation left duplicate options during the next selection, and workflow metadata test attempted an unsupported GET-by-ID route. Repairs use Compose reconciliation, waiting for the dismissed picker, and the supported workflow inventory endpoint. No final full-suite claim.

### Settings/resources sixth iteration

`/tmp/bifrost-settings-resources-sixth.log`: all 4 tests passed including setup. Real MCP personal OAuth callback and disconnect, MCP settings save/reload/reset/restore, and workflow metadata persistence/search/navigation passed. API container reconciliation applied the test-only public URL; the previous browser run had retained its old environment. Ledger: 39 journeys with targeted passing evidence, not a full candidate gate.

### Agent review persistence

`/tmp/bifrost-agent-review-acceptance-first.log`: 2 passed including setup. A completed run from the local model fixture is flagged through the API; the real UI saves a review note, reloads it, marks the run good, verifies persisted verdict/note and an empty review queue after reload. This replaces the previous empty-queue smoke. Ledger now binds 40 targeted passing journeys.

### V1 included controls matrix

`/tmp/bifrost-v1-controls-first.log`: 6 passed including setup, existing real workflow/navigation journey, and four new viewport/theme cases. Each controls case exercises preview and published runtime with checkbox state, select state, dialog open/close and viewport bounds, bare-child CommandDialog selection, tab switching and table cells. At 320px no document horizontal overflow. Parent reviewed the mobile dark screenshot. Ledger: 41 targeted passing journeys (a matrix remains one journey). Backfill component validation: 18 passed in `/tmp/bifrost-backfill-component-validation.log`.

### Resource management first iteration

`/tmp/bifrost-resource-management-first.log`: 2 passed including setup, 2 failed. Integration create/edit/logo/card-selection/table-navigation/delete passed with API deletion and reload verification; ledger now binds 42 targeted passing journeys. Event source and MCP connection records were persisted, but ambiguous subscription button and obsolete organization-count assertions failed. Corrected selectors are under validation with solution lifecycle in `/tmp/bifrost-resource-management-second.log`; no passing claim yet.

### Resource management third iteration

`/tmp/bifrost-resource-management-third.log`: 2 passed including setup, 3 failed. Event source create/subscription/edit/reload/deactivate/delete passed; ledger now 43 targeted passing journeys. MCP matched global update text via an inexact Available locator. Workspace editor expected a bare filename although the current workspace tree includes scope in the accessible name; obsolete unsaved-label assertions also removed after source review. Solution Reactivate exposed a product contract defect: zip install omitted required reactivate query flag and returned inactive_install_exists. Product repair is in progress, not waived or hidden by a test change. Current fourth run excludes solution until that repair and includes new chat-instructions/pricing journeys.

### Management/settings fourth iteration

`/tmp/bifrost-management-settings-fourth.log`: 2 passed including setup, 3 failed. Chat instructions UI save/API persistence/reload passed with original prompt restoration; ledger 44 targeted passing journeys. Pricing fixture expected six decimals against existing Numeric(10,4) storage; adjusted to four-decimal exact values. MCP delete succeeded but final heading matched No MCP servers as well; exact heading now used. Global editor uses one unnamed Monaco model rather than app-editor path identities; test now observes that actual contract and still verifies both named files through API/reload. Solution reactivation fix passes 101 focused service/component/page tests and is selected for the fifth browser batch, along with the connected fixture idempotence/form journey.

### Management batch fifth iteration

`/tmp/bifrost-ui-acceptance-iterations/management-fifth.json`: 4 passed including setup, 2 failed. MCP management, AI pricing, and global workspace editor now have passing real-platform UI/API/reload evidence. Ledger: 47 journeys. Review-pack seed exposed invalid Python identifiers from hyphenated namespaces; solution reactivation still remains inactive and is under investigation. These are not passing evidence; full nightly and clean-candidate pre-PR remain pending.

### Connected review and solution lifecycle closure

Seventh management run: 3 passed including setup, 1 failed. Solution uninstall/reactivate/delete and the idempotent connected review pack now pass real-platform UI/API/reload evidence. The pack proves Home form -> integration mapping -> workflow result and webhook -> event delivery -> history result. Ledger: 49 journeys. MCP catalog retrieval works; the browser assertion incorrectly expected description on the public catalog DTO, which exposes schema/name/state but no description. The corrected case is running with form structure, account onboarding, and tuning apply. Protocol unit regression: 11 passed. Maintenance and Config page tests: 13 passed. No final candidate gates have passed yet.

### Eighth/ninth closure runs

`closure-eighth.json`: MCP catalog and mixed tuning Apply passed; the latter controls proposal/list responses but persists Apply through the real backend. `account-role-ninth.json`: password settings change and independent new-password sign-in passed; existing role-user assignment also passed. Ledger: 52 journeys. Account recovery sign-in exposed Login maxlength truncating formatted recovery codes. Role-form assignment needs browser response-status assertion instead of eagerly reading a discarded response body. Forms deletion fixture was invalid because the deleted field remained a required workflow input; valid target workflow fixture is now in place. No timeout/retry increases.

### Targeted closure complete

`final-closure-tenth.json`: 6 passed including setup, 1 failed (form deactivation expectation). `form-final-eleventh.json`: 2 passed including setup; the form remains visible as Disabled after deactivation, verified after reload. Ledger: 56 targeted passing journeys. Login recovery-code length and mobile header passkey prompt were repaired with component regressions. Public debug form/webhook execution and Home/execution 1440px/390px screenshots passed review. Source client tsc/lint and strict changed-e2e tsc passed; API quality passed with zero errors/warnings. Full candidate nightly and clean pre-PR gates remain required.


## Clean-candidate nightly and repairs

Full nightly on `43a1a3fab44a886b6615e308bc7374cffbdaa1f5` selected 153 tests: **150 passed, 3 failed, 0 skipped, 0 retries**. Private artifacts are preserved under `/tmp/bifrost-ui-acceptance-iterations/nightly-clean-43a1a3f`.

- **SECURITY-03:** cookie-only bootstrap exposed competing refresh paths in AuthProvider and the API client. A deterministic component regression demonstrated two concurrent refresh requests before the repair. AuthProvider now shares the existing API/SDK refresh lock; the regression and API-client suite pass (22 tests). The browser test retains cookie-only bootstrap rather than bypassing the problem with injected local storage.
- **Agent desktop overflow:** browser measurements captured 4,133px of outer overflow during the route transform, despite correctly bounded inner scroll containers. The route reveal now uses opacity only. The Runs browser test holds the entrance animation mid-flight to exercise containment; Overview and Runs desktop/mobile scroll checks pass.
- **EVENT-MGMT-01:** an empty source list renders equivalent header and empty-state create actions. The test now intentionally selects the first/header action rather than assuming the accessible name is unique.

`./test.sh client e2e --screenshots --workers=1 e2e/account-onboarding-acceptance.admin.spec.ts e2e/agents-detail-runs.admin.spec.ts e2e/event-source-management-acceptance.admin.spec.ts` passed **11/11** after the repairs. This is targeted evidence; the final complete nightly and pre-PR gate remain required on the repaired candidate.


### Repaired candidate full-run follow-up

Nightly on `df3d94891323c8f7fcfcbeb39e153ee130fbc3e8` selected 153 tests: **150 passed, 3 failed, 0 skipped, 0 retries**. All three original failures passed. This run exposed two overlong test flows and an imprecise redirect assertion under substantial shared-host contention.

- Solution lifecycle is now three independently seeded browser actions (uninstall/filter, reactivate, permanent delete). Each retains the standard 30-second action limit; setup has a separate 30-second fixture budget. The ledger requires all three for SOLUTION-LIFECYCLE-01.
- The global editor helper no longer performs a second full navigation immediately after the test's reload. Save, switch, reload, and both persisted file contents remain checked.
- The login redirect test now requires `/workflows` exactly with a web-first assertion. Its former optional regex matched `/login` too, and waiting for a document load could race route navigation.
- The Sidebar integration fixture now supplies a populated read-only collection. Empty shared collections intentionally remain hidden; SidebarCollections tests preserve that contract.

Focused browser verification of solution lifecycle, workspace editor, and authentication passed after these repairs. Sidebar/SidebarCollections component tests passed 8/8, and strict TypeScript checking passed. The full Vitest attempt was interrupted after revealing the sidebar fixture defect during severe shared-host load; it is not counted as passing. The mandatory clean-candidate pre-PR gate and complete nightly remain required.


### Pre-PR component gate follow-up

Pre-PR on `4c623809a` passed client TypeScript/lint, then stopped at Vitest: **2,852 passed, 3 failed across 487 files**. Backend and browser gate stages had not run.

- StandaloneV2App's opening-state test expected ASCII `...` while the shared opening status uses `…`. Its status assertion and test name now match the actual opening experience.
- UsageReports dynamically imported the page inside the first five-second test. During the complete suite that import timed out, then its late render contaminated the next test. Static module import moves transformation/import into test-file setup; retry and cached-content assertions are unchanged. The original UsageReports file passed isolated, while the stale loading label reproduced.
- Both repaired files passed their targeted 20-test run. Final pre-PR and complete nightly are still required on the next clean candidate.


### Backend contract and live-service closure

Pre-PR reached backend unit checks after all 2,855 component tests passed. Backend unit findings were repaired:

- Integration manifest golden includes the intentional nullable description field.
- Five newly exposed React exports route to `react` during V1-to-V2 migration and have platform reference sections; a rewrite regression preserves that import boundary.
- HomeCollection is explicitly classified as an owner/shared identity record. Existing unit/live Home tests enforce owner/admin/audience boundaries and prove collection membership grants no resource access.
- CLI/OpenAPI generated appendices include the new description, logo, and Home endpoints; mirrors are synchronized.
- Mirror parity and public namespace checks moved from skipped Docker pytest cases to `scripts/check_skill_mirrors.py`, enforced by local pre-PR and CI. The non-enforcing, always-true git staleness test was removed; manifest coverage and hard generated freshness remain.

The repaired backend unit/contract lane passed **5,981 tests**, with no skips (21 slow cases remain excluded by the standard unit marker).

The first complete live backend run selected 1,824 tests and finished **1,821 passed, 2 failed, 1 skipped** in 41 minutes. Both failures exposed missing `description` in MCP integration create/update signatures and DTO forwarding; those tools are repaired with focused wrapper coverage. The skipped CLI round-trip test expected obsolete token stdout; it was deleted. Current successful login/storage mechanics remain in `test_cli_login_ephemeral.py`, live token issuance/MFA in `test_auth.py`, and real CLI MFA-refusal/env-token transport in `test_cli_ephemeral_login.py`. The default MFA requirement is now an assertion rather than a conditional skip, and token-bearing failure output was removed.

Focused MCP parity, wrapper, and CLI live verification passed **69/69**. These are iteration results; the final clean-commit pre-PR and complete nightly gates remain required.

### Clean candidate gate and final empty-state selector repair

`a04e170037101656ceaf3bdea0d9e61433120fe3` passed the complete clean-current-main pre-PR gate: 2,855 component tests, 5,983 standard-lane backend unit tests, 1,823 backend live-service tests, 14 zero-retry browser smoke tests, static checks, and production builds. The unit lane excludes 21 slow cases by its standard marker; there were no test skips in these completed lanes.

The subsequent 155-test nightly finished **154 passed, 1 failed, zero skipped/retried**. The remaining event-source lifecycle failure was an ambiguous page-heading selector: the empty state adds `No Event Sources`, which also matches a substring query for `Event Sources`. The assertion now targets the exact level-one page heading. Empty-state creation and every lifecycle/persistence assertion remain intact. Earlier solution, editor, auth, and animated-layout repairs passed in full-suite order.

Parent reviewed fresh Home and execution screenshots at 1440×1000 and 390×844 and exercised the connected debug form/webhook review pack successfully. The final selector repair requires targeted empty-list validation and a new clean-candidate gate/nightly; the passing pre-PR result above belongs only to `a04e17003`.

Targeted empty-list validation passed: `./test.sh client e2e event-source-management-acceptance.admin.spec.ts` completed setup and the full lifecycle (2/2, no retries). The new clean-candidate pre-PR/nightly gates remain required.

### Component import boundary audit

Pre-PR on `d486d6f8c` passed client type/lint checks, then stopped with 2,852 component tests passed and three failures: ROIReports first-test import timeout and subsequent duplicate rendering, plus FormShareDialog's combined private-link/publication/options/unpublish test exceeding five seconds under full-suite load. The affected files passed isolated (15 tests), confirming that full-suite conditions exposed the issue.

ROIReports now imports at test-file setup. An audit found 26 additional page/component tests with the same unnecessary first-render dynamic import and no reset/doMock requirement; their tested-component imports are now static too. Existing mocks, test assertions, and timeouts remain. FormShareDialog's long case is split into three independently seeded contracts; URL input uses paste because per-character typing is not the behavior under test. All existing assertions are preserved.

The repaired report/sharing/shared-component group passed 126 tests; the 16 page files passed 203 tests. The next clean candidate must still pass complete pre-PR and nightly gates. No product source changed in these harness repairs.

### Deployment observation deadline

`03701ea27` passed all 2,857 component tests, 5,983 standard-lane backend unit tests, and static checks. The backend live suite completed with 1,820 passed and three deployment-wait failures after 66 minutes. All three were the helper's 30-second terminal-state deadline, not failed jobs: app table resolution, app-removal redeploy, and vendored workflow deployment.

Read-only inspection of the durable job records confirmed successful completion for the corresponding job IDs, with approximately 31, 41, and 33 seconds from enqueue to completion. The tests observed one artifact-write phase and two still-queued legacy deployment projections at their deadlines. The stack remained healthy. No global repository scan or accidental Node build was found; these fixtures use prebuilt app output. A fresh-process registry import alone took 9.24 seconds on the shared host, and asynchronous jobs include process startup and artifact work.

The user explicitly approved aligning deployment observation to the existing 60-second installation deadline, provided real issues are not masked. This changes only how long the test observes a real job: terminal failures still fail immediately, all result/persistence assertions remain, and no retries are added. This is functional acceptance, not a claim that deployments meet a 30-second latency target. The next candidate still requires full pre-PR and nightly verification.

The three failing cases passed isolated before the change (112.72 seconds total) and after the approved helper change (112.44 seconds total). Their table-resolution, app-removal, and vendored-workflow result assertions all remain intact.

### Shared-host component concurrency

After merging current main (`668b2676a`) into the review branch, candidate `f776b813e` passed frontend type/lint checks but its component gate finished 2,853 passed and four failed. Knowledge, AIModelSettings, and CollectionEditor interaction tests exceeded their five-second limits; the timed-out collection test continued into the next test and contaminated its audience assertion. Host load was approximately 58 on eight CPUs.

The affected files passed 17/17 with `VITEST_MAX_WORKERS=1`. Their source and assertions were left unchanged. The local client-check Compose service now forwards Vitest's existing optional worker override, allowing the full pre-PR suite to run serially on this contended host while retaining the configured default elsewhere. This does not alter timeouts, retries, selected tests, or CI's default concurrency. The next full pre-PR command is `VITEST_MAX_WORKERS=1 ./test.sh pre-pr`; final nightly remains required on the same clean commit.

### Stable log pagination

Candidate `7851f67af` passed all 2,857 component tests with the serial worker override, API quality checks, and 5,984 standard-lane backend unit tests. Its live backend suite finished 1,822 passed and one failed: log pagination repeated an ID across pages. All three deployment cases passed with the approved observation deadline.

The log list used timestamp-only ordering and numeric offsets, which cannot maintain a stable position across equal timestamps or newly arriving rows. It now orders by timestamp and row ID and issues a cursor containing both; legacy numeric offsets remain accepted. Cursor decoding preserves the timestamp instant and rejects malformed row identities. The live regression owns five equal-timestamp rows, inserts newer and same-timestamp rows between requests, and proves every original row appears exactly once across the remaining pages.

`./test.sh tests/unit/repositories/test_execution_logs_list.py tests/e2e/test_execution_logs_list_endpoint.py -v` passed 35 tests. The repair still requires full clean-candidate pre-PR and nightly verification.
