# SDK Bulk Update Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add obvious Update All and standards-compliant subset selection to Apps and Solutions without bypassing per-App PlatformJobs.

**Architecture:** The existing Apps batch endpoint receives explicit IDs computed from the organization-scoped unsearched list. A new Solution batch endpoint accepts explicit Solution IDs, loads their Apps in one query, and reuses the existing per-App enqueue helper. React pages own selection state and pass selection-mode behavior into their list surfaces; the existing WebSocket tracker animates accepted Apps.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, React, TypeScript, React Query, Vitest, Playwright.

---

### Task 1: Add one-request Solution batch enqueue

**Files:**
- Modify: `api/src/models/contracts/solutions.py`
- Modify: `api/src/routers/solutions.py`
- Modify: `api/tests/unit/test_solution_contracts.py`
- Modify: `api/tests/e2e/platform/test_application_sdk_update.py`

- [ ] Add a failing contract test for `SolutionSdkUpdateBatchRequest(solution_ids=[...])` and a response containing the existing per-App accepted/skipped records.
- [ ] Add a failing E2E test that submits two Solution IDs, proves actionable Apps from both enqueue, current/unavailable Apps are skipped, and the App load is one set query rather than per-Solution HTTP orchestration.
- [ ] Implement `POST /api/solutions/sdk/update` with explicit non-empty Solution IDs, authorize each Solution, load contained Apps in one query, and reuse `_sdk_update_action_skip_reason` plus `_enqueue_sdk_update_for_application`.
- [ ] Run `./test.sh tests/unit/test_solution_contracts.py tests/e2e/platform/test_application_sdk_update.py -v` and expect all selected tests to pass.
- [ ] Regenerate `client/src/lib/v1.d.ts`, run DTO/contract tripwires, and commit `feat: batch Solution SDK updates`.

### Task 2: Add Apps Update All and selection mode

**Files:**
- Modify: `client/src/pages/Applications.tsx`
- Modify: `client/src/components/applications/ApplicationListSurface.tsx`
- Modify: `client/src/components/applications/ApplicationListSurface.test.tsx`
- Add or modify: `client/src/pages/Applications.test.tsx`
- Modify: `client/e2e/applications-sdk-update.admin.spec.ts`

- [ ] Write failing component/page tests for the organization-scoped actionable count, Update All ignoring search, Select mode, full-card toggling, Select All visible, table checkboxes, Update Selected, and accepted-job tracking.
- [ ] Add a batch mutation that calls `batchUpdateApplicationSdks(ids)`, preserves selection on failure, clears it on acceptance, and reports accepted/skipped counts.
- [ ] Add toolbar controls matching Integrations: `Select`, selection count, `Select all`, `Update selected (N)`, and `Done`; place `Update all SDKs (N)` outside selection mode.
- [ ] Extend `ApplicationListSurface` with selection props. Only `canUpdateApplicationSdk` Apps are selectable; cards use `role=button`, `aria-pressed`, Enter/Space, and a visible check marker, while table rows use semantic checkboxes.
- [ ] Run targeted Vitest and `./test.sh client e2e --screenshots e2e/applications-sdk-update.admin.spec.ts`; inspect desktop/mobile captures and commit `feat: add bulk App SDK updates`.

### Task 3: Add Solutions Update All and selection mode

**Files:**
- Modify: `client/src/services/solutions.ts`
- Modify: `client/src/services/solutions.test.ts`
- Modify: `client/src/pages/Solutions.tsx`
- Modify: `client/src/pages/Solutions.test.tsx`
- Modify: `client/e2e/solutions-sdk-update.admin.spec.ts`

- [ ] Write failing service tests for the new batch endpoint and page tests for Update All ignoring search, organization scope, actionable-only full-card selection, Select All visible, direct per-card update, and partial-result messaging.
- [ ] Implement the generated-client service wrapper and one page mutation. Track every accepted App job with `useApplicationSdkUpdateJobs`; invalidate Solution aggregates after terminal updates.
- [ ] Add toolbar controls parallel to Apps and Integrations. In selection mode cards toggle as a whole and navigation/actions are suppressed; table view uses checkboxes. Keep the direct card action and existing Solution detail action.
- [ ] Run targeted Vitest and `./test.sh client e2e --screenshots e2e/solutions-sdk-update.admin.spec.ts`; inspect list, selected, in-progress, and Notification captures and commit `feat: add bulk Solution SDK updates`.

### Task 4: Verify and hand off a usable stack

**Files:**
- Modify only files required by failures attributable to this feature.

- [ ] Run `./test.sh quality api`, targeted backend tests, targeted frontend tests, `npm run tsc`, and `npm run lint`.
- [ ] Run both SDK Playwright specs with screenshots and inspect every new capture for desktop/mobile overflow, selection affordance, pending state, and contrast.
- [ ] Confirm `./debug.sh status`, seed actionable independent and Solution-managed Apps in the debug stack, and exercise Update All through the running UI.
- [ ] Commit the exact candidate, verify a clean tree, and run `./test.sh pre-pr` before opening or queueing a PR.
