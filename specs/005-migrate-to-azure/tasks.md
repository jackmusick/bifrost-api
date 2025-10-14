# Tasks: Azure Functions Docker Runtime Migration (Unified Architecture)

**Feature Branch**: `005-migrate-to-azure`
**Input**: Design documents from `/specs/005-migrate-to-azure/`
**Architecture**: Single unified Function App (API + workflow engine merged)
**Organization**: Tasks grouped by user story for independent implementation and testing

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story this task belongs to (US1, US2, US3, US4)
- Exact file paths included in descriptions

**Total Tasks**: 96
**MVP Scope**: User Story 1 + User Story 2 (T001-T038)
**Full Scope**: All 4 User Stories

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Merge workflows into api project and initialize unified Function App structure

- [X] T001 Copy engine directory from `/workflows/engine/` to `/api/engine/` preserving all modules (shared/, data_providers/, admin/, execute/)
- [X] T002 Copy workspace directory from `/workflows/workspace/` to `/api/workspace/` with example workflows
- [X] T003 [P] Copy test suites from `/workflows/tests/` to `/api/tests/engine/` to maintain workflow engine test coverage
- [X] T004 [P] Merge `/workflows/requirements.txt` into `/api/requirements.txt` (add azure-storage-file-share>=12.14.1, debugpy>=1.8.0, gitpython for sync)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Update `/api/function_app.py` to import and initialize workspace discovery from workflows pattern (discover_workspace_modules function)
- [X] T006 [P] Add import restrictor initialization to `/api/function_app.py` (install_import_restrictions from engine.shared.import_restrictor)
- [X] T007 [P] Add table initialization to `/api/function_app.py` (init_tables from engine.shared.init_tables)
- [X] T008 [P] Import engine data providers in `/api/function_app.py` (import engine.data_providers for built-in providers)
- [X] T009 Deprecated proxy endpoints in `/api/functions/workflows.py` with documentation (direct engine endpoints already registered in function_app.py, proxy kept for backwards compatibility)
- [X] T010 [P] Removed WORKFLOWS_ENGINE_URL and WORKFLOWS_ENGINE_FUNCTION_KEY from `/api/local.settings.example.json` (replaced with WORKSPACE_PATH, TMP_PATH, ENABLE_DEBUGGING for unified architecture)
- [X] T011 [P] Created workspace service layer in `/api/services/workspace_service.py` (list_files, read_file, write_file, delete_file using standard filesystem for mounted directories) + temp file service in `/api/services/temp_file_service.py` (PowerShell-style helpers)
- [X] T012 [P] Created ZIP generation utility in `/api/services/zip_service.py` (create_workspace_zip with in-memory BytesIO buffer per research.md Decision 8, uses workspace_service)

**Checkpoint**: Foundation ready - unified Function App structure complete, user stories can begin

---

## Phase 3: User Story 1 - One-Command Local Development Setup (Priority: P1) 🎯 MVP

**Goal**: Developers run `docker compose up` and have fully functioning local environment with optional debugging

**Independent Test**: Developer runs docker-compose.dev.yml, accesses http://localhost:7071/api/health, executes workflow, optionally attaches debugger with breakpoints in workspace code

### Implementation for User Story 1

- [ ] T013 [P] [US1] Create Dockerfile in `/api/Dockerfile` based on mcr.microsoft.com/azure-functions/python:4-python3.11 (per research.md Decision 1)
- [ ] T014 [P] [US1] Configure Dockerfile to copy unified api directory to /home/site/wwwroot and install requirements.txt
- [ ] T015 [P] [US1] Add debugpy port exposure (5678) to `/api/Dockerfile` for VS Code debugging
- [ ] T016 [P] [US1] Add conditional debugpy initialization to `/api/function_app.py` with ENABLE_DEBUGGING guard (debugpy.listen + wait_for_client per research.md Decision 2)
- [ ] T017 [US1] Create docker-compose.dev.yml in repository root with azurite service (ports 10000-10003 for Blob/Queue/Table/Files)
- [ ] T018 [US1] Add unified api service to docker-compose.dev.yml building from `/api/Dockerfile` with ports 7071:80 and 5678:5678
- [ ] T019 [US1] Configure environment variables in docker-compose.dev.yml: AzureWebJobsStorage (azurite connection), AZURE_FILES_CONNECTION_STRING, ENABLE_DEBUGGING, PYTHONPATH=/home/site/wwwroot, WORKSPACE_PATH=/workspace
- [ ] T020 [US1] Add volume mounts to docker-compose.dev.yml: ./api:/home/site/wwwroot (live reload), workspace-data:/workspace, tmp-data:/tmp
- [ ] T021 [P] [US1] Create .dockerignore in `/api/.dockerignore` excluding __pycache__, *.pyc, .git/, .vscode/, tests/, .pytest_cache/
- [ ] T022 [P] [US1] Create VS Code launch configuration in `.vscode/launch.json` for "Attach to Docker Functions" with pathMappings localRoot=${workspaceFolder}/api, remoteRoot=/home/site/wwwroot

**Checkpoint**: User Story 1 complete - Local development environment fully functional with unified Function App

---

## Phase 4: User Story 2 - Simplified Production Deployment (Priority: P1) 🎯 MVP

**Goal**: Administrators run ARM template and get operational production environment with single unified Function App containing both API and workflow engine

**Independent Test**: Execute ARM deployment, access Static Web App URL, trigger workflow via UI, verify execution without manual configuration (no workflow URL or function key needed)

### Implementation for User Story 2

- [ ] T023 [P] [US2] Create ARM template main file in `/deployment/main.bicep` with parameters: location, resourceGroupName, dockerHubImage, frontendGitHubRepoUrl, frontendGitHubToken, workspacesQuotaGB, tmpQuotaGB
- [ ] T024 [P] [US2] Create Storage Account module in `/deployment/modules/storage.bicep` with Azure Files shares: workspaces (Hot tier) and tmp (Hot tier) per research.md Decision 3
- [ ] T025 [P] [US2] Create SINGLE unified Function App module in `/deployment/modules/functions.bicep` with container deployment (kind='functionapp,linux,container', linuxFxVersion='DOCKER|${dockerHubImage}')
- [ ] T026 [US2] Configure Azure Files mounting in `/deployment/modules/functions.bicep` siteConfig.azureStorageAccounts: workspaces→/workspace, tmp→/tmp (per research.md Decision 3)
- [ ] T027 [US2] Add Function App app settings in `/deployment/modules/functions.bicep`: WEBSITE_RUN_FROM_PACKAGE=0, WEBSITES_ENABLE_APP_SERVICE_STORAGE=true, WORKSPACE_PATH=/workspace, AzureWebJobsStorage, Key Vault references
- [ ] T028 [P] [US2] Create Static Web App module in `/deployment/modules/staticwebapp.bicep` with GitHub integration (repositoryUrl, repositoryToken, buildProperties per research.md Decision 4)
- [ ] T029 [P] [US2] Create Key Vault module in `/deployment/modules/keyvault.bicep` with RBAC for Function App managed identity (read secrets permission)
- [ ] T030 [P] [US2] Create Application Insights module in `/deployment/modules/appinsights.bicep` linked to Function App via APPINSIGHTS_INSTRUMENTATIONKEY
- [ ] T031 [US2] Add ARM template outputs to `/deployment/main.bicep`: functionAppUrl, staticWebAppUrl, githubWebhookUrl, keyVaultName
- [ ] T032 [P] [US2] Create ARM template parameters file template in `/deployment/parameters/template.json` with all required parameters and defaults (workspacesQuotaGB=100, tmpQuotaGB=50)
- [ ] T033 [P] [US2] Create deployment script in `/scripts/deploy-production.sh` with az group create and az deployment group create commands
- [ ] T034 [P] [US2] Update quickstart.md "First Production Deployment" section with build/push Docker image steps and ARM deployment instructions
- [ ] T035 [US2] Test: Deploy ARM template to test subscription and verify SINGLE Function App created with both API and workflow engine functionality
- [ ] T036 [US2] Test: Verify Azure Files shares mounted at /workspace and /tmp in Function App container (SSH into container: ls /workspace, ls /tmp)
- [ ] T037 [US2] Test: Trigger workflow from UI and verify execution completes via direct function invocation without cross-service HTTP calls
- [ ] T038 [US2] Test: Verify Static Web App auto-deploys from GitHub when frontend code pushed (GitHub Actions workflow created by ARM template)

**Checkpoint**: User Story 2 complete - Production deployment fully automated with unified Function App (API + workflow engine in single service)

---

## Phase 5: User Story 3 - GitHub Integration for Workspace Sync (Priority: P2)

**Goal**: Teams connect GitHub repository and changes automatically sync to platform via webhooks within 2 minutes

**Independent Test**: Connect GitHub repository via API, push changes, observe workspace files updated within 2 minutes without manual intervention

### Implementation for User Story 3

- [ ] T039 [P] [US3] Add GitHubConnection entity model to `/api/shared/models.py` (PartitionKey="GITHUB_CONNECTIONS", RowKey=OrgId/GLOBAL, fields from data-model.md)
- [ ] T040 [P] [US3] Add GitHubSyncJob entity model to `/api/shared/models.py` (PartitionKey="SYNC_JOBS", RowKey=CommitSha, status enum, fields from data-model.md)
- [ ] T041 [P] [US3] Create GitHub sync service in `/api/services/github_sync_service.py` with rsync-style algorithm (three-phase: clone, diff, apply per research.md Decision 6)
- [ ] T042 [US3] Implement git clone --depth 1 phase in sync service (shallow clone to /tmp/sync-{commitsha} for performance)
- [ ] T043 [US3] Implement file tree building with SHA256 hashing in sync service (GitHub files + Azure Files comparison)
- [ ] T044 [US3] Implement diff computation in sync service (to_add, to_update, to_delete sets)
- [ ] T045 [US3] Implement parallel file operations in sync service using asyncio.gather with limit=10 (uploads/deletes)
- [ ] T046 [P] [US3] Create GitHub connections blueprint in `/api/functions/github_connections.py` (POST /github-connections to create connection per github-sync-api.yaml)
- [ ] T047 [P] [US3] Implement GET /github-connections endpoint (list all connections for MSP users)
- [ ] T048 [P] [US3] Implement GET /github-connections/{orgId} endpoint (get single connection details)
- [ ] T049 [P] [US3] Implement PUT /github-connections/{orgId} endpoint (update connection: branch, isEnabled, PAT)
- [ ] T050 [P] [US3] Implement DELETE /github-connections/{orgId} endpoint (disconnect GitHub, workspace files remain)
- [ ] T051 [US3] Add webhook secret generation and Key Vault storage in connection creation (generate 32-char secret, store in Key Vault with reference in Table Storage)
- [ ] T052 [US3] Create GitHub webhook receiver in `/api/functions/github_webhook.py` (POST /github-webhook with HMAC-SHA256 signature verification per research.md Decision 5)
- [ ] T053 [US3] Implement HMAC signature verification using hmac.compare_digest for timing-attack resistance (X-Hub-Signature-256 header validation)
- [ ] T054 [US3] Implement idempotency check in webhook handler (query GitHubSyncJob by CommitSha, return 200 if already processed)
- [ ] T055 [US3] Implement sync job queueing in webhook handler (create GitHubSyncJob entity with status="queued", queue message to Azure Queue, return 202)
- [ ] T056 [P] [US3] Create sync job processor in `/api/functions/process_sync_jobs.py` (Azure Queue trigger to process queued sync jobs)
- [ ] T057 [US3] Implement sync job processing logic: update status="processing", call sync service, update with Files* counts and DurationMs, set status="completed"
- [ ] T058 [US3] Add error handling and retry logic to sync job processor (max 3 retries with RetryCount tracking, status="failed" on final failure)
- [ ] T059 [US3] Add workflow reload trigger after successful sync (call registry.reload_workflows() to make updated workflows immediately available per FR-015)
- [ ] T060 [P] [US3] Create sync jobs monitoring blueprint in `/api/functions/sync_jobs.py` (GET /sync-jobs with filtering per github-sync-api.yaml)
- [ ] T061 [P] [US3] Implement GET /sync-jobs/{commitSha} endpoint (get specific sync job details)
- [ ] T062 [P] [US3] Update quickstart.md "GitHub Integration Setup" section with connection creation, webhook configuration, and testing steps
- [ ] T063 [US3] Test: Create GitHub connection via API and verify webhook URL and secret returned
- [ ] T064 [US3] Test: Configure webhook in GitHub repository with secret from Key Vault
- [ ] T065 [US3] Test: Push commit to GitHub and verify webhook received with valid signature
- [ ] T066 [US3] Test: Verify sync job queued and processed successfully (check sync job entity status transitions)
- [ ] T067 [US3] Test: Verify workspace files updated in /workspace share after sync completes (compare file content before/after)
- [ ] T068 [US3] Test: Verify workflow reload triggered and updated workflows executable (execute workflow to confirm new code running)
- [ ] T069 [US3] Test: Measure end-to-end time from GitHub push to executable workflow (<2 minutes per SC-003)

**Checkpoint**: User Story 3 complete - GitHub sync fully functional with automatic workspace updates

---

## Phase 6: User Story 4 - Manual Workflow Script Management (Priority: P2)

**Goal**: Users without GitHub can create/edit workflow scripts directly via UI with full CRUD operations on /workspace files

**Independent Test**: With no GitHub connected, create new workflow file via API, save it, execute it successfully

### Implementation for User Story 4

- [ ] T070 [P] [US4] Create workspace service in `/api/services/workspace_service.py` with file operations wrapping azure_files_service (list, read, create, update, delete with validations)
- [ ] T071 [US4] Add file path validation to workspace service (no ".." traversal, no leading "/", no invalid characters, relative paths only)
- [ ] T072 [US4] Add file size validation to workspace service (max 10MB per spec assumption FR-012)
- [ ] T073 [US4] Add UTF-8 validation for text files in workspace service (Python, YAML, JSON files must be valid UTF-8)
- [ ] T074 [P] [US4] Create workspace files blueprint in `/api/functions/workspace_files.py` (GET /workspace/files to list files per workspace-files-api.yaml)
- [ ] T075 [P] [US4] Implement GET /workspace/files/{filePath} endpoint (read file content, return JSON with metadata or text/plain based on Accept header)
- [ ] T076 [US4] Implement PUT /workspace/files/{filePath} endpoint (create/update file with GitHub sync enabled check, return 403 if GitHubConnection.IsEnabled=true)
- [ ] T077 [US4] Add immediate workflow reload after file save in PUT endpoint (call registry.reload_workflows() to make changes available in <5 seconds per SC-004)
- [ ] T078 [P] [US4] Implement DELETE /workspace/files/{filePath} endpoint (delete file with GitHub sync check, reload workflows after deletion)
- [ ] T079 [P] [US4] Implement POST /workspace/directories/{dirPath} endpoint (create directory with GitHub sync check)
- [ ] T080 [P] [US4] Implement DELETE /workspace/directories/{dirPath} endpoint (delete directory recursively with GitHub sync check)
- [ ] T081 [US4] Create workspace download endpoint in `/api/functions/workspace_files.py` (GET /workspace/download generates ZIP per research.md Decision 8)
- [ ] T082 [US4] Implement in-memory ZIP generation using zipfile.ZipFile with BytesIO buffer (add all files from /workspace share, rewind buffer, return with Content-Disposition header)
- [ ] T083 [P] [US4] Create workspace status endpoint in `/api/functions/workspace_files.py` (GET /workspace/status returns mode, isReadOnly, statistics per workspace-files-api.yaml)
- [ ] T084 [US4] Implement workspace statistics calculation in status endpoint (totalFiles, totalDirectories, totalSize, lastModified from Azure Files share)
- [ ] T085 [P] [US4] Update quickstart.md "Manual Editing Mode" section with disconnect GitHub, file CRUD, and download backup instructions
- [ ] T086 [US4] Test: With no GitHub connection, create file via PUT /workspace/files/{filePath} and verify persisted to Azure Files
- [ ] T087 [US4] Test: Update existing file and verify changes reflected in workflow execution within 5 seconds (SC-004)
- [ ] T088 [US4] Test: Delete file via DELETE endpoint and verify removed from Azure Files share
- [ ] T089 [US4] Test: Create directory via POST /workspace/directories/{dirPath} and verify created in Azure Files
- [ ] T090 [US4] Test: Enable GitHub connection and verify file editing returns 403 Forbidden with appropriate error message
- [ ] T091 [US4] Test: Download workspace as ZIP and verify all files included with correct directory structure
- [ ] T092 [US4] Test: ZIP download completes in <10 seconds for 50MB workspace (SC-004a)
- [ ] T093 [US4] Test: Disconnect GitHub and verify manual editing immediately re-enabled (no delay)

**Checkpoint**: User Story 4 complete - Manual editing fully functional with proper GitHub sync enforcement

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements affecting multiple user stories

- [ ] T094 [P] Add comprehensive error handling across all endpoints with structured error responses (Error model from contracts)
- [ ] T095 [P] Add structured logging for all major operations using Application Insights (sync jobs, file operations, deployments, workflow executions)
- [ ] T096 [P] Create health check endpoint in `/api/functions/health.py` with Azure Files connectivity verification (check /workspace and /tmp share accessibility per FR-019)
- [ ] T097 [P] Add performance monitoring for sync operations (track DurationMs, file counts in GitHubSyncJob entities)
- [ ] T098 [P] Create GitHub Actions workflow in `.github/workflows/build-release.yml` for automated Docker image builds on tag push to Docker Hub
- [ ] T099 [P] Configure Docker image tagging strategy in build workflow (latest + semantic versioning tags, extract bifrost.pyi as release artifact)
- [ ] T100 [P] Update CLAUDE.md with new technologies added in this spec: Docker, Azure Files SDK (azure-storage-file-share), Bicep/ARM, debugpy, Azurite, GitPython
- [ ] T101 Security review: Verify HMAC signature implementation uses hmac.compare_digest (timing-attack resistant, research.md Decision 5)
- [ ] T102 Security review: Verify all secrets stored in Key Vault with references in Table Storage (webhook secrets, GitHub PATs, not in environment variables)
- [ ] T103 Security review: Verify file path validation prevents directory traversal attacks (reject paths containing "..", absolute paths)
- [ ] T104 [P] Performance optimization: Verify parallel file uploads/downloads in sync service use asyncio.gather with limit=10 (research.md Decision 6)
- [ ] T105 [P] Add exponential backoff retry logic for failed sync jobs (max 3 attempts per FR-009)
- [ ] T106 Verify ARM template RBAC assignments: Function App managed identity has Storage Blob Data Contributor (Azure Files access) and Key Vault Secrets User (secret access)
- [ ] T107 Test: End-to-end scenario - local development with docker-compose → commit changes → deploy ARM template → GitHub sync → manual edit → download backup
- [ ] T108 [P] Create migration guide document in `/docs/migration-from-separate-function-apps.md` for existing deployments (manual steps, out of scope for automation per spec)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US1 (Local Dev) and US2 (Production Deployment): Can proceed in parallel (both P1 priority)
  - US3 (GitHub Sync) and US4 (Manual Editing): Can proceed in parallel after US1/US2 (both P2 priority)
- **Polish (Phase 7)**: Depends on desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Foundational (T005-T012) - No dependencies on other stories
- **User Story 2 (P1)**: Depends on Foundational (T005-T012) - Can run in parallel with US1
- **User Story 3 (P2)**: Depends on Foundational (T005-T012) and azure_files_service (T011) - Independent from US1/US2
- **User Story 4 (P2)**: Depends on Foundational (T005-T012), azure_files_service (T011), and zip_service (T012) - Independent from US1/US2/US3

### Within Each User Story

- **US1**: Dockerfile setup → docker-compose configuration → debugging setup → testing
- **US2**: ARM template resources → modules → outputs → deployment script → testing
- **US3**: Models → sync service → connection CRUD → webhook receiver → sync processor → monitoring endpoints → testing
- **US4**: Service layer → file CRUD endpoints → download ZIP → status endpoint → testing

### Parallel Opportunities

- Setup: T001 (engine copy), T002 (workspace copy), T003 (tests copy), T004 (requirements merge) can all run in parallel
- Foundational: T006 (import restrictor), T007 (tables), T008 (data providers), T010 (remove old config), T011 (azure files service), T012 (ZIP service) can run in parallel after T005
- US1: T013-T016 (Dockerfile setup), T021 (dockerignore), T022 (VS Code config) can run in parallel; T017-T020 (docker-compose) sequential
- US2: T024-T030 (all ARM modules) can run in parallel; T032-T034 (parameters, script, docs) can run in parallel
- US3: T039-T040 (models), T046-T050 (connection endpoints), T060-T061 (sync job endpoints) can run in parallel within their groups
- US4: T074-T080 (all file/directory endpoints) can run in parallel; T081-T083 (download and status) can run in parallel
- Polish: All tasks T094-T108 can run in parallel except T107 (integration test) which depends on all features

---

## Parallel Example: Foundational Phase

```bash
# After T005 completes (function_app.py updated), launch in parallel:
Task T006: "Add import restrictor to /api/function_app.py"
Task T007: "Add table initialization to /api/function_app.py"
Task T008: "Import engine data providers in /api/function_app.py"
Task T010: "Remove old workflow engine config from /api/shared/config.py"
Task T011: "Create azure_files_service.py"
Task T012: "Create zip_service.py"

# These touch different files/functions and can proceed simultaneously
```

---

## Parallel Example: User Story 1 + User Story 2

```bash
# After Foundational completes, launch both P1 stories in parallel:

# Team Member A works on US1 (Local Development):
Task T013-T016: "Dockerfile setup in /api"
Task T017-T020: "docker-compose.dev.yml configuration"
Task T021-T022: "dockerignore and VS Code config"

# Team Member B works on US2 (Production Deployment):
Task T023: "Create main.bicep"
Task T024-T030: "Create all ARM modules in parallel"
Task T031-T034: "Outputs, parameters, script, docs"

# Both stories progress independently with no conflicts
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 - P1 Priority)

1. Complete Phase 1: Setup (T001-T004) - Merge projects
2. Complete Phase 2: Foundational (T005-T012) - CRITICAL blocking phase (unified Function App)
3. Complete Phase 3: User Story 1 (T013-T022) - Local development with Docker
4. Complete Phase 4: User Story 2 (T023-T038) - Production deployment with ARM template
5. **STOP and VALIDATE**: Test local docker-compose, deploy to Azure, trigger workflow via UI
6. Deploy/demo MVP (local dev + production deployment with unified architecture)

### Incremental Delivery

1. Setup + Foundational → Unified Function App foundation ready
2. Add User Story 1 → Test local docker-compose → Demo (working local development!)
3. Add User Story 2 → Test ARM deployment → Demo (working production with single Function App!)
4. Add User Story 3 → Test GitHub sync → Demo (automated workspace updates!)
5. Add User Story 4 → Test manual editing → Demo (complete platform with dual edit modes!)
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers after Foundational phase completes:

1. Team completes Setup + Foundational together (T001-T012)
2. Once Foundational done:
   - Developer A: User Story 1 (Local Development)
   - Developer B: User Story 2 (Production Deployment)
   - Progress in parallel since they touch different concerns
3. After US1/US2 complete (MVP delivered):
   - Developer C: User Story 3 (GitHub Sync)
   - Developer D: User Story 4 (Manual Editing)
   - Progress in parallel since they are independent features
4. All developers: Polish phase together (T094-T108)

---

## Success Metrics

After completing all tasks, verify these success criteria from spec.md:

- **SC-001**: Local dev starts in <5 minutes ✓ (US1)
- **SC-002**: Production deployment in <30 minutes ✓ (US2)
- **SC-003**: GitHub sync in <2 minutes ✓ (US3)
- **SC-004**: Manual edits available in <5 seconds ✓ (US4)
- **SC-004a**: ZIP download in <10 seconds ✓ (US4)
- **SC-005**: Debugger attachment works ✓ (US1)
- **SC-006**: ARM template 95% first-time success ✓ (US2)
- **SC-007**: 100 executions/hour ✓ (US2)
- **SC-008**: 99.9% workspace uptime ✓ (US2)
- **SC-009**: Editor ops <2 seconds ✓ (US4)
- **SC-010**: Zero manual config steps ✓ (US2 - unified architecture eliminates workflow URL/function key)
- **SC-011**: Workflow execution latency <100ms ✓ (US2 - direct invocation, no HTTP overhead)

---

## Key Architectural Changes from Original Plan

**Unified Function App Benefits** (FR-001a):
- Single container image combining API and workflow engine
- Direct function invocation (no HTTP proxy between API and workflows)
- No workflow engine URL or function key configuration needed (SC-010, SC-011)
- Simpler deployment (1 Function App instead of 2)
- Reduced operational complexity (50% fewer services)
- Lower execution latency (<100ms vs ~200-500ms with HTTP proxy)

**Migration Note**: Existing deployments with separate API and workflow Function Apps are not automatically migrated (out of scope per spec). See `/docs/migration-from-separate-function-apps.md` after T108 completion.

---

## Notes

- [P] tasks = different files, no dependencies → can run in parallel
- [Story] label (US1, US2, US3, US4) maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Foundational phase (T005-T012) is CRITICAL and blocks all user stories - prioritize completion
- Unified Function App architecture eliminates cross-service dependencies and configuration complexity
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- User Stories 1 and 2 are P1 (MVP) - deliver these first for maximum value
- User Stories 3 and 4 are P2 (enhancements) - can be delivered incrementally after MVP
- Total estimated effort: 4-5 weeks for experienced developer (MVP: 2 weeks, full: 4-5 weeks)
