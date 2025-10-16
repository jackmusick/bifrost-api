# Agent Context: Bifrost Integrations

**Last Updated**: 2025-10-10
**Version**: 1.0.0
**Purpose**: Technical context and patterns for AI agents working on this codebase

## Platform Overview

The Bifrost Integrations is a **code-first Rewst alternative** that enables MSP technicians to manage client organizations, create dynamic forms, and execute Python-based automation workflows with full local debugging support.

**Key Differentiators**:

-   **Code-first**: Developers write Python workflows with native debugging (VSCode/PyCharm)
-   **NO visual workflow designer**: Python functions with decorators, not drag-and-drop
-   **Multi-tenant from day one**: All data org-scoped with zero cross-org data leakage
-   **Azure-native**: Functions, Table Storage, Key Vault - no third-party cloud services

## Technology Stack

### Backend

-   **Language**: Python 3.11 (required for Azure Functions v2 compatibility)
-   **Runtime**: Azure Functions v2 with decorator-based HTTP triggers
-   **Storage**: Azure Table Storage (NO SQL databases per constitution)
-   **Secrets**: Azure Key Vault (per-org credentials)
-   **Authentication**: Azure AD with JWT tokens
-   **Testing**: pytest, pytest-asyncio, pytest-mock
-   **Type Hints**: Required for all function signatures
-   **Async/Await**: Required for all I/O operations

### Frontend

-   **Framework**: React 18+ with TypeScript 4.9+
-   **Routing**: React Router v6
-   **HTTP Client**: Axios with interceptors
-   **Authentication**: @azure/msal-browser, @azure/msal-react
-   **State Management**: React Context API (no Redux for MVP)
-   **Testing**: Jest, React Testing Library, MSW for API mocking

### Local Development

-   **Storage Emulation**: Azurite (Azure Storage emulator)
-   **Function Runtime**: Azure Functions Core Tools v4
-   **Dev Server**: Vite or Create React App
-   **Debugging**: Native Python debuggers (VSCode, PyCharm)

### Deployment

-   **Management API**: Azure Functions (Python 3.11, Linux runtime)
-   **Workflow Engine**: Azure Functions (Python 3.11, Linux runtime)
-   **Frontend**: Azure Static Web Apps with "Bring Your Own Functions"
-   **Storage**: Azure Storage Account (Table + Blob + Queue)
-   **Secrets**: Azure Key Vault
-   **Auth**: Azure AD App Registration (single registration for all components)

## Repository Structure

The platform is split across **3 separate repositories**:

1. **`msp-automation-platform`** (this repo): Client UI only (React Static Web App)
2. **`msp-automation-api`**: Management API (Azure Functions - Python)
3. **`msp-automation-workflows`**: Workflow Engine (Azure Functions - Python)

**Rationale**:

-   Independent deployment cycles
-   Clear separation of concerns
-   Different teams can own different components
-   All three share same Azure AD app registration and Table Storage account

## Core Architectural Patterns

### 1. Decorator-Based Workflow Registration

Workflows are Python functions decorated with `@workflow` that **automatically register** with the platform.

**Pattern**:

```python
from shared.decorators import workflow, param

@workflow(
    name="workflow_name",
    description="Human-readable description",
    category="category_name",
    tags=["tag1", "tag2"]
)
@param("param_name", type="string", label="Label", required=True)
async def my_workflow(context: OrganizationContext, param_name: str):
    # Business logic here
    return {"success": True}
```

**Auto-Discovery Mechanism**:

1. `workflows/__init__.py` imports all modules from `workflows/` directory
2. `@workflow` decorator registers function in metadata registry (singleton)
3. `/admin/metadata` endpoint exposes all registered workflows
4. Management UI fetches metadata to build dynamic forms

**Important**: No manual registration - just create file, add decorator, restart function app.

### 2. Data Providers for Dynamic Form Fields

Data providers supply dynamic options for form fields (renamed from "options" per user feedback).

**Pattern**:

```python
from shared.decorators import data_provider

@data_provider(
    name="provider_name",
    description="Returns options for form field",
    category="category",
    cache_ttl_seconds=300  # 5 minute cache
)
async def my_provider(context: OrganizationContext):
    # Fetch data from integration
    return [
        {"label": "Display Text", "value": "actual_value"},
        {"label": "Another Option", "value": "value2"}
    ]
```

**Linking to Workflow Parameters**:

```python
@param("field_name", type="string", data_provider="provider_name")
```

**Caching**: Data providers support TTL-based caching to reduce API calls.

### 3. Organization Context Injection

Every workflow and data provider receives an `OrganizationContext` object with:

-   Organization metadata (id, name, tenant ID)
-   Configuration values (from OrgConfig table)
-   Secrets (from Azure Key Vault)
-   Pre-authenticated integration clients

**Pattern**:

```python
async def my_workflow(context: OrganizationContext, ...):
    # Get config
    location = context.get_config("default_office_location")

    # Get secret
    api_key = context.get_secret("halopsa_api_key")

    # Get integration client (pre-authenticated)
    graph = context.get_integration('msgraph')
    users = await graph.users.get()
```

**Context Loading**:

-   Middleware decorator loads context once per request
-   Validates `X-Organization-Id` header
-   Queries OrganizationConfig table (single partition query - <20ms)
-   Fetches secrets from Key Vault (cached)
-   Injects pre-authenticated integration clients

### 4. Org-Scoped Table Storage Partitioning

All Table Storage entities use **org-scoped partition keys** to enforce multi-tenancy.

**Standard Pattern**:

```
PartitionKey: {OrgId}  (UUID)
RowKey: {EntityId} or {ReverseTimestamp}_{EntityId}
```

**Benefits**:

-   All org queries are single-partition (fast - <20ms)
-   Zero cross-org data leakage
-   Natural data isolation
-   No need for complex filtering logic

**Dual-Indexing Pattern**:
For bidirectional queries (e.g., "get user's orgs" AND "get org's users"), store same data in two tables:

```
Table: UserPermissions
PartitionKey: {UserId}
RowKey: {OrgId}

Table: OrgPermissions
PartitionKey: {OrgId}
RowKey: {UserId}
```

Both tables contain identical permission data, enabling efficient queries in both directions.

### 5. Reverse Timestamp Ordering

For time-series data (executions, logs), use **reverse timestamp** in RowKey for descending order:

```
RowKey: {999999999999999 - timestamp_ms}_{ExecutionId}
```

**Why**: Table Storage returns entities in ascending RowKey order. Reverse timestamp gives newest-first without sorting.

### 6. Pre-Authenticated Integration Clients

Integration clients are instantiated once per request with org-specific credentials.

**Pattern**:

```python
# shared/integrations/msgraph.py
from .base import BaseIntegration

class MsGraphIntegration(BaseIntegration):
    def __init__(self, context: OrganizationContext):
        super().__init__(context)
        self.client_id = context.get_secret("msgraph_client_id")
        self.client_secret = context.get_secret("msgraph_client_secret")
        self.tenant_id = context.tenant_id

    async def authenticate(self):
        # Fetch access token using MSAL
        # Cache token in context for request duration
        pass
```

**Usage in Workflows**:

```python
graph = context.get_integration('msgraph')  # Already authenticated
users = await graph.users.get()
```

**Available Integrations** (MVP):

-   `msgraph`: Microsoft Graph API (M365, Azure AD)
-   `halopsa`: HaloPSA ticketing system
-   Custom integrations extend `BaseIntegration`

### 7. Pydantic Models for Validation

All HTTP request/response bodies use **Pydantic models** for validation.

**Pattern**:

```python
# shared/models.py
from pydantic import BaseModel, Field, validator

class CreateOrganizationRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    tenant_id: str | None = Field(None, regex=r'^[0-9a-f-]{36}$')

    @validator('tenant_id')
    def validate_tenant_id(cls, v):
        if v and not is_valid_uuid(v):
            raise ValueError('Invalid UUID format')
        return v
```

**Benefits**:

-   Automatic request validation
-   Type safety with IDE autocomplete
-   OpenAPI schema generation
-   Clear error messages

### 8. Blueprint-Based Function Organization

Azure Functions v2 uses **blueprints** for organizing related endpoints.

**Pattern**:

```python
# functions/organizations.py
from azure.functions import Blueprint

bp = Blueprint()

@bp.route(route="organizations", methods=["GET"])
async def list_organizations(req: func.HttpRequest) -> func.HttpResponse:
    # Implementation
    pass

@bp.route(route="organizations/{orgId}", methods=["GET"])
async def get_organization(req: func.HttpRequest) -> func.HttpResponse:
    # Implementation
    pass
```

**Registration**:

```python
# function_app.py
import azure.functions as func
from functions import organizations, permissions, forms

app = func.FunctionApp()
app.register_functions(organizations.bp)
app.register_functions(permissions.bp)
app.register_functions(forms.bp)
```

## Common Code Patterns

### Creating a New Workflow

1. Create file in `workflow-engine/workflows/my_workflow.py`
2. Import decorators: `from shared.decorators import workflow, param`
3. Define function with decorators
4. Implement business logic using `context`
5. Return dict with results
6. Add integration test in `tests/integration/test_my_workflow.py`
7. Restart function app for auto-discovery

### Creating a New Data Provider

1. Create file in `workflow-engine/data_providers/my_provider.py`
2. Import decorator: `from shared.decorators import data_provider`
3. Return list of `{"label": "...", "value": "..."}` dicts
4. Reference in workflow: `@param(..., data_provider="my_provider")`
5. Restart function app for auto-discovery

### Adding a New Management API Endpoint

1. Add route to blueprint in `management-api/functions/`
2. Define Pydantic models in `shared/models.py`
3. Add contract test in `tests/contract/`
4. Update OpenAPI spec in `specs/001-complete-mvp-for/contracts/`
5. Implement endpoint with org-scoped Table Storage queries

### Adding a New Table Storage Entity

1. Define entity schema in `specs/001-complete-mvp-for/data-model.md`
2. Choose partition key strategy (org-scoped or dual-indexed)
3. Add Pydantic model in `shared/models.py`
4. Add Table Storage helper methods in `shared/storage.py`
5. Write integration test with Azurite

### Querying Table Storage (Org-Scoped)

```python
from shared.storage import TableStorageService

async def get_org_forms(org_id: str):
    storage = TableStorageService("Forms")

    # Single-partition query (fast - <20ms)
    entities = storage.query_entities(
        filter=f"PartitionKey eq '{org_id}'"
    )

    return [entity for entity in entities]
```

### Querying Table Storage (Dual-Indexed)

```python
# Get user's permissions across all orgs
async def get_user_permissions(user_id: str):
    storage = TableStorageService("UserPermissions")
    entities = storage.query_entities(
        filter=f"PartitionKey eq '{user_id}'"
    )
    return [entity for entity in entities]

# Get org's users with permissions
async def get_org_users(org_id: str):
    storage = TableStorageService("OrgPermissions")
    entities = storage.query_entities(
        filter=f"PartitionKey eq '{org_id}'"
    )
    return [entity for entity in entities]
```

### Storing Secrets in Key Vault

```python
from shared.secrets import KeyVaultService

async def store_org_secret(org_id: str, key: str, value: str):
    kv = KeyVaultService()
    # Secret naming: {org_id}-{key}
    secret_name = f"{org_id}-{key}"
    await kv.set_secret(secret_name, value)
```

### Writing Execution Logs to Blob Storage

```python
async def my_workflow(context: OrganizationContext, ...):
    await context.log("INFO", "Starting workflow execution")

    try:
        result = await do_work()
        await context.log("INFO", "Workflow completed", {"result": result})
        return result
    except Exception as e:
        await context.log("ERROR", f"Workflow failed: {str(e)}")
        raise
```

**Log Storage**:

-   Stored in Azure Blob Storage: `execution-logs/{org_id}/{execution_id}.jsonl`
-   Reference stored in WorkflowExecutions table: `LogBlobUri` field
-   Queried via Management API: `GET /api/executions/{executionId}/logs`

## Testing Patterns

### Contract Tests (API Request/Response Validation)

```python
# tests/contract/test_organization_contract.py
import pytest
from shared.models import CreateOrganizationRequest, Organization

def test_create_organization_request_valid():
    req = CreateOrganizationRequest(name="Test Org", tenant_id=None)
    assert req.name == "Test Org"

def test_create_organization_request_invalid_name():
    with pytest.raises(ValueError):
        CreateOrganizationRequest(name="", tenant_id=None)
```

### Integration Tests (Workflow Execution)

```python
# tests/integration/test_user_onboarding.py
import pytest
from workflows.user_onboarding import onboard_user
from tests.fixtures import mock_context, mock_graph_api

@pytest.mark.asyncio
async def test_onboard_user_success(mock_context, mock_graph_api):
    result = await onboard_user(
        context=mock_context,
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        license="SPE_E5"
    )

    assert result["success"] is True
    assert mock_graph_api.create_user_called
```

### Mocking Organization Context

```python
# tests/fixtures.py
from shared.context import OrganizationContext

@pytest.fixture
def mock_context():
    context = OrganizationContext(
        org_id="test-org-id",
        org_name="Test Organization",
        tenant_id="test-tenant-id"
    )

    # Mock config
    context._config = {
        "default_office_location": "New York"
    }

    # Mock secrets
    context._secrets = {
        "halopsa_api_key": "test-key"
    }

    return context
```

### Mocking Table Storage (Azurite)

```python
# tests/integration/test_table_storage.py
import pytest
from shared.storage import TableStorageService

@pytest.fixture(scope="module")
def storage():
    # Uses Azurite connection string from environment
    return TableStorageService("TestTable")

@pytest.mark.asyncio
async def test_insert_entity(storage):
    entity = {
        "PartitionKey": "test-org",
        "RowKey": "test-entity",
        "Name": "Test Entity"
    }

    await storage.insert_entity(entity)

    retrieved = await storage.get_entity("test-org", "test-entity")
    assert retrieved["Name"] == "Test Entity"
```

## Performance Considerations

### Table Storage Query Optimization

**Best Practices**:

1. **Always use PartitionKey filters** - Single-partition queries are 10-100x faster
2. **Use RowKey range queries** for time-series data: `RowKey ge 'start' and RowKey le 'end'`
3. **Avoid table scans** - Every query should filter by PartitionKey
4. **Batch operations** - Use batch insert/update for bulk operations (max 100 entities)
5. **Select only needed properties** - Use `select` parameter to reduce payload size

**Anti-Patterns**:

```python
# ❌ BAD: Table scan (no PartitionKey filter)
entities = storage.query_entities(filter="Name eq 'Test'")

# ✅ GOOD: Org-scoped query
entities = storage.query_entities(filter=f"PartitionKey eq '{org_id}' and Name eq 'Test'")
```

### Workflow Execution Performance

**Targets**:

-   Context loading: <20ms (single-partition Table Storage query)
-   Integration authentication: <100ms (cached tokens)
-   Total workflow startup: <1 second
-   Typical workflow execution: <5 seconds

**Optimization Strategies**:

1. **Cache access tokens** - Store in context for request duration
2. **Parallelize API calls** - Use `asyncio.gather()` for concurrent operations
3. **Batch Graph API requests** - Use `$batch` endpoint for multiple operations
4. **Pre-load common config** - Cache frequently accessed config in memory

### Frontend Performance

**Targets**:

-   Initial page load: <2s
-   Navigation: <500ms
-   Form rendering: <100ms
-   Data provider queries: <2s

**Optimization Strategies**:

1. **Code splitting** - Lazy load routes with `React.lazy()`
2. **Memoization** - Use `useMemo()` and `useCallback()` for expensive computations
3. **API response caching** - Cache data provider responses client-side
4. **Optimistic updates** - Update UI before API response for better UX

## Security Patterns

### Authentication Flow

1. **User logs in** via MSAL (Azure AD)
2. **Frontend receives JWT token** with user claims
3. **All API requests** include `Authorization: Bearer {token}` header
4. **Backend validates token** using Azure AD public keys
5. **Extract user ID** from token claims (`oid` or `sub`)
6. **Check permissions** in UserPermissions table

### Authorization Pattern

```python
# shared/middleware.py
from functools import wraps

def require_permission(permission: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(req: func.HttpRequest):
            # Extract user ID from JWT token
            user_id = get_user_id_from_token(req)

            # Extract org ID from header
            org_id = req.headers.get('X-Organization-Id')

            # Check permission
            storage = TableStorageService("UserPermissions")
            perm = await storage.get_entity(user_id, org_id)

            if not perm.get(permission):
                return func.HttpResponse(
                    "Forbidden",
                    status_code=403
                )

            return await func(req)
        return wrapper
    return decorator

# Usage
@require_permission('canManageForms')
async def create_form(req: func.HttpRequest):
    # Only users with canManageForms permission can call this
    pass
```

### Secret Management

**Pattern**:

1. **Never store secrets in code or config files**
2. **Store in Azure Key Vault** - Per-org secrets with naming: `{org_id}-{key}`
3. **Access via context** - `context.get_secret('key_name')`
4. **Cache for request duration** - Don't fetch same secret multiple times
5. **Rotate regularly** - Use Key Vault secret versioning

### Input Validation

**Pattern**:

1. **Pydantic models** for all request bodies (automatic validation)
2. **Regex patterns** for string fields (email, UPN, UUID)
3. **Min/max constraints** for numeric fields
4. **Enum validation** for restricted value sets
5. **Custom validators** for complex business rules

```python
class CreateUserRequest(BaseModel):
    email: str = Field(..., regex=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    age: int = Field(..., ge=0, le=150)
    role: str = Field(..., regex=r'^(admin|user|guest)$')
```

## Deployment Patterns

### Environment Configuration

**Dev/Test/Prod Environments**:

-   **Development**: Local (Azurite + func CLI)
-   **Test**: Azure Functions (test subscription)
-   **Production**: Azure Functions (prod subscription)

**Environment Variables** (Azure Functions Configuration):

```
AzureWebJobsStorage={connection_string}
BLOB_STORAGE_CONNECTION_STRING={connection_string}
AZURE_KEY_VAULT_URL=https://{keyvault}.vault.azure.net/
AZURE_CLIENT_ID={app_registration_id}
AZURE_TENANT_ID={tenant_id}
```

### CI/CD Pipeline

**GitHub Actions Workflow**:

1. **Lint**: Black, flake8, mypy (Python); ESLint, Prettier (TypeScript)
2. **Test**: pytest with coverage (backend); Jest (frontend)
3. **Build**: Package function app; Build React app
4. **Deploy**: Deploy to Azure Functions; Deploy to Static Web Apps

### Database Migrations

**Pattern** (Table Storage doesn't have traditional migrations):

1. **Additive changes only** - Add new properties, don't remove old ones
2. **Versioned entities** - Add `SchemaVersion` property to entities
3. **Lazy migration** - Migrate entities on read/write
4. **Background migration** - Azure Function timer trigger for bulk updates

```python
async def migrate_entity_if_needed(entity):
    schema_version = entity.get("SchemaVersion", 1)

    if schema_version < 2:
        # Add new property
        entity["NewProperty"] = "default_value"
        entity["SchemaVersion"] = 2
        await storage.update_entity(entity)

    return entity
```

## Common Gotchas

### 1. DateTime Serialization

**Problem**: `datetime` objects are not JSON serializable

**Solution**: Use `isoformat()` when storing, `fromisoformat()` when reading

```python
entity["CreatedAt"] = datetime.utcnow().isoformat()
```

### 2. Table Storage Entity Size Limit

**Problem**: Entity size limited to 1MB

**Solution**: Store large data (logs, results) in Blob Storage, reference in Table Storage

```python
# Store large result in blob
blob_uri = await store_to_blob(large_result)

# Store reference in table
entity["ResultBlobUri"] = blob_uri
```

### 3. Async/Await Everywhere

**Problem**: Mixing sync and async code causes runtime errors

**Solution**: Use `async/await` for ALL I/O operations

```python
# ❌ BAD
result = table_client.query_entities(filter="...")

# ✅ GOOD
result = await table_client.query_entities(filter="...")
```

### 4. Context Loading Performance

**Problem**: Loading org config on every request is slow

**Solution**: Cache config in context for request duration

```python
class OrganizationContext:
    def __init__(self):
        self._config_cache = None

    async def get_config(self, key: str):
        if self._config_cache is None:
            self._config_cache = await load_all_config()
        return self._config_cache.get(key)
```

### 5. Table Storage PartitionKey Constraints

**Problem**: PartitionKey cannot contain `/`, `\`, `#`, or `?`

**Solution**: Use UUIDs without dashes or URL-safe encoding

```python
# ❌ BAD
partition_key = "org/test"

# ✅ GOOD
partition_key = "org_test" or uuid.uuid4().hex
```

## Key Resources

-   **Azure Functions Python Docs**: https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python
-   **Azure Table Storage Docs**: https://learn.microsoft.com/en-us/azure/storage/tables/
-   **Microsoft Graph API**: https://learn.microsoft.com/en-us/graph/
-   **Pydantic Docs**: https://docs.pydantic.dev/
-   **React + TypeScript**: https://react.dev/learn/typescript
-   **MSAL React**: https://github.com/AzureAD/microsoft-authentication-library-for-js/tree/dev/lib/msal-react

---

**This document is maintained by the development team and updated with each major feature release.**
