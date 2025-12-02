# Testing Guide for Bifrost Integrations

## Quick Start

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run only unit tests (fast)
pytest -m unit

# Run integration tests (starts isolated infrastructure)
pytest -m integration

# Run with coverage
pytest --cov=shared --cov=functions
```

## Architecture

### Isolated Test Infrastructure

Integration tests use **real HTTP requests** to a **FastAPI server** running on isolated infrastructure with Docker containers:

| Service | Dev Ports | Test Ports |
|---------|-----------|------------|
| **PostgreSQL** | 5432 | 5433 |
| **RabbitMQ** | 5672 | 5673 |
| **Redis** | 6379 | 6380 |
| **FastAPI** | 8000 | 8001 |

This ensures:
- **No conflicts** between dev and test environments (different ports)
- **Real HTTP stack** - tests exercise actual code paths users will experience
- **Fast startup** - infrastructure starts once per test session, then reused
- **Clean isolation** - each test gets fresh data via database cleanup

### Key Principles

1. **Real HTTP for integration tests** - Not mock requests, not direct function calls
2. **No seed data** - Tests create entities organically through API calls
3. **Test user journeys** - Follow actual workflows from first login to complex operations
4. **Mock external dependencies** - Only mock what we can't run locally (Key Vault, Graph API)
5. **Isolated test state** - Each test starts clean, no pollution

## Test Types

### Unit Tests (`tests/unit/`)
- Test business logic in isolation
- Mock all external dependencies
- Speed: <5s total for all unit tests
- Marker: `@pytest.mark.unit`

### Integration Tests (`tests/integration/`)
- Test complete API endpoints via real HTTP
- Use real Azure Functions + Azurite
- Create data organically (no seed data)
- Marker: `@pytest.mark.integration`

### E2E Tests (`tests/e2e/`)
- Test complete multi-step user journeys
- Full stack from auth to workflow completion
- Marker: `@pytest.mark.e2e`

## Session Fixtures

These initialize once per test session and are shared:
- `test_db` - Isolated PostgreSQL database (port 5433)
- `test_rabbitmq` - Isolated RabbitMQ broker (port 5673)
- `test_redis` - Isolated Redis cache (port 6380)
- `fastapi_server` - FastAPI server (port 8001)

## Function Fixtures

These create fresh state for each test:
- `db_session` - Database session with automatic cleanup
- Database fixture factories for creating test entities
- `test_org`, `test_user`, `test_form` - Test entities

## Special Fixtures

- `isolated_registry` - Clean WorkflowRegistry (prevents state pollution in unit tests)

## Authentication Helpers

Located in `tests/fixtures/auth.py`:

```python
from tests.fixtures.auth import create_test_jwt, auth_headers, org_headers

# Create JWT token
token = create_test_jwt(email="user@test.com", name="Test User")

# Add to request headers
headers = auth_headers(token)

# With organization context
headers = org_headers("org-123", token)
```

## Running Tests

### All Tests
```bash
pytest
pytest -v  # Verbose
pytest --cov=shared --cov=functions  # With coverage
```

### By Type
```bash
pytest -m unit  # Just unit tests
pytest -m integration  # Just integration tests
pytest -m e2e  # Just E2E tests
```

### Specific Tests
```bash
pytest tests/integration/test_user_provisioning_journey.py
pytest tests/integration/test_organization_journey.py::TestOrganizationJourney
pytest tests/integration/test_organization_journey.py::TestOrganizationJourney::test_admin_creates_organization
```

## Integration Test Patterns

### User Journey
```python
@pytest.mark.integration
def test_user_creates_organization(fastapi_server):
    # 1. User authenticates
    token = create_test_jwt(email="user@test.com")

    # 2. Create organization via HTTP
    response = requests.post(
        f"{fastapi_server}/api/organizations",
        json={"name": "Test Org"},
        headers=auth_headers(token)
    )

    assert response.status_code == 201
```

### Multi-User Scenario
```python
@pytest.mark.integration
def test_org_isolation(fastapi_server):
    # Create two organizations
    admin_token = create_test_jwt(email="admin@platform.com")

    org_a = requests.post(
        f"{fastapi_server}/api/organizations",
        json={"name": "Org A"},
        headers=auth_headers(admin_token)
    ).json()

    # Each org's data is isolated
    ...
```

## Journey Tests

Integration tests follow real user workflows:

- **test_user_provisioning_journey.py** - First user becomes admin, domain-based assignment
- **test_organization_journey.py** - Create orgs, auto-join by domain
- **test_config_journey.py** - Global configs with org overrides
- **test_secrets_journey.py** - Org secret isolation
- **test_forms_journey.py** - Form creation with data providers
- **test_workflow_execution_journey.py** - Workflow execution with configs/secrets
- **test_form_context_journey.py** - Form launch workflows and visibility

## Troubleshooting

### "FastAPI server failed to start"
- Ensure port 8001 is available
- Check Docker containers are running: `docker ps`
- View logs: `docker logs bifrost-api-test`

### "PostgreSQL connection failed"
- Ensure port 5433 is available
- Check database is healthy: `docker exec bifrost-postgres-test psql -U postgres -d bifrost_test -c "SELECT 1"`

### "RabbitMQ connection failed"
- Ensure port 5673 is available
- Check: `docker ps | grep rabbitmq`

### Tests timeout
- First run may be slow (container startup)
- Increase timeout: `pytest --timeout=300`

### State pollution
- Each test gets fresh database
- Unit tests use `isolated_registry` fixture
- Cleanup runs automatically after each test

## Best Practices

1. Use real HTTP for integration tests (not mock requests)
2. Create data via APIs (not direct table manipulation)
3. Follow user journeys (tests should feel realistic)
4. Mark tests appropriately (`@pytest.mark.unit`, etc.)
5. Isolate test state (no cross-test dependencies)
6. Use fixtures for common setup
7. Document complex test logic
