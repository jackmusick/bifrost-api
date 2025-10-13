# Implementation Plan: Azure Functions Docker Runtime Migration

**Branch**: `005-migrate-to-azure` | **Date**: 2025-01-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-migrate-to-azure/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Convert the existing Azure Functions workflow engine to use Docker runtime (func init --docker-only) while maintaining Azure Functions deployment. Create comprehensive ARM template for one-command production deployment of all platform resources (Azure Functions with Docker, Static Web App with GitHub CI/CD, Storage with Azure Files, Key Vault, Application Insights). Enable local docker-compose development with optional debugging support and Azure Files mounts at `/workspace` (user code) and `/tmp` (temporary storage). Support GitHub webhook-based workspace sync with rsync behavior and manual editing mode when GitHub is disconnected.

## Technical Context

**Language/Version**: Python 3.11 (Azure Functions v2 programming model), TypeScript 4.9+ (frontend), Bicep/ARM (infrastructure)
**Primary Dependencies**:

-   Backend: azure-functions, azure-data-tables, aiohttp (GitHub API), azure-identity (Key Vault), azure-storage-file-share (Azure Files mounting)
-   Frontend: React 18+, React Router, @azure/msal-browser
-   Container: Docker, docker-compose
-   Infrastructure: Azure CLI, Bicep/ARM templates, func CLI (Azure Functions Core Tools)

**Storage**: Azure Table Storage (existing data), Azure Files (Hot tier for `/workspace` and `/tmp` mounts), Azure Blob Storage (logs), Azure Key Vault (secrets)
**Testing**: pytest, pytest-asyncio (backend contract/integration tests), Jest + React Testing Library (frontend)
**Target Platform**:

-   Production: Azure Functions (Linux container, Docker runtime from Docker Hub)
-   Local Development: Docker containers via docker-compose
-   Frontend: Azure Static Web App with GitHub Actions CI/CD

**Project Type**: Web application (Python backend + React frontend)
**Performance Goals**:

-   Local startup: <5 minutes from clone to running
-   Production deployment: <30 minutes ARM template execution
-   GitHub sync: <2 minutes from push to executable
-   Manual edits: <5 seconds availability
-   Workspace download: <10 seconds for zip export

**Constraints**:

-   Container image size: <2GB (pull time optimization)
-   Azure Files IOPS: Hot tier limits
-   GitHub webhook payload: <5MB
-   File path length: 260 chars (Windows), 4096 (Linux)
-   Azure Functions container SKU limits

**Scale/Scope**:

-   Target: 50-200 client organizations
-   Workflows: 100-1000 executions per day
-   Workflow files: <10MB each
-   Azure Files quota: User-configurable with sensible defaults

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

### Principle I: Azure-First Architecture ✅ PASS

-   **Compute**: Azure Functions with Docker runtime (still Azure Functions platform)
-   **Storage**: Azure Files (workspace/tmp), Azure Table Storage (metadata), Azure Blob Storage (logs)
-   **Auth**: Azure AD (existing, no changes)
-   **Secrets**: Azure Key Vault (existing, no changes)
-   **Frontend**: Azure Static Web App (existing, now ARM-deployed)
-   **Monitoring**: Application Insights (ARM template provisioned)
-   **Local Development**: Azurite for storage (existing), Docker for containerization

**Verdict**: No violations. All services remain Azure-native. Docker runtime is Azure Functions feature, not external service.

### Principle II: Table Storage Only ✅ PASS

-   **Existing data**: Azure Table Storage unchanged (organizations, workflows metadata, permissions)
-   **New storage**: Azure Files for workspace files and temporary execution storage (acceptable exception per principle: "Large data >32KB MUST use Blob Storage with Table Storage reference")
-   **GitHub Connection metadata**: Stored in Table Storage (connection config, sync status)
-   **No new databases**: No SQL, Cosmos DB, or third-party databases introduced

**Verdict**: No violations. Azure Files is acceptable for workspace files (similar to Blob Storage exception). Metadata remains in Table Storage.

### Principle III: Python Backend Standard ✅ PASS

-   **Backend language**: Python 3.11 with Azure Functions v2 (unchanged)
-   **Type hints**: Existing pattern maintained
-   **Async/await**: Existing pattern for Table Storage, GitHub API calls
-   **Pydantic**: Existing models reused
-   **Shared code**: New GitHub sync logic in `shared/` module

**Verdict**: No violations. Python backend remains standard. Docker runtime doesn't change programming model.

### Principle IV: Test-First Development ✅ PASS (with implementation notes)

**Contract tests required**:

-   `tests/contract/test_github_sync_api.py` - GitHub webhook endpoint, download workspace endpoint
-   `tests/contract/test_workspace_files_api.py` - Manual editing CRUD operations

**Integration tests required**:

-   `tests/integration/test_github_sync_workflow.py` - Webhook → sync → reload workflows
-   `tests/integration/test_docker_compose_startup.py` - Local development environment
-   `tests/integration/test_azure_files_mount.py` - Production mount verification

**Tests optional for**:

-   ARM template (manual deployment verification in acceptance testing)
-   docker-compose configuration (verified via integration test)
-   Dockerfile (verified via container build + integration test)

**Verdict**: Tests required for business logic (GitHub sync, workspace management). Infrastructure templates verified through deployment testing.

### Principle V: Single-MSP Multi-Organization Design ✅ PASS

-   **Workspace scope**: `/workspace` contains all organizations' workflows (org-scoped execution via existing context)
-   **GitHub connection**: Can be configured per-org OR globally (Table Storage with `PartitionKey = OrgId` or `GLOBAL`)
-   **Manual editing**: Respects org context from `X-Organization-Id` header (existing pattern)
-   **Permissions**: Existing MSP users (full access) vs ORG users (role-based) applies to script editor

**Verdict**: No violations. GitHub sync and manual editing respect existing org-scoping patterns.

### Additional Gates

**Deployment Simplification Gate** ✅ PASS

-   **Requirement**: ARM template deploys ALL platform resources in single command
-   **Resources**: Azure Functions, Static Web App, Storage Account, Key Vault, Application Insights, Azure Files shares
-   **Configuration**: GitHub repository URLs, storage quotas, resource names as parameters
-   **Zero manual steps**: SC-010 requires zero post-deployment configuration

**Docker Migration Gate** ✅ PASS

-   **Requirement**: Maintain Azure Functions deployment (not standalone Docker)
-   **Approach**: func init --docker-only (Azure Functions feature, not platform change)
-   **Runtime**: Still deploys to Azure Functions, just uses container mode
-   **Compatibility**: Existing Python code, Table Storage, Key Vault access unchanged

**Summary**: All constitution principles satisfied. No complexity violations to track.

## Project Structure

### Documentation (this feature)

```
specs/005-migrate-to-azure/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── github-sync-api.yaml
│   ├── workspace-files-api.yaml
│   └── health-checks-api.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
# Web application structure (existing + Docker additions)

# Backend (Azure Functions with Docker)
workflows/                      # Existing Azure Functions project
├── function_app.py            # Existing (unchanged)
├── functions/                 # Existing functions
│   ├── github_sync.py         # NEW: GitHub webhook handler
│   └── workspace_files.py     # NEW: Manual editing CRUD
├── services/                  # Existing services
│   ├── github_sync_service.py # NEW: GitHub API, rsync logic
│   └── workspace_service.py   # NEW: Azure Files operations
├── shared/                    # Existing shared code
│   └── azure_files.py         # NEW: Azure Files helper
├── Dockerfile                 # NEW: Azure Functions container
├── docker-compose.dev.yml     # NEW: Local development
├── docker-compose.prod.yml    # NEW: Production reference
├── host.json                  # Existing (may need container tweaks)
├── local.settings.json        # Existing (local dev config)
└── requirements.txt           # Existing (add azure-storage-file-share)

# Frontend (Static Web App)
client/                        # Existing React app
├── src/
│   ├── components/
│   │   └── ScriptEditor.tsx   # NEW/MODIFIED: Manual editing UI
│   ├── pages/
│   │   └── WorkspaceSettings.tsx # NEW: GitHub connection UI
│   └── services/
│       └── workspace.ts       # NEW: Workspace API calls
└── tests/

# Infrastructure (ARM templates)
infrastructure/                # NEW: Deployment templates
├── main.bicep                # NEW: Main ARM template
├── modules/
│   ├── functions.bicep       # NEW: Azure Functions (container)
│   ├── staticwebapp.bicep    # NEW: Static Web App + GitHub
│   ├── storage.bicep         # NEW: Storage + Azure Files
│   ├── keyvault.bicep        # NEW: Key Vault
│   └── appinsights.bicep     # NEW: Application Insights
└── parameters/
    ├── dev.json              # NEW: Dev environment params
    └── prod.json             # NEW: Prod environment params

# Tests
tests/
├── contract/
│   ├── test_github_sync_api.py        # NEW
│   └── test_workspace_files_api.py    # NEW
└── integration/
    ├── test_github_sync_workflow.py   # NEW
    ├── test_docker_compose_startup.py # NEW
    └── test_azure_files_mount.py      # NEW
```

**Structure Decision**: Web application structure with separate backend (Azure Functions) and frontend (React SPA). Adding Docker containerization to existing Azure Functions project (workflows/) and new infrastructure/ directory for ARM templates. Frontend remains in client/ with additions for workspace management UI.

## Complexity Tracking

_No constitution violations - this section intentionally left empty._

All complexity additions justified by requirements:

-   Docker runtime: Required by FR-001 (containerized deployment), FR-004 (local debugging)
-   ARM templates: Required by FR-005, FR-006 (automated infrastructure deployment)
-   Azure Files mounting: Required by FR-007 (persistent workspace/tmp storage)
-   GitHub sync service: Required by FR-008, FR-009 (workspace synchronization)
-   Manual editing API: Required by FR-012 (CRUD operations when GitHub disconnected)

No simpler alternatives available that satisfy functional requirements within constitution constraints.
