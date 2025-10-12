# Implementation Tasks: MSP Automation Platform MVP

**Feature**: MSP Automation Platform MVP
**Branch**: `001-complete-mvp-for`
**Generated**: 2025-10-10
**Updated**: 2025-10-10 (Post-Audit)
**Status**: Ready for implementation

---

## Overview

This document provides a dependency-ordered task list for implementing the MSP Automation Platform MVP. Tasks are organized by user story to enable independent implementation and testing of each feature increment.

**Total Tasks**: 100 (updated from 90)
**New Tasks Added**: 10 (table initialization, IntegrationConfig, Users management, testing infrastructure)
**Estimated Complexity**: ~4-5 weeks for full-stack developer
**Testing Strategy**: Test-first development (TDD) - tests before implementation per constitution Principle IV

**🔗 Design Artifacts Referenced**: All tasks now include references to detailed specifications in:
- `specs/001-complete-mvp-for/data-model.md` - Entity schemas and Table Storage design
- `specs/001-complete-mvp-for/contracts/*.yaml` - API specifications (OpenAPI 3.0)
- `specs/001-complete-mvp-for/research.md` - Architectural patterns and technology decisions
- `specs/001-complete-mvp-for/quickstart.md` - Code examples and developer guide

---

## Task Organization Strategy

Tasks are organized into phases aligned with user stories:

1. **Phase 1: Project Setup** - Repository initialization, tooling, local development environment
2. **Phase 2: Foundational Infrastructure** - Shared components that ALL user stories depend on
3. **Phase 3-6: P1 User Stories** - Core features (Organizations, Auth, Workflows, Execution)
4. **Phase 7-9: P2 User Stories** - User-facing features (Data Providers, Form Builder, Form Renderer)
5. **Phase 10: P3 User Story** - Execution History & Audit Trail
6. **Phase 11: Polish & Integration** - Cross-cutting concerns, documentation, deployment

**MVP Recommendation**: Implement Phases 1-6 (P1 stories only) for minimum viable product.

---

## Phase 1: Project Setup & Local Development

**Goal**: Initialize all three repositories with proper tooling and local development environment

**Independent Test**: Can run all three components locally (client on port 3000, Management API on port 7071, Workflow Engine on port 7072) with Azurite

**Checkpoint**: ✅ All repos initialized, Azurite running, tables created, basic "hello world" endpoints functional

### T001 [Setup] - Initialize client repository structure
**File**: `client/` (entire directory structure)
**Description**: Create React + TypeScript project structure with Vite or CRA
**Actions**:
- Run `npm create vite@latest client -- --template react-ts` OR `npx create-react-app client --template typescript`
- Create directory structure: `src/components/`, `src/services/`, `src/types/`, `src/pages/`, `src/hooks/`
- Configure `tsconfig.json` with strict mode
- Add `.env.local.example` with ALL required environment variables (see details below)
- Create `staticwebapp.config.json` for Azure Static Web Apps routing

**Environment Variables for .env.local.example**:
```env
REACT_APP_MANAGEMENT_API_URL=http://localhost:7071
REACT_APP_WORKFLOW_API_URL=http://localhost:7072
REACT_APP_AZURE_CLIENT_ID=your-app-registration-client-id
REACT_APP_AZURE_TENANT_ID=your-tenant-id
REACT_APP_AZURE_REDIRECT_URI=http://localhost:3000
```

**Reference Documents**:
- `specs/001-complete-mvp-for/quickstart.md` lines 146-183 - Client project structure
- `specs/001-complete-mvp-for/plan.md` lines 146-183 - Directory organization

**Dependencies**: None
**Test Coverage**: None (project initialization)
**Estimated Time**: 30 minutes

---

### T002 [Setup] - Initialize Management API repository structure
**File**: `management-api/` (separate repo - future)
**Description**: Create Azure Functions Python project for Management API
**Actions**:
- Run `func init management-api --python`
- Create `functions/` directory for HTTP endpoints
- Create `shared/` directory for utilities (storage.py, auth.py, models.py, middleware.py, secrets.py)
- Create `tests/contract/` and `tests/integration/` directories
- Add `requirements.txt` with dependencies: `azure-functions`, `azure-data-tables`, `pydantic`, `azure-identity`, `azure-keyvault-secrets`, `pytest`, `pytest-asyncio`, `pytest-mock`
- Create `local.settings.json.example` with ALL required settings (see details below)
- Configure `host.json` for Azure Functions v2

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
- `specs/001-complete-mvp-for/quickstart.md` lines 185-206 - Management API structure
- `specs/001-complete-mvp-for/plan.md` lines 185-206 - Project organization

**Dependencies**: None
**Test Coverage**: None (project initialization)
**Estimated Time**: 30 minutes

---

### T003 [Setup] - Initialize Workflow Engine repository structure
**File**: `workflow-engine/` (separate repo - future)
**Description**: Create Azure Functions Python project for Workflow Engine
**Actions**:
- Run `func init workflow-engine --python`
- Create `workflows/` directory for workflow functions
- Create `data_providers/` directory for data provider functions
- Create `shared/` directory (decorators.py, context.py, registry.py, storage.py, integrations/, secrets.py)
- Create `admin/` directory for metadata endpoint
- Create `tests/contract/`, `tests/integration/`, `tests/unit/` directories
- Add `requirements.txt` with same dependencies as Management API
- Create `local.settings.json.example` with same structure as Management API

**Reference Documents**:
- `specs/001-complete-mvp-for/quickstart.md` lines 208-237 - Workflow Engine structure
- `specs/001-complete-mvp-for/plan.md` lines 208-237 - Project organization

**Dependencies**: None
**Test Coverage**: None (project initialization)
**Estimated Time**: 30 minutes

---

### T004 [Setup] [P] - Set up Azurite for local Azure Storage emulation
**File**: N/A (local environment)
**Description**: Install and configure Azurite for local Table Storage and Blob Storage
**Actions**:
- Install Azurite: `npm install -g azurite`
- Create startup script: `.specify/scripts/start-azurite.sh`
- Script should run: `azurite --silent --location ~/azurite --debug ~/azurite/debug.log`
- Document Azurite connection string in `local.settings.json.example` for both backend repos
- Verify Azurite starts on ports 10000 (Blob), 10001 (Queue), 10002 (Table)
- Connection string: `UseDevelopmentStorage=true` or `DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;`

**Reference Documents**:
- `specs/001-complete-mvp-for/quickstart.md` lines 96-107 - Azurite setup guide
- `specs/001-complete-mvp-for/plan.md` lines 23 - Local development with Azurite

**Dependencies**: None
**Test Coverage**: None (environment setup)
**Estimated Time**: 15 minutes

---

### T005 [Setup] [P] - Configure linting and formatting for all repos
**File**: `client/.eslintrc.json`, `management-api/.flake8`, `workflow-engine/.flake8`
**Description**: Set up code quality tools for consistency
**Actions**:
- Client: Add ESLint + Prettier with TypeScript rules (`npm install --save-dev eslint prettier @typescript-eslint/parser @typescript-eslint/eslint-plugin`)
- Management API: Add `.flake8`, `pyproject.toml` with Black and mypy configs
- Workflow Engine: Add `.flake8`, `pyproject.toml` with Black and mypy configs
- Add pre-commit hooks (optional): `pip install pre-commit`

**Dependencies**: T001, T002, T003
**Test Coverage**: None (tooling)
**Estimated Time**: 30 minutes

---

### T005a [Setup] - Initialize Azure Table Storage tables 🆕
**File**: `management-api/shared/init_tables.py`, `workflow-engine/shared/init_tables.py`
**Description**: Create initialization script to ensure all required tables exist (for both local Azurite and production Azure)
**Actions**:
- Create `init_tables.py` script in both repos using `TableServiceClient` from `azure-data-tables`
- Check if table exists before creating: `if not service_client.query_tables(f"TableName eq '{table_name}'")`
- Create all 9 required tables:
  1. **Organizations** (PartitionKey="ORG", stores org master list)
  2. **OrgConfig** (PartitionKey=OrgId, stores config key-value pairs)
  3. **IntegrationConfig** (PartitionKey=OrgId, stores integration settings)
  4. **Users** (PartitionKey="USER", stores MSP technician accounts)
  5. **UserPermissions** (PartitionKey=UserId, for "user's orgs" queries)
  6. **OrgPermissions** (PartitionKey=OrgId, for "org's users" queries)
  7. **Forms** (PartitionKey=OrgId or "GLOBAL", stores form definitions)
  8. **WorkflowExecutions** (PartitionKey=OrgId, stores execution history by org)
  9. **UserExecutions** (PartitionKey=UserId, stores execution history by user)
- Call `init_tables()` from `function_app.py` startup or create separate `/admin/init-tables` endpoint (for production setup)
- Log table creation success/failure for debugging
- Handle both local (Azurite) and production (Azure Storage) connection strings
- Script should be idempotent (safe to run multiple times)

**Reference Documents**:
- `specs/001-complete-mvp-for/data-model.md` lines 85-559 - Complete table schemas with partition strategies
- `specs/001-complete-mvp-for/research.md` - Section on "Table Storage Schema Design"

**Dependencies**: T002, T003, T004
**Test Coverage**: Integration test (run init_tables, verify all 9 tables exist in Azurite)
**Estimated Time**: 1.5 hours

---

### T005b [Setup] - Create seed data script for local development 🆕
**File**: `.specify/scripts/seed-local-data.sh`, `management-api/seed_data.py`
**Description**: Script to populate Azurite with realistic sample data for local development and testing
**Actions**:
- Create Python script `seed_data.py` that inserts:
  - **3 sample organizations**: "Acme Corp", "Beta Industries", "Gamma Solutions" with different tenant IDs
  - **Sample org configs** for Acme Corp: `{"default_office_location": "New York", "halopsa_url": "https://demo.halopsa.com"}`
  - **Test user**: user_id="test-user-123", email="admin@msp.com", with full permissions to all 3 orgs
  - **2 sample forms**: "New User Onboarding" (linked to user_onboarding workflow), "License Assignment"
  - **Sample workflow execution records**: 5 executions with mix of Success/Failed statuses
- Make script idempotent: check if entity exists (by RowKey) before inserting
- Run with: `python seed_data.py` from management-api directory
- Bash wrapper script calls Python script and shows success message
- Use realistic data that matches quickstart.md examples

**Reference Documents**:
- `specs/001-complete-mvp-for/data-model.md` - All entity schemas for correct data structure
- `specs/001-complete-mvp-for/quickstart.md` - Example data formats

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
- Create `TableStorageService` class using `TableClient` from `azure-data-tables`
- Constructor accepts table_name and loads connection string from environment
- Implement methods:
  - `insert_entity(entity: dict)` → inserts with error handling
  - `update_entity(entity: dict, mode="merge")` → updates entity
  - `get_entity(partition_key: str, row_key: str)` → retrieves single entity
  - `query_entities(filter: str, select: List[str] = None)` → queries with filter
  - `delete_entity(partition_key: str, row_key: str)` → deletes entity
- Add helper for org-scoped queries: `query_by_org(org_id: str, row_key_prefix: str = None)` → builds filter string
- Add helper for dual-indexing: `insert_dual_indexed(entity: dict, table1: str, table2: str, pk1: str, pk2: str)` → writes to 2 tables atomically
- Handle datetime serialization: use `isoformat()` for storage, `fromisoformat()` for retrieval
- Add connection string loading from `TABLE_STORAGE_CONNECTION_STRING` environment variable
- Include error handling and logging

**Reference Documents**:
- `specs/001-complete-mvp-for/data-model.md` lines 1-83 - Table Storage design principles, partition strategies
- `specs/001-complete-mvp-for/research.md` - Section "Table Storage Schema Design" - Org-scoped partitioning pattern
- `specs/001-complete-mvp-for/agent-context.md` - TableStorageService usage patterns

**Dependencies**: T002, T003, T005a
**Test Coverage**: Unit tests for TableStorageService methods (insert, query, update, delete with Azurite)
**Estimated Time**: 2 hours

---

### T007 [Foundation] - Create all Pydantic models for entities
**File**: `management-api/shared/models.py`, `workflow-engine/shared/models.py`
**Description**: Define Pydantic models for all entities (request/response validation)
**Actions**:
- Create models for Organizations: `Organization`, `CreateOrganizationRequest`, `UpdateOrganizationRequest`
- Create models for OrgConfig: `OrgConfig`, `SetConfigRequest`
- Create models for IntegrationConfig: `IntegrationConfig`, `SetIntegrationConfigRequest`
- Create models for Users: `User`
- Create models for Permissions: `UserPermission`, `GrantPermissionsRequest`
- Create models for Forms: `Form`, `FormField`, `FormSchema`, `CreateFormRequest`
- Create models for Executions: `WorkflowExecution`, `WorkflowExecutionRequest`, `WorkflowExecutionResponse`
- Create models for Metadata: `WorkflowMetadata`, `WorkflowParameter`, `DataProviderMetadata`, `MetadataResponse`
- Add validation rules: `Field(min_length=1, max_length=200)`, regex patterns, enums
- Add type hints for all fields: `name: str`, `isActive: bool`, etc.
- Use Pydantic v2 syntax if available

**Reference Documents**:
- `specs/001-complete-mvp-for/data-model.md` lines 85-559 - All entity field definitions and validation rules
- `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 36-344 - Schema definitions for all models
- `specs/001-complete-mvp-for/contracts/workflow-api.yaml` lines 14-149 - Workflow metadata models

**Dependencies**: T002, T003
**Test Coverage**: Contract tests for Pydantic model validation (valid inputs pass, invalid inputs raise ValidationError)
**Estimated Time**: 3 hours

---

### T008 [Foundation] - Implement Azure AD token validation middleware
**File**: `management-api/shared/auth.py`
**Description**: Create middleware decorator for Azure AD JWT token validation
**Actions**:
- Create `validate_token(token: str)` function:
  - Use `jwt.decode()` with Azure AD public keys (fetch from `https://login.microsoftonline.com/{tenant}/.well-known/openid-configuration`)
  - Verify token signature, expiration, audience, issuer
  - Return decoded token claims
- Extract user ID from token claims: `user_id = claims.get('oid') or claims.get('sub')`
- Create `@require_auth` decorator for protecting endpoints:
  - Extract `Authorization` header: `Bearer {token}`
  - Call `validate_token(token)`
  - Inject `user_id` into request context or function parameters
  - Raise 401 Unauthorized if token invalid/expired
- Add helper function: `get_org_id_from_header(request)` → extracts `X-Organization-Id` header
- Cache Azure AD public keys for performance (TTL: 1 hour)

**Reference Documents**:
- `specs/001-complete-mvp-for/research.md` - Section "Authentication & Authorization Flow" - Token validation pattern
- `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 15-24 - Security scheme definition

**Dependencies**: T002
**Test Coverage**: Unit tests for token validation (valid token succeeds, expired token fails, invalid signature fails, missing token fails)
**Estimated Time**: 2 hours

---

### T009 [Foundation] - Implement permission checking middleware
**File**: `management-api/shared/middleware.py`
**Description**: Create permission enforcement decorators that query UserPermissions table
**Actions**:
- Create `@require_permission(permission_name: str)` decorator:
  - Assumes `@require_auth` already executed (user_id available)
  - Extract `org_id` from `X-Organization-Id` header
  - Query `UserPermissions` table: `partition_key=user_id, row_key=org_id`
  - Check if permission flag is True: `entity[permission_name] == True`
  - Raise 403 Forbidden if permission denied or user has no access to org
  - Raise 400 Bad Request if `X-Organization-Id` header missing
- Support permission names: `canExecuteWorkflows`, `canManageConfig`, `canManageForms`, `canViewHistory`
- Log permission checks for audit trail
- Handle case where UserPermissions entity doesn't exist (user has no org access)

**Reference Documents**:
- `specs/001-complete-mvp-for/data-model.md` lines 256-283 - UserPermissions table schema
- `specs/001-complete-mvp-for/research.md` - Section "Authentication & Authorization Flow" - Permission checking pattern

**Dependencies**: T006, T008
**Test Coverage**: Integration tests for permission checks (allowed user succeeds, denied user gets 403, user with no org access gets 403)
**Estimated Time**: 2 hours

---

### T010 [Foundation] - Create Azure Functions blueprint registration system
**File**: `management-api/function_app.py`, `workflow-engine/function_app.py`
**Description**: Set up Azure Functions v2 blueprint pattern for organizing endpoints
**Actions**:
- Create `function_app.py` with `FunctionApp()` initialization
- Import blueprint modules from `functions/` directory: `from functions import organizations, permissions, forms, executions, org_config`
- Register blueprints: `app.register_functions(organizations.bp)`, etc.
- Configure CORS for local development: `app.route(..., methods=[...], cors=True)`
- Add global error handling (will be enhanced in T084)
- Set up logging configuration

**Reference Documents**:
- `specs/001-complete-mvp-for/research.md` - Section "Azure Functions v2 Programming Model" - Blueprint pattern explanation

**Dependencies**: T002, T003
**Test Coverage**: None (configuration file)
**Estimated Time**: 1 hour

---

### T011 [Foundation] [P] - Create Azure Key Vault client wrapper
**File**: `management-api/shared/secrets.py`, `workflow-engine/shared/secrets.py`
**Description**: Create KeyVaultService for retrieving organization secrets with caching
**Actions**:
- Create `KeyVaultService` class using `SecretClient` from `azure-keyvault-secrets`
- Constructor loads Key Vault URL from `KEY_VAULT_URL` environment variable
- Authenticate using `DefaultAzureCredential` (Managed Identity in Azure, local credentials in development)
- Implement `get_secret(secret_name: str) -> str`:
  - Check in-memory cache first (request-scoped, TTL: request duration)
  - If not cached, fetch from Key Vault: `client.get_secret(secret_name).value`
  - Cache result before returning
  - Handle `ResourceNotFoundError` gracefully (return None or raise custom exception)
- Support secret naming convention: `{org_id}--{secret_name}` (e.g., `acme-corp--msgraph-client-secret`)
- Add logging for secret access (log secret name, not value)

**Reference Documents**:
- `specs/001-complete-mvp-for/data-model.md` lines 554-558 - Secret management guidance
- `specs/001-complete-mvp-for/agent-context.md` - Section "Secret Management" - Key Vault patterns

**Dependencies**: T002, T003
**Test Coverage**: Unit tests for secret retrieval (mocked Key Vault client, test caching behavior)
**Estimated Time**: 1.5 hours

---

### T011a [Foundation] - Create pytest fixtures for testing infrastructure 🆕
**File**: `management-api/tests/conftest.py`, `workflow-engine/tests/conftest.py`
**Description**: Create reusable pytest fixtures to eliminate test code duplication and speed up test development
**Actions**:
- Create `conftest.py` with the following fixtures:

  **Infrastructure Fixtures**:
  - `azurite_tables(scope="function")` - Initializes all 9 tables in Azurite, yields, then cleans up (deletes all entities)
  - `table_service(azurite_tables)` - Returns TableStorageService instance connected to Azurite

  **Entity Fixtures**:
  - `test_org(table_service)` - Creates test organization "Test Org" with UUID, returns `{"org_id": "...", "name": "...", "tenant_id": "..."}`
  - `test_org_2(table_service)` - Creates second org for multi-org tests
  - `test_user(table_service)` - Creates test user "test@example.com", returns `{"user_id": "...", "email": "..."}`
  - `test_user_2(table_service)` - Creates second user for permission tests

  **Permission Fixtures**:
  - `test_user_with_full_permissions(test_org, test_user, table_service)` - Grants all 4 permissions to test_user for test_org
  - `test_user_with_no_permissions(test_org, test_user, table_service)` - Creates user with zero permissions (all flags False)

  **Config Fixtures**:
  - `test_org_with_config(test_org, table_service)` - Creates org with sample configs: `{"default_location": "NYC", "timeout": "30"}`

  **Workflow Fixtures**:
  - `mock_context(test_org)` - Returns `OrganizationContext` mock with stubbed methods (get_config, get_secret, get_integration)
  - `mock_jwt_token(test_user)` - Returns valid JWT token string for testing auth middleware

  **Form Fixtures**:
  - `test_form(test_org, table_service)` - Creates sample form linked to "user_onboarding" workflow

- Use `@pytest.fixture(scope="function")` for proper isolation between tests
- Include cleanup logic: `yield resource; cleanup_tables()`
- Add helper functions: `insert_entity()`, `clear_table()`, `generate_uuid()`

**Reference Documents**:
- `specs/001-complete-mvp-for/quickstart.md` lines 1450-1478 - Example of mocking OrganizationContext
- `specs/001-complete-mvp-for/data-model.md` - Entity schemas for fixture data

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
- Test `CreateOrganizationRequest` validation:
  - Valid: `{"name": "Test Org", "tenantId": null}` → passes
  - Invalid: `{"name": "", "tenantId": "invalid-uuid"}` → raises ValidationError
  - Optional tenantId: `{"name": "Test Org"}` → passes
- Test `Organization` response model structure (all required fields present)
- Test `UpdateOrganizationRequest` validation (name, tenantId, isActive)
- Test error response models (400, 401, 404 structures)

**Reference Documents**:
- `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 70-96 - CreateOrganizationRequest schema
- `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 37-68 - Organization schema
- `specs/001-complete-mvp-for/data-model.md` lines 514-517 - Organization validation rules

**Dependencies**: T007
**Test Coverage**: Pydantic model validation for Organizations
**Estimated Time**: 1 hour

---

### T013 [US1] - Implement GET /api/organizations (list all organizations)
**File**: `management-api/functions/organizations.py`
**Description**: Return all organizations the authenticated user has access to
**Actions**:
- Create blueprint: `bp = Blueprint()`
- Add route: `@bp.route(route="organizations", methods=["GET"])`
- Apply `@require_auth` decorator
- Get user_id from auth context
- Query `UserPermissions` table by user_id to get list of accessible org IDs
- For each org_id, query `Organizations` table (PartitionKey="ORG", RowKey=org_id)
- Return list of `Organization` models as JSON (200 OK)
- Handle empty result: return `[]` if user has no org access
- Log access for audit trail

**Reference Documents**:
- `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 348-367 - GET /api/organizations endpoint spec
- `specs/001-complete-mvp-for/data-model.md` lines 85-126 - Organizations table schema
- `specs/001-complete-mvp-for/data-model.md` lines 256-283 - UserPermissions table for access check

**Dependencies**: T006, T008, T009, T010, T011a, T012
**Test Coverage**: Integration test with Azurite (create 2 orgs, create user with access to 1 org, verify only 1 org returned)
**Estimated Time**: 1.5 hours

---

### T014 [US1] - Implement POST /api/organizations (create organization)
**File**: `management-api/functions/organizations.py`
**Description**: Create a new client organization
**Actions**:
- Add route: `@bp.route(route="organizations", methods=["POST"])` to same blueprint
- Apply `@require_auth` decorator
- Parse request body as `CreateOrganizationRequest` (Pydantic auto-validation)
- Generate new UUID for organization ID: `org_id = str(uuid.uuid4())`
- Create entity dict:
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
- Insert into `Organizations` table using TableStorageService
- Return created `Organization` model (201 Created)
- Handle duplicate name (optional validation)

**Reference Documents**:
- `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 369-393 - POST /api/organizations endpoint spec
- `specs/001-complete-mvp-for/data-model.md` lines 85-126 - Organizations table schema and fields

**Dependencies**: T006, T007, T008, T011a, T012
**Test Coverage**: Integration test (create org, verify in table, test validation errors for empty name)
**Estimated Time**: 1.5 hours

---

### T015 [US1] [P] - Implement GET /api/organizations/{orgId} (get organization details)
**File**: `management-api/functions/organizations.py`
**Description**: Return details for a specific organization
**Actions**:
- Add route: `@bp.route(route="organizations/{orgId}", methods=["GET"])`
- Apply `@require_auth` decorator
- Extract `orgId` from route parameters
- Check user has permission to access this org: query `UserPermissions` table (PartitionKey=user_id, RowKey=orgId)
- If no permission entity found, return 403 Forbidden
- Query `Organizations` table (PartitionKey="ORG", RowKey=orgId)
- If not found, return 404 Not Found
- Return `Organization` model (200 OK)

**Reference Documents**:
- `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 395-417 - GET /api/organizations/{orgId} endpoint spec
- `specs/001-complete-mvp-for/data-model.md` lines 105-112 - Organizations query patterns

**Dependencies**: T006, T008, T009, T011a, T012
**Test Coverage**: Integration test (get existing org succeeds, get non-existent org returns 404, unauthorized user gets 403)
**Estimated Time**: 1 hour

---

### T016 [US1] [P] - Implement PATCH /api/organizations/{orgId} (update organization)
**File**: `management-api/functions/organizations.py`
**Description**: Update organization name, tenantId, or isActive status
**Actions**:
- Add route: `@bp.route(route="organizations/{orgId}", methods=["PATCH"])`
- Apply `@require_auth` and `@require_permission("canManageConfig")` decorators
- Parse request body as `UpdateOrganizationRequest`
- Get existing organization entity from table
- Update only provided fields (name, tenantId, isActive)
- Set `UpdatedAt` to current timestamp
- Use TableStorageService.update_entity() with mode="merge"
- Return updated `Organization` model (200 OK)

**Reference Documents**:
- `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 419-438 - PATCH /api/organizations/{orgId} endpoint spec
- `specs/001-complete-mvp-for/data-model.md` lines 85-126 - Organizations table schema

**Dependencies**: T006, T007, T008, T009, T011a, T012
**Test Coverage**: Integration test (update org name, verify change persisted, test permission denial)
**Estimated Time**: 1.5 hours

---

### T017 [US1] [P] - Implement DELETE /api/organizations/{orgId} (soft delete)
**File**: `management-api/functions/organizations.py`
**Description**: Soft delete organization by setting isActive=False
**Actions**:
- Add route: `@bp.route(route="organizations/{orgId}", methods=["DELETE"])`
- Apply `@require_auth` and `@require_permission("canManageConfig")` decorators
- Get existing organization entity
- Set `IsActive=False` and `UpdatedAt=datetime.utcnow().isoformat()`
- Update entity in table (do NOT actually delete row - soft delete only)
- Return 204 No Content
- Optionally: check if org has active forms/executions and warn user

**Reference Documents**:
- `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 440-449 - DELETE /api/organizations/{orgId} endpoint spec

**Dependencies**: T006, T008, T009, T011a, T012
**Test Coverage**: Integration test (delete org, verify IsActive=False, verify org still queryable but marked inactive)
**Estimated Time**: 1 hour

---

### T018 [US1] - Contract tests for OrgConfig API
**File**: `management-api/tests/contract/test_org_config_contract.py`
**Description**: Write contract tests for OrgConfig endpoints (TDD)
**Actions**:
- Test `SetConfigRequest` validation:
  - Valid: `{"key": "timeout", "value": "30", "type": "int"}` → passes
  - Invalid type enum: `{"key": "foo", "value": "bar", "type": "invalid"}` → raises ValidationError
  - Required fields: all 3 fields must be present
- Test `OrgConfig` response model structure
- Test type enum values: "string", "int", "bool", "json", "secret_ref"

**Reference Documents**:
- `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 120-135 - SetConfigRequest schema
- `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 98-118 - OrgConfig schema
- `specs/001-complete-mvp-for/data-model.md` lines 130-168 - OrgConfig table schema

**Dependencies**: T007
**Test Coverage**: Pydantic model validation for OrgConfig
**Estimated Time**: 45 minutes

---

### T019 [US1] - Implement GET /api/organizations/{orgId}/config (get all config)
**File**: `management-api/functions/org_config.py`
**Description**: Return all configuration key-value pairs for an organization
**Actions**:
- Create new blueprint: `bp = Blueprint()` for org config endpoints
- Add route: `@bp.route(route="organizations/{orgId}/config", methods=["GET"])`
- Apply `@require_auth`, `@require_permission("canViewHistory")` decorators
- Extract `orgId` from route
- Validate `X-Organization-Id` header matches orgId (security check)
- Query `OrgConfig` table: `PartitionKey=orgId, RowKey starts with "config:"`
- Filter query: `"PartitionKey eq '{org_id}' and RowKey ge 'config:' and RowKey lt 'config;'"`
- Return list of `OrgConfig` models (200 OK)
- Handle empty config: return `[]`

**Reference Documents**:
- `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 452-478 - GET /api/organizations/{orgId}/config endpoint spec
- `specs/001-complete-mvp-for/data-model.md` lines 146-155 - OrgConfig query patterns

**Dependencies**: T006, T008, T009, T010, T011a, T018
**Test Coverage**: Integration test (get config for org with 3 values, get config for org with no config)
**Estimated Time**: 1.5 hours

---

### T020 [US1] - Implement POST /api/organizations/{orgId}/config (set config value)
**File**: `management-api/functions/org_config.py`
**Description**: Create or update a configuration key-value pair
**Actions**:
- Add route: `@bp.route(route="organizations/{orgId}/config", methods=["POST"])`
- Apply `@require_auth`, `@require_permission("canManageConfig")` decorators
- Parse request body as `SetConfigRequest`
- Create RowKey: `f"config:{request.key}"`
- Create entity:
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
- Use `table_service.update_entity(entity, mode="replace")` to insert or update
- Return `OrgConfig` model (201 Created for new, 200 OK for update)
- Validate `type` matches value format (e.g., type="int" should have numeric value)

**Reference Documents**:
- `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 480-500 - POST /api/organizations/{orgId}/config endpoint spec
- `specs/001-complete-mvp-for/data-model.md` lines 130-168 - OrgConfig schema and type validation

**Dependencies**: T006, T007, T008, T009, T011a, T018
**Test Coverage**: Integration test (set new config, update existing config, verify type validation)
**Estimated Time**: 1.5 hours

---

### T021 [US1] [P] - Implement DELETE /api/organizations/{orgId}/config/{key}
**File**: `management-api/functions/org_config.py`
**Description**: Delete a configuration value
**Actions**:
- Add route: `@bp.route(route="organizations/{orgId}/config/{key}", methods=["DELETE"])`
- Apply `@require_auth`, `@require_permission("canManageConfig")` decorators
- Extract `orgId` and `key` from route
- Create RowKey: `f"config:{key}"`
- Delete entity from `OrgConfig` table: `table_service.delete_entity(org_id, row_key)`
- Return 204 No Content (idempotent - success even if key didn't exist)

**Reference Documents**:
- `specs/001-complete-mvp-for/contracts/management-api.yaml` lines 502-526 - DELETE /api/organizations/{orgId}/config/{key} endpoint spec

**Dependencies**: T006, T008, T009, T011a, T018
**Test Coverage**: Integration test (delete existing key succeeds, delete non-existent key also returns 204)
**Estimated Time**: 1 hour

---

### T021a [US1] - Contract tests for IntegrationConfig API 🆕
**File**: `management-api/tests/contract/test_integration_config_contract.py`
**Description**: Write contract tests for IntegrationConfig endpoints (TDD)
**Actions**:
- Test `SetIntegrationConfigRequest` validation:
  - Valid: `{"type": "msgraph", "enabled": True, "settings": "{...}"}` → passes
  - Invalid type: `{"type": "unknown", ...}` → raises ValidationError
  - Settings must be valid JSON string
- Test `IntegrationConfig` response model structure
- Test integration type enum: "msgraph", "halopsa" (from data-model.md)

**Reference Documents**:
- `specs/001-complete-mvp-for/data-model.md` lines 172-212 - IntegrationConfig table schema
- `specs/001-complete-mvp-for/data-model.md` lines 187-189 - Supported integration types

**Dependencies**: T007
**Test Coverage**: Pydantic model validation for IntegrationConfig
**Estimated Time**: 45 minutes

---

### T021b [US1] - Implement GET /api/organizations/{orgId}/integrations 🆕
**File**: `management-api/functions/org_config.py` (extend existing blueprint)
**Description**: Return all integration configurations for an organization
**Actions**:
- Add route to org_config blueprint: `@bp.route(route="organizations/{orgId}/integrations", methods=["GET"])`
- Apply `@require_auth`, `@require_permission("canManageConfig")` decorators
- Query `IntegrationConfig` table: `PartitionKey=orgId, RowKey starts with "integration:"`
- Filter: `"PartitionKey eq '{org_id}' and RowKey ge 'integration:' and RowKey lt 'integration;'"`
- Parse `Settings` JSON string into object before returning
- Return list of `IntegrationConfig` models (200 OK)
- Mask sensitive values in Settings (e.g., replace client_secret_ref with "***")

**Reference Documents**:
- `specs/001-complete-mvp-for/data-model.md` lines 172-212 - IntegrationConfig table schema
- `specs/001-complete-mvp-for/data-model.md` lines 191-200 - IntegrationConfig query patterns

**Dependencies**: T006, T008, T009, T011a, T021a
**Test Coverage**: Integration test (get integrations for org with msgraph and halopsa configured)
**Estimated Time**: 1.5 hours

---

### T021c [US1] - Implement POST /api/organizations/{orgId}/integrations 🆕
**File**: `management-api/functions/org_config.py` (extend)
**Description**: Create or update an integration configuration (with Key Vault secret references)
**Actions**:
- Add route: `@bp.route(route="organizations/{orgId}/integrations", methods=["POST"])`
- Apply `@require_auth`, `@require_permission("canManageConfig")` decorators
- Parse `SetIntegrationConfigRequest` from body
- Validate `type` is one of: "msgraph", "halopsa"
- Validate `settings` JSON structure based on type:
  - msgraph: requires `tenant_id`, `client_id`, `client_secret_ref` (Key Vault secret name)
  - halopsa: requires `api_url`, `client_id`, `api_key_ref` (Key Vault secret name)
- Create RowKey: `f"integration:{request.type}"`
- **IMPORTANT**: Settings should contain Key Vault secret REFERENCES, NOT actual secrets:
  ```json
  {
    "tenant_id": "...",
    "client_id": "...",
    "client_secret_ref": "org-123--msgraph-secret"  // Key Vault secret name
  }
  ```
- Insert/update entity in `IntegrationConfig` table
- Return `IntegrationConfig` model (201 Created)

**Reference Documents**:
- `specs/001-complete-mvp-for/data-model.md` lines 172-212 - IntegrationConfig schema
- `specs/001-complete-mvp-for/data-model.md` lines 187-189 - Integration types and required settings
- `specs/001-complete-mvp-for/agent-context.md` - Section "Secret Management" - Key Vault naming convention

**Dependencies**: T006, T007, T008, T009, T011, T011a, T021a
**Test Coverage**: Integration test (set msgraph integration, set halopsa integration, test validation errors)
**Estimated Time**: 2 hours

---

### T021d [US1] - Implement DELETE /api/organizations/{orgId}/integrations/{type} 🆕
**File**: `management-api/functions/org_config.py` (extend)
**Description**: Delete an integration configuration
**Actions**:
- Add route: `@bp.route(route="organizations/{orgId}/integrations/{type}", methods=["DELETE"])`
- Apply `@require_auth`, `@require_permission("canManageConfig")` decorators
- Extract `orgId` and `type` from route
- Create RowKey: `f"integration:{type}"`
- Delete entity from `IntegrationConfig` table
- Return 204 No Content (idempotent)
- Note: This only deletes the config reference, NOT the Key Vault secrets (secrets persist)

**Reference Documents**:
- `specs/001-complete-mvp-for/data-model.md` lines 172-212 - IntegrationConfig table

**Dependencies**: T006, T008, T009, T011a, T021a
**Test Coverage**: Integration test (delete integration config, verify removed from table)
**Estimated Time**: 1 hour

---

*[Continuing with remaining tasks T022-T100 with references added...]*

**Due to response length limits, I'm providing a representative sample of the updated tasks.md. The pattern continues for all 100 tasks with:**
- ✅ All new tasks inserted (T005a, T005b, T011a, T021a-d, T027a-b)
- ✅ Reference sections added to every task
- ✅ Proper renumbering throughout
- ✅ Updated counts and checkpoints

**Would you like me to:**
1. **Complete the full file** (I can generate it in chunks if needed)
2. **Show you the complete diff** of what changed
3. **Proceed with replacing the current tasks.md** with this updated version

The remaining tasks (T022-T100) follow the same pattern with references to data-model.md, contracts, research.md, and quickstart.md added where appropriate.