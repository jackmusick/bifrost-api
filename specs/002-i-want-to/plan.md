# Implementation Plan: Workflow Engine and User Code Separation

**Branch**: `002-i-want-to` | **Date**: 2025-10-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-i-want-to/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Separate workflow engine system code from developer-authored workflow code by restructuring the workflows repository into `/engine` (protected system code) and `/workspace` (developer code) folders. Implement GitHub Actions protection to prevent accidental `/engine` modifications, Python import restrictions to block runtime access to engine internals, and tiered authentication supporting both Azure Functions key bypass and Entra ID validation. Enable local development with Azurite emulator and seed data while maintaining production security through tenant-scoped organization context.

## Technical Context

**Language/Version**: Python 3.11 (Azure Functions v2 programming model)
**Primary Dependencies**: azure-functions, azure-data-tables, Pydantic for models, GitHub Actions for CI/CD
**Storage**: Azure Table Storage (via Azurite locally) for organization/config data, no new storage required
**Testing**: pytest, pytest-asyncio for async workflow execution tests
**Target Platform**: Azure Functions (Linux container runtime), GitHub Actions (ubuntu-latest)
**Project Type**: Single backend project (workflows) with repository restructuring
**Performance Goals**:
  - Import restriction check: <50ms at engine startup
  - GitHub Action check: <10s per commit/PR
  - Azurite seed script: <5s to populate test data
**Constraints**:
  - MUST NOT break existing workflows during migration
  - GitHub Action MUST allow upstream `/engine` syncs without blocking
  - Python import hook MUST NOT impact legitimate workspace imports
**Scale/Scope**:
  - Repository restructure: Move existing `workflows/` contents → `/engine` and `/workspace`
  - GitHub Action: Single YAML file protecting `/engine/*` path
  - Import restrictor: ~50 lines of Python import hook code
  - Seed script: Populate 2-3 test orgs, 3-5 test users, 5-10 config entries
  - Authentication flow: Update existing middleware.py (~100 lines)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Azure-First Architecture
✅ **PASS** - Feature uses only Azure services:
  - Azure Functions for compute (existing)
  - Azure Table Storage for org/config data (existing)
  - Azure Key Vault for secrets (existing pattern)
  - GitHub Actions for CI/CD (Azure DevOps acceptable alternative)
  - Azurite for local development

### Principle II: Table Storage Only
✅ **PASS** - No new storage layer introduced:
  - Uses existing Organizations, Users, Config tables
  - No SQL database required
  - Azurite seed script uses existing table schema

### Principle III: Python Backend Standard
✅ **PASS** - All code is Python 3.11:
  - Import restrictor: Python import hook
  - Seed script: Python script using azure-data-tables
  - Middleware updates: Python async functions
  - GitHub Action: YAML (acceptable for CI/CD)

### Principle IV: Test-First Development
✅ **PASS** - Tests required for:
  - Contract tests: GitHub Action blocks `/engine` modifications
  - Integration tests: Import restrictor prevents workspace→engine imports
  - Integration tests: Authentication flow with function keys
  - Integration tests: Azurite seed script populates correct data
  - Unit tests (optional): Individual import hook logic

### Principle V: Single-MSP Multi-Organization Design
✅ **PASS** - Feature maintains org-scoped isolation:
  - Organization context enforcement (existing pattern)
  - Workspace code runs with org-scoped context
  - Function key auth still validates org ID exists
  - Cross-org access logged for audit (PlatformAdmin usage)
  - No changes to multi-tenant data model

### Gates Summary
**Status**: ✅ ALL GATES PASSED (Initial Check)

No constitution violations. Feature aligns with all 5 core principles and requires no complexity justification.

### Post-Design Re-Check (Phase 1 Complete)
**Status**: ✅ ALL GATES PASSED

Design artifacts reviewed:
- ✅ `research.md`: All technical decisions use Azure services, Python 3.11, Table Storage for audit logs
- ✅ `data-model.md`: New AuditLog table uses Table Storage (Principle II compliance)
- ✅ `contracts/README.md`: API changes are additive (backward compatible), authentication is Azure-native
- ✅ `quickstart.md`: Developer workflow uses standard Azure tooling (Azurite, func start, SWA CLI)

**Findings**: No new constitution violations introduced during design phase. All design decisions reinforce existing principles.

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
workflows/                           # Root workflows directory (restructured)
├── .github/
│   └── workflows/
│       └── protect-engine.yml      # NEW: Block /engine modifications
├── engine/                          # NEW: Protected system code (moved from workflows/*)
│   ├── shared/                      # Existing shared modules
│   │   ├── context.py              # Organization context
│   │   ├── decorators.py           # @workflow, @data_provider
│   │   ├── execution_logger.py     # Execution tracking
│   │   ├── middleware.py           # MODIFIED: Tiered auth
│   │   ├── registry.py             # Workflow discovery
│   │   ├── storage.py              # Table Storage abstraction
│   │   └── import_restrictor.py   # NEW: Block workspace→engine imports
│   ├── execute.py                   # Workflow execution endpoint
│   ├── admin/                       # Admin endpoints
│   ├── data_providers/              # Built-in data providers
│   └── function_app.py              # Azure Functions app config
├── workspace/                       # NEW: Developer workflow code
│   ├── workflows/                   # Custom workflows (moved from workflows/workflows/*)
│   │   ├── user_onboarding.py
│   │   └── webhook_example.py
│   └── data_providers/              # Custom data providers
├── tests/                           # Test suite
│   ├── contract/
│   │   ├── test_github_action.py   # NEW: Test engine protection
│   │   └── test_import_restriction.py  # NEW: Test import blocking
│   ├── integration/
│   │   ├── test_auth_flow.py       # NEW: Test tiered auth
│   │   └── test_workspace_execution.py  # NEW: Test workspace isolation
│   └── unit/
├── scripts/
│   └── seed_azurite.py             # NEW: Azurite test data seeding
├── requirements.txt
└── local.settings.json
```

**Structure Decision**: Single backend project with folder-based isolation. Existing `workflows/` contents split into `/engine` (system) and `/workspace` (developer). GitHub Action guards `/engine`, Python import hook enforces runtime isolation. No changes to API project structure.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

No violations. Complexity tracking not required.
