# Implementation Plan: Azure Key Vault Integration for Secret Management

**Branch**: `003-use-azure-key` | **Date**: 2025-10-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-use-azure-key/spec.md`

## Summary

Integrate Azure Key Vault as the secure secret store for all configuration secrets, providing a unified `get_config()` interface that transparently resolves secret references. Supports both production (managed identity) and local development (interactive authentication or local secrets). Includes full secret lifecycle management UI (create, update, delete) restricted to platform admins, with health monitoring endpoint for operational visibility.

**Technical approach**: Implement Key Vault integration in workflow engine's OrganizationContext using azure-keyvault-secrets SDK with DefaultAzureCredential for authentication. Management API will provide secret management endpoints using same SDK. Secrets follow naming convention `{org_id}--{secret-name}` or `GLOBAL--{secret-name}` with automatic fallback.

## Technical Context

**Language/Version**: Python 3.11 (Azure Functions v2 programming model)
**Primary Dependencies**:
- `azure-keyvault-secrets` - Key Vault SDK for secret operations
- `azure-identity` - Authentication (DefaultAzureCredential for managed identity + interactive)
- `azure-data-tables` - Existing table storage operations
- `pydantic` - Existing model validation

**Storage**:
- Azure Table Storage - Config entries with secret_ref type
- Azure Key Vault - Actual secret values
- Naming convention: `{org_id}--{secret-key}` or `GLOBAL--{secret-key}`

**Testing**:
- `pytest` with `pytest-asyncio` for async tests
- Contract tests for API endpoints
- Integration tests for Key Vault operations
- Mock Key Vault client for unit tests

**Target Platform**: Azure Functions (Python 3.11 runtime)

**Project Type**: Distributed web application (workflows + client API + frontend)

**Performance Goals**:
- Secret resolution: <100ms after initial authentication (with cached credentials)
- Health check endpoint: <2s response time
- Secret CRUD operations: <30s end-to-end including UI feedback
- Context loading: <20ms (existing target maintained)

**Constraints**:
- Must use Azure Key Vault (no third-party secret stores)
- Must support local development without Azure access
- Must prevent secret value exposure in logs/responses
- Secrets must be masked after initial creation/update display
- Only platform admins can manage secrets

**Scale/Scope**:
- 50-200 client organizations
- 10-50 secrets per organization (org-scoped)
- 10-20 platform-wide secrets (GLOBAL scope)
- 100-1000 workflow executions per day accessing secrets

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Azure-First Architecture ✅ COMPLIANT

- **All compute**: Azure Functions (existing) ✅
- **All storage**: Azure Table Storage (config refs) + Azure Key Vault (secrets) ✅
- **All authentication**: Azure AD + Managed Identity ✅
- **Local development**: Azurite (existing) + local secret fallback ✅

**Status**: PASS - Using only Azure services (Key Vault, Functions, Table Storage, AD)

### II. Table Storage Only ✅ COMPLIANT

- **Config storage**: Config entries with `secret_ref` type remain in Table Storage ✅
- **Secret storage**: Azure Key Vault (explicitly listed as acceptable exception in constitution) ✅
- **No SQL databases**: Not introducing any SQL ✅

**Status**: PASS - Constitution explicitly lists "Blob Storage for logs, files, and large execution results (with Table Storage pointers)" and "Key Vault for secrets" as acceptable exceptions to Table Storage Only principle. Key Vault is the designated storage for secrets per constitution line 176.

### III. Python Backend Standard ✅ COMPLIANT

- **Backend code**: All in Python 3.11 ✅
- **Shared code**: Extending existing `workflows/engine/shared/context.py` ✅
- **Type hints**: Using Pydantic models for API contracts ✅
- **Async/await**: All I/O operations async (Key Vault calls, Table Storage) ✅

**Status**: PASS - No new languages, extending existing Python backend

### IV. Test-First Development ✅ COMPLIANT

- **Contract tests**: Required for new secret management API endpoints
- **Integration tests**: Required for Key Vault operations (create, read, update, delete, health check)
- **Unit tests**: Required for get_config() resolution logic and fallback behavior
- **Test categories**:
  - Contract: `tests/contract/test_secrets_api.py` - API contracts for secret CRUD
  - Integration: `tests/integration/test_keyvault_integration.py` - End-to-end Key Vault operations
  - Unit: `tests/unit/test_config_resolution.py` - Secret reference resolution logic

**Status**: PASS - Will follow test-first for all secret management logic

### V. Single-MSP Multi-Organization Design ✅ COMPLIANT

- **Org-scoped secrets**: `{org_id}--{secret-key}` naming convention ✅
- **Global MSP secrets**: `GLOBAL--{secret-key}` for platform-wide secrets ✅
- **Fallback pattern**: Try org-specific → fallback to global ✅
- **Permission model**: Platform admins only for secret write operations ✅
- **Context loading**: Integrated into existing OrganizationContext ✅

**Status**: PASS - Follows org-scoped + global pattern, integrates with existing context model

## Project Structure

### Documentation (this feature)

```
specs/003-use-azure-key/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (Key Vault patterns, authentication strategies)
├── data-model.md        # Phase 1 output (Secret entities, health check schema)
├── quickstart.md        # Phase 1 output (Local setup guide)
├── contracts/           # Phase 1 output (OpenAPI specs for secret management API)
│   ├── secret-management.yaml
│   └── health-check.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

This project uses **Option 2: Web application** structure with separate backend projects for workflows and client API:

```
# Workflow Engine (where secrets are consumed)
workflows/
├── engine/
│   └── shared/
│       ├── context.py                    # MODIFY: Implement get_config() with Key Vault resolution
│       ├── keyvault.py                   # NEW: Key Vault client wrapper
│       └── config_resolver.py            # NEW: Config resolution with secret_ref support
└── tests/
    ├── contract/
    │   └── test_config_resolution.py     # NEW: Contract tests for get_config()
    ├── integration/
    │   └── test_keyvault_integration.py  # NEW: Integration tests for Key Vault
    └── unit/
        └── test_config_resolver.py       # NEW: Unit tests for resolution logic

# Client API (where secrets are managed)
client/api/
├── functions/
│   ├── secrets.py                        # NEW: Secret CRUD endpoints (create, update, delete, list)
│   └── health.py                         # NEW: Health check endpoint
├── shared/
│   ├── models.py                         # MODIFY: Add Secret* Pydantic models
│   └── keyvault.py                       # NEW: Key Vault client (shared with workflows)
└── tests/
    ├── contract/
    │   ├── test_secrets_api.py           # NEW: Contract tests for secret management API
    │   └── test_health_api.py            # NEW: Contract tests for health endpoint
    └── integration/
        └── test_secret_lifecycle.py      # NEW: Integration test for full secret lifecycle

# Frontend (where secrets UI will be added)
client/
└── src/
    ├── components/
    │   └── secrets/                      # NEW: Secret management UI components
    │       ├── SecretList.tsx
    │       ├── SecretCreate.tsx
    │       ├── SecretUpdate.tsx
    │       └── SecretDelete.tsx
    └── services/
        └── secretsClient.ts              # NEW: API client for secret management
```

**Structure Decision**:

The project uses a distributed web application structure with three main components:
1. **Workflows** (`workflows/` directory) - Python Azure Functions for workflow execution, where secrets are consumed via `context.get_config()`
2. **Client API** (`client/api/` directory) - Python Azure Functions for management operations, including secret CRUD endpoints
3. **Frontend** (`client/` directory) - React SPA for UI, including new secret management interface

Key Vault integration spans all three:
- **Workflows**: Read-only access for secret consumption during workflow execution
- **Client API**: Full CRUD access for secret management endpoints (admin only)
- **Frontend**: UI for secret management with masked display after creation

Both backend projects share the same Key Vault client implementation pattern, following the existing `shared/` module architecture. The `workflows/engine/shared/keyvault.py` and `client/api/shared/keyvault.py` will contain similar Key Vault client wrappers but tailored to their specific use cases (read-only vs full CRUD).

## Complexity Tracking

*No constitution violations - this section intentionally left empty*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
