---
description: "Task list for Azure Key Vault Integration feature"
---

# Tasks: Azure Key Vault Integration for Secret Management

**Input**: Design documents from `/specs/003-use-azure-key/`
**Prerequisites**: plan.md, spec.md, research.md

**Tests**: Tests are OPTIONAL - not included in this task list as they were not explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- Workflows backend: `workflows/engine/shared/`
- Client API backend: `client/api/`
- Tests: `workflows/tests/` and `client/api/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency installation

- [X] T001 Add azure-keyvault-secrets SDK to workflows/requirements.txt
- [X] T002 Add azure-identity SDK to workflows/requirements.txt
- [X] T003 [P] Add azure-keyvault-secrets SDK to client/api/requirements.txt
- [X] T004 [P] Add azure-identity SDK to client/api/requirements.txt
- [X] T005 [P] Install dependencies with pip install -r workflows/requirements.txt
- [X] T006 [P] Install dependencies with pip install -r client/api/requirements.txt

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Create Key Vault client wrapper with DefaultAzureCredential in workflows/engine/shared/keyvault.py
- [X] T008 [P] Create Key Vault client wrapper with full CRUD operations in client/api/shared/keyvault.py
- [X] T009 Implement secret naming convention helpers (org-scoped, global fallback) in workflows/engine/shared/keyvault.py
- [X] T010 Implement in-memory secret cache with 1-hour TTL in workflows/engine/shared/keyvault.py
- [X] T011 [P] Implement retry logic with exponential backoff (5 attempts, 0.8 backoff factor) in workflows/engine/shared/keyvault.py
- [X] T012 [P] Configure Key Vault URL environment variable handling (AZURE_KEY_VAULT_URL) in both projects
- [X] T013 Add error handling for ResourceNotFoundError, ClientAuthenticationError, HttpResponseError in workflows/engine/shared/keyvault.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Unified Configuration Access (Priority: P1) 🎯 MVP

**Goal**: Provide a single `get_config()` method that transparently resolves values from plain config or Key Vault based on config type

**Independent Test**: Configure a secret reference (e.g., `api_key` marked as secret type), request that config value in a workflow, and verify the actual secret value is returned from Key Vault

### Implementation for User Story 1

- [X] T014 [US1] Create ConfigResolver class with get_config() method in workflows/engine/shared/config_resolver.py
- [X] T015 [US1] Implement config type detection logic (secret_ref vs plain text) in workflows/engine/shared/config_resolver.py
- [X] T016 [US1] Implement org-scoped → global fallback pattern for secret resolution in workflows/engine/shared/config_resolver.py
- [X] T017 [US1] Integrate ConfigResolver into OrganizationContext.get_config() in workflows/engine/shared/context.py
- [X] T018 [US1] Add error handling for missing secrets with clear error messages in workflows/engine/shared/config_resolver.py
- [X] T019 [US1] Add audit logging for secret access attempts (without logging values) in workflows/engine/shared/config_resolver.py
- [X] T020 [US1] Ensure secret values never appear in logs or error messages in workflows/engine/shared/config_resolver.py

**Checkpoint**: At this point, User Story 1 should be fully functional - workflows can transparently access secrets via get_config()

---

## Phase 4: User Story 3 - Local Development Secret Management (Priority: P1)

**Goal**: Enable local development with secrets accessible via Key Vault (developer credentials) or local fallback configuration

**Independent Test**: Run platform locally and verify workflows can access secrets through either Key Vault with developer auth or local settings

### Implementation for User Story 3

- [X] T021 [US3] Implement local development fallback logic in workflows/engine/shared/config_resolver.py
- [X] T022 [US3] Add environment variable fallback pattern ({ORG_ID}__{SECRET_KEY}, GLOBAL__{SECRET_KEY}) in workflows/engine/shared/config_resolver.py
- [X] T023 [US3] Add .env file support for local secrets (with .gitignore entry) in workflows/engine/shared/config_resolver.py
- [X] T024 [US3] Handle DefaultAzureCredential failure gracefully with fallback to local config in workflows/engine/shared/keyvault.py
- [X] T025 [US3] Add clear error messages when secret missing in both Key Vault and local config in workflows/engine/shared/config_resolver.py
- [X] T026 [US3] Update local.settings.json.example with secret configuration examples in workflows/
- [X] T027 [US3] Create quickstart documentation for local Key Vault setup in specs/003-use-azure-key/quickstart.md

**Checkpoint**: At this point, User Story 3 should be fully functional - local development works with or without Key Vault access

---

## Phase 5: User Story 4 - Production Secret Resolution (Priority: P1)

**Goal**: Enable automatic identity-based authentication to Key Vault in production using managed identity

**Independent Test**: Deploy to production with managed identity enabled and verify workflows can retrieve secrets without any credentials in configuration

### Implementation for User Story 4

- [X] T028 [US4] Verify DefaultAzureCredential managed identity support in workflows/engine/shared/keyvault.py
- [X] T029 [US4] Add environment detection logic (production vs local) in workflows/engine/shared/keyvault.py
- [X] T030 [US4] Implement authentication credential caching for workflow execution duration in workflows/engine/shared/keyvault.py
- [X] T031 [US4] Add retry logic for transient Key Vault failures (network errors, rate limiting) in workflows/engine/shared/keyvault.py
- [X] T032 [US4] Add clear error messages for permission issues (403 Forbidden) in workflows/engine/shared/keyvault.py
- [X] T033 [US4] Verify no credentials stored in app configuration files

**Checkpoint**: At this point, User Story 4 should be fully functional - production workflows authenticate automatically with managed identity

---

## Phase 6: User Story 2 - Secret Configuration UI with Dropdown Selection (Priority: P2)

**Goal**: Provide dropdown selection of available secrets when configuring secret reference config values in the UI

**Independent Test**: Open config management UI, select secret reference type, and verify dropdown appears with available secret names

### Implementation for User Story 2

- [X] T034 [P] [US2] Implement list_secrets() method with org-scoped filtering in client/api/shared/keyvault.py
- [X] T035 [P] [US2] Create SecretListResponse Pydantic model in client/api/shared/models.py
- [X] T036 [US2] Create GET /api/secrets endpoint to list available secrets in client/api/functions/secrets.py
- [X] T037 [US2] Add org_id query parameter filtering to secrets list endpoint in client/api/functions/secrets.py
- [X] T038 [US2] Handle list permission failures gracefully with 200 response and empty list in client/api/functions/secrets.py
- [ ] T039 [US2] Create secretsClient.ts API client with listSecrets() method in client/src/services/secretsClient.ts **[FRONTEND - DEFERRED]**
- [ ] T040 [US2] Create SecretDropdown component for config management UI in client/src/components/secrets/SecretDropdown.tsx **[FRONTEND - DEFERRED]**
- [ ] T041 [US2] Integrate SecretDropdown into config management form when secret_ref type selected **[FRONTEND - DEFERRED]**
- [ ] T042 [US2] Add fallback to manual text input if list permissions unavailable in SecretDropdown component **[FRONTEND - DEFERRED]**

**Checkpoint**: At this point, User Story 2 should be fully functional - admins can select secrets from dropdown when configuring

---

## Phase 7: User Story 5 - Secret Lifecycle Management (Priority: P2)

**Goal**: Enable platform admins to create, update, and delete secrets through the platform UI

**Independent Test**: Access secret management UI, create a new secret, update its value, delete it, and verify all operations succeed

### Implementation for User Story 5

- [ ] T043 [P] [US5] Create SecretCreateRequest Pydantic model in client/api/shared/models.py
- [ ] T044 [P] [US5] Create SecretUpdateRequest Pydantic model in client/api/shared/models.py
- [ ] T045 [P] [US5] Create SecretResponse Pydantic model in client/api/shared/models.py
- [ ] T046 [US5] Create POST /api/secrets endpoint for secret creation in client/api/functions/secrets.py
- [ ] T047 [US5] Create PUT /api/secrets/{name} endpoint for secret updates in client/api/functions/secrets.py
- [ ] T048 [US5] Create DELETE /api/secrets/{name} endpoint for secret deletion in client/api/functions/secrets.py
- [ ] T049 [US5] Add platform admin role validation middleware for secret write operations in client/api/shared/auth.py
- [ ] T050 [US5] Add secret name validation against Key Vault naming rules in client/api/functions/secrets.py
- [ ] T051 [US5] Implement conflict detection for duplicate secret names in create endpoint in client/api/functions/secrets.py
- [ ] T052 [US5] Implement warning for deleting referenced secrets in delete endpoint in client/api/functions/secrets.py
- [ ] T053 [P] [US5] Create SecretCreate component with name and value input in client/src/components/secrets/SecretCreate.tsx
- [ ] T054 [P] [US5] Create SecretUpdate component for updating secret values in client/src/components/secrets/SecretUpdate.tsx
- [ ] T055 [P] [US5] Create SecretDelete component with confirmation dialog in client/src/components/secrets/SecretDelete.tsx
- [ ] T056 [P] [US5] Create SecretList component showing masked values in client/src/components/secrets/SecretList.tsx
- [ ] T057 [US5] Implement plaintext display immediately after create/update in SecretCreate and SecretUpdate components
- [ ] T058 [US5] Implement value masking in SecretList component (show ******* for all values)
- [ ] T059 [US5] Add createSecret() method to secretsClient.ts
- [ ] T060 [US5] Add updateSecret() method to secretsClient.ts
- [ ] T061 [US5] Add deleteSecret() method to secretsClient.ts
- [ ] T062 [US5] Add routing for secret management UI in client/src/
- [ ] T063 [US5] Add platform admin permission check in UI routing

**Checkpoint**: At this point, User Story 5 should be fully functional - admins can fully manage secrets through the UI

---

## Phase 8: User Story 6 - Secure Store Health Monitoring (Priority: P3)

**Goal**: Provide connectivity status for Key Vault to enable quick troubleshooting

**Independent Test**: Access health/status endpoint and verify it shows Key Vault connectivity status with accurate connected/disconnected state

### Implementation for User Story 6

- [ ] T064 [P] [US6] Create KeyVaultHealthResponse Pydantic model in client/api/shared/models.py
- [ ] T065 [US6] Implement health check using list_properties_of_secrets() in client/api/shared/keyvault.py
- [ ] T066 [US6] Create GET /api/health/keyvault endpoint in client/api/functions/health.py
- [ ] T067 [US6] Add error detail formatting for health check failures in client/api/functions/health.py
- [ ] T068 [US6] Add actionable guidance messages for common issues (auth failure, permission denied, network error) in client/api/functions/health.py
- [ ] T069 [US6] Create KeyVaultStatus component for admin dashboard in client/src/components/health/KeyVaultStatus.tsx
- [ ] T070 [US6] Integrate KeyVaultStatus into admin dashboard or settings page
- [ ] T071 [US6] Add timestamp of last successful Key Vault access to health response

**Checkpoint**: At this point, User Story 6 should be fully functional - admins can monitor Key Vault health proactively

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T072 [P] Add comprehensive docstrings to all Key Vault integration classes and methods
- [X] T073 [P] Add inline comments for complex fallback and retry logic
- [X] T074 Code review and refactoring for consistency across workflows and client API
- [X] T075 [P] Verify all secret values are properly masked in UI components **[N/A - No UI in MVP]**
- [X] T076 [P] Verify no secret values appear in any log statements
- [X] T077 Security review of error messages to ensure no information leakage
- [ ] T078 Performance testing of secret caching (verify <100ms after cache warm-up) **[REQUIRES PRODUCTION TESTING]**
- [ ] T079 [P] Update ARM template documentation with Key Vault permission requirements **[DEFERRED - ARM template separate]**
- [ ] T080 [P] Create data model documentation in specs/003-use-azure-key/data-model.md **[DEFERRED - Optional]**
- [ ] T081 [P] Create API contract documentation in specs/003-use-azure-key/contracts/ **[DEFERRED - Optional]**
- [X] T082 Validate quickstart.md guide for local development setup

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-8)**: All depend on Foundational phase completion
  - US1, US3, US4 (P1): Can proceed in parallel after Phase 2
  - US2, US5 (P2): Can proceed in parallel after Phase 2 (recommended after US1 for better context)
  - US6 (P3): Can proceed after Phase 2 (recommended after US5 for better context)
- **Polish (Phase 9)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 3 (P1)**: Can start after Foundational (Phase 2) - Extends US1 with local fallback
- **User Story 4 (P1)**: Can start after Foundational (Phase 2) - Extends US1 with production auth
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Builds UI for secret selection
- **User Story 5 (P2)**: Can start after Foundational (Phase 2) - Full secret CRUD in UI
- **User Story 6 (P3)**: Can start after Foundational (Phase 2) - Health monitoring endpoint

**Recommended Order**: US1 → US3 → US4 (core functionality) → US2 → US5 (UI enhancements) → US6 (monitoring)

### Within Each User Story

- API models before endpoints (client/api)
- Backend logic before frontend components
- API client methods before UI components
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 1**: All dependency installation tasks marked [P] can run in parallel
- **Phase 2**: Tasks T008, T011, T012 marked [P] can run in parallel after T007
- **Phase 3 (US1)**: No parallel opportunities (sequential logic building)
- **Phase 4 (US3)**: No parallel opportunities (extends US1 sequentially)
- **Phase 5 (US4)**: No parallel opportunities (extends US1 sequentially)
- **Phase 6 (US2)**: Tasks T034, T035 can run in parallel; later UI tasks independent
- **Phase 7 (US5)**: Tasks T043, T044, T045 (models) can run in parallel; T053, T054, T055, T056 (UI components) can run in parallel
- **Phase 8 (US6)**: Tasks T064, T065 can run in parallel
- **Phase 9**: All documentation and review tasks marked [P] can run in parallel

---

## Parallel Example: User Story 5 (Secret Lifecycle Management)

```bash
# Launch all Pydantic models together:
Task: "Create SecretCreateRequest Pydantic model in client/api/shared/models.py"
Task: "Create SecretUpdateRequest Pydantic model in client/api/shared/models.py"
Task: "Create SecretResponse Pydantic model in client/api/shared/models.py"

# After API endpoints are complete, launch all UI components together:
Task: "Create SecretCreate component in client/src/components/secrets/SecretCreate.tsx"
Task: "Create SecretUpdate component in client/src/components/secrets/SecretUpdate.tsx"
Task: "Create SecretDelete component in client/src/components/secrets/SecretDelete.tsx"
Task: "Create SecretList component in client/src/components/secrets/SecretList.tsx"
```

---

## Implementation Strategy

### MVP First (User Stories 1, 3, 4 Only - Core P1 Functionality)

1. Complete Phase 1: Setup (install dependencies)
2. Complete Phase 2: Foundational (Key Vault client and infrastructure)
3. Complete Phase 3: User Story 1 (unified get_config interface)
4. Complete Phase 4: User Story 3 (local development support)
5. Complete Phase 5: User Story 4 (production managed identity auth)
6. **STOP and VALIDATE**: Test secret resolution end-to-end in both local and production
7. Deploy/demo if ready - **core secret management working!**

### Incremental Delivery (Add UI Enhancements)

1. Complete MVP above (US1, US3, US4)
2. Add Phase 6: User Story 2 → Test secret dropdown → Deploy/Demo
3. Add Phase 7: User Story 5 → Test full secret CRUD → Deploy/Demo
4. Add Phase 8: User Story 6 → Test health monitoring → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - **Developer A**: User Story 1 (core get_config)
   - **Developer B**: User Story 3 (local fallback - requires coordination with Dev A)
   - After US1 complete:
     - **Developer A**: User Story 2 (UI dropdown)
     - **Developer B**: User Story 4 (production auth)
     - **Developer C**: User Story 5 (secret CRUD UI)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- **Security critical**: Ensure no secret values in logs, errors, or UI after initial display
- **Naming convention**: Follow `{org_id}--{secret-name}` or `GLOBAL--{secret-name}` consistently
- **Performance target**: Secret resolution <100ms with caching
- Tests are optional and not included in this task list per feature specification
