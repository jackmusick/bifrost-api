# Feature Specification: Azure Functions Docker Runtime Migration

**Feature Branch**: `005-migrate-to-azure`
**Created**: 2025-01-13
**Status**: Draft
**Input**: User description: "Migrate to Azure Functions with Docker (func init --docker-only). The goal is to simplify deployment and local development. Local development and prod are simplified because we can mount ONLY our worksplace folder (and source code separately if developing the actual engine). We'd basically have a docker-compose.dev.yml and a docker-compose.prod.yml that accomplished this. Dev would have a ENABLE_REMOTE_DEBUGGING env to accomplish this so we can have the experience of breakpointing in whatever code we had in the editor, rather that was source + workplace or just workspace. In Prod, we'd map Azure Files to a /workspace and a /tmp folder. This allows us to connect directly with GitHub using auth, create a webhook and then have our app resync the repo rather than using GitHub Actions. Deployment would now be an ARM template that scaffoled the Azure Function with live deployment from our Dockerhub image, our SWA, Azure Key Vault, a Storage account for Azure Files, Azure Table storage and Queue, App Insights -- all connected appropriately. If we can accomplish everything with a GitHub PAT or token, we can start there. Not sure how webhooks would work if so, but I like the Connect with GitHub option. Not connecting to GitHub would allow them to access the script editor, which would have a folder tree with crud operations and the ability to save scripts. Connecting to GitHub would make this readonly (UI and permissions in the API). Again, one of the goal is to have a docker-compose up + attach developer experience. They could put the docker-compose file in their workplace-only repo to make this super easy."

## Clarifications

### Session 2025-01-13

-   Q: What is the scope of this migration? → A: Converting the existing Azure Functions workflow engine app to use Docker runtime (func init --docker-only), which still deploys to Azure Functions but enables local docker-compose development
-   Q: What is the ENABLE_DEBUGGING environment variable for? → A: LOCAL development only - allows developers to attach VS Code debugger to container and set breakpoints in their workspace code (not engine source code)
-   Q: Is User Story 5 "Debugging Production Issues" needed? → A: No, removing it - there's already sufficient coverage for debugging needs
-   Q: What Azure Files share tier should the ARM template provision for production workloads? → A: Hot tier (balanced performance and cost); can be made configurable as ARM template parameter for user customization
-   Q: Should the ARM template deploy the container image from Docker Hub public registry or a private Azure Container Registry? → A: Docker Hub public registry (open source project, simpler deployment)
-   Q: When GitHub sync writes to `/workspace`, should it perform a full replacement or incremental update of files? → A: Rsync-style sync with delete flag to match repository state exactly (removes deleted files, updates changed files)
-   Q: What quota/size limits should apply to the `/tmp` Azure Files share for temporary workflow storage? → A: User-configurable ARM template parameter with suggested default (users pay for their own storage)
-   Q: Should the ARM template create a single Storage Account for both Azure Files AND Table/Queue storage, or separate accounts? → A: Single Storage Account for Files, Tables, and Queues (simpler deployment, lower cost)
-   Q: When manual edits are saved to `/workspace` (no GitHub sync), where exactly are files persisted - same Azure Files share structure, or different location? → A: Same `/workspace` Azure Files share; manual editing disabled when GitHub sync enabled; option to download workspace as zip before enabling sync (to prevent data loss)
-   Q: When a user disconnects GitHub sync after it was enabled, should manual editing be re-enabled on the existing `/workspace` content? → A: Yes, manual editing immediately re-enabled on existing `/workspace` content after disconnecting GitHub
-   Q: Should the ARM template configure the Static Web App with GitHub integration for automatic frontend deployment? → A: Yes, ARM template connects Static Web App to frontend GitHub repository for automatic CI/CD deployment

## User Scenarios & Testing

### User Story 1 - One-Command Local Development Setup (Priority: P1)

A developer wants to start working on workflows locally without complex environment configuration. They navigate to their workspace repository, run a single docker compose command, and have a fully functioning local instance of the platform. When ENABLE_DEBUGGING is set, they can attach their code editor's debugger to the container and set breakpoints in their workspace code.

**Why this priority**: This is the foundation that enables all other development workflows. Without simple local development, the platform becomes difficult to maintain and extend. This directly addresses developer productivity and onboarding time.

**Independent Test**: Developer clones workspace repo, runs docker compose command, and can execute workflows and set breakpoints in their code editor within 5 minutes.

**Acceptance Scenarios**:

1. **Given** a developer has the workspace repository, **When** they run the docker compose dev command, **Then** the platform starts and they can access the UI and execute workflows
2. **Given** the platform is running locally with ENABLE_DEBUGGING enabled, **When** they attach their debugger and set a breakpoint in their workspace code, **Then** code execution pauses at the breakpoint and they can inspect variables
3. **Given** they modify workspace code while the platform is running, **When** they save the file, **Then** the changes are immediately available without restart

---

### User Story 2 - Simplified Production Deployment (Priority: P1)

An administrator needs to deploy the platform to Azure without managing complex infrastructure or build pipelines. They provide configuration parameters, run the deployment template, and have a fully operational production environment with all required Azure services connected and configured.

**Why this priority**: Production deployment complexity is a major barrier to adoption. Simplifying this to a single template execution makes the platform accessible to more organizations and reduces deployment errors.

**Independent Test**: Administrator provides required configuration (subscription, resource group, etc.), executes deployment template, and can access working production instance within 30 minutes.

**Acceptance Scenarios**:

1. **Given** an Azure subscription and resource group, **When** administrator runs the ARM deployment template with configuration parameters (including frontend GitHub repository URL), **Then** all Azure resources are created and properly connected (Azure Functions with Docker runtime, Static Web App with GitHub CI/CD, Storage, Key Vault, Application Insights)
2. **Given** the deployment completes, **When** administrator navigates to the Static Web App URL, **Then** they can log in and access all platform features (frontend automatically deployed from GitHub)
3. **Given** workspace code exists in mounted storage, **When** a workflow is triggered via the UI, **Then** it executes successfully using the mounted workspace in Azure Functions container
4. **Given** frontend code is pushed to connected GitHub repository, **When** Static Web App CI/CD detects the change, **Then** updated frontend is automatically deployed and accessible

---

### User Story 3 - GitHub Integration for Workspace Sync (Priority: P2)

A team wants to manage their workflow scripts in GitHub with version control. They connect their workspace repository to the platform using GitHub authentication, and all changes pushed to the repository are automatically synchronized to the running platform without manual intervention.

**Why this priority**: This enables proper version control and team collaboration on workflows. While essential for teams, a manual file upload option could serve as a temporary workaround, making this P2.

**Independent Test**: User connects GitHub repository, pushes changes to GitHub, and observes changes reflected in platform within 2 minutes without manual sync.

**Acceptance Scenarios**:

1. **Given** a GitHub repository with workflows, **When** administrator connects the repository to the platform, **Then** all workflows are synchronized and available for execution
2. **Given** the repository is connected, **When** a developer pushes changes to GitHub, **Then** webhook triggers sync and updated workflows are available within 2 minutes
3. **Given** changes are synchronized, **When** user views workflow in the UI, **Then** they see updated code and read-only indicator showing GitHub-managed source

---

### User Story 4 - Manual Workflow Script Management (Priority: P2)

A user without GitHub integration wants to create and edit workflow scripts directly in the platform. They access the script editor, see a folder tree of their workspace, create new files, edit existing ones, and save changes that persist and are immediately available for execution.

**Why this priority**: This provides an alternative for users who don't want GitHub integration or need quick edits. Essential for flexibility but not critical for teams using version control.

**Independent Test**: User without GitHub connected creates new workflow file via UI editor, saves it, and successfully executes it.

**Acceptance Scenarios**:

1. **Given** no GitHub repository is connected, **When** user opens the script editor, **Then** they see an editable folder tree with CRUD operations available for `/workspace` files
2. **Given** the editor is open, **When** user creates a new workflow file and saves it, **Then** file is persisted to `/workspace` Azure Files share and immediately available for execution
3. **Given** a workflow file exists, **When** user edits and saves changes, **Then** updated version is used for subsequent executions
4. **Given** GitHub is connected, **When** user attempts to edit a file, **Then** editor shows read-only mode with message indicating GitHub management
5. **Given** user has manual edits in `/workspace`, **When** they attempt to enable GitHub sync, **Then** system offers option to download current workspace as zip before proceeding with sync (which will overwrite manual changes)
6. **Given** GitHub sync is enabled, **When** user disconnects the GitHub repository, **Then** manual editing is immediately re-enabled on existing `/workspace` content

---

### Edge Cases

-   What happens when GitHub webhook fails to reach the platform (network issue, timeout)?
-   How does the system handle workspace files that are modified both in GitHub and manually (GitHub sync will overwrite manual changes with rsync --delete behavior)?
-   What occurs if deployment template runs with insufficient Azure permissions?
-   How does platform behave when mounted storage becomes unavailable during workflow execution?
-   What happens when multiple developers debug the same workflow simultaneously in dev environment?
-   How does system handle container image pull failures during deployment or updates?
-   What occurs when GitHub repository is disconnected while workflows are actively executing?

## Requirements

### Functional Requirements

-   **FR-001**: System MUST provide containerized deployment package that includes all platform dependencies
-   **FR-002**: System MUST support mounting external workspace folder for workflow scripts
-   **FR-003**: System MUST provide separate development and production configuration profiles
-   **FR-004**: Local development environment MUST support interactive debugging with breakpoints in workspace code via debugger attachment (e.g., VS Code)
-   **FR-005**: System MUST provide automated deployment template for all required Azure infrastructure
-   **FR-006**: ARM deployment template MUST create and configure all platform resources: Azure Functions (container-enabled with Docker runtime from Docker Hub), Static Web App (connected to frontend GitHub repository for automatic CI/CD), Key Vault, single Storage Account with Azure Files (Hot tier with /workspace and /tmp shares), Table Storage, and Queue Storage, plus Application Insights with proper connectivity and permissions
-   **FR-007**: Production environment MUST mount Azure Files shares at `/workspace` (for user workflow code) and `/tmp` (for temporary file storage) with Hot tier performance; quota configurable via ARM template parameter
-   **FR-008**: System MUST support GitHub repository connection for workspace synchronization
-   **FR-009**: System MUST respond to GitHub webhook events to trigger workspace synchronization using rsync-style logic (update changed files, remove deleted files to match repository state exactly)
-   **FR-010**: System MUST support personal access token authentication for GitHub integration
-   **FR-011**: When GitHub is connected, script editor MUST be read-only with clear indication of source control management; when GitHub is disconnected, manual editing MUST be immediately re-enabled
-   **FR-012**: When GitHub is not connected, script editor MUST support full CRUD operations on workspace files in `/workspace` share
-   **FR-012a**: System MUST provide option to download current `/workspace` contents as zip file before enabling GitHub sync (data loss prevention)
-   **FR-013**: Script editor MUST display folder tree structure matching workspace organization
-   **FR-014**: System MUST persist manual script changes to mounted storage
-   **FR-015**: System MUST reload workflows immediately after sync or manual save
-   **FR-016**: Development environment MUST start with single command execution
-   **FR-017**: System MUST support source code mounting separate from workspace mounting for platform development
-   **FR-018**: All Azure services created by deployment template MUST be properly connected and authorized
-   **FR-019**: System MUST provide health checks for mounted storage connectivity
-   **FR-020**: System MUST log all workspace synchronization events

### Key Entities

-   **Workspace**: Collection of workflow scripts and supporting files organized in folder structure; represents the executable code managed either via GitHub or manual editing; stored in `/workspace` Azure Files share
-   **Temporary Storage**: Transient file storage for workflow execution artifacts; mounted at `/tmp` from Azure Files share with user-configurable quota
-   **GitHub Connection**: Configuration linking platform to a GitHub repository, including authentication credentials, webhook URL, and sync status
-   **Deployment Configuration**: Set of ARM template parameters defining Azure resource names, regions, SKUs, storage quotas, GitHub repository URLs (frontend for Static Web App, optional workspace repo), and connectivity settings
-   **Local Debug Session**: Development environment execution context with debugger attachment support, allowing developers to set breakpoints and inspect variables in their workspace code

## Success Criteria

### Measurable Outcomes

-   **SC-001**: Developers can start local development environment from clone to running platform in under 5 minutes
-   **SC-002**: Production deployment from template execution to operational platform completes in under 30 minutes
-   **SC-003**: GitHub-pushed changes appear in platform and are executable within 2 minutes of webhook delivery
-   **SC-004**: Manual script edits to `/workspace` are immediately available for execution (under 5 seconds from save)
-   **SC-004a**: Users can download workspace backup as zip file before enabling GitHub sync in under 10 seconds
-   **SC-005**: Developers can attach debugger (e.g., VS Code) to local container and set breakpoints in their workspace code during workflow execution
-   **SC-006**: Deployment template successfully provisions all Azure resources in 95% of executions on first attempt
-   **SC-007**: Platform supports at least 100 workflow executions per hour in production configuration
-   **SC-008**: Workspace storage remains accessible with 99.9% uptime
-   **SC-009**: Script editor operations (open, edit, save) complete in under 2 seconds for files up to 10KB
-   **SC-010**: Zero manual configuration steps required after deployment template completes

## Out of Scope

-   Migration of existing deployments to new containerized architecture (manual migration procedures may be provided separately)
-   Multi-region deployment or disaster recovery configuration
-   Custom container image builds (using provided image from Docker Hub public registry)
-   Private Azure Container Registry provisioning
-   GitHub Enterprise Server support (GitHub.com only)
-   Alternative version control systems (GitLab, Bitbucket, etc.)
-   Production debugging capabilities (debugging is for local development only)
-   Automated rollback of failed deployments

## Assumptions

-   Developers have container runtime installed locally (assumption: Docker Desktop or compatible)
-   Azure subscription has sufficient quota for all resources in deployment template (assumption: standard subscription limits)
-   GitHub repositories use standard webhook capabilities available in free/paid GitHub.com accounts
-   Workspace scripts are text files under 10MB each (assumption: typical workflow size)
-   Network connectivity exists between Azure and GitHub for webhook delivery
-   Administrators have necessary Azure permissions to create resources and assign roles
-   Container image updates follow semantic versioning and breaking changes are documented
-   Local development uses localhost ports that are not conflicting with other services (assumption: standard ports 7071, 4280 available)

## Dependencies

-   Docker Hub public registry hosting the platform image must be accessible from deployment targets
-   Azure subscription and appropriate service quotas
-   GitHub account with repository admin access for Static Web App CI/CD connection (frontend repository)
-   GitHub account with repository admin access for workspace webhook configuration (optional, for workflow sync)
-   DNS configuration for custom domains (if using custom URLs instead of Azure defaults)
-   Certificate management for HTTPS (if using custom domains)

## Constraints

-   Container image size should remain under 2GB for reasonable pull times
-   GitHub webhook payload size limits (5MB per GitHub documentation)
-   Azure Functions container memory and CPU limits based on selected SKU
-   File storage IOPS and throughput limits based on Azure Files tier
-   Maximum file path length supported by underlying filesystem (260 characters Windows, 4096 Linux)
