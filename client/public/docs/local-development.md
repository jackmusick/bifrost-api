# Local Development Guide

Complete guide for setting up and developing with Bifrost Integrations locally using Docker.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Development Workflow](#development-workflow)
- [Testing with API Clients](#testing-with-api-clients)
- [Debugging](#debugging)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

- **Docker Desktop 24+** - Container runtime
- **Git** - Version control
- **VS Code** (recommended) - Code editor with Python and Docker extensions
- **Node.js 18+** - For frontend development (if working on client)

### Optional Tools

- **Postman** or **Insomnia** - API testing
- **curl** - Command-line API testing
- **Azure Storage Explorer** - View Azurite data

---

## Quick Start

### 1. Clone and Build

```bash
# Clone the repository
git clone https://github.com/your-org/bifrost-integrations.git
cd bifrost-integrations

# Build the Docker image
cd workflows
docker build -t bifrost-workflows:latest .
cd ..
```

### 2. Start the Environment

```bash
# Start Azurite + Workflows Engine
./start.sh
```

This starts:

- **Azurite** - Azure Storage emulator (Table, Blob, Queue)
- **Workflows Engine** - Azure Functions runtime in Docker
- **Debugger** - Remote debugging on port 5678 (if ENABLE_DEBUGGING=true)

### 3. Verify Services

```bash
# Check health endpoint
curl http://localhost:7071/api/health

# Expected response:
# {"status": "healthy", "version": "1.0.0"}
```

### 4. Access the Platform

- **API**: http://localhost:7071
- **Health Check**: http://localhost:7071/api/health
- **OpenAPI Spec**: http://localhost:7071/api/openapi.json
- **Swagger UI**: http://localhost:7071/api/docs

---

## Development Workflow

### Project Structure

```
bifrost-integrations/
├── workflows/                    # Azure Functions backend
│   ├── engine/                   # Core platform code
│   │   ├── shared/               # Context, decorators, utilities
│   │   ├── data_providers/       # Data provider functions
│   │   └── functions/            # HTTP-triggered Azure Functions
│   ├── workspace/                # User workflow files (mounted volume)
│   │   └── workflows/            # Your custom workflows
│   ├── Dockerfile                # Container image definition
│   ├── requirements.txt          # Python dependencies
│   └── function_app.py           # Azure Functions entry point
├── example_clean_workspace/      # Example setup for testing
│   ├── docker-compose.yml        # Local dev compose file
│   ├── start.sh                  # Start script
│   └── workflows/                # Example workflows
└── client/                       # React frontend (optional)
```

### Making Changes

**Backend Changes (Python)**:

1. Edit files in `workflows/` directory
2. Restart Docker container to pick up changes:
    ```bash
    ./stop.sh
    ./start.sh
    ```

**Workflow Changes**:

1. Edit files in `/workspace/workflows/` (mounted volume)
2. Changes are picked up automatically on next execution
3. For decorator changes (e.g., new `@workflow` or `@param`), restart is required

### Building Docker Images

**For local development** (uses pre-built image):

```bash
cd workflows
docker build -t bifrost-workflows:latest .
```

**For production** (push to Docker Hub):

```bash
# Build with version tag
docker build -t yourdockerhub/bifrost-workflows:v1.0.0 .
docker build -t yourdockerhub/bifrost-workflows:latest .

# Push to registry
docker login
docker push yourdockerhub/bifrost-workflows:v1.0.0
docker push yourdockerhub/bifrost-workflows:latest
```

---

## Testing with API Clients

### Authentication

The Docker environment uses **function keys** for authentication (matching production behavior).

**Master Key**: `test` (configured in Dockerfile)

**Authentication Methods**:

1. **Header (recommended)**:

    ```bash
    -H "x-functions-key: test"
    ```

2. **Query parameter**:
    ```bash
    ?code=test
    ```

### Common API Endpoints

#### Health Check

```bash
# No authentication required
curl http://localhost:7071/api/health
```

#### List All Workflows

```bash
curl -H "x-functions-key: test" \
     -H "X-Organization-Id: test-org-active" \
     http://localhost:7071/api/registry/metadata
```

#### Execute a Workflow

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "x-functions-key: test" \
  -H "X-Organization-Id: test-org-active" \
  -d '{"name": "Alice", "language": "spanish"}' \
  http://localhost:7071/api/workflows/hello_world
```

#### Get Data Provider Options

```bash
curl -H "x-functions-key: test" \
     -H "X-Organization-Id: test-org-active" \
     http://localhost:7071/api/data-providers/get_greeting_languages
```

### Testing with Postman

#### 1. Create a New Collection

1. Open Postman
2. Click "New" → "Collection"
3. Name it "Bifrost Integrations - Local"

#### 2. Set Collection Variables

Add these variables to the collection:

- `base_url`: `http://localhost:7071`
- `api_key`: `test`
- `org_id`: `test-org-active`

#### 3. Add Authentication Header

In Collection settings → Authorization:

- Type: **API Key**
- Key: `x-functions-key`
- Value: `{{api_key}}`
- Add to: **Header**

#### 4. Create Requests

**Health Check**:

```
GET {{base_url}}/api/health
```

**List Workflows**:

```
GET {{base_url}}/api/registry/metadata
Headers:
  X-Organization-Id: {{org_id}}
```

**Execute Workflow**:

```
POST {{base_url}}/api/workflows/hello_world
Headers:
  Content-Type: application/json
  X-Organization-Id: {{org_id}}
Body (JSON):
{
  "name": "Alice",
  "language": "spanish"
}
```

### Testing with curl

#### Basic Workflow Execution

```bash
# Execute hello_world workflow
curl -X POST \
  -H "Content-Type: application/json" \
  -H "x-functions-key: test" \
  -H "X-Organization-Id: test-org-active" \
  -d '{
    "name": "Alice",
    "language": "spanish"
  }' \
  http://localhost:7071/api/workflows/hello_world | jq
```

#### Test User Onboarding Workflow

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "x-functions-key: test" \
  -H "X-Organization-Id: test-org-active" \
  -d '{
    "email": "alice@example.com",
    "first_name": "Alice",
    "last_name": "Smith",
    "department": "Engineering",
    "license_sku": "SPE_E3"
  }' \
  http://localhost:7071/api/workflows/onboard_new_user | jq
```

#### Get Available Licenses (Data Provider)

```bash
curl -H "x-functions-key: test" \
     -H "X-Organization-Id: test-org-active" \
     http://localhost:7071/api/data-providers/get_available_licenses | jq
```

### Postman Collection Export

You can export/import this Postman collection:

```json
{
	"info": {
		"name": "Bifrost Integrations - Local",
		"schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
	},
	"variable": [
		{ "key": "base_url", "value": "http://localhost:7071" },
		{ "key": "api_key", "value": "test" },
		{ "key": "org_id", "value": "test-org-active" }
	],
	"auth": {
		"type": "apikey",
		"apikey": [
			{ "key": "key", "value": "x-functions-key" },
			{ "key": "value", "value": "{{api_key}}" },
			{ "key": "in", "value": "header" }
		]
	},
	"item": [
		{
			"name": "Health Check",
			"request": {
				"method": "GET",
				"url": "{{base_url}}/api/health"
			}
		},
		{
			"name": "List Workflows",
			"request": {
				"method": "GET",
				"header": [
					{ "key": "X-Organization-Id", "value": "{{org_id}}" }
				],
				"url": "{{base_url}}/api/registry/metadata"
			}
		},
		{
			"name": "Execute Hello World",
			"request": {
				"method": "POST",
				"header": [
					{ "key": "Content-Type", "value": "application/json" },
					{ "key": "X-Organization-Id", "value": "{{org_id}}" }
				],
				"body": {
					"mode": "raw",
					"raw": "{\"name\": \"Alice\", \"language\": \"spanish\"}"
				},
				"url": "{{base_url}}/api/workflows/hello_world"
			}
		}
	]
}
```

---

## Debugging

### VS Code Debugger Setup

Debugging is **enabled by default** in the local environment.

#### 1. Launch Configuration

The `.vscode/launch.json` is already configured:

```json
{
	"version": "0.2.0",
	"configurations": [
		{
			"name": "Attach to Docker Functions",
			"type": "debugpy",
			"request": "attach",
			"connect": {
				"host": "localhost",
				"port": 5678
			},
			"pathMappings": [
				{
					"localRoot": "${workspaceFolder}",
					"remoteRoot": "/workspace"
				}
			],
			"justMyCode": true
		}
	]
}
```

#### 2. Start Debugging

1. Start the environment: `./start.sh`
2. Wait for message: `"⏳ Waiting for debugger attach on port 5678..."`
3. Open VS Code
4. Set breakpoint in any Python file (e.g., `workflows/test.py`)
5. Press `F5` or click "Run and Debug" → "Attach to Docker Functions"
6. Trigger the function with curl or Postman
7. VS Code will pause at your breakpoint

#### 3. Debugging Tips

**Inspect Variables**:

- Hover over variables to see values
- Use the Debug Console to evaluate expressions
- View the Call Stack to understand execution flow

**Step Through Code**:

- `F10` - Step over
- `F11` - Step into
- `Shift+F11` - Step out
- `F5` - Continue

**Watch Expressions**:

- Add variables to the Watch panel
- Monitor `context.org_id`, `context.execution_id`, etc.

### Debugging Without VS Code

If you prefer command-line debugging or want to use a different IDE:

1. Start with debugging enabled (default)
2. Connect debugger to `localhost:5678`
3. Use your IDE's remote debugging features

### Disable Debugging

To start without waiting for debugger:

```bash
# Edit docker-compose.yml
# Change: ENABLE_DEBUGGING=${ENABLE_DEBUGGING:-true}
# To:     ENABLE_DEBUGGING=${ENABLE_DEBUGGING:-false}

# Or set environment variable
export ENABLE_DEBUGGING=false
./start.sh
```

### Viewing Logs

**Real-time logs**:

```bash
docker compose logs -f functions
```

**Azurite logs**:

```bash
docker compose logs -f azurite
```

**All logs**:

```bash
docker compose logs -f
```

---

## Troubleshooting

### Container Won't Start

**Symptoms**: `docker compose up` fails

**Solutions**:

```bash
# Check logs
docker compose logs functions

# Rebuild image
docker compose build --no-cache

# Verify Dockerfile syntax
docker build -t test ./workflows

# Check port conflicts
lsof -i :7071
lsof -i :5678
```

### Azurite Connection Refused

**Symptoms**: Functions start but fail to connect to Azurite

**Solutions**:

```bash
# Verify Azurite is running
docker compose ps

# Check connection string uses container name
# Should be: http://azurite:10002 (NOT localhost)

# Restart services
docker compose restart
```

### Debugging Not Working

**Symptoms**: VS Code won't attach to debugger

**Checklist**:

1. ✓ `ENABLE_DEBUGGING=true` in docker-compose.yml
2. ✓ Port 5678 is exposed and mapped
3. ✓ Container logs show "Waiting for debugger attach"
4. ✓ VS Code launch.json has correct configuration
5. ✓ No other process using port 5678

**Solutions**:

```bash
# Check if debugpy is listening
nc -zv localhost 5678

# Verify debugpy is installed in container
docker exec -it functions pip show debugpy

# Restart with clean build
docker compose down
docker compose up --build
```

### Workflow Changes Not Detected

**Symptoms**: Code changes don't take effect

**Solutions**:

```bash
# For decorator changes (@workflow, @param), restart required
docker compose restart functions

# For code changes in mounted volumes, verify mount
docker inspect functions | grep Mounts -A 10

# Rebuild if needed
docker compose up --build
```

### Health Check Fails

**Symptoms**: `curl http://localhost:7071/api/health` returns error

**Solutions**:

```bash
# Wait for Functions runtime to start (can take 10-30 seconds)
sleep 10 && curl http://localhost:7071/api/health

# Check if port is correct (7071 not 7071)
curl http://localhost:7071/api/health

# Verify function key
curl -H "x-functions-key: test" http://localhost:7071/api/health

# Check container is running
docker ps | grep functions
```

### API Returns 401 Unauthorized

**Symptoms**: API calls return 401 error

**Solutions**:

```bash
# Verify function key is correct
curl -H "x-functions-key: test" http://localhost:7071/api/health

# Check key in container
docker exec functions cat /azure-functions-host/Secrets/host.json

# Rebuild with correct key
docker compose down
docker compose build --no-cache
docker compose up
```

---

## Production vs Local Differences

### Docker Compose Configuration

**Local** (`example_clean_workspace/docker-compose.yml`):

- Uses pre-built image: `bifrost-workflows:latest`
- Mounts workspace as volume: `./:/workspace`
- Debugging enabled by default
- Uses Azurite for storage
- Port 7071 (to avoid conflicts with other services)

**Production** (Azure):

- Pulls from Docker Hub: `yourdockerhub/bifrost-workflows:latest`
- No volume mounts (code baked into image)
- Debugging disabled
- Uses Azure Storage
- Standard HTTPS port

### Environment Variables

**Local**:

```yaml
AzureWebJobsStorage=http://azurite:10002/devstoreaccount1
AzureWebJobsSecretStorageType=files
ENABLE_DEBUGGING=true
WEBSITE_AUTH_ENCRYPTION_KEY=C0sm0Rk3y567890123456789...
```

**Production**:

```yaml
AzureWebJobsStorage={Azure Storage connection string}
ENABLE_DEBUGGING=false
# Key Vault references for secrets
```

### Testing Strategy

1. **Local Development**: Test with curl/Postman, verify logs
2. **Pre-Production**: Build image, test in isolated environment
3. **Production**: Deploy via GitHub Actions, monitor Application Insights

---

## Next Steps

- **Create Your First Workflow**: See [getting-started.md](./getting-started.md)
- **Workflow Development**: See [workflow-development.md](./workflow-development.md)
- **OAuth Setup**: See [secrets-and-oauth.md](./secrets-and-oauth.md)
- **Production Deployment**: See [/specs/005-migrate-to-azure/quickstart.md](../../specs/005-migrate-to-azure/quickstart.md)

---

## Quick Reference

### Common Commands

```bash
# Start environment
./start.sh

# Stop environment
./stop.sh

# View logs
docker compose logs -f

# Rebuild and restart
docker compose down
docker compose up --build

# Execute a workflow
curl -X POST \
  -H "Content-Type: application/json" \
  -H "x-functions-key: test" \
  -H "X-Organization-Id: test-org-active" \
  -d '{"param": "value"}' \
  http://localhost:7071/api/workflows/workflow_name
```

### Key Files

- `docker-compose.yml` - Local dev environment configuration
- `workflows/Dockerfile` - Container image definition
- `workflows/requirements.txt` - Python dependencies
- `workflows/function_app.py` - Azure Functions entry point
- `.vscode/launch.json` - VS Code debugger configuration

### Important URLs

- API: http://localhost:7071
- Health: http://localhost:7071/api/health
- OpenAPI: http://localhost:7071/api/openapi.json
- Debugger: localhost:5678

---

Happy coding! 🚀
