# Implementation Plan: Azure Functions Docker Runtime Migration with Unified Architecture

**Branch**: `005-migrate-to-azure` | **Date**: 2025-01-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-migrate-to-azure/spec.md`

**Note**: This plan includes architectural consolidation to merge API and workflow projects into a single Azure Function App.

## Summary

Migrate the platform to Azure Functions with Docker runtime support, enabling simplified local development via docker-compose and production deployment via ARM templates. The architecture will use a **single unified Function App** containing both the management API and workflow execution engine, eliminating cross-service HTTP calls and configuration complexity.

Key changes:

-   **Unified Function App**: Merge `/api` and `/workflows` projects into single codebase
-   **Docker-first**: Use `func init --docker-only` for containerized deployment
-   **Azure Files mounts**: `/workspace` (user workflows) and `/tmp` (temporary storage)
-   **ARM template deployment**: Single template creates all Azure resources
-   **GitHub sync**: Optional webhook-based workspace synchronization
-   **Local debugging**: VS Code attach support with `ENABLE_DEBUGGING` flag

## Technical Context

**Language/Version**: Python 3.11 (Azure Functions v2 programming model)
**Primary Dependencies**:

-   Backend: azure-functions, azure-data-tables, azure-storage-file-share, aiohttp, pydantic, debugpy
-   Frontend: React 18+, TypeScript 4.9+, @azure/msal-browser
-   Infrastructure: Bicep (ARM templates)

**Storage**:

-   Persistent data: Azure Table Storage
-   Secrets: Azure Key Vault
-   Workspace files: Azure Files (Hot tier, `/workspace` and `/tmp` mounts)
-   Logs: Azure Blob Storage (via Application Insights)

**Testing**: pytest, pytest-asyncio (backend); Jest, React Testing Library (frontend)
**Target Platform**: Azure Functions (Linux containers), Azure Static Web Apps (frontend)
**Project Type**: Web application with unified backend Function App
**Performance Goals**:

-   Workflow execution latency: <100ms from API to execution (direct invocation)
-   Local dev startup: <5 minutes
-   Production deployment: <30 minutes
-   GitHub sync latency: <2 minutes

**Constraints**:

-   Container image size: <2GB
-   File path length: 260 chars (Windows), 4096 (Linux)
-   Workspace file size: <10MB per file
-   GitHub webhook payload: <5MB

**Scale/Scope**:

-   Target: 50-200 client organizations
-   Workflows: 100-1000 executions/day
-   Local: single developer experience
-   Production: 100 concurrent executions/hour

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

### Principle I: Azure-First Architecture ✅ **PASS**

-   ✅ All compute uses Azure Functions (unified Function App with Docker runtime)
-   ✅ Storage uses Azure Table Storage + Azure Files + Key Vault
-   ✅ Authentication uses Azure AD (Static Web App integration)
-   ✅ Local development uses Azurite

### Principle II: Table Storage Only ✅ **PASS**

-   ✅ All persistent data in Azure Table Storage
-   ✅ NO SQL databases
-   ✅ Org-scoped partition keys maintained
-   ✅ Dual-indexing pattern for permissions
-   ✅ Azurite for local development

### Principle III: Python Backend Standard ✅ **PASS**

-   ✅ Unified Function App uses Python 3.11
-   ✅ Azure Functions v2 programming model
-   ✅ Shared code in `engine/shared/` module (workflow engine shared with API)
-   ✅ Type hints for all function signatures
-   ✅ Async/await for I/O operations
-   ✅ Pydantic for models

**Note**: Constitution currently states "All shared code between API and Workflows MUST be in `shared/` module". With the merger, this becomes `engine/shared/` as the unified shared module.

### Principle IV: Test-First Development ✅ **PASS**

-   ✅ Contract tests for all API endpoints (existing + new)
-   ✅ Integration tests for Docker compose startup
-   ✅ Integration tests for GitHub sync workflow
-   ✅ Integration tests for workspace file operations
-   ⚠️ **Exemption**: Infrastructure setup tasks (Dockerfile, docker-compose, ARM templates) do not require tests per constitution

### Principle V: Single-MSP Multi-Organization Design ✅ **PASS**

-   ✅ Org-scoped partition keys maintained
-   ✅ Global config/secrets use `PartitionKey = "GLOBAL"`
-   ✅ `X-Organization-Id` header validation continues
-   ✅ Permission checks unchanged
-   ✅ Organization context loading unchanged

**Post-Merger Architecture Benefits**:

-   ✅ **Simplified deployment**: Single Function App reduces complexity
-   ✅ **Better performance**: Direct function calls instead of HTTP proxy calls
-   ✅ **Easier debugging**: Single codebase, single container
-   ✅ **Reduced configuration**: No workflow engine URL/key needed

### Constitution Compliance: ✅ **ALL GATES PASSED**

No principle violations. The unified architecture **improves** compliance by reducing complexity while maintaining all constitutional requirements.

## Project Structure

### Documentation (this feature)

```
specs/005-migrate-to-azure/
├── spec.md              # Feature specification (INPUT)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output - technical decisions
├── data-model.md        # Phase 1 output - entities and schema
├── quickstart.md        # Phase 1 output - user guide
├── contracts/           # Phase 1 output - API contracts
│   ├── github-sync-api.yaml
│   ├── workspace-files-api.yaml
│   └── health-check-api.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

**BEFORE** (Current - Two Separate Projects):

```
api/                     # Management API Function App
├── functions/           # API endpoints
├── shared/              # API-specific shared code
├── tests/
└── requirements.txt

workflows/               # Workflow Engine Function App (SEPARATE)
├── engine/              # Workflow execution engine
│   ├── shared/         # Engine-specific shared code
│   ├── admin/          # Metadata endpoints
│   ├── execute/        # Workflow execution
│   └── functions/      # Data provider API
├── workspace/          # User workflow files
├── tests/
└── requirements.txt
```

**AFTER** (Target - Unified Architecture):

```
api/                     # UNIFIED Function App (merged project)
├── functions/           # API endpoints (management)
│   ├── organizations.py
│   ├── permissions.py
│   ├── forms.py
│   ├── executions.py   # UPDATED: Direct workflow execution
│   ├── workflow_metadata.py  # NEW: Direct registry access
│   ├── data_providers.py     # NEW: Direct provider access
│   ├── github_connections.py # NEW: GitHub sync management
│   ├── workspace_files.py    # NEW: Manual workspace editing
│   └── [other existing endpoints...]
├── engine/              # MOVED FROM workflows/engine/
│   ├── shared/         # Unified shared code (context, registry, decorators)
│   ├── data_providers/ # Built-in data providers
│   ├── admin/          # Metadata endpoints
│   ├── execute/        # Workflow execution
│   └── functions/      # Data provider API, OpenAPI
├── workspace/          # MOVED FROM workflows/workspace/
│   └── examples/
├── services/           # NEW: Business logic layer
│   ├── github_sync_service.py
│   └── workspace_service.py
├── tests/              # Unified test suite
│   ├── contract/       # API contract tests
│   ├── integration/    # End-to-end tests
│   └── engine/         # MOVED FROM workflows/tests/
├── Dockerfile          # MERGED: Single container image
├── requirements.txt    # MERGED: All dependencies
└── function_app.py     # UPDATED: Registers all blueprints

client/                 # Frontend (unchanged)
└── [React SWA app]

infrastructure/         # NEW: ARM templates
├── main.bicep          # Main deployment template
├── modules/
│   ├── functions.bicep      # Unified Function App
│   ├── staticwebapp.bicep
│   ├── storage.bicep        # Files, Tables, Queues
│   └── keyvault.bicep
└── parameters/
    └── prod.json

docker-compose.yml      # UPDATED: Single service (no separate workflows)
```

**Structure Decision**: Web application with unified backend. The merger consolidates two Function App projects into one, eliminating cross-service communication. The `api/` directory becomes the single source of truth for all backend code (both management API and workflow engine).

## Complexity Tracking

_No complexity violations - unified architecture reduces complexity._

| Metric                    | Before          | After          | Change     |
| ------------------------- | --------------- | -------------- | ---------- |
| Function Apps             | 2               | 1              | ✅ -50%    |
| HTTP proxy calls          | ~10/request     | 0              | ✅ -100%   |
| Configuration vars        | 2 (URL + key)   | 0              | ✅ -100%   |
| Docker containers (local) | 2               | 1              | ✅ -50%    |
| ARM template resources    | 2 Function Apps | 1 Function App | ✅ Simpler |
| Codebase complexity       | Split repos     | Unified        | ✅ Simpler |

**Architectural Simplification**: This change **reduces** overall system complexity by eliminating inter-service communication, removing configuration burden, and consolidating deployment.

## Phase 0: Research & Technical Decisions

### Research Tasks

1. **Azure Functions Docker Support**

    - `func init --docker-only` usage and best practices
    - Container runtime requirements (Python 3.11 base image)
    - Debug configuration for VS Code attachment
    - Volume mount patterns for workspace and source code
    - Live reload in container development

2. **Azure Files Integration**

    - Mounting Azure Files to Function App container (`/workspace`, `/tmp`)
    - Hot tier vs Cool tier performance characteristics
    - File share quota sizing (defaults and limits)
    - SDK usage: azure-storage-file-share for Python
    - Recursive file operations (list, upload, delete)

3. **GitHub Integration Patterns**

    - Webhook signature verification (HMAC-SHA256)
    - Personal Access Token (PAT) permissions required
    - Webhook payload structure and limits (5MB)
    - Idempotency handling for duplicate webhooks
    - Rsync-style synchronization logic (diff + apply)

4. **ARM Template Best Practices**

    - Bicep module organization
    - Static Web App GitHub CI/CD connection
    - Managed identity for Key Vault access
    - Application Insights integration
    - Docker container deployment from Docker Hub

5. **Unified Function App Architecture**
    - Merging two function_app.py files (blueprint registration)
    - Shared module structure (`engine/shared/`)
    - Workspace discovery in unified app
    - Import restriction for workspace code
    - Direct function invocation patterns (no HTTP)

### Decisions

**Output**: `research.md` with consolidated findings and rationale for each decision.

## Phase 1: Design & Contracts

### 1. Data Model (`data-model.md`)

**Entities**:

1. **GitHubConnection**

    - PartitionKey: `"GITHUB_CONNECTIONS"`
    - RowKey: `{OrgId}` or `"GLOBAL"`
    - Fields: RepositoryUrl, RepositoryBranch, IsEnabled, WebhookSecret, LastSync\*, CreatedAt, UpdatedAt
    - Purpose: Track GitHub repository connections for workspace sync

2. **GitHubSyncJob**

    - PartitionKey: `"SYNC_JOBS"`
    - RowKey: `{CommitSha}`
    - Fields: Status, CommitMessage, Author, Files\* counts, StartedAt, CompletedAt, DurationMs, ErrorMessage, RetryCount
    - Purpose: Track sync job execution and status

3. **WorkspaceFile** (virtual - stored in Azure Files)
    - Location: `/workspace` Azure Files share
    - Metadata: File path, size, last modified (from Azure Files API)
    - Purpose: User-defined workflow scripts

**Relationships**:

-   GitHubConnection (1) → GitHubSyncJob (many) via OrgId
-   Organization (1) → GitHubConnection (0..1) via OrgId

### 2. API Contracts (`contracts/`)

#### `github-sync-api.yaml` (NEW)

-   `POST /api/github-connections` - Create GitHub connection
-   `GET /api/github-connections` - List connections
-   `GET /api/github-connections/{orgId}` - Get connection
-   `PUT /api/github-connections/{orgId}` - Update connection
-   `DELETE /api/github-connections/{orgId}` - Disconnect
-   `POST /api/github-webhook` - Receive GitHub webhook

#### `workspace-files-api.yaml` (NEW)

-   `GET /api/workspace/files` - List workspace files
-   `GET /api/workspace/files/{filePath}` - Read file
-   `PUT /api/workspace/files/{filePath}` - Create/update file
-   `DELETE /api/workspace/files/{filePath}` - Delete file
-   `POST /api/workspace/directories/{dirPath}` - Create directory
-   `DELETE /api/workspace/directories/{dirPath}` - Delete directory
-   `GET /api/workspace/download` - Download workspace as ZIP
-   `GET /api/workspace/status` - Get workspace mode and statistics

#### `workflow-execution-api.yaml` (UPDATED)

-   `GET /api/workflows/metadata` - Get workflow metadata (UPDATED: direct registry access)
-   `POST /api/workflows/{workflowName}` - Execute workflow (UPDATED: direct invocation)
-   `GET /api/data-providers/{providerName}` - Get data provider options (UPDATED: direct call)

**Changes from Current API**:

-   **REMOVE**: `/api/config/validate-workflows-engine` (no longer needed)
-   **REMOVE**: `/api/workflows/health` (unified health endpoint)
-   **UPDATE**: Workflow execution endpoints no longer proxy to external service

### 3. Quickstart Guide (`quickstart.md`)

**Sections**:

1. **Local Development Setup**

    - Prerequisites (Docker Desktop)
    - Running `docker-compose up`
    - Accessing UI at http://localhost:7071
    - Enabling debugging with `ENABLE_DEBUGGING=true`
    - Attaching VS Code debugger

2. **Production Deployment**

    - Building Docker image
    - Pushing to Docker Hub
    - Configuring ARM template parameters
    - Running `az deployment group create`
    - Accessing deployed services

3. **GitHub Integration**

    - Creating Personal Access Token
    - Connecting repository via API
    - Configuring webhook
    - Testing sync workflow

4. **Manual Workspace Editing**
    - Accessing script editor
    - Creating/editing files
    - Downloading workspace backup
    - Switching between GitHub and manual modes

### 4. Agent Context Update

Run `.specify/scripts/bash/update-agent-context.sh` to add:

-   Docker container development patterns
-   Azure Files SDK usage
-   GitHub webhook handling
-   ARM template deployment
-   **Unified Function App architecture** (single codebase patterns)

## Phase 2: Implementation Tasks

**Output**: `tasks.md` (generated by `/speckit.tasks` command - NOT by this command)

The tasks.md will break down implementation into:

-   **Phase 1: Setup** - Dockerfile, docker-compose, infrastructure directory
-   **Phase 2: Merge Projects** - Copy engine code to api/, update imports, remove proxy endpoints
-   **Phase 3: Local Development** - Debug configuration, volume mounts, workspace discovery
-   **Phase 4: Production Deployment** - ARM templates, deployment scripts
-   **Phase 5: GitHub Sync** - Webhook handler, sync service, UI
-   **Phase 6: Manual Editing** - Workspace file CRUD, script editor UI
-   **Phase 7: Polish** - Health checks, documentation, testing

## Key Integration Points

### 1. Unified Function App Registration

**File**: `api/function_app.py`

```python
import azure.functions as func
from pathlib import Path
import os
import importlib.util

# Import restrictor for workspace isolation
from engine.shared.import_restrictor import install_import_restrictions
WORKSPACE_PATH = os.environ.get('WORKSPACE_PATH', '/workspace')
install_import_restrictions([WORKSPACE_PATH])

# Initialize tables
from engine.shared.init_tables import init_tables
init_tables()

# Workspace discovery (from workflows/function_app.py)
def discover_workspace_modules():
    # ... dynamic workspace discovery logic

discover_workspace_modules()

# Import engine data providers
import engine.data_providers

# Create app with ANONYMOUS auth (Static Web App handles auth)
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Register ALL blueprints (API + Engine)
from functions.organizations import bp as organizations_bp
from functions.permissions import bp as permissions_bp
# ... other API blueprints
from functions.workflow_metadata import bp as workflow_metadata_bp  # NEW
from functions.workflow_execute import bp as workflow_execute_bp    # NEW
from functions.data_providers import bp as data_providers_bp        # NEW
from functions.github_connections import bp as github_connections_bp # NEW
from functions.workspace_files import bp as workspace_files_bp      # NEW

app.register_functions(organizations_bp)
# ... register all blueprints
app.register_functions(workflow_metadata_bp)
app.register_functions(workflow_execute_bp)
app.register_functions(data_providers_bp)
app.register_functions(github_connections_bp)
app.register_functions(workspace_files_bp)
```

### 2. Direct Workflow Execution (No HTTP Proxy)

**File**: `api/functions/workflow_execute.py` (NEW - replaces proxy in workflows.py)

```python
from engine.shared.registry import get_registry
from engine.shared.context import OrganizationContext
from engine.execute import execute_workflow_internal

@bp.function_name("workflows_execute")
@bp.route(route="workflows/{workflowName}", methods=["POST"])
@require_auth
async def execute_workflow(req: func.HttpRequest) -> func.HttpResponse:
    """Direct workflow execution - no HTTP proxy"""
    workflow_name = req.route_params.get("workflowName")
    org_id, user_id, error = get_scope_context(req)

    # Load organization context
    context = await load_organization_context(org_id, user_id)

    # Get workflow from registry
    registry = get_registry()
    workflow_metadata = registry.get_workflow(workflow_name)

    # Execute directly (no HTTP call)
    result = await execute_workflow_internal(
        workflow_metadata=workflow_metadata,
        context=context,
        parameters=req.get_json()
    )

    return func.HttpResponse(json.dumps(result), mimetype="application/json")
```

**Benefits**:

-   ✅ No HTTP overhead (sub-100ms latency)
-   ✅ No function key configuration needed
-   ✅ No cross-service authentication
-   ✅ Direct access to registry and context
-   ✅ Easier debugging (single call stack)

### 3. Docker Compose Simplification

**File**: `docker-compose.yml` (UPDATED)

```yaml
services:
    azurite:
        image: mcr.microsoft.com/azure-storage/azurite:latest
        ports:
            - "10000:10000" # Blob
            - "10001:10001" # Queue
            - "10002:10002" # Table
            - "10003:10003" # Files (NEW)
        command: "azurite --blobHost 0.0.0.0 --queueHost 0.0.0.0 --tableHost 0.0.0.0 --fileHost 0.0.0.0 --loose"
        volumes:
            - azurite-data:/data

    api: # RENAMED from 'functions' - single unified service
        build:
            context: ./api # Single build context
            dockerfile: Dockerfile
        ports:
            - "7071:80" # Azure Functions
            - "5678:5678" # Debugpy
        environment:
            - AzureWebJobsStorage=... # Connection to azurite
            - AZURE_FILES_CONNECTION_STRING=... # For workspace/tmp mounts
            - ENABLE_DEBUGGING=${ENABLE_DEBUGGING:-false}
            - WORKSPACE_PATH=/workspace
            - AZURE_FUNCTIONS_ENVIRONMENT=Development
        volumes:
            - ./api:/home/site/wwwroot # Live source reload
            - workspace-data:/workspace # Workspace files
            - tmp-data:/tmp # Temporary storage
        depends_on:
            - azurite

    # REMOVED: workflows service (merged into api service)

volumes:
    azurite-data:
    workspace-data:
    tmp-data:
```

**Key Changes**:

-   ✅ Single service instead of two
-   ✅ One port (7071) instead of two (7071 + 7071)
-   ✅ No inter-container networking needed
-   ✅ Simpler environment configuration

### 4. ARM Template Simplification

**File**: `infrastructure/main.bicep`

```bicep
// Single Function App with unified codebase
module functionApp 'modules/functions.bicep' = {
  name: 'functionApp'
  params: {
    functionAppName: functionAppName
    dockerHubImage: dockerHubImage  // Single image
    storageAccountName: storageAccount.outputs.name
    keyVaultName: keyVault.outputs.name
    appInsightsInstrumentationKey: appInsights.outputs.instrumentationKey
    // Mount both workspace and tmp shares
    azureFilesShares: [
      { name: 'workspaces', mountPath: '/workspace' }
      { name: 'tmp', mountPath: '/tmp' }
    ]
  }
}

// REMOVED: Separate workflow engine Function App
// REMOVED: Workflow engine URL configuration
// REMOVED: Function key management
```

**Benefits**:

-   ✅ One Function App resource instead of two
-   ✅ Simpler networking (no VNet peering needed)
-   ✅ Lower cost (single App Service Plan)
-   ✅ Easier monitoring (single Application Insights resource)

## Testing Strategy

### Contract Tests (Required by Constitution)

1. **GitHub Sync API** (`tests/contract/test_github_sync_api.py`)

    - POST /api/github-connections creates connection
    - GET /api/github-connections lists connections
    - PUT /api/github-connections/{orgId} updates connection
    - DELETE /api/github-connections/{orgId} removes connection
    - POST /api/github-webhook validates signature and queues job

2. **Workspace Files API** (`tests/contract/test_workspace_files_api.py`)

    - GET /api/workspace/files lists files
    - PUT /api/workspace/files/{path} creates/updates file
    - DELETE /api/workspace/files/{path} removes file
    - GET /api/workspace/download returns ZIP

3. **Updated Workflow Execution** (`tests/contract/test_workflow_execution.py`)
    - Verify direct execution (no HTTP proxy)
    - Verify sub-100ms latency
    - Verify no function key required

### Integration Tests (Required for Complex Flows)

1. **Docker Compose Startup** (`tests/integration/test_docker_compose_startup.py`)

    - `docker-compose up` completes successfully
    - Health endpoint returns 200
    - Workspace mount accessible
    - Registry discovers workspace modules

2. **GitHub Sync Workflow** (`tests/integration/test_github_sync_workflow.py`)

    - Create GitHub connection
    - Simulate webhook event
    - Verify files synced to Azure Files
    - Verify workflows reload

3. **Manual Workspace Editing** (`tests/integration/test_workspace_editing.py`)
    - Create file via API
    - Read file via API
    - Execute workflow using created file
    - Download workspace ZIP

### Manual Verification (Infrastructure)

-   Local development: `docker-compose up` + VS Code attach
-   Production deployment: Run ARM template → verify all resources
-   GitHub integration: Connect repo → push commit → verify sync

## Deployment Workflow

### Local Development

1. Clone repository
2. Run `docker-compose up`
3. Access UI at http://localhost:7071
4. Set `ENABLE_DEBUGGING=true` and restart to enable VS Code debugging
5. Make changes to workspace files → changes immediately available

### Production Deployment

1. Build Docker image: `docker build -t user/bifrost:latest ./api`
2. Push to Docker Hub: `docker push user/bifrost:latest`
3. Configure ARM template parameters (`infrastructure/parameters/prod.json`)
4. Deploy: `az deployment group create --template-file infrastructure/main.bicep --parameters @infrastructure/parameters/prod.json`
5. Wait ~30 minutes for deployment
6. Access Static Web App URL from outputs
7. Configure GitHub integration via UI (optional)

### CI/CD (Future Enhancement)

-   GitHub Actions to build/push Docker image on `main` branch
-   Automated ARM template deployment to staging
-   Manual approval gate for production
-   Smoke tests post-deployment

## Migration from Current State

**For Existing Deployments** (out of scope for this feature, but documented for reference):

1. **Backup data**: Export all Table Storage tables
2. **Deploy unified Function App**: Run new ARM template
3. **Migrate configuration**: Copy environment variables and Key Vault secrets
4. **Update frontend**: Point to new unified API endpoint
5. **Test workflows**: Verify all workflows execute correctly
6. **Decommission old services**: Remove separate workflow Function App
7. **Clean up**: Remove workflow engine URL/key configuration

**For New Deployments** (in scope):

-   Single ARM template deploys everything
-   No migration needed

## Success Metrics

-   **SC-001**: Local dev startup: <5 minutes ✅ Measured via `time docker-compose up`
-   **SC-002**: Production deployment: <30 minutes ✅ Measured via ARM template execution time
-   **SC-003**: GitHub sync latency: <2 minutes ✅ Measured via webhook timestamp → workflow available
-   **SC-010**: Zero manual config: ✅ No workflow engine URL or function key needed
-   **SC-011**: Execution latency: <100ms ✅ Measured via API endpoint → workflow start time

## Risks & Mitigation

| Risk                                             | Likelihood | Impact | Mitigation                                                         |
| ------------------------------------------------ | ---------- | ------ | ------------------------------------------------------------------ |
| Container image >2GB                             | Medium     | Medium | Optimize .dockerignore, multi-stage build                          |
| ARM deployment quota exceeded                    | Low        | High   | Document quota requirements, validation script                     |
| Workspace mount unavailable                      | Low        | High   | Health check for Azure Files, retry logic                          |
| GitHub webhook signature fails                   | Medium     | Medium | Unit tests for HMAC verification, test payloads                    |
| Workspace sync conflicts (GitHub + manual edits) | Medium     | Medium | Block manual editing when GitHub enabled, ZIP download before sync |
| Import restriction bypass                        | Low        | High   | Comprehensive tests for import restrictor                          |
| Merge breaks existing tests                      | High       | Medium | Run full test suite after merge, fix incrementally                 |

## Next Steps

1. ✅ **This command complete**: plan.md generated with unified architecture
2. **Run `/speckit.tasks`**: Generate detailed implementation tasks (tasks.md)
3. **Run `/speckit.implement`**: Execute tasks phase by phase
4. **Manual verification**: Test Docker compose startup, ARM deployment, GitHub sync
5. **Documentation update**: Update README, quickstart.md, deployment.md
6. **Merge to main**: PR with unified architecture changes

---

**Plan Status**: ✅ **READY FOR TASKS GENERATION**
**Constitution Compliance**: ✅ **ALL GATES PASSED**
**Next Command**: Run `/speckit.tasks` to generate implementation task breakdown
