# Test Suite Guide

This guide shows you how to run the full test suite for the Bifrost Integrations API.

## Migration Complete!

All E2E tests have been successfully migrated to integration tests that call Azure Functions directly (no HTTP). This provides:
- **10-100x faster test execution** (1.44 seconds vs 30+ seconds)
- **Same business logic coverage** as E2E tests
- **Reliable CI execution** without Azure Functions host dependencies
- **E2E tests preserved** for manual HTTP testing when needed

## Test Structure

The test suite is organized into three layers following the test pyramid approach:

```
tests/
├── unit/                  # Unit tests (fast, isolated)
│   ├── models/           # Pydantic model validation tests
│   ├── services/         # Service layer unit tests
│   ├── functions/        # Function logic unit tests
│   └── engine/           # Engine unit tests
├── integration/          # Integration tests (call functions directly, no HTTP)
│   ├── api/             # API function integration tests
│   ├── engine/          # Engine integration tests
│   └── workflows/       # Full workflow tests
├── e2e/                  # End-to-end tests (real HTTP, excluded from CI)
│   └── ...              # E2E tests hitting actual HTTP endpoints
└── helpers/              # Test helper utilities
```

### Test Layers Explained

1. **Unit Tests** (`tests/unit/`)
   - Fast, isolated tests that don't require external dependencies
   - Test individual functions, models, and logic
   - Run in milliseconds
   - Included in CI

2. **Integration Tests** (`tests/integration/`)
   - Test components working together
   - Call Azure Functions directly (no HTTP)
   - Test service layer + storage + business logic
   - Included in CI

3. **E2E Tests** (`tests/e2e/`)
   - Test actual HTTP endpoints with Azure Functions running
   - Require Azure Functions host and Azurite
   - Slow but comprehensive
   - **Excluded from CI** - run manually/locally

## Quick Start

### Run ALL Tests (Unit + Integration)

```bash
# Simplest way (recommended)
npm test

# Or directly with pytest
pytest

# Or with explicit path
pytest tests/ -v
```

> **Note**: E2E tests are excluded by default (configured in `pytest.ini`)

### Run Tests by Layer

#### Unit Tests (Fastest)

```bash
# All unit tests
pytest tests/unit/ -v

# Just model validation tests
pytest tests/unit/models/ -v

# Just engine unit tests
pytest tests/unit/engine/ -v
```

#### Integration Tests

Integration tests require Azurite to be running and test data to be seeded:

```bash
# 1. Start Azurite (if not already running)
azurite --silent --location /tmp/azurite --debug /tmp/azurite/debug.log &

# 2. Seed test data (automatically resets tables for development storage)
AzureWebJobsStorage="UseDevelopmentStorage=true" python seed_data.py

# 3. Run integration tests
pytest tests/integration/ -v

# Just API integration tests
pytest tests/integration/api/ -v

# Just engine integration tests
pytest tests/integration/engine/ -v
```

**Integration Test Features:**
- Call Azure Functions directly (no HTTP overhead)
- 10-100x faster than E2E tests
- Same coverage as E2E for business logic and authorization
- Automatically included in CI

#### E2E Tests (Requires Azure Functions Running)

```bash
# Make sure Azure Functions is running first!
# Terminal 1: Start Azurite
azurite --silent --location /tmp/azurite --debug /tmp/azurite/debug.log

# Terminal 2: Start API
func start --port 7071

# Terminal 3: Run E2E tests
pytest tests/e2e/ -v
```

**E2E Test Categories:**

- `test_organizations_e2e.py` - Organizations CRUD (9 tests)
- `test_forms_e2e.py` - Forms CRUD (11 tests)
- `test_config_e2e.py` - Config management (15 tests)
- `test_oauth_e2e.py` - OAuth connections (12 tests)
- `test_roles_permissions_e2e.py` - Roles & permissions (11 tests)
- `test_workflow_execution_e2e.py` - Workflow execution (7 tests)
- `test_security_e2e.py` - Security & authorization (22 tests) ⭐

## Common Test Commands

### Run Specific Test File

```bash
pytest tests/unit/models/test_oauth_api_contract.py -v
```

### Run Specific Test Class

```bash
pytest tests/e2e/test_security_e2e.py::TestOAuthAccessControl -v
```

### Run Specific Test

```bash
pytest tests/e2e/test_security_e2e.py::TestOAuthAccessControl::test_org_user_cannot_create_oauth_connection -v
```

### Run with Detailed Output

```bash
# Show print statements
pytest tests/ -v -s

# Show full error tracebacks
pytest tests/ -v --tb=long

# Show short tracebacks (recommended)
pytest tests/ -v --tb=short
```

### Run Only Failed Tests

```bash
# Run only tests that failed in last run
pytest tests/ --lf -v

# Run failed tests first, then all others
pytest tests/ --ff -v
```

### Filter Tests by Name

```bash
# Run all tests with "oauth" in the name
pytest tests/ -k oauth -v

# Run all tests with "security" in the name
pytest tests/ -k security -v

# Run all tests that DON'T have "slow" in name
pytest tests/ -k "not slow" -v
```

### Generate Test Coverage Report

```bash
# Run tests with coverage
pytest tests/ --cov=. --cov-report=html

# Open coverage report
open htmlcov/index.html
```

## Test Output Modes

### Minimal Output (quieter)

```bash
pytest tests/ -q
```

### Verbose Output (recommended)

```bash
pytest tests/ -v
```

### Very Verbose (shows each assertion)

```bash
pytest tests/ -vv
```

## Prerequisites for E2E Tests

E2E tests require the following to be running:

### 1. Start Azurite (Local Azure Storage Emulator)

```bash
# Terminal 1
azurite --silent --location /tmp/azurite --debug /tmp/azurite/debug.log
```

### 2. Start Azure Functions API

```bash
# Terminal 2
func start --port 7071
```

### 3. Run E2E Tests

```bash
# Terminal 3
pytest tests/e2e/ -v
```

## Test Configuration

### Environment Variables

The E2E tests use these default values:

```python
BASE_URL = "http://localhost:7071/api"
STORAGE_CONNECTION_STRING = "UseDevelopmentStorage=true"
```

You can override them:

```bash
# Use different API URL
BASE_URL="http://different-url/api" pytest tests/e2e/ -v

# Use different storage
STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;..." pytest tests/e2e/ -v
```

### Pytest Configuration

Configuration is in `pytest.ini`:

```ini
[pytest]
pythonpath = .
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto

# Exclude E2E tests by default (run with pytest tests/e2e to run them)
addopts = --ignore=tests/e2e
```

## Seed Data for Integration Tests

Integration tests require seed data to be loaded into Azurite. The `seed_data.py` script provides a safe way to reset test data.

### Running Seed Script

```bash
# For development storage only (Azurite)
AzureWebJobsStorage="UseDevelopmentStorage=true" python seed_data.py
```

### Safety Features

The seed script has built-in safety features to prevent accidental data loss:

1. **Development Storage Only**: Only resets tables when using `UseDevelopmentStorage=true` or `devstoreaccount1`
2. **Production Protection**: Refuses to delete tables if using production storage connection strings
3. **Clean Slate**: Deletes all tables, recreates them, and inserts fresh seed data
4. **Idempotent**: Safe to run multiple times

### Tables Reset

When using development storage, the script resets these tables:
- `Config` - System and organization configuration
- `Entities` - Organizations, forms, workflows, etc.
- `Relationships` - User permissions, org memberships, etc.
- `Users` - User accounts

### Example Output

```
🔄 Development storage detected - resetting tables...
  ✓ Deleted table: Config
  ✓ Deleted table: Entities
  ✓ Deleted table: Relationships
  ✓ Deleted table: Users
  ✓ Created table: Config
  ✓ Created table: Entities
  ✓ Created table: Relationships
  ✓ Created table: Users
✓ Tables reset complete

Seeding Config table...
  ✓ Inserted Config: system:version...
  ✓ Inserted Config: system:maintenance_mode...
  ...
```

## Test Fixtures

### Unit Test Fixtures

Defined in `tests/conftest.py`:

- `mock_table_client` - Mock Azure Table Storage client
- `mock_context` - Mock request context

### Integration Test Helpers

Defined in `tests/helpers/http_helpers.py`:

- `create_mock_request()` - Create mock HttpRequest for Azure Functions
- `create_platform_admin_headers()` - Headers with platform admin role
- `create_org_user_headers()` - Headers with org user role
- `create_anonymous_headers()` - Headers with no authentication
- `parse_response()` - Parse HttpResponse to (status_code, body_dict)

### E2E Test Fixtures

Defined in `tests/e2e/conftest.py`:

- `base_url` - API base URL (http://localhost:7071/api)
- `platform_admin_headers` - Headers for platform admin user
- `org_user_headers` - Headers for org user (jack@gocovi.dev)
- `anonymous_headers` - Headers with no auth

## Continuous Integration

In CI (GitHub Actions), we run **unit + integration tests only** (E2E tests excluded):

```bash
# Run all tests with JUnit XML output
pytest tests/ -v --junitxml=test-results.xml

# Run with coverage and XML output
pytest tests/ --cov=. --cov-report=xml --junitxml=test-results.xml
```

## Troubleshooting

### "ModuleNotFoundError"

Make sure you're in the `/api` directory:

```bash
cd /Users/jack/GitHub/bifrost-integrations/api
pytest tests/ -v
```

### Integration Tests Failing with "TableNotFound"

Integration tests require seed data. Run the seed script:

```bash
AzureWebJobsStorage="UseDevelopmentStorage=true" python seed_data.py
```

### Integration Tests Failing with "Connection refused"

Make sure Azurite is running:

```bash
# Check if Azurite is running
curl http://127.0.0.1:10002/devstoreaccount1

# Start Azurite if not running
azurite --silent --location /tmp/azurite --debug /tmp/azurite/debug.log &
```

### E2E Tests Failing with Connection Errors

1. Check Azurite is running: `curl http://127.0.0.1:10002/devstoreaccount1`
2. Check API is running: `curl http://localhost:7071/api/health`
3. Check for port conflicts: `lsof -i :7071` and `lsof -i :10000-10002`

### "No tests collected"

Check you're in the `/api` directory and test files start with `test_`:

```bash
pwd  # Should show: /Users/jack/GitHub/bifrost-integrations/api
ls tests/unit/test_*.py
```

### E2E Tests Not Running

E2E tests are excluded by default. Run them explicitly:

```bash
pytest tests/e2e/ -v
```

## Test Statistics

Current test coverage (fully migrated integration tests):

- **Unit Tests**: ~307 tests
  - Model validation: ~101 tests
  - Engine unit: ~59 tests
  - Authorization: ~37 tests
  - Request context: ~110 tests
- **Integration Tests**: 154 tests (all migrated from E2E!)
  - API integration: 87 tests
    - Organizations: 9 tests
    - Forms: 11 tests
    - Config: 14 tests
    - OAuth: 10 tests
    - Roles/Permissions: 15 tests
    - Workflow Execution: 7 tests
    - Security: 21 tests
  - Engine integration: 67 tests
- **E2E Tests**: 87 tests (excluded from CI, kept for manual HTTP testing)
  - Organizations: 9 tests
  - Forms: 11 tests
  - Config: 15 tests
  - OAuth: 12 tests
  - Roles/Permissions: 11 tests
  - Workflow Execution: 7 tests
  - **Security: 22 tests** ⭐
- **Total CI Tests**: ~461 tests (unit + integration)
- **Total All Tests**: ~548 tests (including E2E)

## Key Security Tests

The security test suite (`test_security_e2e.py`) validates:

✅ Cross-org data isolation
✅ Platform admin authorization
✅ Org user access restrictions
✅ OAuth connection access control (9 tests)
✅ Config endpoint protection
✅ Sensitive data masking

Run security tests:

```bash
pytest tests/e2e/test_security_e2e.py -v
```

## Quick Commands

```bash
# Run unit + integration tests (default, CI)
npm test
# or: pytest

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests only
pytest tests/integration/ -v

# Run E2E tests (requires Azure Functions running)
pytest tests/e2e/ -v

# Run with coverage
pytest --cov=. --cov-report=html

# Run only security tests
pytest tests/e2e/test_security_e2e.py -v

# Run only failed tests from last run
pytest --lf

# Run with verbose output
pytest -v
```

## Best Practices

### When to Use Each Test Type

1. **Unit Tests** - Use when testing:
   - Pydantic model validation
   - Individual function logic
   - Pure business logic without external dependencies

2. **Integration Tests** - Use when testing:
   - Services interacting with storage
   - Multiple components working together
   - Functions with mocked Azure Functions context

3. **E2E Tests** - Use when testing:
   - Full HTTP request/response cycle
   - Authentication/authorization flows
   - Complete user workflows

### Development Workflow

1. **Before committing code**: Run unit tests (fast validation)
   ```bash
   pytest tests/unit/ -v
   ```

2. **Before pushing to main**: Run unit + integration tests
   ```bash
   pytest tests/ -v
   ```

3. **Before releasing**: Run E2E tests manually
   ```bash
   pytest tests/e2e/ -v
   ```

4. **Check everything** (lint + typecheck + tests):
   ```bash
   npm run check
   ```

## Converting E2E to Integration Tests

We're gradually converting E2E tests to integration tests for faster CI runs. Integration tests call functions directly instead of making HTTP requests:

**E2E approach** (slow, requires Azure Functions):
```python
response = requests.get(f"{base_url}/oauth/connections", headers=headers)
assert response.status_code == 200
```

**Integration approach** (fast, no HTTP):
```python
from functions.oauth_api import list_oauth_connections
import azure.functions as func

req = func.HttpRequest(method='GET', url='/api/oauth/connections', headers=headers)
response = list_oauth_connections(req)
assert response.status_code == 200
```

This provides the same coverage but runs 10-100x faster and works reliably in CI.
