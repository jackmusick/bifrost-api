# Decorators and Discovery System

## Overview

Bifrost uses a decorator-based system to automatically discover and register workflows and data providers from `/platform` and `/home` directories. This document explains how the system works end-to-end.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  1. Function App Startup (function_app.py)                  │
│     - Initializes Azure Functions                           │
│     - Calls discover_workspace_modules()                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  2. Workspace Discovery (function_app.py:170-246)           │
│     - Scans /platform and /home directories                 │
│     - Finds all *.py files (except __init__.py)             │
│     - Imports each file as a module                         │
│     - No __init__.py files required!                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  3. Decorator Execution (shared/decorators.py)              │
│     - @workflow and @data_provider decorators run           │
│     - @param decorators attach parameter metadata           │
│     - Metadata is registered in WorkflowRegistry            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  4. Registry Storage (shared/registry.py)                   │
│     - WorkflowRegistry (singleton, thread-safe)             │
│     - Stores WorkflowMetadata (dataclass)                   │
│     - Stores DataProviderMetadata (dataclass)               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  5. API Endpoints                                           │
│     - GET /api/discovery → get_discovery_metadata()         │
│     - GET /api/data-providers → list_data_providers()       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  6. Model Conversion (shared/handlers/discovery_handlers.py)│
│     - convert_registry_workflow_to_model()                  │
│     - convert_registry_provider_to_model()                  │
│     - Converts dataclass → Pydantic model for API           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  7. Client Consumption                                       │
│     - Form builder fetches data providers                   │
│     - Workflow UI shows available workflows                 │
│     - Type-safe API responses (Pydantic validated)          │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Workspace Discovery

**Location**: `function_app.py` lines 170-246

**What it does**:

- Scans `/platform` and `/home` directories recursively
- Finds all `.py` files (except those starting with `_`)
- Imports each file using `importlib`
- Module names follow pattern: `workspace.{path}.{filename}`

**Example**:

```
File: platform/examples/data_providers/my_provider.py
Module name: workspace.examples.data_providers.my_provider
```

**Key characteristics**:

- No `__init__.py` files required
- Hot-reload friendly (paths determined dynamically)
- Import restrictions enforced (`/home` can only use `bifrost`, `/platform` can use `shared.*`)

### 2. The `@workflow` Decorator

**Location**: `shared/decorators.py` line 70-170

**What it does**:

1. Wraps your async function
2. Collects metadata (name, description, parameters, etc.)
3. Registers function in `WorkflowRegistry`
4. Returns the original function (unmodified)

**Example**:

```python
from bifrost import workflow, param

@workflow(
    name="process_order",
    description="Process customer order",
    category="sales"
)
@param("order_id", type="string", required=True)
@param("priority", type="string", default_value="normal")
async def process_order(context, order_id: str, priority: str = "normal"):
    # Your logic here
    return {"status": "processed"}
```

**Behind the scenes**:

```python
# Decorator creates WorkflowMetadata dataclass
metadata = WorkflowMetadata(
    name="process_order",
    description="Process customer order",
    category="sales",
    parameters=[
        WorkflowParameter(name="order_id", type="string", required=True),
        WorkflowParameter(name="priority", type="string", default_value="normal")
    ],
    function=process_order  # Your actual function
)

# Registers in singleton registry
get_registry().register_workflow(metadata)
```

### 3. The `@data_provider` Decorator

**Location**: `shared/decorators.py` line 250-360

**What it does**:

1. Wraps your async function
2. Collects metadata (name, description, category, cache TTL)
3. Collects parameters from `@param` decorators
4. Registers function in `WorkflowRegistry`
5. Returns the original function (unmodified)

**Example**:

```python
from bifrost import data_provider, param

@data_provider(
    name="get_github_repos",
    description="Get GitHub repositories",
    category="github",
    cache_ttl_seconds=300
)
@param("token", type="string", required=True, label="GitHub Token")
@param("org", type="string", required=False, default_value="")
async def get_github_repos(context, token: str, org: str = ""):
    # Your logic here
    return [
        {"label": "repo-1", "value": "org/repo-1"},
        {"label": "repo-2", "value": "org/repo-2"}
    ]
```

### 4. The `@param` Decorator

**Location**: `shared/decorators.py` line 10-68

**What it does**:

1. Creates a `WorkflowParameter` object
2. Attaches it to the function via `__workflow_params__` or `__data_provider_params__`
3. Parent decorator (`@workflow` or `@data_provider`) collects these during registration

**Stacking**:

```python
@workflow(name="example")
@param("field1", type="string")  # Collected third (top-down)
@param("field2", type="number")  # Collected second
@param("field3", type="boolean") # Collected first
async def example(context, field1, field2, field3):
    pass

# Results in parameters list: [field3, field2, field1]
# We reverse the list to match declaration order!
```

### 5. WorkflowRegistry (Singleton)

**Location**: `shared/registry.py` line 70-215

**What it stores**:

```python
# Two dataclasses for metadata
@dataclass
class WorkflowMetadata:
    name: str
    description: str
    parameters: list[WorkflowParameter]
    function: Any  # The actual Python function
    # ... more fields

@dataclass
class DataProviderMetadata:
    name: str
    description: str
    parameters: list[WorkflowParameter]
    function: Any  # The actual Python function
    category: str
    cache_ttl_seconds: int
```

**Thread safety**: Uses `threading.Lock()` for concurrent registration

**Singleton pattern**: Only one instance exists across the entire app

### 6. Model Conversion for API

**Location**: `shared/handlers/discovery_handlers.py` line 70-108

**Why needed**:

- Registry uses **dataclasses** (lightweight, internal)
- API needs **Pydantic models** (validation, serialization, OpenAPI)

**Conversion flow**:

```python
# Registry dataclass (internal)
@dataclass
class DataProviderMetadata:
    parameters: list[WorkflowParameter]  # Python list

# Pydantic model (API)
class DataProviderMetadata(BaseModel):
    parameters: list[WorkflowParameter] = Field(...)  # Validated list

# Conversion function
def convert_registry_provider_to_model(registry_provider):
    # Maps dataclass fields → Pydantic model fields
    # Handles snake_case → camelCase (e.g., cache_ttl_seconds → cacheTtlSeconds)
    # Converts parameter objects to dicts
    return DataProviderMetadata(
        name=registry_provider.name,
        parameters=[param_to_dict(p) for p in registry_provider.parameters]
    )
```

## Data Flow Example: Form with Data Provider

### Step 1: User creates form in UI

```json
{
	"name": "Create Ticket",
	"formSchema": {
		"fields": [
			{
				"name": "priority",
				"type": "select",
				"dataProvider": "get_priority_levels",
				"dataProviderInputs": {
					"filter": {
						"mode": "static",
						"value": "active"
					}
				}
			}
		]
	}
}
```

### Step 2: Form validation (create/update)

**Location**: `shared/handlers/forms_handlers.py`

```python
# Validates that data provider exists
provider = registry.get_data_provider("get_priority_levels")
if not provider:
    raise ValidationError("Unknown provider")

# Validates required parameters are configured
for param in provider.parameters:
    if param.required and param.name not in field.dataProviderInputs:
        raise ValidationError(f"Missing required parameter: {param.name}")
```

### Step 3: Form startup (when user opens form)

**Location**: `functions/http/forms.py` → `execute_form_startup_handler`

```python
# For each field with dataProvider
for field in form.fields:
    if field.dataProvider:
        # Resolve inputs (static, fieldRef, expression)
        inputs = resolve_data_provider_inputs(field.dataProviderInputs, context)

        # Call data provider
        options = await call_data_provider(field.dataProvider, inputs, context)

        # Return options to client
        response["fields"][field.name]["options"] = options
```

### Step 4: Data provider execution

**Location**: `shared/handlers/data_providers_handlers.py`

```python
async def get_data_provider_options_handler(
    provider_name: str,
    inputs: dict,
    context: RequestContext
):
    # Get provider from registry
    provider = registry.get_data_provider(provider_name)

    # Validate inputs against parameters
    errors = validate_data_provider_inputs(provider, inputs)
    if errors:
        return {"error": "ValidationError", "details": errors}, 400

    # Check cache
    cache_key = compute_cache_key(provider_name, inputs, context.org_id)
    cached = get_from_cache(cache_key)
    if cached:
        return cached, 200

    # Call provider function with inputs as kwargs
    options = await provider.function(context, **inputs)

    # Cache result
    set_cache(cache_key, options, ttl=provider.cache_ttl_seconds)

    return {"provider": provider_name, "options": options}, 200
```

## Import Restrictions

**Location**: `shared/import_restrictor.py`

### /home code (user workflows)

- ✅ Can import: `bifrost.*`
- ❌ Cannot import: `shared.*`, `functions.*`, `azure.*`
- **Why**: Users should only use the public SDK

### /platform code (platform workflows, examples)

- ✅ Can import: `bifrost.*`, `shared.*`
- ❌ Cannot import: `functions.*` (HTTP handlers)
- **Why**: Platform code may need internal handlers but shouldn't touch HTTP layer

### /functions code (HTTP endpoints)

- ✅ Can import: Everything
- **Why**: HTTP layer orchestrates all other layers

## Key Design Decisions

### 1. Why dataclass for registry + Pydantic for API?

**Registry (dataclass)**:

- Lightweight (no validation overhead during registration)
- Fast (no serialization needed)
- Mutable (can attach `function` reference)

**API (Pydantic)**:

- Validation (ensures API contracts)
- Serialization (automatic JSON conversion)
- OpenAPI (generates API documentation)

### 2. Why singleton registry?

- **Global state**: All modules register to same registry
- **Thread safety**: Multiple imports during startup
- **Performance**: No repeated initialization

### 3. Why no **init**.py required?

- **User experience**: Drop files, they just work
- **Hot reload**: No module structure to maintain
- **Flexibility**: Mix Python packages and standalone files

## Troubleshooting

### Provider not showing up in /api/data-providers

1. **Check file is being imported**:
    - Look for startup logs: `✓ Discovered: workspace.examples.providers.my_provider`
    - If missing: File starts with `_` or import failed

2. **Check decorator is correct**:

    ```python
    from bifrost import data_provider  # ✅ Correct
    from shared.decorators import data_provider  # ❌ Wrong (import restrictions)
    ```

3. **Check registry**:
    ```python
    from shared.registry import get_registry
    registry = get_registry()
    providers = registry.get_all_data_providers()
    print([p.name for p in providers])
    ```

### Parameters not showing up

1. **Check `@param` comes AFTER `@data_provider`**:

    ```python
    @data_provider(name="test")  # First
    @param("field", ...)          # After
    async def test(context, field):
        pass
    ```

2. **Check registry dataclass has `parameters` field**:
    - Should be in `shared/registry.py` line 68
    - Added in T024

3. **Check conversion function includes parameters**:
    - Should be in `shared/handlers/discovery_handlers.py` line 82-108
    - Converts registry dataclass → Pydantic model

## Related Files

- **Decorators**: `shared/decorators.py`
- **Registry**: `shared/registry.py`
- **Discovery**: `function_app.py` (lines 170-246)
- **API Endpoints**:
    - `functions/http/discovery.py`
    - `functions/http/data_providers.py`
- **Handlers**:
    - `shared/handlers/discovery_handlers.py`
    - `shared/handlers/data_providers_handlers.py`
    - `shared/handlers/forms_handlers.py`
- **Models**: `shared/models.py` (lines 750-800)
- **SDK**: `bifrost.py`, `sdk/__init__.py`
