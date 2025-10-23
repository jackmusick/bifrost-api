# Research & Design Decisions: Dynamic Data Provider Inputs

**Feature**: 007-in-our-applications
**Date**: 2025-10-22
**Status**: Complete

## Overview

This document captures research findings and design decisions for enabling data providers to accept input parameters, configured through form fields using static values, field references, or JavaScript expressions.

## Key Design Decisions

### Decision 1: Extend @param Decorator to Data Providers

**Context**: Workflows already use `@param` decorator to define input parameters. Data providers need the same capability.

**Decision**: Reuse the existing `@param` decorator for data providers, just like workflows.

**Rationale**:
- **Consistency**: Developers already understand `@param` from workflows
- **Code reuse**: Same parameter validation logic
- **Familiar API**: No new decorator syntax to learn
- **Type safety**: Leverages existing Pydantic validation for parameter types

**Implementation approach**:
```python
@data_provider(name="get_github_repos", description="...")
@param("token", type="string", label="GitHub Token", required=True)
@param("org", type="string", label="Organization", required=False)
async def get_github_repos(context, token, org=None):
    # Implementation
    pass
```

**Alternatives considered**:
- **New decorator syntax** (e.g., `@input`) - Rejected: Adds unnecessary complexity
- **Config-based approach** (JSON/YAML) - Rejected: Less type-safe, harder to validate at load time

---

### Decision 2: FormField Model Extension for Input Configuration

**Context**: Need to store how data provider inputs are configured (static value, field reference, or expression).

**Decision**: Add optional `dataProviderInputs` field to FormField model as a dictionary mapping parameter names to input configurations.

**Rationale**:
- **Backward compatibility**: Optional field, existing forms unaffected
- **Flexible structure**: Dict allows any number of parameters
- **Type safety**: Pydantic model for input configuration structure
- **Table Storage friendly**: JSON serialization works out of the box

**Data structure**:
```python
class DataProviderInputConfig(BaseModel):
    """Configuration for a single data provider input parameter"""
    mode: Literal["static", "fieldRef", "expression"]
    value: str | None = None  # Static value
    fieldName: str | None = None  # Referenced field name
    expression: str | None = None  # JavaScript expression

class FormField(BaseModel):
    # ... existing fields ...
    dataProvider: str | None = None
    dataProviderInputs: dict[str, DataProviderInputConfig] | None = None
```

**Alternatives considered**:
- **Separate table** (DataProviderInputConfigs) - Rejected: Overkill, adds complexity, needs joins
- **Nested list structure** - Rejected: Dict provides O(1) lookup by parameter name
- **String-encoded config** (e.g., "static:value") - Rejected: Not type-safe, harder to validate

---

### Decision 3: Reuse Existing Expression Evaluator

**Context**: Forms already have JavaScript expression evaluation for `visibilityExpression`. Need same for data provider input expressions.

**Decision**: Reuse the exact same expression evaluator that handles `visibilityExpression`, providing the same `context.field.*` and `context.workflow.*` API.

**Rationale**:
- **Consistency**: Same expression syntax across visibility and data provider inputs
- **No new dependencies**: Already have a working, tested evaluator
- **Familiar API**: Form administrators already understand `context.field.*` expressions
- **Security**: Inherits same sandboxing/security measures as visibility expressions

**Implementation approach**:
- Frontend: Same evaluation function used for both visibilityExpression and dataProviderInputs
- Context structure:
  ```typescript
  const context = {
    field: {
      [fieldName]: fieldValue,
      // ... all field values
    },
    workflow: {
      // ... workflow properties if in workflow context
    }
  };
  ```

**Alternatives considered**:
- **New expression engine** - Rejected: Unnecessary duplication, no new requirements
- **Template strings** (e.g., `${field.token}`) - Rejected: Less powerful than full JavaScript expressions
- **GraphQL-like syntax** - Rejected: Overengineering for simple value access

---

### Decision 4: Blur-Based Refresh Strategy

**Context**: Need to refresh data provider options when dependent field values change, but not on every keystroke.

**Decision**: Trigger data provider refresh only on blur events (when user leaves focus) from fields referenced by data provider inputs.

**Rationale**:
- **Performance**: Prevents excessive API calls during typing (80%+ reduction per SC-005)
- **User experience**: Final value is what matters, not intermediate states
- **Backend friendly**: Reduces load on data provider endpoints
- **Mobile friendly**: Works well with touch interfaces where blur is clear

**Implementation approach**:
- Frontend: Register blur event handlers on all fields referenced by data provider inputs
- Debounce logic: Not needed since blur naturally debounces
- Loading states: Show spinner during refresh
- Error states: Display data provider errors inline

**Alternatives considered**:
- **Debounced onChange** (e.g., 500ms delay) - Rejected: Still causes unnecessary calls, complex to tune
- **Manual refresh button** - Rejected: Poor UX, requires extra user action
- **Change + delay** - Rejected: Blur is simpler and more predictable

---

### Decision 5: Circular Dependency Detection Algorithm

**Context**: Must prevent forms with circular dependencies (Field A depends on B, B depends on A).

**Decision**: Use graph-based cycle detection with topological sort during form save validation.

**Rationale**:
- **Correctness**: Catches all circular dependencies, including indirect ones (A→B→C→A)
- **Fast**: O(V+E) where V=fields, E=dependencies - well under 100ms constraint for typical forms
- **Standard algorithm**: Well-understood, easy to test
- **Server-side**: Authoritative validation, can't be bypassed

**Implementation approach**:
1. Build dependency graph from form fields with dataProviderInputs
2. Run depth-first search to detect cycles
3. Return specific error with cycle path (e.g., "Field A → Field B → Field C → Field A")
4. Block form save until circular dependencies are resolved

**Alternatives considered**:
- **Field order enforcement** (only reference earlier fields) - Rejected: Too restrictive, prevents valid use cases
- **Runtime detection** (detect at render time) - Rejected: Poor UX, user sees error after filling form
- **Depth limit** (max 5 levels) - Rejected: Doesn't prevent true cycles, arbitrary limit

---

### Decision 6: Data Provider Cache Key Strategy

**Context**: Existing data provider cache uses provider name as key. With inputs, need to include input values in cache key.

**Decision**: Extend cache key to include hash of input parameter values: `{provider_name}:{input_hash}`

**Rationale**:
- **Correctness**: Different input values should not share cache entries
- **Performance**: Cache hit rate remains high for repeated queries with same inputs
- **Simplicity**: Minimal change to existing cache infrastructure
- **Deterministic**: Same inputs always produce same cache key

**Implementation approach**:
```python
def compute_cache_key(provider_name: str, input_params: dict[str, Any]) -> str:
    if not input_params:
        return provider_name  # Backward compatible

    # Sort keys for deterministic hash
    param_str = json.dumps(input_params, sort_keys=True)
    param_hash = hashlib.sha256(param_str.encode()).hexdigest()[:16]
    return f"{provider_name}:{param_hash}"
```

**Alternatives considered**:
- **Full JSON in key** - Rejected: Keys could be very long, less efficient
- **Separate cache per input** - Rejected: Overcomplicates cache management
- **No caching with inputs** - Rejected: Would harm performance significantly

---

### Decision 7: Required Input Handling & Disabled State

**Context**: When a data provider has required inputs that are not satisfied, the field should be disabled.

**Decision**: Frontend calculates "readiness" based on required inputs and disables field + shows explanatory message when not ready.

**Rationale**:
- **Clear UX**: User understands why field is disabled and what's needed
- **Prevents errors**: No API call until all required inputs are available
- **Progressive disclosure**: Field becomes available as user fills dependencies
- **Accessible**: Disabled state with message is screen-reader friendly

**Implementation approach**:
- Check required inputs on field mount and whenever dependencies change
- Disabled state: Gray out dropdown, show message like "Requires GitHub Token"
- Auto-enable: Field enables when all required inputs become valid
- Optional inputs: Field enabled even if optional inputs are missing

**Message examples**:
- "Requires GitHub Token" (single required input missing)
- "Requires GitHub Token and Organization" (multiple missing)
- "Loading repositories..." (all inputs satisfied, fetching data)

**Alternatives considered**:
- **Allow selection with placeholder** - Rejected: Confusing, user expects data
- **Error on submit** - Rejected: Too late, poor UX
- **Hide field entirely** - Rejected: User doesn't know field exists or what's needed

---

### Decision 8: API Contract for Data Provider Execution

**Context**: Need to pass input parameters when calling data provider endpoints.

**Decision**: Extend existing `/api/data-providers/{provider_name}` endpoint to accept optional `inputs` query parameter or request body.

**Rationale**:
- **Backward compatible**: Existing calls without inputs continue to work
- **RESTful**: Uses same endpoint, parameter as query string or body
- **Type-safe**: Input values validated against parameter metadata
- **Cacheable**: GET with query params is cacheable by HTTP layer

**API design**:
```
GET /api/data-providers/{provider_name}?inputs[token]=abc123&inputs[org]=acme
POST /api/data-providers/{provider_name}
Body: { "inputs": { "token": "abc123", "org": "acme" } }
```

**Validation**:
- Check all required parameters are provided
- Validate types match parameter definitions
- Apply validation rules (min, max, pattern, etc.)
- Return 400 Bad Request with clear error for missing/invalid inputs

**Alternatives considered**:
- **New endpoint** (`/api/data-providers/{name}/execute`) - Rejected: Unnecessary, breaks backward compat
- **Inputs in headers** - Rejected: Not RESTful, harder to debug
- **Separate endpoint per provider** - Rejected: Doesn't scale, complex routing

---

### Decision 9: Form Builder UI Pattern

**Context**: Need UI in form builder to configure data provider inputs without JSON editing.

**Decision**: Expandable panel below field configuration showing all available inputs with mode selector (Static / Field Reference / Expression).

**Rationale**:
- **Discoverability**: Inputs are visible when configuring field
- **Progressive complexity**: Simple cases (static) are easy, advanced cases (expressions) are available
- **Validation feedback**: Inline errors for misconfigured inputs
- **Autocomplete**: Field reference dropdown and expression suggestions

**UI flow**:
1. User selects data provider for field
2. If provider has parameters, panel appears showing each input
3. For each input, user chooses mode:
   - **Static**: Text input for value
   - **Field Reference**: Dropdown of available fields (only earlier fields shown)
   - **Expression**: Code editor with autocomplete for `context.*`
4. Required inputs marked with asterisk
5. Save button disabled if required inputs not configured

**Alternatives considered**:
- **Modal dialog** - Rejected: Disrupts flow, harder to see field context
- **Separate screen** - Rejected: Too much navigation
- **JSON editor only** - Rejected: Power users only, not user-friendly

---

## Technical Patterns & Best Practices

### Parameter Validation Pattern

Follow existing workflow parameter validation:
1. Define parameters with `@param` decorator
2. Store metadata in registry at module load time
3. Validate at request time before calling data provider function
4. Use Pydantic models for type coercion and validation
5. Return structured validation errors (400 Bad Request)

### Circular Dependency Detection Pattern

```python
def detect_circular_dependencies(form_fields: list[FormField]) -> list[str]:
    """
    Returns list of error messages for circular dependencies.
    Empty list if no cycles found.
    """
    graph = build_dependency_graph(form_fields)
    cycles = find_cycles_dfs(graph)
    return [format_cycle_error(cycle) for cycle in cycles]

def build_dependency_graph(form_fields: list[FormField]) -> dict[str, set[str]]:
    """Build adjacency list: field_name -> {dependent_field_names}"""
    graph = {}
    for field in form_fields:
        dependencies = extract_field_dependencies(field)
        graph[field.name] = dependencies
    return graph

def extract_field_dependencies(field: FormField) -> set[str]:
    """Extract field names this field depends on"""
    dependencies = set()
    if field.dataProviderInputs:
        for input_config in field.dataProviderInputs.values():
            if input_config.mode == "fieldRef":
                dependencies.add(input_config.fieldName)
            elif input_config.mode == "expression":
                # Parse expression for field references
                dependencies.update(parse_field_refs_from_expression(input_config.expression))
    return dependencies
```

### Expression Evaluation Security

Reuse existing security measures from visibilityExpression:
- Sandboxed evaluation (no access to window, document, etc.)
- Timeout limit (50ms per expression)
- No async operations allowed
- Limited scope (only context object accessible)
- No eval() or Function() constructor

### Cache Invalidation Strategy

- Cache entries expire based on data provider `cache_ttl_seconds` (existing)
- Input-based cache keys ensure different inputs get different cache entries
- No manual invalidation needed (TTL handles staleness)
- Cache warming possible for common input combinations (future optimization)

## Integration Points

### Existing Systems Leveraged

1. **Workflow @param decorator**: Reused for data provider parameters
2. **Data provider registry**: Extended to store parameter metadata
3. **Data provider cache**: Extended with input-aware cache keys
4. **Expression evaluator**: Reused from visibilityExpression
5. **Form validation**: Extended to include circular dependency checks
6. **FormField model**: Extended with optional dataProviderInputs field

### New Components Required

1. **Circular dependency detector**: New validation logic (shared/validators.py)
2. **Input configuration UI**: New form builder component (client)
3. **Dynamic refresh logic**: New hook for managing input-driven refresh (client)
4. **Enhanced metadata API**: Extended data provider metadata to include parameters

## Testing Strategy

### Contract Tests
- Data provider metadata includes parameters
- Data provider endpoint accepts inputs
- Form validation rejects circular dependencies
- Form save/load preserves dataProviderInputs

### Integration Tests
- Data provider with required inputs rejects calls without them
- Data provider with optional inputs uses defaults when omitted
- Cache keys differentiate calls with different inputs
- Circular dependency detection catches all cycle types

### Unit Tests
- Circular dependency detector (various graph structures)
- Expression parser extracts field dependencies correctly
- Cache key generation is deterministic

### E2E Tests (Frontend)
- Form builder UI for configuring inputs
- Dropdown disables when required inputs missing
- Dropdown refreshes on blur from dependent field
- Error messages display for data provider failures

## Performance Considerations

### Expected Load
- 10-100 forms per org
- 1-10 data providers with inputs per form
- Average 2-3 dependent fields per form
- 100-1000 data provider calls per day per org

### Optimizations
- Circular dependency check only on form save (not every render)
- Expression evaluation cached per render cycle
- Data provider results cached with TTL
- Dependency graph computed once per form load

### Bottlenecks to Monitor
- Expression evaluation time (target <50ms)
- Data provider response time (target <500ms including cache check)
- Form validation time (target <100ms including circular dependency check)

## Security Considerations

### Input Validation
- All data provider inputs validated against parameter definitions
- Type coercion with strict validation (Pydantic)
- No arbitrary code execution (expressions sandboxed)

### Authorization
- Data providers run with user's organization context
- Existing org-scoped permissions apply
- No cross-org data leakage through shared cache (cache keys include org context implicitly via data provider execution)

### Expression Safety
- Sandboxed evaluator prevents XSS
- No access to DOM or browser APIs
- Timeout prevents infinite loops
- Scope limited to context object

## Rollout Plan

### Phase 1 (MVP - P1)
- Backend: @param support for data providers
- Backend: Input validation and passing to functions
- Backend: Extended cache key logic
- Frontend: Static input configuration UI
- Tests: Contract and integration tests for backend

### Phase 2 (P2)
- Frontend: Field reference input mode
- Frontend: Blur-based refresh logic
- Frontend: Disabled state for missing required inputs
- Backend: Enhanced metadata API
- Tests: E2E tests for dynamic behavior

### Phase 3 (P3)
- Frontend: JavaScript expression input mode
- Frontend: Expression editor with autocomplete
- Backend: Circular dependency detection
- Tests: Validation tests for cycles

### Phase 4 (Polish)
- Performance optimization (cache warming)
- Enhanced error messages
- Accessibility improvements
- Documentation and examples

## Open Questions

### Resolved
1. ✅ Should @param decorator work for data providers? **YES** - Reuse existing mechanism
2. ✅ How to detect circular dependencies? **Graph cycle detection** with DFS
3. ✅ When to refresh data providers? **On blur** from dependent fields
4. ✅ How to cache with inputs? **Include input hash** in cache key
5. ✅ How to handle required inputs? **Disable field + show message** until satisfied

### For Implementation
- None remaining - all design decisions made

## References

- Feature Spec: [spec.md](./spec.md)
- Implementation Plan: [plan.md](./plan.md)
- Existing Workflow Parameters: `shared/decorators.py::@param`
- Existing Expression Evaluator: `client/src/utils/expressionEvaluator.ts`
- Data Provider Cache: `shared/handlers/data_providers_handlers.py`
