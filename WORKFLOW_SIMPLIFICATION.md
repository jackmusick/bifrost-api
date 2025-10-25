# Workflow Execution Simplification Plan

## Problem Statement

Currently, workflow execution logic is duplicated across multiple files:
- `shared/handlers/workflows_handlers.py` - HTTP endpoint execution
- `functions/queue/worker.py` - Async queue worker execution
- `shared/handlers/forms_handlers.py` - Form submission execution
- `shared/handlers/data_providers_handlers.py` - Data provider execution

This duplication means:
- Bug fixes must be applied in 3+ places (e.g., logging capture fix)
- New features require changes in multiple files
- Metadata models are artificially separated (WorkflowMetadata vs DataProviderMetadata)
- No clear separation between execution engine and HTTP/queue handling

## Goals

1. **Single Execution Engine** - All execution logic in `shared/engine.py`
2. **Unified Metadata** - Single `FunctionMetadata` class instead of separate Workflow/DataProvider
3. **Tag-based Categorization** - Functions can have multiple "uses" via decorator tags
4. **DRY Principle** - Zero duplication of execution logic
5. **Backward Compatibility** - Existing decorators and API contracts unchanged

## Architecture Changes

### 1. Unified Metadata Model

**Current:**
```python
@dataclass
class WorkflowMetadata:
    name: str
    description: str
    execution_mode: Literal["sync", "async"]
    parameters: list[WorkflowParameter]
    # ... 10+ workflow-specific fields

@dataclass
class DataProviderMetadata:
    name: str
    description: str
    cache_ttl_seconds: int
    parameters: list[WorkflowParameter]
    # ... data-provider-specific fields
```

**New:**
```python
@dataclass
class FunctionMetadata:
    """Unified metadata for all registered functions"""
    # Identity
    name: str
    description: str
    category: str = "General"
    tags: list[str] = field(default_factory=list)  # ["workflow", "data_provider", etc.]

    # Execution
    execution_mode: Literal["sync", "async"] = "async"
    timeout_seconds: int = 300
    function: Any = None

    # Parameters
    parameters: list[WorkflowParameter] = field(default_factory=list)

    # HTTP Endpoint (for "workflow" tag)
    endpoint_enabled: bool = False
    allowed_methods: list[str] = field(default_factory=lambda: ["POST"])
    disable_global_key: bool = False
    public_endpoint: bool = False

    # Caching (for "data_provider" tag)
    cache_ttl_seconds: int = 300

    # Source tracking
    source: Literal["home", "platform", "workspace"] | None = None

    # Retry/scheduling (future use)
    retry_policy: dict[str, Any] | None = None
    schedule: str | None = None
```

**Key Insight:** The `tags` list determines where a function can be used:
- `"workflow"` tag → Can run from /workflows page, can be HTTP endpoint
- `"data_provider"` tag → Can provide dropdown options for forms
- Function can have BOTH tags!

### 2. Unified Registry

**Current:**
```python
class WorkflowRegistry:
    _workflows: dict[str, WorkflowMetadata] = {}
    _data_providers: dict[str, DataProviderMetadata] = {}

    def register_workflow(self, metadata: WorkflowMetadata): ...
    def register_data_provider(self, metadata: DataProviderMetadata): ...
    def get_workflow(self, name: str): ...
    def get_data_provider(self, name: str): ...
```

**New:**
```python
class FunctionRegistry:
    _functions: dict[str, FunctionMetadata] = {}

    def register_function(self, metadata: FunctionMetadata):
        """Register or merge metadata for a function"""
        if metadata.name in self._functions:
            # Merge tags from multiple decorators
            existing = self._functions[metadata.name]
            existing.tags = list(set(existing.tags + metadata.tags))
            # Update other fields as needed
        else:
            self._functions[metadata.name] = metadata

    def get_function(self, name: str) -> FunctionMetadata | None:
        return self._functions.get(name)

    # Convenience methods (backward compat)
    def get_workflow(self, name: str) -> FunctionMetadata | None:
        func = self.get_function(name)
        return func if func and "workflow" in func.tags else None

    def get_data_provider(self, name: str) -> FunctionMetadata | None:
        func = self.get_function(name)
        return func if func and "data_provider" in func.tags else None
```

### 3. Unified Execution Engine

Create `shared/engine.py`:

```python
@dataclass
class ExecutionRequest:
    """Request to execute code or registered function"""
    execution_id: str
    caller: Caller
    organization: Organization | None
    config: dict[str, Any]

    # EITHER inline code OR function name
    code: str | None = None              # Base64 Python code
    name: str | None = None              # Registered function name

    # Parameters
    parameters: dict[str, Any] = field(default_factory=dict)

    # Flags
    transient: bool = False              # Don't write to DB
    no_cache: bool = False               # For data providers


@dataclass
class ExecutionResult:
    """Result of code/function execution"""
    execution_id: str
    status: ExecutionStatus
    result: Any
    duration_ms: int

    # Captured data
    logs: list[dict[str, Any]]
    variables: dict[str, Any] | None     # Only for inline scripts
    state_snapshots: list[dict[str, Any]]
    integration_calls: list[dict[str, Any]]

    # Error details
    error_message: str | None = None
    error_type: str | None = None

    # Data provider specific
    cached: bool = False
    cache_expires_at: str | None = None


async def execute(request: ExecutionRequest) -> ExecutionResult:
    """
    Unified execution engine for all code execution.

    Handles:
    - Inline Python scripts (request.code set)
    - Registered workflows (request.name set, has "workflow" tag)
    - Registered data providers (request.name set, has "data_provider" tag)
    """
    start_time = datetime.utcnow()

    # Resolve what we're executing
    if request.code:
        metadata = None
        func = None
        is_script = True
    elif request.name:
        registry = get_registry()
        metadata = registry.get_function(request.name)
        if not metadata:
            raise ValueError(f"Function '{request.name}' not found")
        func = metadata.function
        is_script = False
    else:
        raise ValueError("Must provide either code or name")

    # Create execution context
    context = ExecutionContext(
        user_id=request.caller.user_id,
        email=request.caller.email,
        name=request.caller.name,
        scope=request.organization.id if request.organization else "GLOBAL",
        organization=request.organization,
        execution_id=request.execution_id,
        _config=request.config
    )

    # Set up logging capture
    script_logs = []
    logger_output = []

    # Custom handler for Python logging module
    class ListHandler(logging.Handler):
        def __init__(self, logs_list):
            super().__init__()
            self.logs_list = logs_list

        def emit(self, record):
            self.logs_list.append({
                'level': record.levelname,
                'message': record.getMessage(),
                'timestamp': datetime.fromtimestamp(record.created).isoformat()
            })

    list_handler = ListHandler(script_logs)
    list_handler.setLevel(logging.DEBUG)
    root_logger = logging.getLogger()
    original_level = root_logger.level
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(list_handler)

    try:
        # Execute based on type
        if is_script:
            result, captured_variables = await _execute_script(
                request.code,
                context,
                request.name or "script"
            )
        else:
            # Check cache for data providers
            if "data_provider" in metadata.tags and not request.no_cache:
                cached_result = _check_cache(request.name, request.parameters, context.org_id)
                if cached_result:
                    return _build_cached_result(request.execution_id, cached_result)

            # Execute function
            result = await func(context, **request.parameters)
            captured_variables = None  # Functions don't capture variables

            # Cache if data provider
            if "data_provider" in metadata.tags:
                _cache_result(request.name, request.parameters, context.org_id, result, metadata.cache_ttl_seconds)

        # Format logs
        for log_entry in script_logs:
            logger_output.append({
                'timestamp': log_entry.get('timestamp', datetime.utcnow().isoformat()),
                'level': log_entry.get('level', 'INFO').lower(),
                'message': log_entry.get('message', ''),
                'source': 'logger'
            })

        # Calculate duration
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        return ExecutionResult(
            execution_id=request.execution_id,
            status=ExecutionStatus.SUCCESS,
            result=result,
            duration_ms=duration_ms,
            logs=logger_output,
            variables=captured_variables,
            state_snapshots=context._state_snapshots,
            integration_calls=context._integration_calls
        )

    except Exception as e:
        # Error handling
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        return ExecutionResult(
            execution_id=request.execution_id,
            status=ExecutionStatus.FAILED,
            result=None,
            duration_ms=duration_ms,
            logs=logger_output,
            variables=None,
            state_snapshots=context._state_snapshots,
            integration_calls=context._integration_calls,
            error_message=str(e),
            error_type=type(e).__name__
        )

    finally:
        # Cleanup
        root_logger.removeHandler(list_handler)
        root_logger.setLevel(original_level)


async def _execute_script(code: str, context: ExecutionContext, name: str) -> tuple[Any, dict]:
    """Execute inline Python script"""
    compiled_code = compile(code, f'<script:{name}>', 'exec')

    exec_globals = {
        '__name__': '__main__',
        '__file__': f'<script:{name}>',
        'context': context
    }

    exec(compiled_code, exec_globals)

    # Capture variables
    captured_variables = {
        k: v for k, v in exec_globals.items()
        if not k.startswith('__')
        and not callable(v)
        and not isinstance(v, type(sys))
        and k != 'context'
    }

    result = {"status": "completed", "message": "Script executed successfully"}
    return result, captured_variables
```

### 4. Updated Decorators

**@workflow decorator:**
```python
def workflow(**kwargs):
    """Decorator to register a function as a workflow"""
    def decorator(func):
        metadata = FunctionMetadata(
            name=kwargs['name'],
            description=kwargs.get('description', ''),
            category=kwargs.get('category', 'General'),
            tags=kwargs.get('tags', []) + ['workflow'],  # Add 'workflow' tag
            execution_mode=kwargs.get('execution_mode', 'async'),
            timeout_seconds=kwargs.get('timeout_seconds', 300),
            endpoint_enabled=kwargs.get('endpoint_enabled', False),
            allowed_methods=kwargs.get('allowed_methods', ['POST']),
            source=kwargs.get('source'),
            function=func
        )
        get_registry().register_function(metadata)
        return func
    return decorator
```

**@data_provider decorator:**
```python
def data_provider(**kwargs):
    """Decorator to register a function as a data provider"""
    def decorator(func):
        metadata = FunctionMetadata(
            name=kwargs['name'],
            description=kwargs.get('description', ''),
            category=kwargs.get('category', 'General'),
            tags=['data_provider'],  # Just this tag
            cache_ttl_seconds=kwargs.get('cache_ttl_seconds', 300),
            function=func
        )
        get_registry().register_function(metadata)
        return func
    return decorator
```

**Multi-tag example:**
```python
@workflow(name="multi_use", description="Can be both!")
@data_provider(name="multi_use")
@param("filter", type="string")
def multi_use(context, filter: str = ""):
    # This function has tags: ["workflow", "data_provider"]
    # Can be called from /workflows OR used in form dropdowns
    return [{"label": "Option 1", "value": "1"}]
```

## Implementation Plan

### Phase 1: Create Foundation (No Breaking Changes)

**Step 1.1: Create FunctionMetadata**
- Add `FunctionMetadata` class to `shared/registry.py`
- Keep existing `WorkflowMetadata` and `DataProviderMetadata` (will deprecate later)

**Step 1.2: Update Registry**
- Add `_functions: dict[str, FunctionMetadata]` storage
- Add `register_function()` and `get_function()` methods
- Keep existing methods for backward compatibility

**Step 1.3: Create Engine**
- Create `shared/engine.py` with `ExecutionRequest`, `ExecutionResult`, `execute()` function
- Extract all shared execution logic from `workflows_handlers.py`
- No callers yet - just the engine itself

**Step 1.4: Update Decorators**
- Update `@workflow` and `@data_provider` to also call `register_function()`
- Still maintain old registration for backward compat

### Phase 2: Migrate Callers

**Step 2.1: Update workflows_handlers.py**
```python
async def execute_workflow_handler(...) -> tuple[dict[str, Any], int]:
    # Build ExecutionRequest
    request = ExecutionRequest(
        execution_id=execution_id,
        caller=Caller(...),
        organization=org,
        config=config,
        code=script_code if is_script else None,
        name=workflow_name if not is_script else None,
        parameters=workflow_params,
        transient=transient
    )

    # Execute via engine
    result = await execute(request)

    # Convert to HTTP response
    return _build_response(result), 200
```

**Step 2.2: Update worker.py**
```python
async def workflow_execution_worker(msg: func.QueueMessage):
    # Parse message
    message_data = json.loads(msg.get_body().decode('utf-8'))

    # Build ExecutionRequest
    request = ExecutionRequest(
        execution_id=message_data["execution_id"],
        caller=Caller(...),
        organization=org,
        config=config,
        name=message_data["workflow_name"],
        parameters=message_data["parameters"]
    )

    # Execute via engine
    result = await execute(request)

    # Update execution in DB
    exec_logger.update_execution(
        execution_id=result.execution_id,
        status=result.status,
        result=result.result,
        logs=result.logs,
        ...
    )
```

**Step 2.3: Update data_providers_handlers.py**
```python
async def get_data_provider_options_handler(...):
    # Build ExecutionRequest
    request = ExecutionRequest(
        execution_id=str(uuid.uuid4()),
        caller=Caller(...),
        organization=context.organization,
        config=context._config,
        name=provider_name,
        parameters=inputs or {},
        no_cache=no_cache
    )

    # Execute via engine
    result = await execute(request)

    # Build data provider response
    return {
        "provider": provider_name,
        "options": result.result,
        "cached": result.cached,
        "cache_expires_at": result.cache_expires_at
    }, 200
```

### Phase 3: Cleanup

**Step 3.1: Remove Deprecated Code**
- Remove old execution logic from handlers (now just thin wrappers)
- Remove `WorkflowMetadata` and `DataProviderMetadata` classes
- Remove `register_workflow()` and `register_data_provider()` from registry

**Step 3.2: Update Tests**
- Update all tests to use new `FunctionMetadata` model
- Verify all integration tests pass
- Add new tests for multi-tag functions

**Step 3.3: Update Documentation**
- Update API documentation
- Regenerate TypeScript types
- Update platform examples

## Benefits

1. **~800 lines of duplicated code eliminated**
2. **Single source of truth** for execution logic
3. **Easier to add features** - change engine once, affects all callers
4. **Easier to debug** - single execution path
5. **More flexible** - functions can have multiple uses via tags
6. **Better separation** - handlers are thin HTTP/queue wrappers, engine has business logic

## Backward Compatibility

- Existing `@workflow` and `@data_provider` decorators work unchanged
- Existing API contracts unchanged
- Migration is internal refactoring only
- All existing tests should pass

## Testing Strategy

1. **Unit tests** for engine.py (execution logic in isolation)
2. **Integration tests** for each handler calling engine
3. **End-to-end tests** ensuring HTTP/queue workflows still work
4. **Run existing test suite** - should pass 100%

## File Changes Summary

**New Files:**
- `shared/engine.py` - Unified execution engine

**Modified Files:**
- `shared/registry.py` - Add FunctionMetadata, update registry
- `shared/decorators.py` - Update to use unified metadata
- `shared/handlers/workflows_handlers.py` - Call engine instead of duplicating logic
- `functions/queue/worker.py` - Call engine instead of duplicating logic
- `shared/handlers/data_providers_handlers.py` - Call engine instead of duplicating logic
- `shared/handlers/forms_handlers.py` - Call engine for workflow execution

**Deleted Code:**
- ~800 lines of duplicated execution logic across handlers

## Risks and Mitigations

**Risk:** Breaking existing workflows
**Mitigation:** Extensive testing, backward compatibility layer

**Risk:** Performance regression
**Mitigation:** Engine is same logic, just consolidated. Should be identical performance.

**Risk:** Cache behavior changes
**Mitigation:** Cache logic moved to engine but behavior identical

## Timeline Estimate

- Phase 1 (Foundation): 2-3 hours
- Phase 2 (Migration): 2-3 hours
- Phase 3 (Cleanup/Testing): 1-2 hours
- **Total: 5-8 hours**

## Success Criteria

✅ All existing tests pass
✅ No API contract changes
✅ Execution logic exists in exactly one place
✅ New engine.py has >90% test coverage
✅ TypeScript types regenerated successfully
✅ Zero duplicated execution code across handlers
