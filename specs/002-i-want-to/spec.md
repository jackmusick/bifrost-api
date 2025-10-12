# Feature Specification: Workflow Engine and User Code Separation

**Feature Branch**: `002-i-want-to`
**Created**: 2025-10-12
**Status**: Draft
**Input**: User description: "I want to separate workflow engine from user-defined code. Ideally, user code would live in their own repo that the workflow engine Azure Function would injest somehow, possibly into table storage or table storage + blob storage (I don't know the size limitations of table storage columns). The problem right now is that if a developer interacts with the workflow project to write and deploy their code, there's a lot of system-level load-bearing stuff that they could break or worse, change that allows for data leakage."

## Clarifications

### Session 2025-10-12

- Q: Is the main isolation risk developers accidentally modifying engine code, or malicious runtime code exploitation? → A: Accidental modifications (option A). GitHub Actions can check for `/engine/*` changes to prevent accidental commits.
- Q: How should storage failures be handled during workflow execution? → A: Fail with retriable error (option A). If Azure Storage is down, there are bigger infrastructure issues.
- Q: Should architecture use separate repos or single repo with protected `/engine` folder? → A: Single repo with `/engine` (system code) and `/workspace` (developer code) folders. GitHub Action blocks changes to `/engine/*` except from upstream syncs.
- Q: How should local development work? → A: Azure Functions local runtime (`func start`) + Azurite emulator. Provide seed script to populate test org/user data. Developers use Postman/curl to test with `X-Organization-Id` and `X-User-Id` headers (only accepted in Development mode).
- Q: How should authentication work across local and production environments? → A: Use tiered authentication flow (same logic for both local and production): (1) If `x-functions-key` present → bypass all auth, accept `X-Organization-Id`/`X-User-Id` headers at face value, log warning for audit; (2) If `X-MS-CLIENT-PRINCIPAL` present → normal Entra ID auth flow with user/org validation; (3) Neither → 403 Unauthorized. This allows proper production auth testing locally via SWA while maintaining system access via function keys.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Writes Workflow Code in Protected Workspace (Priority: P1)

Developers fork the workflows repository and write their custom workflow logic exclusively in the `/workspace` folder without modifying or accessing the `/engine` folder containing system infrastructure code. GitHub Actions automatically block any commits that modify `/engine` files.

**Why this priority**: This is the foundational capability that enables safe separation of concerns. Without this protection, developers continue to have dangerous access to system internals, risking data leakage and system instability.

**Independent Test**: Can be fully tested by a developer forking the repo, creating a workflow in `/workspace`, attempting to modify `/engine` code, and verifying the commit is blocked by GitHub Actions while valid `/workspace` changes succeed.

**Acceptance Scenarios**:

1. **Given** a developer has forked the workflows repository, **When** they create workflow code in the `/workspace` folder, **Then** they can commit and deploy their changes successfully
2. **Given** a developer attempts to modify files in the `/engine` folder, **When** they commit or create a PR, **Then** the GitHub Action blocks the change with a clear error message
3. **Given** an upstream update to `/engine` is available, **When** the developer syncs from the canonical repository, **Then** the `/engine` updates are allowed while preserving their `/workspace` customizations

---

### User Story 2 - Workflow Engine Executes Workspace Code Safely (Priority: P2)

The workflow engine loads and executes code from the `/workspace` folder in an isolated runtime environment that prevents access to system-level resources, configuration, or data from other tenants/organizations, even if workspace code attempts to import engine modules.

**Why this priority**: Once workspace code separation exists, safe execution is the next critical requirement to prevent the security risks mentioned (data leakage, system modification through runtime imports).

**Independent Test**: Can be tested by writing workspace code that attempts to import engine modules or access restricted resources, executing it, and verifying that access is denied while legitimate workflow operations succeed.

**Acceptance Scenarios**:

1. **Given** workspace workflow code attempts to import engine modules (e.g., `from engine.shared.storage import ...`), **When** the workflow executes, **Then** the import is blocked with an ImportError and the execution fails safely
2. **Given** workflow code from Organization A is executing, **When** it attempts to access data belonging to Organization B through the provided context object, **Then** access is denied and an appropriate error is logged
3. **Given** workspace code execution completes successfully, **When** results are stored, **Then** they are properly scoped to the correct organization/tenant with full audit trail

---

### User Story 3 - Developer Tests Workflows Locally (Priority: P3)

Developers can run and debug their workspace workflows locally using the Azure Functions runtime with Azurite storage emulator and seeded test data, allowing full local development without deploying to production.

**Why this priority**: This enables iterative development and debugging. While important for developer productivity, it builds on the foundation of P1 and P2.

**Independent Test**: Can be tested by running the Azurite seed script, starting Azure Functions locally, and executing a workspace workflow via Postman with test org/user headers.

**Acceptance Scenarios**:

1. **Given** a developer has run the Azurite seed script, **When** they start the Azure Functions runtime locally and execute a workflow with an `x-functions-key` plus `X-Organization-Id` and `X-User-Id` headers, **Then** the workflow executes with properly scoped test organization context
2. **Given** a developer wants to test production authentication locally, **When** they run the workflow through Azure SWA locally with mock Entra ID auth (`X-MS-CLIENT-PRINCIPAL` header), **Then** the system validates the user and organization membership using the same flow as production
3. **Given** a developer needs to debug a workflow, **When** they set breakpoints in their workspace code and run locally with function key auth, **Then** they can step through execution with full access to context and state

---

### Edge Cases

- What happens when a developer force-pushes to bypass the GitHub Action that protects `/engine`?
- How does the system handle workspace code with syntax errors or import errors during discovery/loading?
- What happens when workspace code execution times out or consumes excessive resources?
- How are workflows handled when the Azurite emulator is unavailable during local development?
- What happens when function key auth is used with a non-existent organization ID in the `X-Organization-Id` header?
- What happens if both `x-functions-key` and `X-MS-CLIENT-PRINCIPAL` headers are present in the same request?
- How does the system prevent workspace code from using reflection or other dynamic techniques to bypass import restrictions?
- What happens when a developer syncs upstream `/engine` changes that conflict with their `/workspace` code's expected interfaces?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Repository structure MUST separate engine code (`/engine` folder) from workspace code (`/workspace` folder) with clear boundaries
- **FR-002**: GitHub Action MUST automatically block commits or pull requests that modify files in the `/engine` folder, except for commits originating from the canonical upstream repository
- **FR-003**: System MUST prevent workspace code from importing engine modules at runtime by implementing Python import restrictions that raise ImportError for any imports starting with `engine.` or `shared.` from engine directories
- **FR-004**: System MUST execute workspace workflow code with organization context that enforces tenant boundaries, preventing access to other organizations' data
- **FR-005**: System MUST implement tiered authentication with the following priority: (1) If `x-functions-key` is present (query param or header), bypass authentication and use `X-Organization-Id` and `X-User-Id` headers directly; (2) If `X-MS-CLIENT-PRINCIPAL` is present, extract and validate user from Entra ID JWT and enforce organization membership; (3) If neither present, return 403 Unauthorized
- **FR-006**: System MUST log a warning-level audit entry whenever function key authentication bypass is used, including the org ID, user ID from headers, source IP address, and timestamp
- **FR-007**: System MUST validate that organization ID provided in `X-Organization-Id` header exists and is active in the Organizations table, even when using function key authentication bypass
- **FR-008**: System MUST provide an Azurite seed script that populates local storage with test organizations, users, and configuration data for local development
- **FR-009**: System MUST support local development workflow testing using Azure Functions runtime (`func start`) with Azurite emulator without requiring production authentication
- **FR-010**: System MUST prevent workspace code from accessing system-level Azure Table Storage tables, Key Vault secrets, or configuration outside their organization scope through the provided context object
- **FR-011**: System MUST scan workspace code during engine initialization to discover workflows using decorator-based registration, failing startup if workspace code contains import violations
- **FR-012**: System MUST handle Azure Storage unavailability by failing workflow execution with a retriable error, allowing upstream retry mechanisms to handle transient failures

### Key Entities

- **Engine Folder**: System-controlled directory (`/engine`) containing core workflow engine infrastructure, storage abstractions, context management, execution logging, and Azure Functions endpoints; protected from modification by GitHub Actions
- **Workspace Folder**: Developer-controlled directory (`/workspace`) containing custom workflow implementations organized in any structure; developers have full control within this directory
- **Organization Context**: Runtime object injected into workspace workflow executions containing organization identity, configuration, secrets access (scoped to org), and audit logging capabilities; enforces tenant isolation boundaries
- **Import Restrictor**: Python import hook mechanism that intercepts import statements during workspace code execution and blocks attempts to import engine internal modules
- **Azurite Seed Data**: Test dataset including sample organizations, users, configuration, and permissions loaded into local Azurite storage emulator for development testing

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can write and test workspace workflows locally using Azurite and function key auth, with full debug capabilities, in under 5 minutes from initial setup
- **SC-002**: Zero successful attempts by workspace code to import engine modules or access system-level tables outside their organization scope (100% isolation enforcement)
- **SC-003**: GitHub Actions block 100% of attempts to modify `/engine` folder contents in developer commits, with clear error messages explaining the restriction
- **SC-004**: System eliminates accidental engine modification risks by preventing workspace code from accessing `/engine` internals at both commit-time and runtime (zero incidents of successful engine code modification by developers)
- **SC-005**: 100% of workflow executions operate within correct organization/tenant boundaries with no cross-contamination, regardless of authentication method used
- **SC-006**: All function key authentication bypass usage is logged with warning level for audit purposes (100% logging coverage)
- **SC-007**: Local development authentication flow matches production behavior when using `X-MS-CLIENT-PRINCIPAL`, enabling accurate integration testing

## Assumptions

- Developers will fork the canonical workflows repository to create their own instance rather than working directly in the upstream repository
- Azure Functions host keys and function keys are managed securely and rotated regularly according to security best practices
- Azure SWA provides mock Entra ID authentication in local development mode via `X-MS-CLIENT-PRINCIPAL` header
- Organization/tenant identity is already established in the Organizations table and available for validation during workflow execution
- Workspace workflow code conforms to decorator-based registration pattern (`@workflow`, `@data_provider`) for engine discovery
- Python import hook mechanisms are sufficient to prevent workspace code from importing engine modules without requiring OS-level sandboxing
- Developers have Node.js, Python, Azure Functions Core Tools, and Azurite installed for local development
- The canonical workflows repository maintains a stable interface for organization context and decorators that workspace code depends on
