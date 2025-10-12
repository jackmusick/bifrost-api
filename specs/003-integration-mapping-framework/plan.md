# Implementation Plan: Integration Mapping Framework

**Branch**: `003-integration-mapping-framework` | **Date**: 2025-10-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-integration-mapping-framework/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a generic framework for mapping MSP organizations to external integration systems (HaloPSA, Microsoft 365, NinjaRMM, etc.) through a standardized interface. Integrations implement `list_organizations()` for discovery, administrators use UI to create mappings between MSP orgs and external org IDs, and workflows access mappings via `get_integration_mapping()` and `set_integration_mapping()` context methods. This enables zero-code integration setup and eliminates custom mapping logic for each integration.

## Technical Context

**Language/Version**: Python 3.11 (Backend - Azure Functions), TypeScript 4.9+ (Frontend - React 18)
**Primary Dependencies**:
- Backend: azure-functions, azure-data-tables, pydantic
- Frontend: React Router, Axios, ShadCN UI components
**Storage**: Azure Table Storage (dual-indexed mappings), Azure Key Vault (integration credentials)
**Testing**: pytest, pytest-asyncio (backend); Jest, React Testing Library (frontend)
**Target Platform**: Azure Functions (Python 3.11 Linux runtime), Azure Static Web Apps (React frontend)
**Project Type**: Web application (split across 3 repos: api, workflows, client)
**Performance Goals**:
- Mapping queries: <20ms (single-partition Table Storage)
- Organization discovery: <10s for 1000+ external orgs
- Mapping creation: <2 minutes end-to-end
**Constraints**:
- Must support multiple mappings per integration (e.g., multiple M365 tenants)
- Must work with existing OrganizationContext workflow pattern
- API response time: <200ms p95
- Zero custom code required for new integrations supporting mapping
**Scale/Scope**:
- 50-200 MSP organizations
- 5-20 integrations with mapping support
- 1000+ external organizations per integration

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ I. Azure-First Architecture
**Status**: PASS
**Rationale**: All storage uses Azure Table Storage (OrgIntegrationMappings, IntegrationMappings tables). Credentials in Azure Key Vault. Backend runs on Azure Functions. No third-party cloud services.

### ✅ II. Table Storage Only
**Status**: PASS
**Rationale**: Mappings stored in Azure Table Storage with dual-indexing pattern:
- `OrgIntegrationMappings` table: PartitionKey = `{org_id}`, RowKey = `{integration_name}_{mapping_id}`
- `IntegrationMappings` table: PartitionKey = `{integration_name}`, RowKey = `{org_id}_{mapping_id}`

This enables fast lookups in both directions (org → mappings, integration → mappings) with sub-10ms single-partition queries. No exceptions needed.

### ✅ III. Python Backend Standard
**Status**: PASS
**Rationale**:
- New integration interface contract in `workflows/shared/integrations/base.py`
- Workflow context methods in `workflows/shared/context.py`
- API endpoints in `api/functions/org_integrations.py` (Python 3.11 Azure Functions)
- Pydantic models for request/response validation
- Type hints and async/await throughout

### ✅ IV. Test-First Development
**Status**: PASS
**Rationale**: This is a non-trivial feature with business logic requiring tests:
- **Contract tests**: API request/response models for mapping CRUD operations
- **Integration tests**: End-to-end mapping creation, discovery, and workflow retrieval
- Tests cover: multiple mappings per integration, missing mapping errors, permission checks

### ✅ V. Single-MSP Multi-Organization Design
**Status**: PASS
**Rationale**:
- Mappings are org-scoped with PartitionKey = `{org_id}`
- Permission checks require `canManageConfig` for mapping management
- OrganizationContext already loaded by decorators, extended with `get_integration_mapping()` and `set_integration_mapping()`
- Workflow execution context has access to org info for mapping lookups
- Integration credentials stored at GLOBAL level (MSP-wide) with mapping data at org level

**Overall**: No constitution violations. Feature aligns perfectly with existing architectural patterns.

## Project Structure

### Documentation (this feature)

```
specs/003-integration-mapping-framework/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── mapping-api.yaml            # CRUD endpoints for mappings
│   ├── discovery-api.yaml          # Organization discovery endpoint
│   └── integration-interface.py    # Python interface contract
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

This is a web application split across 3 repositories:

```
# Repository 1: msp-automation-platform (client)
client/
├── src/
│   ├── components/
│   │   └── integrations/
│   │       ├── IntegrationMappingsList.tsx
│   │       ├── CreateMappingDialog.tsx
│   │       ├── EditMappingDialog.tsx
│   │       └── TestConnectionDialog.tsx
│   ├── pages/
│   │   └── Organizations.tsx (add Integrations tab)
│   ├── services/
│   │   └── integrationMappings.ts
│   ├── hooks/
│   │   └── useIntegrationMappings.ts
│   └── types/
│       └── integrationMapping.ts
└── tests/
    └── components/
        └── integrations/

# Repository 2: msp-automation-api (management API)
api/
├── functions/
│   └── org_integrations.py (new - CRUD endpoints)
├── shared/
│   ├── models.py (add mapping models)
│   └── storage.py (add mapping storage methods)
└── tests/
    └── contract/
        └── test_org_integrations_contract.py

# Repository 3: msp-automation-workflows (workflow engine)
workflows/
├── shared/
│   ├── context.py (add get/set_integration_mapping)
│   ├── integrations/
│   │   ├── __init__.py (update registry)
│   │   └── base.py (define IntegrationInterface)
│   └── models.py (add mapping models)
└── tests/
    └── integration/
        └── test_integration_mapping_workflow.py
```

**Structure Decision**: Using existing 3-repository structure (client, api, workflows). Integration interface and context methods live in workflows repo (shared by all workflows). CRUD API lives in api repo (admin operations). UI components live in client repo. This maintains clear separation of concerns and enables independent deployment cycles.

## Complexity Tracking

*No constitution violations detected. Table left empty per template guidance.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| - | - | - |
