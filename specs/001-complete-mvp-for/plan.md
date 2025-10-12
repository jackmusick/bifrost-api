# Implementation Plan: MSP Automation Platform MVP

**Branch**: `001-complete-mvp-for` | **Date**: 2025-10-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-complete-mvp-for/spec.md`

## Summary

Building a code-first Rewst alternative that enables MSP technicians to manage client organizations, create dynamic forms, and execute Python-based automation workflows with full local debugging support. The platform is multi-tenant by design with Azure AD authentication, org-scoped permissions, and Azure Table Storage for all persistent data. Key capabilities include: GDAP tenant linking, workflow auto-registration via decorators, data providers for dynamic form fields, and comprehensive execution history with audit trails.

## Technical Context

**Language/Version**: Python 3.11 (Azure Functions v2), React 18+ with TypeScript 4.9+

**Primary Dependencies**:
- Backend (Management API & Workflow Engine): azure-functions, azure-data-tables, aiohttp, pydantic, azure-identity, azure-keyvault-secrets
- Frontend (React SPA): React Router, Axios, @azure/msal-browser, @azure/msal-react
- Testing: pytest, pytest-asyncio, pytest-mock (backend); Jest, React Testing Library, MSW (frontend)

**Storage**:
- Persistent data: Azure Table Storage with org-scoped partitioning
- Secrets: Azure Key Vault (per-org credentials for integrations)
- Large files/logs: Azure Blob Storage with Table Storage references
- Local development: Azurite for Table/Blob Storage emulation

**Testing**:
- Backend: pytest with async support, contract tests for HTTP endpoints, integration tests for workflow execution
- Frontend: Jest + React Testing Library for components, MSW for API mocking
- Test-first development per constitution Principle IV

**Target Platform**:
- Management API: Azure Functions (Python 3.11, Linux runtime)
- Workflow Engine: Azure Functions (Python 3.11, Linux runtime)
- Frontend: Azure Static Web Apps with "Bring Your Own Functions" integration
- Local: Azurite + func CLI + React dev server

**Project Type**: Web application (3 components: client UI, Management API, Workflow Engine)

**Performance Goals**:
- Workflow context loading: <20ms (single-partition Table Storage queries)
- API response time: <200ms p95 for org-scoped queries
- Workflow execution: Sub-second startup, <5 seconds total for typical operations
- UI page load: <2s initial, <500ms navigation
- Data provider queries: <2s for dynamic form field options

**Constraints**:
- NO SQL databases (Table Storage only per constitution Principle II)
- Azure services only (no AWS/GCP per constitution Principle I)
- Python 3.11 for all backend code (Principle III)
- Multi-tenant from day one - all data org-scoped (Principle V)
- Test-first development for business logic (Principle IV)

**Scale/Scope**:
- Target: 50-200 client organizations
- Users: 5-50 MSP technicians per deployment
- Workflows: 100-1000 executions per day
- Forms: 10-100 per organization
- Data retention: 90 days execution history, configurable

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Azure-First Architecture ✅ PASS

- ✅ All compute uses Azure Functions (Python 3.11 runtime)
- ✅ All storage uses Azure services (Table Storage, Blob Storage, Key Vault)
- ✅ All authentication uses Azure AD with single app registration
- ✅ No third-party cloud services for core infrastructure
- ✅ Local development uses Azurite for storage emulation

**Compliance**: Feature is fully compliant. All components are Azure-native.

### Principle II: Table Storage Only ✅ PASS

- ✅ All persistent entities use Azure Table Storage
- ✅ NO SQL databases (Azure SQL, Cosmos DB) used
- ✅ Partition keys chosen for org-scoped access patterns (PartitionKey=OrgId)
- ✅ Dual-indexing pattern for UserPermissions/OrgPermissions and WorkflowExecutions/UserExecutions
- ✅ Large execution results and logs use Blob Storage with Table Storage pointers
- ✅ Local development uses Azurite

**Compliance**: Feature is fully compliant. Table Storage is the sole persistent store.

### Principle III: Python Backend Standard ✅ PASS

- ✅ Management API uses Python 3.11 Azure Functions
- ✅ Workflow Engine uses Python 3.11 Azure Functions
- ✅ Shared code in `shared/` module (decorators, context loading, storage helpers)
- ✅ Type hints required for all function signatures
- ✅ Async/await for all I/O operations (Table Storage, HTTP, Key Vault)
- ✅ Pydantic for request/response models and validation

**Compliance**: Feature is fully compliant. Frontend uses React/TypeScript as allowed exception.

### Principle IV: Test-First Development ✅ PASS

- ✅ Contract tests for all HTTP endpoints (organizations, forms, workflows, permissions, executions)
- ✅ Integration tests for workflow execution with organization context
- ✅ Integration tests for data provider execution
- ✅ Tests written before implementation (Red-Green-Refactor)
- ✅ Test files in `tests/contract/` and `tests/integration/` directories
- ⚠️ UI component tests optional (allowed per constitution - styling/layout)

**Compliance**: Feature requires comprehensive test coverage for business logic. UI tests optional but recommended for form builder/renderer.

### Principle V: Multi-Tenancy by Design ✅ PASS

- ✅ All Table Storage entities use org-scoped partition keys (PartitionKey=OrgId)
- ✅ All HTTP endpoints validate `X-Organization-Id` header
- ✅ All queries filter by organization context
- ✅ Permission checks verify user has org access before processing requests
- ✅ OrganizationContext loaded once per request via decorator, passed to functions
- ✅ Dual-indexing for UserPermissions (by UserId) and OrgPermissions (by OrgId)
- ✅ Global forms use PartitionKey="GLOBAL" for shared resources

**Compliance**: Feature is architected for multi-tenancy from the ground up. Zero cross-org data leakage tolerance.

### Overall Constitution Compliance: ✅ PASS

**No violations detected.** Feature aligns with all 5 core principles. Proceed to Phase 0 research.

## Project Structure

### Documentation (this feature)

```
specs/001-complete-mvp-for/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (technology decisions and patterns)
├── data-model.md        # Phase 1 output (entity definitions and Table Storage schema)
├── quickstart.md        # Phase 1 output (developer onboarding guide)
├── contracts/           # Phase 1 output (OpenAPI specs for Management API)
│   ├── organizations.yaml
│   ├── permissions.yaml
│   ├── forms.yaml
│   ├── executions.yaml
│   └── workflows.yaml   # Workflow Engine metadata endpoint
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

This is a **web application** with three distinct components sharing authentication and storage.

```
# MANAGEMENT UI (React Static Web App)
client/
├── src/
│   ├── components/          # Reusable React components
│   │   ├── common/          # Buttons, inputs, layouts, nav
│   │   ├── organizations/   # Org list, create, edit, config
│   │   ├── forms/           # Form builder, form renderer
│   │   ├── workflows/       # Workflow list, execution trigger
│   │   ├── executions/      # Execution history, details
│   │   └── permissions/     # User permission management
│   ├── services/            # API clients
│   │   ├── apiClient.ts     # Management API wrapper
│   │   ├── workflowClient.ts # Workflow Engine wrapper
│   │   └── authService.ts   # Azure AD MSAL wrapper
│   ├── types/               # TypeScript interfaces
│   │   ├── organization.ts
│   │   ├── form.ts
│   │   ├── workflow.ts
│   │   ├── execution.ts
│   │   └── permission.ts
│   ├── pages/               # Route components
│   │   ├── OrganizationsPage.tsx
│   │   ├── FormsPage.tsx
│   │   ├── ExecutionsPage.tsx
│   │   └── WorkflowsPage.tsx
│   ├── hooks/               # Custom React hooks
│   │   ├── useOrganizations.ts
│   │   ├── useForms.ts
│   │   └── useAuth.ts
│   ├── App.tsx              # Main app component with routing
│   └── index.tsx            # Entry point
├── public/
├── staticwebapp.config.json # Routes, auth config, linked backends
├── package.json
├── tsconfig.json
└── tests/                   # Jest + React Testing Library
    ├── components/
    └── services/

# MANAGEMENT API (Azure Functions - Python)
# NOTE: This will be a separate repository: msp-automation-api
# Structure shown here for reference
management-api/              # FUTURE: Separate repo
├── functions/               # HTTP-triggered endpoints
│   ├── organizations.py     # CRUD for organizations
│   ├── org_config.py        # Organization configuration k/v
│   ├── permissions.py       # User permission management
│   ├── forms.py             # Form CRUD and retrieval
│   └── executions.py        # Execution history queries
├── shared/                  # Shared utilities
│   ├── storage.py           # TableStorageService wrapper
│   ├── auth.py              # Token validation, permission checks
│   ├── models.py            # Pydantic models for entities
│   └── middleware.py        # Auth middleware decorators
├── function_app.py          # Entry point (registers blueprints)
├── requirements.txt
├── host.json
├── local.settings.json.example
└── tests/
    ├── contract/            # API contract tests
    └── integration/         # Integration tests with Table Storage

# WORKFLOW ENGINE (Azure Functions - Python)
# NOTE: This will be a separate repository: msp-automation-workflows
# Structure shown here for reference
workflow-engine/             # FUTURE: Separate repo
├── workflows/               # Main automation workflows
│   ├── user_onboarding.py   # Example: M365 user onboarding
│   └── __init__.py          # Auto-discovery of @workflow decorated functions
├── data_providers/          # Data provider functions (renamed from "options")
│   ├── get_available_licenses.py  # Example: M365 license options
│   └── __init__.py          # Auto-discovery of @data_provider decorated functions
├── shared/                  # Shared utilities
│   ├── decorators.py        # @workflow, @data_provider, @param decorators
│   ├── context.py           # OrganizationContext class
│   ├── registry.py          # Workflow/data provider metadata registry
│   ├── storage.py           # Table Storage helpers
│   ├── integrations/        # Pre-authenticated integration clients
│   │   ├── msgraph.py       # Microsoft Graph client
│   │   ├── halopsa.py       # HaloPSA client
│   │   └── base.py          # Base integration class
│   └── error_handling.py    # Workflow exception handling
├── admin/                   # Admin endpoints
│   └── metadata.py          # GET /admin/metadata (workflow discovery)
├── function_app.py          # Entry point (registers HTTP triggers for workflows)
├── requirements.txt
├── host.json
├── local.settings.json.example
└── tests/
    ├── contract/            # Workflow execution contract tests
    ├── integration/         # Integration tests with real integrations (mocked)
    └── unit/                # Unit tests for context, decorators, registry
```

**Structure Decision**:

We are using Option 2 (Web application) with THREE separate repositories:

1. **`msp-automation-platform`** (this repo): Client UI only (React Static Web App)
2. **`msp-automation-api`**: Management API (Azure Functions - Python)
3. **`msp-automation-workflows`**: Workflow Engine (Azure Functions - Python)

**Rationale**:
- Separate repos allow independent deployment cycles (client can deploy without redeploying workflows)
- Clear separation of concerns (UI, API, automation logic)
- Enables different teams to own different components
- Follows Azure Static Web Apps "Bring Your Own Functions" pattern
- All three share same Azure AD app registration and Table Storage account

**Current Implementation Scope**:
For this MVP, we will implement **all three components** but focus primarily on the **`client`** directory in this repository. The Management API and Workflow Engine will be referenced and designed (data models, contracts) but initial implementation will be stubbed/mocked for client development.

## Complexity Tracking

*No constitution violations detected. This section is empty.*

## Design Artifacts

The following design artifacts have been created as part of Phase 0 (Research) and Phase 1 (Design & Contracts):

### Phase 0: Technology Research

**File**: `specs/001-complete-mvp-for/research.md`

**Contents**: 7 major technology decision topics:
1. Azure Functions v2 Programming Model (decorator-based HTTP triggers, blueprints)
2. Table Storage Schema Design (org-scoped partitioning, dual-indexing patterns)
3. Workflow Decorator Pattern (`@workflow`, `@data_provider`, `@param` decorators)
4. Organization Context Loading (automatic injection, config/secrets/integrations)
5. Data Providers (renamed from "options" - supplies dynamic form field data)
6. Authentication & Authorization Flow (Azure AD JWT validation, permission checks)
7. Local Development & Debugging Setup (Azurite, func CLI, native Python debugging)

**Status**: ✅ Complete

### Phase 1: Data Model Design

**File**: `specs/001-complete-mvp-for/data-model.md`

**Contents**: Complete Table Storage schema for all 8 entity types:
- Organizations (single-partition listing with PartitionKey="ORG")
- UserPermissions / OrgPermissions (dual-indexed for bidirectional queries)
- OrgConfig (org-scoped configuration key-value pairs)
- Forms (org-scoped with global forms using PartitionKey="GLOBAL")
- WorkflowExecutions / UserExecutions (dual-indexed with reverse timestamp ordering)
- ExecutionLogs (references to Blob Storage for large log files)

**Includes**:
- Entity relationship diagrams
- Partition key strategies
- RowKey patterns (UUIDs, reverse timestamps)
- Query patterns and performance characteristics
- Migration strategies

**Status**: ✅ Complete

### Phase 1: API Contracts

**Directory**: `specs/001-complete-mvp-for/contracts/`

**Files Created**:
1. **management-api.yaml** (OpenAPI 3.0 specification)
   - All Management API endpoints (Organizations, Permissions, Forms, Config, Executions)
   - Complete schema definitions for all request/response models
   - Security schemes (Azure AD JWT)
   - Parameter definitions (X-Organization-Id header requirement)
   - Example requests and responses

2. **workflow-api.yaml** (OpenAPI 3.0 specification)
   - Workflow Engine endpoints (metadata discovery, workflow execution, data providers)
   - Workflow and data provider metadata schemas
   - Execution request/response models
   - Data provider option format
   - Admin metadata endpoint for auto-discovery

**Status**: ✅ Complete

### Phase 1: Developer Onboarding Guide

**File**: `specs/001-complete-mvp-for/quickstart.md`

**Contents**: Comprehensive developer onboarding guide covering:
- Prerequisites and environment setup
- Quick start (5 minutes to running locally)
- Creating first workflow with decorators
- Creating data providers for dynamic form fields
- Debugging workflows with native Python tooling (VSCode, PyCharm)
- Understanding organization context
- Project structure navigation
- Common development workflows
- Testing patterns (contract, integration, unit)
- Troubleshooting guide
- Environment configuration

**Status**: ✅ Complete

### Agent Context Update

**File**: `.specify/memory/agent-context.md`

**Contents**: Technical context and patterns for AI agents:
- Platform overview and key differentiators
- Complete technology stack (backend, frontend, local dev, deployment)
- Repository structure (3-repo strategy)
- Core architectural patterns (8 major patterns documented)
- Common code patterns with examples
- Testing patterns
- Performance considerations and optimization strategies
- Security patterns (authentication, authorization, secret management)
- Deployment patterns
- Common gotchas and solutions

**Status**: ✅ Complete

## Post-Design Constitution Re-Evaluation

**Re-Evaluation Date**: 2025-10-10 (post Phase 1 design completion)

All design artifacts (data-model.md, API contracts, quickstart.md, agent-context.md) have been reviewed against the 5 constitution principles:

### Principle I: Azure-First Architecture ✅ PASS
- ✅ All compute confirmed using Azure Functions (documented in quickstart.md, agent-context.md)
- ✅ All storage confirmed using Azure services (data-model.md defines 8 Table Storage tables)
- ✅ Authentication confirmed using Azure AD (API contracts define security schemes)
- ✅ No third-party cloud services introduced in design
- ✅ Azurite documented for local development (quickstart.md)

**Compliance**: No violations introduced during design phase.

### Principle II: Table Storage Only ✅ PASS
- ✅ data-model.md defines 8 tables, all using Azure Table Storage exclusively
- ✅ No SQL databases (Azure SQL, Cosmos DB) introduced
- ✅ Dual-indexing patterns implemented for bidirectional queries
- ✅ Blob Storage used only for large files with Table Storage pointers (execution logs)
- ✅ All entity schemas use org-scoped partitioning

**Compliance**: Table Storage is sole persistent data store. No violations.

### Principle III: Python Backend Standard ✅ PASS
- ✅ Python 3.11 confirmed for all backend code (agent-context.md, quickstart.md)
- ✅ Async/await patterns documented in all code examples
- ✅ Pydantic models confirmed in API contracts and agent-context.md
- ✅ Type hints required per agent-context.md code patterns
- ✅ Shared code modules defined (decorators, context, storage, integrations)

**Compliance**: All backend code follows Python 3.11 standards. Frontend uses React/TypeScript as allowed exception.

### Principle IV: Test-First Development ✅ PASS
- ✅ Contract test patterns documented in quickstart.md and agent-context.md
- ✅ Integration test patterns documented with code examples
- ✅ Test directories defined in project structure (tests/contract/, tests/integration/)
- ✅ Test-first workflow documented in quickstart.md
- ✅ Testing strategy pyramid documented in agent-context.md

**Compliance**: Comprehensive test coverage patterns established for business logic.

### Principle V: Multi-Tenancy by Design ✅ PASS
- ✅ All entities in data-model.md use org-scoped partition keys (PartitionKey=OrgId)
- ✅ All API contracts require X-Organization-Id header (documented in both YAML specs)
- ✅ OrganizationContext pattern fully documented in research.md, quickstart.md, agent-context.md
- ✅ Permission check patterns documented in agent-context.md security section
- ✅ Dual-indexing for UserPermissions/OrgPermissions ensures efficient bidirectional queries
- ✅ Global forms use PartitionKey="GLOBAL" (data-model.md)
- ✅ Zero cross-org leakage guaranteed by partition key isolation

**Compliance**: Multi-tenancy architected into every component from ground up. No violations.

### Overall Post-Design Compliance: ✅ PASS

**Conclusion**: All 5 constitution principles remain satisfied after completing Phase 0 (Research) and Phase 1 (Design & Contracts). No violations introduced during design phase. **Cleared to proceed to Phase 2 (Task Generation).**

## Next Steps

### 1. Generate Implementation Tasks

Run the `/speckit.tasks` command to generate `tasks.md` with a dependency-ordered task list:

```bash
/speckit.tasks
```

This will create `specs/001-complete-mvp-for/tasks.md` with:
- Dependency-ordered task graph
- Estimated complexity for each task
- Prerequisites and blockers
- Testing requirements
- Links back to design artifacts

### 2. Begin Implementation

Once tasks.md is generated, proceed with implementation using the `/speckit.implement` command or manual task execution:

**Recommended Approach** (Manual):
1. Review tasks.md for dependency order
2. Start with foundational tasks (Table Storage setup, auth middleware)
3. Follow test-first development (Red-Green-Refactor)
4. Reference design artifacts:
   - data-model.md for entity schemas
   - API contracts for endpoint signatures
   - quickstart.md for code patterns
   - agent-context.md for architectural patterns
5. Use quickstart.md debugging guide for local development

**Alternative Approach** (Automated):
```bash
/speckit.implement
```

This will execute all tasks in dependency order with automatic testing.

### 3. Local Development Setup

Follow quickstart.md to set up your local environment:
1. Start Azurite for local Azure Storage
2. Run Management API on port 7071
3. Run Workflow Engine on port 7072
4. Run React dev server on port 3000
5. Use native Python debugging in VSCode/PyCharm

### 4. Continuous Validation

- Run constitution compliance checks before major milestones
- Execute test suite after each task completion
- Validate API contracts with contract tests
- Review agent-context.md for architectural patterns

### 5. Documentation Maintenance

As implementation progresses:
- Update quickstart.md with new patterns
- Document gotchas in agent-context.md
- Expand API contracts if new endpoints are needed
- Keep data-model.md in sync with schema changes

---

**Implementation plan complete. Ready for task generation with `/speckit.tasks`.**

