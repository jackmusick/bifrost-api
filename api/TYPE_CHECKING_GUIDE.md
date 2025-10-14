# Type Checking Guide for Azure Functions

This guide explains how to fix common Pylance/Pyright type checking issues in Azure Functions endpoints.

## Common Issues and Solutions

### Issue 1: `Cannot access attribute "context" for class "HttpRequest"`

**Problem:**
```python
@with_request_context
async def handler(req: func.HttpRequest):
    context = req.context  # ❌ Pylance error: attribute "context" is unknown
```

**Solution:**
Use the `get_context()` helper from `shared.types`:

```python
from shared.types import get_context

@with_request_context
async def handler(req: func.HttpRequest):
    context = get_context(req)  # ✅ Properly typed as RequestContext
```

### Issue 2: `Argument of type "str | None" cannot be assigned to parameter of type "str"`

**Problem:**
```python
connection_name = req.route_params.get("connection_name")  # Returns str | None
some_function(connection_name)  # ❌ Pylance error: could be None
```

**Solution:**
Use the `get_route_param()` helper from `shared.types`:

```python
from shared.types import get_route_param

connection_name = get_route_param(req, "connection_name")  # ✅ Returns str (raises ValueError if None)
some_function(connection_name)  # ✅ Type checker knows it's not None
```

## Quick Reference

### Import Statement

```python
from shared.types import get_context, get_route_param
from shared.decorators import with_request_context
```

### Full Example

```python
import azure.functions as func
from shared.types import get_context, get_route_param
from shared.decorators import with_request_context

@with_request_context
async def my_handler(req: func.HttpRequest) -> func.HttpResponse:
    # Get context (replaces: context = req.context)
    context = get_context(req)

    # Get required route param (replaces: param = req.route_params.get("param"))
    resource_id = get_route_param(req, "resourceId")

    # Now use context and resource_id with proper type checking
    logger.info(f"User {context.email} accessing resource {resource_id}")

    # Access context properties
    org_id = context.scope
    user_id = context.user_id
    is_admin = context.is_platform_admin

    # ... rest of handler
```

## Type Helpers API

### `get_context(req: HttpRequest) -> RequestContext`

Extracts the RequestContext from an HttpRequest that has been decorated with `@with_request_context`.

**Returns:** `RequestContext` with properties:
- `user_id: str`
- `email: str`
- `name: str`
- `org_id: str | None`
- `scope: str` (GLOBAL or org_id)
- `is_platform_admin: bool`
- `is_function_key: bool`

**Raises:** None (context is guaranteed to exist after decorator runs)

### `get_route_param(req: HttpRequest, param_name: str) -> str`

Extracts a required route parameter from the request.

**Parameters:**
- `param_name`: The name of the route parameter (e.g., "connection_name", "orgId")

**Returns:** `str` - The parameter value

**Raises:** `ValueError` if parameter is missing (automatically handled by `@with_request_context` decorator as 401 error)

## Migration Checklist

When migrating an endpoint to use proper type checking:

- [ ] Add import: `from shared.types import get_context, get_route_param`
- [ ] Replace `context = req.context` with `context = get_context(req)`
- [ ] Replace `param = req.route_params.get("param")` with `param = get_route_param(req, "param")`
- [ ] Remove manual None checks for route params (get_route_param handles this)
- [ ] Run `python3 -m py_compile` to verify syntax
- [ ] Check Pylance errors are resolved

## Files Already Migrated

✅ `functions/oauth_api.py` - All 11 endpoints migrated
✅ `shared/types.py` - Type definitions created

## Files That May Need Migration

Check any file using `@with_request_context` decorator:
- `functions/organizations.py`
- `functions/roles.py`
- `functions/forms.py`
- `functions/workflows.py`
- `functions/config.py`
- And others...

Run this command to find them:
```bash
grep -r "@with_request_context" functions/ --include="*.py"
```
