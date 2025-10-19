# Testing Guide

## Test Organization

Tests are organized by type using pytest markers:

### Test Types

1. **Unit Tests** (`@pytest.mark.unit`)
   - Location: `tests/unit/`
   - **No dependencies** - fully mocked
   - Fast execution
   - Run anytime

2. **Integration Tests** (`@pytest.mark.integration`)
   - Location: `tests/integration/`
   - May require Azurite (Azure Table Storage emulator)
   - Tests handlers directly (no HTTP)

3. **API Integration Tests** (`@pytest.mark.requires_api`)
   - Location: `tests/integration/api/`
   - **REQUIRES** Azure Functions API running
   - Makes real HTTP requests to `http://localhost:7071`
   - Tests full HTTP stack (routing, middleware, auth, handlers)

4. **Contract Tests**
   - Location: `tests/contract/`
   - Validates Pydantic model schemas
   - No external dependencies

## Running Tests

### All Tests (Except API-dependent)
```bash
pytest tests/ -m "not requires_api"
```
**Result**: ~1631 tests should pass

### Only Unit Tests
```bash
pytest tests/unit/ -v
```
**Fast**: Completes in <10 seconds

### Only Integration Tests (No API required)
```bash
pytest tests/integration/engine/ -v
```
**Moderate**: Requires Azurite but not func start

### API Integration Tests (Requires func start)
```bash
# Terminal 1: Start API
cd api
func start --port 7071

# Terminal 2: Run API tests
pytest tests/ -m requires_api -v
```
**Result**: 8 API integration tests

### All Tests (Including API)
```bash
# Terminal 1: Start API
cd api
func start --port 7071

# Terminal 2: Run all tests
pytest tests/ -v
```
**Result**: All 1640 tests

## Test Dependencies

### Always Required
- Python 3.11
- pytest and plugins (see `requirements.txt`)

### Sometimes Required
- **Azurite** (Azure Storage Emulator)
  - Required for: Integration tests
  - Start with: `docker compose up azurite`

- **Azure Functions Runtime** (func start)
  - Required for: API integration tests (`@pytest.mark.requires_api`)
  - Start with: `cd api && func start --port 7071`

## Continuous Integration

### CI Pipeline (GitHub Actions)
```bash
# Fast feedback (no API tests)
pytest tests/ -m "not requires_api"

# Full validation (with func start)
pytest tests/  # Runs all tests including API
```

### Pre-commit Hook
```bash
# Run fast tests only
pytest tests/unit/ tests/contract/
```

## Test Coverage

Check coverage:
```bash
pytest tests/ --cov=functions --cov=shared --cov-report=html
open htmlcov/index.html
```

## Marking New Tests

### Unit Test Example
```python
# tests/unit/test_my_module.py
import pytest

@pytest.mark.unit
def test_my_function():
    """Test pure business logic"""
    assert my_function(1) == 2
```

### API Integration Test Example
```python
# tests/integration/api/test_my_endpoint.py
import pytest
import requests

pytestmark = pytest.mark.requires_api  # Mark entire file

def test_my_endpoint(api_base_url, platform_admin_headers):
    """Test via real HTTP request"""
    response = requests.get(f"{api_base_url}/api/my-endpoint", headers=platform_admin_headers)
    assert response.status_code == 200
```

## Troubleshooting

### Tests Timeout
- **Cause**: API not running
- **Fix**: Start `func start --port 7071` in a separate terminal

### Port 7071 Already in Use
```bash
lsof -i :7071
kill <PID>
```

### Azurite Connection Failed
```bash
docker compose up azurite -d
```

### Import Errors
```bash
pip install -r requirements.txt
```
