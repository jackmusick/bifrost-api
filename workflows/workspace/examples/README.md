# Example Workflows (T067)

Example workflows demonstrating best practices and common patterns.

## Available Examples

### 1. Hello World (`hello_world.py`)

The simplest possible workflow demonstrating:
- Basic `@workflow` and `@param` decorators
- Context usage (`context.log`, `context.org`, `context.caller`)
- Return value structure

**Test:**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org-active" \
  -H "x-functions-key: test_key" \
  -d '{"name": "Alice"}' \
  http://localhost:7072/api/workflows/hello_world
```

### 2. Error Handling (`error_handling.py`)

Demonstrates structured error handling:
- `ValidationError` for input validation (HTTP 400)
- `IntegrationError` for external API failures (HTTP 500)
- Detailed error messages with context

**Test:**
```bash
# Success case
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org-active" \
  -H "x-functions-key: test_key" \
  -d '{"operation": "success"}' \
  http://localhost:7072/api/workflows/error_handling_example

# Validation error (HTTP 400)
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org-active" \
  -H "x-functions-key: test_key" \
  -d '{"operation": "validate"}' \
  http://localhost:7072/api/workflows/error_handling_example

# Integration error (HTTP 500)
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org-active" \
  -H "x-functions-key: test_key" \
  -d '{"operation": "integrate"}' \
  http://localhost:7072/api/workflows/error_handling_example
```

## Running Examples

### Prerequisites

1. Azurite running
2. Test data seeded
3. Azure Functions running

```bash
# Start Azurite
azurite --silent --location /tmp/azurite

# Seed data
python scripts/seed_azurite.py

# Start Functions
func start
```

### Testing Examples

All examples use function key authentication for local testing:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org-active" \
  -H "x-functions-key: test_key" \
  -d '{PARAMETERS}' \
  http://localhost:7072/api/workflows/WORKFLOW_NAME
```

## Creating Your Own Workflows

Use these examples as templates:

1. Copy an example to `/workspace/workflows/`
2. Modify the workflow logic
3. Restart Azure Functions to register
4. Test with curl or your client

**Remember:**
- Only import from public API (`engine.shared.decorators`, `engine.shared.context`, etc.)
- Always use async functions
- Return JSON-serializable data
- Use structured error handling
- Log important steps

## Additional Resources

- **Workspace API**: `/docs/workspace-api.md`
- **Local Development**: `/docs/local-development.md`
- **Migration Guide**: `/docs/migration-guide.md`
