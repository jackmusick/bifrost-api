# Implementation Plan: Dynamic Data Provider Inputs for Forms

**Branch**: `007-in-our-applications` | **Date**: 2025-10-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-in-our-applications/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Enable data providers to accept input parameters (like workflows currently do) and allow form fields to configure these inputs using three modes: static values, field references, or JavaScript expressions. Forms will dynamically refresh data provider options on blur events when dependent field values change, with proper disabled states for missing required inputs and circular dependency prevention.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 4.9+ (frontend)
**Primary Dependencies**:
- Backend: azure-functions, azure-data-tables, Pydantic (existing)
- Frontend: React 18+, existing form builder framework, existing expression evaluator (for visibilityExpression)

**Storage**: Azure Table Storage (FormField model extensions, caching handled by existing data provider cache)
**Testing**: pytest (backend), Jest/React Testing Library (frontend)
**Target Platform**: Azure Functions (backend), Modern browsers (frontend form builder + runtime)
**Project Type**: Web application (backend API + frontend form builder/renderer)
**Performance Goals**:
- Data provider refresh: <500ms from blur event to options loaded
- Form validation (circular dependency detection): <100ms
- Expression evaluation: <50ms per expression

**Constraints**:
- MUST maintain backward compatibility with existing forms that don't use data provider inputs
- MUST work with existing data provider cache infrastructure
- MUST reuse existing visibilityExpression JavaScript evaluator
- Blur-only refresh (no keystroke triggers) to minimize API calls

**Scale/Scope**:
- 10-100 forms per organization
- 1-10 data providers with inputs per form
- Support for complex dependency chains (Field A → Field B → Field C dropdowns)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Azure-First Architecture ✅ PASS

- **Compliance**: Feature uses existing Azure Functions (Python 3.11) and Azure Table Storage
- **Impact**: No new Azure services required; extends existing form storage schema
- **Assessment**: Fully compliant

### II. Table Storage Only ✅ PASS

- **Compliance**: All data stored in Azure Table Storage via extensions to FormField model
- **Impact**: No SQL database required; uses existing Table Storage patterns
- **Assessment**: Fully compliant

### III. Python Backend Standard ✅ PASS

- **Compliance**: Backend changes use Python 3.11, Pydantic models, async/await patterns
- **Impact**: Extends existing `@param` decorator pattern from workflows to data providers
- **Frontend**: TypeScript/React for form builder UI (acceptable exception per constitution)
- **Assessment**: Fully compliant

### IV. Test-First Development ✅ PASS

- **Compliance**: Feature requires contract tests for API changes and integration tests for data provider execution
- **Test Plan**:
  - Contract tests for extended data provider metadata API
  - Integration tests for data provider parameter validation
  - Integration tests for circular dependency detection
  - Unit tests for expression evaluation (frontend)
  - E2E tests for form builder UI and runtime behavior
- **Assessment**: Fully compliant - tests required before implementation

### V. Single-MSP Multi-Organization Design ✅ PASS

- **Compliance**: Feature is org-agnostic; works for forms at both global (MSP) and org-specific levels
- **Impact**: Data provider inputs work the same whether form is global or org-scoped
- **Org Context**: When data provider requires org-specific data, existing org context patterns apply
- **Assessment**: Fully compliant

### Violations Requiring Justification

**None** - This feature extends existing patterns (workflow parameters → data provider parameters) and reuses existing infrastructure (caching, expression evaluation, form storage).

## Project Structure

### Documentation (this feature)

```
specs/007-in-our-applications/
├── spec.md              # Feature specification
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
├── checklists/          # Quality validation checklists
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
# Backend (Python/Azure Functions)
api/ (root)
├── shared/
│   ├── models.py                    # [MODIFY] Extend DataProviderMetadata, FormField models
│   ├── decorators.py                # [MODIFY] Extend @data_provider to support @param
│   ├── registry.py                  # [MODIFY] Store data provider parameters
│   ├── handlers/
│   │   ├── data_providers_handlers.py  # [MODIFY] Accept input params in request
│   │   └── forms_handlers.py        # [MODIFY] Validate data provider input configs
│   └── validators.py                # [NEW] Circular dependency detection logic
├── functions/
│   └── http/
│       ├── data_providers.py        # [MODIFY] Pass input params to data provider functions
│       └── forms.py                 # [MODIFY] Add validation for data provider configs
└── tests/
    ├── contract/
    │   └── test_data_providers_enhanced_api.py  # [NEW] Contract tests
    ├── integration/
    │   ├── test_data_provider_with_params.py    # [NEW] Integration tests
    │   └── test_form_validation.py              # [NEW] Circular dependency tests
    └── unit/
        └── test_validators.py                   # [NEW] Unit tests for validation logic

# Frontend (React/TypeScript)
# NOTE: Client repo is separate - specs/contracts will guide implementation
client/ (separate repo: /Users/jack/GitHub/bifrost-client)
├── src/
│   ├── components/
│   │   ├── FormBuilder/
│   │   │   └── DataProviderInputConfig.tsx   # [NEW] UI for configuring inputs
│   │   └── FormRenderer/
│   │       └── DynamicDataProviderField.tsx  # [MODIFY] Handle dynamic refresh
│   ├── services/
│   │   └── dataProviderService.ts            # [MODIFY] Call API with input params
│   ├── hooks/
│   │   └── useDataProviderInputs.ts          # [NEW] Hook for managing input state
│   └── utils/
│       ├── expressionEvaluator.ts            # [EXISTING] Reuse for input expressions
│       └── circularDependencyDetector.ts     # [NEW] Client-side validation
└── tests/
    └── components/
        └── DataProviderInputConfig.test.tsx  # [NEW] Component tests
```

**Structure Decision**: This is a Web application (Option 2) with backend API and frontend form builder/renderer. Backend modifications extend existing patterns (models, decorators, handlers). Frontend components will be added to the separate bifrost-client repository following contract specifications generated in Phase 1.

## Complexity Tracking

*No constitution violations - no complexity additions requiring justification.*

This feature extends existing patterns:
- Reuses `@param` decorator mechanism from workflows
- Reuses expression evaluator from visibilityExpression
- Reuses data provider caching infrastructure
- Extends existing Pydantic models (FormField, DataProviderMetadata)

---

## Post-Design Constitution Re-evaluation

*Completed after Phase 1 design artifacts (research.md, data-model.md, contracts, quickstart.md)*

### I. Azure-First Architecture ✅ PASS (Confirmed)

**Design Review**:
- All backend changes remain within Azure Functions (Python 3.11)
- Data stored in Azure Table Storage (FormField model extensions)
- No new Azure services introduced
- Frontend changes in separate client repo (acceptable exception)

**Compliance**: CONFIRMED - No violations introduced during design phase

### II. Table Storage Only ✅ PASS (Confirmed)

**Design Review**:
- FormField model extended with optional `dataProviderInputs` field
- DataProviderMetadata extended with `parameters` field
- All stored as JSON in existing Table Storage tables
- No schema migration required (schema-less)
- Cache remains in-memory (existing implementation)

**Compliance**: CONFIRMED - No SQL database or Cosmos DB introduced

### III. Python Backend Standard ✅ PASS (Confirmed)

**Design Review**:
- Backend uses Python 3.11, Pydantic models, async/await
- Extends existing `@param` decorator to support data providers
- Circular dependency detector implemented in Python (shared/validators.py)
- Cache key computation in Python (shared/handlers/data_providers_handlers.py)
- All shared logic in `shared/` module

**Compliance**: CONFIRMED - All backend patterns follow Python standard

### IV. Test-First Development ✅ PASS (Confirmed)

**Design Review**:
- Contract tests defined in quickstart.md and contracts/README.md
- Integration tests specified for data provider execution, caching, validation
- Unit tests specified for circular dependency detection, expression parsing
- E2E tests specified for form builder UI and runtime behavior
- Test-first approach documented in quickstart guide

**Test Coverage Plan**:
- ✅ Contract: Data provider metadata with parameters
- ✅ Contract: Data provider execution with inputs
- ✅ Contract: Form validation (circular dependencies, required params)
- ✅ Integration: Data provider parameter validation
- ✅ Integration: Cache key isolation with inputs
- ✅ Integration: Circular dependency detection (all cycle types)
- ✅ Unit: Circular dependency detector algorithm
- ✅ Unit: Expression parser for field references
- ✅ E2E: Form builder input configuration UI
- ✅ E2E: Dropdown disabled state and dynamic refresh

**Compliance**: CONFIRMED - Comprehensive test plan covers all requirements

### V. Single-MSP Multi-Organization Design ✅ PASS (Confirmed)

**Design Review**:
- Feature works at both global (MSP) and org-specific levels
- Data provider inputs are org-agnostic (depend on form configuration)
- Form storage follows existing PartitionKey patterns (OrgId or "GLOBAL")
- No changes to org context or permission patterns
- When data provider requires org-specific data, existing org context applies

**Compliance**: CONFIRMED - Follows single-MSP multi-org architecture

### Final Assessment

**All principles remain compliant after design phase. No new violations introduced.**

Key design confirmations:
1. ✅ Reuses existing patterns (workflow @param, expression evaluator, caching)
2. ✅ Extends existing models (FormField, DataProviderMetadata) without breaking changes
3. ✅ No new infrastructure or services required
4. ✅ Backward compatible (optional fields, existing forms work unchanged)
5. ✅ Comprehensive test plan following test-first development
6. ✅ Org-aware design compatible with MSP multi-org architecture

**Ready to proceed to Phase 2: Task Generation (`/speckit.tasks`)**
