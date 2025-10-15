# Test Suite Guide

This guide shows you how to run the full test suite for the Bifrost Integrations API.

## Test Structure

The test suite is organized into three layers following the test pyramid approach:

```
tests/
├── contract/              # Contract/schema validation tests
├── integration_e2e/       # End-to-end integration tests (real HTTP, Azurite)
├── engine/
│   ├── unit/             # Engine unit tests
│   ├── contract/         # Engine contract tests
│   └── integration/      # Engine integration tests
└── helpers/              # Test helper utilities
```

## Quick Start

### Run ALL Tests

```bash
# Simplest way (recommended)
npm test

# Or directly with pytest
pytest

# Or with explicit path
PYTHONPATH=. python -m pytest tests/ -v
```

> **Note**: The `npm test` command is defined in `package.json` and runs `pytest` with proper configuration from `pytest.ini`.

### Run Tests by Layer

#### 1. Contract Tests (Schema Validation)
Fast tests that validate data models and API contracts:

```bash
# Simple way
pytest tests/contract/ -v

# Or with full path
PYTHONPATH=. python -m pytest tests/contract/ -v
```

#### 2. End-to-End Integration Tests
Tests against real running API with Azurite:

```bash
# Make sure Azurite is running first!
# Terminal 1: Start Azurite
azurite --silent --location /tmp/azurite --debug /tmp/azurite/debug.log

# Terminal 2: Start API
func start --port 7072

# Terminal 3: Run E2E tests
PYTHONPATH=. python -m pytest tests/integration_e2e/ -v
```

**E2E Test Categories:**
- `test_organizations_e2e.py` - Organizations CRUD (9 tests)
- `test_forms_e2e.py` - Forms CRUD (11 tests)
- `test_config_e2e.py` - Config management (15 tests)
- `test_oauth_e2e.py` - OAuth connections (12 tests)
- `test_roles_permissions_e2e.py` - Roles & permissions (11 tests)
- `test_workflow_execution_e2e.py` - Workflow execution (7 tests)
- `test_security_e2e.py` - Security & authorization (22 tests) ⭐

#### 3. Engine Tests
Workflow engine tests:

```bash
# All engine tests
PYTHONPATH=. python -m pytest tests/engine/ -v

# Just engine unit tests
PYTHONPATH=. python -m pytest tests/engine/unit/ -v

# Just engine contract tests
PYTHONPATH=. python -m pytest tests/engine/contract/ -v
```

## Common Test Commands

### Run Specific Test File

```bash
PYTHONPATH=. python -m pytest tests/integration_e2e/test_security_e2e.py -v
```

### Run Specific Test Class

```bash
PYTHONPATH=. python -m pytest tests/integration_e2e/test_security_e2e.py::TestOAuthAccessControl -v
```

### Run Specific Test

```bash
PYTHONPATH=. python -m pytest tests/integration_e2e/test_security_e2e.py::TestOAuthAccessControl::test_org_user_cannot_create_oauth_connection -v
```

### Run with Detailed Output

```bash
# Show print statements
PYTHONPATH=. python -m pytest tests/ -v -s

# Show full error tracebacks
PYTHONPATH=. python -m pytest tests/ -v --tb=long

# Show short tracebacks (recommended)
PYTHONPATH=. python -m pytest tests/ -v --tb=short
```

### Run Only Failed Tests

```bash
# Run only tests that failed in last run
PYTHONPATH=. python -m pytest tests/ --lf -v

# Run failed tests first, then all others
PYTHONPATH=. python -m pytest tests/ --ff -v
```

### Filter Tests by Name

```bash
# Run all tests with "oauth" in the name
PYTHONPATH=. python -m pytest tests/ -k oauth -v

# Run all tests with "security" in the name
PYTHONPATH=. python -m pytest tests/ -k security -v

# Run all tests that DON'T have "slow" in name
PYTHONPATH=. python -m pytest tests/ -k "not slow" -v
```

### Generate Test Coverage Report

```bash
# Run tests with coverage
PYTHONPATH=. python -m pytest tests/ --cov=. --cov-report=html

# Open coverage report
open htmlcov/index.html
```

## Test Output Modes

### Minimal Output (quieter)

```bash
PYTHONPATH=. python -m pytest tests/ -q
```

### Verbose Output (recommended)

```bash
PYTHONPATH=. python -m pytest tests/ -v
```

### Very Verbose (shows each assertion)

```bash
PYTHONPATH=. python -m pytest tests/ -vv
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
cd /Users/jack/GitHub/bifrost-integrations/api
func start --port 7072
```

### 3. Seed Test Data (Optional - E2E tests create their own data)

```bash
# If you want pre-seeded data
./tests/integration_e2e/setup.sh
```

### 4. Run E2E Tests

```bash
# Terminal 3
PYTHONPATH=. python -m pytest tests/integration_e2e/ -v
```

## Test Configuration

### Environment Variables

The E2E tests use these default values:

```python
BASE_URL = "http://localhost:7072/api"
STORAGE_CONNECTION_STRING = "UseDevelopmentStorage=true"
```

You can override them:

```bash
# Use different API URL
BASE_URL="http://different-url/api" PYTHONPATH=. python -m pytest tests/integration_e2e/ -v

# Use different storage
STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;..." PYTHONPATH=. python -m pytest tests/integration_e2e/ -v
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
```

## Test Fixtures

E2E tests use these fixtures (defined in `tests/integration_e2e/conftest.py`):

- `base_url` - API base URL (http://localhost:7072/api)
- `platform_admin_headers` - Headers for platform admin user
- `org_user_headers` - Headers for org user (jack@gocovi.dev)
- `anonymous_headers` - Headers with no auth (empty dict)

## Continuous Integration

For CI/CD pipelines:

```bash
# Run all tests with JUnit XML output
PYTHONPATH=. python -m pytest tests/ -v --junitxml=test-results.xml

# Run with coverage and XML output
PYTHONPATH=. python -m pytest tests/ --cov=. --cov-report=xml --junitxml=test-results.xml
```

## Troubleshooting

### "ModuleNotFoundError"

Make sure you're setting `PYTHONPATH`:

```bash
PYTHONPATH=. python -m pytest tests/ -v
```

### E2E Tests Failing with Connection Errors

1. Check Azurite is running: `curl http://127.0.0.1:10002/devstoreaccount1`
2. Check API is running: `curl http://localhost:7072/api/health`
3. Check for port conflicts: `lsof -i :7072` and `lsof -i :10000-10002`

### "No tests collected"

Check you're in the `/api` directory and test files start with `test_`:

```bash
pwd  # Should show: /Users/jack/GitHub/bifrost-integrations/api
ls tests/integration_e2e/test_*.py
```

## Test Statistics

Current test coverage (as of last update):

- **Contract Tests**: ~15 tests (schema validation)
- **E2E Integration Tests**: 87 tests
  - Organizations: 9 tests
  - Forms: 11 tests
  - Config: 15 tests
  - OAuth: 12 tests
  - Roles/Permissions: 11 tests
  - Workflow Execution: 7 tests
  - **Security: 22 tests** ⭐
- **Engine Tests**: ~26 tests
- **Total**: ~128 tests

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
PYTHONPATH=. python -m pytest tests/integration_e2e/test_security_e2e.py -v
```

## Quick Commands

```bash
# Run all tests
npm test

# Run with coverage
pytest --cov=. --cov-report=html

# Run only security tests
pytest tests/integration_e2e/test_security_e2e.py -v

# Run only failed tests from last run
pytest --lf

# Run with verbose output
pytest -v
```

## Next Steps

1. **Before committing code**: Run contract tests (fast validation)
   ```bash
   pytest tests/contract/ -v
   ```

2. **Before pushing to main**: Run full E2E suite
   ```bash
   pytest tests/integration_e2e/ -v
   ```

3. **For comprehensive validation**: Run entire test suite
   ```bash
   npm test
   # or just: pytest
   ```

4. **Check everything** (lint + typecheck + tests):
   ```bash
   npm run check
   ```
