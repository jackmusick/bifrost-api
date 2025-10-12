# Implementation Tasks: Bifrost Integrations MVP

**Feature**: Bifrost Integrations MVP
**Branch**: `001-complete-mvp-for`
**Generated**: 2025-10-10
**Updated**: 2025-10-11 (Phase 11 Polish & Integration Complete)
**Status**: ✅ Phase 1-7 Complete | ✅ Phase 8a-b Complete | ✅ Phase 8d-e Complete | ✅ Phase 11 Complete | 📋 Phase 8c, 9-10 Ready (T103-T125)

---

## Implementation Progress

### ✅ Completed Phases (Phase 1-7, Phase 8a-b, Phase 8d-e, Phase 11)

-   **Phase 1-4**: Project Setup, Foundation, Organizations, Permissions - ✅ Complete
-   **Phase 5**: Workflow Development & Registration (T039-T045) - ✅ Complete
-   **Phase 6**: Workflow Execution Infrastructure (T046-T054) - ✅ Complete
-   **Phase 7**: Data Providers (T055-T060) - ✅ Complete (T055-T059 done, T060 optional)
-   **Phase 8a**: Backend Foundation - Config, Roles, Users (T091-T095) (2025-10-11) - ✅ Complete
    -   Config table supporting GLOBAL and org-specific partitions with fallback pattern
    -   Roles, UserRoles, FormRoles tables for role-based access control
    -   UserType enum (PLATFORM vs ORG) with role assignment validation
    -   Comprehensive contract tests (27 roles API tests) and integration tests (24 config tests)
    -   Sensitive value masking for secrets, passwords, tokens, keys
-   **Phase 8b**: Frontend UI - Config, Roles, Users (T096-T102) (2025-10-11) - ✅ Complete
    -   ShadCN UI + Tailwind CSS 4 setup with responsive layout
    -   Global config management UI with scope switching (GLOBAL/org)
    -   Roles management UI with user/form assignment dialogs
    -   User management UI with type filtering and role assignments
    -   Form access control verified (backend filtering implementation confirmed)
-   **Phase 8d**: Form Execution Implementation (2025-10-11 AM) - ✅ Complete
    -   Form submission endpoint with orgId parameter passing
    -   Synchronous execution result display with formatted JSON
    -   Merged Forms and Execute Forms into single card view page
    -   Fixed sidebar navigation to single Forms menu item
    -   API client updated to support params in POST/PUT methods
-   **Phase 8e**: Form Builder UI Enhancements (2025-10-11 PM) - ✅ Complete
    -   Advanced drag-and-drop form builder with @atlaskit/pragmatic-drag-and-drop
    -   Two-section field palette: "Workflow Inputs" (pre-filled from workflow metadata) + "All Field Types"
    -   Visual drop indicators showing insertion position during drag operations
    -   Workflow inputs auto-removed from palette after adding to form
    -   Python variable name validation for field names (snake_case, no keywords)
    -   Form metadata dialog with workflow dropdown from registry metadata endpoint
    -   Compact header layout with badges for workflow/scope
    -   Centered, responsive form preview/runner (max-w-2xl)
    -   Consistent form card layout with pinned action buttons
-   **Phase 11**: Polish & Integration (T126-T132) (2025-10-11) - ✅ Complete
    -   PrettyInputDisplay component for execution history with smart formatting
    -   View toggle (Pretty/JSON) for Platform Admins
    -   ErrorBoundary component for graceful crash recovery
    -   Toast notifications comprehensive across all CRUD operations
    -   Loading states and empty states verified on all 12 pages
    -   Production-ready error handling and UX consistency

### 🚀 Ready for Implementation (Phase 8c, 9-10)

-   **Phase 8c**: Form Builder (T103-T113) - Renumbered
-   **Phase 9**: Form Renderer (T114-T116) - Renumbered (partially complete - form renderer exists, needs data provider support)
-   **Phase 10**: Execution History (T117-T125) - Renumbered

### 📊 Test Status

-   **75+ tests passing** (0 failures)
-   56 contract tests (13 execution + 16 data provider + 27 roles)
-   36 integration tests (12 existing + 24 config)
-   39+ unit tests

### 📁 Artifacts Created

-   Phase 1-7: See `workflows/PHASE6-7-COMPLETE.md` for detailed documentation
-   Phase 8a-b: See section below for testing and validation summary

---

## Overview

This document provides a dependency-ordered task list for implementing the Bifrost Integrations MVP. Tasks are organized by user story to enable independent implementation and testing of each feature increment.

**Total Tasks**: 132 (updated from 90)
**New Tasks Added**: 42 (12 Phase 8 backend/frontend + 30 renumbered existing UI tasks)
**Estimated Complexity**: ~5-6 weeks for full-stack developer
**Testing Strategy**: Test-first development (TDD) - tests before implementation per constitution Principle IV

**🔗 Design Artifacts Referenced**: All tasks now include references to detailed specifications in:

-   `specs/001-complete-mvp-for/data-model.md` - Entity schemas and Table Storage design
-   `specs/001-complete-mvp-for/contracts/*.yaml` - API specifications (OpenAPI 3.0)
-   `specs/001-complete-mvp-for/research.md` - Architectural patterns and technology decisions
-   `specs/001-complete-mvp-for/quickstart.md` - Code examples and developer guide

---

## Task Organization Strategy

Tasks are organized into phases aligned with user stories:

1. **Phase 1: Project Setup** - Repository initialization, tooling, local development environment
2. **Phase 2: Foundational Infrastructure** - Shared components that ALL user stories depend on
3. **Phase 3-6: P1 User Stories** - Core features (Organizations, Auth, Workflows, Execution)
4. **Phase 7: Data Providers** - Dynamic field options for forms
5. **Phase 8: Config, Roles & User Management UI** - Global config, role-based access, user types (T091-T100)
6. **Phase 8b: Form Builder** - Form CRUD with JSON schema (T101-T111)
7. **Phase 9: Form Renderer** - Render and submit forms (T112-T114)
8. **Phase 10: Execution History** - Audit trail and monitoring (T115-T123)
9. **Phase 11: Polish & Integration** - Cross-cutting concerns, deployment (T124-T130)

**MVP Recommendation**: Implement Phases 1-7 for backend foundation, then Phase 8 for UI layer.

---

## Phase 1: Project Setup & Local Development

**Goal**: Initialize all three repositories with proper tooling and local development environment

**Independent Test**: Can run all three components locally (client on port 3000, Management API on port 7071, Workflow Engine on port 7072) with Azurite

**Checkpoint**: ✅ All repos initialized, Azurite running, tables created, basic "hello world" endpoints functional

### T001 [Setup] - Initialize client repository structure

**File**: `client/` (entire directory structure)
**Description**: Create React + TypeScript project structure with Vite or CRA
**Actions**:

-   Run `npm create vite@latest client -- --template react-ts` OR `npx create-react-app client --template typescript`
-   Create directory structure: `src/components/`, `src/services/`, `src/types/`, `src/pages/`, `src/hooks/`
-   Configure `tsconfig.json` with strict mode
-   Add `.env.local.example` with ALL required environment variables (see details below)
-   Create `staticwebapp.config.json` for Azure Static Web Apps routing

**Environment Variables for .env.local.example**:

```env
REACT_APP_MANAGEMENT_API_URL=http://localhost:7071
REACT_APP_WORKFLOW_API_URL=http://localhost:7072
REACT_APP_AZURE_CLIENT_ID=your-app-registration-client-id
REACT_APP_AZURE_TENANT_ID=your-tenant-id
REACT_APP_AZURE_REDIRECT_URI=http://localhost:3000
```

**Reference Documents**:

-   `specs/001-complete-mvp-for/quickstart.md` lines 146-183 - Client project structure
-   `specs/001-complete-mvp-for/plan.md` lines 146-183 - Directory organization

**Dependencies**: None
**Test Coverage**: None (project initialization)
**Estimated Time**: 30 minutes

---

### T002 [Setup] - Initialize Management API repository structure

**File**: `management-api/` (separate repo - future)
**Description**: Create Azure Functions Python project for Management API
**Actions**:

-   Run `func init management-api --python`
-   Create `functions/` directory for HTTP endpoints
-   Create `shared/` directory for utilities (storage.py, auth.py, models.py, middleware.py, secrets.py)
-   Create `tests/contract/` and `tests/integration/` directories
-   Add `requirements.txt` with dependencies: `azure-functions`, `azure-data-tables`, `pydantic`, `azure-identity`, `azure-keyvault-secrets`, `pytest`, `pytest-asyncio`, `pytest-mock`
-   Create `local.settings.json.example` with ALL required settings (see details below)
-   Configure `host.json` for Azure Functions v2

**Environment Variables for local.settings.json.example**:

```json
{
    "IsEncrypted": false,
    "Values": {
        "AzureWebJobsStorage": "UseDevelopmentStorage=true",
        "FUNCTIONS_WORKER_RUNTIME": "python",
        "TABLE_STORAGE_CONNECTION_STRING": "UseDevelopmentStorage=true",
        "BLOB_STORAGE_CONNECTION_STRING": "UseDevelopmentStorage=true",
        "KEY_VAULT_URL": "https://your-keyvault.vault.azure.net/",
        "AZURE_CLIENT_ID": "your-app-registration-client-id",
        "AZURE_TENANT_ID": "your-azure-ad-tenant-id",
        "ALLOWED_ORIGINS": "http://localhost:3000"
    }
}
```

**Reference Documents**:

-   `specs/001-complete-mvp-for/quickstart.md` lines 185-206 - Management API structure
-   `specs/001-complete-mvp-for/plan.md` lines 185-206 - Project organization

**Dependencies**: None
**Test Coverage**: None (project initialization)
**Estimated Time**: 30 minutes

---

### T003 [Setup] - Initialize Workflow Engine repository structure

**File**: `workflow-engine/` (separate repo - future)
**Description**: Create Azure Functions Python project for Workflow Engine
**Actions**:

-   Run `func init workflow-engine --python`
-   Create `workflows/` directory for workflow functions
-   Create `data_providers/` directory for data provider functions
-   Create `shared/` directory (decorators.py, context.py, registry.py, storage.py, integrations/, secrets.py)
-   Create `admin/` directory for metadata endpoint
-   Create `tests/contract/`, `tests/integration/`, `tests/unit/` directories
-   Add `requirements.txt` with same dependencies as Management API
-   Create `local.settings.json.example` with same structure as Management API

**Reference Documents**:

-   `specs/001-complete-mvp-for/quickstart.md` lines 208-237 - Workflow Engine structure
-   `specs/001-complete-mvp-for/plan.md` lines 208-237 - Project organization

**Dependencies**: None
**Test Coverage**: None (project initialization)
**Estimated Time**: 30 minutes

---

### T004 [Setup] [P] - Set up Azurite for local Azure Storage emulation

**File**: N/A (local environment)
**Description**: Install and configure Azurite for local Table Storage and Blob Storage
**Actions**:

-   Install Azurite: `npm install -g azurite`
-   Create startup script: `.specify/scripts/start-azurite.sh`
-   Script should run: `azurite --silent --location ~/azurite --debug ~/azurite/debug.log`
-   Document Azurite connection string in `local.settings.json.example` for both backend repos
-   Verify Azurite starts on ports 10000 (Blob), 10001 (Queue), 10002 (Table)
-   Connection string: `UseDevelopmentStorage=true` or `DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;`

**Reference Documents**:

-   `specs/001-complete-mvp-for/quickstart.md` lines 96-107 - Azurite setup guide
-   `specs/001-complete-mvp-for/plan.md` lines 23 - Local development with Azurite

**Dependencies**: None
**Test Coverage**: None (environment setup)
**Estimated Time**: 15 minutes

---

### T005 [Setup] [P] - Configure linting and formatting for all repos

**File**: `client/.eslintrc.json`, `management-api/.flake8`, `workflow-engine/.flake8`
**Description**: Set up code quality tools for consistency
**Actions**:

-   Client: Add ESLint + Prettier with TypeScript rules (`npm install --save-dev eslint prettier @typescript-eslint/parser @typescript-eslint/eslint-plugin`)
-   Management API: Add `.flake8`, `pyproject.toml` with Black and mypy configs
-   Workflow Engine: Add `.flake8`, `pyproject.toml` with Black and mypy configs
-   Add pre-commit hooks (optional): `pip install pre-commit`

**Dependencies**: T001, T002, T003
**Test Coverage**: None (tooling)
**Estimated Time**: 30 minutes

---

### T005a [Setup] - Initialize Azure Table Storage tables 🆕

**File**: `management-api/shared/init_tables.py`, `workflow-engine/shared/init_tables.py`
**Description**: Create initialization script to ensure all required tables exist (for both local Azurite and production Azure)
**Actions**:

-   Create `init_tables.py` script in both repos using `TableServiceClient` from `azure-data-tables`
-   Check if table exists before creating: `if not service_client.query_tables(f"TableName eq '{table_name}'")`
-   Create all 9 required tables:
    1. **Organizations** (PartitionKey="ORG", stores org master list)
    2. **OrgConfig** (PartitionKey=OrgId, stores config key-value pairs)
    3. **IntegrationConfig** (PartitionKey=OrgId, stores integration settings)
    4. **Users** (PartitionKey="USER", stores MSP technician accounts)
    5. **UserPermissions** (PartitionKey=UserId, for "user's orgs" queries)
    6. **OrgPermissions** (PartitionKey=OrgId, for "org's users" queries)
    7. **Forms** (PartitionKey=OrgId or "GLOBAL", stores form definitions)
    8. **WorkflowExecutions** (PartitionKey=OrgId, stores execution history by org)
    9. **UserExecutions** (PartitionKey=UserId, stores execution history by user)
-   Call `init_tables()` from `function_app.py` startup or create separate `/admin/init-tables` endpoint (for production setup)
-   Log table creation success/failure for debugging
-   Handle both local (Azurite) and production (Azure Storage) connection strings
-   Script should be idempotent (safe to run multiple times)

**Reference Documents**:

-   `specs/001-complete-mvp-for/data-model.md` lines 85-559 - Complete table schemas with partition strategies
-   `specs/001-complete-mvp-for/research.md` - Section on "Table Storage Schema Design"

**Dependencies**: T002, T003, T004
**Test Coverage**: Integration test (run init_tables, verify all 9 tables exist in Azurite)
**Estimated Time**: 1.5 hours

---

### T005b [Setup] - Create seed data script for local development 🆕

**File**: `.specify/scripts/seed-local-data.sh`, `management-api/seed_data.py`
**Description**: Script to populate Azurite with realistic sample data for local development and testing
**Actions**:

-   Create Python script `seed_data.py` that inserts:
    -   **3 sample organizations**: "Acme Corp", "Beta Industries", "Gamma Solutions" with different tenant IDs
    -   **Sample org configs** for Acme Corp: `{"default_office_location": "New York", "halopsa_url": "https://demo.halopsa.com"}`
    -   **Test user**: user_id="test-user-123", email="admin@msp.com", with full permissions to all 3 orgs
    -   **2 sample forms**: "New User Onboarding" (linked to user_onboarding workflow), "License Assignment"
    -   **Sample workflow execution records**: 5 executions with mix of Success/Failed statuses
-   Make script idempotent: check if entity exists (by RowKey) before inserting
-   Run with: `python seed_data.py` from management-api directory
-   Bash wrapper script calls Python script and shows success message
-   Use realistic data that matches quickstart.md examples

**Reference Documents**:

-   `specs/001-complete-mvp-for/data-model.md` - All entity schemas for correct data structure
-   `specs/001-complete-mvp-for/quickstart.md` - Example data formats

**Dependencies**: T005a (tables must exist first)
**Test Coverage**: None (development tooling)
**Estimated Time**: 2 hours

---

## Phase 2: Foundational Infrastructure

**Goal**: Build shared components that ALL user stories depend on (Table Storage, Auth, Pydantic models, Testing)

**Independent Test**: Can create Table Storage entities, validate Azure AD tokens, use Pydantic models for validation, and use pytest fixtures for tests

**Checkpoint**: ✅ TableStorageService working with Azurite, auth middleware validates tokens, all Pydantic models defined, pytest fixtures available

### T006 [Foundation] - Create TableStorageService base class

**File**: `management-api/shared/storage.py`, `workflow-engine/shared/storage.py`
**Description**: Create reusable Table Storage wrapper with org-scoped query helpers
**Actions**:

-   Create `TableStorageService` class using `TableClient` from `azure-data-tables`
-   Constructor accepts table_name and loads connection string from environment
-   Implement methods:
    -   `insert_entity(entity: dict)` → inserts with error handling
    -   `update_entity(entity: dict, mode="merge")` → updates entity
    -   `get_entity(partition_key: str, row_key: str)` → retrieves single entity
    -   `query_entities(filter: str, select: List[str] = None)` → queries with filter
    -   `delete_entity(partition_key: str, row_key: str)` → deletes entity
-   Add helper for org-scoped queries: `query_by_org(org_id: str, row_key_prefix: str = None)` → builds filter string
-   Add helper for dual-indexing: `insert_dual_indexed(entity: dict, table1: str, table2: str, pk1: str, pk2: str)` → writes to 2 tables atomically
-   Handle datetime serialization: use `isoformat()` for storage, `fromisoformat()` for retrieval
-   Add connection string loading from `TABLE_STORAGE_CONNECTION_STRING` environment variable
-   Include error handling and logging

**Reference Documents**:

-   `specs/001-complete-mvp-for/data-model.md` lines 1-83 - Table Storage design principles, partition strategies
-   `specs/001-complete-mvp-for/research.md` - Section "Table Storage Schema Design" - Org-scoped partitioning pattern
-   `specs/001-complete-mvp-for/agent-context.md` - TableStorageService usage patterns

**Dependencies**: T002, T003, T005a
**Test Coverage**: Unit tests for TableStorageService methods (insert, query, update, delete with Azurite)
**Estimated Time**: 2 hours

---

### T007 [Foundation] - Create all Pydantic models for entities

**File**: `management-api/shared/models.py`, `workflow-engine/shared/models.py`
**Description**: Define Pydantic models for all entities (request/response validation)
**Actions**:

-   Create models for Organizations: `Organization`, `CreateOrganizationRequest`, `UpdateOrganizationRequest`
-   Create models for OrgConfig: `OrgConfig`, `SetConfigRequest`
-   Create models for IntegrationConfig: `IntegrationConfig`, `SetIntegrationConfigRequest`
-   Create models for Users: `User`
-   Create models for Permissions: `UserPermission`, `GrantPermissionsRequest`
-   Create models for Forms: `Form`, `FormField`, `FormSchema`, `CreateFormRequest`
-   Create models for Executions: `WorkflowExecution`, `WorkflowExecutionRequest`, `WorkflowExecutionResponse`
-   Create models for Metadata: `WorkflowMetadata`, `WorkflowParameter`, `DataProviderMetadata`, `MetadataResponse`
-   Add validation rules: `Field(min_length=1, max_length=200)`, regex patterns, enums
-   Add type hints for all fields: `name: str`, `isActive: bool`, etc.
-   Use Pydantic v2 syntax if available

**Reference Documents**:

-   `specs/001-complete-mvp-for/data-model.md` lines 85-559 - All entity field definitions and validation rules
-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 36-344 - Schema definitions for all models
-   `specs/001-complete-mvp-for/contracts/workflow-api.yaml` lines 14-149 - Workflow metadata models

**Dependencies**: T002, T003
**Test Coverage**: Contract tests for Pydantic model validation (valid inputs pass, invalid inputs raise ValidationError)
**Estimated Time**: 3 hours

---

### T008 [Foundation] - Implement Azure AD token validation middleware

**File**: `management-api/shared/auth.py`
**Description**: Create middleware decorator for Azure AD JWT token validation
**Actions**:

-   Create `validate_token(token: str)` function:
    -   Use `jwt.decode()` with Azure AD public keys (fetch from `https://login.microsoftonline.com/{tenant}/.well-known/openid-configuration`)
    -   Verify token signature, expiration, audience, issuer
    -   Return decoded token claims
-   Extract user ID from token claims: `user_id = claims.get('oid') or claims.get('sub')`
-   Create `@require_auth` decorator for protecting endpoints:
    -   Extract `Authorization` header: `Bearer {token}`
    -   Call `validate_token(token)`
    -   Inject `user_id` into request context or function parameters
    -   Raise 401 Unauthorized if token invalid/expired
-   Add helper function: `get_org_id_from_header(request)` → extracts `X-Organization-Id` header
-   Cache Azure AD public keys for performance (TTL: 1 hour)

**Reference Documents**:

-   `specs/001-complete-mvp-for/research.md` - Section "Authentication & Authorization Flow" - Token validation pattern
-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 15-24 - Security scheme definition

**Dependencies**: T002
**Test Coverage**: Unit tests for token validation (valid token succeeds, expired token fails, invalid signature fails, missing token fails)
**Estimated Time**: 2 hours

---

### T009 [Foundation] - Implement permission checking middleware

**File**: `management-api/shared/middleware.py`
**Description**: Create permission enforcement decorators that query UserPermissions table
**Actions**:

-   Create `@require_permission(permission_name: str)` decorator:
    -   Assumes `@require_auth` already executed (user_id available)
    -   Extract `org_id` from `X-Organization-Id` header
    -   Query `UserPermissions` table: `partition_key=user_id, row_key=org_id`
    -   Check if permission flag is True: `entity[permission_name] == True`
    -   Raise 403 Forbidden if permission denied or user has no access to org
    -   Raise 400 Bad Request if `X-Organization-Id` header missing
-   Support permission names: `canExecuteWorkflows`, `canManageConfig`, `canManageForms`, `canViewHistory`
-   Log permission checks for audit trail
-   Handle case where UserPermissions entity doesn't exist (user has no org access)

**Reference Documents**:

-   `specs/001-complete-mvp-for/data-model.md` lines 256-283 - UserPermissions table schema
-   `specs/001-complete-mvp-for/research.md` - Section "Authentication & Authorization Flow" - Permission checking pattern

**Dependencies**: T006, T008
**Test Coverage**: Integration tests for permission checks (allowed user succeeds, denied user gets 403, user with no org access gets 403)
**Estimated Time**: 2 hours

---

### T010 [Foundation] - Create Azure Functions blueprint registration system

**File**: `management-api/function_app.py`, `workflow-engine/function_app.py`
**Description**: Set up Azure Functions v2 blueprint pattern for organizing endpoints
**Actions**:

-   Create `function_app.py` with `FunctionApp()` initialization
-   Import blueprint modules from `functions/` directory: `from functions import organizations, permissions, forms, executions, org_config`
-   Register blueprints: `app.register_functions(organizations.bp)`, etc.
-   Configure CORS for local development: `app.route(..., methods=[...], cors=True)`
-   Add global error handling (will be enhanced in T124)
-   Set up logging configuration

**Reference Documents**:

-   `specs/001-complete-mvp-for/research.md` - Section "Azure Functions v2 Programming Model" - Blueprint pattern explanation

**Dependencies**: T002, T003
**Test Coverage**: None (configuration file)
**Estimated Time**: 1 hour

---

### T011 [Foundation] [P] - Create Azure Key Vault client wrapper

**File**: `management-api/shared/secrets.py`, `workflow-engine/shared/secrets.py`
**Description**: Create KeyVaultService for retrieving organization secrets with caching
**Actions**:

-   Create `KeyVaultService` class using `SecretClient` from `azure-keyvault-secrets`
-   Constructor loads Key Vault URL from `KEY_VAULT_URL` environment variable
-   Authenticate using `DefaultAzureCredential` (Managed Identity in Azure, local credentials in development)
-   Implement `get_secret(secret_name: str) -> str`:
    -   Check in-memory cache first (request-scoped, TTL: request duration)
    -   If not cached, fetch from Key Vault: `client.get_secret(secret_name).value`
    -   Cache result before returning
    -   Handle `ResourceNotFoundError` gracefully (return None or raise custom exception)
-   Support secret naming convention: `{org_id}--{secret_name}` (e.g., `acme-corp--msgraph-client-secret`)
-   Add logging for secret access (log secret name, not value)

**Reference Documents**:

-   `specs/001-complete-mvp-for/data-model.md` lines 554-558 - Secret management guidance
-   `specs/001-complete-mvp-for/agent-context.md` - Section "Secret Management" - Key Vault patterns

**Dependencies**: T002, T003
**Test Coverage**: Unit tests for secret retrieval (mocked Key Vault client, test caching behavior)
**Estimated Time**: 1.5 hours

---

### T011a [Foundation] - Create pytest fixtures for testing infrastructure 🆕

**File**: `management-api/tests/conftest.py`, `workflow-engine/tests/conftest.py`
**Description**: Create reusable pytest fixtures to eliminate test code duplication and speed up test development
**Actions**:

-   Create `conftest.py` with the following fixtures:

    **Infrastructure Fixtures**:

    -   `azurite_tables(scope="function")` - Initializes all 9 tables in Azurite, yields, then cleans up (deletes all entities)
    -   `table_service(azurite_tables)` - Returns TableStorageService instance connected to Azurite

    **Entity Fixtures**:

    -   `test_org(table_service)` - Creates test organization "Test Org" with UUID, returns `{"org_id": "...", "name": "...", "tenant_id": "..."}`
    -   `test_org_2(table_service)` - Creates second org for multi-org tests
    -   `test_user(table_service)` - Creates test user "test@example.com", returns `{"user_id": "...", "email": "..."}`
    -   `test_user_2(table_service)` - Creates second user for permission tests

    **Permission Fixtures**:

    -   `test_user_with_full_permissions(test_org, test_user, table_service)` - Grants all 4 permissions to test_user for test_org
    -   `test_user_with_no_permissions(test_org, test_user, table_service)` - Creates user with zero permissions (all flags False)

    **Config Fixtures**:

    -   `test_org_with_config(test_org, table_service)` - Creates org with sample configs: `{"default_location": "NYC", "timeout": "30"}`

    **Workflow Fixtures**:

    -   `mock_context(test_org)` - Returns `OrganizationContext` mock with stubbed methods (get_config, get_secret, get_integration)
    -   `mock_jwt_token(test_user)` - Returns valid JWT token string for testing auth middleware

    **Form Fixtures**:

    -   `test_form(test_org, table_service)` - Creates sample form linked to "user_onboarding" workflow

-   Use `@pytest.fixture(scope="function")` for proper isolation between tests
-   Include cleanup logic: `yield resource; cleanup_tables()`
-   Add helper functions: `insert_entity()`, `clear_table()`, `generate_uuid()`

**Reference Documents**:

-   `specs/001-complete-mvp-for/quickstart.md` lines 1450-1478 - Example of mocking OrganizationContext
-   `specs/001-complete-mvp-for/data-model.md` - Entity schemas for fixture data

**Dependencies**: T006, T007, T005a
**Test Coverage**: None (this IS the testing infrastructure - used by all other tests)
**Estimated Time**: 2.5 hours

---

## Phase 3: User Story 1 - Organization Management (P1)

**User Story**: An MSP administrator needs to manage client organizations and link them to Microsoft 365 tenants via GDAP to enable automated workflows.

**Goal**: Implement CRUD operations for organizations, organization configuration, and integration configuration

**Independent Test**: Can create an organization, link it to a test GDAP tenant, store configuration values, configure integrations, and verify data isolation between organizations.

**Entities**: Organizations, OrgConfig, IntegrationConfig
**Endpoints**: Organizations CRUD, OrgConfig CRUD, IntegrationConfig CRUD

**Checkpoint**: ✅ Organizations CRUD working, config storage functional, integration config working, cross-org data isolation verified

### T012 [US1] - Contract tests for Organizations API

**File**: `management-api/tests/contract/test_organizations_contract.py`
**Description**: Write contract tests for Organizations endpoints (TDD - test first)
**Actions**:

-   Test `CreateOrganizationRequest` validation:
    -   Valid: `{"name": "Test Org", "tenantId": null}` → passes
    -   Invalid: `{"name": "", "tenantId": "invalid-uuid"}` → raises ValidationError
    -   Optional tenantId: `{"name": "Test Org"}` → passes
-   Test `Organization` response model structure (all required fields present)
-   Test `UpdateOrganizationRequest` validation (name, tenantId, isActive)
-   Test error response models (400, 401, 404 structures)

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 70-96 - CreateOrganizationRequest schema
-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 37-68 - Organization schema
-   `specs/001-complete-mvp-for/data-model.md` lines 514-517 - Organization validation rules

**Dependencies**: T007
**Test Coverage**: Pydantic model validation for Organizations
**Estimated Time**: 1 hour

---

### T013 [US1] - Implement GET /api/organizations (list all organizations)

**File**: `management-api/functions/organizations.py`
**Description**: Return all organizations the authenticated user has access to
**Actions**:

-   Create blueprint: `bp = Blueprint()`
-   Add route: `@bp.route(route="organizations", methods=["GET"])`
-   Apply `@require_auth` decorator
-   Get user_id from auth context
-   Query `UserPermissions` table by user_id to get list of accessible org IDs
-   For each org_id, query `Organizations` table (PartitionKey="ORG", RowKey=org_id)
-   Return list of `Organization` models as JSON (200 OK)
-   Handle empty result: return `[]` if user has no org access
-   Log access for audit trail

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 348-367 - GET /api/organizations endpoint spec
-   `specs/001-complete-mvp-for/data-model.md` lines 85-126 - Organizations table schema
-   `specs/001-complete-mvp-for/data-model.md` lines 256-283 - UserPermissions table for access check

**Dependencies**: T006, T008, T009, T010, T011a, T012
**Test Coverage**: Integration test with Azurite (create 2 orgs, create user with access to 1 org, verify only 1 org returned)
**Estimated Time**: 1.5 hours

---

### T014 [US1] - Implement POST /api/organizations (create organization)

**File**: `management-api/functions/organizations.py`
**Description**: Create a new client organization
**Actions**:

-   Add route: `@bp.route(route="organizations", methods=["POST"])` to same blueprint
-   Apply `@require_auth` decorator
-   Parse request body as `CreateOrganizationRequest` (Pydantic auto-validation)
-   Generate new UUID for organization ID: `org_id = str(uuid.uuid4())`
-   Create entity dict:
    ```python
    entity = {
      "PartitionKey": "ORG",
      "RowKey": org_id,
      "Name": request.name,
      "TenantId": request.tenantId,
      "IsActive": True,
      "CreatedAt": datetime.utcnow().isoformat(),
      "CreatedBy": user_id,
      "UpdatedAt": datetime.utcnow().isoformat()
    }
    ```
-   Insert into `Organizations` table using TableStorageService
-   Return created `Organization` model (201 Created)
-   Handle duplicate name (optional validation)

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 369-393 - POST /api/organizations endpoint spec
-   `specs/001-complete-mvp-for/data-model.md` lines 85-126 - Organizations table schema and fields

**Dependencies**: T006, T007, T008, T011a, T012
**Test Coverage**: Integration test (create org, verify in table, test validation errors for empty name)
**Estimated Time**: 1.5 hours

---

### T015 [US1] [P] - Implement GET /api/organizations/{orgId} (get organization details)

**File**: `management-api/functions/organizations.py`
**Description**: Return details for a specific organization
**Actions**:

-   Add route: `@bp.route(route="organizations/{orgId}", methods=["GET"])`
-   Apply `@require_auth` decorator
-   Extract `orgId` from route parameters
-   Check user has permission to access this org: query `UserPermissions` table (PartitionKey=user_id, RowKey=orgId)
-   If no permission entity found, return 403 Forbidden
-   Query `Organizations` table (PartitionKey="ORG", RowKey=orgId)
-   If not found, return 404 Not Found
-   Return `Organization` model (200 OK)

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 395-417 - GET /api/organizations/{orgId} endpoint spec
-   `specs/001-complete-mvp-for/data-model.md` lines 105-112 - Organizations query patterns

**Dependencies**: T006, T008, T009, T011a, T012
**Test Coverage**: Integration test (get existing org succeeds, get non-existent org returns 404, unauthorized user gets 403)
**Estimated Time**: 1 hour

---

### T016 [US1] [P] - Implement PATCH /api/organizations/{orgId} (update organization)

**File**: `management-api/functions/organizations.py`
**Description**: Update organization name, tenantId, or isActive status
**Actions**:

-   Add route: `@bp.route(route="organizations/{orgId}", methods=["PATCH"])`
-   Apply `@require_auth` and `@require_permission("canManageConfig")` decorators
-   Parse request body as `UpdateOrganizationRequest`
-   Get existing organization entity from table
-   Update only provided fields (name, tenantId, isActive)
-   Set `UpdatedAt` to current timestamp
-   Use TableStorageService.update_entity() with mode="merge"
-   Return updated `Organization` model (200 OK)

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 419-438 - PATCH /api/organizations/{orgId} endpoint spec
-   `specs/001-complete-mvp-for/data-model.md` lines 85-126 - Organizations table schema

**Dependencies**: T006, T007, T008, T009, T011a, T012
**Test Coverage**: Integration test (update org name, verify change persisted, test permission denial)
**Estimated Time**: 1.5 hours

---

### T017 [US1] [P] - Implement DELETE /api/organizations/{orgId} (soft delete)

**File**: `management-api/functions/organizations.py`
**Description**: Soft delete organization by setting isActive=False
**Actions**:

-   Add route: `@bp.route(route="organizations/{orgId}", methods=["DELETE"])`
-   Apply `@require_auth` and `@require_permission("canManageConfig")` decorators
-   Get existing organization entity
-   Set `IsActive=False` and `UpdatedAt=datetime.utcnow().isoformat()`
-   Update entity in table (do NOT actually delete row - soft delete only)
-   Return 204 No Content
-   Optionally: check if org has active forms/executions and warn user

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 440-449 - DELETE /api/organizations/{orgId} endpoint spec

**Dependencies**: T006, T008, T009, T011a, T012
**Test Coverage**: Integration test (delete org, verify IsActive=False, verify org still queryable but marked inactive)
**Estimated Time**: 1 hour

---

### T018 [US1] - Contract tests for OrgConfig API

**File**: `management-api/tests/contract/test_org_config_contract.py`
**Description**: Write contract tests for OrgConfig endpoints (TDD)
**Actions**:

-   Test `SetConfigRequest` validation:
    -   Valid: `{"key": "timeout", "value": "30", "type": "int"}` → passes
    -   Invalid type enum: `{"key": "foo", "value": "bar", "type": "invalid"}` → raises ValidationError
    -   Required fields: all 3 fields must be present
-   Test `OrgConfig` response model structure
-   Test type enum values: "string", "int", "bool", "json", "secret_ref"

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 120-135 - SetConfigRequest schema
-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 98-118 - OrgConfig schema
-   `specs/001-complete-mvp-for/data-model.md` lines 130-168 - OrgConfig table schema

**Dependencies**: T007
**Test Coverage**: Pydantic model validation for OrgConfig
**Estimated Time**: 45 minutes

---

### T019 [US1] - Implement GET /api/organizations/{orgId}/config (get all config)

**File**: `management-api/functions/org_config.py`
**Description**: Return all configuration key-value pairs for an organization
**Actions**:

-   Create new blueprint: `bp = Blueprint()` for org config endpoints
-   Add route: `@bp.route(route="organizations/{orgId}/config", methods=["GET"])`
-   Apply `@require_auth`, `@require_permission("canViewHistory")` decorators
-   Extract `orgId` from route
-   Validate `X-Organization-Id` header matches orgId (security check)
-   Query `OrgConfig` table: `PartitionKey=orgId, RowKey starts with "config:"`
-   Filter query: `"PartitionKey eq '{org_id}' and RowKey ge 'config:' and RowKey lt 'config;'"`
-   Return list of `OrgConfig` models (200 OK)
-   Handle empty config: return `[]`

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 452-478 - GET /api/organizations/{orgId}/config endpoint spec
-   `specs/001-complete-mvp-for/data-model.md` lines 146-155 - OrgConfig query patterns

**Dependencies**: T006, T008, T009, T010, T011a, T018
**Test Coverage**: Integration test (get config for org with 3 values, get config for org with no config)
**Estimated Time**: 1.5 hours

---

### T020 [US1] - Implement POST /api/organizations/{orgId}/config (set config value)

**File**: `management-api/functions/org_config.py`
**Description**: Create or update a configuration key-value pair
**Actions**:

-   Add route: `@bp.route(route="organizations/{orgId}/config", methods=["POST"])`
-   Apply `@require_auth`, `@require_permission("canManageConfig")` decorators
-   Parse request body as `SetConfigRequest`
-   Create RowKey: `f"config:{request.key}"`
-   Create entity:
    ```python
    entity = {
      "PartitionKey": org_id,
      "RowKey": f"config:{request.key}",
      "Value": request.value,
      "Type": request.type,
      "Description": request.description,
      "UpdatedAt": datetime.utcnow().isoformat(),
      "UpdatedBy": user_id
    }
    ```
-   Use `table_service.update_entity(entity, mode="replace")` to insert or update
-   Return `OrgConfig` model (201 Created for new, 200 OK for update)
-   Validate `type` matches value format (e.g., type="int" should have numeric value)

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 480-500 - POST /api/organizations/{orgId}/config endpoint spec
-   `specs/001-complete-mvp-for/data-model.md` lines 130-168 - OrgConfig schema and type validation

**Dependencies**: T006, T007, T008, T009, T011a, T018
**Test Coverage**: Integration test (set new config, update existing config, verify type validation)
**Estimated Time**: 1.5 hours

---

### T021 [US1] [P] - Implement DELETE /api/organizations/{orgId}/config/{key}

**File**: `management-api/functions/org_config.py`
**Description**: Delete a configuration value
**Actions**:

-   Add route: `@bp.route(route="organizations/{orgId}/config/{key}", methods=["DELETE"])`
-   Apply `@require_auth`, `@require_permission("canManageConfig")` decorators
-   Extract `orgId` and `key` from route
-   Create RowKey: `f"config:{key}"`
-   Delete entity from `OrgConfig` table: `table_service.delete_entity(org_id, row_key)`
-   Return 204 No Content (idempotent - success even if key didn't exist)

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 502-526 - DELETE /api/organizations/{orgId}/config/{key} endpoint spec

**Dependencies**: T006, T008, T009, T011a, T018
**Test Coverage**: Integration test (delete existing key succeeds, delete non-existent key also returns 204)
**Estimated Time**: 1 hour

---

### T021a [US1] - Contract tests for IntegrationConfig API 🆕

**File**: `management-api/tests/contract/test_integration_config_contract.py`
**Description**: Write contract tests for IntegrationConfig endpoints (TDD)
**Actions**:

-   Test `SetIntegrationConfigRequest` validation:
    -   Valid: `{"type": "msgraph", "enabled": True, "settings": "{...}"}` → passes
    -   Invalid type: `{"type": "unknown", ...}` → raises ValidationError
    -   Settings must be valid JSON string
-   Test `IntegrationConfig` response model structure
-   Test integration type enum: "msgraph", "halopsa" (from data-model.md)

**Reference Documents**:

-   `specs/001-complete-mvp-for/data-model.md` lines 172-212 - IntegrationConfig table schema
-   `specs/001-complete-mvp-for/data-model.md` lines 187-189 - Supported integration types

**Dependencies**: T007
**Test Coverage**: Pydantic model validation for IntegrationConfig
**Estimated Time**: 45 minutes

---

### T021b [US1] - Implement GET /api/organizations/{orgId}/integrations 🆕

**File**: `management-api/functions/org_config.py` (extend existing blueprint)
**Description**: Return all integration configurations for an organization
**Actions**:

-   Add route to org_config blueprint: `@bp.route(route="organizations/{orgId}/integrations", methods=["GET"])`
-   Apply `@require_auth`, `@require_permission("canManageConfig")` decorators
-   Query `IntegrationConfig` table: `PartitionKey=orgId, RowKey starts with "integration:"`
-   Filter: `"PartitionKey eq '{org_id}' and RowKey ge 'integration:' and RowKey lt 'integration;'"`
-   Parse `Settings` JSON string into object before returning
-   Return list of `IntegrationConfig` models (200 OK)
-   Mask sensitive values in Settings (e.g., replace client_secret_ref with "\*\*\*")

**Reference Documents**:

-   `specs/001-complete-mvp-for/data-model.md` lines 172-212 - IntegrationConfig table schema
-   `specs/001-complete-mvp-for/data-model.md` lines 191-200 - IntegrationConfig query patterns

**Dependencies**: T006, T008, T009, T011a, T021a
**Test Coverage**: Integration test (get integrations for org with msgraph and halopsa configured)
**Estimated Time**: 1.5 hours

---

### T021c [US1] - Implement POST /api/organizations/{orgId}/integrations 🆕

**File**: `management-api/functions/org_config.py` (extend)
**Description**: Create or update an integration configuration (with Key Vault secret references)
**Actions**:

-   Add route: `@bp.route(route="organizations/{orgId}/integrations", methods=["POST"])`
-   Apply `@require_auth`, `@require_permission("canManageConfig")` decorators
-   Parse `SetIntegrationConfigRequest` from body
-   Validate `type` is one of: "msgraph", "halopsa"
-   Validate `settings` JSON structure based on type:
    -   msgraph: requires `tenant_id`, `client_id`, `client_secret_ref` (Key Vault secret name)
    -   halopsa: requires `api_url`, `client_id`, `api_key_ref` (Key Vault secret name)
-   Create RowKey: `f"integration:{request.type}"`
-   **IMPORTANT**: Settings should contain Key Vault secret REFERENCES, NOT actual secrets:
    ```json
    {
        "tenant_id": "...",
        "client_id": "...",
        "client_secret_ref": "org-123--msgraph-secret" // Key Vault secret name
    }
    ```
-   Insert/update entity in `IntegrationConfig` table
-   Return `IntegrationConfig` model (201 Created)

**Reference Documents**:

-   `specs/001-complete-mvp-for/data-model.md` lines 172-212 - IntegrationConfig schema
-   `specs/001-complete-mvp-for/data-model.md` lines 187-189 - Integration types and required settings
-   `specs/001-complete-mvp-for/agent-context.md` - Section "Secret Management" - Key Vault naming convention

**Dependencies**: T006, T007, T008, T009, T011, T011a, T021a
**Test Coverage**: Integration test (set msgraph integration, set halopsa integration, test validation errors)
**Estimated Time**: 2 hours

---

### T021d [US1] - Implement DELETE /api/organizations/{orgId}/integrations/{type} 🆕

**File**: `management-api/functions/org_config.py` (extend)
**Description**: Delete an integration configuration
**Actions**:

-   Add route: `@bp.route(route="organizations/{orgId}/integrations/{type}", methods=["DELETE"])`
-   Apply `@require_auth`, `@require_permission("canManageConfig")` decorators
-   Extract `orgId` and `type` from route
-   Create RowKey: `f"integration:{type}"`
-   Delete entity from `IntegrationConfig` table
-   Return 204 No Content (idempotent)
-   Note: This only deletes the config reference, NOT the Key Vault secrets (secrets persist)

**Reference Documents**:

-   `specs/001-complete-mvp-for/data-model.md` lines 172-212 - IntegrationConfig table

**Dependencies**: T006, T008, T009, T011a, T021a
**Test Coverage**: Integration test (delete integration config, verify removed from table)
**Estimated Time**: 1 hour

---

### T022 [US1] - Client: Create Organization TypeScript types

**File**: `client/src/types/organization.ts`
**Description**: Define TypeScript interfaces matching API models
**Actions**:

-   Create `Organization`, `CreateOrganizationRequest`, `UpdateOrganizationRequest` interfaces
-   Create `OrgConfig`, `SetConfigRequest` interfaces
-   Create `IntegrationConfig`, `SetIntegrationConfigRequest` interfaces
-   Export all types

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 37-135 - All Organization/Config schemas

**Dependencies**: T001, T007
**Test Coverage**: None (type definitions)
**Estimated Time**: 30 minutes

---

### T023 [US1] - Client: Create Organization API service

**File**: `client/src/services/apiClient.ts`
**Description**: Create API wrapper for Organizations endpoints
**Actions**:

-   Set up Axios instance with base URL from environment variables
-   Add request interceptor to include Azure AD token from MSAL
-   Implement methods: `getOrganizations()`, `getOrganization(id)`, `createOrganization(data)`, `updateOrganization(id, data)`, `deleteOrganization(id)`
-   Implement methods: `getOrgConfig(orgId)`, `setOrgConfig(orgId, data)`, `deleteOrgConfig(orgId, key)`
-   Implement methods: `getIntegrations(orgId)`, `setIntegration(orgId, data)`, `deleteIntegration(orgId, type)`
-   Handle errors and return typed responses

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/management-api.yaml` - All Organizations/Config API endpoints
-   `specs/001-complete-mvp-for/quickstart.md` - API client examples

**Dependencies**: T001, T022
**Test Coverage**: None (or MSW mock tests)
**Estimated Time**: 2 hours

---

### T024 [US1] - Client: Create useOrganizations custom hook

**File**: `client/src/hooks/useOrganizations.ts`
**Description**: React hook for organization state management
**Actions**:

-   Create `useOrganizations()` hook using `useState` and `useEffect`
-   Fetch organizations on mount
-   Provide methods: `createOrg(data)`, `updateOrg(id, data)`, `deleteOrg(id)`
-   Handle loading and error states
-   Return `{ organizations, loading, error, createOrg, updateOrg, deleteOrg }`

**Dependencies**: T001, T023
**Test Coverage**: None (or React Testing Library tests)
**Estimated Time**: 1.5 hours

---

### T025 [US1] - Client: Build OrganizationsPage UI component

**File**: `client/src/pages/OrganizationsPage.tsx`
**Description**: Page component for listing and managing organizations
**Actions**:

-   Use `useOrganizations()` hook
-   Display table/list of organizations with name, tenant ID, status
-   Add "Create Organization" button → opens modal/form
-   Add edit/delete actions per row
-   Handle loading and error states
-   Show success/error toasts for operations

**Dependencies**: T001, T024
**Test Coverage**: None (or React Testing Library component tests)
**Estimated Time**: 3 hours

---

### T026 [US1] - Client: Build OrganizationConfigPage UI component

**File**: `client/src/pages/OrganizationConfigPage.tsx`
**Description**: Page for managing organization configuration key-value pairs and integrations
**Actions**:

-   Accept `orgId` from route parameters
-   Display table of config key-value pairs with type
-   Add "Add Configuration" button → opens form
-   Add edit/delete actions per config row
-   Support config types: string, int, bool, json, secret_ref
-   Show descriptions and last updated info
-   Add section for integration configurations (msgraph, halopsa)
-   Display integration status and last updated timestamp

**Reference Documents**:

-   `specs/001-complete-mvp-for/data-model.md` lines 130-212 - OrgConfig and IntegrationConfig schemas

**Dependencies**: T001, T023
**Test Coverage**: None
**Estimated Time**: 3 hours

---

## Phase 4: User Story 2 - User Authentication & Permissions (P1)

**User Story**: MSP technicians need to log in with their Microsoft 365 accounts and have granular permissions to access specific client organizations.

**Goal**: Implement Azure AD authentication and org-scoped permission management

**Independent Test**: Can create users with different permission sets, attempt to access various organizations, and verify permission enforcement at API level.

**Entities**: Users, UserPermissions, OrgPermissions (dual-indexed)
**Endpoints**: `GET /api/permissions/users/{userId}`, `GET /api/permissions/organizations/{orgId}`, `POST /api/permissions`, `DELETE /api/permissions`

**Checkpoint**: ✅ Azure AD login working, permission CRUD functional, API endpoints enforce permissions

### T027 [US2] - Contract tests for Permissions API

**File**: `management-api/tests/contract/test_permissions_contract.py`
**Description**: Write contract tests for Permissions endpoints (TDD)
**Actions**:

-   Test `GrantPermissionsRequest` validation (userId, orgId, permissions object)
-   Test `UserPermission` response model
-   Test error responses for invalid permission structures

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 137-173 - Permission schemas
-   `specs/001-complete-mvp-for/data-model.md` lines 256-312 - UserPermissions/OrgPermissions schemas

**Dependencies**: T007
**Test Coverage**: Pydantic model validation for permissions
**Estimated Time**: 1 hour

---

### T027a [US2] - Implement user auto-creation on first login 🆕

**File**: `management-api/shared/auth.py` (extend)
**Description**: Automatically create user record in Users table on first Azure AD login
**Actions**:

-   Extend `@require_auth` decorator to check if user exists in Users table
-   Extract user info from token claims: `oid` (user_id), `preferred_username` (email), `name` (display name)
-   Query Users table: `PartitionKey="USER", RowKey=user_id`
-   If user doesn't exist:
    -   Create entity:
        ```python
        entity = {
          "PartitionKey": "USER",
          "RowKey": user_id,
          "Email": claims.get("preferred_username"),
          "DisplayName": claims.get("name"),
          "CreatedAt": datetime.utcnow().isoformat(),
          "LastLoginAt": datetime.utcnow().isoformat()
        }
        ```
    -   Insert into Users table
-   If user exists: update `LastLoginAt` timestamp
-   Continue with normal auth flow

**Reference Documents**:

-   `specs/001-complete-mvp-for/data-model.md` lines 216-254 - Users table schema
-   `specs/001-complete-mvp-for/research.md` - Section "Authentication & Authorization Flow"

**Dependencies**: T006, T008, T011a
**Test Coverage**: Integration test (first login creates user, second login updates LastLoginAt)
**Estimated Time**: 1.5 hours

---

### T027b [US2] - Implement GET /api/users (list all users) 🆕

**File**: `management-api/functions/permissions.py` (extend)
**Description**: Return all MSP technician users for user management UI
**Actions**:

-   Add route: `@bp.route(route="users", methods=["GET"])`
-   Apply `@require_auth` decorator (may add admin-only check later)
-   Query Users table: `PartitionKey="USER"`
-   Return list of `User` models with email, displayName, createdAt, lastLoginAt
-   Sort by lastLoginAt descending (most recent first)
-   Do NOT expose sensitive fields

**Reference Documents**:

-   `specs/001-complete-mvp-for/data-model.md` lines 216-254 - Users table schema

**Dependencies**: T006, T008, T011a, T027a
**Test Coverage**: Integration test (create 3 users, list all, verify sorting)
**Estimated Time**: 1 hour

---

### T028 [US2] - Implement GET /api/permissions/users/{userId}

**File**: `management-api/functions/permissions.py`
**Description**: Get all organizations a user can access and their permissions
**Actions**:

-   Create blueprint for permissions endpoints
-   Add `@bp.route(route="permissions/users/{userId}", methods=["GET"])`
-   Apply `@require_auth` decorator
-   Ensure requesting user can only query their own permissions (or is admin)
-   Query `UserPermissions` table (PartitionKey=userId)
-   Return list of `UserPermission` models

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 529-555 - GET /api/permissions/users/{userId} endpoint
-   `specs/001-complete-mvp-for/data-model.md` lines 256-283 - UserPermissions table schema

**Dependencies**: T006, T008, T010, T011a, T027
**Test Coverage**: Integration test (get permissions for user with multiple orgs, user with no orgs)
**Estimated Time**: 1.5 hours

---

### T029 [US2] - Implement GET /api/permissions/organizations/{orgId}

**File**: `management-api/functions/permissions.py`
**Description**: Get all users who have access to an organization
**Actions**:

-   Add `@bp.route(route="permissions/organizations/{orgId}", methods=["GET"])`
-   Apply `@require_auth`, `@require_permission("canManageConfig")` decorators
-   Query `OrgPermissions` table (PartitionKey=orgId)
-   Return list of `UserPermission` models

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 557-583 - GET /api/permissions/organizations/{orgId} endpoint
-   `specs/001-complete-mvp-for/data-model.md` lines 285-312 - OrgPermissions table schema

**Dependencies**: T006, T008, T009, T011a, T027
**Test Coverage**: Integration test (get users for org, org with no users)
**Estimated Time**: 1.5 hours

---

### T030 [US2] - Implement POST /api/permissions (grant permissions)

**File**: `management-api/functions/permissions.py`
**Description**: Grant a user permissions to access an organization
**Actions**:

-   Add `@bp.route(route="permissions", methods=["POST"])`
-   Apply `@require_auth`, `@require_permission("canManageConfig")` decorators
-   Parse and validate `GrantPermissionsRequest`
-   Create permission entity with all 4 permission flags
-   Perform DUAL INSERT (atomic if possible):
    -   Insert into `UserPermissions` (PartitionKey=userId, RowKey=orgId)
    -   Insert into `OrgPermissions` (PartitionKey=orgId, RowKey=userId)
-   Set `GrantedBy` and `GrantedAt` fields
-   Return created `UserPermission` model (201 Created)

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 585-605 - POST /api/permissions endpoint
-   `specs/001-complete-mvp-for/data-model.md` lines 256-312 - Dual-indexing pattern

**Dependencies**: T006, T007, T008, T009, T011a, T027
**Test Coverage**: Integration test (grant permissions, verify in both tables, test overwrite)
**Estimated Time**: 2 hours

---

### T031 [US2] - Implement DELETE /api/permissions (revoke permissions)

**File**: `management-api/functions/permissions.py`
**Description**: Revoke a user's access to an organization
**Actions**:

-   Add `@bp.route(route="permissions", methods=["DELETE"])`
-   Apply `@require_auth`, `@require_permission("canManageConfig")` decorators
-   Extract `userId` and `orgId` from query parameters
-   Perform DUAL DELETE:
    -   Delete from `UserPermissions` (PartitionKey=userId, RowKey=orgId)
    -   Delete from `OrgPermissions` (PartitionKey=orgId, RowKey=userId)
-   Return 204 No Content (idempotent)

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 607-631 - DELETE /api/permissions endpoint

**Dependencies**: T006, T008, T009, T011a, T027
**Test Coverage**: Integration test (revoke permissions, verify deletion from both tables)
**Estimated Time**: 1.5 hours

---

### T032 [US2] - Client: Set up MSAL authentication provider

**File**: `client/src/services/authService.ts`
**Description**: Configure Azure AD authentication with @azure/msal-react
**Actions**:

-   Install `@azure/msal-browser` and `@azure/msal-react`
-   Create `PublicClientApplication` with Azure AD config from environment variables
-   Export `MsalProvider` wrapper
-   Create `useAuth()` hook for login/logout/token access
-   Configure scopes for backend APIs

**Reference Documents**:

-   `specs/001-complete-mvp-for/research.md` - Section "Authentication & Authorization Flow"
-   `specs/001-complete-mvp-for/quickstart.md` - MSAL configuration examples

**Dependencies**: T001
**Test Coverage**: None (authentication library)
**Estimated Time**: 2 hours

---

### T033 [US2] - Client: Add authentication wrapper to App component

**File**: `client/src/App.tsx`
**Description**: Wrap app with MSAL provider and handle auth state
**Actions**:

-   Import and wrap app with `<MsalProvider>`
-   Add `AuthenticatedTemplate` and `UnauthenticatedTemplate` components
-   Show login button for unauthenticated users
-   Show app content for authenticated users
-   Add token refresh logic
-   Handle auth errors

**Dependencies**: T001, T032
**Test Coverage**: None
**Estimated Time**: 1.5 hours

---

### T034 [US2] - Client: Create Permission TypeScript types

**File**: `client/src/types/permission.ts`
**Description**: Define TypeScript interfaces for permissions
**Actions**:

-   Create `UserPermission`, `GrantPermissionsRequest` interfaces
-   Create `PermissionFlags` type with all 4 permission fields
-   Create `User` interface

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 137-173 - Permission schemas

**Dependencies**: T001, T007
**Test Coverage**: None (type definitions)
**Estimated Time**: 15 minutes

---

### T035 [US2] - Client: Create Permissions API service

**File**: `client/src/services/apiClient.ts` (extend existing)
**Description**: Add API wrapper methods for Permissions endpoints
**Actions**:

-   Add methods: `getUserPermissions(userId)`, `getOrgPermissions(orgId)`, `grantPermissions(data)`, `revokePermissions(userId, orgId)`
-   Add method: `getUsers()` for user management
-   Include `X-Organization-Id` header where required

**Dependencies**: T023, T034
**Test Coverage**: None
**Estimated Time**: 1 hour

---

### T036 [US2] - Client: Build PermissionsPage UI component

**File**: `client/src/pages/PermissionsPage.tsx`
**Description**: Page for managing user permissions for organizations
**Actions**:

-   Display table of users and their permissions per organization
-   Add "Grant Permissions" button → opens form (select user, select org, checkboxes for 4 permissions)
-   Add revoke action per user-org pair
-   Filter by organization
-   Show permission flags as checkboxes (read-only or editable)

**Dependencies**: T001, T035
**Test Coverage**: None
**Estimated Time**: 3 hours

---

## Phase 5: User Story 3 - Workflow Development & Registration (P1)

**User Story**: A developer needs to write Python workflows using decorators that automatically register with the platform and expose metadata for form generation.

**Goal**: Implement decorator pattern for workflows with auto-discovery and metadata registration

**Independent Test**: Can create a simple Python workflow with `@workflow` decorator, start workflow engine, and verify workflow appears in metadata endpoint with correct parameter definitions.

**Entities**: Workflow (metadata only - not persisted)
**Endpoints**: `GET /admin/metadata`

**Checkpoint**: ✅ Workflow decorators working, auto-discovery functional, metadata endpoint returns workflow definitions

### T037 [US3] - Create @workflow decorator

**File**: `workflow-engine/shared/decorators.py`
**Description**: Implement decorator for registering workflow functions
**Actions**:

-   Create `@workflow(name, description, category, tags=[])` decorator
-   Store workflow metadata in global registry (singleton)
-   Extract function signature and parameter types
-   Support `requires_org=True` flag (default)
-   Return decorated function unchanged (for normal Python execution)

**Reference Documents**:

-   `specs/001-complete-mvp-for/quickstart.md` lines 239-312 - Workflow decorator examples
-   `specs/001-complete-mvp-for/research.md` - Section "Workflow Registration Pattern"

**Dependencies**: T003
**Test Coverage**: Unit tests for decorator (register workflow, extract metadata, verify callable)
**Estimated Time**: 2 hours

---

### T038 [US3] - Create @param decorator

**File**: `workflow-engine/shared/decorators.py`
**Description**: Implement decorator for defining workflow parameters with metadata
**Actions**:

-   Create `@param(name, type, label=None, required=False, validation=None, data_provider=None, default_value=None, help_text=None)` decorator
-   Store parameter metadata in workflow registry
-   Support chaining multiple `@param` decorators
-   Validate parameter types: string, int, bool, float, json, list

**Reference Documents**:

-   `specs/001-complete-mvp-for/quickstart.md` lines 313-400 - Parameter decorator examples
-   `specs/001-complete-mvp-for/contracts/workflow-api.yaml` lines 85-149 - WorkflowParameter schema

**Dependencies**: T037
**Test Coverage**: Unit tests for parameter decorator (single param, multiple params, validation rules)
**Estimated Time**: 1.5 hours

---

### T039 [US3] - Create workflow metadata registry

**File**: `workflow-engine/shared/registry.py`
**Description**: Singleton registry for storing workflow and data provider metadata
**Actions**:

-   Create `WorkflowRegistry` class (singleton pattern)
-   Implement methods: `register_workflow(metadata)`, `get_workflow(name)`, `get_all_workflows()`
-   Implement methods: `register_data_provider(metadata)`, `get_data_provider(name)`, `get_all_data_providers()`
-   Store metadata in memory (dict)
-   Thread-safe access (use threading.Lock if needed)

**Reference Documents**:

-   `specs/001-complete-mvp-for/research.md` - Section "Workflow Registration Pattern"

**Dependencies**: T003
**Test Coverage**: Unit tests for registry (register, retrieve, list all)
**Estimated Time**: 1.5 hours

---

### T040 [US3] - Implement workflow auto-discovery system

**File**: `workflow-engine/workflows/__init__.py`
**Description**: Auto-import all workflow modules to trigger decorator registration
**Actions**:

-   Use `importlib` to dynamically import all `.py` files in `workflows/` directory
-   Skip `__init__.py` and private files (starting with `_`)
-   Import happens on module load (when workflow engine starts)
-   Log discovered workflows to console

**Reference Documents**:

-   `specs/001-complete-mvp-for/quickstart.md` lines 401-450 - Auto-discovery explanation

**Dependencies**: T037, T038, T039
**Test Coverage**: Integration test (create dummy workflow file, verify auto-discovery)
**Estimated Time**: 1 hour

---

### T041 [US3] - Implement GET /admin/metadata endpoint

**File**: `workflow-engine/admin/metadata.py`
**Description**: Return metadata for all registered workflows and data providers
**Actions**:

-   Create blueprint for admin endpoints
-   Add `@bp.route(route="admin/metadata", methods=["GET"])`
-   NO authentication required (public metadata endpoint)
-   Query `WorkflowRegistry` to get all workflows
-   Query `WorkflowRegistry` to get all data providers
-   Return `MetadataResponse` model (workflows + dataProviders arrays)

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/workflow-api.yaml` lines 14-149 - Metadata endpoint spec

**Dependencies**: T010, T039, T040
**Test Coverage**: Integration test (start workflow engine, call metadata endpoint, verify structure)
**Estimated Time**: 1.5 hours

---

### T042 [US3] - Create example workflow: user_onboarding

**File**: `workflow-engine/workflows/user_onboarding.py`
**Description**: Create example workflow for testing and documentation
**Actions**:

-   Create `user_onboarding()` function with `@workflow` decorator
-   Add `@param` decorators for: first_name, last_name, email, license
-   Implement mock business logic (print or return test data)
-   Add docstring explaining workflow purpose
-   Accept `OrganizationContext` as first parameter

**Reference Documents**:

-   `specs/001-complete-mvp-for/quickstart.md` lines 239-400 - Complete workflow example

**Dependencies**: T037, T038
**Test Coverage**: Integration test (execute workflow with mock context, verify output)
**Estimated Time**: 1 hour

---

### T043 [US3] - Create OrganizationContext class

**File**: `workflow-engine/shared/context.py`
**Description**: Context object injected into all workflows
**Actions**:

-   Create `OrganizationContext` class with fields: `org_id`, `org_name`, `tenant_id`
-   Add method: `get_config(key)` → queries `OrgConfig` table
-   Add method: `get_secret(key)` → queries Key Vault via `KeyVaultService`
-   Add method: `get_integration(name)` → returns pre-authenticated integration client
-   Add method: `log(level, message, data=None)` → writes to execution log
-   Cache config and secrets for request duration

**Reference Documents**:

-   `specs/001-complete-mvp-for/quickstart.md` lines 1450-1478 - OrganizationContext usage examples
-   `specs/001-complete-mvp-for/research.md` - Section "Organization Context Pattern"

**Dependencies**: T003, T006, T011
**Test Coverage**: Unit tests for context methods (get_config, get_secret with mocks)
**Estimated Time**: 2.5 hours

---

### T044 [US3] - Contract tests for Metadata API

**File**: `workflow-engine/tests/contract/test_metadata_contract.py`
**Description**: Write contract tests for metadata endpoint (TDD)
**Actions**:

-   Test `MetadataResponse` model structure
-   Test `WorkflowMetadata` model (name, description, parameters)
-   Test `WorkflowParameter` model (name, type, required, dataProvider)
-   Test `DataProviderMetadata` model

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/workflow-api.yaml` lines 14-149 - All metadata schemas

**Dependencies**: T007
**Test Coverage**: Pydantic model validation for metadata responses
**Estimated Time**: 1 hour

---

### T045 [US3] - Integration test for workflow registration and execution

**File**: `workflow-engine/tests/integration/test_workflow_execution.py`
**Description**: End-to-end test of workflow registration and execution
**Actions**:

-   Create test workflow with `@workflow` and `@param` decorators
-   Verify workflow appears in registry
-   Execute workflow with mock `OrganizationContext`
-   Verify workflow receives correct parameters
-   Verify workflow can access context methods
-   Test workflow with `requires_org=False`

**Dependencies**: T037, T038, T039, T040, T042, T043
**Test Coverage**: Integration test for full workflow lifecycle
**Estimated Time**: 2 hours

---

## Phase 6: User Story 7 - Workflow Execution with Organization Context (P1) ✅ COMPLETE

**User Story**: Workflows need to automatically receive organization context including config, secrets, and pre-authenticated integration clients when executed.

**Goal**: Implement workflow execution endpoint with automatic context loading

**Independent Test**: Can execute a workflow that accesses organization config, retrieves a secret, and uses an integration client, verifying all context is correctly loaded.

**Entities**: WorkflowExecutions, UserExecutions (dual-indexed)
**Endpoints**: `POST /workflows/{workflowName}`

**Checkpoint**: ✅ Workflows can be executed via HTTP, context is automatically loaded, executions are logged to Table Storage

**Completion Date**: 2025-10-10
**Tests Added**: 18 tests (13 contract + 5 integration)
**Files Created**: 7 new files (middleware, context, error_handling, execution_logger, execute.py, etc.)

### T046 [US7] - Create context loading middleware ✅

**File**: `workflows/shared/middleware.py` (164 lines)
**Description**: Decorator for loading OrganizationContext from request headers
**Status**: ✅ Complete
**Actions**:

-   Create `@with_org_context` decorator
-   Extract `X-Organization-Id` header from request
-   Query `Organizations` table to get org details
-   Query `OrgConfig` table to load all config (PartitionKey=org_id)
-   Create `OrganizationContext` object with org details and config
-   Inject context into route handler function
-   Handle missing header or invalid org ID (400 Bad Request)

**Reference Documents**:

-   `specs/001-complete-mvp-for/research.md` - Section "Organization Context Pattern"

**Dependencies**: T006, T043
**Test Coverage**: Unit tests for context loading (valid org, invalid org, missing header)
**Estimated Time**: 2 hours

---

### T047 [US7] - Create base integration client class

**File**: `workflow-engine/shared/integrations/base.py`
**Description**: Base class for all integration clients
**Actions**:

-   Create `BaseIntegration` abstract class
-   Accept `OrganizationContext` in constructor
-   Define abstract method: `authenticate()` → returns access token
-   Add helper method: `_get_secret(key)` → calls `context.get_secret(key)`
-   Add helper method: `_get_config(key)` → calls `context.get_config(key)`

**Reference Documents**:

-   `specs/001-complete-mvp-for/quickstart.md` lines 1325-1400 - Integration client patterns

**Dependencies**: T003, T043
**Test Coverage**: None (abstract class)
**Estimated Time**: 45 minutes

---

### T048 [US7] [P] - Create Microsoft Graph integration client

**File**: `workflow-engine/shared/integrations/msgraph.py`
**Description**: Pre-authenticated Microsoft Graph API client
**Actions**:

-   Extend `BaseIntegration`
-   Implement `authenticate()` using MSAL with client credentials flow
-   Retrieve credentials from config/secrets: `msgraph_client_id`, `msgraph_client_secret`, `tenant_id`
-   Create HTTP client wrapper for Graph API calls
-   Add common methods: `get_users()`, `create_user()`, `assign_license()`, `get_subscribed_skus()`
-   Cache access token in context for request duration

**Reference Documents**:

-   `specs/001-complete-mvp-for/quickstart.md` lines 1480-1600 - Microsoft Graph integration examples
-   `specs/001-complete-mvp-for/data-model.md` lines 187-189 - Integration configuration structure

**Dependencies**: T043, T047
**Test Coverage**: Unit tests with mocked Graph API responses
**Estimated Time**: 3 hours

---

### T049 [US7] [P] - Create HaloPSA integration client

**File**: `workflow-engine/shared/integrations/halopsa.py`
**Description**: Pre-authenticated HaloPSA API client
**Actions**:

-   Extend `BaseIntegration`
-   Implement `authenticate()` using HaloPSA OAuth2 flow
-   Retrieve credentials from config/secrets: `halopsa_client_id`, `halopsa_client_secret`, `halopsa_api_url`
-   Create HTTP client wrapper for HaloPSA API calls
-   Add common methods: `get_tickets()`, `create_ticket()`, `update_ticket()`
-   Cache access token

**Reference Documents**:

-   `specs/001-complete-mvp-for/data-model.md` lines 187-189 - Integration configuration structure

**Dependencies**: T043, T047
**Test Coverage**: Unit tests with mocked HaloPSA responses
**Estimated Time**: 2.5 hours

---

### T050 [US7] - Add get_integration() method to OrganizationContext

**File**: `workflow-engine/shared/context.py`
**Description**: Factory method for creating integration clients
**Actions**:

-   Add `get_integration(name: str)` method to `OrganizationContext`
-   Support integration names: "msgraph", "halopsa"
-   Instantiate appropriate integration class with `self` as context
-   Call `authenticate()` on integration before returning
-   Cache integration instances for request duration
-   Raise error if integration name not recognized

**Reference Documents**:

-   `specs/001-complete-mvp-for/quickstart.md` lines 1450-1478 - Context usage examples

**Dependencies**: T043, T048, T049
**Test Coverage**: Unit tests for get_integration (msgraph, halopsa, invalid name)
**Estimated Time**: 1 hour

---

### T051 [US7] - Contract tests for Workflow Execution API

**File**: `workflow-engine/tests/contract/test_execution_contract.py`
**Description**: Write contract tests for workflow execution endpoint (TDD)
**Actions**:

-   Test `WorkflowExecutionRequest` validation (parameters, metadata)
-   Test `WorkflowExecutionResponse` model (executionId, status, result, error)
-   Test error responses (400, 404, 500)

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/workflow-api.yaml` lines 151-274 - Execution endpoint spec

**Dependencies**: T007
**Test Coverage**: Pydantic model validation for execution requests/responses
**Estimated Time**: 1 hour

---

### T052 [US7] - Implement POST /workflows/{workflowName} (execute workflow)

**File**: `workflow-engine/function_app.py` (or `functions/execute.py`)
**Description**: Execute a workflow with provided parameters and org context
**Actions**:

-   Add `@bp.route(route="workflows/{workflowName}", methods=["POST"])`
-   Apply `@require_auth` (from T008), `@with_org_context` (from T046), `@require_permission("canExecuteWorkflows")` decorators
-   Extract `workflowName` from route
-   Get workflow metadata from registry
-   Parse and validate `WorkflowExecutionRequest`
-   Generate execution ID (UUID)
-   Create execution record in `WorkflowExecutions` table (status="Pending")
-   Invoke workflow function with context + parameters
-   Update execution record with result/error and status ("Success" or "Failed")
-   Also insert into `UserExecutions` table (dual-indexing)
-   Return `WorkflowExecutionResponse` (200 for success, 500 for failure with error message)

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/workflow-api.yaml` lines 151-274 - Execution endpoint spec
-   `specs/001-complete-mvp-for/data-model.md` lines 401-495 - WorkflowExecutions/UserExecutions schemas

**Dependencies**: T006, T008, T009, T039, T043, T046, T051
**Test Coverage**: Integration test (execute workflow, verify execution logged, verify context passed correctly)
**Estimated Time**: 4 hours

---

### T053 [US7] - Implement execution logging to Table Storage

**File**: `workflow-engine/shared/execution_logger.py`
**Description**: Helper for logging workflow execution details
**Actions**:

-   Create `ExecutionLogger` class
-   Implement `create_execution(org_id, workflow_name, executed_by, input_data)` → returns execution_id
-   Implement `update_execution(execution_id, status, result=None, error_message=None, duration_ms=None)`
-   Handle dual-indexing: write to `WorkflowExecutions` (by org) and `UserExecutions` (by user)
-   Calculate reverse timestamp for RowKey
-   Store InputData and Result as JSON strings
-   Handle large results (>32KB) → store in Blob Storage, reference in table

**Reference Documents**:

-   `specs/001-complete-mvp-for/data-model.md` lines 401-495 - Execution logging schemas
-   `specs/001-complete-mvp-for/data-model.md` lines 43-64 - Reverse timestamp pattern

**Dependencies**: T006
**Test Coverage**: Unit tests for execution logging (create, update, dual-index)
**Estimated Time**: 2.5 hours

---

### T054 [US7] - Integration test for workflow execution with context

**File**: `workflow-engine/tests/integration/test_workflow_with_context.py`
**Description**: Test workflow execution with full organization context
**Actions**:

-   Set up test organization in Table Storage (via Azurite)
-   Add test config values to `OrgConfig` table
-   Mock Key Vault secret retrieval
-   Execute workflow that uses `context.get_config()` and `context.get_secret()`
-   Verify workflow receives correct config and secrets
-   Verify execution is logged in both `WorkflowExecutions` and `UserExecutions` tables
-   Test workflow failure handling (exception → status="Failed")

**Dependencies**: T043, T046, T052, T053
**Test Coverage**: Integration test for full workflow execution flow
**Estimated Time**: 2.5 hours

---

## Phase 7: User Story 4 - Data Providers for Dynamic Form Fields (P2)

**User Story**: Developers need to create data provider functions that supply dynamic options for form fields.

**Goal**: Implement decorator pattern for data providers with auto-discovery and execution endpoint

**Independent Test**: Can create a data provider that returns a list of items, create a form field that references it, and verify the form receives the correct options when rendered.

**Entities**: DataProvider (metadata only - not persisted)
**Endpoints**: `GET /data-providers/{providerName}`

**Checkpoint**: ✅ Data provider decorators working, auto-discovery functional, data provider endpoint returns options

### T055 [US4] - Create @data_provider decorator

**File**: `workflow-engine/shared/decorators.py`
**Description**: Implement decorator for registering data provider functions
**Actions**:

-   Create `@data_provider(name, description, category="", cache_ttl_seconds=0)` decorator
-   Store data provider metadata in registry
-   Return decorated function unchanged
-   Support cache TTL for performance

**Reference Documents**:

-   `specs/001-complete-mvp-for/quickstart.md` lines 800-900 - Data provider decorator examples

**Dependencies**: T039
**Test Coverage**: Unit tests for data_provider decorator (register, extract metadata)
**Estimated Time**: 1.5 hours

---

### T056 [US4] - Implement data provider auto-discovery

**File**: `workflow-engine/data_providers/__init__.py`
**Description**: Auto-import all data provider modules to trigger registration
**Actions**:

-   Use `importlib` to import all `.py` files in `data_providers/` directory
-   Skip `__init__.py` and private files
-   Log discovered data providers

**Dependencies**: T055
**Test Coverage**: Integration test (create dummy data provider, verify auto-discovery)
**Estimated Time**: 45 minutes

---

### T057 [US4] - Create example data provider: get_available_licenses

**File**: `workflow-engine/data_providers/get_available_licenses.py`
**Description**: Example data provider for M365 license options
**Actions**:

-   Create `get_available_licenses()` function with `@data_provider` decorator
-   Accept `OrganizationContext` as parameter
-   Use `context.get_integration("msgraph")` to fetch subscribed SKUs
-   Filter to available licenses (consumedUnits < prepaidUnits)
-   Return list of `{"label": "M365 E5 (15 available)", "value": "sku-id"}` dicts
-   Add error handling for Graph API failures

**Reference Documents**:

-   `specs/001-complete-mvp-for/quickstart.md` lines 901-1000 - Data provider examples

**Dependencies**: T043, T048, T055
**Test Coverage**: Unit test with mocked Graph API
**Estimated Time**: 1.5 hours

---

### T058 [US4] - Contract tests for Data Provider API

**File**: `workflow-engine/tests/contract/test_data_provider_contract.py`
**Description**: Write contract tests for data provider endpoint (TDD)
**Actions**:

-   Test `DataProviderResponse` model (options array, cached flag)
-   Test option structure: `{"label": string, "value": any, "metadata"?: object}`
-   Test error responses

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/workflow-api.yaml` lines 276-340 - Data provider endpoint spec

**Dependencies**: T007
**Test Coverage**: Pydantic model validation for data provider responses
**Estimated Time**: 45 minutes

---

### T059 [US4] - Implement GET /data-providers/{providerName}

**File**: `workflow-engine/functions/data_providers.py` (or in function_app.py)
**Description**: Execute a data provider and return options
**Actions**:

-   Add `@bp.route(route="data-providers/{providerName}", methods=["GET"])`
-   Apply `@require_auth`, `@with_org_context` decorators
-   Extract `providerName` from route
-   Get data provider metadata from registry
-   Execute data provider function with context
-   Cache result if `cache_ttl_seconds > 0` (in-memory cache with expiration)
-   Return `DataProviderResponse` (options + cached flag)
-   Handle data provider exceptions gracefully (500 error with message)

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/workflow-api.yaml` lines 276-340 - Data provider endpoint spec

**Dependencies**: T008, T039, T046, T055, T058
**Test Coverage**: Integration test (execute data provider, verify options, test caching)
**Estimated Time**: 2.5 hours

---

### T060 [US4] - Integration test for data provider execution

**File**: `workflow-engine/tests/integration/test_data_provider_execution.py`
**Description**: Test data provider execution with organization context
**Actions**:

-   Create test data provider that uses context.get_config()
-   Execute data provider via endpoint
-   Verify correct options returned
-   Test caching behavior (call twice, verify cached flag)
-   Test data provider failure handling

**Dependencies**: T055, T056, T057, T059
**Test Coverage**: Integration test for data provider lifecycle
**Estimated Time**: 1.5 hours

---

## Phase 8a-b: Config, Roles & User Management (2025-10-11) ✅ COMPLETE

**Goal**: Implement global configuration management, role-based access control, and user type differentiation (PLATFORM vs ORG)

**Status**: ✅ Complete
**Completion Date**: 2025-10-11
**Related User Stories**: US9 (User Management & Roles), US10 (Global Config Management)
**Tasks Completed**: T091-T102

### Implementation Summary

This phase implemented foundational configuration management and role-based access control infrastructure for the Bifrost Integrations. Key achievements include global/org-scoped configuration, comprehensive roles system, and user type differentiation.

#### Backend Changes (Phase 8a: T091-T095)

**Tables Added** (`api/shared/init_tables.py`):

-   `Config` - Renamed from OrgConfig, supports GLOBAL and org-specific partitions
-   `Roles` - Organization-specific roles (name, description, isActive)
-   `UserRoles` - Many-to-many mapping of ORG users to roles
-   `FormRoles` - Many-to-many mapping of forms to roles for access control

**User Model Updates** (`api/shared/models.py`):

-   Added `UserType` enum with values: `PLATFORM`, `ORG`
-   Updated `User` model with `user_type` field
-   Added validation: only ORG users can be assigned to roles

**Config API** (`api/functions/org_config.py`):

-   Supports `?scope=global|org` query parameter
-   Implements fallback pattern: org-specific → GLOBAL → None
-   `get_config_value(key, org_id)` helper function for config resolution
-   Sensitive value masking for keys containing: secret, password, token, key, credential
-   Mask format: shows first 4 and last 4 characters (e.g., "supe\*\*\*2345")

**Roles API** (`api/functions/roles.py` - NEW):

-   `GET /api/roles` - List all roles for organization
-   `POST /api/roles` - Create new role
-   `PUT /api/roles/{roleId}` - Update role
-   `DELETE /api/roles/{roleId}` - Soft delete role (IsActive=False)
-   `GET /api/roles/{roleId}/users` - List users in role
-   `POST /api/roles/{roleId}/users` - Batch assign users to role
-   `DELETE /api/roles/{roleId}/users/{userId}` - Remove user from role
-   `GET /api/roles/{roleId}/forms` - List forms assigned to role
-   `POST /api/roles/{roleId}/forms` - Batch assign forms to role
-   `DELETE /api/roles/{roleId}/forms/{formId}` - Remove form from role
-   Validation: rejects PLATFORM users from role assignment

**Users API Updates** (`api/functions/permissions.py`):

-   Added `?type=platform|org&orgId={id}` query parameters to `list_users`
-   Implements role-based form access control in `list_forms` endpoint
-   Form access logic: PLATFORM users see all forms, ORG users see only public forms or forms assigned to their roles via FormRoles table

#### Frontend Changes (Phase 8b: T096-T102)

**UI Framework Setup** (`client/`):

-   ShadCN UI installed and configured with Tailwind CSS 4
-   15+ ShadCN components added: button, card, input, table, dialog, dropdown-menu, toast, form, select, tabs, badge, alert, skeleton, separator, checkbox, label
-   React Query setup for data fetching with cache management
-   Responsive layout with dark mode support

**Layout Components** (`client/src/components/layout/`):

-   `Layout.tsx` - Flex container with sidebar + main content area
-   `Header.tsx` - User profile dropdown, organization selector, dark mode toggle
-   `Sidebar.tsx` - Navigation menu with active route highlighting

**API Client** (`client/src/services/api.ts`):

-   Axios instance with baseURL from environment variables
-   Request interceptor for authentication token injection
-   Response interceptor for global error handling (401 → logout, 403 → permission error)

**Config Management UI** (`client/src/pages/Config.tsx`):

-   Scope switching: GLOBAL vs organization-specific config
-   Config table with columns: Key, Value (masked for secrets), Type, Description, Actions
-   ConfigDialog for create/edit with validation
-   Support for config types: string, int, bool, json, secret_ref
-   Visual indicators for GLOBAL partition vs org-specific

**Roles Management UI** (`client/src/pages/Roles.tsx`):

-   Role CRUD operations with table view
-   AssignUsersDialog - Multi-select ORG users for role assignment
-   AssignFormsDialog - Multi-select forms for role assignment
-   Badge displays for user count and form count per role

**User Management UI** (`client/src/pages/Users.tsx`):

-   User type filtering: PLATFORM vs ORG users
-   Organization filtering for ORG users
-   Role assignment dialog (ORG users only)
-   Visual distinction: PLATFORM users get admin badge, ORG users get role badges

**Form Access Control** (`client/src/pages/Forms.tsx`):

-   Backend filtering implementation verified and confirmed working
-   PLATFORM users: see all forms
-   ORG users: see public forms + forms assigned to their roles
-   No additional frontend filtering needed (API handles it)

#### Testing & Validation

**Contract Tests** (`api/tests/contract/test_roles_contract.py` - NEW):

-   27 comprehensive tests covering all Roles API request/response models
-   `CreateRoleRequest` validation (5 tests): required fields, min/max length, empty values
-   `UpdateRoleRequest` validation (6 tests): partial updates, field validation
-   `AssignUsersToRoleRequest` validation (4 tests): empty list rejection, required fields
-   `AssignFormsToRoleRequest` validation (4 tests): empty list rejection, required fields
-   `Role` response model (2 tests): full and minimal field validation
-   `UserType` enum validation (3 tests): PLATFORM, ORG, invalid type handling
-   Request/response cycle contracts (3 tests): create flow, update flow, assignment flow
-   **Result**: 27 passed, 2 warnings

**Integration Tests** (`api/tests/integration/test_config_integration.py` - NEW):

-   24 integration tests covering Config API with GLOBAL/org scope patterns
-   GLOBAL config CRUD (4 tests): create, get, update, delete operations
-   Org-specific config CRUD (2 tests): create, get operations
-   Fallback pattern validation (4 tests):
    -   Org config takes priority over GLOBAL
    -   Falls back to GLOBAL when org missing
    -   Returns None when both missing
    -   GLOBAL-only lookup when no org_id provided
-   Sensitive value masking (8 tests):
    -   Keywords: secret, password, token, key, credential
    -   Mask format verification: first 4 + \*\*\* + last 4 characters
    -   Short value handling: full masking
    -   Case-insensitive detection
    -   Non-sensitive values pass through unchanged
-   Config types (4 tests): STRING, INT, BOOL, SECRET_REF storage and retrieval
-   Query by scope (2 tests): GLOBAL partition query, org partition query
-   **Result**: 24 passed, 2 warnings

**Test Suite Summary**:

-   Total tests: 75+ (51 new tests added in Phase 8a-b)
-   Contract tests: 56 (13 execution + 16 data provider + 27 roles)
-   Integration tests: 36 (12 existing + 24 config)
-   Unit tests: 39+
-   All tests passing with 0 failures

#### Architecture Decisions

**Config Fallback Pattern**:

-   Allows org-specific overrides of GLOBAL defaults
-   Single table with partition key differentiation: `GLOBAL` vs `org-{id}`
-   Row key format: `config:{key_name}`
-   Explicit fallback logic in `get_config_value()` helper

**Role-Based Access Control**:

-   Three-table design: Roles, UserRoles, FormRoles
-   Only ORG users can be assigned roles (PLATFORM users have implicit full access)
-   Forms can be public (accessible to all) or role-restricted
-   FormRoles table enables granular form-level permissions

**User Type Differentiation**:

-   PLATFORM users: MSP administrators with full system access
-   ORG users: Customer organization users with role-based restrictions
-   User type determines access control strategy (bypass vs enforce)

**Sensitive Value Protection**:

-   Client-side masking in Config UI for secret_ref type
-   Server-side masking for config keys containing sensitive keywords
-   Prevents accidental exposure of credentials in UI and logs

### Files Created/Modified

**Backend**:

-   `api/shared/init_tables.py` - Added 4 new tables
-   `api/shared/models.py` - UserType enum, Role models, request/response schemas
-   `api/functions/org_config.py` - GLOBAL scope support, fallback, masking
-   `api/functions/roles.py` - NEW FILE: Complete Roles API (11 endpoints)
-   `api/functions/permissions.py` - User type filtering, form access logic
-   `api/tests/contract/test_roles_contract.py` - NEW FILE: 27 contract tests
-   `api/tests/integration/test_config_integration.py` - NEW FILE: 24 integration tests

**Frontend**:

-   `client/package.json` - ShadCN UI, Tailwind CSS 4, React Query dependencies
-   `client/tailwind.config.js` - Tailwind CSS 4 configuration
-   `client/src/components/ui/*` - 15+ ShadCN UI components
-   `client/src/components/layout/Layout.tsx` - NEW FILE: Main layout
-   `client/src/components/layout/Header.tsx` - NEW FILE: Header with user menu
-   `client/src/components/layout/Sidebar.tsx` - NEW FILE: Navigation sidebar
-   `client/src/services/api.ts` - Axios client with auth interceptor
-   `client/src/pages/Config.tsx` - NEW FILE: Config management UI
-   `client/src/pages/Roles.tsx` - NEW FILE: Roles management UI
-   `client/src/pages/Users.tsx` - NEW FILE: User management UI
-   `client/src/components/config/ConfigDialog.tsx` - NEW FILE: Config editor
-   `client/src/components/roles/*` - NEW FILES: Role assignment dialogs
-   `client/src/components/users/*` - NEW FILES: User role assignment dialogs
-   `client/src/hooks/useConfig.ts` - NEW FILE: Config data fetching hooks
-   `client/src/hooks/useRoles.ts` - NEW FILE: Roles data fetching hooks
-   `client/src/contexts/OrgScopeContext.tsx` - NEW FILE: Org scope management

### Next Steps

Phase 8a-b provides the foundational infrastructure for:

-   **Phase 8c**: Form Builder UI (T103-T113) - Can now use role-based form visibility
-   **Phase 9**: Form Renderer (T114-T116) - Can enforce role-based access during form execution
-   **Phase 10**: Execution History (T117-T125) - Can show role-filtered execution logs
-   **Phase 11**: Polish & Integration (T126-T132) - Final UX improvements with role-aware UI

The config and roles infrastructure is production-ready with comprehensive test coverage and follows Azure Table Storage best practices for partition key design and query efficiency.

---

## Phase 8d: Form Execution Implementation (2025-10-11) ✅ COMPLETE

**Goal**: Enable end-to-end form submission and workflow execution with proper result display

**Status**: ✅ Complete
**Completion Date**: 2025-10-11
**Related User Stories**: US5 (Form Builder), US6 (Form Renderer), US7 (Workflow Execution)

### Implementation Summary

This phase implemented the complete form execution flow from form submission through workflow execution to result display. Key achievements:

#### Backend Changes

**File**: `/api/functions/forms.py` (lines 719-894)

-   Added `submit_form` endpoint: `POST /api/forms/{formId}/submit?orgId={orgId}`
-   Validates user permissions and form active status
-   Calls workflow engine with form data
-   Returns complete execution result (status, duration, output, error)

**File**: `/client/src/services/api.ts` (lines 107-121)

-   Fixed `post()` and `put()` methods to accept third `params` parameter
-   Enables query parameter passing for orgId and other values
-   Critical fix for orgId parameter requirement

#### Frontend Changes

**File**: `/client/src/pages/Forms.tsx` (complete rewrite)

-   Merged "Forms" and "Execute Forms" into single page
-   Changed from table layout to card grid (3 columns)
-   Added "Launch" button as primary action on each card
-   Edit and Delete buttons shown as icon buttons
-   Removed all references to separate "Execute Forms" page

**File**: `/client/src/pages/RunForm.tsx` (lines 16-20, 76-80, 84-128)

-   Changed page title from "Execute Workflow" to display `{form.name}`
-   Shows form description or linked workflow name as subtitle
-   Updated all navigation to use "Forms" instead of "Workflows"
-   Changed state from `executionId` to `executionResult` for full result storage
-   Displays formatted JSON result with duration and status indicators

**File**: `/client/src/pages/ExecuteWorkflow.tsx` (lines 22-40, 191-235)

-   Updated to display full execution results instead of "queued for response"
-   Shows result as formatted JSON in expandable code block
-   Displays execution duration and status
-   Shows error details when workflows fail

**File**: `/client/src/components/forms/FormRenderer.tsx` (lines 26-28, 94-104)

-   Changed `onSuccess` prop from `(executionId: string)` to `(executionResult: any)`
-   Passes complete result object to parent component
-   Enables result display in RunForm and ExecuteWorkflow pages

**File**: `/client/src/components/layout/Sidebar.tsx` (lines 22-68)

-   Removed "Execute Forms" navigation item
-   Fixed issue where both "Forms" and "Execute Forms" would show as active
-   Kept single "Forms" menu item at position #3

**File**: `/client/src/services/forms.ts` (lines 58-66)

-   Updated `submitForm()` to accept `orgId` parameter
-   Passes orgId as query parameter via API client

**File**: `/client/src/hooks/useForms.ts` (lines 128-144)

-   Updated `useSubmitForm()` hook to get orgId from UserContext
-   Passes orgId to forms service method

**File**: `/client/src/App.tsx` (lines 53-67)

-   Removed `<Route path="forms/execute">` route
-   Removed ExecuteForms component import
-   Single route: `/forms` for card view, `/execute/:formId` for form runner

#### Files Modified

-   `/api/functions/forms.py` - Form submission endpoint
-   `/client/src/services/api.ts` - API client params fix
-   `/client/src/pages/Forms.tsx` - Merged card view
-   `/client/src/pages/RunForm.tsx` - Result display
-   `/client/src/pages/ExecuteWorkflow.tsx` - Result display
-   `/client/src/components/forms/FormRenderer.tsx` - Result callback
-   `/client/src/components/layout/Sidebar.tsx` - Navigation fix
-   `/client/src/services/forms.ts` - OrgId parameter
-   `/client/src/hooks/useForms.ts` - OrgId from context
-   `/client/src/App.tsx` - Route cleanup

#### Key Technical Decisions

1. **Synchronous Execution Display**: Instead of showing "queued for response", display actual execution results when workflows complete synchronously
2. **Single Forms Page**: Merge Forms and Execute Forms into one page with Launch button (no separate navigation item)
3. **OrgId Parameter Passing**: Pass orgId as query parameter through entire chain (hook → service → API client → backend)
4. **Card Grid Layout**: Use 3-column grid for better visual hierarchy and action visibility
5. **Result Formatting**: Display workflow results as formatted JSON with syntax highlighting

#### Issues Resolved

1. **404 Error on Form Submission**: Missing endpoint implementation
2. **OrgId Parameter Missing**: Multi-layer fix across hook, service, and API client
3. **"Queued for Response" Message**: Updated UI to show actual synchronous results
4. **Page Title Confusion**: Changed from "Execute Workflow" to actual form name
5. **Dual Navigation Items**: Removed "Execute Forms" from sidebar
6. **API Client Limitation**: Added params parameter support to POST/PUT methods

#### Remaining Work

-   **Role-Based UI**: Edit/Delete buttons should only show for admins (currently visible to all users)
-   **Data Provider Support**: FormBuilder needs UI for linking fields to data providers
-   **History Page**: Execution history viewer needs implementation
-   **Organizations Page**: Org management UI not yet built
-   **Users Page**: User management UI not yet built

---

## Phase 11: Polish & Integration (2025-10-11) ✅ COMPLETE

**Goal**: Cross-cutting UX improvements, error handling, and final polish for production readiness

**Status**: ✅ Complete
**Completion Date**: 2025-10-11
**Tasks Completed**: T126-T132 (Polish tasks)

### Implementation Summary

This phase focused on enhancing user experience, error handling, and overall application polish to achieve production quality. Key improvements centered on execution history visualization, error boundaries, and UX consistency.

#### Execution History Enhancements

**Component Created**: `client/src/components/execution/PrettyInputDisplay.tsx`

-   **Smart field name conversion**: Automatically converts snake_case → Title Case
    -   Examples: `user_name` → "User Name", `api_key` → "API Key"
    -   Handles common acronyms (API, ID, URL, HTTP)
-   **Intelligent value formatting**:
    -   Booleans: "Yes"/"No" instead of true/false
    -   Numbers: Locale-formatted with thousands separators
    -   Dates: Auto-detected and formatted with toLocaleString()
    -   URLs: Detected and badged
    -   Arrays: Comma-separated display with count badge
    -   Objects: Formatted JSON with syntax highlighting
-   **Type badges**: Visual indicators for each value type (number, date, URL, array, etc.)
-   **View toggle for Platform Admins**:
    -   Platform Admins can switch between Pretty View and Raw JSON
    -   ORG users only see Pretty View (no toggle shown)
    -   Default view: Pretty for better UX
-   **Responsive grid layout**: 2-column grid on desktop, single column on mobile
-   **Friendly labels with technical reference**: Shows both friendly name and original snake_case key

**Page Updated**: `client/src/pages/ExecutionDetails.tsx`

-   Integrated `PrettyInputDisplay` component for Input Parameters section
-   Added `useAuth()` hook to detect Platform Admin status
-   Toggle visibility controlled by `isPlatformAdmin` flag
-   Improved user experience for viewing execution inputs

#### Error Handling & Recovery

**Component Created**: `client/src/components/ErrorBoundary.tsx`

-   **React Error Boundary** for graceful crash recovery
-   **Production-safe error display**:
    -   User-friendly error message with icon
    -   Actionable recovery options (Try Again, Go Home buttons)
    -   Hidden technical stack traces in production
-   **Development mode enhancements**:
    -   Full error stack trace visible in details
    -   Component stack trace for debugging
    -   Console logging of errors
-   **Elegant error UI**:
    -   Centered card layout with destructive alert
    -   Helpful suggestions (refresh page, clear cache, contact support)
    -   Consistent with ShadCN UI design system

**App Integration**: `client/src/App.tsx`

-   Wrapped entire app with `<ErrorBoundary>`
-   Catches errors anywhere in component tree
-   Prevents white screen of death
-   Graceful degradation with recovery options

#### Toast Notifications (Already Implemented)

**Audit Results**: Toast notifications already comprehensive across all CRUD operations

-   ✅ Organizations: create, update, delete
-   ✅ Config: create, update, delete
-   ✅ Roles: create, update, delete, assign users, assign forms
-   ✅ Users: create, update, role assignments
-   ✅ Forms: create, update, delete
-   ✅ Workflows: execution status
-   All toasts include success/error states with descriptive messages
-   Consistent use of Sonner toast library

#### Loading & Empty States (Already Implemented)

**Audit Results**: All pages have proper loading and empty states

-   ✅ **12 pages audited**: All have Skeleton loaders
-   ✅ **Empty states**: Contextual icons, messages, and CTAs
-   ✅ **Loading buttons**: All mutations show pending state
-   ✅ **Error handling**: API errors displayed with retry options
-   Pages checked:
    -   Organizations, Users, Roles, Config (4 states each)
    -   Forms, ExecutionHistory, ExecutionDetails (4-6 states each)
    -   Workflows, ExecuteWorkflow, RunForm (4-6 states each)

#### Architecture Quality

**Error Boundaries**:

-   Class component implementation (React requirement)
-   TypeScript-safe with proper error typing
-   Customizable fallback UI support
-   Production/development mode awareness

**User Experience**:

-   Consistent spacing and typography across all pages
-   ShadCN UI components used throughout
-   Dark mode support maintained
-   Responsive design verified
-   Accessible error recovery flows

### Files Created/Modified

**New Files**:

-   `client/src/components/execution/PrettyInputDisplay.tsx` - Pretty input display component
-   `client/src/components/ErrorBoundary.tsx` - Global error boundary

**Modified Files**:

-   `client/src/pages/ExecutionDetails.tsx` - Integrated PrettyInputDisplay with admin toggle
-   `client/src/App.tsx` - Wrapped app with ErrorBoundary

### User Experience Improvements

**For ORG Users**:

-   Execution inputs always displayed in friendly, readable format
-   No confusing snake_case or raw JSON
-   Clear labeling with type indicators
-   Responsive card layout for easy scanning

**For Platform Admins**:

-   Toggle between Pretty View and Raw JSON
-   Flexibility to debug with JSON when needed
-   Default to Pretty View for better UX
-   Quick switch with single button click

**For All Users**:

-   Application crashes handled gracefully
-   Clear error messages with recovery options
-   No more white screen of death
-   Toast notifications for all actions
-   Consistent loading states everywhere
-   Empty states with helpful guidance

### Next Steps (Future Enhancements)

While Phase 11 polish is complete, potential future improvements:

-   Add user filtering to execution history (show only "My Executions")
-   Add date range filtering to execution history
-   Add export functionality for execution results
-   Add keyboard shortcuts for power users
-   Add bulk operations for roles/users
-   Enhanced form validation with inline error messages

---

## Phase 8: User Story 9 - User Management, Config & Secrets UI (P2)

**User Story**: An MSP administrator needs to manage global config/secrets, create roles for organization users, and manage user access to forms.

**Goal**: Implement backend APIs and UI for Config, Roles, User management with MSP vs ORG user types

**Independent Test**: Can create global config key-values, create roles, assign roles to organization users, and verify organization users only see permitted forms.

**Entities**: Config, Roles, UserRoles, FormRoles, Users (with UserType)
**Endpoints**: Config CRUD, Roles CRUD, UserRoles CRUD, FormRoles CRUD, Users list/update

**Checkpoint**: ✅ Global config management working, role-based access control functional, user type differentiation clear

---

### **Phase 8a: Backend Foundation (T091-T095)** ✅ COMPLETE

### T091 [US9] - Backend: Add new tables to init_tables.py ✅

**Completed**: 2025-10-11
**File**: `api/shared/init_tables.py`
**Description**: Add Config, Roles, UserRoles, FormRoles tables
**Actions**:

-   Rename `OrgConfig` to `Config` in REQUIRED_TABLES list
-   Add `Roles` to REQUIRED_TABLES
-   Add `UserRoles` to REQUIRED_TABLES
-   Add `FormRoles` to REQUIRED_TABLES
-   Update comments to reflect global vs org partitioning for Config table
-   Run init script to create tables locally

**Reference Documents**:

-   `specs/001-complete-mvp-for/data-model.md` lines 130-204 - Config table
-   `specs/001-complete-mvp-for/data-model.md` lines 450-567 - Roles tables

**Dependencies**: None (foundational change)
**Test Coverage**: None (table initialization)
**Estimated Time**: 30 minutes

---

### T092 [US9] - Backend: Update User model with UserType field ✅

**Completed**: 2025-10-11
**File**: `api/shared/models.py`
**Description**: Add UserType enum and field to User Pydantic model
**Actions**:

-   Create `UserType` enum with values: `MSP`, `ORG`
-   Add `user_type: UserType` field to `User` model
-   Add `is_msp_admin: bool` field (only applies to MSP users)
-   Update any existing user creation logic to default to UserType.MSP
-   Add validation: `is_msp_admin` can only be True for MSP users

**Reference Documents**:

-   `specs/001-complete-mvp-for/data-model.md` lines 252-316 - Users table with UserType
-   `specs/001-complete-mvp-for/spec.md` lines 154-171 - User Story 9

**Dependencies**: T091
**Test Coverage**: Contract tests for User model validation
**Estimated Time**: 1 hour

---

### T093 [US9] - Backend: Rename OrgConfig to Config with GLOBAL support ✅

**Completed**: 2025-10-11
**File**: `api/functions/org_config.py` → rename to `api/functions/config.py`
**Description**: Update Config API to support GLOBAL partition
**Actions**:

-   Rename file from `org_config.py` to `config.py`
-   Update all references to `OrgConfig` table → `Config`
-   Add `scope` query parameter to GET endpoint: `?scope=global|org`
-   Update GET logic: if scope=global, query PartitionKey="GLOBAL"
-   Update POST logic: accept `scope` in request body, set PartitionKey accordingly
-   Implement fallback lookup helper: `get_config_value(key, org_id)` → checks org then global
-   Add value masking for sensitive keys (containing "secret", "password", "token")
-   Update all tests to use new table name

**Reference Documents**:

-   `specs/001-complete-mvp-for/data-model.md` lines 130-204 - Config table schema
-   `specs/001-complete-mvp-for/spec.md` lines 174-194 - User Story 10

**Dependencies**: T091, T092
**Test Coverage**: Integration tests for global vs org config, fallback pattern
**Estimated Time**: 3 hours

---

### T094 [US9] - Backend: Create Roles API endpoints ✅

**Completed**: 2025-10-11
**File**: `api/functions/roles.py` (new file)
**Description**: Implement CRUD for Roles, UserRoles, FormRoles
**Actions**:

-   Create new `roles.py` function file with blueprint
-   Implement `GET /api/roles` → list all roles
-   Implement `POST /api/roles` → create role (name, description)
-   Implement `PUT /api/roles/{roleId}` → update role
-   Implement `DELETE /api/roles/{roleId}` → soft delete (IsActive=False)
-   Implement `GET /api/roles/{roleId}/users` → list users in role (query UserRoles)
-   Implement `POST /api/roles/{roleId}/users` → batch assign users to role (UserRoles insert)
-   Implement `DELETE /api/roles/{roleId}/users/{userId}` → remove user from role
-   Implement `GET /api/roles/{roleId}/forms` → list forms assigned to role (query FormRoles)
-   Implement `POST /api/roles/{roleId}/forms` → batch assign forms to role (FormRoles insert)
-   Implement `DELETE /api/roles/{roleId}/forms/{formId}` → remove form from role
-   Add validation: only ORG users can be assigned to roles (reject MSP users)
-   Apply `@require_auth` and `@require_permission("canManageRoles")` decorators

**Reference Documents**:

-   `specs/001-complete-mvp-for/data-model.md` lines 450-567 - Roles table schemas

**Dependencies**: T091, T092, T093
**Test Coverage**: Contract + integration tests for all endpoints
**Estimated Time**: 6 hours

---

### T095 [US9] - Backend: Update Users API for roles and form access ✅

**Completed**: 2025-10-11
**File**: `api/functions/permissions.py` (extend existing `list_users` function)
**Description**: Add user type filtering and role-based form access
**Actions**:

-   Update `list_users` to accept `?type=msp|org&orgId={id}` query params
-   Add filter logic for UserType field
-   Implement `PUT /api/users/{userId}/roles` → batch update user's roles (UserRoles upsert/delete)
-   Implement `GET /api/users/{userId}/roles` → get user's assigned roles
-   Implement `GET /api/users/{userId}/forms` → get forms user can access:
    -   If user is MSP: return all forms
    -   If user is ORG: query UserRoles → get role IDs → query FormRoles → return form IDs
-   Update user auto-creation logic to set UserType (check domain or default to ORG)
-   Add validation: MSP users cannot be assigned roles (return 400 error)

**Reference Documents**:

-   `specs/001-complete-mvp-for/data-model.md` lines 252-316 - Users with UserType
-   `specs/001-complete-mvp-for/data-model.md` lines 450-567 - Role access logic

**Dependencies**: T091, T092, T093, T094
**Test Coverage**: Integration tests for type filtering, role assignments, form access
**Estimated Time**: 4 hours

---

### **Phase 8b: Frontend UI (T096-T102)** ✅ COMPLETE

### T096 [US9] - Client: Setup ShadCN UI and Tailwind CSS 4 ✅

**Completed**: 2025-10-11
**File**: `client/` (configuration files)
**Description**: Install and configure ShadCN UI with Tailwind CSS 4
**Actions**:

-   Install Tailwind CSS 4: `npm install tailwindcss@next @tailwindcss/postcss@next autoprefixer`
-   Run `npx tailwindcss init -p` to create config
-   Configure `tailwind.config.js` with darkMode: ["class"], content paths
-   Install ShadCN: `npx shadcn@latest init` (Style: Default, Base color: Slate, CSS variables: Yes)
-   Add core components: button, card, input, label, table, dialog, dropdown-menu, toast, form, select, tabs, badge, alert, skeleton, separator, checkbox
-   Install dependencies: `npm install @tanstack/react-query zustand react-hook-form zod @hookform/resolvers lucide-react axios date-fns`
-   Create `src/lib/queryClient.ts` for React Query setup
-   Update `src/main.tsx` to wrap with QueryClientProvider
-   Verify path aliases work: `@/components/ui/button`

**Reference Documents**:

-   `client/SETUP.md` - Complete setup guide
-   `client/UI_STANDARDS.md` - Component standards and best practices
-   `specs/001-complete-mvp-for/spec.md` lines 230-276 - UI Requirements (UI-001 to UI-030)

**Dependencies**: T001
**Test Coverage**: None (setup task)
**Estimated Time**: 2 hours

---

### T097 [US9] - Client: Create base Layout with Header and Sidebar ✅

**Completed**: 2025-10-11
**File**: `client/src/components/layout/Layout.tsx`, `Header.tsx`, `Sidebar.tsx`
**Description**: Build responsive layout structure using ShadCN components
**Actions**:

-   Create `Layout.tsx` with flex container for sidebar + main content
-   Create `Header.tsx` with user profile dropdown, organization selector
-   Create `Sidebar.tsx` with navigation menu (Dashboard, Workflows, Forms, Users, Roles, Config, History)
-   Use `Outlet` from react-router for nested routes
-   Implement dark mode toggle in header
-   Add MSP vs ORG user type indicator in header
-   Style with Tailwind utilities, responsive breakpoints

**Reference Documents**:

-   `client/SETUP.md` lines 153-174 - Layout structure example
-   `specs/001-complete-mvp-for/spec.md` lines 232-236 - UI navigation requirements

**Dependencies**: T091
**Test Coverage**: None
**Estimated Time**: 3 hours

---

### T098 [US9] - Client: Create API client with auth interceptor ✅

**Completed**: 2025-10-11
**File**: `client/src/services/api.ts`
**Description**: Setup Axios instance with authentication and error handling
**Actions**:

-   Create base Axios instance with `baseURL` from env var
-   Add request interceptor to inject auth token from localStorage
-   Add response interceptor for global error handling (401 → logout, 403 → show permission error)
-   Export typed API methods for Config, Users, Roles endpoints
-   Create `src/services/types.ts` for API response types

**Reference Documents**:

-   `client/SETUP.md` lines 130-151 - API client setup
-   `specs/001-complete-mvp-for/spec.md` lines 267-276 - Error handling requirements

**Dependencies**: T091
**Test Coverage**: None
**Estimated Time**: 2 hours

---

### T099 [US9] - Client: Build Global Config Management UI ✅

**Completed**: 2025-10-11
**File**: `client/src/pages/ConfigPage.tsx`, `client/src/components/config/ConfigList.tsx`, `ConfigEditor.tsx`
**Description**: UI for managing global MSP-wide configuration key-values
**Actions**:

-   Create `ConfigPage.tsx` with tabs: "Global Config" and "Organization Overrides"
-   Build `ConfigList.tsx` table component:
    -   Columns: Key, Value (masked for secrets), Type, Description, Actions
    -   Filter by config type (string, number, boolean, json)
    -   Search by key name
    -   Actions: Edit, Delete
-   Build `ConfigEditor.tsx` dialog:
    -   Fields: Key (text), Value (textarea for json, input for others), Type (select), Description (textarea)
    -   Validation: Key uniqueness, JSON validation for json type
    -   Save → POST/PUT to Config API
-   Use ShadCN: Table, Dialog, Input, Select, Button, Badge components
-   Use React Query for data fetching with cache invalidation
-   Show visual indicator for GLOBAL partition vs org-specific

**Reference Documents**:

-   `specs/001-complete-mvp-for/spec.md` lines 174-194 - User Story 10 (Config Management)
-   `specs/001-complete-mvp-for/data-model.md` lines 130-204 - Config table schema
-   `client/UI_STANDARDS.md` - Component standards

**Dependencies**: T096, T097, T098, T093
**Test Coverage**: None
**Estimated Time**: 5 hours

---

### T100 [US9] - Client: Build Roles Management UI ✅

**Completed**: 2025-10-11
**File**: `client/src/pages/RolesPage.tsx`, `client/src/components/roles/RoleList.tsx`, `RoleEditor.tsx`
**Description**: UI for creating and managing roles for organization users
**Actions**:

-   Create `RolesPage.tsx` with role list and create button
-   Build `RoleList.tsx` table:
    -   Columns: Role Name, Description, # of Users, # of Forms, Created, Actions
    -   Actions: Edit, Delete, Assign Users, Assign Forms
-   Build `RoleEditor.tsx` dialog:
    -   Fields: Name (text), Description (textarea)
    -   Save → POST/PUT to Roles API
-   Build `AssignUsersDialog.tsx`:
    -   Multi-select from organization users (UserType="ORG" only)
    -   Save → batch POST to UserRoles API
-   Build `AssignFormsDialog.tsx`:
    -   Multi-select from available forms
    -   Save → batch POST to FormRoles API
-   Use ShadCN: Table, Dialog, Multi-Select, Badge components
-   Use React Query with optimistic updates

**Reference Documents**:

-   `specs/001-complete-mvp-for/spec.md` lines 154-171 - User Story 9 (User Management & Roles)
-   `specs/001-complete-mvp-for/data-model.md` lines 450-567 - Roles, UserRoles, FormRoles tables

**Dependencies**: T096, T097, T098, T094
**Test Coverage**: None
**Estimated Time**: 6 hours

---

### T101 [US9] - Client: Build User Management UI with User Types ✅

**Completed**: 2025-10-11
**File**: `client/src/pages/UsersPage.tsx`, `client/src/components/users/UserList.tsx`, `UserEditor.tsx`
**Description**: UI for managing MSP and ORG users with role assignments
**Actions**:

-   Create `UsersPage.tsx` with tabs: "MSP Users" and "Organization Users"
-   Build `UserList.tsx` table:
    -   Columns: Name, Email, User Type (badge), Organization (for ORG users), Roles (for ORG users), Last Login, Status, Actions
    -   Filter by user type (MSP vs ORG)
    -   Filter by organization (for ORG users)
    -   Search by name/email
    -   Actions: Edit Roles (ORG users only), Deactivate
-   Build `UserEditor.tsx` dialog:
    -   Display user info (read-only, auto-created from Entra ID)
    -   For ORG users: Multi-select roles
    -   Save → PUT to Users API
-   Show visual distinction: MSP users get admin badge, ORG users get role badges
-   Use ShadCN: Table, Tabs, Badge, Dialog, Multi-Select components

**Reference Documents**:

-   `specs/001-complete-mvp-for/spec.md` lines 154-171 - User Story 9
-   `specs/001-complete-mvp-for/data-model.md` lines 252-316 - Users table with UserType

**Dependencies**: T096, T097, T098, T095
**Test Coverage**: None
**Estimated Time**: 5 hours

---

### T102 [US9] - Client: Implement Form Access Control for ORG Users ✅

**Completed**: 2025-10-11
**File**: `client/src/hooks/useFormAccess.ts`, update form list pages
**Description**: Filter forms based on user type and role assignments
**Actions**:

-   Create `useFormAccess()` hook:
    -   If user is MSP: return all forms (bypass role check)
    -   If user is ORG: fetch `GET /api/users/{userId}/forms` to get permitted forms
    -   Cache results in React Query
-   Update `FormsPage.tsx` to use `useFormAccess()` for filtering
-   Update `FormRenderer.tsx` to check access before rendering
-   Show "No access" message for restricted forms
-   Use Zustand store for current user context (type, roles, org)

**Reference Documents**:

-   `specs/001-complete-mvp-for/data-model.md` lines 450-567 - FormRoles access logic
-   `specs/001-complete-mvp-for/spec.md` lines 154-171 - Role-based form access

**Dependencies**: T096, T101, T095
**Test Coverage**: None
**Estimated Time**: 3 hours

---

## Phase 8c: User Story 5 - Form Builder (P2)

**User Story**: An MSP administrator needs to create forms with various field types that are linked to workflows and use data providers for dynamic fields.

**Goal**: Implement form CRUD operations with JSON schema storage

**Independent Test**: Can create a form with multiple field types (text, email, select, checkbox), link it to a workflow, and verify the form can be saved and retrieved.

**Entities**: Forms
**Endpoints**: `GET /api/forms`, `POST /api/forms`, `GET /api/forms/{formId}`, `PUT /api/forms/{formId}`, `DELETE /api/forms/{formId}`

**Checkpoint**: ✅ Forms CRUD working, form schema validation functional, forms can reference data providers

### T113 [US5] - Contract tests for Forms API

**File**: `management-api/tests/contract/test_forms_contract.py`
**Description**: Write contract tests for Forms endpoints (TDD)
**Actions**:

-   Test `CreateFormRequest` validation (name, linkedWorkflow, formSchema)
-   Test `Form` response model
-   Test `FormSchema` structure (fields array)
-   Test `FormField` validation (name, type enum, required, validation object, dataProvider)
-   Test error responses

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 175-344 - Forms schemas
-   `specs/001-complete-mvp-for/data-model.md` lines 314-399 - Forms table schema

**Dependencies**: T007
**Test Coverage**: Pydantic model validation for forms
**Estimated Time**: 1.5 hours

---

### T112 [US5] - Implement GET /api/forms (list forms)

**File**: `management-api/functions/forms.py`
**Description**: Return all forms for an organization plus global forms
**Actions**:

-   Create blueprint for forms endpoints
-   Add `@bp.route(route="forms", methods=["GET"])`
-   Apply `@require_auth` decorator
-   Extract `X-Organization-Id` from header
-   Query `Forms` table for org-specific forms (PartitionKey=org_id)
-   Query `Forms` table for global forms (PartitionKey="GLOBAL")
-   Merge results and return as array of `Form` models

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 633-663 - GET /api/forms endpoint
-   `specs/001-complete-mvp-for/data-model.md` lines 314-399 - Forms table with GLOBAL partition

**Dependencies**: T006, T008, T010, T011a, T101
**Test Coverage**: Integration test (list org forms, list global forms, combined list)
**Estimated Time**: 1.5 hours

---

### T113 [US5] - Implement POST /api/forms (create form)

**File**: `management-api/functions/forms.py`
**Description**: Create a new form for an organization
**Actions**:

-   Add `@bp.route(route="forms", methods=["POST"])`
-   Apply `@require_auth`, `@require_permission("canManageForms")` decorators
-   Parse and validate `CreateFormRequest`
-   Validate `formSchema` JSON structure (parse and validate against schema)
-   Validate `linkedWorkflow` exists (call Workflow Engine metadata endpoint)
-   Generate form ID (UUID)
-   Insert into `Forms` table (PartitionKey=org_id OR "GLOBAL", RowKey=form_id)
-   Set CreatedBy, CreatedAt, UpdatedAt, IsActive=True
-   Return created `Form` model (201 Created)

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 665-689 - POST /api/forms endpoint
-   `specs/001-complete-mvp-for/data-model.md` lines 314-399 - Forms table schema

**Dependencies**: T006, T007, T008, T009, T011a, T101
**Test Coverage**: Integration test (create form, validate schema, test invalid workflow link)
**Estimated Time**: 2.5 hours

---

### T112 [US5] [P] - Implement GET /api/forms/{formId} (get form details)

**File**: `management-api/functions/forms.py`
**Description**: Return details for a specific form
**Actions**:

-   Add `@bp.route(route="forms/{formId}", methods=["GET"])`
-   Apply `@require_auth` decorator
-   Extract `formId` from route and `X-Organization-Id` from header
-   Try to get form from org partition OR GLOBAL partition
-   Parse `FormSchema` JSON string into object before returning
-   Return `Form` model or 404 Not Found

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 691-717 - GET /api/forms/{formId} endpoint

**Dependencies**: T006, T008, T011a, T101
**Test Coverage**: Integration test (get org form, get global form, get non-existent form)
**Estimated Time**: 1.5 hours

---

### T113 [US5] [P] - Implement PUT /api/forms/{formId} (update form)

**File**: `management-api/functions/forms.py`
**Description**: Update an existing form
**Actions**:

-   Add `@bp.route(route="forms/{formId}", methods=["PUT"])`
-   Apply `@require_auth`, `@require_permission("canManageForms")` decorators
-   Parse and validate `CreateFormRequest` (full replacement)
-   Get existing form entity
-   Validate new `formSchema` and `linkedWorkflow`
-   Update entity fields (name, description, formSchema, linkedWorkflow)
-   Set UpdatedAt to current timestamp
-   Update entity in Table Storage
-   Return updated `Form` model

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 719-741 - PUT /api/forms/{formId} endpoint

**Dependencies**: T006, T007, T008, T009, T011a, T101
**Test Coverage**: Integration test (update form, verify changes, test validation)
**Estimated Time**: 2 hours

---

### T112 [US5] [P] - Implement DELETE /api/forms/{formId} (delete form)

**File**: `management-api/functions/forms.py`
**Description**: Soft delete a form by setting isActive=False
**Actions**:

-   Add `@bp.route(route="forms/{formId}", methods=["DELETE"])`
-   Apply `@require_auth`, `@require_permission("canManageForms")` decorators
-   Get existing form entity
-   Set IsActive=False and UpdatedAt
-   Update entity
-   Return 204 No Content

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 743-757 - DELETE /api/forms/{formId} endpoint

**Dependencies**: T006, T008, T009, T011a, T101
**Test Coverage**: Integration test (delete form, verify IsActive=False)
**Estimated Time**: 1 hour

---

### T113 [US5] - Client: Create Form TypeScript types

**File**: `client/src/types/form.ts`
**Description**: Define TypeScript interfaces for forms
**Actions**:

-   Create `Form`, `CreateFormRequest`, `FormSchema`, `FormField` interfaces
-   Create enum for field types: `text | email | number | select | checkbox | textarea`
-   Export all types

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 175-344 - Forms schemas

**Dependencies**: T001, T007
**Test Coverage**: None (type definitions)
**Estimated Time**: 30 minutes

---

### T112 [US5] - Client: Create Forms API service

**File**: `client/src/services/apiClient.ts` (extend)
**Description**: Add API wrapper methods for Forms endpoints
**Actions**:

-   Add methods: `getForms()`, `getForm(id)`, `createForm(data)`, `updateForm(id, data)`, `deleteForm(id)`
-   Include `X-Organization-Id` header

**Dependencies**: T023, T107
**Test Coverage**: None
**Estimated Time**: 1 hour

---

### T113 [US5] - Client: Create useForms custom hook

**File**: `client/src/hooks/useForms.ts`
**Description**: React hook for form state management
**Actions**:

-   Create `useForms()` hook
-   Fetch forms on mount
-   Provide methods: `createForm(data)`, `updateForm(id, data)`, `deleteForm(id)`
-   Handle loading and error states
-   Return `{ forms, loading, error, createForm, updateForm, deleteForm }`

**Dependencies**: T001, T108
**Test Coverage**: None
**Estimated Time**: 1.5 hours

---

### T112 [US5] - Client: Build FormBuilderPage UI component

**File**: `client/src/pages/FormBuilderPage.tsx`
**Description**: Page for creating and editing forms
**Actions**:

-   Accept optional `formId` from route (edit mode vs. create mode)
-   Display form metadata fields: name, description, linkedWorkflow (dropdown from metadata)
-   Display field builder section:
    -   List of added fields with drag-and-drop reordering
    -   "Add Field" button → opens field editor
    -   Field editor form: name, label, type (dropdown), required (checkbox), validation rules, dataProvider (dropdown from metadata), defaultValue, placeholder, helpText
-   Implement field type-specific options (e.g., dataProvider only for select fields)
-   Save button → validates and submits form
-   Preview section showing how form will render

**Dependencies**: T001, T109
**Test Coverage**: None
**Estimated Time**: 5 hours

---

### T113 [US5] - Client: Fetch and cache workflow metadata

**File**: `client/src/services/workflowClient.ts`
**Description**: Create client for Workflow Engine API
**Actions**:

-   Create Axios instance for Workflow Engine base URL
-   Add auth interceptor (same as Management API)
-   Implement `getMetadata()` method → fetches `/admin/metadata`
-   Cache metadata in memory or React Context
-   Parse workflows and data providers for form builder dropdowns

**Dependencies**: T001
**Test Coverage**: None
**Estimated Time**: 1.5 hours

---

## Phase 9: User Story 6 - Form Renderer & Submission (P2)

**User Story**: An MSP technician needs to view and submit forms to execute workflows, with dynamic field options loaded from data providers.

**Goal**: Implement form rendering with validation and workflow execution

**Independent Test**: Can render a form, fill in fields (including a select field with dynamic options), submit it, and verify the workflow is executed with the correct parameters.

**Entities**: None (uses Forms from US5, triggers Workflows from US7)
**Endpoints**: Uses existing `GET /api/forms/{formId}`, `POST /workflows/{workflowName}`, `GET /data-providers/{providerName}`

**Checkpoint**: ✅ Forms render correctly, data providers populate select fields, form submission executes workflows

### T116 [US6] - Client: Create FormRenderer component

**File**: `client/src/components/forms/FormRenderer.tsx`
**Description**: Component for rendering and validating forms
**Actions**:

-   Accept `form: Form` as prop
-   Parse `formSchema` to get field definitions
-   Render field for each type:
    -   text → `<input type="text">`
    -   email → `<input type="email">`
    -   number → `<input type="number">`
    -   select → `<select>` with options from data provider
    -   checkbox → `<input type="checkbox">`
    -   textarea → `<textarea>`
-   Implement client-side validation (required, pattern, min/max)
-   Show inline validation errors
-   For select fields with `dataProvider`, fetch options on mount from `GET /data-providers/{providerName}`
-   Handle loading state for data provider queries
-   Disable submit until all validations pass
-   Emit `onSubmit(formData)` event with field values as object

**Dependencies**: T001, T107, T111
**Test Coverage**: None (or React Testing Library component tests)
**Estimated Time**: 4 hours

---

### T115 [US6] - Client: Create FormSubmissionPage UI component

**File**: `client/src/pages/FormSubmissionPage.tsx`
**Description**: Page for submitting forms and executing workflows
**Actions**:

-   Accept `formId` from route parameters
-   Fetch form details using `getForm(formId)`
-   Render form using `<FormRenderer>`
-   Handle form submission:
    -   Extract form data
    -   Call `POST /workflows/{linkedWorkflow}` with parameters from form data
    -   Include `X-Organization-Id` header (from organization selector)
    -   Show loading spinner during execution
    -   Display execution result (success message + result data OR error message)
    -   Provide execution ID for tracking
-   Add "Submit Another" button to reset form

**Dependencies**: T001, T108, T111, T112
**Test Coverage**: None
**Estimated Time**: 3 hours

---

### T116 [US6] - Client: Add organization selector to navigation

**File**: `client/src/components/common/OrganizationSelector.tsx`
**Description**: Dropdown for selecting active organization (sets X-Organization-Id)
**Actions**:

-   Fetch user's accessible organizations on mount
-   Display dropdown in app header/nav
-   Store selected org ID in React Context or state
-   Automatically include selected org ID in `X-Organization-Id` header for all API requests (via Axios interceptor)
-   Show org name in dropdown
-   Persist selection in localStorage

**Dependencies**: T001, T023
**Test Coverage**: None
**Estimated Time**: 2 hours

---

## Phase 10: User Story 8 - Execution History & Audit Trail (P3)

**User Story**: MSP technicians need to view a history of workflow executions to monitor automation activity, troubleshoot issues, and maintain an audit trail.

**Goal**: Implement execution history queries and detail views

**Independent Test**: Can execute several workflows, then query execution history and verify all executions are recorded with correct timestamps, status, and details.

**Entities**: WorkflowExecutions, UserExecutions (already created in US7)
**Endpoints**: `GET /api/executions`, `GET /api/executions/{executionId}`, `GET /api/executions/users/{userId}`

**Checkpoint**: ✅ Execution history queries working, filtering functional, execution details viewable

### T125 [US8] - Contract tests for Executions API

**File**: `management-api/tests/contract/test_executions_contract.py`
**Description**: Write contract tests for Executions endpoints (TDD)
**Actions**:

-   Test `WorkflowExecution` response model
-   Test query parameter validation (status enum, limit range)

**Reference Documents**:

-   `specs/001-complete-mvp-for/contracts/workflow-api.yaml` lines 151-274 - Execution schemas
-   `specs/001-complete-mvp-for/data-model.md` lines 401-495 - WorkflowExecutions schema

**Dependencies**: T007
**Test Coverage**: Pydantic model validation for executions
**Estimated Time**: 45 minutes

---

### T124 [US8] - Implement GET /api/executions (list executions for org)

**File**: `management-api/functions/executions.py`
**Description**: Return execution history for an organization with filtering
**Actions**:

-   Create blueprint for executions endpoints
-   Add `@bp.route(route="executions", methods=["GET"])`
-   Apply `@require_auth`, `@require_permission("canViewHistory")` decorators
-   Extract `X-Organization-Id` from header
-   Extract query parameters: `status`, `workflowName`, `limit` (default=50, max=200)
-   Query `WorkflowExecutions` table (PartitionKey=org_id)
-   Filter by status and workflowName if provided
-   Limit results (take first N)
-   Return array of `WorkflowExecution` models (newest first due to reverse timestamp)

**Reference Documents**:

-   `specs/001-complete-mvp-for/data-model.md` lines 401-464 - WorkflowExecutions table schema
-   `specs/001-complete-mvp-for/data-model.md` lines 43-64 - Reverse timestamp ordering

**Dependencies**: T006, T008, T009, T010, T011a, T115
**Test Coverage**: Integration test (list executions, filter by status, filter by workflow)
**Estimated Time**: 2 hours

---

### T125 [US8] [P] - Implement GET /api/executions/{executionId} (get execution details)

**File**: `management-api/functions/executions.py`
**Description**: Return full details for a specific execution
**Actions**:

-   Add `@bp.route(route="executions/{executionId}", methods=["GET"])`
-   Apply `@require_auth`, `@require_permission("canViewHistory")` decorators
-   Extract `executionId` from route
-   Extract `X-Organization-Id` from header (to determine RowKey with reverse timestamp)
-   Query `WorkflowExecutions` table (scan if necessary - execution ID is not in RowKey directly)
-   Parse InputData and Result JSON strings into objects
-   Return `WorkflowExecution` model or 404 Not Found

**Reference Documents**:

-   `specs/001-complete-mvp-for/data-model.md` lines 401-464 - WorkflowExecutions schema

**Dependencies**: T006, T008, T009, T011a, T115
**Test Coverage**: Integration test (get execution, get non-existent execution)
**Estimated Time**: 1.5 hours

---

### T124 [US8] [P] - Implement GET /api/executions/users/{userId} (user execution history)

**File**: `management-api/functions/executions.py`
**Description**: Return all executions by a user across all authorized organizations
**Actions**:

-   Add `@bp.route(route="executions/users/{userId}", methods=["GET"])`
-   Apply `@require_auth` decorator
-   Ensure requesting user can only query their own executions (or is admin)
-   Extract query parameter: `limit` (default=50, max=200)
-   Query `UserExecutions` table (PartitionKey=userId)
-   Limit results
-   Return array of `WorkflowExecution` models (summary data from UserExecutions table)

**Reference Documents**:

-   `specs/001-complete-mvp-for/data-model.md` lines 466-495 - UserExecutions table schema

**Dependencies**: T006, T008, T011a, T115
**Test Coverage**: Integration test (get user executions across multiple orgs)
**Estimated Time**: 1.5 hours

---

### T125 [US8] - Client: Create Execution TypeScript types

**File**: `client/src/types/execution.ts`
**Description**: Define TypeScript interfaces for executions
**Actions**:

-   Create `WorkflowExecution` interface
-   Create enum for status: `Pending | Running | Success | Failed`
-   Export types

**Dependencies**: T001, T007
**Test Coverage**: None (type definitions)
**Estimated Time**: 15 minutes

---

### T124 [US8] - Client: Create Executions API service

**File**: `client/src/services/apiClient.ts` (extend)
**Description**: Add API wrapper methods for Executions endpoints
**Actions**:

-   Add methods: `getExecutions(orgId, filters)`, `getExecution(executionId, orgId)`, `getUserExecutions(userId, limit)`
-   Include `X-Organization-Id` header

**Dependencies**: T023, T119
**Test Coverage**: None
**Estimated Time**: 1 hour

---

### T125 [US8] - Client: Create useExecutions custom hook

**File**: `client/src/hooks/useExecutions.ts`
**Description**: React hook for execution history state
**Actions**:

-   Create `useExecutions(orgId, filters)` hook
-   Fetch executions on mount and when filters change
-   Support filtering by status and workflow name
-   Handle loading and error states
-   Return `{ executions, loading, error, refetch }`

**Dependencies**: T001, T120
**Test Coverage**: None
**Estimated Time**: 1 hour

---

### T124 [US8] - Client: Build ExecutionHistoryPage UI component

**File**: `client/src/pages/ExecutionHistoryPage.tsx`
**Description**: Page for viewing execution history with filtering
**Actions**:

-   Use `useExecutions()` hook
-   Display table of executions with columns: timestamp, workflow name, executed by, status, duration
-   Add filters: status dropdown (All/Pending/Running/Success/Failed), workflow name input
-   Add "My Executions" toggle → switches to user-scoped query
-   Click row → navigate to execution details page
-   Color-code status (green=Success, red=Failed, yellow=Running, gray=Pending)
-   Auto-refresh every 10 seconds for Running executions
-   Pagination or infinite scroll

**Dependencies**: T001, T121
**Test Coverage**: None
**Estimated Time**: 3.5 hours

---

### T125 [US8] - Client: Build ExecutionDetailsPage UI component

**File**: `client/src/pages/ExecutionDetailsPage.tsx`
**Description**: Page for viewing detailed execution information
**Actions**:

-   Accept `executionId` from route parameters
-   Fetch execution details using `getExecution(executionId, orgId)`
-   Display:
    -   Execution ID, workflow name, status badge
    -   Executed by user, timestamp, duration
    -   Input parameters (formatted JSON)
    -   Output result (formatted JSON) or error message
    -   Link to associated form (if formId present)
-   Add "Re-run" button (navigates to form submission page with pre-filled data)
-   Add "View Logs" button (if logs available)

**Dependencies**: T001, T120
**Test Coverage**: None
**Estimated Time**: 2.5 hours

---

## Phase 11: Polish & Integration

**Goal**: Cross-cutting concerns, documentation, error handling, deployment preparation

**Checkpoint**: ✅ All components integrated, documentation complete, ready for deployment

### T124 [Polish] - Add global error handling to all backend endpoints

**File**: `management-api/function_app.py`, `workflow-engine/function_app.py`
**Description**: Centralized error handling for consistent API responses
**Actions**:

-   Add global exception handler in function app
-   Catch all unhandled exceptions
-   Return structured error response: `{"error": "...", "message": "...", "details": {...}}`
-   Log errors with stack traces
-   Differentiate between expected errors (400, 404) and unexpected errors (500)

**Dependencies**: T010
**Test Coverage**: Integration test (trigger error, verify response format)
**Estimated Time**: 1.5 hours

---

### T125 [Polish] [P] - Implement logging and monitoring

**File**: All backend files
**Description**: Add structured logging for observability
**Actions**:

-   Use Python `logging` module
-   Log all HTTP requests (method, path, user, org, duration)
-   Log workflow executions (start, end, status)
-   Log errors with stack traces
-   Configure log level from environment variables
-   Integrate with Azure Application Insights (optional)

**Dependencies**: All backend tasks
**Test Coverage**: None (logging infrastructure)
**Estimated Time**: 2 hours

---

### T126 [Polish] [P] - Add loading states and error handling to all client pages

**File**: All client page components
**Description**: Improve UX with consistent loading and error states
**Actions**:

-   Add loading spinners for all API calls
-   Add error messages for failed API calls
-   Add retry buttons for failed requests
-   Add empty states for lists (e.g., "No organizations yet")
-   Add success toasts for CRUD operations

**Dependencies**: All client tasks
**Test Coverage**: None
**Estimated Time**: 3 hours

---

### T127 [Polish] - Create client routing configuration

**File**: `client/src/App.tsx`
**Description**: Set up React Router with all pages
**Actions**:

-   Install `react-router-dom`
-   Configure routes:
    -   `/` → OrganizationsPage
    -   `/organizations/:orgId` → OrganizationConfigPage
    -   `/permissions` → PermissionsPage
    -   `/forms` → List of forms (new page or reuse FormBuilderPage)
    -   `/forms/new` → FormBuilderPage (create mode)
    -   `/forms/:formId/edit` → FormBuilderPage (edit mode)
    -   `/forms/:formId/submit` → FormSubmissionPage
    -   `/executions` → ExecutionHistoryPage
    -   `/executions/:executionId` → ExecutionDetailsPage
-   Add navigation menu with links
-   Add protected routes (require authentication)

**Dependencies**: T033, T025, T026, T036, T110, T113, T122, T123
**Test Coverage**: None
**Estimated Time**: 2 hours

---

### T128 [Polish] - Update quickstart.md with real implementation details

**File**: `specs/001-complete-mvp-for/quickstart.md`
**Description**: Update developer guide with actual file paths and code examples from implementation
**Actions**:

-   Update project structure to match actual implementation
-   Add real code examples from implemented workflows and data providers
-   Update environment variable examples
-   Add troubleshooting section with actual errors encountered
-   Verify all commands work

**Dependencies**: All implementation tasks
**Test Coverage**: None (documentation)
**Estimated Time**: 2 hours

---

### T129 [Polish] - Create deployment documentation

**File**: `docs/deployment.md` (new file)
**Description**: Document how to deploy all three components to Azure
**Actions**:

-   Document Azure resources needed (Functions App x2, Static Web App, Storage Account, Key Vault)
-   Provide ARM templates or Bicep files for infrastructure-as-code
-   Document environment variable configuration for production
-   Document CI/CD pipeline setup (GitHub Actions)
-   Document DNS and custom domain setup
-   Document secret management in production

**Dependencies**: All implementation tasks
**Test Coverage**: None (documentation)
**Estimated Time**: 3 hours

---

### T130 [Polish] - End-to-end integration test

**File**: `management-api/tests/e2e/test_full_workflow.py` (new directory)
**Description**: Test complete user flow from org creation to workflow execution
**Actions**:

-   Create organization via API
-   Grant user permissions via API
-   Create form via API
-   Execute workflow via form submission
-   Verify execution logged
-   Query execution history
-   Verify all data isolated by org
-   Clean up test data

**Dependencies**: All implementation tasks
**Test Coverage**: E2E test for complete platform
**Estimated Time**: 3 hours

---

## Dependency Graph

```
Phase 1 (Setup)
└─> Phase 2 (Foundation)
    └─> Phase 3 (US1: Organizations) ──┐
    └─> Phase 4 (US2: Permissions) ────┤
    └─> Phase 5 (US3: Workflows) ──────┤
                                        ├─> Phase 6 (US7: Execution)
                                        │       │
                                        │       └─> Phase 7 (US4: Data Providers)
                                        │                   │
                                        └───────────────────┴─> Phase 8 (US5: Form Builder)
                                                                        │
                                                                        └─> Phase 9 (US6: Form Renderer)
                                                                                    │
                                                                                    └─> Phase 10 (US8: Execution History)
                                                                                                │
                                                                                                └─> Phase 11 (Polish)
```

**Critical Path**: Setup → Foundation → Organizations → Workflows → Execution → Data Providers → Forms → Form Renderer → Polish

**Parallelizable Phases** (after Foundation):

-   Phase 3 (Organizations), Phase 4 (Permissions), Phase 5 (Workflows) can be developed in parallel
-   Phase 8 (Forms) and Phase 10 (Execution History) can be developed in parallel after Phase 6

---

## Implementation Strategy

### Recommended MVP Scope (Weeks 1-2)

Implement **only P1 user stories** for minimum viable product:

**Week 1**:

-   Phase 1: Project Setup (T001-T005b) - Day 1
-   Phase 2: Foundational Infrastructure (T006-T011a) - Days 2-3
-   Phase 3: User Story 1 - Organizations (T012-T026) - Days 4-5

**Week 2**:

-   Phase 4: User Story 2 - Permissions (T027-T036) - Days 1-2
-   Phase 5: User Story 3 - Workflows (T037-T045) - Days 3-4
-   Phase 6: User Story 7 - Execution (T046-T054) - Day 5

**Result**: Working platform where developers can create workflows, admins can manage orgs/permissions, workflows execute with org context.

### Extended MVP (Weeks 3-5)

Add **P2 user stories** for UI and user-facing forms:

**Week 3**:

-   Phase 7: User Story 4 - Data Providers (T055-T060) - Day 1
-   Phase 8: Config, Roles & User Management UI (T091-T100) - Days 2-5

**Week 4**:

-   Phase 8b: Form Builder (T101-T111) - Days 1-4
-   Phase 9: Form Renderer (T112-T114) - Day 5

**Week 5**:

-   Phase 10: Execution History (T115-T123) - Days 1-3
-   Phase 11: Polish & Integration (T124-T130) - Days 4-5

**Result**: Complete MVP with global config management, role-based access, forms, execution history, and production-ready polish.

---

## Validation Checkpoints

After each phase, validate:

1. **After Phase 2**: Can insert/query Table Storage, validate tokens, use Pydantic models
2. **After Phase 3**: Can create org, add config, configure integrations, verify org isolation
3. **After Phase 4**: Can grant permissions, login enforces org access, users auto-created
4. **After Phase 5**: Workflows auto-register, metadata endpoint works
5. **After Phase 6**: Can execute workflow via HTTP, context loads correctly, execution logged
6. **After Phase 7**: Data providers return options, caching works
7. **After Phase 8**: Global config UI works, roles created, users assigned, form access controlled
8. **After Phase 8b**: Can create form with multiple field types, link to workflow
9. **After Phase 9**: Can render form, submit, execute workflow
10. **After Phase 10**: Can view execution history, filter results
11. **After Phase 11**: All pages work, errors handled gracefully, ready for deployment

---

## Next Steps

1. **Review this task list** with team and stakeholders
2. **Assign tasks** to developers based on expertise (frontend vs. backend)
3. **Set up repositories** and run Phase 1 tasks
4. **Start with Foundation phase** (all user stories depend on this)
5. **Follow TDD approach**: Write contract tests before implementation for each user story
6. **Use parallel execution** where possible (different files = parallelizable)
7. **Run validation checkpoints** after each phase
8. **Prioritize P1 stories** for MVP (Phases 1-6)
9. **Expand to P2 stories** once P1 is stable (Phases 7-9)
10. **Polish and deploy** (Phase 11)

---

**Ready for implementation!** 🚀
