# Tasks: Integration Mapping Framework

**Input**: Design documents from `/specs/003-integration-mapping-framework/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL in this feature - Constitution requires test-first, so tests ARE included for all non-trivial business logic.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
This is a **web application** split across 3 repositories:
- **api/**: Management API (Python 3.11 Azure Functions)
- **workflows/**: Workflow engine (Python 3.11 Azure Functions)
- **client/**: React frontend (TypeScript)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and Table Storage setup

- [ ] T001 [P] Create OrgIntegrationMappings table in Azure Table Storage (PartitionKey=org_id, RowKey=integration_name_mapping_id)
- [ ] T002 [P] Create IntegrationMappings table in Azure Table Storage (PartitionKey=integration_name, RowKey=org_id_mapping_id)
- [ ] T003 [P] Add MappingStorageService scaffold to workflows/shared/storage.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 [P] Create OrganizationMapping Pydantic model in workflows/shared/models.py with to_org_entity(), to_integration_entity(), from_entity() methods
- [ ] T005 [P] Create ExternalOrganization Pydantic model in workflows/shared/models.py (frozen dataclass)
- [ ] T006 [P] Create TestResult Pydantic model in workflows/shared/models.py (frozen dataclass)
- [ ] T007 [P] Create IntegrationInterface abstract base class in workflows/shared/integrations/base.py with supports_org_mapping(), list_organizations(), get_client(), test_connection() methods
- [ ] T008 [P] Create BaseIntegration class in workflows/shared/integrations/base.py with default implementations
- [ ] T009 [P] Add OrganizationMapping model to api/shared/models.py (duplicate for API)
- [ ] T010 Implement MappingStorageService.create_mapping() in workflows/shared/storage.py (dual-table write with asyncio.gather)
- [ ] T011 Implement MappingStorageService.get_org_mappings() in workflows/shared/storage.py (query OrgIntegrationMappings table)
- [ ] T012 Implement MappingStorageService.get_mapping() in workflows/shared/storage.py (single entity fetch)
- [ ] T013 Implement MappingStorageService.update_mapping() in workflows/shared/storage.py (dual-table update)
- [ ] T014 Implement MappingStorageService.delete_mapping() in workflows/shared/storage.py (soft delete with is_active=false)
- [ ] T015 Implement MappingStorageService.update_test_result() in workflows/shared/storage.py (update last_tested_at and last_test_result fields)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Enable Integration for Organization Mapping (Priority: P1) 🎯 MVP

**Goal**: Integrations can declare support for organization mapping and discover external organizations

**Independent Test**: Create integration that implements `supports_org_mapping()=True` and `list_organizations()`, verify discovery endpoint returns external organizations

### Tests for User Story 1

**NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T016 [P] [US1] Contract test for IntegrationInterface in workflows/tests/contract/test_integration_interface.py - verify all abstract methods defined, type hints correct
- [ ] T017 [P] [US1] Integration test for list_organizations() in workflows/tests/integration/test_organization_discovery.py - mock external API, verify ExternalOrganization list returned

### Implementation for User Story 1

- [ ] T018 [P] [US1] Create GET /api/integrations/{integrationName}/discover endpoint in workflows/functions/integration_discovery.py (Blueprint route)
- [ ] T019 [P] [US1] Implement in-memory TTL cache for discovered organizations in workflows/shared/cache.py (OrganizationCache dataclass with is_expired() method)
- [ ] T020 [US1] Implement discovery endpoint logic: load integration class, check supports_org_mapping(), call list_organizations(), cache results, return JSON
- [ ] T021 [US1] Add validation: integration must exist in INTEGRATION_REGISTRY, must support mapping, orgId query param required
- [ ] T022 [US1] Add error handling: IntegrationNotFoundError → 404, NotImplementedError → 400 "doesn't support discovery"
- [ ] T023 [US1] Add cache refresh logic: check refresh query param, bypass cache if true
- [ ] T024 [US1] Register blueprint in workflows/function_app.py

**Checkpoint**: At this point, integrations can be marked as "Integration Mapping Enabled" and discovery works

---

## Phase 4: User Story 2 - Map Organization to External System (Priority: P1)

**Goal**: Administrators can create mappings between MSP organizations and external org IDs through UI

**Independent Test**: Create mapping via UI, verify it's persisted in both tables and displayed in mappings list

### Tests for User Story 2

- [ ] T025 [P] [US2] Contract test for CreateMappingRequest Pydantic model in api/tests/contract/test_mapping_models.py - validate required fields, regex patterns, field constraints
- [ ] T026 [P] [US2] Contract test for OrganizationMapping response model in api/tests/contract/test_mapping_models.py - verify all fields serialized correctly, datetime to ISO8601
- [ ] T027 [P] [US2] Integration test for POST /api/organizations/{orgId}/integrations in api/tests/integration/test_create_mapping.py - full CRUD flow with Azurite

### Implementation for User Story 2 (Backend)

- [ ] T028 [P] [US2] Create CreateMappingRequest Pydantic model in api/shared/models.py with validators (integration_name regex, external_org_id length, no special chars)
- [ ] T029 [P] [US2] Create POST /api/organizations/{orgId}/integrations endpoint in api/functions/org_integrations.py (Blueprint route)
- [ ] T030 [US2] Implement create mapping logic: parse request body, validate org exists, validate integration exists in registry, generate mapping_id (UUID), call MappingStorageService.create_mapping()
- [ ] T031 [US2] Add permission check: @require_permission('canManageConfig') decorator
- [ ] T032 [US2] Add validation: org_id from path must exist, integration_name must be in INTEGRATION_REGISTRY, external_org_id not empty
- [ ] T033 [US2] Add error handling: ValidationError → 400, OrgNotFoundError → 404, DuplicateMappingError → 409
- [ ] T034 [US2] Add audit logging: log_audit_event with mapping creation details (org_id, integration_name, external_org_id, user_id)
- [ ] T035 [US2] Create GET /api/organizations/{orgId}/integrations endpoint in api/functions/org_integrations.py - list all mappings for org with activeOnly filter
- [ ] T036 [US2] Register blueprint in api/function_app.py

### Implementation for User Story 2 (Frontend)

- [ ] T037 [P] [US2] Create OrganizationMapping TypeScript interface in client/src/types/integrationMapping.ts
- [ ] T038 [P] [US2] Create ExternalOrganization TypeScript interface in client/src/types/integrationMapping.ts
- [ ] T039 [P] [US2] Create integrationMappingsService with createMapping(), listMappings(), getMapping() in client/src/services/integrationMappings.ts
- [ ] T040 [P] [US2] Create useIntegrationMappings React Query hook in client/src/hooks/useIntegrationMappings.ts
- [ ] T041 [P] [US2] Create IntegrationMappingsList component in client/src/components/integrations/IntegrationMappingsList.tsx (table with columns: Integration, External Org, Status, Actions)
- [ ] T042 [P] [US2] Create CreateMappingDialog component in client/src/components/integrations/CreateMappingDialog.tsx (integration dropdown, external org selector, mapping data fields)
- [ ] T043 [US2] Implement CreateMappingDialog logic: integration dropdown (filtered to mapping-enabled), trigger discovery on selection, show searchable dropdown or text input based on supports_org_mapping
- [ ] T044 [US2] Add "Integrations" tab to Organizations page in client/src/pages/Organizations.tsx
- [ ] T045 [US2] Integrate IntegrationMappingsList into Integrations tab
- [ ] T046 [US2] Add "Add Integration Mapping" button to trigger CreateMappingDialog
- [ ] T047 [US2] Add empty state when no mappings exist ("No Integration Mappings" with CTA)
- [ ] T048 [US2] Add empty state when integration doesn't support discovery (manual entry instructions)

**Checkpoint**: At this point, users can create mappings via UI and see them in the list

---

## Phase 5: User Story 3 - Retrieve Mapping in Workflow (Priority: P1)

**Goal**: Workflows can retrieve organization's integration mapping to interact with external systems

**Independent Test**: Call get_integration_mapping() in workflow, verify it returns correct external org ID and metadata for the integration

### Tests for User Story 3

- [ ] T049 [P] [US3] Integration test for OrganizationContext.get_integration_mapping() in workflows/tests/integration/test_workflow_mapping_retrieval.py - create mapping, call from workflow, verify correct mapping returned
- [ ] T050 [P] [US3] Integration test for MappingNotFoundError in workflows/tests/integration/test_workflow_mapping_retrieval.py - call get_integration_mapping() without mapping, verify error raised
- [ ] T051 [P] [US3] Integration test for MultipleMappingsError in workflows/tests/integration/test_workflow_mapping_retrieval.py - create 2 mappings for same integration, call without mapping_id, verify error raised

### Implementation for User Story 3

- [ ] T052 [P] [US3] Create MappingNotFoundError exception in workflows/shared/exceptions.py
- [ ] T053 [P] [US3] Create MultipleMappingsError exception with mapping_ids list in workflows/shared/exceptions.py
- [ ] T054 [US3] Add get_integration_mapping(integration_name, mapping_id=None) method to OrganizationContext in workflows/shared/context.py
- [ ] T055 [US3] Implement get_integration_mapping() logic: query MappingStorageService.get_org_mappings(self.org_id), filter by integration_name, raise MappingNotFoundError if none, raise MultipleMappingsError if >1 and mapping_id None, return single mapping
- [ ] T056 [US3] Update get_integration() method in OrganizationContext to accept optional mapping_id parameter
- [ ] T057 [US3] Implement get_integration() logic: call get_integration_mapping() to load mapping, get integration class, call integration.get_client(mapping), return authenticated client
- [ ] T058 [US3] Add context.log() calls for mapping retrieval operations (info: "Loading mapping for integration X", error: "No mapping found for integration X")

**Checkpoint**: At this point, workflows can retrieve and use integration mappings

---

## Phase 6: User Story 4 - Create Mapping from Workflow (Priority: P2)

**Goal**: Workflows can automatically create integration mappings for automation scenarios

**Independent Test**: Call set_integration_mapping() in workflow, verify mapping is created and retrievable via get_integration_mapping()

### Tests for User Story 4

- [ ] T059 [P] [US4] Integration test for OrganizationContext.set_integration_mapping() in workflows/tests/integration/test_workflow_mapping_creation.py - call from workflow, verify mapping persisted in both tables
- [ ] T060 [P] [US4] Integration test for set_integration_mapping() update behavior in workflows/tests/integration/test_workflow_mapping_creation.py - create mapping, update with new external_org_id, verify updated

### Implementation for User Story 4

- [ ] T061 [US4] Add set_integration_mapping(integration_name, external_org_id, external_org_name="", mapping_data=None, mapping_id=None) method to OrganizationContext in workflows/shared/context.py
- [ ] T062 [US4] Implement set_integration_mapping() logic: check if mapping_id provided and exists (update), else create new, validate integration exists, call MappingStorageService.create_mapping() or update_mapping(), return OrganizationMapping
- [ ] T063 [US4] Add validation: integration_name must exist in INTEGRATION_REGISTRY, external_org_id required, auto-generate mapping_id if not provided
- [ ] T064 [US4] Add context.log() calls for mapping creation/update (info: "Created mapping for integration X", debug: "Using external org ID: Y")

**Checkpoint**: At this point, workflows can create and update mappings programmatically

---

## Phase 7: User Story 5 - View and Manage Integration Mappings (Priority: P2)

**Goal**: Administrators can view, edit, and delete integration mappings in dedicated UI

**Independent Test**: Navigate to organization's Integrations tab, perform CRUD operations (edit external org name, delete mapping), verify changes persisted

### Tests for User Story 5

- [ ] T065 [P] [US5] Contract test for UpdateMappingRequest Pydantic model in api/tests/contract/test_mapping_models.py - verify all fields optional, validation rules applied
- [ ] T066 [P] [US5] Integration test for PATCH /api/organizations/{orgId}/integrations/{mappingId} in api/tests/integration/test_update_mapping.py - update mapping, verify changes persisted
- [ ] T067 [P] [US5] Integration test for DELETE /api/organizations/{orgId}/integrations/{mappingId} in api/tests/integration/test_delete_mapping.py - delete mapping, verify soft delete (is_active=false)

### Implementation for User Story 5 (Backend)

- [ ] T068 [P] [US5] Create UpdateMappingRequest Pydantic model in api/shared/models.py with optional fields (external_org_id, external_org_name, mapping_data, is_active)
- [ ] T069 [P] [US5] Create GET /api/organizations/{orgId}/integrations/{mappingId} endpoint in api/functions/org_integrations.py - get specific mapping
- [ ] T070 [P] [US5] Create PATCH /api/organizations/{orgId}/integrations/{mappingId} endpoint in api/functions/org_integrations.py - update mapping fields
- [ ] T071 [P] [US5] Create DELETE /api/organizations/{orgId}/integrations/{mappingId} endpoint in api/functions/org_integrations.py - soft delete mapping
- [ ] T072 [US5] Implement update mapping logic: parse RowKey format (integration_name_mapping_id), load existing mapping, merge updates, validate, call MappingStorageService.update_mapping()
- [ ] T073 [US5] Implement delete mapping logic: parse RowKey, call MappingStorageService.delete_mapping() (soft delete with is_active=false)
- [ ] T074 [US5] Add permission checks: @require_permission('canManageConfig') on all endpoints
- [ ] T075 [US5] Add audit logging: log_audit_event for mapping updates and deletes

### Implementation for User Story 5 (Frontend)

- [ ] T076 [P] [US5] Create EditMappingDialog component in client/src/components/integrations/EditMappingDialog.tsx (pre-filled form with current mapping data)
- [ ] T077 [P] [US5] Create DeleteConfirmationDialog component (shared or inline) for mapping deletion
- [ ] T078 [US5] Add updateMapping() and deleteMapping() to integrationMappingsService in client/src/services/integrationMappings.ts
- [ ] T079 [US5] Add Edit button to IntegrationMappingsList table rows, trigger EditMappingDialog
- [ ] T080 [US5] Add Delete button to IntegrationMappingsList table rows, trigger DeleteConfirmationDialog
- [ ] T081 [US5] Implement EditMappingDialog save logic: call updateMapping(), refetch mappings list, show success toast
- [ ] T082 [US5] Implement delete confirmation logic: call deleteMapping(), refetch mappings list, show success toast
- [ ] T083 [US5] Add mapping status indicator (active/inactive) to IntegrationMappingsList table

**Checkpoint**: At this point, users can fully manage mappings through UI (view, edit, delete)

---

## Phase 8: User Story 6 - Test Integration Connection (Priority: P3)

**Goal**: Administrators can test integration mappings to verify correct configuration

**Independent Test**: Click "Test Connection" button, verify system attempts connection and displays success or failure result

### Tests for User Story 6

- [ ] T084 [P] [US6] Integration test for POST /api/organizations/{orgId}/integrations/{mappingId}/test in api/tests/integration/test_connection.py - test mapping with mock integration, verify TestResult returned
- [ ] T085 [P] [US6] Integration test for IntegrationInterface.test_connection() in workflows/tests/integration/test_integration_test_connection.py - implement test_connection() in mock integration, verify success/failure scenarios

### Implementation for User Story 6 (Backend)

- [ ] T086 [P] [US6] Create POST /api/organizations/{orgId}/integrations/{mappingId}/test endpoint in api/functions/org_integrations.py - test connection
- [ ] T087 [US6] Implement test connection logic: parse RowKey, load mapping, get integration class, instantiate with context, call integration.test_connection(mapping), update mapping with test result, return TestResult
- [ ] T088 [US6] Call MappingStorageService.update_test_result() to persist last_tested_at and last_test_result after test
- [ ] T089 [US6] Add error handling: integration not found → 404, test_connection() raises exception → wrap in TestResult with success=false
- [ ] T090 [US6] Add permission check: @require_permission('canManageConfig')

### Implementation for User Story 6 (Frontend)

- [ ] T091 [P] [US6] Create TestConnectionDialog component in client/src/components/integrations/TestConnectionDialog.tsx (loading spinner, success/error message, details)
- [ ] T092 [US6] Add testConnection() to integrationMappingsService in client/src/services/integrationMappings.ts
- [ ] T093 [US6] Add "Test Connection" button to IntegrationMappingsList table rows
- [ ] T094 [US6] Implement test connection logic: call testConnection(), show loading spinner, display result in TestConnectionDialog (green checkmark + success message OR red X + error message)
- [ ] T095 [US6] Update IntegrationMappingsList to show last_tested_at and last_test_result in table (timestamp + success/failure indicator)
- [ ] T096 [US6] Add retry button in TestConnectionDialog for failed tests

**Checkpoint**: At this point, users can test mappings and see connection status

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T097 [P] Add comprehensive error messages for all API endpoints in api/functions/org_integrations.py (validation details, troubleshooting guidance)
- [ ] T098 [P] Add loading states and skeleton loaders to all frontend components in client/src/components/integrations/
- [ ] T099 [P] Optimize Table Storage queries: ensure all queries use PartitionKey filter, add select parameter for needed fields only
- [ ] T100 [P] Add caching headers to discovery endpoint (Cache-Control: max-age=3600)
- [ ] T101 [P] Code cleanup: extract common validation logic to shared validators in api/shared/validators.py
- [ ] T102 [P] Add TypeScript types export for all integration mapping types in client/src/types/index.ts
- [ ] T103 Performance optimization: batch discovery API calls when multiple integrations selected
- [ ] T104 Security hardening: validate external_org_id doesn't contain injection characters, sanitize mapping_data JSON
- [ ] T105 Documentation: Add integration developer guide based on quickstart.md to docs/integrations.md
- [ ] T106 Documentation: Add API documentation using OpenAPI spec in api/docs/
- [ ] T107 [P] Add example integration implementation (HaloPSAIntegration) in workflows/shared/integrations/halopsa.py following quickstart.md pattern
- [ ] T108 Validate quickstart.md: walk through all steps, ensure commands work, verify examples compile

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories 1-3 (Phase 3-5)**: All depend on Foundational phase completion - these are P1 (MVP scope)
  - US1 (Enable Integration): Foundation for US2 and US3
  - US2 (Map Organization): Depends on US1 (needs discovery), foundation for US3
  - US3 (Retrieve in Workflow): Can start after Foundation, logically after US2 (needs mappings to retrieve)
- **User Story 4 (Phase 6)**: Depends on Foundational + US3 (uses same context methods)
- **User Story 5 (Phase 7)**: Depends on Foundational + US2 (extends UI from US2)
- **User Story 6 (Phase 8)**: Depends on Foundational + US1 (uses IntegrationInterface.test_connection())
- **Polish (Phase 9)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Depends on US1 completion (needs discovery endpoint) - Logically sequential after US1
- **User Story 3 (P1)**: Can start after Foundational - May benefit from US2 existing (test data), but independently testable
- **User Story 4 (P2)**: Can start after Foundational - Uses same APIs as US3, independently testable
- **User Story 5 (P2)**: Depends on US2 completion (extends same UI) - Logically sequential after US2
- **User Story 6 (P3)**: Can start after Foundational + US1 (needs IntegrationInterface) - Independently testable

### Recommended Execution Order

**For MVP (P1 only - minimum viable product)**:
1. Phase 1: Setup → Phase 2: Foundational
2. Phase 3: US1 (Enable Integration) - Test independently
3. Phase 4: US2 (Map Organization) - Test independently
4. Phase 5: US3 (Retrieve in Workflow) - Test independently
5. **STOP**: MVP complete! Can map orgs and use in workflows

**For Full Feature (P1 + P2)**:
6. Phase 6: US4 (Create from Workflow) - Test independently
7. Phase 7: US5 (Manage Mappings UI) - Test independently

**For Complete Feature (P1 + P2 + P3)**:
8. Phase 8: US6 (Test Connection) - Test independently
9. Phase 9: Polish

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD)
- Backend models before backend services
- Backend endpoints before frontend services
- Frontend services before frontend components
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

**Setup Phase (Phase 1)**:
- T001 (create table 1) || T002 (create table 2) || T003 (storage service scaffold)

**Foundational Phase (Phase 2)**:
- T004 (OrganizationMapping model) || T005 (ExternalOrganization model) || T006 (TestResult model) || T007 (IntegrationInterface) || T008 (BaseIntegration) || T009 (API models)
- Then: T010-T015 sequential (storage service methods depend on models)

**User Story 1 (Phase 3)**:
- Tests: T016 (contract test) || T017 (integration test)
- Implementation: T018 (endpoint) || T019 (cache)
- Then: T020-T024 sequential (endpoint logic, validation, error handling)

**User Story 2 (Phase 4)**:
- Tests: T025 (contract 1) || T026 (contract 2) || T027 (integration test)
- Backend: T028 (request model) || T029 (endpoint scaffold)
- Then: T030-T036 sequential (backend logic)
- Frontend (can start in parallel with backend testing): T037-T039 (types and services) || T040 (hook) || T041-T042 (components)
- Then: T043-T048 sequential (UI integration)

**User Story 3 (Phase 5)**:
- Tests: T049 (happy path) || T050 (error 1) || T051 (error 2)
- Implementation: T052 (exception 1) || T053 (exception 2)
- Then: T054-T058 sequential (context methods)

**User Story 4 (Phase 6)**:
- Tests: T059 (create) || T060 (update)
- Then: T061-T064 sequential (context method)

**User Story 5 (Phase 7)**:
- Tests: T065 (contract) || T066 (update test) || T067 (delete test)
- Backend: T068 (model) || T069 (get endpoint) || T070 (update endpoint) || T071 (delete endpoint)
- Then: T072-T075 sequential (backend logic)
- Frontend: T076 (edit dialog) || T077 (delete dialog)
- Then: T078-T083 sequential (UI integration)

**User Story 6 (Phase 8)**:
- Tests: T084 (API test) || T085 (interface test)
- Backend: T086 (endpoint scaffold)
- Then: T087-T090 sequential (test logic)
- Frontend: T091 (dialog) || T092 (service)
- Then: T093-T096 sequential (UI integration)

**Polish Phase (Phase 9)**:
- T097-T102 (all improvements) || T107 (example integration)
- Then: T103-T108 sequential (optimizations, validation)

---

## Parallel Example: User Story 2 (Map Organization)

```bash
# Launch all tests for User Story 2 together:
Task: "Contract test for CreateMappingRequest in api/tests/contract/test_mapping_models.py"
Task: "Contract test for OrganizationMapping response in api/tests/contract/test_mapping_models.py"
Task: "Integration test for POST /api/organizations/{orgId}/integrations in api/tests/integration/test_create_mapping.py"

# Launch backend and frontend models in parallel:
Task: "Create CreateMappingRequest model in api/shared/models.py"
Task: "Create OrganizationMapping TypeScript interface in client/src/types/integrationMapping.ts"
Task: "Create ExternalOrganization TypeScript interface in client/src/types/integrationMapping.ts"

# Launch frontend components in parallel:
Task: "Create IntegrationMappingsList component in client/src/components/integrations/IntegrationMappingsList.tsx"
Task: "Create CreateMappingDialog component in client/src/components/integrations/CreateMappingDialog.tsx"
```

---

## Implementation Strategy

### MVP First (User Stories 1-3 Only - P1 Priority)

1. Complete Phase 1: Setup (Tables + Storage scaffold)
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Enable Integration & Discovery)
4. **CHECKPOINT**: Test discovery endpoint independently - can list external orgs
5. Complete Phase 4: User Story 2 (Map Organization via UI)
6. **CHECKPOINT**: Test mapping creation independently - can create and view mappings
7. Complete Phase 5: User Story 3 (Retrieve in Workflow)
8. **CHECKPOINT**: Test workflow retrieval independently - workflows can access mapped orgs
9. **STOP and VALIDATE**: All 3 P1 stories work together - MVP is ready!
10. Deploy/demo if ready

**MVP Validation Checklist**:
- ✅ Can discover external organizations from integration
- ✅ Can create mapping via UI
- ✅ Mapping persisted in both tables
- ✅ Workflow can retrieve mapping and use external org ID
- ✅ All acceptance scenarios from spec.md US1-3 pass

### Incremental Delivery

1. **Foundation**: Setup + Foundational → Tables and core models ready
2. **MVP (P1)**: Add US1-3 → Test independently → Deploy/Demo
   - Delivers: Integration discovery, mapping creation, workflow usage
   - Value: Zero-code integration setup for any integration
3. **Enhanced (P1+P2)**: Add US4-5 → Test independently → Deploy/Demo
   - Adds: Workflow automation, mapping management UI
   - Value: Automated provisioning, better UX
4. **Complete (P1+P2+P3)**: Add US6 → Test independently → Deploy/Demo
   - Adds: Connection testing
   - Value: Troubleshooting and validation

### Parallel Team Strategy

With multiple developers:

1. **Team completes Setup + Foundational together** (1-2 days)
2. **Once Foundational is done** (can parallelize user stories):
   - Developer A: User Story 1 (Discovery) + User Story 6 (Test Connection)
   - Developer B: User Story 2 (Map UI) + User Story 5 (Manage UI)
   - Developer C: User Story 3 (Workflow Retrieval) + User Story 4 (Workflow Creation)
3. **Stories complete and integrate independently**

**Note**: US1 should complete before US2 starts (US2 depends on discovery), but US3-4 can be done in parallel with US1-2.

---

## Notes

- **[P] tasks** = different files, no dependencies, safe to parallelize
- **[Story] label** maps task to specific user story for traceability
- **Each user story is independently completable and testable** (validates acceptance criteria from spec.md)
- **Tests written first** (TDD): Verify tests fail before implementing
- **Commit after each task** or logical group
- **Stop at any checkpoint** to validate story independently
- **MVP = User Stories 1-3** (P1 priority): Provides core value with minimal scope
- **Avoid**: vague tasks, same file conflicts, cross-story dependencies that break independence

## Task Count Summary

- **Total Tasks**: 108 tasks
- **Phase 1 (Setup)**: 3 tasks
- **Phase 2 (Foundational)**: 12 tasks (BLOCKING)
- **Phase 3 (US1 - P1)**: 9 tasks
- **Phase 4 (US2 - P1)**: 21 tasks
- **Phase 5 (US3 - P1)**: 7 tasks
- **Phase 6 (US4 - P2)**: 6 tasks
- **Phase 7 (US5 - P2)**: 19 tasks
- **Phase 8 (US6 - P3)**: 13 tasks
- **Phase 9 (Polish)**: 12 tasks

**MVP Scope** (P1 only): 15 + 47 tasks = 62 tasks to complete US1-3
**Parallel Opportunities**: 40+ tasks marked [P] across all phases
