# Implementation Tasks: Azure Functions Docker Runtime Migration

**Branch**: `005-migrate-to-azure` | **Date**: 2025-01-13
**Plan**: [plan.md](./plan.md) | **Spec**: [spec.md](./spec.md)

## Overview

This document breaks down the implementation into executable tasks organized by user story priority. Each user story represents an independently testable increment.

**Total Tasks**: 43
**MVP Scope**: User Story 1 (T001-T010) - One-Command Local Development Setup
**Full Scope**: All 4 User Stories

---

## Phase 1: Setup & Initialization

Foundation tasks that prepare the project structure (no tests required for infrastructure setup).

### T001 [US-Setup] - Initialize Docker support for Azure Functions

**File**: `workflows/Dockerfile`
**Description**: Run `func init --docker-only` in workflows directory to generate Dockerfile with Python 3.11 Azure Functions base image
**Details**:

-   Base image: `mcr.microsoft.com/azure-functions/python:4-python3.11`
-   Copy function code to `/home/site/wwwroot`
-   Install Python dependencies from requirements.txt
-   Expose port 5678 for debugpy
    **Acceptance**: Dockerfile exists and builds successfully with `docker build -t test ./workflows`

### T002 [US-Setup] - Add azure-storage-file-share dependency

**File**: `workflows/requirements.txt`
**Description**: Add azure-storage-file-share SDK and debugpy to requirements
**Details**:

```
azure-storage-file-share>=12.14.1
debugpy>=1.8.0
```

**Acceptance**: `pip install -r requirements.txt` succeeds

### T003 [US-Setup] - Create infrastructure directory structure

**Files**: `infrastructure/main.bicep`, `infrastructure/modules/`, `infrastructure/parameters/`
**Description**: Create ARM template directory structure for Bicep modules
**Details**:

-   Create `infrastructure/` directory
-   Create `infrastructure/modules/` for resource modules
-   Create `infrastructure/parameters/` for environment configs
    **Acceptance**: Directory structure exists and is committed

---

## Phase 2: User Story 1 - One-Command Local Development Setup (P1)

**Goal**: Developer runs single docker compose command and has fully functioning local platform with debugging support

**Independent Test**: Developer clones repo, runs `docker-compose -f docker-compose.dev.yml up`, accesses UI at http://localhost:7071, sets breakpoint in workspace code, debugger pauses execution

### T004 [US1] - Create docker-compose.dev.yml with Azurite

**File**: `docker-compose.dev.yml` (repository root)
**Description**: Create docker-compose configuration for local development with Azurite and Azure Functions
**Details**:

-   Azurite service with all endpoints (Blob:10000, Queue:10001, Table:10002, Files:10003)
-   Azure Functions service building from ./workflows/Dockerfile
-   Volume mounts: ./workflows → /home/site/wwwroot (live reload)
-   Volume mounts: workspace-data → /workspace, tmp-data → /tmp
-   Ports: 7071:80 (Functions), 5678:5678 (debugpy)
-   Environment: AzureWebJobsStorage, AZURE_FILES_CONNECTION_STRING, ENABLE_DEBUGGING, PYTHONPATH
-   Depends on: azurite
    **Acceptance**: `docker-compose -f docker-compose.dev.yml up` starts both services without errors

### T005 [US1] - Add conditional debugpy initialization to function startup

**File**: `workflows/function_app.py` or `workflows/__init__.py`
**Description**: Add debugpy.listen() with ENABLE_DEBUGGING guard to enable VS Code attachment
**Details**:

```python
import os
if os.getenv('ENABLE_DEBUGGING') == 'true':
    import debugpy
    debugpy.listen(("0.0.0.0", 5678))
    print("⏳ Waiting for debugger attach on port 5678...")
    debugpy.wait_for_client()
    print("✅ Debugger attached")
```

**Acceptance**: When ENABLE_DEBUGGING=true, function waits for debugger; when false, starts normally

### T006 [US1] - Create VS Code launch configuration for Docker debugging

**File**: `.vscode/launch.json`
**Description**: Add "Attach to Docker Functions" debug configuration
**Details**:

```json
{
    "name": "Attach to Docker Functions",
    "type": "python",
    "request": "attach",
    "connect": { "host": "localhost", "port": 5678 },
    "pathMappings": [
        {
            "localRoot": "${workspaceFolder}/workflows",
            "remoteRoot": "/home/site/wwwroot"
        }
    ]
}
```

**Acceptance**: VS Code can attach to running container and hit breakpoints

### T007 [US1] - Update .dockerignore for optimal build

**File**: `workflows/.dockerignore`
**Description**: Exclude unnecessary files from Docker image
**Details**:

```
__pycache__/
*.pyc
.git/
.vscode/
.env
local.settings.json
.pytest_cache/
tests/
```

**Acceptance**: Docker build excludes listed files (check with `docker history`)

### T008 [US1] - Document local development setup in quickstart

**File**: `README.md` or `docs/local-development.md`
**Description**: Add local development section with docker-compose instructions
**Details**:

-   Prerequisites (Docker Desktop)
-   Commands: `docker-compose -f docker-compose.dev.yml up`
-   How to enable debugging (ENABLE_DEBUGGING=true)
-   How to attach VS Code debugger
-   Troubleshooting common issues
    **Acceptance**: Following documented steps results in running local environment

### T009 [US1] [P] - Test local development workflow (manual verification)

**Description**: Manual test to verify US1 acceptance criteria
**Steps**:

1. Clone repository
2. Run `docker-compose -f docker-compose.dev.yml up`
3. Verify Functions accessible at http://localhost:7071
4. Set ENABLE_DEBUGGING=true and restart
5. Set breakpoint in workspace code
6. Attach VS Code debugger
7. Trigger function execution
8. Verify debugger pauses at breakpoint
9. Modify workspace file and save
10. Verify change immediately available (no restart)
    **Acceptance**: All steps complete successfully in under 5 minutes

### T010 [US1-Checkpoint] - User Story 1 Complete ✓

**Verification**: MVP is now functional - developers can run platform locally with debugging

---

## Phase 3: User Story 2 - Simplified Production Deployment (P1)

**Goal**: Administrator runs ARM template and has fully operational production environment with all Azure resources

**Independent Test**: Administrator runs `az deployment group create ...`, waits ~30 minutes, accesses Static Web App URL, logs in, triggers workflow, sees successful execution

### T011 [US2] - Create main ARM template (main.bicep)

**File**: `infrastructure/main.bicep`
**Description**: Create main Bicep template that orchestrates all modules
**Details**:

-   Parameters: location, resourceGroupName, dockerHubImage, frontendGitHubRepo, storageQuotas
-   Modules: functions, staticwebapp, storage, keyvault, appinsights
-   Outputs: functionAppUrl, staticWebAppUrl, githubWebhookUrl
    **Acceptance**: Template syntax validates with `az bicep build`

### T012 [US2] [P] - Create Storage Account module

**File**: `infrastructure/modules/storage.bicep`
**Description**: Bicep module for Storage Account with Azure Files shares
**Details**:

-   Storage Account: Standard_LRS, StorageV2, TLS 1.2, HTTPS only
-   File Services: workspaces share (Hot tier, configurable quota), tmp share (Hot tier, configurable quota)
-   Outputs: storageAccountName, storageAccountKey, connectionString
    **Acceptance**: Module deploys successfully in isolation

### T013 [US2] [P] - Create Azure Functions module with Docker support

**File**: `infrastructure/modules/functions.bicep`
**Description**: Bicep module for container-enabled Azure Functions
**Details**:

-   App Service Plan: Linux, B1 or higher SKU
-   Function App: kind='functionapp,linux,container'
-   linuxFxVersion: 'DOCKER|{dockerHubImage}'
-   App Settings: WEBSITE_RUN_FROM_PACKAGE=0, WEBSITES_ENABLE_APP_SERVICE_STORAGE=true
-   azureStorageAccounts: workspaces (/workspace mount), tmp (/tmp mount)
-   Outputs: functionAppName, functionAppUrl
    **Acceptance**: Module deploys and mounts Azure Files correctly

### T014 [US2] [P] - Create Static Web App module with GitHub integration

**File**: `infrastructure/modules/staticwebapp.bicep`
**Description**: Bicep module for Static Web App with GitHub CI/CD
**Details**:

-   Static Site: Free or Standard SKU
-   repositoryUrl, repositoryToken, branch parameters
-   buildProperties: appLocation='/client', outputLocation='dist'
-   Outputs: staticWebAppUrl, deploymentToken
    **Acceptance**: Module creates SWA and GitHub Actions workflow

### T015 [US2] [P] - Create Key Vault module

**File**: `infrastructure/modules/keyvault.bicep`
**Description**: Bicep module for Azure Key Vault
**Details**:

-   Key Vault: enableRbacAuthorization=true, enabledForDeployment=true
-   Access policies: Grant Function App managed identity read secrets
-   Outputs: keyVaultName, keyVaultUri
    **Acceptance**: Module deploys and Function App can access secrets

### T016 [US2] [P] - Create Application Insights module

**File**: `infrastructure/modules/appinsights.bicep`
**Description**: Bicep module for Application Insights
**Details**:

-   Application Insights: kind='web'
-   Link to Function App via APPINSIGHTS_INSTRUMENTATIONKEY
-   Outputs: appInsightsName, instrumentationKey
    **Acceptance**: Module deploys and telemetry flows to App Insights

### T017 [US2] - Create production parameter file

**File**: `infrastructure/parameters/prod.json`
**Description**: Parameter file template for production deployment
**Details**:

-   All required parameters with example values
-   Comments for secure parameters (GitHub tokens)
-   Sensible defaults (workspacesQuotaGB=100, tmpQuotaGB=50)
    **Acceptance**: Parameter file is valid JSON with all required fields

### T018 [US2] - Add deployment script

**File**: `scripts/deploy-production.sh`
**Description**: Bash script to deploy ARM template
**Details**:

```bash
az group create --name $RG --location $LOCATION
az deployment group create \
  --resource-group $RG \
  --template-file infrastructure/main.bicep \
  --parameters infrastructure/parameters/prod.json
```

**Acceptance**: Script executes deployment successfully

### T019 [US2] - Document production deployment in quickstart

**File**: `docs/deployment.md` or update `README.md`
**Description**: Add production deployment instructions
**Details**:

-   Prerequisites (Azure CLI, Docker Hub account, GitHub PAT)
-   Build and push container image steps
-   ARM template parameter configuration
-   Deployment command
-   Output retrieval (URLs, webhook URL)
-   Post-deployment verification
    **Acceptance**: Following documented steps results in working production deployment

### T020 [US2] - Test production deployment (manual verification)

**Description**: Manual test to verify US2 acceptance criteria
**Steps**:

1. Build Docker image: `docker build -t user/bifrost:latest ./workflows`
2. Push to Docker Hub: `docker push user/bifrost:latest`
3. Configure parameters file with actual values
4. Run `az deployment group create ...`
5. Wait for completion (~30 minutes)
6. Retrieve Function App URL from outputs
7. Retrieve Static Web App URL from outputs
8. Access Static Web App, verify login works
9. Create sample workflow in /workspace
10. Trigger workflow via UI
11. Verify workflow executes successfully
12. Push to frontend GitHub repo
13. Verify Static Web App auto-deploys
    **Acceptance**: All resources deployed, connected, and functional

### T021 [US2-Checkpoint] - User Story 2 Complete ✓

**Verification**: Production deployment now works via single ARM template command

---

## Phase 4: User Story 3 - GitHub Integration for Workspace Sync (P2)

**Goal**: Administrator connects GitHub repository, pushes changes, changes sync automatically within 2 minutes

**Independent Test**: User connects GitHub repo via API, pushes commit, waits <2 minutes, verifies files updated in /workspace

### T022 [US3] - Create GitHubConnection entity model

**File**: `workflows/models/github_connection.py`
**Description**: Pydantic model for GitHubConnection Table Storage entity
**Details**:

-   Fields: PartitionKey (fixed "GITHUB_CONNECTIONS"), RowKey (OrgId/GLOBAL), RepositoryUrl, RepositoryBranch, IsEnabled, LastSync\* fields
-   Validation: URL format, branch non-empty
    **Acceptance**: Model validates correct data, rejects invalid data

### T023 [US3] - Create GitHubSyncJob entity model

**File**: `workflows/models/github_sync_job.py`
**Description**: Pydantic model for GitHubSyncJob Table Storage entity
**Details**:

-   Fields: PartitionKey (fixed "SYNC_JOBS"), RowKey (CommitSha), Status, Files\* counts, timestamps
-   Status enum: queued, processing, completed, failed
    **Acceptance**: Model validates correct data, status transitions enforced

### T024 [US3] - Create Azure Files helper service

**File**: `workflows/shared/azure_files.py`
**Description**: Helper functions for Azure Files operations
**Details**:

-   list_all_files(share_name, directory_path) → recursive walker
-   read_file(share_name, file_path) → bytes
-   write_file(share_name, file_path, content) → create parent dirs, upload
-   delete_file(share_name, file_path)
-   Uses azure-storage-file-share SDK with async support
    **Acceptance**: Helper functions work with Azurite Files endpoint locally

### T025 [US3] - Create GitHub sync service with rsync logic

**File**: `workflows/services/github_sync_service.py`
**Description**: Service to sync GitHub repository to Azure Files
**Details**:

-   sync_github_to_azure_files(repo_url, branch, commit_sha, pat)
-   Phase 1: Clone repo (--depth 1) to /tmp/sync-{sha}
-   Phase 2: Build file trees (GitHub + Azure Files) with SHA256 hashing
-   Phase 3: Compute diff (to_add, to_delete, to_update)
-   Phase 4: Apply changes with asyncio.gather (parallel, limit=10)
-   Phase 5: Cleanup temp directory
    **Acceptance**: Syncing test repo results in correct /workspace state

### T026 [US3] - Create GitHub connection CRUD endpoints

**File**: `workflows/functions/github_connections.py`
**Description**: Azure Function endpoints for managing GitHub connections (FR-008)
**Details**:

-   POST /api/github-connections → Create connection, generate webhook secret, store in Key Vault
-   GET /api/github-connections → List connections
-   GET /api/github-connections/{orgId} → Get specific connection
-   PUT /api/github-connections/{orgId} → Update (branch, isEnabled, PAT)
-   DELETE /api/github-connections/{orgId} → Disconnect (files remain)
-   MSP users only, validates X-Organization-Id header
    **Acceptance**: All CRUD operations work, secrets stored in Key Vault

### T027 [US3] - Create GitHub webhook receiver endpoint

**File**: `workflows/functions/github_webhook.py`
**Description**: Azure Function to receive GitHub push webhooks (FR-009)
**Details**:

-   POST /api/github-webhook
-   Verify X-Hub-Signature-256 with HMAC-SHA256 (timing-attack resistant)
-   Parse webhook payload (commit SHA, repo URL, branch, author, message)
-   Check idempotency: query GitHubSyncJob by CommitSha
-   Create GitHubSyncJob entity with Status='queued'
-   Queue sync job to Azure Queue
-   Return 202 Accepted
    **Acceptance**: Valid webhook queues sync, invalid signature returns 401

### T028 [US3] - Create sync job processor (queue trigger)

**File**: `workflows/functions/process_sync_job.py`
**Description**: Azure Function queue trigger to process sync jobs
**Details**:

-   Triggered by Azure Queue message
-   Update GitHubSyncJob Status='processing', StartedAt=now
-   Call github_sync_service.sync_github_to_azure_files()
-   Update GitHubSyncJob with Files\* counts, DurationMs, Status='completed'
-   On error: Update Status='failed', ErrorMessage, RetryCount++ (max 3)
-   Log sync events (FR-020)
    **Acceptance**: Queued job processes successfully, updates entity, syncs files

### T029 [US3] - Create sync job monitoring endpoints

**File**: `workflows/functions/sync_jobs.py`
**Description**: Azure Function endpoints to view sync job history
**Details**:

-   GET /api/sync-jobs → List recent jobs (filter by orgId, status, limit)
-   GET /api/sync-jobs/{commitSha} → Get specific job details
-   Returns: Job status, timestamps, file counts, error messages
    **Acceptance**: Endpoints return sync job history for monitoring

### T030 [US3] [P] - Create GitHub connection UI component

**File**: `client/src/pages/workspaceettings.tsx`
**Description**: React page to manage GitHub connection
**Details**:

-   Form: Repository URL, Branch, Personal Access Token inputs
-   Display current connection status (connected/disconnected)
-   Show last sync timestamp, status, file counts
-   Connect/Disconnect buttons
-   Webhook URL display with copy button
-   MSP users only (check user role)
    **Acceptance**: UI allows connecting/disconnecting GitHub, displays status

### T031 [US3] [P] - Create sync job history UI component

**File**: `client/src/components/SyncJobHistory.tsx`
**Description**: React component to display sync job history
**Details**:

-   Table: Commit SHA, Author, Message, Status, Duration, File Counts, Timestamp
-   Filter by status (all, completed, failed)
-   Pagination (20 per page)
-   Refresh button
-   Color-coded status badges
    **Acceptance**: UI displays sync job history with filtering

### T032 [US3] - Test GitHub integration workflow (manual verification)

**Description**: Manual test to verify US3 acceptance criteria
**Steps**:

1. Create test GitHub repository with workflow files
2. Use API to create GitHubConnection (POST /api/github-connections)
3. Configure GitHub webhook with returned URL and secret
4. Push commit to GitHub repository
5. Verify webhook received (check Azure Function logs)
6. Wait for sync job to process
7. Query sync job status (GET /api/sync-jobs)
8. Verify files synced to /workspace (GET /api/workspace/files)
9. Verify workflow executable via platform
10. View sync history in UI
11. Time from push to executable: <2 minutes
    **Acceptance**: GitHub integration works end-to-end within performance targets

### T033 [US3-Checkpoint] - User Story 3 Complete ✓

**Verification**: GitHub sync now works - pushes automatically sync to platform

---

## Phase 5: User Story 4 - Manual Workflow Script Management (P2)

**Goal**: User edits workspace files via UI when GitHub is disconnected, changes persist and are immediately executable

**Independent Test**: User disconnects GitHub, creates new file via UI, saves, executes workflow successfully

### T034 [US4] - Create workspace file service

**File**: `workflows/services/workspace_service.py`
**Description**: Service for workspace file operations
**Details**:

-   list_files(share_name='workspaces', path='/') → WorkspaceItem[]
-   get_file(file_path) → WorkspaceFile
-   create_or_update_file(file_path, content) → WorkspaceFile
-   delete_file(file_path)
-   create_directory(dir_path)
-   delete_directory(dir_path)
-   Uses azure_files.py helper
-   Validates: no ".." traversal, max 10MB, valid UTF-8
    **Acceptance**: Service operations work against Azure Files

### T035 [US4] - Create workspace file CRUD endpoints

**File**: `workflows/functions/workspace_files.py`
**Description**: Azure Function endpoints for manual editing (FR-012)
**Details**:

-   GET /api/workspace/files → List files (recursive)
-   GET /api/workspace/files/{filePath} → Read file
-   PUT /api/workspace/files/{filePath} → Create/update file
-   DELETE /api/workspace/files/{filePath} → Delete file
-   POST /api/workspace/directories/{dirPath} → Create directory
-   DELETE /api/workspace/directories/{dirPath} → Delete directory
-   Check GitHubConnection.IsEnabled → return 403 if enabled (read-only mode)
-   MSP users only
-   Reload workflows after save (FR-015)
    **Acceptance**: CRUD operations work when GitHub disconnected, blocked when connected

### T036 [US4] - Create workspace download ZIP endpoint

**File**: `workflows/functions/download_workspace.py`
**Description**: Azure Function to download workspace as ZIP (FR-012a)
**Details**:

-   GET /api/workspace/download
-   List all files in /workspace share
-   Create in-memory ZIP with zipfile.ZipFile
-   Add each file to ZIP
-   Return with Content-Disposition: attachment; filename=workspace-{timestamp}.zip
-   Memory limit: ~500MB workspaces
    **Acceptance**: ZIP download works, contains all workspace files

### T037 [US4] - Create workspace status endpoint

**File**: `workflows/functions/workspace_status.py`
**Description**: Azure Function to get workspace mode and statistics
**Details**:

-   GET /api/workspace/status
-   Return: mode (github-sync/manual-edit), isReadOnly, githubConnection details, statistics (file count, total size, last modified)
-   Query GitHubConnection entity for current state
    **Acceptance**: Status endpoint returns correct mode and statistics

### T038 [US4] [P] - Create script editor UI component

**File**: `client/src/components/ScriptEditor.tsx`
**Description**: React component for editing workspace files
**Details**:

-   File tree view (folders collapsible)
-   Code editor (Monaco Editor or CodeMirror)
-   CRUD operations: New file, Edit, Delete, Rename
-   Save button with Ctrl+S shortcut
-   Read-only mode indicator when GitHub connected
-   Syntax highlighting (Python, YAML, JSON)
-   File size validation (<10MB)
    **Acceptance**: Editor allows creating/editing files when GitHub disconnected

### T039 [US4] [P] - Add download workspace button to UI

**File**: `client/src/pages/workspaceettings.tsx`
**Description**: Add "Download Workspace" button to settings page
**Details**:

-   Button visible when GitHub connection exists
-   Click triggers GET /api/workspace/download
-   Browser downloads ZIP file
-   Show warning: "Enabling GitHub sync will overwrite manual changes"
-   Integrated with GitHub connection form
    **Acceptance**: Button downloads ZIP successfully

### T040 [US4] - Implement workspace mode toggle logic

**File**: `workflows/services/workspace_service.py` + UI components
**Description**: Handle transitions between GitHub sync and manual edit modes
**Details**:

-   When isEnabled changes from false→true: Offer ZIP download first
-   When isEnabled changes from true→false: Re-enable editor immediately
-   Update UI state based on workspace status
-   Show appropriate messages ("GitHub-managed - read only" vs "Manual editing enabled")
    **Acceptance**: Mode transitions work correctly with data loss prevention

### T041 [US4] - Test manual editing workflow (manual verification)

**Description**: Manual test to verify US4 acceptance criteria
**Steps**:

1. Disconnect GitHub connection (PUT /api/github-connections/{orgId} with isEnabled=false)
2. Open script editor UI
3. Verify file tree is editable
4. Create new file "test_workflow.py"
5. Add Python code
6. Save file (verify <2 seconds response time)
7. Trigger workflow execution
8. Verify workflow executes with new code
9. Edit existing file
10. Save changes
11. Verify updated code used in execution
12. Download workspace ZIP
13. Verify ZIP contains all files
14. Re-enable GitHub connection
15. Verify editor becomes read-only
16. Disconnect again
17. Verify editor becomes editable immediately
    **Acceptance**: All manual editing operations work, mode transitions correct

### T042 [US4-Checkpoint] - User Story 4 Complete ✓

**Verification**: Manual editing now works - users can edit via UI when GitHub disconnected

---

## Phase 6: Polish & Integration

Cross-cutting concerns and final integration.

### T043 [Polish] - Add health check endpoint with storage connectivity

**File**: `workflows/functions/health.py`
**Description**: Health check endpoint that verifies Azure Files connectivity (FR-019)
**Details**:

-   GET /api/health
-   Check: Azure Table Storage connectivity
-   Check: Azure Files /workspace share accessible
-   Check: Azure Files /tmp share accessible
-   Return: {"status": "healthy", "checks": {...}}
-   Return 503 if any check fails
    **Acceptance**: Health check passes when all dependencies healthy

---

## Task Dependencies & Parallel Execution

### Critical Path (Sequential)

```
Setup (T001-T003)
  ↓
US1: Docker Compose (T004-T010)
  ↓
US2: ARM Template (T011-T021)
  ↓
US3: GitHub Sync (T022-T033) || US4: Manual Edit (T034-T042)
  ↓
Polish (T043)
```

### Parallelizable Tasks

**Setup Phase**: T001, T002, T003 can run in parallel (different files)

**User Story 1**: T007 parallel with T004-T006 (different files)

**User Story 2**:

-   T012-T016 all parallel (different Bicep modules)
-   T017-T018 parallel with module development
-   T019 parallel with T020

**User Story 3**:

-   T022-T023 parallel (different models)
-   T030-T031 parallel (different UI components, independent of backend)
-   T024 can start early (no dependencies)

**User Story 4**:

-   T038-T039 parallel (different UI components)

### MVP Execution Plan

**Week 1: MVP (User Story 1)**

-   Day 1: T001-T003 (Setup)
-   Day 2-3: T004-T008 (Docker Compose configuration)
-   Day 4: T009-T010 (Testing and documentation)

**Week 2: Production Deployment (User Story 2)**

-   Day 1: T011 (Main template) + T012-T016 in parallel (Modules)
-   Day 2: T017-T018 (Parameters and scripts)
-   Day 3-4: T019-T020 (Documentation and testing)
-   Day 5: T021 (Checkpoint)

**Week 3: GitHub Integration (User Story 3)**

-   Day 1: T022-T024 in parallel (Models and helpers)
-   Day 2: T025 (Sync service)
-   Day 3: T026-T029 (Backend endpoints)
-   Day 4: T030-T031 in parallel (UI components)
-   Day 5: T032-T033 (Testing and checkpoint)

**Week 4: Manual Editing (User Story 4)**

-   Day 1: T034-T037 (Backend services and endpoints)
-   Day 2: T038-T040 (UI components and mode toggle)
-   Day 3: T041-T042 (Testing and checkpoint)
-   Day 4: T043 (Polish)

---

## Implementation Strategy

### Incremental Delivery

1. **MVP First**: Complete User Story 1 for immediate developer value
2. **Production Next**: User Story 2 enables deployment
3. **Features Parallel**: User Stories 3 & 4 are independent, can develop simultaneously
4. **Test Continuously**: Manual verification after each user story checkpoint

### Testing Approach

**No automated tests specified in requirements** - using manual verification checkpoints after each user story.

**Manual Test Points**:

-   After US1 (T009): Verify local development workflow
-   After US2 (T020): Verify production deployment
-   After US3 (T032): Verify GitHub integration end-to-end
-   After US4 (T041): Verify manual editing workflow

**Future Test Expansion** (if needed):

-   Contract tests: tests/contract/test_github_sync_api.py, test_workspace_files_api.py
-   Integration tests: tests/integration/test_github_sync_workflow.py, test_docker_compose_startup.py

### Risk Mitigation

**Risk**: Docker image size >2GB
**Mitigation**: T007 (.dockerignore optimization), monitor with `docker images`

**Risk**: ARM deployment fails due to quota
**Mitigation**: T020 includes quota verification step

**Risk**: GitHub webhook signature verification fails
**Mitigation**: T027 includes HMAC testing with known-good payloads

**Risk**: Rsync performance poor for large workspaces
**Mitigation**: T025 includes optimization (parallel uploads, SHA256 hashing)

---

## Success Metrics

After completing all tasks, verify these success criteria from spec.md:

-   **SC-001**: Local dev starts in <5 minutes ✓ (US1)
-   **SC-002**: Production deployment in <30 minutes ✓ (US2)
-   **SC-003**: GitHub sync in <2 minutes ✓ (US3)
-   **SC-004**: Manual edits available in <5 seconds ✓ (US4)
-   **SC-004a**: ZIP download in <10 seconds ✓ (US4)
-   **SC-005**: Debugger attachment works ✓ (US1)
-   **SC-006**: ARM template 95% first-time success ✓ (US2)
-   **SC-007**: 100 executions/hour ✓ (US2)
-   **SC-008**: 99.9% workspace uptime ✓ (US2)
-   **SC-009**: Editor ops <2 seconds ✓ (US4)
-   **SC-010**: Zero manual config steps ✓ (US2)

---

## Notes

-   Tasks are sequenced for single-developer implementation
-   Parallel tasks [P] can be distributed across team members
-   Each user story is independently testable (acceptance scenarios in spec.md)
-   Checkpoints after each story enable demo/feedback cycles
-   Total estimated effort: 3-4 weeks for experienced developer
-   MVP (US1) can be completed in 1 week for immediate value
