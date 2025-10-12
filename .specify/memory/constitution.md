<!--
SYNC IMPACT REPORT
==================
Version Change: TEMPLATE → 1.0.0
Change Type: MINOR (Initial constitution establishment)
Date: 2025-10-10

Principles Defined:
  - I. Azure-First Architecture (new)
  - II. Table Storage Only (new)
  - III. Python Backend Standard (new)
  - IV. Test-First Development (new)
  - V. Multi-Tenancy by Design (new)

Sections Added:
  - All Core Principles sections (5 principles)
  - Technology Standards section
  - Development Workflow section
  - Governance section

Templates Status:
  ✅ plan-template.md - Reviewed, Constitution Check placeholder exists
  ✅ spec-template.md - Reviewed, technology-agnostic as intended
  ✅ tasks-template.md - Reviewed, includes optional test guidance

Command Files:
  ✅ .claude/commands/*.md - No agent-specific references found

Follow-up TODOs:
  - None. All placeholders filled. Constitution ready for use.
-->

# Bifrost Integrations Constitution

## Core Principles

### I. Azure-First Architecture

All platform components MUST use Azure services exclusively. This principle ensures:

-   **Unified ecosystem**: Single cloud provider simplifies management, billing, and support
-   **Leveraged CSP pricing**: Take advantage of Microsoft partner pricing
-   **Integrated auth**: Azure AD provides single sign-on across all components
-   **Consistent tooling**: Familiar Azure CLI, Portal, and ARM templates

**Non-negotiable rules:**

-   All compute MUST use Azure Functions (Python 3.11 runtime)
-   All storage MUST use Azure Storage services (Table, Blob, Key Vault)
-   All authentication MUST use Azure AD
-   No third-party cloud services (AWS, GCP) for core infrastructure
-   Local development MUST use Azurite (Azure Storage Emulator)

**Rationale**: Using a single cloud provider reduces complexity, cost, and cognitive load. The team already has Azure expertise and CSP pricing benefits.

### II. Table Storage Only

All persistent data MUST be stored in Azure Table Storage. NO SQL databases allowed.

**Non-negotiable rules:**

-   All entity storage MUST use Azure Table Storage
-   NO Azure SQL, Cosmos DB, or third-party databases
-   Partition keys MUST be chosen for org-scoped access patterns
-   Dual-indexing pattern MUST be used when bidirectional lookups are required
-   Large data (>32KB) MUST use Blob Storage with Table Storage reference
-   Local development MUST use Azurite

**Acceptable exceptions:**

-   Blob Storage for logs, files, and large execution results (with Table Storage pointers)
-   Application Insights for metrics and observability
-   If project exceeds 1000+ organizations with complex cross-org analytics requirements

**Rationale**: Table Storage provides sub-10ms queries for org-scoped operations, costs <$1/month vs $5+/month for SQL, requires no schema migrations, and is trivial to set up locally. The MSP use case (50-200 orgs, org-scoped queries) is perfectly suited to this model.

### III. Python Backend Standard

All backend code MUST be written in Python 3.11 using Azure Functions v2 programming model.

**Non-negotiable rules:**

-   Management API MUST use Python 3.11 Azure Functions
-   Workflow Engine MUST use Python 3.11 Azure Functions
-   All shared code between API and Workflows MUST be in `shared/` module
-   Type hints MUST be used for all function signatures
-   Async/await MUST be used for all I/O operations (Table Storage, HTTP calls)
-   Pydantic MUST be used for request/response models

**Acceptable exceptions:**

-   Frontend (React/TypeScript) for client UI
-   Infrastructure as Code (Bicep/ARM templates)
-   Build/deployment scripts (Bash, PowerShell)

**Rationale**: Single language for all backend code enables code sharing (shared/ module), consistent patterns (decorators, context loading), and reduces context switching. Python is ideal for workflows and has excellent Azure SDK support.

### IV. Test-First Development

Tests MUST be written before implementation for all non-trivial features.

**Non-negotiable rules:**

-   For any feature with business logic, tests MUST be written first
-   Tests MUST fail before implementation begins (Red-Green-Refactor)
-   Contract tests MUST be written for all HTTP endpoints
-   Integration tests MUST be written for workflows that touch external services
-   All test files MUST be in `tests/` directory with clear naming

**Test categories (examples):**

-   **Contract tests**: `tests/contract/test_organizations_api.py` - API contracts
-   **Integration tests**: `tests/integration/test_user_onboarding_workflow.py` - End-to-end flows
-   **Unit tests** (optional): `tests/unit/test_context.py` - Isolated function tests

**When tests are optional:**

-   UI component styling/layout
-   Configuration files
-   Documentation updates
-   Simple CRUD operations with well-established patterns

**Rationale**: Test-first development prevents regressions, documents expected behavior, and ensures features work before shipping. For a multi-tenant automation platform, this is critical.

### V. Single-MSP Multi-Organization Design

This platform serves a SINGLE MSP managing MULTIPLE client organizations. All features MUST support org-scoped data with global MSP-level configuration.

**Architecture clarity:**

-   This is a **single MSP platform**, NOT a multi-MSP SaaS
-   The MSP has **technicians** (MSP users) who manage the platform and write workflows
-   The MSP has **client organizations** (customers) with external users who execute forms
-   Config and secrets are **global-first** (MSP-level) with optional org overrides
-   Workflows run at **MSP level** but can be org-aware when needed

**Non-negotiable rules:**

-   All organization-specific entities MUST use org-scoped partition keys
-   Global MSP config/secrets MUST use `PartitionKey = "GLOBAL"`
-   All HTTP endpoints MUST validate `X-Organization-Id` header (when org context required)
-   Permission checks MUST verify user has access to the org before processing requests
-   Organization context MUST be loaded once per request and passed through call chain
-   MSP users bypass org restrictions; ORG users require role-based permissions

**Key patterns:**

-   **Partition strategy**: `PartitionKey = OrgId` for org-specific entities
-   **Global partition**: `PartitionKey = "GLOBAL"` for MSP-wide config, secrets, forms
-   **Dual-indexing**: Maintain both `UserPermissions` (by UserId) and `OrgPermissions` (by OrgId)
-   **Context object**: OrganizationContext loaded by decorators, passed to all functions
-   **Config fallback**: Check org-specific first → fallback to global → return None
-   **User types**: MSP users (full access) vs ORG users (role-based form access)

**Rationale**: This platform serves an MSP managing 50-200 client organizations. Most config/secrets are MSP-wide (API credentials, environment variables), with org-specific overrides for data mapping (e.g., finding client in HaloPSA). Org context enables targeted automation while maintaining global workflow libraries.

## Technology Standards

All projects MUST adhere to the following technical specifications:

**Language/Runtime:**

-   Frontend: React 18+ with TypeScript 4.9+
-   Backend: Python 3.11 (Azure Functions v2 programming model)
-   Infrastructure: Bicep (ARM templates)

**Primary Dependencies:**

-   Frontend: React Router, Axios, @azure/msal-browser
-   Backend: azure-functions, azure-data-tables, aiohttp, pydantic
-   Testing: pytest, pytest-asyncio (backend); Jest, React Testing Library (frontend)

**Storage:**

-   Persistent data: Azure Table Storage (via Azurite locally)
-   Secrets: Azure Key Vault
-   Large files/logs: Azure Blob Storage
-   NO SQL databases

**Authentication:**

-   Azure AD (single app registration for all components)
-   JWT tokens validated on every request
-   Org-scoped permissions stored in Table Storage

**Performance Goals:**

-   Workflow context loading: <20ms (Table Storage queries)
-   API response time: <200ms p95 (org-scoped queries)
-   Workflow execution: Sub-second startup time
-   UI page load: <2s initial, <500ms navigation

**Scale/Scope:**

-   Target: 50-200 client organizations
-   Users: 5-50 techs per MSP
-   Workflows: 100-1000 executions per day
-   Forms: 10-100 per organization

## Development Workflow

All feature development MUST follow this workflow:

1. **Specification**: Create feature spec using `spec-template.md` (via `/speckit.specify`)
2. **Planning**: Generate implementation plan using `plan-template.md` (via `/speckit.plan`)
3. **Constitution Check**: Verify feature complies with all principles before proceeding
4. **Test Creation**: Write tests first (if feature requires tests per Principle IV)
5. **Implementation**: Write code to make tests pass (Red-Green-Refactor)
6. **Review**: Code review checks constitution compliance
7. **Deployment**: CI/CD pipeline deploys to staging, then production

**Constitution compliance verification:**

-   All PRs MUST include Constitution Check section in plan.md
-   Any principle violations MUST be explicitly justified
-   Complexity additions MUST be documented in plan.md "Complexity Tracking" table

**Branch strategy:**

-   `main`: Production-ready code
-   `develop`: Integration branch for features
-   `###-feature-name`: Feature branches following spec numbering

## Governance

This constitution supersedes all other development practices and architectural decisions.

**Amendment procedure:**

1. Propose amendment with justification and impact analysis
2. Update constitution with version bump (MAJOR for breaking changes, MINOR for additions, PATCH for clarifications)
3. Run consistency check across all templates (plan, spec, tasks, commands)
4. Update dependent artifacts (templates, commands, documentation)
5. Commit with message: `docs: amend constitution to vX.Y.Z (description)`

**Compliance review:**

-   All PRs MUST verify constitution compliance
-   Any complexity additions MUST be justified (why simpler alternatives insufficient)
-   Constitution violations MUST be approved by tech lead with documented rationale

**Versioning policy:**

-   **MAJOR**: Backward-incompatible changes (principle removal, redefinition that invalidates existing code)
-   **MINOR**: New principles or sections added (requires team review)
-   **PATCH**: Clarifications, wording fixes, typos (no semantic changes)

**Runtime guidance:**

-   For day-to-day development guidance, refer to `PROJECT.md` (architecture and patterns)
-   For AI-assisted development, refer to `client/AI_DOCS.md`
-   Constitution defines WHAT MUST be done; PROJECT.md defines HOW to do it

**Version**: 1.1.0 | **Ratified**: 2025-10-10 | **Last Amended**: 2025-10-10 (Principle V clarified for single-MSP architecture)
