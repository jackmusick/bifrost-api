# Phase 0: Research & Technology Decisions

**Feature**: Integration Mapping Framework
**Date**: 2025-10-11
**Status**: Complete

## Overview

This document captures technology decisions, best practices, and research findings for implementing the Integration Mapping Framework. The goal is to enable zero-code integration setup by providing a standard contract for integrations to expose organization discovery and mapping functionality.

## Technology Stack (Confirmed)

### Backend
- **Language**: Python 3.11 (Azure Functions v2)
- **Storage**: Azure Table Storage with dual-indexing pattern
- **Secrets**: Azure Key Vault (existing integration credentials)
- **Validation**: Pydantic models for all request/response
- **Testing**: pytest, pytest-asyncio, pytest-mock

### Frontend
- **Framework**: React 18 + TypeScript 4.9+
- **UI Components**: ShadCN UI (existing component library)
- **State Management**: React Query for server state
- **HTTP Client**: Axios with interceptors

### Integration with Existing System
- **Workflow Context**: Extend existing `OrganizationContext` class
- **Decorators**: Use existing decorator pattern for integration registration
- **Permissions**: Leverage existing `canManageConfig` permission
- **API Structure**: Azure Functions blueprints (existing pattern)

## Key Technical Decisions

### 1. Dual-Indexing Strategy for Table Storage

**Decision**: Use two separate tables for bidirectional lookups

**Tables**:
```
OrgIntegrationMappings
├── PartitionKey: {org_id}
├── RowKey: {integration_name}_{mapping_id}
└── Enables: "Get all mappings for organization"

IntegrationMappings
├── PartitionKey: {integration_name}
├── RowKey: {org_id}_{mapping_id}
└── Enables: "Get all orgs using this integration"
```

**Rationale**:
- Single-partition queries (<20ms) in both directions
- No need for expensive cross-partition queries
- Storage cost minimal (~$1/month for 10K mappings)
- Write penalty acceptable (2 writes per operation)
- Follows existing pattern in platform (UserPermissions/OrgPermissions)

**Alternatives Considered**:
- ❌ **Single table with cross-partition queries**: Too slow (100ms+), violates constitution
- ❌ **Composite keys in single table**: Can't efficiently query both directions
- ❌ **Global secondary indexes**: Not supported by Azure Table Storage

### 2. Integration Interface Contract

**Decision**: Python Abstract Base Class (ABC) with required methods

**Interface Methods**:
```python
class IntegrationInterface(ABC):
    @abstractmethod
    def supports_org_mapping(self) -> bool:
        """Returns True if integration supports organization mapping"""

    @abstractmethod
    async def list_organizations(self) -> List[ExternalOrganization]:
        """Discover external organizations from integration API"""

    @abstractmethod
    async def get_client(self, mapping: OrganizationMapping):
        """Get pre-authenticated client for specific org mapping"""

    @abstractmethod
    async def test_connection(self, mapping: OrganizationMapping) -> TestResult:
        """Validate mapping configuration"""
```

**Rationale**:
- **Type safety**: Python type hints enable IDE autocomplete and mypy validation
- **Explicit contract**: Integrations must implement all methods or raise NotImplementedError
- **Backward compatible**: Existing integrations without mapping support return `False` from `supports_org_mapping()`
- **Testable**: Easy to create mocks for integration tests

**Alternatives Considered**:
- ❌ **Protocol (structural typing)**: Less explicit, no enforcement at instantiation
- ❌ **Dictionary-based config**: No type safety, error-prone
- ❌ **Separate mapping adapter classes**: Adds complexity, violates YAGNI

### 3. Caching Strategy for Discovered Organizations

**Decision**: In-memory TTL-based cache with manual refresh

**Implementation**:
```python
@dataclass
class OrganizationCache:
    integration_name: str
    organizations: List[ExternalOrganization]
    cached_at: datetime
    ttl_seconds: int = 3600  # 1 hour default

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.cached_at + timedelta(seconds=self.ttl_seconds)
```

**Rationale**:
- **Reduce API calls**: External systems may have rate limits (e.g., HaloPSA: 100 req/min)
- **Improve UX**: Instant dropdown population (<100ms vs 2-5s API call)
- **Simple invalidation**: Manual refresh button for immediate updates
- **Acceptable staleness**: Organization lists change infrequently (days/weeks)

**Alternatives Considered**:
- ❌ **No caching**: Too slow, wastes API quota
- ❌ **Redis cache**: Over-engineering, adds infrastructure dependency
- ❌ **Table Storage cache**: Too slow for frequent reads (50ms vs <1ms in-memory)
- ❌ **Background refresh**: Complexity not justified for MVP

### 4. Multiple Mappings Per Integration

**Decision**: Support multiple mappings using unique `mapping_id` in RowKey

**RowKey Format**: `{integration_name}_{mapping_id}`

**Example**:
```
Organization: "Acme Corp" (org_id: abc-123)
Mappings:
  - PartitionKey: abc-123, RowKey: microsoft_graph_mapping_001
  - PartitionKey: abc-123, RowKey: microsoft_graph_mapping_002
  - PartitionKey: abc-123, RowKey: halopsa_mapping_001
```

**Rationale**:
- **Real use case**: MSPs manage multiple M365 tenants for single customer
- **Simple implementation**: Just change RowKey from `{integration_name}` to `{integration_name}_{mapping_id}`
- **Future-proof**: No schema changes needed when use case emerges
- **Query pattern**: `get_integration_mapping(integration_name, mapping_id=None)` - requires mapping_id if multiple exist

**Alternatives Considered**:
- ❌ **Single mapping only**: Doesn't support multi-tenant M365 customers
- ❌ **Separate table per integration**: Explosion of tables, hard to query
- ❌ **Array field in single entity**: Table Storage doesn't support efficient array queries

### 5. Workflow Context API Design

**Decision**: Add methods to existing `OrganizationContext` class

**Methods**:
```python
class OrganizationContext:
    # New methods
    async def get_integration_mapping(
        self,
        integration_name: str,
        mapping_id: Optional[str] = None
    ) -> OrganizationMapping:
        """
        Get mapping for this organization.
        Raises MappingNotFoundError if no mapping exists.
        Raises MultipleMappingsError if multiple exist and mapping_id not provided.
        """

    async def set_integration_mapping(
        self,
        integration_name: str,
        external_org_id: str,
        external_org_name: str = "",
        mapping_data: Dict[str, Any] = None,
        mapping_id: Optional[str] = None
    ) -> OrganizationMapping:
        """
        Create or update integration mapping.
        Auto-generates mapping_id if not provided.
        Updates existing mapping if mapping_id matches.
        """
```

**Rationale**:
- **Consistent with existing patterns**: Same approach as `get_config()` and `get_secret()`
- **Context-aware**: Automatically scopes to current organization
- **Type-safe**: Returns Pydantic models with validation
- **Clear errors**: Explicit exceptions for common failures (missing mapping, ambiguous request)

**Alternatives Considered**:
- ❌ **Global service class**: Breaks encapsulation, requires passing org_id everywhere
- ❌ **Separate mapping client**: Adds complexity, doesn't integrate with context
- ❌ **Direct Table Storage access**: Violates abstraction, hard to test

### 6. Permission Model

**Decision**: Reuse existing `canManageConfig` permission

**Rationale**:
- **Semantic fit**: Managing integration mappings is configuration management
- **No new permissions**: Avoids permission sprawl
- **Consistent UX**: Same permission controls org config, secrets, and mappings

**Alternatives Considered**:
- ❌ **New `canManageIntegrations` permission**: Permission sprawl, YAGNI
- ❌ **Integration-specific permissions**: Too granular, complex UI
- ❌ **MSP-admin-only**: Too restrictive, prevents delegation

### 7. Mapping Data Field

**Decision**: Flexible `mapping_data` JSON field for integration-specific config

**Use Cases**:
- **HaloPSA**: Store API base URL, agent ID preferences
- **Microsoft Graph**: Store preferred scopes, resource URLs
- **NinjaRMM**: Store location ID, API region
- **Custom integrations**: Any additional config needed

**Schema** (intentionally flexible):
```python
mapping_data: Dict[str, Any] = {
    "api_base_url": "https://custom.halopsa.com",
    "default_agent_id": "12345",
    "custom_field_mappings": {...}
}
```

**Rationale**:
- **Extensible**: Each integration defines its own schema
- **No core changes**: Adding new integration-specific config doesn't require platform changes
- **Type safety**: Integration class validates its own mapping_data using Pydantic
- **Storage efficient**: JSON serialization in Table Storage

**Alternatives Considered**:
- ❌ **Fixed schema with known fields**: Too rigid, can't support unknown integrations
- ❌ **Separate table per integration**: Explosion of tables
- ❌ **String-based key-value**: Less type-safe than JSON objects

## Integration Discovery Pattern

### list_organizations() Implementation

**Pattern for Integration Developers**:

```python
from shared.integrations.base import IntegrationInterface
from shared.models import ExternalOrganization

class HaloPSAIntegration(IntegrationInterface):
    def supports_org_mapping(self) -> bool:
        return True

    async def list_organizations(self) -> List[ExternalOrganization]:
        """Fetch customers from HaloPSA API"""
        # 1. Get integration credentials from Key Vault
        api_key = self.context.get_secret("halopsa_api_key")
        api_url = self.context.get_config("halopsa_api_url")

        # 2. Call external API
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{api_url}/api/client",
                headers={"Authorization": f"Bearer {api_key}"}
            ) as response:
                clients = await response.json()

        # 3. Transform to standard format
        return [
            ExternalOrganization(
                id=str(client["id"]),
                name=client["name"],
                metadata={"client_code": client.get("code")}
            )
            for client in clients
        ]

    async def get_client(self, mapping: OrganizationMapping):
        """Return pre-authenticated HaloPSA client for this mapping"""
        api_key = self.context.get_secret("halopsa_api_key")
        api_url = mapping.mapping_data.get("api_base_url", "https://api.halopsa.com")

        return HaloPSAClient(
            api_key=api_key,
            api_url=api_url,
            client_id=mapping.external_org_id
        )

    async def test_connection(self, mapping: OrganizationMapping) -> TestResult:
        """Test connection by fetching client details"""
        try:
            client = await self.get_client(mapping)
            details = await client.get_client_details(mapping.external_org_id)

            return TestResult(
                success=True,
                message=f"Successfully connected to {details['name']}",
                details={"client_name": details["name"]}
            )
        except Exception as e:
            return TestResult(
                success=False,
                message=f"Connection failed: {str(e)}",
                details={"error_type": type(e).__name__}
            )
```

**Key Design Points**:
- Uses existing context methods (`get_secret`, `get_config`)
- Returns standard `ExternalOrganization` model
- Async/await for all I/O operations
- Error handling returns TestResult instead of raising exceptions
- Metadata field allows integration-specific extra data

## UI/UX Patterns

### Organizations Page → Integrations Tab

**Component Hierarchy**:
```
Organizations.tsx
└── Tabs
    ├── Details Tab (existing)
    ├── Users Tab (existing)
    └── Integrations Tab (new)
        ├── IntegrationMappingsList.tsx
        │   ├── Table with columns: Integration, External Org, Status, Actions
        │   └── "Add Mapping" button
        ├── CreateMappingDialog.tsx
        │   ├── Integration dropdown (filtered to mapping-enabled)
        │   ├── External org selector (dropdown if discovery supported, text input otherwise)
        │   ├── Mapping data fields (integration-specific)
        │   └── Test Connection button
        ├── EditMappingDialog.tsx (same fields as Create)
        └── TestConnectionDialog.tsx
            ├── Loading spinner during test
            └── Success/error message with details
```

**Data Fetching**:
- **React Query hooks**: `useIntegrationMappings(orgId)`, `useOrganizationDiscovery(integrationName, orgId)`
- **Cache time**: 5 minutes for mappings, 1 hour for discovered orgs
- **Refetch triggers**: After create/update/delete operations
- **Optimistic updates**: Update UI before API response for better UX

### Empty States

**No Mappings**:
```
┌────────────────────────────────────────┐
│  No Integration Mappings               │
│                                        │
│  Map this organization to external     │
│  systems to enable workflow automation │
│                                        │
│  [Add Integration Mapping]             │
└────────────────────────────────────────┘
```

**No Discovery Support**:
```
┌────────────────────────────────────────┐
│  Manual Configuration Required         │
│                                        │
│  This integration doesn't support      │
│  automatic discovery. Enter the        │
│  external organization ID manually.    │
│                                        │
│  External Org ID: [________________]   │
│                                        │
│  Find this ID in the integration's     │
│  admin panel or documentation.         │
└────────────────────────────────────────┘
```

## Error Handling Patterns

### Workflow Errors

**Scenario 1: No Mapping Exists**
```python
# Workflow code
try:
    mapping = await context.get_integration_mapping('halopsa')
except MappingNotFoundError:
    await context.log("error", "No HaloPSA mapping configured for this organization")
    return {"success": False, "error": "Integration not configured"}
```

**Scenario 2: Multiple Mappings Without ID**
```python
try:
    # This will fail if multiple mappings exist
    mapping = await context.get_integration_mapping('microsoft_graph')
except MultipleMappingsError as e:
    await context.log("error", f"Multiple M365 mappings found: {e.mapping_ids}")
    return {"success": False, "error": "Specify which tenant to use"}

# Correct usage
mapping = await context.get_integration_mapping('microsoft_graph', mapping_id='mapping_001')
```

**Scenario 3: Integration Doesn't Support Mapping**
```python
try:
    mapping = await context.get_integration_mapping('custom_integration')
except IntegrationNotFoundError:
    await context.log("error", "Integration 'custom_integration' not found or doesn't support mapping")
    return {"success": False, "error": "Integration not available"}
```

### API Errors

**Validation Errors** (400):
```json
{
  "error": "Validation failed",
  "details": {
    "external_org_id": ["This field is required"],
    "integration_name": ["Integration 'invalid' not found"]
  }
}
```

**Permission Errors** (403):
```json
{
  "error": "Forbidden",
  "message": "canManageConfig permission required to manage integration mappings"
}
```

**Not Found** (404):
```json
{
  "error": "Mapping not found",
  "message": "No mapping found with ID 'mapping_001' for integration 'halopsa'"
}
```

## Performance Optimization

### Query Performance

**Single-Partition Queries** (target: <20ms):
```python
# Get all mappings for org (single partition)
storage = TableStorageService("OrgIntegrationMappings")
entities = await storage.query_entities(
    filter=f"PartitionKey eq '{org_id}'"
)
# Expected: 10-20ms for <100 mappings
```

**Batch Operations**:
```python
# Create mapping in both tables atomically
from azure.data.tables import TableTransactionError

async def create_mapping_dual_indexed(mapping: OrganizationMapping):
    try:
        # Write to both tables in parallel
        await asyncio.gather(
            storage_org.insert_entity(mapping.to_org_entity()),
            storage_int.insert_entity(mapping.to_integration_entity())
        )
    except TableTransactionError:
        # Rollback if either fails
        await cleanup_partial_writes(mapping)
        raise
```

### Frontend Performance

**Code Splitting**:
```typescript
// Lazy load integration mapping components
const IntegrationMappingsList = lazy(() => import('./components/integrations/IntegrationMappingsList'))

// Only load when Integrations tab is selected
<TabsContent value="integrations">
  <Suspense fallback={<LoadingSpinner />}>
    <IntegrationMappingsList orgId={orgId} />
  </Suspense>
</TabsContent>
```

**Debounced Search**:
```typescript
// Debounce search input when filtering discovered orgs
const debouncedSearch = useMemo(
  () => debounce((value: string) => setSearchTerm(value), 300),
  []
)
```

## Security Considerations

### Input Validation

**External Org ID Validation**:
```python
from pydantic import validator

class CreateMappingRequest(BaseModel):
    integration_name: str = Field(..., regex=r'^[a-z_]+$')
    external_org_id: str = Field(..., min_length=1, max_length=200)

    @validator('external_org_id')
    def validate_external_org_id(cls, v):
        # No SQL injection risk (Table Storage), but sanitize for safety
        if any(char in v for char in ['<', '>', '"', "'"]):
            raise ValueError("Invalid characters in external_org_id")
        return v
```

### Permission Checks

**All Endpoints**:
```python
from shared.middleware import require_permission, load_organization_context

@bp.route(route="organizations/{orgId}/integrations", methods=["POST"])
@require_permission('canManageConfig')
@load_organization_context
async def create_mapping(req: func.HttpRequest, context: OrganizationContext):
    # Permission checked before execution
    # Context automatically loaded and validated
    pass
```

### Audit Logging

**All Operations**:
```python
from shared.audit import log_audit_event

async def create_mapping(...):
    mapping = await storage.insert_entity(mapping_entity)

    await log_audit_event(
        event_type="integration_mapping.created",
        org_id=context.org_id,
        user_id=context.user_id,
        details={
            "integration_name": mapping.integration_name,
            "external_org_id": mapping.external_org_id,
            "mapping_id": mapping.id
        }
    )
```

## Testing Strategy

### Contract Tests

**Pydantic Model Validation**:
```python
def test_create_mapping_request_valid():
    req = CreateMappingRequest(
        integration_name="halopsa",
        external_org_id="12345",
        external_org_name="Acme Corp",
        mapping_data={"api_url": "https://acme.halopsa.com"}
    )
    assert req.integration_name == "halopsa"

def test_create_mapping_request_invalid_integration_name():
    with pytest.raises(ValidationError):
        CreateMappingRequest(
            integration_name="Invalid Name!",  # No spaces or special chars
            external_org_id="12345"
        )
```

### Integration Tests

**Full Workflow Test**:
```python
@pytest.mark.asyncio
async def test_workflow_uses_integration_mapping(mock_context, azurite_storage):
    # Setup: Create mapping
    await mock_context.set_integration_mapping(
        integration_name="halopsa",
        external_org_id="12345",
        external_org_name="Acme Corp"
    )

    # Execute: Workflow retrieves mapping
    mapping = await mock_context.get_integration_mapping("halopsa")

    # Assert: Mapping data correct
    assert mapping.external_org_id == "12345"
    assert mapping.external_org_name == "Acme Corp"

    # Execute: Workflow uses integration
    halo = await mock_context.get_integration("halopsa")
    tickets = await halo.list_tickets()  # Uses mapping automatically

    assert len(tickets) > 0
```

**Discovery Test**:
```python
@pytest.mark.asyncio
async def test_list_organizations_with_mock_api(mock_halopsa_api):
    integration = HaloPSAIntegration(mock_context)

    orgs = await integration.list_organizations()

    assert len(orgs) == 3
    assert orgs[0].name == "Acme Corp"
    assert orgs[0].id == "12345"
```

## Migration Considerations

**No Existing Data**: This is a new feature with no migration required.

**Backward Compatibility**:
- Existing integrations without `supports_org_mapping()` return `False`
- Workflows can check if mapping exists before using:
  ```python
  try:
      mapping = await context.get_integration_mapping('halopsa')
  except MappingNotFoundError:
      # Fallback to legacy behavior
      pass
  ```

## Best Practices for Integration Developers

### Implementing Organization Mapping

1. **Return `True` from `supports_org_mapping()`** if your integration can list external orgs
2. **Implement `list_organizations()`** to fetch and transform external org data
3. **Use `mapping_data` for integration-specific config** (API URLs, preferences)
4. **Implement `test_connection()`** to validate mapping configuration
5. **Document required `mapping_data` fields** in integration README

### Example Integration Template

```python
from shared.integrations.base import IntegrationInterface
from shared.models import ExternalOrganization, OrganizationMapping, TestResult
from typing import List

class MyIntegration(IntegrationInterface):
    def supports_org_mapping(self) -> bool:
        return True  # Enable mapping support

    async def list_organizations(self) -> List[ExternalOrganization]:
        # Fetch orgs from external API
        api_key = self.context.get_secret("myintegration_api_key")
        orgs = await self._api_call("/organizations", api_key)

        return [
            ExternalOrganization(
                id=org["id"],
                name=org["name"],
                metadata=org.get("metadata", {})
            )
            for org in orgs
        ]

    async def get_client(self, mapping: OrganizationMapping):
        # Return pre-authenticated client
        api_key = self.context.get_secret("myintegration_api_key")
        return MyIntegrationClient(
            api_key=api_key,
            org_id=mapping.external_org_id,
            config=mapping.mapping_data
        )

    async def test_connection(self, mapping: OrganizationMapping) -> TestResult:
        try:
            client = await self.get_client(mapping)
            await client.ping()
            return TestResult(success=True, message="Connection successful")
        except Exception as e:
            return TestResult(success=False, message=str(e))
```

## Summary

**Key Takeaways**:
1. **Dual-indexing** enables fast bidirectional queries (<20ms)
2. **Abstract base class** provides type-safe integration contract
3. **TTL cache** reduces external API calls while keeping data fresh
4. **Multiple mappings** supported via unique mapping_id in RowKey
5. **OrganizationContext extension** maintains consistency with existing patterns
6. **canManageConfig permission** reused to avoid permission sprawl
7. **Flexible mapping_data** allows integration-specific configuration
8. **Test-first approach** with contract and integration tests

**No Blockers**: All technical decisions align with platform constitution and existing patterns.

**Ready for Phase 1**: Data model and API contracts can now be designed.
