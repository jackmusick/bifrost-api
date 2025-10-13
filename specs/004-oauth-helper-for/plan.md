# Implementation Plan: OAuth Helper for Integrations and Workflows

**Branch**: `004-oauth-helper-for` | **Date**: 2025-10-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-oauth-helper-for/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Provide a centralized OAuth connection management system that allows workflows and integrations to authenticate with external services without handling OAuth flows manually. The system will store OAuth connection configurations, handle OAuth authorization callbacks, automatically refresh expiring tokens every 30 minutes (when tokens will expire within 4 hours), and provide simple credential retrieval via connection names. This enables workflows to focus on business logic rather than authentication complexity.

## Technical Context

**Language/Version**: Python 3.11 (Azure Functions v2 programming model)
**Primary Dependencies**: azure-functions, azure-data-tables, aiohttp (for OAuth HTTP calls), pydantic (for models)
**Storage**: Azure Table Storage (OAuth metadata), existing secret system (all sensitive OAuth data via Azure Key Vault)
**Testing**: pytest, pytest-asyncio (contract and integration tests required)
**Target Platform**: Azure Functions (Linux runtime), local development with Azurite
**Project Type**: Single backend project (extends existing Azure Functions app)
**Performance Goals**:
- OAuth credential retrieval: <100ms (per spec SC-002)
- Token refresh: <2 seconds per connection (per spec SC-006)
- OAuth authorization flow: <3 minutes setup time (per spec SC-001)
**Constraints**:
- Must handle 100+ concurrent OAuth connections (per spec SC-005)
- 99% token refresh success rate before expiration (per spec SC-003)
- Scheduled job runs every 30 minutes, refreshes tokens expiring within 4 hours
**Scale/Scope**:
- Support 100+ OAuth connections with different providers
- Handle authorization code, client credentials, and refresh token flows
- Integrate with existing workflow/integration execution context

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Azure-First Architecture ✅

**Compliance**: PASS
- Compute: Azure Functions (Python 3.11 runtime)
- Storage: Azure Table Storage for OAuth configs/credentials, Azure Key Vault for encryption keys
- Auth: Existing Azure AD integration (no changes needed)
- Local dev: Azurite for Table Storage emulation

**Justification**: Feature fully aligns with Azure-first principle. No third-party services required.

### II. Table Storage Only ✅

**Compliance**: PASS
- OAuth Connection Configurations: Table Storage (PartitionKey = "OAUTH_CONFIG" or org-scoped)
- OAuth Credentials: Table Storage with encrypted token fields
- Connection Status: Table Storage (embedded in config or separate rows)
- Workflow Disable State: Table Storage (PartitionKey = org-scoped or "GLOBAL")

**Access patterns**:
- Get OAuth config by name: Single partition query (sub-10ms)
- List all OAuth connections: Partition scan
- Get credentials by connection name: Single point query
- Find workflows using connection: Requires research (dual-indexing pattern may be needed)

**Justification**: OAuth connections are inherently org-scoped or global. Table Storage provides fast lookups by connection name and supports the <100ms credential retrieval requirement.

### III. Python Backend Standard ✅

**Compliance**: PASS
- Language: Python 3.11
- Framework: Azure Functions v2 programming model
- Models: Pydantic for OAuth connection config, credentials, callback events
- Async I/O: aiohttp for OAuth provider HTTP calls, async Table Storage SDK
- Shared code: OAuth helper functions can be in `shared/` module for use by workflows

**Justification**: Feature naturally fits Python backend standard. OAuth flows are I/O-bound (perfect for async/await).

### IV. Test-First Development ✅

**Compliance**: PASS (tests required)

This feature has significant business logic and external integrations:

**Contract tests required**:
- `tests/contract/test_oauth_api.py`: Test OAuth management endpoints (create, list, delete, reconnect)
- `tests/contract/test_oauth_callback.py`: Test OAuth callback endpoint contract
- `tests/contract/test_oauth_credentials.py`: Test credential retrieval endpoint

**Integration tests required**:
- `tests/integration/test_oauth_authorization_flow.py`: End-to-end OAuth authorization with mock provider
- `tests/integration/test_oauth_token_refresh.py`: Token refresh with mock OAuth provider
- `tests/integration/test_workflow_credential_access.py`: Workflow retrieves and uses OAuth credentials
- `tests/integration/test_oauth_connection_deletion.py`: Delete connection and verify workflow disable cascade

**Justification**: OAuth flows are complex and failure-prone. Test-first approach ensures correct implementation of authorization codes, token exchange, refresh logic, and error handling.

### V. Single-MSP Multi-Organization Design ✅

**Compliance**: PASS

OAuth connections follow the same pattern as existing configs/secrets:

**Storage pattern**:
- PartitionKey = "GLOBAL" for MSP-level OAuth connections (Azure CSP, HaloPSA, shared integrations)
- PartitionKey = OrgId for org-specific OAuth connections (client's own Microsoft 365 tenant, etc.)
- RowKey = connection name (unique identifier)

**Access pattern (matches existing config fallback)**:
```python
# Check org-specific first, fallback to global
connection = await get_oauth_connection(org_id, connection_name)
# Implementation: Try PartitionKey=OrgId first, then PartitionKey="GLOBAL"
```

**Use cases**:
- MSP-level: Shared integrations like Azure CSP, HaloPSA API, monitoring tools
- Org-level: Client-specific OAuth like their own Microsoft 365 tenant, custom applications

**Workflow context**: OAuth connections are retrieved using org context (just like `get_config()`), enabling integration developers to write workflows that work for both MSP and client-specific integrations.

**Justification**: OAuth connections are fundamentally a type of credential/config. Using the same org-scoped pattern maintains consistency with existing platform architecture and supports both MSP-wide and client-specific integrations.

### Gate Status: ✅ PASS

All constitutional principles align. Feature follows established patterns for Azure-first, Table Storage, Python backend, test-first development, and org-scoped data with global fallback.

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── oauth_connection.py      # Pydantic model for OAuth connection config
│   ├── oauth_credentials.py     # Pydantic model for stored credentials
│   └── oauth_callback.py        # Pydantic model for callback events
├── services/
│   ├── oauth_service.py         # Core OAuth logic (create, authorize, refresh)
│   ├── oauth_provider.py        # OAuth provider HTTP client (token exchange, refresh)
│   └── workflow_disable_service.py  # Workflow detection and disable logic
├── shared/
│   └── oauth_helper.py          # Shared helper for workflows: get_oauth_connection()
└── functions/
    ├── oauth_api.py             # HTTP endpoints: create, list, delete, reconnect
    ├── oauth_callback.py        # HTTP endpoint: OAuth callback handler
    └── oauth_refresh_timer.py   # Timer trigger: scheduled token refresh job

tests/
├── contract/
│   ├── test_oauth_api.py
│   ├── test_oauth_callback.py
│   └── test_oauth_credentials.py
└── integration/
    ├── test_oauth_authorization_flow.py
    ├── test_oauth_token_refresh.py
    ├── test_workflow_credential_access.py
    └── test_oauth_connection_deletion.py
```

**Structure Decision**: Single backend project extending existing Azure Functions app. OAuth functionality follows established patterns:
- **Models**: Pydantic models for type safety and validation
- **Services**: Business logic separated from HTTP handlers
- **Shared**: Reusable helper for workflow code (`get_oauth_connection()`)
- **Functions**: Azure Functions HTTP triggers and timer trigger
- **Tests**: Contract tests for API contracts, integration tests for OAuth flows

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

No constitutional violations. Feature aligns with all principles.

---

## Post-Design Constitution Check

*Re-evaluation after Phase 1 design completion*

### Design Artifacts Completed

✅ Phase 0: research.md - All research decisions documented
✅ Phase 1: data-model.md - 5 entities with Table Storage schemas
✅ Phase 1: contracts/oauth-api.openapi.yaml - OpenAPI 3.0 specification
✅ Phase 1: quickstart.md - Developer implementation guide

### Constitution Compliance Re-Check

**I. Azure-First Architecture** ✅ PASS
- All services remain Azure-native (Functions, Table Storage, Key Vault)
- No additional dependencies introduced
- Design maintains Azure-first principle

**II. Table Storage Only** ✅ PASS
- All entities stored in Table Storage as designed
- Dual-indexing pattern used for workflow dependencies
- No SQL database requirements emerged during design
- Secret system integration leverages existing Key Vault infrastructure

**III. Python Backend Standard** ✅ PASS
- All components use Python 3.11 + async/await
- Pydantic models for type safety
- Azure Functions v2 programming model maintained
- Shared oauth_helper.py for workflow integration

**IV. Test-First Development** ✅ PASS
- Contract tests defined for all API endpoints
- Integration tests defined for OAuth flows
- Quickstart includes test-first examples
- Test strategy documented

**V. Single-MSP Multi-Organization Design** ✅ PASS
- Org-scoped partitioning implemented (OrgId or "GLOBAL")
- Config fallback pattern matches existing architecture
- OAuth connections support both MSP-level and org-specific use cases
- Workflow disable state is org-scoped

### Design Quality Assessment

**Strengths**:
- Clean separation of concerns (models, services, functions)
- Unified secret storage (all sensitive data via existing secret system) maintains platform consistency
- Dual-indexing enables fast bidirectional workflow dependency lookups
- No separate encryption logic needed - leverages existing secret system
- API contracts are comprehensive and follow REST conventions

**Potential Risks**:
- Workflow dependency detection relies on explicit registration (workflows must call registration endpoint)
- Token refresh job scans all connections every 30 minutes (may need optimization at scale)
- No automatic retry for failed OAuth connections (manual reconnection required)

**Mitigation**:
- Document workflow dependency registration requirements in quickstart
- Add monitoring/alerting for token refresh failures
- Consider background job optimization if connection count exceeds 500+

### Final Gate Status: ✅ PASS

All constitutional principles remain satisfied after design. Feature ready for Phase 2 (task generation via `/speckit.tasks`).
