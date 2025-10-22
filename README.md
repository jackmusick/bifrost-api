# Bifrost API

**Azure Functions backend for the Bifrost Integrations Platform** - The workflow engine and API layer that powers automated integration services.

[![License: AGPL](https://img.shields.io/badge/License-AGPL-green.svg)](https://opensource.org/licenses/agpl)
[![Azure Functions](https://img.shields.io/badge/Azure%20Functions-v4-blue.svg)](https://azure.microsoft.com/en-us/services/functions/)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)

> **Note**: This repository contains only the backend API. For the frontend client, see [bifrost-client](https://github.com/jackmusick/bifrost-client).

---

## Table of Contents

- [What is Bifrost API?](#what-is-bifrost-api)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Development](#development)
- [Deployment](#deployment)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

---

## What is Bifrost API?

Bifrost API is the Azure Functions-based backend that powers the Bifrost Integrations Platform - an open-source automation platform designed for Integration Services businesses.

This repository provides:

- **Workflow Engine**: Python-based workflow execution with sandboxed environments
- **Multi-Tenant Architecture**: Complete data isolation per organization
- **OAuth Management**: Automated token refresh and credential storage
- **Secrets Management**: Secure integration with Azure Key Vault
- **Dynamic APIs**: Workflow-defined endpoints with OpenAPI documentation
- **File Storage**: Azure Files mounts for `/workspace` and `/tmp`

### Key Features

**Workflow Execution**
- Execute Python workflows with full language capabilities
- Sandbox execution with import restrictions for security
- Async workflow support with Azure Queue integration
- Automatic error handling and retry logic

**Multi-Tenancy**
- Organization-scoped data and configuration
- Role-based access control (RBAC)
- Complete tenant isolation at the database level

**Integration Management**
- OAuth 2.0 connection management with automatic refresh
- Secure secrets storage in Azure Key Vault
- Key/value configuration per organization
- Support for Microsoft Graph, HaloPSA, Pax8, and custom APIs

**Developer Experience**
- Hot reload with Azure Functions Core Tools
- Comprehensive test suite with pytest
- Type safety with Pydantic models
- OpenAPI specification auto-generation

---

## Quick Start

### Prerequisites

- Python 3.11+
- Azure Functions Core Tools v4
- Azure Storage Emulator (Azurite) or Azure Storage Account
- Azure Key Vault (production) or local emulator (development)

### Local Development

#### Option 1: Dev Container (Recommended)

Open in VS Code with the Dev Containers extension:

1. Open this repository in VS Code
2. Click "Reopen in Container" when prompted
3. Wait for container to build (~2 minutes)
4. Run:
   ```bash
   func start
   ```

The dev container includes:
- Python 3.11
- Azure Functions Core Tools
- Azure CLI
- Azurite (Azure Storage Emulator)
- All Python dependencies

#### Option 2: Manual Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Install Azure Functions Core Tools
npm install -g azure-functions-core-tools@4 --unsafe-perm true

# 3. Start Azurite (in separate terminal)
azurite --silent &

# 4. Configure local settings
cp local.settings.example.json local.settings.json
# Edit local.settings.json with your Azure Storage connection string

# 5. Start the Functions runtime
func start
```

**Access the API:**
- **API**: http://localhost:7071
- **OpenAPI Spec**: http://localhost:7071/api/openapi.json
- **Health Check**: http://localhost:7071/api/health

### Running Tests

**IMPORTANT**: Always use `./test.sh` to run tests, NOT `pytest` directly. The test script starts all required dependencies (Azurite, Functions runtime).

```bash
# Run all tests
./test.sh

# Run specific test file
./test.sh tests/integration/platform/test_sdk_from_workflow.py

# Run specific test
./test.sh tests/integration/platform/test_sdk_from_workflow.py::TestSDKFileOperations::test_file_path_sandboxing -v

# Run with coverage
./test.sh --coverage
```

### Quick API Test

```bash
# Test workflow execution with function key
curl -X POST \
  -H "Content-Type: application/json" \
  -H "x-functions-key: test" \
  -H "X-Organization-Id: test-org-active" \
  -d '{"name": "Alice", "language": "spanish"}' \
  http://localhost:7071/api/workflows/hello_world

# Expected: {"greeting": "¡Hola, Alice!", ...}
```

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│             Azure Functions (Python 3.11)               │
├─────────────────────────────────────────────────────────┤
│  HTTP Triggers          │  Timer Triggers               │
│  • Workflow Execution   │  • OAuth Token Refresh        │
│  • Organization Mgmt    │  • Execution Cleanup          │
│  • OAuth Config         │                               │
│  • Secrets Mgmt         │  Queue Triggers               │
│  • Dynamic Endpoints    │  • Async Workflow Worker      │
│  • GetRoles (SWA Auth)  │  • Poison Queue Handler       │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────▼─────┐   ┌───────▼──────┐   ┌─────▼──────┐
│   Azure     │   │    Azure     │   │   Azure    │
│   Tables    │   │    Files     │   │  Key Vault │
│             │   │              │   │            │
│ • Orgs      │   │ • /workspace │   │ • Secrets  │
│ • Users     │   │ • /tmp       │   │ • OAuth    │
│ • Executions│   │              │   │   Tokens   │
│ • Config    │   │              │   │            │
└─────────────┘   └──────────────┘   └────────────┘
```

### Project Structure

```
bifrost-api/
├── functions/                     # Azure Functions (HTTP/Timer/Queue triggers)
│   ├── http/                      # HTTP-triggered endpoints
│   │   ├── discovery.py           # Workflow discovery
│   │   ├── endpoints.py           # Dynamic workflow endpoints
│   │   ├── executions.py          # Execution management
│   │   ├── forms.py               # Form management
│   │   ├── organizations.py       # Organization CRUD
│   │   ├── users.py               # User management
│   │   └── openapi.py             # OpenAPI spec generation
│   ├── timer/                     # Timer-triggered functions
│   │   ├── oauth_refresh.py       # OAuth token refresh
│   │   └── execution_cleanup.py   # Old execution cleanup
│   └── queue/                     # Queue-triggered functions
│       ├── worker.py               # Async workflow worker
│       └── poison_queue_handler.py # Failed message handler
├── shared/                        # Business logic (NOT in functions/)
│   ├── models.py                  # Pydantic models (source of truth)
│   ├── async_executor.py          # Async workflow execution
│   ├── execution_logger.py        # Execution logging
│   ├── workflow_endpoint_utils.py # Dynamic endpoint helpers
│   ├── handlers/                  # Business logic handlers
│   │   ├── discovery_handlers.py
│   │   ├── endpoints_handlers.py
│   │   ├── executions_handlers.py
│   │   ├── forms_handlers.py
│   │   └── workflows_handlers.py
│   ├── repositories/              # Data access layer
│   │   ├── base_repository.py
│   │   ├── executions_repository.py
│   │   ├── organizations_repository.py
│   │   └── users_repository.py
│   └── services/                  # External services
│       ├── key_vault_service.py
│       └── blob_storage_service.py
├── sdk/                           # Bifrost SDK (available in workflows)
│   ├── __init__.py                # SDK public API
│   ├── _context.py                # Execution context
│   ├── _internal.py               # Internal helpers
│   ├── workflows.py               # Workflow operations
│   ├── executions.py              # Execution management
│   ├── organizations.py           # Organization operations
│   ├── secrets.py                 # Secrets access
│   ├── oauth.py                   # OAuth operations
│   ├── files.py                   # File operations
│   └── forms.py                   # Form operations
├── workspace/                     # User workflows (mounted from Azure Files)
│   └── examples/                  # Example workflows
├── tests/                         # Test suite
│   ├── contract/                  # Contract tests
│   ├── unit/                      # Unit tests
│   ├── integration/               # Integration tests
│   └── conftest.py                # Pytest configuration
├── bifrost.py                     # Azure Functions app registration
├── requirements.txt               # Python dependencies
├── host.json                      # Functions host configuration
├── local.settings.json            # Local development settings
├── test.sh                        # Test runner script
└── .devcontainer/                 # Dev container configuration
```

### Azure Resources

| Resource | Purpose | SKU |
|----------|---------|-----|
| **Azure Functions** | Workflow engine runtime | Flex Consumption |
| **Storage Account** | Tables, Blobs, Files (workspace mounts) | Standard LRS, Hot tier |
| **Key Vault** | Secrets management | Standard |
| **Application Insights** | Monitoring and telemetry | Pay-as-you-go |
| **Log Analytics** | Log aggregation | Pay-as-you-go |

---

## Development

### Code Organization

**CRITICAL RULES**:

1. **Models**: All Pydantic models MUST be defined in `shared/models.py`
2. **Business Logic**: MUST live in `shared/`, NOT in `functions/`
   - Functions are thin HTTP/timer/queue handlers only
   - Complex logic, algorithms, business rules go in `shared/handlers/`
3. **Routing**: Create one function file per base route
   - Example: `/discovery` → `functions/http/discovery.py`
   - Sub-routes and related functions live in the same file
4. **Decorators**: Always use `@shared/openapi_decorators.py` on HTTP functions
5. **Request/Response**: Always use Pydantic Request and Response models

### Development Workflow

```bash
# 1. Make changes to code
# 2. Run linting
ruff check .

# 3. Run type checking
npx pyright

# 4. Run tests
./test.sh

# 5. Test manually with Functions runtime
func start
```

### Testing Guidelines

- **Unit Tests**: Test individual functions and classes in `tests/unit/`
- **Integration Tests**: Test full workflows with Azure Functions context in `tests/integration/`
- **Contract Tests**: Test SDK public API contracts in `tests/contract/`
- Use fixtures from `tests/conftest.py` for common setup
- Mock external services (Azure Storage, Key Vault) in unit tests
- Use real services in integration tests (via Azurite)

### Type Safety

- Use Pydantic models for all data structures
- Enable strict type checking with Pyright
- Never ignore type errors - fix them
- Generate OpenAPI types from Pydantic models

---

## Deployment

### GitHub Releases

This repository uses GitHub Actions to create release packages:

1. Tag a release: `git tag v1.0.0 && git push origin v1.0.0`
2. GitHub Actions builds `api.zip` with all dependencies
3. Download `api.zip` from the GitHub release
4. Deploy to Azure Functions using zip deploy

### Zip Deploy (Quick)

```bash
# Download api.zip from GitHub releases, then:
az functionapp deployment source config-zip \
  --resource-group <rg-name> \
  --name <function-app-name> \
  --src api.zip
```

### GitHub Actions (Recommended)

See [bifrost-client](https://github.com/jackmusick/bifrost-client) repository for complete deployment workflow that deploys both API and client.

**Required GitHub Secrets**:
- `AZURE_FUNCTIONAPP_NAME` - Your Function App name
- `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` - Publish profile XML from Azure Portal

### Infrastructure Setup

Deploy Azure infrastructure using ARM templates:

```bash
# Clone the deployment repository
git clone https://github.com/your-org/bifrost-infrastructure.git
cd bifrost-infrastructure

# Deploy to Azure
az deployment group create \
  --resource-group bifrost-prod-rg \
  --template-file azuredeploy.json \
  --parameters baseName=bifrost workspacesQuotaGB=100 tmpQuotaGB=50
```

This creates:
- Azure Functions (Flex Consumption plan)
- Storage Account with Tables, Blobs, and Files
- Key Vault for secrets
- Application Insights for monitoring

---

## Documentation

### API Documentation

When the Functions runtime is running:
- **OpenAPI Spec**: http://localhost:7071/api/openapi.json
- **Swagger UI**: http://localhost:7071/api/docs (if enabled)

### Additional Resources

- **Frontend Repository**: [bifrost-client](https://github.com/jackmusick/bifrost-client)
- **Platform Documentation**: See bifrost-client repository docs
- **Azure Functions Docs**: https://docs.microsoft.com/en-us/azure/azure-functions/

---

## Contributing

We welcome contributions! Please follow these guidelines:

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run the full test suite: `./test.sh`
5. Run type checking: `npx pyright`
6. Run linting: `ruff check .`
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to your fork (`git push origin feature/amazing-feature`)
9. Open a Pull Request

### Code Standards

- **Python**: Follow PEP 8 style guide
- **Type Hints**: Use type hints for all functions
- **Docstrings**: Document public APIs with docstrings
- **Tests**: Write tests for new features
- **Commits**: Use conventional commit messages

---

## License

This project is licensed under the AGPL License - see the [LICENSE](LICENSE) file for details.

---

## Community & Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/jackmusick/bifrost-api/issues)
- **Frontend Repository**: [bifrost-client](https://github.com/jackmusick/bifrost-client)

---

## Cost Estimates

**Typical Production Deployment:**

- **Azure Functions (Flex Consumption)**: $5-20/month
  - Pay per execution and memory usage
  - Example: 50k executions/month ≈ $5
- **Storage Account**: $2-10/month
  - Tables: $0.05 per GB
  - Files (100 GB workspace): ~$2.30
  - Blobs: $0.02 per GB
- **Key Vault**: $0.50/month (10k operations free)
- **Application Insights**: $2-5/month (first 5 GB free)

**Total: ~$10-35/month for small-to-medium workloads**

**Example scenarios:**
- **5 customers, 10k executions/month**: ~$10/month
- **25 customers, 100k executions/month**: ~$20/month
- **100 customers, 500k executions/month**: ~$35-50/month

Monitor costs in Azure Cost Management.

---

**Ready to get started?**

- [Quick Start](#quick-start) - Get running locally in 5 minutes
- [Development](#development) - Learn the development workflow
- [Deployment](#deployment) - Deploy to Azure
- [Frontend Repository](https://github.com/jackmusick/bifrost-client) - Complete platform with UI
