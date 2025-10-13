# Quickstart: Azure Functions Docker Runtime Migration

**Feature**: 005-migrate-to-azure | **Date**: 2025-01-13

This guide walks through local development setup and first production deployment.

## Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [First Production Deployment](#first-production-deployment)
3. [GitHub Integration Setup](#github-integration-setup)
4. [Manual Editing Mode](#manual-editing-mode)
5. [Troubleshooting](#troubleshooting)

---

## Local Development Setup

### Prerequisites

-   Docker Desktop 24+ installed and running
-   VS Code with Python extension (optional, for debugging)
-   Git installed
-   Node.js 18+ (for frontend development)

### Step 1: Initialize Docker Support

Add Docker support to the existing Azure Functions project:

```bash
cd workflows
func init --docker-only
```

This creates:

-   `Dockerfile` - Container image definition
-   `.dockerignore` - Files to exclude from image

### Step 2: Create docker-compose.dev.yml

Create `docker-compose.dev.yml` in repository root:

```yaml
version: "3.8"

services:
    azurite:
        image: mcr.microsoft.com/azure-storage/azurite:latest
        ports:
            - "10000:10000" # Blob
            - "10001:10001" # Queue
            - "10002:10002" # Table
            - "10003:10003" # Files
        command: "azurite --blobHost 0.0.0.0 --queueHost 0.0.0.0 --tableHost 0.0.0.0 --fileHost 0.0.0.0 --loose"
        volumes:
            - azurite-data:/data

    functions:
        build:
            context: ./workflows
            dockerfile: Dockerfile
        ports:
            - "7071:80" # Azure Functions runtime
            - "5678:5678" # Debugpy (when ENABLE_DEBUGGING=true)
        environment:
            - AzureWebJobsStorage=DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://azurite:10000/devstoreaccount1;QueueEndpoint=http://azurite:10001/devstoreaccount1;TableEndpoint=http://azurite:10002/devstoreaccount1;
            - AZURE_FILES_CONNECTION_STRING=DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;FileEndpoint=http://azurite:10003/devstoreaccount1;
            - ENABLE_DEBUGGING=${ENABLE_DEBUGGING:-false}
            - PYTHONPATH=/home/site/wwwroot
            - AZURE_FUNCTIONS_ENVIRONMENT=Development
        volumes:
            - ./workflows:/home/site/wwwroot # Live code reload
            - workspace-data:/workspace # Workspace files
            - tmp-data:/tmp # Temporary storage
        depends_on:
            - azurite

volumes:
    azurite-data:
    workspace-data:
    tmp-data:
```

### Step 3: Start Local Environment

```bash
# Start services
docker-compose -f docker-compose.dev.yml up

# Wait for "Azure Functions runtime started" message
# Functions available at: http://localhost:7071
```

**Expected output**:

```
functions_1  | Azure Functions Core Tools
functions_1  | Core Tools Version:       4.0.5455
functions_1  | Function Runtime Version: 4.21.3.20371
functions_1  |
functions_1  | Functions:
functions_1  |   github_webhook: [POST] http://localhost:7071/api/github-webhook
functions_1  |   workspace_files: [GET,PUT,DELETE] http://localhost:7071/api/workspace/files/{filePath}
```

### Step 4: Verify Local Setup

**Test Azure Functions:**

```bash
curl http://localhost:7071/api/health
# Expected: {"status": "healthy", "version": "1.0.0"}
```

**Test Azurite connection:**

```bash
# Install Azure Storage Explorer or use azure-storage-python
pip install azure-data-tables

python -c "
from azure.data.tables import TableServiceClient
conn_str = 'DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;...'
client = TableServiceClient.from_connection_string(conn_str)
print('✓ Azurite connected')
"
```

### Step 5: Enable Debugging (Optional)

**Set environment variable:**

```bash
export ENABLE_DEBUGGING=true
docker-compose -f docker-compose.dev.yml up
```

**VS Code launch.json:**
Create `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Attach to Docker Functions",
            "type": "python",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5678
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}/workflows",
                    "remoteRoot": "/home/site/wwwroot"
                }
            ]
        }
    ]
}
```

**Set breakpoint:**

1. Open `workflows/functions/github_sync.py`
2. Click left of line number to set breakpoint
3. Press F5 or select "Run > Start Debugging"
4. Trigger function (e.g., POST to /api/github-webhook)
5. Debugger pauses at breakpoint

---

## First Production Deployment

### Prerequisites

-   Azure subscription with appropriate permissions
-   Azure CLI installed and authenticated (`az login`)
-   Docker Hub account (for container image hosting)
-   GitHub account with repository admin access

### Step 1: Build and Push Container Image

**Build image:**

```bash
cd workflows
docker build -t yourdockerhub/bifrost-functions:latest .
```

**Push to Docker Hub:**

```bash
docker login
docker push yourdockerhub/bifrost-functions:latest
```

**Note**: Update image tag in ARM template parameters (see Step 3).

### Step 2: Prepare ARM Template Parameters

Create `infrastructure/parameters/prod.json`:

```json
{
    "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
    "contentVersion": "1.0.0.0",
    "parameters": {
        "resourceGroupName": {
            "value": "bifrost-prod-rg"
        },
        "location": {
            "value": "eastus"
        },
        "dockerHubImage": {
            "value": "yourdockerhub/bifrost-functions:latest"
        },
        "frontendGitHubRepoUrl": {
            "value": "https://github.com/your-org/bifrost-frontend"
        },
        "frontendGitHubToken": {
            "value": "ghp_YOUR_GITHUB_PAT"
        },
        "frontendRepoBranch": {
            "value": "main"
        },
        "workspacesQuotaGB": {
            "value": 100
        },
        "tmpQuotaGB": {
            "value": 50
        },
        "storageAccountTier": {
            "value": "Hot"
        }
    }
}
```

**Security note**: Store GitHub token in Azure Key Vault or GitHub Secrets, not in parameter file.

### Step 3: Deploy ARM Template

**Create resource group:**

```bash
az group create \
  --name bifrost-prod-rg \
  --location eastus
```

**Deploy template:**

```bash
az deployment group create \
  --resource-group bifrost-prod-rg \
  --template-file infrastructure/main.bicep \
  --parameters infrastructure/parameters/prod.json \
  --mode Incremental
```

**Expected duration**: ~25-30 minutes

**Monitor deployment:**

```bash
az deployment group show \
  --resource-group bifrost-prod-rg \
  --name main \
  --query properties.provisioningState
```

### Step 4: Retrieve Deployment Outputs

**Get Function App URL:**

```bash
az deployment group show \
  --resource-group bifrost-prod-rg \
  --name main \
  --query properties.outputs.functionAppUrl.value \
  --output tsv
```

**Get Static Web App URL:**

```bash
az deployment group show \
  --resource-group bifrost-prod-rg \
  --name main \
  --query properties.outputs.staticWebAppUrl.value \
  --output tsv
```

**Get GitHub webhook URL:**

```bash
az deployment group show \
  --resource-group bifrost-prod-rg \
  --name main \
  --query properties.outputs.githubWebhookUrl.value \
  --output tsv
```

### Step 5: Verify Deployment

**Test Function App:**

```bash
FUNCTION_URL=$(az deployment group show ...)
curl $FUNCTION_URL/api/health
```

**Test Static Web App:**

```bash
STATIC_URL=$(az deployment group show ...)
curl $STATIC_URL
# Expected: HTML page with React app
```

**Check Azure Files mounts:**

```bash
# SSH into Function App container (via Azure Portal > SSH)
ls /workspace  # Should exist (empty initially)
ls /tmp         # Should exist (empty initially)
```

---

## GitHub Integration Setup

### Step 1: Create GitHub Connection (via API)

**Prerequisites**:

-   GitHub Personal Access Token with `repo` scope
-   GitHub repository for workspace code

**Create connection:**

```bash
FUNCTION_URL="https://bifrost-functions.azurewebsites.net"
TOKEN="your-azure-ad-jwt-token"  # From MSAL login

curl -X POST "$FUNCTION_URL/api/github-connections" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: GLOBAL" \
  -d '{
    "repositoryUrl": "https://github.com/your-org/workflows.git",
    "repositoryBranch": "main",
    "personalAccessToken": "ghp_YOUR_GITHUB_PAT"
  }'
```

**Expected response:**

```json
{
    "connection": {
        "orgId": "GLOBAL",
        "repositoryUrl": "https://github.com/your-org/workflows.git",
        "repositoryBranch": "main",
        "webhookUrl": "https://bifrost-functions.azurewebsites.net/api/github-webhook",
        "isEnabled": true,
        "createdAt": "2025-01-13T10:00:00Z"
    },
    "webhookUrl": "https://bifrost-functions.azurewebsites.net/api/github-webhook"
}
```

### Step 2: Configure GitHub Webhook

**In GitHub repository settings**:

1. Navigate to Settings > Webhooks > Add webhook
2. Payload URL: (use webhookUrl from Step 1 response)
3. Content type: `application/json`
4. Secret: (retrieve from Azure Key Vault secret `github-webhook-secret-global`)
5. Events: Select "Just the push event"
6. Active: ✓ Enabled
7. Click "Add webhook"

**Retrieve webhook secret:**

```bash
VAULT_NAME="bifrost-keyvault"
az keyvault secret show \
  --vault-name $VAULT_NAME \
  --name github-webhook-secret-global \
  --query value \
  --output tsv
```

### Step 3: Trigger First Sync

**Push to GitHub repository:**

```bash
cd /path/to/workflows-repo
git add workflows/
git commit -m "Initial workspace commit"
git push origin main
```

**Monitor sync job:**

```bash
curl "$FUNCTION_URL/api/sync-jobs?limit=1" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected response:**

```json
{
    "jobs": [
        {
            "commitSha": "a1b2c3d4e5f6...",
            "status": "completed",
            "filesAdded": 50,
            "filesModified": 0,
            "filesDeleted": 0,
            "durationMs": 25000
        }
    ],
    "total": 1
}
```

**Verify workspace files:**

```bash
curl "$FUNCTION_URL/api/workspace/files" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Manual Editing Mode

### Step 1: Disconnect GitHub (Optional)

If you want to edit files via UI without GitHub sync:

```bash
curl -X PUT "$FUNCTION_URL/api/github-connections/GLOBAL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "isEnabled": false
  }'
```

### Step 2: Create/Edit Files via API

**Create new file:**

```bash
curl -X PUT "$FUNCTION_URL/api/workspace/files/workflows/test.py" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "def test():\n    print(\"Hello World\")"
  }'
```

**Update existing file:**

```bash
curl -X PUT "$FUNCTION_URL/api/workspace/files/workflows/test.py" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "def test():\n    print(\"Updated!\")"
  }'
```

**Delete file:**

```bash
curl -X DELETE "$FUNCTION_URL/api/workspace/files/workflows/test.py" \
  -H "Authorization: Bearer $TOKEN"
```

### Step 3: Download Workspace Backup

Before re-enabling GitHub sync (which will overwrite manual changes):

```bash
curl "$FUNCTION_URL/api/workspace/download" \
  -H "Authorization: Bearer $TOKEN" \
  -o workspace-backup-$(date +%Y%m%d-%H%M%S).zip
```

---

## Troubleshooting

### Issue: Container won't start locally

**Symptoms**: `docker-compose up` fails with "Container exited with code 1"

**Solutions**:

1. Check logs: `docker-compose logs functions`
2. Verify Dockerfile syntax: `docker build -t test ./workflows`
3. Check Python dependencies: `docker run -it test /bin/bash` → `pip list`
4. Verify Azure Functions version: Check `Dockerfile` base image matches `host.json` version

### Issue: Azurite connection refused

**Symptoms**: Functions start but fail with "Connection refused to Azurite"

**Solutions**:

1. Verify Azurite is running: `docker-compose ps`
2. Check Azurite logs: `docker-compose logs azurite`
3. Verify connection string uses container name `azurite:10002`, not `localhost:10002`
4. Restart services: `docker-compose down && docker-compose up`

### Issue: Debugging not working

**Symptoms**: VS Code doesn't attach to container

**Solutions**:

1. Verify `ENABLE_DEBUGGING=true` is set
2. Check debug port is exposed: `docker-compose ps` → port 5678
3. Verify debugpy is installed: `docker exec -it functions pip show debugpy`
4. Check function logs for "Waiting for debugger attach" message
5. Restart with clean build: `docker-compose down && docker-compose up --build`

### Issue: GitHub webhook returns 401 Unauthorized

**Symptoms**: GitHub webhook delivery fails with 401 status

**Solutions**:

1. Verify webhook secret matches Key Vault secret
2. Check HMAC signature calculation (see GitHub delivery details)
3. Test webhook endpoint manually: `curl -X POST ... -H "X-Hub-Signature-256: sha256=..."`
4. Review function logs: `az webapp log tail --name bifrost-functions --resource-group bifrost-prod-rg`

### Issue: ARM deployment fails

**Symptoms**: `az deployment group create` returns error

**Common errors**:

-   **"Location not available"**: Change `location` parameter to supported region
-   **"Insufficient quota"**: Request quota increase or use smaller SKU
-   **"Name already taken"**: Change resource names (must be globally unique)
-   **"Invalid GitHub token"**: Verify token has `repo` and `workflow` scopes

**Debug steps**:

1. Check deployment status: `az deployment group show ... --query properties.error`
2. Review activity log: Azure Portal > Resource Group > Activity log
3. Validate template syntax: `az deployment group validate ...`

### Issue: Workspace files not syncing

**Symptoms**: GitHub push succeeds but files don't appear in `/workspace`

**Solutions**:

1. Check sync job status: `GET /api/sync-jobs`
2. Review sync job error message if status="failed"
3. Verify Azure Files mount: SSH into container → `ls /workspace`
4. Check storage account connectivity: Azure Portal > Storage Account > Networking
5. Verify GitHub PAT has read access to repository

---

## Next Steps

After completing this quickstart:

1. **Implement workflows**: Add Python workflow files to GitHub repository
2. **Configure CI/CD**: Set up GitHub Actions for container image builds
3. **Add monitoring**: Configure Application Insights alerts
4. **Enable custom domain**: Configure custom domain for Static Web App
5. **Set up staging**: Deploy second environment with separate ARM template
6. **Configure backup**: Enable Azure Files snapshot backups

For implementation details, see [tasks.md](./tasks.md) (generated by `/speckit.tasks`).
