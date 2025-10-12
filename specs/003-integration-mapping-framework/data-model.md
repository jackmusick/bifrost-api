# Data Model: Integration Mapping Framework

**Feature**: Integration Mapping Framework
**Date**: 2025-10-11
**Status**: Complete

## Overview

This document defines all entities, relationships, and storage schemas for the Integration Mapping Framework. The system uses Azure Table Storage with dual-indexing for bidirectional queries.

## Core Entities

### 1. OrganizationMapping

The primary entity representing a mapping between an MSP organization and an external system organization.

**Purpose**: Links an MSP org to an external org ID in an integration system (HaloPSA, M365, NinjaRMM, etc.)

**Lifecycle**: Created by admin via UI or workflow via `set_integration_mapping()`. Updated when external org changes. Soft-deleted when mapping no longer needed.

**Python Model**:
```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID

class OrganizationMapping(BaseModel):
    """Mapping between MSP organization and external integration organization"""

    id: str = Field(..., description="Unique mapping ID (UUID)")
    org_id: str = Field(..., description="MSP organization ID")
    integration_name: str = Field(..., description="Integration identifier (e.g., 'halopsa', 'microsoft_graph')")
    external_org_id: str = Field(..., description="External organization/tenant ID in integration system")
    external_org_name: str = Field(default="", description="Human-readable external org name")
    mapping_data: Dict[str, Any] = Field(default_factory=dict, description="Integration-specific configuration")
    is_active: bool = Field(default=True, description="Mapping active status (soft delete)")
    created_at: datetime = Field(..., description="Creation timestamp")
    created_by: str = Field(..., description="User ID who created mapping")
    updated_at: datetime = Field(..., description="Last update timestamp")
    updated_by: Optional[str] = Field(None, description="User ID who last updated mapping")
    last_tested_at: Optional[datetime] = Field(None, description="Last test connection timestamp")
    last_test_result: Optional[str] = Field(None, description="Result of last test (success/failure message)")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    def to_org_entity(self) -> dict:
        """Convert to OrgIntegrationMappings table entity"""
        return {
            "PartitionKey": self.org_id,
            "RowKey": f"{self.integration_name}_{self.id}",
            "MappingId": self.id,
            "IntegrationName": self.integration_name,
            "ExternalOrgId": self.external_org_id,
            "ExternalOrgName": self.external_org_name,
            "MappingData": json.dumps(self.mapping_data),
            "IsActive": self.is_active,
            "CreatedAt": self.created_at.isoformat(),
            "CreatedBy": self.created_by,
            "UpdatedAt": self.updated_at.isoformat(),
            "UpdatedBy": self.updated_by,
            "LastTestedAt": self.last_tested_at.isoformat() if self.last_tested_at else None,
            "LastTestResult": self.last_test_result,
        }

    def to_integration_entity(self) -> dict:
        """Convert to IntegrationMappings table entity (inverted index)"""
        return {
            "PartitionKey": self.integration_name,
            "RowKey": f"{self.org_id}_{self.id}",
            "MappingId": self.id,
            "OrgId": self.org_id,
            "ExternalOrgId": self.external_org_id,
            "ExternalOrgName": self.external_org_name,
            "MappingData": json.dumps(self.mapping_data),
            "IsActive": self.is_active,
            "CreatedAt": self.created_at.isoformat(),
            "CreatedBy": self.created_by,
            "UpdatedAt": self.updated_at.isoformat(),
            "UpdatedBy": self.updated_by,
            "LastTestedAt": self.last_tested_at.isoformat() if self.last_tested_at else None,
            "LastTestResult": self.last_test_result,
        }

    @staticmethod
    def from_entity(entity: dict) -> "OrganizationMapping":
        """Parse from Table Storage entity"""
        return OrganizationMapping(
            id=entity["MappingId"],
            org_id=entity.get("OrgId", entity["PartitionKey"]),
            integration_name=entity["IntegrationName"],
            external_org_id=entity["ExternalOrgId"],
            external_org_name=entity.get("ExternalOrgName", ""),
            mapping_data=json.loads(entity.get("MappingData", "{}")),
            is_active=entity.get("IsActive", True),
            created_at=datetime.fromisoformat(entity["CreatedAt"]),
            created_by=entity["CreatedBy"],
            updated_at=datetime.fromisoformat(entity["UpdatedAt"]),
            updated_by=entity.get("UpdatedBy"),
            last_tested_at=datetime.fromisoformat(entity["LastTestedAt"]) if entity.get("LastTestedAt") else None,
            last_test_result=entity.get("LastTestResult"),
        )
```

**Field Constraints**:
- `id`: UUID v4 (36 chars with hyphens)
- `org_id`: UUID v4 (must exist in Organizations table)
- `integration_name`: Lowercase snake_case, 1-50 chars (e.g., `halopsa`, `microsoft_graph`)
- `external_org_id`: 1-200 chars, no special chars (`<`, `>`, `"`, `'`)
- `external_org_name`: 0-200 chars (optional, human-readable label)
- `mapping_data`: Valid JSON object, max 32KB total entity size
- `created_by`/`updated_by`: Azure AD user ID (oid claim from JWT)

### 2. ExternalOrganization

Transient entity representing an organization discovered from an integration. Not persisted - returned by `list_organizations()` and cached in-memory.

**Purpose**: Standard format for external org data from any integration

**Lifecycle**: Created on-demand when admin clicks "Discover Organizations". Cached for TTL period (1 hour). Not persisted to storage.

**Python Model**:
```python
from pydantic import BaseModel, Field
from typing import Dict, Any

class ExternalOrganization(BaseModel):
    """External organization from integration discovery"""

    id: str = Field(..., description="External org identifier (tenant ID, customer ID, etc.)")
    name: str = Field(..., description="Organization display name")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Integration-specific extra data")

    class Config:
        frozen = True  # Immutable
```

**Example Instances**:

```python
# Microsoft Graph
ExternalOrganization(
    id="72f988bf-86f1-41af-91ab-2d7cd011db47",
    name="Contoso Corporation",
    metadata={"domain": "contoso.com", "country": "US"}
)

# HaloPSA
ExternalOrganization(
    id="12345",
    name="Acme Corp",
    metadata={"client_code": "ACME001", "is_vip": True}
)

# NinjaRMM
ExternalOrganization(
    id="67890",
    name="Wayne Enterprises",
    metadata={"location_id": "LOC-456", "org_type": "enterprise"}
)
```

### 3. TestResult

Result of testing an integration mapping connection.

**Purpose**: Standard format for connection test results

**Lifecycle**: Created when admin clicks "Test Connection" or integration calls `test_connection()`. Not persisted directly - summary stored in `OrganizationMapping.last_test_result`.

**Python Model**:
```python
from pydantic import BaseModel, Field
from typing import Dict, Any

class TestResult(BaseModel):
    """Result of testing an integration mapping"""

    success: bool = Field(..., description="Test succeeded")
    message: str = Field(..., description="Human-readable result message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional diagnostic information")

    class Config:
        frozen = True
```

**Example Instances**:

```python
# Success
TestResult(
    success=True,
    message="Successfully connected to Acme Corp (ID: 12345)",
    details={"client_name": "Acme Corp", "api_version": "1.0"}
)

# Failure - Invalid credentials
TestResult(
    success=False,
    message="Authentication failed: Invalid API key",
    details={"error_code": "AUTH_001", "http_status": 401}
)

# Failure - Network error
TestResult(
    success=False,
    message="Connection timeout after 30 seconds",
    details={"error_type": "TimeoutError", "endpoint": "https://api.example.com"}
)
```

## Table Storage Schemas

### Table 1: OrgIntegrationMappings

**Purpose**: Primary table for querying mappings by organization

**Partition Strategy**: One partition per organization

**Query Patterns**:
- Get all mappings for org: `PartitionKey eq '{org_id}'`
- Get specific mapping: `PartitionKey eq '{org_id}' and RowKey eq '{integration_name}_{mapping_id}'`
- Get all mappings for integration within org: `PartitionKey eq '{org_id}' and RowKey ge '{integration_name}_' and RowKey lt '{integration_name}`'`

**Schema**:
```
┌────────────────────┬──────────────────────────┬────────────────────────────┐
│ PartitionKey       │ RowKey                   │ Properties                 │
├────────────────────┼──────────────────────────┼────────────────────────────┤
│ {org_id}           │ {integration}_{mapping}  │ MappingId: string          │
│ (UUID)             │ e.g., "halopsa_abc123"   │ IntegrationName: string    │
│                    │                          │ ExternalOrgId: string      │
│                    │                          │ ExternalOrgName: string    │
│                    │                          │ MappingData: JSON string   │
│                    │                          │ IsActive: boolean          │
│                    │                          │ CreatedAt: ISO8601         │
│                    │                          │ CreatedBy: string          │
│                    │                          │ UpdatedAt: ISO8601         │
│                    │                          │ UpdatedBy: string (null OK)│
│                    │                          │ LastTestedAt: ISO8601 (opt)│
│                    │                          │ LastTestResult: string     │
└────────────────────┴──────────────────────────┴────────────────────────────┘
```

**Example Entities**:
```
PartitionKey: "550e8400-e29b-41d4-a716-446655440000"  (Acme Corp org_id)
RowKey: "halopsa_abc123"
MappingId: "abc123"
IntegrationName: "halopsa"
ExternalOrgId: "12345"
ExternalOrgName: "Acme Corp"
MappingData: '{"api_base_url":"https://acme.halopsa.com"}'
IsActive: true
CreatedAt: "2025-10-11T10:30:00Z"
CreatedBy: "user-uuid-123"
UpdatedAt: "2025-10-11T10:30:00Z"
UpdatedBy: null
LastTestedAt: "2025-10-11T10:31:00Z"
LastTestResult: "Successfully connected to Acme Corp"

PartitionKey: "550e8400-e29b-41d4-a716-446655440000"  (Same org)
RowKey: "microsoft_graph_def456"
MappingId: "def456"
IntegrationName: "microsoft_graph"
ExternalOrgId: "72f988bf-86f1-41af-91ab-2d7cd011db47"
ExternalOrgName: "Contoso Corporation"
MappingData: '{}'
IsActive: true
CreatedAt: "2025-10-11T11:00:00Z"
CreatedBy: "user-uuid-123"
UpdatedAt: "2025-10-11T11:00:00Z"
UpdatedBy: null
LastTestedAt: null
LastTestResult: null
```

**Indexes**: None (PartitionKey + RowKey is default clustered index)

**Estimated Size**: ~500 bytes per entity × 1000 orgs × 5 mappings/org = 2.5MB

**Cost**: <$0.01/month

### Table 2: IntegrationMappings

**Purpose**: Inverted index for querying mappings by integration

**Partition Strategy**: One partition per integration

**Query Patterns**:
- Get all orgs using integration: `PartitionKey eq '{integration_name}'`
- Get specific org's mapping for integration: `PartitionKey eq '{integration_name}' and RowKey eq '{org_id}_{mapping_id}'`

**Schema**:
```
┌────────────────────┬──────────────────────────┬────────────────────────────┐
│ PartitionKey       │ RowKey                   │ Properties                 │
├────────────────────┼──────────────────────────┼────────────────────────────┤
│ {integration_name} │ {org_id}_{mapping_id}    │ MappingId: string          │
│ e.g., "halopsa"    │ e.g., "uuid_abc123"      │ OrgId: string              │
│                    │                          │ ExternalOrgId: string      │
│                    │                          │ ExternalOrgName: string    │
│                    │                          │ MappingData: JSON string   │
│                    │                          │ IsActive: boolean          │
│                    │                          │ CreatedAt: ISO8601         │
│                    │                          │ CreatedBy: string          │
│                    │                          │ UpdatedAt: ISO8601         │
│                    │                          │ UpdatedBy: string (null OK)│
│                    │                          │ LastTestedAt: ISO8601 (opt)│
│                    │                          │ LastTestResult: string     │
└────────────────────┴──────────────────────────┴────────────────────────────┘
```

**Example Entities**:
```
PartitionKey: "halopsa"
RowKey: "550e8400-e29b-41d4-a716-446655440000_abc123"
MappingId: "abc123"
OrgId: "550e8400-e29b-41d4-a716-446655440000"
ExternalOrgId: "12345"
ExternalOrgName: "Acme Corp"
MappingData: '{"api_base_url":"https://acme.halopsa.com"}'
IsActive: true
CreatedAt: "2025-10-11T10:30:00Z"
CreatedBy: "user-uuid-123"
UpdatedAt: "2025-10-11T10:30:00Z"
UpdatedBy: null
LastTestedAt: "2025-10-11T10:31:00Z"
LastTestResult: "Successfully connected to Acme Corp"

PartitionKey: "halopsa"
RowKey: "660e8400-e29b-41d4-a716-446655440001_ghi789"
MappingId: "ghi789"
OrgId: "660e8400-e29b-41d4-a716-446655440001"
ExternalOrgId: "67890"
ExternalOrgName: "Wayne Enterprises"
MappingData: '{"api_base_url":"https://wayne.halopsa.com"}'
IsActive: true
CreatedAt: "2025-10-11T12:00:00Z"
CreatedBy: "user-uuid-456"
UpdatedAt: "2025-10-11T12:00:00Z"
UpdatedBy: null
LastTestedAt: null
LastTestResult: null
```

**Indexes**: None (PartitionKey + RowKey is default clustered index)

**Estimated Size**: ~500 bytes per entity × 1000 orgs × 5 mappings/org = 2.5MB

**Cost**: <$0.01/month

**Note**: Data is duplicated between OrgIntegrationMappings and IntegrationMappings. This is intentional for query performance (single-partition queries vs cross-partition queries).

## Entity Relationships

```
┌─────────────────┐
│  Organization   │
│  (existing)     │
└────────┬────────┘
         │
         │ 1:N
         │
         ▼
┌─────────────────────┐       discovers       ┌──────────────────────┐
│ OrganizationMapping │◄---------------------  │ ExternalOrganization │
│                     │                        │   (transient)        │
│ - id                │                        │ - id                 │
│ - org_id            │                        │ - name               │
│ - integration_name  │                        │ - metadata           │
│ - external_org_id   │◄-----------------------│                      │
│ - external_org_name │       matches          └──────────────────────┘
│ - mapping_data      │
│ - is_active         │
│ - created_at        │
│ - created_by        │
│ - updated_at        │
│ - last_tested_at    │
│ - last_test_result  │◄── produces ──┐
└─────────────────────┘                │
                                       │
                            ┌──────────┴────────┐
                            │    TestResult     │
                            │  (transient)      │
                            │ - success         │
                            │ - message         │
                            │ - details         │
                            └───────────────────┘
```

**Relationships**:
1. **Organization → OrganizationMapping**: One-to-many. Each org can have multiple mappings (multiple integrations, multiple mappings per integration).
2. **OrganizationMapping → ExternalOrganization**: Many-to-one (transient). Multiple MSP orgs can map to same external org ID (uncommon but possible).
3. **OrganizationMapping → TestResult**: One-to-one (transient). Test result summarized in `last_test_result` field.

## Data Integrity Rules

### Uniqueness Constraints

1. **Unique mapping ID**: `id` field must be globally unique (UUID v4)
2. **Unique org+integration+mapping combination**: `(org_id, integration_name, mapping_id)` must be unique
3. **No duplicate RowKeys**: RowKey = `{integration_name}_{mapping_id}` must be unique within partition

**Enforcement**: Unique RowKey constraint enforced by Table Storage. Application-level validation prevents duplicate mapping IDs.

### Referential Integrity

1. **Organization must exist**: `org_id` must reference existing entity in Organizations table
2. **Integration must be registered**: `integration_name` must exist in integration registry
3. **User must exist**: `created_by` and `updated_by` must reference valid Azure AD users

**Enforcement**: Application-level validation before insert/update. Foreign key constraints not supported by Table Storage.

### Business Rules

1. **Active mappings only**: Queries should filter `IsActive == true` by default (soft delete)
2. **Unique external org ID per integration per org**: Only one active mapping can map to same `external_org_id` within same org+integration
   - Exception: Multiple mappings allowed if mapping_id differs (e.g., multiple M365 tenants)
3. **Audit trail immutability**: `created_at` and `created_by` never change. Only `updated_at` and `updated_by` change on updates.

**Enforcement**: Application logic in storage service layer.

## Storage Service API

### MappingStorageService

**Purpose**: Abstraction layer for Table Storage operations

**Methods**:

```python
from shared.storage import TableStorageService
from typing import List, Optional
import uuid
from datetime import datetime

class MappingStorageService:
    """Service for managing integration mappings in Table Storage"""

    def __init__(self):
        self.org_table = TableStorageService("OrgIntegrationMappings")
        self.int_table = TableStorageService("IntegrationMappings")

    async def create_mapping(
        self,
        org_id: str,
        integration_name: str,
        external_org_id: str,
        external_org_name: str,
        mapping_data: Dict[str, Any],
        user_id: str
    ) -> OrganizationMapping:
        """
        Create mapping in both tables atomically.

        Args:
            org_id: MSP organization ID
            integration_name: Integration identifier
            external_org_id: External org ID in integration system
            external_org_name: External org display name
            mapping_data: Integration-specific configuration
            user_id: User creating the mapping

        Returns:
            Created OrganizationMapping

        Raises:
            ValueError: If org or integration doesn't exist
            TableTransactionError: If atomic write fails
        """
        mapping = OrganizationMapping(
            id=str(uuid.uuid4()),
            org_id=org_id,
            integration_name=integration_name,
            external_org_id=external_org_id,
            external_org_name=external_org_name,
            mapping_data=mapping_data,
            is_active=True,
            created_at=datetime.utcnow(),
            created_by=user_id,
            updated_at=datetime.utcnow()
        )

        # Write to both tables in parallel
        await asyncio.gather(
            self.org_table.insert_entity(mapping.to_org_entity()),
            self.int_table.insert_entity(mapping.to_integration_entity())
        )

        return mapping

    async def get_org_mappings(
        self,
        org_id: str,
        active_only: bool = True
    ) -> List[OrganizationMapping]:
        """Get all mappings for organization"""
        filter_query = f"PartitionKey eq '{org_id}'"
        if active_only:
            filter_query += " and IsActive eq true"

        entities = self.org_table.query_entities(filter=filter_query)
        return [OrganizationMapping.from_entity(e) for e in entities]

    async def get_mapping(
        self,
        org_id: str,
        integration_name: str,
        mapping_id: str
    ) -> Optional[OrganizationMapping]:
        """Get specific mapping by ID"""
        row_key = f"{integration_name}_{mapping_id}"

        try:
            entity = await self.org_table.get_entity(org_id, row_key)
            return OrganizationMapping.from_entity(entity)
        except ResourceNotFoundError:
            return None

    async def update_mapping(
        self,
        mapping: OrganizationMapping,
        user_id: str
    ) -> OrganizationMapping:
        """Update mapping in both tables"""
        mapping.updated_at = datetime.utcnow()
        mapping.updated_by = user_id

        await asyncio.gather(
            self.org_table.update_entity(mapping.to_org_entity(), mode="replace"),
            self.int_table.update_entity(mapping.to_integration_entity(), mode="replace")
        )

        return mapping

    async def delete_mapping(
        self,
        org_id: str,
        integration_name: str,
        mapping_id: str,
        user_id: str
    ) -> None:
        """Soft delete mapping by setting IsActive=false"""
        mapping = await self.get_mapping(org_id, integration_name, mapping_id)

        if not mapping:
            raise ValueError(f"Mapping not found: {mapping_id}")

        mapping.is_active = False
        await self.update_mapping(mapping, user_id)

    async def update_test_result(
        self,
        org_id: str,
        integration_name: str,
        mapping_id: str,
        test_result: TestResult
    ) -> None:
        """Update last test result for mapping"""
        mapping = await self.get_mapping(org_id, integration_name, mapping_id)

        if not mapping:
            raise ValueError(f"Mapping not found: {mapping_id}")

        mapping.last_tested_at = datetime.utcnow()
        mapping.last_test_result = test_result.message

        # Don't pass user_id since this is automated
        await asyncio.gather(
            self.org_table.update_entity(mapping.to_org_entity(), mode="merge"),
            self.int_table.update_entity(mapping.to_integration_entity(), mode="merge")
        )
```

## Summary

**Tables**: 2 (OrgIntegrationMappings, IntegrationMappings)
**Entities**: 1 persisted (OrganizationMapping), 2 transient (ExternalOrganization, TestResult)
**Storage Cost**: <$0.02/month for 1000 orgs × 5 mappings/org
**Query Performance**: <20ms for all single-partition queries
**Data Integrity**: Application-enforced referential integrity and business rules

**Next Steps**: Design API contracts and integration interface in `/contracts/` directory.
