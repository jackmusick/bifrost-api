# Tasks: Dynamic Data Provider Inputs for Forms

**Input**: Design documents from `/specs/007-in-our-applications/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: This feature follows test-first development (Constitution Principle IV). Contract and integration tests are included and must be written BEFORE implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions
- **Backend**: Repository root (`/Users/jack/GitHub/bifrost-api/`)
  - Models: `shared/models.py`
  - Decorators: `shared/decorators.py`
  - Handlers: `shared/handlers/`
  - Validators: `shared/validators.py`
  - Functions: `functions/http/`
  - Tests: `tests/`
- **Frontend**: Separate repository (`/Users/jack/GitHub/bifrost-client/`)
  - Components: `client/src/components/`
  - Hooks: `client/src/hooks/`
  - Services: `client/src/services/`
  - Utils: `client/src/utils/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Review existing codebase structure for @param decorator pattern in `shared/decorators.py`
- [X] T002 Review existing expression evaluator in client repo for reuse with data provider inputs
- [X] T003 [P] Review existing data provider cache implementation in `shared/handlers/data_providers_handlers.py`
- [X] T004 [P] Review existing form validation logic in `shared/handlers/forms_handlers.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Backend Foundation

- [X] T005 [P] Create `DataProviderInputMode` enum in `shared/models.py`
- [X] T006 [P] Create `DataProviderInputConfig` Pydantic model in `shared/models.py` with validation
- [X] T007 Extend `FormField` model with optional `dataProviderInputs` field in `shared/models.py` (depends on T006)
- [X] T008 [P] Extend `DataProviderMetadata` model with `parameters` field in `shared/models.py`
- [X] T009 [P] Extend `DataProviderRequest` model with optional `inputs` field in `shared/models.py`
- [X] T010 Modify `@data_provider` decorator to collect `@param` decorators in `shared/decorators.py`
- [X] T011 Update registry to store data provider parameters in `shared/registry.py` (depends on T010)
- [X] T012 [P] Implement cache key computation function with input hash in `shared/handlers/data_providers_handlers.py`

### Validation Infrastructure

- [X] T013 Create `shared/validators.py` file
- [X] T014 Implement circular dependency detection algorithm (graph-based DFS) in `shared/validators.py::detect_circular_dependencies()`
- [X] T015 Implement field reference extraction from expressions in `shared/validators.py::extract_field_references()`
- [X] T016 Implement dependency graph builder in `shared/validators.py::build_dependency_graph()`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Configure Data Provider with Static Input Values (Priority: P1) 🎯 MVP

**Goal**: Enable data providers to define input parameters using @param decorators and allow forms to configure static values for those parameters. Forms can be saved and rendered with static data provider inputs.

**Independent Test**: Create a form with a dropdown field configured to use a data provider that requires inputs. Set static values for all required inputs in the form builder JSON. Verify the dropdown populates correctly when the form is rendered and calls the data provider with the static input values.

### Tests for User Story 1

**NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T017 [P] [US1] Contract test: GET /api/metadata returns data provider parameters in `tests/contract/test_data_providers_enhanced_api.py`
- [X] T018 [P] [US1] Contract test: POST /api/data-providers/{name} accepts inputs object in `tests/contract/test_data_providers_enhanced_api.py`
- [X] T019 [P] [US1] Contract test: POST /api/data-providers/{name} validates required parameters in `tests/contract/test_data_providers_enhanced_api.py`
- [X] T020 [P] [US1] Contract test: POST /api/forms validates dataProviderInputs for required params in `tests/contract/test_forms_enhanced_api.py`
- [ ] T021 [P] [US1] Integration test: Data provider with @param decorators executes with inputs in `tests/integration/api/test_data_provider_with_params.py`
- [ ] T022 [P] [US1] Integration test: Form save with static dataProviderInputs succeeds in `tests/integration/api/test_forms_with_provider_inputs.py`
- [X] T023 [P] [US1] Unit test: Cache key computation includes input hash in `tests/unit/handlers/test_data_providers_handlers.py`

### Implementation for User Story 1

#### Backend: Data Provider Parameter Support

- [X] T024 [US1] Modify data provider handler to accept inputs in request in `shared/handlers/data_providers_handlers.py::handle_data_provider_request()`
- [X] T025 [US1] Add parameter validation logic using Pydantic in `shared/handlers/data_providers_handlers.py::validate_data_provider_inputs()`
- [X] T026 [US1] Update cache key logic to include input hash in `shared/handlers/data_providers_handlers.py::get_data_provider_options()`
- [X] T027 [US1] Modify data provider function caller to pass validated inputs in `shared/handlers/data_providers_handlers.py`

#### Backend: Form Validation for Static Inputs

- [X] T028 [US1] Add validation for dataProviderInputs presence when dataProvider is set in `shared/handlers/forms_handlers.py::validate_form_schema()`
- [X] T029 [US1] Add validation for required data provider parameters in `shared/handlers/forms_handlers.py::validate_data_provider_inputs()`
- [X] T030 [US1] Add validation for static input mode configuration in `shared/handlers/forms_handlers.py`

#### Backend: API Endpoints

- [X] T031 [US1] Update metadata endpoint to include parameters in response in `functions/http/data_providers.py`
- [X] T032 [US1] Update data provider POST endpoint to accept inputs in `functions/http/data_providers.py`
- [X] T033 [US1] Add GET endpoint variant for data providers with query param inputs in `functions/http/data_providers.py`
- [X] T034 [US1] Update forms POST endpoint to validate dataProviderInputs in `functions/http/forms.py`

#### Frontend: Basic Data Provider Inputs (Static Mode Only)

**NOTE**: Frontend tasks are for the separate client repository

- [ ] T035 [P] [US1] Update TypeScript types for DataProviderInputConfig in `client/src/lib/v1.d.ts` (run `npm run generate:types`)
- [ ] T036 [P] [US1] Update TypeScript types for FormField with dataProviderInputs in `client/src/lib/v1.d.ts`
- [ ] T037 [US1] Update dataProviderService to accept inputs parameter in `client/src/services/dataProviderService.ts::executeDataProvider()`
- [ ] T038 [US1] Create basic DataProviderInputConfig component for static mode only in `client/src/components/FormBuilder/DataProviderInputConfig.tsx`
- [ ] T039 [US1] Integrate DataProviderInputConfig component into form builder field editor in `client/src/components/FormBuilder/FieldEditor.tsx`
- [ ] T040 [US1] Update form renderer to pass static inputs to data provider calls in `client/src/components/FormRenderer/DynamicDataProviderField.tsx`

#### Testing & Validation

- [X] T041 [US1] Create example data provider with @param decorators in `platform/` for testing (e.g., `get_github_repos`)
- [X] T042 [US1] Create seed form with static data provider inputs in `seed_data.py`
- [X] T021 [US1] Integration test: Data provider with @param decorators executes with inputs (created, needs runtime testing)
- [X] T022 [US1] Integration test: Form save with static dataProviderInputs succeeds (created, needs runtime testing)
- [ ] T043 [US1] Manual test: Verify metadata endpoint returns parameters
- [ ] T044 [US1] Manual test: Call data provider with static inputs via API
- [ ] T045 [US1] Manual test: Create form with static inputs in form builder UI

**Checkpoint**: At this point, User Story 1 should be fully functional - data providers can define parameters, forms can configure static values, and the system validates and executes correctly.

---

## Phase 4: User Story 2 - Reference Other Form Fields as Data Provider Inputs (Priority: P2)

**Goal**: Enable form fields to reference other fields as input values (field reference mode). Dropdowns automatically refresh on blur events when referenced field values change. Fields are disabled with explanatory messages when required inputs are missing.

**Independent Test**: Create a form with two fields - a text input for a token and a dropdown that references that token field as an input parameter. Enter a value in the token field and verify that leaving focus (blur) triggers a refresh of the dropdown with the new token value. Verify the dropdown is disabled before the token is entered.

### Tests for User Story 2

- [ ] T046 [P] [US2] Integration test: Form field reference triggers data provider refresh on blur in `tests/integration/engine/test_form_field_dependencies.py`
- [ ] T047 [P] [US2] Integration test: Dropdown disabled when required field reference is empty in `tests/integration/engine/test_form_field_dependencies.py`
- [ ] T048 [P] [US2] Unit test: Dependency graph builder extracts field references correctly in `tests/unit/test_validators.py`
- [ ] T049 [P] [US2] E2E test: Field reference configuration and runtime behavior in `client/tests/e2e/test_field_reference_inputs.spec.ts`

### Implementation for User Story 2

#### Backend: Field Reference Validation

- [ ] T050 [US2] Add validation for field reference existence in form schema in `shared/handlers/forms_handlers.py::validate_field_references()`
- [ ] T051 [US2] Add validation for forward references (field must appear earlier) in `shared/handlers/forms_handlers.py::validate_field_order()`

#### Frontend: Field Reference Mode & Dynamic Refresh

- [ ] T052 [US2] Extend DataProviderInputConfig component to support field reference mode in `client/src/components/FormBuilder/DataProviderInputConfig.tsx`
- [ ] T053 [US2] Add field reference dropdown showing only earlier fields in `client/src/components/FormBuilder/DataProviderInputConfig.tsx`
- [ ] T054 [US2] Create useDataProviderInputs hook for evaluating inputs at runtime in `client/src/hooks/useDataProviderInputs.ts`
- [ ] T055 [US2] Implement field reference evaluation in useDataProviderInputs hook in `client/src/hooks/useDataProviderInputs.ts`
- [ ] T056 [US2] Implement readiness checking (required inputs satisfied) in `client/src/hooks/useDataProviderInputs.ts`
- [ ] T057 [US2] Update DynamicDataProviderField to use useDataProviderInputs hook in `client/src/components/FormRenderer/DynamicDataProviderField.tsx`
- [ ] T058 [US2] Implement disabled state with explanatory message in `client/src/components/FormRenderer/DynamicDataProviderField.tsx`
- [ ] T059 [US2] Register blur event handlers on referenced fields in `client/src/components/FormRenderer/FormRenderer.tsx`
- [ ] T060 [US2] Build dependency map from dataProviderInputs in `client/src/components/FormRenderer/FormRenderer.tsx`
- [ ] T061 [US2] Trigger data provider refresh on blur from dependent fields in `client/src/components/FormRenderer/FormRenderer.tsx`

#### Testing & Validation

- [ ] T062 [US2] Create example form with field reference inputs in `seed_data.py`
- [ ] T063 [US2] Manual test: Verify dropdown disabled state when referenced field empty
- [ ] T064 [US2] Manual test: Verify blur event triggers refresh with new field value
- [ ] T065 [US2] Manual test: Verify no refresh during typing (only on blur)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - static inputs work, and field references work with dynamic refresh on blur.

---

## Phase 5: User Story 3 - Use JavaScript Expressions for Data Provider Inputs (Priority: P3)

**Goal**: Enable form administrators to use JavaScript expressions to compute input values from form context (e.g., concatenating fields, transformations, accessing workflow properties). Expressions are evaluated safely in a sandboxed context with proper error handling.

**Independent Test**: Create a form with multiple text fields and a dropdown configured with a JavaScript expression input (e.g., `context.field.first_name + ' ' + context.field.last_name`). Enter values in both text fields and verify the dropdown refreshes with the concatenated value. Test error handling by creating an expression that throws an error.

### Tests for User Story 3

- [ ] T066 [P] [US3] Unit test: Expression parser extracts field references from expressions in `tests/unit/test_validators.py::test_extract_field_references_from_expression()`
- [ ] T067 [P] [US3] Integration test: Expression evaluation with context.field.* in `client/tests/unit/utils/expressionEvaluator.test.ts`
- [ ] T068 [P] [US3] Integration test: Expression evaluation with context.workflow.* in `client/tests/unit/utils/expressionEvaluator.test.ts`
- [ ] T069 [P] [US3] Integration test: Expression error handling (invalid syntax, runtime errors) in `client/tests/unit/utils/expressionEvaluator.test.ts`

### Implementation for User Story 3

#### Backend: Expression Field Reference Extraction

- [ ] T070 [US3] Implement regex-based field reference extraction from JavaScript expressions in `shared/validators.py::parse_field_refs_from_expression()`
- [ ] T071 [US3] Update dependency graph builder to extract refs from expressions in `shared/validators.py::build_dependency_graph()` (integrate T070)

#### Frontend: JavaScript Expression Mode

- [ ] T072 [US3] Extend DataProviderInputConfig component to support expression mode in `client/src/components/FormBuilder/DataProviderInputConfig.tsx`
- [ ] T073 [US3] Add code editor/textarea for expression input in `client/src/components/FormBuilder/DataProviderInputConfig.tsx`
- [ ] T074 [US3] Add autocomplete suggestions for context.field.* and context.workflow.* in `client/src/components/FormBuilder/DataProviderInputConfig.tsx`
- [ ] T075 [US3] Implement expression evaluation in useDataProviderInputs hook in `client/src/hooks/useDataProviderInputs.ts`
- [ ] T076 [US3] Add error handling for expression evaluation (try/catch, timeout) in `client/src/hooks/useDataProviderInputs.ts`
- [ ] T077 [US3] Handle invalid expression results (null, undefined, wrong type) in `client/src/hooks/useDataProviderInputs.ts`
- [ ] T078 [US3] Update DynamicDataProviderField to display expression errors in `client/src/components/FormRenderer/DynamicDataProviderField.tsx`

#### Testing & Validation

- [ ] T079 [US3] Create example form with expression inputs in `seed_data.py`
- [ ] T080 [US3] Manual test: Verify expression concatenating two fields works
- [ ] T081 [US3] Manual test: Verify expression with transformation (e.g., toLowerCase()) works
- [ ] T082 [US3] Manual test: Verify expression accessing context.workflow.* works in workflow context
- [ ] T083 [US3] Manual test: Verify error handling for invalid expressions

**Checkpoint**: All three input modes (static, fieldRef, expression) should now work correctly.

---

## Phase 6: User Story 4 - Form Builder UI for Input Configuration (Priority: P2)

**Goal**: Provide a user-friendly interface in the form builder for configuring data provider inputs without manual JSON editing. The UI displays all available parameters, allows mode selection, and provides appropriate input controls for each mode.

**Independent Test**: Open the form builder, select a data provider for a dropdown field. Verify that a configuration panel appears showing all input parameters with their labels, types, and required status. Test switching between static, field reference, and expression modes for each parameter.

### Tests for User Story 4

- [ ] T084 [P] [US4] Component test: DataProviderInputConfig renders all parameters in `client/tests/components/DataProviderInputConfig.test.tsx`
- [ ] T085 [P] [US4] Component test: Mode selector switches between static/fieldRef/expression in `client/tests/components/DataProviderInputConfig.test.tsx`
- [ ] T086 [P] [US4] Component test: Field reference dropdown shows only earlier fields in `client/tests/components/DataProviderInputConfig.test.tsx`
- [ ] T087 [P] [US4] Component test: Required parameters are marked with asterisk in `client/tests/components/DataProviderInputConfig.test.tsx`

### Implementation for User Story 4

#### Frontend: Enhanced Form Builder UI

- [ ] T088 [US4] Fetch data provider metadata when field dataProvider changes in `client/src/components/FormBuilder/FieldEditor.tsx`
- [ ] T089 [US4] Display parameter labels, types, and required status in `client/src/components/FormBuilder/DataProviderInputConfig.tsx`
- [ ] T090 [US4] Add visual indicator for required parameters (asterisk) in `client/src/components/FormBuilder/DataProviderInputConfig.tsx`
- [ ] T091 [US4] Add help text tooltips for parameters in `client/src/components/FormBuilder/DataProviderInputConfig.tsx`
- [ ] T092 [US4] Implement three-way mode selector UI (static/fieldRef/expression) in `client/src/components/FormBuilder/DataProviderInputConfig.tsx`
- [ ] T093 [US4] Add validation feedback for missing required parameters in `client/src/components/FormBuilder/DataProviderInputConfig.tsx`
- [ ] T094 [US4] Disable form save button when required parameters not configured in `client/src/components/FormBuilder/FormBuilder.tsx`
- [ ] T095 [US4] Add inline validation errors for data provider input config in `client/src/components/FormBuilder/FormBuilder.tsx`

#### Testing & Validation

- [ ] T096 [US4] Manual test: Verify parameter panel appears when data provider selected
- [ ] T097 [US4] Manual test: Verify all three modes are selectable and functional
- [ ] T098 [US4] Manual test: Verify required parameter validation prevents save
- [ ] T099 [US4] Manual test: Verify help text and labels display correctly

**Checkpoint**: Form builder UI should be fully functional and user-friendly for all input configuration scenarios.

---

## Phase 7: Circular Dependency Detection & Validation

**Purpose**: Prevent circular dependencies in form configurations and provide clear error messages when detected

### Tests for Circular Dependency Detection

- [ ] T100 [P] [Shared] Unit test: Detect simple cycle (A→B→A) in `tests/unit/test_validators.py::test_detect_simple_cycle()`
- [ ] T101 [P] [Shared] Unit test: Detect complex cycle (A→B→C→A) in `tests/unit/test_validators.py::test_detect_complex_cycle()`
- [ ] T102 [P] [Shared] Unit test: No false positives for valid chains (A→B→C) in `tests/unit/test_validators.py::test_valid_dependency_chain()`
- [ ] T103 [P] [Shared] Contract test: POST /api/forms rejects circular dependencies in `tests/contract/test_forms_enhanced_api.py::test_circular_dependency_rejected()`

### Implementation for Circular Dependency Detection

- [ ] T104 [Shared] Implement DFS-based cycle detection in `shared/validators.py::find_cycles_dfs()`
- [ ] T105 [Shared] Implement cycle path formatting for error messages in `shared/validators.py::format_cycle_error()`
- [ ] T106 [Shared] Integrate circular dependency check into form validation in `shared/handlers/forms_handlers.py::validate_form_schema()`
- [ ] T107 [Shared] Return structured error with cycle path on validation failure in `shared/handlers/forms_handlers.py`

#### Frontend: Circular Dependency Feedback

- [ ] T108 [Shared] Create client-side circular dependency detector in `client/src/utils/circularDependencyDetector.ts`
- [ ] T109 [Shared] Add real-time circular dependency check in form builder in `client/src/components/FormBuilder/FormBuilder.tsx`
- [ ] T110 [Shared] Display clear error message with cycle path in form builder in `client/src/components/FormBuilder/FormBuilder.tsx`

#### Testing & Validation

- [ ] T111 [Shared] Create example form with circular dependency in test data
- [ ] T112 [Shared] Manual test: Verify circular dependency is detected and form save is blocked
- [ ] T113 [Shared] Manual test: Verify error message shows full cycle path
- [ ] T114 [Shared] Manual test: Verify removing circular dependency allows save

**Checkpoint**: Circular dependencies are detected and prevented with clear error messages.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and final quality assurance

### Documentation & Examples

- [ ] T115 [P] [Polish] Update CLAUDE.md with data provider input examples in `/Users/jack/GitHub/bifrost-api/CLAUDE.md`
- [ ] T116 [P] [Polish] Create example data providers with various parameter types in `platform/examples/`
- [ ] T117 [P] [Polish] Create example forms demonstrating all three input modes in `seed_data.py`

### Performance Optimization

- [ ] T118 [P] [Polish] Add performance logging for data provider execution with inputs in `shared/handlers/data_providers_handlers.py`
- [ ] T119 [P] [Polish] Add performance logging for circular dependency detection in `shared/validators.py`
- [ ] T120 [P] [Polish] Optimize expression evaluation (caching, memoization) in `client/src/hooks/useDataProviderInputs.ts`

### Error Handling & UX Improvements

- [ ] T121 [P] [Polish] Add detailed error messages for data provider parameter validation failures in `shared/handlers/data_providers_handlers.py`
- [ ] T122 [P] [Polish] Add loading indicators for data provider refresh in `client/src/components/FormRenderer/DynamicDataProviderField.tsx`
- [ ] T123 [P] [Polish] Add retry mechanism for failed data provider calls in `client/src/components/FormRenderer/DynamicDataProviderField.tsx`

### Code Quality & Refactoring

- [ ] T124 [P] [Polish] Code review: Ensure all Pydantic models have proper validation
- [ ] T125 [P] [Polish] Code review: Ensure all error paths return structured errors
- [ ] T126 [P] [Polish] Refactor duplicate validation logic if any found
- [ ] T127 [P] [Polish] Add type hints to all new Python functions

### Final Testing & Validation

- [ ] T128 [Polish] Run full test suite (contract, integration, unit) in `api/`
- [ ] T129 [Polish] Run frontend test suite in `client/`
- [ ] T130 [Polish] Run `npx pyright` for Python type checking
- [ ] T131 [Polish] Run `ruff check .` for Python linting
- [ ] T132 [Polish] Run `npm run tsc` for TypeScript type checking
- [ ] T133 [Polish] Run `npm run lint` for frontend linting
- [ ] T134 [Polish] Execute quickstart.md validation scenarios
- [ ] T135 [Polish] Update `seed_data.py` to include comprehensive examples
- [ ] T136 [Polish] Generate updated TypeScript types with `npm run generate:types`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) - MVP target
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2) - Can run in parallel with US3/US4 after US1
- **User Story 3 (Phase 5)**: Depends on Foundational (Phase 2) - Can run in parallel with US2/US4 after US1
- **User Story 4 (Phase 6)**: Depends on Foundational (Phase 2) - Can run in parallel with US2/US3 after US1
- **Circular Dependency Detection (Phase 7)**: Depends on Foundational (Phase 2) - Shared by US2/US3
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Foundation only - No dependencies on other stories
- **User Story 2 (P2)**: Foundation only - Builds on US1 concepts but independently testable
- **User Story 3 (P3)**: Foundation + US2 field reference extraction - Extends US2
- **User Story 4 (P2)**: Foundation only - UI for US1/US2/US3, can be built in parallel
- **Circular Detection**: Required by US2 and US3 for field references

### Critical Path

```
Setup (Phase 1)
  → Foundational (Phase 2)
    → US1 Static Inputs (Phase 3) [MVP]
      → US2 Field References (Phase 4)
        → US3 Expressions (Phase 5)
      → US4 Form Builder UI (Phase 6) [Parallel with US2/US3]
      → Circular Detection (Phase 7) [Needed by US2/US3]
    → Polish (Phase 8)
```

### Parallel Opportunities

#### Within Foundational (Phase 2):
- T005-T009: All Pydantic models can be created in parallel
- T012: Cache key function can be created in parallel with models
- T014-T016: Validator functions can be created in parallel

#### Within User Story 1 (Phase 3):
- T017-T023: All tests can be written in parallel
- T035-T036: TypeScript type generation tasks can run in parallel
- T038-T040: Frontend components can be built in parallel after types are ready

#### Within User Story 2 (Phase 4):
- T046-T049: All tests can be written in parallel
- T052-T061: Frontend tasks can largely run in parallel (same file for some)

#### Within User Story 3 (Phase 5):
- T066-T069: All tests can be written in parallel
- T072-T078: Frontend tasks can run in parallel

#### Within User Story 4 (Phase 6):
- T084-T087: All component tests can be written in parallel
- T088-T095: UI implementation tasks can run in parallel

#### Within Circular Detection (Phase 7):
- T100-T103: All tests can be written in parallel
- T108-T110: Frontend detection can run in parallel with backend

#### Within Polish (Phase 8):
- T115-T127: Most polish tasks can run in parallel
- T128-T136: Testing and validation tasks must run sequentially

---

## Parallel Example: User Story 1

### Tests (Write First):
```bash
# Launch all contract tests together:
Task: "Contract test: GET /api/metadata returns data provider parameters"
Task: "Contract test: POST /api/data-providers/{name} accepts inputs object"
Task: "Contract test: POST /api/data-providers/{name} validates required parameters"
Task: "Contract test: POST /api/forms validates dataProviderInputs for required params"

# Launch all integration tests together:
Task: "Integration test: Data provider with @param decorators executes with inputs"
Task: "Integration test: Form save with static dataProviderInputs succeeds"

# Launch unit tests:
Task: "Unit test: Cache key computation includes input hash"
```

### Models (After Tests):
```bash
# All model extensions can run in parallel (different sections of same file):
Task: "Create DataProviderInputMode enum in shared/models.py"
Task: "Create DataProviderInputConfig Pydantic model in shared/models.py"
Task: "Extend FormField model with dataProviderInputs field"
Task: "Extend DataProviderMetadata model with parameters field"
Task: "Extend DataProviderRequest model with inputs field"
```

### Frontend Types & Components:
```bash
# After backend changes:
Task: "Update TypeScript types (run npm run generate:types)"

# Then components in parallel:
Task: "Update dataProviderService to accept inputs parameter"
Task: "Create basic DataProviderInputConfig component"
Task: "Update form renderer to pass static inputs"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

**Goal**: Ship basic static input functionality as fast as possible

1. ✅ Complete Phase 1: Setup (Review existing code - 4 tasks)
2. ✅ Complete Phase 2: Foundational (Core models and infrastructure - 12 tasks)
3. ✅ Complete Phase 3: User Story 1 (Static inputs - 29 tasks)
4. **STOP and VALIDATE**:
   - Run all US1 tests
   - Test data provider with static inputs via API
   - Test form with static inputs in UI
   - Deploy to staging
5. If successful, demo to stakeholders and collect feedback

**MVP Deliverable**: Data providers can define parameters, forms can configure static values, system validates and executes correctly. **Estimated Tasks: 45**

### Incremental Delivery

**After MVP (US1)**, add features in priority order:

1. **Phase 4: User Story 2** (Field references + dynamic refresh - 20 tasks)
   - Test independently: Token field → Repos dropdown
   - Deploy and demo cascading dropdowns

2. **Phase 6: User Story 4** (Form builder UI - 16 tasks)
   - Test independently: Configure inputs without JSON editing
   - Deploy and demo improved UX

3. **Phase 5: User Story 3** (JavaScript expressions - 18 tasks)
   - Test independently: Expression concatenation
   - Deploy and demo advanced use cases

4. **Phase 7: Circular Detection** (12 tasks)
   - Test independently: Invalid circular forms rejected
   - Deploy and demo validation

5. **Phase 8: Polish** (22 tasks)
   - Final cleanup, optimization, documentation
   - Full system validation

**Each increment adds value without breaking previous features**

### Parallel Team Strategy

With multiple developers after Foundational phase:

1. **Team completes Setup + Foundational together** (Phases 1-2: ~16 tasks)

2. **Once Foundational is done, parallelize user stories**:
   - **Developer A**: User Story 1 (Backend focus - Phase 3)
   - **Developer B**: User Story 4 (Frontend focus - Phase 6)
   - **Developer C**: Circular Detection (Shared - Phase 7)

3. **After US1 complete**:
   - **Developer A**: User Story 2 (Phase 4)
   - **Developer B**: Continue US4 or start US3 (Phase 5)
   - **Developer C**: Continue circular detection

4. **Stories integrate and validate independently**

---

## Task Count Summary

| Phase | Description | Task Count |
|-------|-------------|------------|
| Phase 1 | Setup | 4 |
| Phase 2 | Foundational | 12 |
| Phase 3 | User Story 1 (P1) - Static Inputs | 29 |
| Phase 4 | User Story 2 (P2) - Field References | 20 |
| Phase 5 | User Story 3 (P3) - Expressions | 18 |
| Phase 6 | User Story 4 (P2) - Form Builder UI | 16 |
| Phase 7 | Circular Dependency Detection | 15 |
| Phase 8 | Polish & Cross-Cutting | 22 |
| **TOTAL** | | **136 tasks** |

### Tasks Per User Story

- **US1 (MVP)**: 29 implementation + 7 tests = 36 tasks total
- **US2**: 16 implementation + 4 tests = 20 tasks total
- **US3**: 14 implementation + 4 tests = 18 tasks total
- **US4**: 12 implementation + 4 tests = 16 tasks total
- **Shared (Circular Detection)**: 11 implementation + 4 tests = 15 tasks total
- **Foundational**: 12 tasks (blocking for all stories)
- **Setup**: 4 tasks
- **Polish**: 22 tasks

### MVP Scope

**Recommended MVP**: Setup + Foundational + User Story 1 = **45 tasks**

This delivers:
- ✅ Data providers with @param decorators
- ✅ Static input configuration in forms
- ✅ Form validation for required parameters
- ✅ Backend API with input support
- ✅ Basic frontend UI for static inputs
- ✅ Comprehensive test coverage

**MVP can be shipped and provide immediate value, then enhanced incrementally.**

---

## Notes

- **[P] tasks** = different files or independent sections, can run in parallel
- **[Story] label** maps task to specific user story for traceability (US1, US2, US3, US4, Shared, Polish)
- **Test-first approach**: All contract/integration tests written before implementation per Constitution Principle IV
- **Independent stories**: Each user story should be completable and testable independently
- **Checkpoints**: After each user story phase, stop and validate that story works independently
- **File paths**: Backend paths are absolute, frontend paths are in separate client repo
- **Type generation**: Frontend types auto-generated from backend via `npm run generate:types` (requires backend running)
- **Test execution**: Use `./test.sh` for backend tests (starts Azurite), standard `npm test` for frontend

### Avoid
- Vague tasks (each task must be specific and actionable)
- Same file conflicts (coordinate edits or make sequential)
- Cross-story dependencies that break independence (minimize coupling)
- Skipping tests (test-first is non-negotiable per constitution)
