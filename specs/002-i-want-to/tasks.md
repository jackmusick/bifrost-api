# Tasks: Workflow Engine and User Code Separation

**Input**: Design documents from `/specs/002-i-want-to/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are included per Constitution Principle IV (Test-First Development)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- Workflows project root: `/workflows/`
- Engine code: `/workflows/engine/`
- Workspace code: `/workflows/workspace/`
- Tests: `/workflows/tests/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Backup existing structure, create new folder organization

- [ ] T001 Backup existing workflows directory structure to `/workflows-backup` for rollback capability
- [ ] T002 Create new folder structure: `/workflows/engine/`, `/workflows/workspace/`, `/workflows/scripts/`
- [ ] T003 [P] Create `.github/workflows/` directory if not exists

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Move existing `/workflows/shared/` to `/workflows/engine/shared/` (preserve all imports)
- [ ] T005 Move existing `/workflows/execute.py` to `/workflows/engine/execute.py`
- [ ] T006 Move existing `/workflows/function_app.py` to `/workflows/engine/function_app.py`
- [ ] T007 Move existing `/workflows/admin/` to `/workflows/engine/admin/`
- [ ] T008 Move existing `/workflows/data_providers/` (built-in) to `/workflows/engine/data_providers/`
- [ ] T009 Move existing `/workflows/workflows/` (current custom workflows) to `/workflows/workspace/workflows/`
- [ ] T010 [P] Update all import statements in `/workflows/engine/` to reflect new `engine.` prefix
- [ ] T011 [P] Update `function_app.py` to import from `engine.` namespace
- [ ] T012 Create AuditLog table schema in `/workflows/engine/shared/init_tables.py`
- [ ] T013 Verify existing workflows still function after restructure (smoke test)

**Checkpoint**: Foundation ready - repository restructured, all existing code migrated

---

## Phase 3: User Story 1 - Developer Writes Workflow Code in Protected Workspace (Priority: P1) 🎯 MVP

**Goal**: Prevent developers from accidentally modifying `/engine` code through GitHub Actions validation

**Independent Test**: Fork repo, create workflow in `/workspace`, attempt `/engine` modification, verify GitHub Action blocks commit while `/workspace` changes succeed

### Tests for User Story 1

**NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T014 [P] [US1] Contract test for GitHub Action in `/workflows/tests/contract/test_github_action_protection.py` - test that action detects `/engine` modifications
- [ ] T015 [P] [US1] Integration test for fork workflow in `/workflows/tests/integration/test_developer_workflow.py` - test full developer commit flow

### Implementation for User Story 1

- [ ] T016 [US1] Create GitHub Action workflow file `.github/workflows/protect-engine.yml` with tj-actions/changed-files integration
- [ ] T017 [US1] Configure action to detect changes in `/engine/**` path with `fetch-depth: 0`
- [ ] T018 [US1] Add bot detection logic (allow `upstream-sync[bot]`, `github-actions[bot]`)
- [ ] T019 [US1] Add error message formatting with `::error` workflow command syntax
- [ ] T020 [US1] Set timeout to 2 minutes for fast failure
- [ ] T021 [US1] Test GitHub Action locally using `act` or by creating test PR
- [ ] T022 [US1] Create CODEOWNERS file `.github/CODEOWNERS` with `/engine/** @security-team` (optional enhancement)
- [ ] T023 [US1] Update repository README with developer guidelines pointing to `/workspace` folder

**Checkpoint**: At this point, GitHub Actions block all unauthorized `/engine` modifications

---

## Phase 4: User Story 2 - Workflow Engine Executes Workspace Code Safely (Priority: P2)

**Goal**: Prevent workspace code from importing engine modules at runtime and enforce organization isolation

**Independent Test**: Write workspace code that attempts engine imports, verify ImportError raised; test cross-org access denied

### Tests for User Story 2

- [ ] T024 [P] [US2] Contract test for import restrictions in `/workflows/tests/contract/test_import_restriction.py` - verify blocked imports raise ImportError
- [ ] T025 [P] [US2] Integration test for workspace isolation in `/workflows/tests/integration/test_workspace_execution.py` - test org context enforcement
- [ ] T026 [P] [US2] Integration test for cross-org access denial in `/workflows/tests/integration/test_cross_org_isolation.py`

### Implementation for User Story 2

- [ ] T027 [P] [US2] Create import restrictor module `/workflows/engine/shared/import_restrictor.py` implementing `MetaPathFinder`
- [ ] T028 [US2] Define `BLOCKED_PREFIXES` tuple: `('engine.', 'shared.')` in import restrictor
- [ ] T029 [US2] Define `ALLOWED_SHARED_EXPORTS` set: `{'shared.decorators', 'shared.context', 'shared.error_handling', 'shared.models'}`
- [ ] T030 [US2] Implement `find_spec()` method with stack inspection to detect workspace imports
- [ ] T031 [US2] Add clear error messages directing developers to public API
- [ ] T032 [US2] Create `install_import_restrictions()` function with workspace path parameter
- [ ] T033 [US2] Update `/workflows/engine/function_app.py` to install import restrictions at startup (before workspace discovery)
- [ ] T034 [US2] Pass `WORKSPACE_PATH` to install function: `os.path.join(os.path.dirname(__file__), 'workspace')`
- [ ] T035 [P] [US2] Create AuditLogger class in `/workflows/engine/shared/audit.py` with `log_function_key_access()`, `log_cross_org_access()`, `log_import_violation_attempt()`
- [ ] T036 [US2] Integrate audit logger with import restrictor to log violation attempts
- [ ] T037 [US2] Update organization context loading in `/workflows/engine/shared/middleware.py` to enforce org validation even with function key auth
- [ ] T038 [US2] Test import restrictions with sample workspace code attempting blocked imports

**Checkpoint**: At this point, workspace code cannot import engine modules, org isolation enforced

---

## Phase 5: User Story 3 - Developer Tests Workflows Locally (Priority: P3)

**Goal**: Enable local development with Azurite emulator, seed data, and tiered authentication

**Independent Test**: Run seed script, start Functions locally, execute workflow with function key auth, verify org context loaded

### Tests for User Story 3

- [ ] T039 [P] [US3] Integration test for authentication flow in `/workflows/tests/integration/test_auth_flow.py` - test function key and Easy Auth priorities
- [ ] T040 [P] [US3] Integration test for Azurite seed data in `/workflows/tests/integration/test_seed_data.py` - verify test orgs/users created
- [ ] T041 [P] [US3] Contract test for tiered auth in `/workflows/tests/contract/test_tiered_authentication.py` - verify auth priority order

### Implementation for User Story 3

- [ ] T042 [P] [US3] Create Azurite seed script `/workflows/scripts/seed_azurite.py` using `azure-data-tables`
- [ ] T043 [US3] Implement organization seeding (2-3 test orgs: active/inactive)
- [ ] T044 [US3] Implement user seeding (3-5 users: PlatformAdmin, OrgUser roles)
- [ ] T045 [US3] Implement configuration seeding (5-10 entries: global + org-specific)
- [ ] T046 [US3] Add idempotent upsert pattern (check before inserting)
- [ ] T047 [US3] Add execution time reporting (<5s target)
- [ ] T048 [P] [US3] Create authentication service in `/workflows/engine/shared/auth.py` with `AuthenticationService` class
- [ ] T049 [US3] Implement `_authenticate_function_key()` method (check `x-functions-key` header or `code` query param)
- [ ] T050 [US3] Implement `_authenticate_user()` method (decode `X-MS-CLIENT-PRINCIPAL` Base64 JSON)
- [ ] T051 [US3] Implement `authenticate()` method with tiered priority (function key → user auth → 403)
- [ ] T052 [US3] Create `FunctionKeyPrincipal` and `UserPrincipal` dataclasses
- [ ] T053 [US3] Implement `_audit_function_key_usage()` method to log privileged access
- [ ] T054 [US3] Create `@require_auth` decorator for Azure Function endpoints
- [ ] T055 [US3] Update `/workflows/engine/shared/middleware.py` to use new authentication service
- [ ] T056 [US3] Replace existing `load_organization_context()` caller extraction logic with principal-based auth
- [ ] T057 [US3] Update execute_workflow endpoint to use `@require_auth` decorator
- [ ] T058 [US3] Test local development flow: `python scripts/seed_azurite.py` → `func start` → curl with function key
- [ ] T059 [US3] Document local development setup in repository README (link to quickstart.md)

**Checkpoint**: All user stories complete - developers can commit safely, workspace code isolated, local development enabled

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T060 [P] Add unit tests for import restrictor in `/workflows/tests/unit/test_import_restrictor.py`
- [ ] T061 [P] Add unit tests for authentication service in `/workflows/tests/unit/test_auth_service.py`
- [ ] T062 [P] Add unit tests for audit logger in `/workflows/tests/unit/test_audit_logger.py`
- [ ] T063 Create documentation in `/workflows/docs/workspace-api.md` describing public API
- [ ] T064 Create migration guide in `/workflows/docs/migration-guide.md` for existing workflows
- [ ] T065 [P] Update quickstart.md validation with real paths and commands
- [ ] T066 Add performance benchmarks (import restriction <50ms, GitHub Action <10s, seed script <5s)
- [ ] T067 [P] Create example workspace workflows in `/workflows/workspace/examples/`
- [ ] T068 Security review: Audit log retention policy, function key rotation procedure
- [ ] T069 Create troubleshooting guide in `/workflows/docs/troubleshooting.md`
- [ ] T070 Final smoke test: Deploy to staging, verify all protections active, test end-to-end flows

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3-5)**: All depend on Foundational phase completion
  - User Story 1 (P1): Can start after Foundational - Independent
  - User Story 2 (P2): Can start after Foundational - Independent (integrates with middleware)
  - User Story 3 (P3): Can start after Foundational - Builds on US2 auth framework
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories - Pure GitHub Actions protection
- **User Story 2 (P2)**: Independent but enhances runtime security (complements US1)
- **User Story 3 (P3)**: Uses authentication framework from US2 but can be implemented independently

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Import restrictor before function_app integration (US2)
- Auth service before middleware updates (US3)
- Seed script before local testing documentation (US3)

### Parallel Opportunities

- **Phase 1**: T001-T003 all [P] (different operations)
- **Phase 2**: T010-T011 [P] (import updates in different modules)
- **Phase 3**: T014-T015 [P] (separate test files)
- **Phase 4**: T024-T026 [P] (separate test files), T027 can start while tests written, T035 [P] (separate audit module)
- **Phase 5**: T039-T041 [P] (separate test files), T042 [P] (independent seed script), T048 [P] (independent auth module)
- **Phase 6**: T060-T062 [P] (unit tests), T063-T069 [P] (documentation)

**Once Foundational complete**: US1, US2, US3 can proceed in parallel with separate developers

---

## Parallel Example: User Story 2

```bash
# Launch all tests for User Story 2 together:
Task: "Contract test for import restrictions in /workflows/tests/contract/test_import_restriction.py"
Task: "Integration test for workspace isolation in /workflows/tests/integration/test_workspace_execution.py"
Task: "Integration test for cross-org access denial in /workflows/tests/integration/test_cross_org_isolation.py"

# Launch parallel implementation tasks:
Task: "Create import restrictor module /workflows/engine/shared/import_restrictor.py"
Task: "Create AuditLogger class in /workflows/engine/shared/audit.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (backup + folder structure)
2. Complete Phase 2: Foundational (migrate all code to /engine and /workspace)
3. Complete Phase 3: User Story 1 (GitHub Actions protection)
4. **STOP and VALIDATE**: Test fork → commit `/workspace` change (succeeds) → attempt `/engine` change (blocks)
5. Deploy/demo protection active

**MVP Delivers**: Developers protected from accidentally modifying engine code

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (all code migrated)
2. Add User Story 1 → GitHub Actions active → Commit-time protection live (MVP!)
3. Add User Story 2 → Import restrictions active → Runtime protection live
4. Add User Story 3 → Local development enabled → Full developer workflow ready
5. Each story adds security layer without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (critical path)
2. Once Foundational done:
   - **Developer A**: User Story 1 (GitHub Actions) - Independent work
   - **Developer B**: User Story 2 (Import restrictions + Audit) - Independent work
   - **Developer C**: User Story 3 (Auth + Seed script) - Independent work
3. Stories complete and integrate independently
4. Team converges on Phase 6 (Polish) together

---

## Task Count Summary

- **Total Tasks**: 70
- **Phase 1 (Setup)**: 3 tasks
- **Phase 2 (Foundational)**: 10 tasks (CRITICAL PATH)
- **Phase 3 (US1)**: 10 tasks (2 tests + 8 implementation)
- **Phase 4 (US2)**: 15 tasks (3 tests + 12 implementation)
- **Phase 5 (US3)**: 21 tasks (3 tests + 18 implementation)
- **Phase 6 (Polish)**: 11 tasks

**Parallel Opportunities**: 24 tasks marked [P] can run concurrently

**Estimated Timeline** (single developer):
- Phase 1-2: 1-2 days (foundation)
- Phase 3 (US1): 1 day (MVP achievable)
- Phase 4 (US2): 2 days
- Phase 5 (US3): 2-3 days
- Phase 6: 1 day
- **Total: 7-10 days for full feature**

**MVP Timeline** (Phase 1-3 only): 2-3 days

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies

**Critical Path**: Phase 2 (Foundational) - All repository restructuring must complete before any user story work begins

**Success Metrics**:
- US1: 100% of unauthorized `/engine` commits blocked
- US2: 100% of workspace→engine imports blocked
- US3: <5 minute local setup time (seed + start)
