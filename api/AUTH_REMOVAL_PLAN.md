# Remove @require_auth Decorator - Use Azure Functions Auth Instead

## Current Problem

The codebase has redundant authentication:

1. **Function App** is set to `http_auth_level=func.AuthLevel.ANONYMOUS`
2. **Every endpoint** then uses `@require_auth` decorator to add authentication back
3. **@require_auth** is using the OLD authentication model (`req.user` instead of `req.principal`)
4. Azure Functions **already has built-in authentication** via `auth_level` parameter

## Why This Is Wrong

### Azure Functions Has 3 Built-in Auth Levels:

```python
func.AuthLevel.ANONYMOUS  # No auth required (public)
func.AuthLevel.FUNCTION   # Requires function key (x-functions-key or ?code=xxx)
func.AuthLevel.ADMIN      # Requires master key (admin only)
```

When you set `auth_level=func.AuthLevel.FUNCTION`, Azure Functions:
- Automatically checks for function key in header or query param
- Returns 401 if missing
- No decorator needed!

### SWA (Static Web Apps) Already Handles User Auth:

When a user logs in via SWA:
- SWA injects `X-MS-CLIENT-PRINCIPAL` header
- Contains user ID, email, roles
- No decorator needed!

### What We're Doing Now (WRONG):

```python
# function_app.py
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)  # No auth!

# health.py
@bp.route(route="health/keyvault", methods=["GET"])  # Still no auth!
@require_auth  # NOW we add auth with a decorator
def keyvault_health(req: func.HttpRequest):
    user = req.user  # OLD model, doesn't match new code
```

### What We Should Do (RIGHT):

```python
# function_app.py
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)  # Default: require auth

# health.py
@bp.route(route="health/keyvault", methods=["GET"])  # Auth already required!
def keyvault_health(req: func.HttpRequest):
    # If you need user info, get from SWA header
    principal_header = req.headers.get('X-MS-CLIENT-PRINCIPAL')

    # If you need org context, get from header
    org_id = req.headers.get('X-Organization-Id')
```

## Comparison with Engine Code (CORRECT)

The engine already does this correctly:

```python
# engine/execute.py
@bp.route(route="workflows/{workflowName}", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
@with_org_context
async def execute_workflow(req: func.HttpRequest):
    # Azure Functions checks function key automatically
    # @with_org_context extracts org/user from headers
    context = req.context
    user_id = context.caller.user_id
```

**No `@require_auth` needed!**

## Migration Plan

### Option 1: Remove All @require_auth (Recommended)

**Step 1: Change FunctionApp default**
```python
# function_app.py
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
```

**Step 2: Remove @require_auth from all endpoints**
```bash
# Find all usages
grep -r "@require_auth" api/functions/ --include="*.py"

# Remove decorator and update code to get user from headers directly
```

**Step 3: For public endpoints, override with ANONYMOUS**
```python
@bp.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def public_health(req: func.HttpRequest):
    return func.HttpResponse('{"status": "ok"}')
```

### Option 2: Use Middleware Instead (Like Engine)

Create a proper middleware that:
1. Runs AFTER Azure Functions auth (function key already checked)
2. Extracts user from SWA header if present
3. Injects into request context

```python
# shared/middleware.py
def with_user_context(handler):
    """
    Middleware to extract user from SWA headers (if present).
    Use AFTER Azure Functions has already checked function key.
    """
    @wraps(handler)
    async def wrapper(req: func.HttpRequest):
        # Get user from SWA (optional - may be function key call)
        principal_header = req.headers.get('X-MS-CLIENT-PRINCIPAL')
        if principal_header:
            req.user = parse_swa_principal(principal_header)
        else:
            req.user = None  # Function key call, no user

        return await handler(req)
    return wrapper

# Usage:
@bp.route(route="health/keyvault", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
@with_user_context
async def keyvault_health(req: func.HttpRequest):
    user = req.user  # May be None if function key call
    if user:
        logger.info(f"User {user.email} checking health")
```

## What to Keep

From the current auth.py, we should keep:

1. **`FunctionKeyPrincipal` / `UserPrincipal` classes** - Used by engine
2. **`AuthenticationService`** - Used by `@with_org_context` in engine
3. **`is_platform_admin()`** - Used for authorization checks
4. **`get_user_org_id()`** - Used for org context

## What to Remove

1. **`@require_auth` decorator** - Redundant with Azure Functions auth
2. **`AuthenticatedUser` class** - Old model, replaced by `UserPrincipal`
3. **`get_authenticated_user()`** - Old function with hardcoded test users
4. **`require_org_header` decorator** - Not used
5. **`get_org_id()` function** - Trivial one-liner
6. **All hardcoded "jack@gocovi.com" test users**

## Benefits

| Aspect | Before | After |
|--------|--------|-------|
| **Auth location** | Python decorator | Azure Functions (platform) |
| **Test users** | Hardcoded in code | None (use real function keys locally) |
| **Lines of code** | 1,033 lines | ~200 lines |
| **Confusion** | High (two systems) | Low (one system) |
| **Maintainability** | Hard | Easy |
| **Security** | Risk of hardcoded users | Platform-managed |

## Recommendation

**Remove @require_auth entirely**:
1. Change FunctionApp to `http_auth_level=func.AuthLevel.FUNCTION`
2. Remove all `@require_auth` decorators
3. Keep only the engine's authentication system (`@with_org_context`)
4. Public endpoints explicitly set `auth_level=func.AuthLevel.ANONYMOUS`

This aligns with Azure Functions best practices and matches the engine's correct implementation.
