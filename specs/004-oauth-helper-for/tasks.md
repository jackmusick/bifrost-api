# Tasks: OAuth Helper for Integrations and Workflows

**Input**: Design documents from `/specs/004-oauth-helper-for/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/oauth-api.openapi.yaml

**Tests**: This feature follows Test-First Development (Constitutional Principle IV). Tests are written FIRST and MUST FAIL before implementation begins.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- Project root: `/Users/jack/GitHub/bifrost-integrations`
- Source: `src/` (models, services, functions)
- Workflows: `workflows/engine/shared/` (shared helpers)
- Client API: `client/api/` (management API functions)
- Tests: `tests/` (contract, integration)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependencies

- [ ] T001 Install Python dependencies: aiohttp, pydantic (if not already present)
- [ ] T002 [P] Create `src/models/` directory structure for OAuth models
- [ ] T003 [P] Create `src/services/` directory structure for OAuth services
- [ ] T004 [P] Create `client/api/functions/` OAuth endpoints directory structure
- [ ] T005 [P] Create `workflows/engine/shared/` OAuth helper structure
- [ ] T006 [P] Create `tests/contract/` OAuth test structure
- [ ] T007 [P] Create `tests/integration/` OAuth test structure

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T008 Create `OAuthConnections` Table Storage table (PartitionKey=OrgId or "GLOBAL", RowKey=connection_name) in client/api/shared/storage.py or setup script
- [ ] T009 Create `WorkflowOAuthDependencies` Table Storage table (PartitionKey=connection_name, RowKey=workflow_id)
- [ ] T010 Create `WorkflowOAuthDependencies_ByWorkflow` Table Storage table (PartitionKey=workflow_id, RowKey=connection_name) for dual-indexing
- [ ] T011 Create `WorkflowDisableState` Table Storage table (PartitionKey=org_id or "GLOBAL", RowKey=workflow_id)
- [ ] T012 [P] Verify existing Config table supports oauth_* config keys with secret_ref type
- [ ] T013 [P] Verify existing KeyVaultClient can handle OAuth secret operations

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Create OAuth Connection Configuration (Priority: P1) 🎯 MVP

**Goal**: Enable administrators to create and store OAuth connection configurations

**Independent Test**: Create an OAuth configuration through API, save it, verify it persists in Table Storage and Config table with proper secret references

### Tests for User Story 1 (TDD - Write FIRST, ensure FAIL)

- [ ] T014 [P] [US1] Contract test for POST /api/oauth/connections in tests/contract/test_oauth_api.py
  - Test request validation (connection_name, oauth_flow_type, client_id, client_secret, authorization_url, token_url, scopes)
  - Test response schema (connection created with status="not_connected")
  - Test 400 for invalid input
  - Test 409 for duplicate connection name
- [ ] T015 [P] [US1] Contract test for GET /api/oauth/connections in tests/contract/test_oauth_api.py
  - Test list returns array of OAuth connections
  - Test include_global parameter
  - Test org-scoped filtering
- [ ] T016 [P] [US1] Contract test for GET /api/oauth/connections/{connection_name} in tests/contract/test_oauth_api.py
  - Test returns connection details
  - Test sensitive fields masked
  - Test 404 for non-existent connection

### Implementation for User Story 1

- [ ] T017 [P] [US1] Create OAuthConnection Pydantic model in src/models/oauth_connection.py
  - Fields: org_id, connection_name, oauth_flow_type, client_id, authorization_url, token_url, scopes, redirect_uri, status, created_at, updated_at
  - Validation: connection_name pattern, HTTPS URLs, valid flow types
  - Methods: is_expired(), expires_soon()
- [ ] T018 [P] [US1] Create OAuthConnectionSummary model in src/models/oauth_connection.py (for list responses)
- [ ] T019 [P] [US1] Create OAuthConnectionDetail model in src/models/oauth_connection.py (for get/update responses)
- [ ] T020 [P] [US1] Create CreateOAuthConnectionRequest model in src/models/oauth_connection.py
- [ ] T021 [US1] Implement OAuthStorageService in src/services/oauth_storage_service.py (depends on T017-T020)
  - create_connection(): Store metadata in OAuthConnections table
  - create_connection(): Store client_secret as config with Type="secret_ref" (config:oauth_{name}_client_secret)
  - create_connection(): Store metadata as config with Type="json" (config:oauth_{name}_metadata)
  - get_connection(): Read from OAuthConnections + Config table with org→GLOBAL fallback
  - list_connections(): Query OAuthConnections by partition
  - Org-scoped partition logic
- [ ] T022 [US1] Implement POST /api/oauth/connections endpoint in client/api/functions/oauth_api.py (depends on T021)
  - Parse CreateOAuthConnectionRequest
  - Call oauth_storage_service.create_connection()
  - Generate callback URL: f"/api/oauth/callback/{connection_name}"
  - Return OAuthConnectionDetail
  - Handle errors (validation, duplicate name)
- [ ] T023 [US1] Implement GET /api/oauth/connections endpoint in client/api/functions/oauth_api.py (depends on T021)
  - Query org-specific and/or GLOBAL connections
  - Support include_global parameter
  - Return list of OAuthConnectionSummary
  - Mask sensitive fields
- [ ] T024 [US1] Implement GET /api/oauth/connections/{connection_name} endpoint in client/api/functions/oauth_api.py (depends on T021)
  - Get connection with org→GLOBAL fallback
  - Return OAuthConnectionDetail
  - Mask sensitive fields (client secrets)
  - Handle 404
- [ ] T025 [US1] Add logging for OAuth connection creation and retrieval
- [ ] T026 [US1] Run contract tests and verify User Story 1 works independently

**Checkpoint**: User Story 1 complete - Administrators can create and list OAuth connections

---

## Phase 4: User Story 2 - Complete Interactive OAuth Authorization (Priority: P1)

**Goal**: Enable OAuth authorization flow with callback handling and token storage

**Independent Test**: Create OAuth config, initiate authorization, complete flow with mock OAuth provider, verify connection status changes to "Completed" and tokens stored

### Tests for User Story 2 (TDD - Write FIRST, ensure FAIL)

- [ ] T027 [P] [US2] Contract test for POST /api/oauth/connections/{connection_name}/authorize in tests/contract/test_oauth_api.py
  - Test returns authorization_url and state parameter
  - Test 400 for client_credentials flow (doesn't need authorization)
- [ ] T028 [P] [US2] Contract test for GET /api/oauth/callback/{connection_name} in tests/contract/test_oauth_callback.py
  - Test with valid authorization code and state
  - Test with error parameter (user denied)
  - Test invalid state parameter
  - Test returns HTML response
- [ ] T029 [P] [US2] Integration test for OAuth authorization flow in tests/integration/test_oauth_authorization_flow.py
  - Mock OAuth provider
  - Test full authorization code flow
  - Verify status transitions: not_connected → waiting_callback → testing → completed
  - Verify tokens stored in Config table as secret_ref

### Implementation for User Story 2

- [ ] T030 [P] [US2] Create OAuthProviderClient in src/services/oauth_provider.py
  - exchange_code_for_token(): POST to token_url with authorization code
  - get_client_credentials_token(): POST to token_url with client credentials
  - Retry logic for transient failures (3 retries, exponential backoff)
  - Timeout handling (10s default)
  - Error response parsing
- [ ] T031 [P] [US2] Create OAuthTestService in src/services/oauth_test_service.py
  - test_connection(): Call provider's test endpoint (Microsoft Graph /me, Google /userinfo, etc.)
  - detect_provider(): Identify provider from authorization_url
  - Return success/failure with message
- [ ] T032 [US2] Add token storage methods to OAuthStorageService in src/services/oauth_storage_service.py (depends on T021)
  - store_tokens(): Save tokens as config with Type="secret_ref" (config:oauth_{name}_tokens)
  - Tokens stored as JSON: {access_token, refresh_token, expires_at, token_type}
  - update_connection_status(): Update status in OAuthConnections table
  - update_metadata_config(): Update metadata config with status and expires_at
- [ ] T033 [US2] Implement POST /api/oauth/connections/{connection_name}/authorize endpoint in client/api/functions/oauth_api.py (depends on T021)
  - Get connection config
  - Generate state parameter (UUID for CSRF protection)
  - Store state temporarily (or embed in callback URL)
  - Build authorization URL with client_id, redirect_uri, scope, state
  - Return authorization_url and state
  - Return 400 for client_credentials flow
- [ ] T034 [US2] Implement GET+POST /api/oauth/callback/{connection_name} endpoint in client/api/functions/oauth_callback.py (depends on T030, T031, T032)
  - Extract connection_name from route
  - Handle GET and POST methods (different OAuth providers use different methods)
  - Validate state parameter
  - Handle error responses (error, error_description query params)
  - Exchange authorization code for tokens using OAuthProviderClient
  - Update status to "testing"
  - Test connection using OAuthTestService
  - Store tokens via oauth_storage_service.store_tokens()
  - Update status to "completed" or "failed"
  - Return HTML page with status message
  - Log callback events for audit
- [ ] T035 [US2] Add error handling for OAuth provider failures (network, invalid response, expired code)
- [ ] T036 [US2] Add logging for OAuth authorization and callback processing
- [ ] T037 [US2] Run contract and integration tests, verify User Story 2 works independently

**Checkpoint**: User Story 2 complete - OAuth authorization flow end-to-end functional

---

## Phase 5: User Story 3 - Access OAuth Credentials in Workflows (Priority: P1)

**Goal**: Enable workflows to retrieve OAuth credentials by connection name

**Independent Test**: Create workflow that calls get_oauth_connection(context, "connection_name"), verify it receives valid credentials

### Tests for User Story 3 (TDD - Write FIRST, ensure FAIL)

- [ ] T038 [P] [US3] Contract test for GET /api/oauth/credentials/{connection_name} in tests/contract/test_oauth_credentials.py
  - Test returns access_token, token_type, expires_at
  - Test 404 for non-existent connection
  - Test 503 for connection not ready (status != "completed")
- [ ] T039 [P] [US3] Integration test for workflow credential access in tests/integration/test_workflow_credential_access.py
  - Create mock OAuth connection with tokens
  - Call get_oauth_connection() from workflow context
  - Verify credentials returned
  - Verify org→GLOBAL fallback works

### Implementation for User Story 3

- [ ] T040 [P] [US3] Create get_oauth_connection() helper in workflows/engine/shared/oauth_helper.py
  - Load config using existing config_resolver.get_config(org_id, f"oauth_{connection_name}_tokens", config_data)
  - Parse JSON tokens from config
  - Return credentials dict: {access_token, token_type, expires_at, scopes}
  - Handle connection not found error
  - Handle connection not ready error (status != "completed")
  - Support org→GLOBAL fallback (automatic via config system)
- [ ] T041 [P] [US3] Create register_oauth_dependency() helper in workflows/engine/shared/oauth_helper.py
  - Insert into WorkflowOAuthDependencies (PartitionKey=connection_name, RowKey=workflow_id)
  - Insert into WorkflowOAuthDependencies_ByWorkflow (PartitionKey=workflow_id, RowKey=connection_name)
  - Dual-index maintenance
  - Called automatically when get_oauth_connection() is first invoked
- [ ] T042 [US3] Implement GET /api/oauth/credentials/{connection_name} endpoint in client/api/functions/oauth_api.py (depends on T021, T032)
  - Get connection from OAuthConnections table
  - Check status (must be "completed")
  - Get tokens from Config table via config_resolver
  - Return credentials (access_token, token_type, expires_at, scopes)
  - Return 404 if connection not found
  - Return 503 if status != "completed"
  - Log credential access for audit
- [ ] T043 [US3] Add workflow example documentation to quickstart.md showing get_oauth_connection() usage
- [ ] T044 [US3] Run contract and integration tests, verify User Story 3 works independently

**Checkpoint**: User Story 3 complete - Workflows can retrieve and use OAuth credentials

---

## Phase 6: User Story 4 - Automatic Token Refresh (Priority: P2)

**Goal**: Background job refreshes expiring tokens automatically every 30 minutes

**Independent Test**: Create OAuth connection with short-lived token, wait for scheduled job, verify token refreshed before expiration

### Tests for User Story 4 (TDD - Write FIRST, ensure FAIL)

- [ ] T045 [P] [US4] Integration test for token refresh in tests/integration/test_oauth_token_refresh.py
  - Create OAuth connection with token expiring in 3 hours
  - Mock OAuthProviderClient.refresh_access_token()
  - Trigger refresh job
  - Verify token refreshed and expires_at updated
  - Verify status remains "completed"
- [ ] T046 [P] [US4] Integration test for failed token refresh in tests/integration/test_oauth_token_refresh.py
  - Create OAuth connection with expired refresh token
  - Mock OAuthProviderClient.refresh_access_token() to fail
  - Trigger refresh job
  - Verify status changes to "failed"
  - Verify error message logged

### Implementation for User Story 4

- [ ] T047 [P] [US4] Add refresh_access_token() method to OAuthProviderClient in src/services/oauth_provider.py (depends on T030)
  - POST to token_url with refresh_token and client credentials
  - Parse new access_token, refresh_token (if provided), expires_at
  - Handle expired refresh token error (400)
  - Retry transient errors
- [ ] T048 [US4] Add token refresh methods to OAuthStorageService in src/services/oauth_storage_service.py (depends on T032)
  - find_expiring_connections(): Query all connections, filter by expires_at < now + 4 hours
  - refresh_connection_tokens(): Call OAuthProviderClient, update tokens in Config table
  - Handle refresh failures, update status to "failed"
- [ ] T049 [US4] Implement Azure Functions Timer trigger in client/api/functions/oauth_refresh_timer.py (depends on T047, T048)
  - Schedule: "0 */30 * * * *" (every 30 minutes)
  - Get all OAuth connections via oauth_storage_service.find_expiring_connections()
  - Filter: expires_at < now + 4 hours AND has tokens
  - Refresh in parallel using asyncio.gather()
  - For authorization_code flow: Use refresh_token
  - For client_credentials flow: Request new token with client credentials
  - Update tokens and expires_at in Config table
  - Update last_refresh_at in OAuthConnections table
  - Log refresh results to Application Insights
  - Handle failures gracefully (don't crash on single connection failure)
- [ ] T050 [US4] Add monitoring/alerting for token refresh failures (log to Application Insights)
- [ ] T051 [US4] Run integration tests, verify User Story 4 works independently

**Checkpoint**: User Story 4 complete - Tokens refresh automatically every 30 minutes

---

## Phase 7: User Story 5 - Manage and Monitor OAuth Connections (Priority: P2)

**Goal**: Enable administrators to update, delete, reconnect OAuth connections and manage workflow dependencies

**Independent Test**: List connections, edit configuration, delete connection with workflows, verify warnings and workflow disable cascade

### Tests for User Story 5 (TDD - Write FIRST, ensure FAIL)

- [ ] T052 [P] [US5] Contract test for PUT /api/oauth/connections/{connection_name} in tests/contract/test_oauth_api.py
  - Test updates configuration
  - Test marks connection as requiring reconnection
  - Test validation errors
- [ ] T053 [P] [US5] Contract test for DELETE /api/oauth/connections/{connection_name} in tests/contract/test_oauth_api.py
  - Test warning when workflows depend on connection
  - Test requires confirm_disable_workflows parameter
  - Test cascades to disable workflows
- [ ] T054 [P] [US5] Contract test for POST /api/oauth/connections/{connection_name}/test in tests/contract/test_oauth_api.py
  - Test manually triggers connection test
  - Test returns test result
- [ ] T055 [P] [US5] Integration test for connection deletion with workflow cascade in tests/integration/test_oauth_connection_deletion.py
  - Create OAuth connection
  - Register workflow dependency
  - Delete connection with confirmation
  - Verify workflow disabled in WorkflowDisableState table
  - Verify disable reason references OAuth connection

### Implementation for User Story 5

- [ ] T056 [P] [US5] Create UpdateOAuthConnectionRequest model in src/models/oauth_connection.py
- [ ] T057 [P] [US5] Create WorkflowDisableState model in src/models/workflow_disable_state.py
  - Fields: workflow_id, org_id, is_disabled, disabled_reason, disabled_at, disabled_by, related_oauth_connection
- [ ] T058 [P] [US5] Create WorkflowOAuthDependency model in src/models/workflow_dependency.py
  - Fields: connection_name, workflow_id, org_id, workflow_name, registered_at
- [ ] T059 [US5] Add update/delete methods to OAuthStorageService in src/services/oauth_storage_service.py (depends on T056-T058)
  - update_connection(): Update OAuthConnections table, mark as requiring reconnection
  - delete_connection(): Delete from OAuthConnections table, delete configs from Config table
  - find_dependent_workflows(): Query WorkflowOAuthDependencies by connection_name
  - disable_workflows(): Insert/update WorkflowDisableState for each workflow
- [ ] T060 [US5] Create WorkflowDisableService in src/services/workflow_disable_service.py (depends on T057)
  - disable_workflow(): Insert into WorkflowDisableState table
  - enable_workflow(): Update is_disabled=False in WorkflowDisableState
  - is_workflow_disabled(): Check WorkflowDisableState
  - list_disabled_workflows(): Query WorkflowDisableState by org_id
- [ ] T061 [US5] Implement PUT /api/oauth/connections/{connection_name} endpoint in client/api/functions/oauth_api.py (depends on T059)
  - Parse UpdateOAuthConnectionRequest
  - Update connection via oauth_storage_service
  - Mark status as requiring reconnection if URLs/credentials changed
  - Update client_secret in Config if provided
  - Return updated OAuthConnectionDetail
- [ ] T062 [US5] Implement DELETE /api/oauth/connections/{connection_name} endpoint in client/api/functions/oauth_api.py (depends on T059, T060)
  - Find dependent workflows via oauth_storage_service.find_dependent_workflows()
  - If workflows found and confirm_disable_workflows=false: Return 400 with workflow list
  - If confirmed: Delete connection, disable all workflows
  - Delete configs from Config table (oauth_{name}_client_secret, oauth_{name}_tokens, oauth_{name}_metadata)
  - Return list of disabled workflows
- [ ] T063 [US5] Implement POST /api/oauth/connections/{connection_name}/test endpoint in client/api/functions/oauth_api.py (depends on T031)
  - Get connection
  - Get tokens from Config
  - Call oauth_test_service.test_connection()
  - Update last_test_at
  - Return test result
- [ ] T064 [US5] Implement POST /api/oauth/workflows/{workflow_id}/dependencies endpoint in client/api/functions/oauth_api.py (depends on T058)
  - Register workflow dependency in dual-indexed tables
  - Idempotent (don't error if already registered)
- [ ] T065 [US5] Implement GET /api/oauth/workflows/disabled endpoint in client/api/functions/oauth_api.py (depends on T060)
  - List disabled workflows via workflow_disable_service
  - Return WorkflowDisableState list
- [ ] T066 [US5] Implement POST /api/oauth/workflows/{workflow_id}/enable endpoint in client/api/functions/oauth_api.py (depends on T060)
  - Enable workflow via workflow_disable_service
  - Return success message
- [ ] T067 [US5] Add workflow execution check for disabled state (integrate with existing workflow engine)
  - Check WorkflowDisableState before executing workflow
  - Raise WorkflowDisabledException if disabled
  - Include disable reason in error message
- [ ] T068 [US5] Run contract and integration tests, verify User Story 5 works independently

**Checkpoint**: User Story 5 complete - Full OAuth connection lifecycle management operational

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements across all user stories

- [ ] T069 [P] Add comprehensive error messages for all failure scenarios
- [ ] T070 [P] Add Application Insights logging for OAuth events (creation, authorization, refresh, deletion)
- [ ] T071 [P] Update OpenAPI spec in contracts/oauth-api.openapi.yaml if any changes made during implementation
- [ ] T072 [P] Code review and refactoring for consistency
- [ ] T073 Validate all acceptance scenarios from spec.md
- [ ] T074 Run full integration test suite
- [ ] T075 [P] Performance testing: Verify <100ms credential retrieval, <2s token refresh
- [ ] T076 [P] Security review: Verify secret masking, audit logging, CSRF protection (state parameter)
- [ ] T077 [P] Update quickstart.md with any implementation learnings
- [ ] T078 [P] Add TODO reminders for future enhancements (PKCE support, device code flow, etc.)
- [ ] T079 Run complete test suite one final time
- [ ] T080 Deploy to staging environment and validate

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - start immediately
- **Foundational (Phase 2)**: Depends on Setup - **BLOCKS all user stories**
- **User Stories 1-3 (Phase 3-5)**: All P1 stories depend on Foundational completion
  - **US1** is prerequisite for US2 (need connection to authorize)
  - **US2** is prerequisite for US3 (need tokens to retrieve)
  - US1→US2→US3 must be sequential
- **User Story 4 (Phase 6)**: P2, depends on US1-US3 completion
- **User Story 5 (Phase 7)**: P2, depends on US1-US3 completion, can run parallel with US4
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Foundation → Create connections
- **User Story 2 (P1)**: US1 → Complete authorization flow
- **User Story 3 (P1)**: US2 → Access credentials in workflows
- **User Story 4 (P2)**: US1, US2, US3 → Automatic refresh
- **User Story 5 (P2)**: US1, US3 → Manage/monitor connections

### Within Each User Story

- Tests written FIRST and MUST FAIL
- Models before services
- Services before endpoints/functions
- Core functionality before error handling
- Story fully tested before moving to next

### Parallel Opportunities

**Within Setup (Phase 1)**:
- All T002-T007 (directory creation) can run in parallel

**Within Foundational (Phase 2)**:
- T008-T011 (table creation) can run in parallel
- T012-T013 (config verification) can run in parallel

**Within User Story 1 (Phase 3)**:
- T014-T016 (contract tests) can run in parallel
- T017-T020 (models) can run in parallel

**Within User Story 2 (Phase 4)**:
- T027-T029 (tests) can run in parallel
- T030-T031 (OAuth client and test service) can run in parallel

**Within User Story 3 (Phase 5)**:
- T038-T039 (tests) can run in parallel
- T040-T041 (workflow helpers) can run in parallel

**Within User Story 4 (Phase 6)**:
- T045-T046 (integration tests) can run in parallel

**Within User Story 5 (Phase 7)**:
- T052-T055 (contract tests) can run in parallel
- T056-T058 (models) can run in parallel

**Within Polish (Phase 8)**:
- T069-T078 (documentation, logging, reviews) can run in parallel

**Across User Stories**:
- US4 and US5 (both P2) can run in parallel after US1-US3 complete

---

## Parallel Example: User Story 1

```bash
# Write all contract tests in parallel:
Task T014: "Contract test for POST /api/oauth/connections"
Task T015: "Contract test for GET /api/oauth/connections"
Task T016: "Contract test for GET /api/oauth/connections/{connection_name}"

# Create all models in parallel:
Task T017: "Create OAuthConnection model"
Task T018: "Create OAuthConnectionSummary model"
Task T019: "Create OAuthConnectionDetail model"
Task T020: "Create CreateOAuthConnectionRequest model"

# Then sequential implementation:
Task T021: "Implement OAuthStorageService" (depends on models)
Task T022: "Implement POST endpoint" (depends on service)
Task T023: "Implement GET list endpoint" (depends on service)
Task T024: "Implement GET detail endpoint" (depends on service)
```

---

## Implementation Strategy

### MVP First (User Stories 1-3 Only)

1. Complete Phase 1: Setup → Foundation ready
2. Complete Phase 2: Foundational → Tables and configs ready (**CRITICAL BLOCKER**)
3. Complete Phase 3: User Story 1 → Can create OAuth connections
4. Complete Phase 4: User Story 2 → Can authorize connections
5. Complete Phase 5: User Story 3 → Workflows can use OAuth
6. **STOP and VALIDATE**: Test full flow end-to-end
7. Deploy/demo if ready

**At this point, you have a fully functional MVP**: Workflows can use OAuth connections!

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → **DEMO** (can create connections)
3. Add User Story 2 → Test independently → **DEMO** (full authorization flow)
4. Add User Story 3 → Test independently → **DEPLOY MVP** (workflows can use OAuth)
5. Add User Story 4 → Test independently → **DEPLOY** (automatic refresh)
6. Add User Story 5 → Test independently → **DEPLOY** (full management)
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With 2-3 developers after Foundational phase completes:

1. Team completes Setup + Foundational together
2. Once Foundational done:
   - Developer A: User Story 1 → User Story 2 (sequential dependency)
   - Developer B: User Story 3 (needs US1+US2 complete first, so starts later)
   - Developer C: User Story 4 (can start after US1-US3 complete)
3. User Story 5 can be done in parallel with US4

---

## Notes

- **[P] tasks** = different files, can run in parallel
- **[Story] label** maps task to specific user story for traceability
- **Tests required**: Constitutional Principle IV mandates test-first development
- **Each user story independently testable**: Delivers incremental value
- **Verify tests fail** before implementing each story
- **Commit after each task** or logical group
- **Stop at checkpoints** to validate story independently
- **Foundational phase is critical**: Nothing can start until Phase 2 completes
- **US1→US2→US3 are sequential**: Each builds on the previous (create → authorize → use)
- **US4 and US5 can be parallel**: Both P2, both independent after core MVP complete

---

## Task Summary

**Total Tasks**: 80
**Per User Story**:
- Setup: 7 tasks
- Foundational: 6 tasks (BLOCKING)
- User Story 1: 13 tasks (Tests: 3, Implementation: 10)
- User Story 2: 11 tasks (Tests: 3, Implementation: 8)
- User Story 3: 7 tasks (Tests: 2, Implementation: 5)
- User Story 4: 7 tasks (Tests: 2, Implementation: 5)
- User Story 5: 17 tasks (Tests: 4, Implementation: 13)
- Polish: 12 tasks

**Parallel Opportunities**: 35+ tasks marked [P] for parallel execution
**Independent Test Criteria**: Each user story has clear acceptance scenarios from spec.md
**MVP Scope**: Phase 1 + Phase 2 + Phase 3-5 (User Stories 1-3) = First deployable increment

---

## Next Steps

1. Start with Phase 1 (Setup) - quick, no blockers
2. Complete Phase 2 (Foundational) - CRITICAL, blocks everything
3. Implement User Stories 1-3 sequentially (MVP)
4. Validate MVP end-to-end
5. Add User Stories 4-5 for production readiness
6. Polish and deploy

**Estimated MVP completion**: User Stories 1-3 (~40 tasks) delivers working OAuth system for workflows
