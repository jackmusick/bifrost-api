# Research: Azure Functions Docker Runtime Migration

**Feature**: 005-migrate-to-azure | **Date**: 2025-01-13

This document captures technical research and decisions for migrating the Azure Functions workflow engine to Docker runtime.

## Decision 1: Azure Functions Docker Base Image

**Chosen**: `mcr.microsoft.com/azure-functions/python:4-python3.11`

**Rationale**:

-   Official Microsoft-maintained image for Azure Functions Python 3.11
-   Includes Azure Functions runtime v4 + Python 3.11.x
-   Pre-configured for Azure Functions hosting environment
-   Supports both local development and Azure deployment

**Configuration**:

```dockerfile
FROM mcr.microsoft.com/azure-functions/python:4-python3.11

# Copy function code
COPY . /home/site/wwwroot

# Install dependencies
RUN cd /home/site/wwwroot && \
    pip install --no-cache-dir -r requirements.txt

# Expose debugging port when ENABLE_DEBUGGING=true
EXPOSE 5678
```

**Alternatives Considered**:

-   `python:3.11-slim` + manual Azure Functions installation → Rejected: More complex, harder to maintain, missing Azure-specific optimizations
-   `mcr.microsoft.com/azure-functions/python:4` (latest) → Rejected: Pin to specific Python version for reproducibility

**Key Gotchas**:

-   Must use `/home/site/wwwroot` as working directory (Azure Functions convention)
-   Environment variables set in `local.settings.json` (local) or App Settings (Azure)
-   Debug port 5678 for debugpy (VS Code Python debugging)

---

## Decision 2: Docker Compose for Local Development

**Chosen**: Separate `docker-compose.dev.yml` with Azurite and volume mounts

**Rationale**:

-   Azurite provides local Azure Storage emulation (Table, Blob, Queue, Files)
-   Volume mounts enable live code reload without container rebuild
-   Network isolation between services
-   Optional debugging support via ENABLE_DEBUGGING env var

**Configuration**:

```yaml
version: "3.8"

services:
    azurite:
        image: mcr.microsoft.com/azure-storage/azurite
        ports:
            - "10000:10000" # Blob
            - "10001:10001" # Queue
            - "10002:10002" # Table
            - "10003:10003" # Files (Azure Files emulation)
        command: "azurite --blobHost 0.0.0.0 --queueHost 0.0.0.0 --tableHost 0.0.0.0 --fileHost 0.0.0.0"
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
            - AzureWebJobsStorage=DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=...;BlobEndpoint=http://azurite:10000/devstoreaccount1;QueueEndpoint=http://azurite:10001/devstoreaccount1;TableEndpoint=http://azurite:10002/devstoreaccount1;
            - ENABLE_DEBUGGING=${ENABLE_DEBUGGING:-false}
            - PYTHONPATH=/home/site/wwwroot
        volumes:
            - ./workflows:/home/site/wwwroot # Source code (live reload)
            - workspace-data:/workspace # Workspace files
            - ./tmp:/tmp # Temporary storage
        depends_on:
            - azurite

volumes:
    azurite-data:
    workspace-data:
```

**Debugging Setup**:
When `ENABLE_DEBUGGING=true`, modify function startup to:

```python
# In function_app.py or __init__.py
import os
if os.getenv('ENABLE_DEBUGGING') == 'true':
    import debugpy
    debugpy.listen(("0.0.0.0", 5678))
    print("⏳ Waiting for debugger attach on port 5678...")
    debugpy.wait_for_client()
    print("✅ Debugger attached")
```

**VS Code Launch Configuration**:

```json
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
```

**Alternatives Considered**:

-   Single docker-compose.yml for both dev/prod → Rejected: Different requirements (prod uses Azure Storage, dev uses Azurite)
-   No Azurite, connect to real Azure Storage → Rejected: Costs money, slower, requires internet

**Key Gotchas**:

-   Azurite Files endpoint (10003) required for Azure Files SDK testing
-   Volume mounts use `:` on Windows/Mac, but beware of path translation
-   Debug port must be exposed AND debugpy.listen() called in code
-   wait_for_client() blocks startup until debugger attaches

---

## Decision 3: Azure Files Mounting in Production

**Chosen**: ARM template mounts Azure Files via WEBSITE_CONTENTAZUREFILECONNECTIONSTRING + path mapping

**Rationale**:

-   Azure Functions containers support native Azure Files mounting
-   Hot tier provides <10ms latency for file operations
-   Supports both `/workspace` (user code) and `/tmp` (temporary storage)
-   No code changes required (transparent file system access)

**ARM Template Configuration (Bicep)**:

```bicep
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
  }
}

resource workspacesShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-01-01' = {
  name: '${storageAccount.name}/default/workspace'
  properties: {
    shareQuota: workspacesQuotaGB
    enabledProtocols: 'SMB'
    accessTier: 'Hot'
  }
}

resource tmpShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-01-01' = {
  name: '${storageAccount.name}/default/tmp'
  properties: {
    shareQuota: tmpQuotaGB
    enabledProtocols: 'SMB'
    accessTier: 'Hot'
  }
}

resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux,container'
  properties: {
    siteConfig: {
      linuxFxVersion: 'DOCKER|${dockerHubImage}'
      appSettings: [
        {
          name: 'WEBSITE_RUN_FROM_PACKAGE'
          value: '0'  // Required for Azure Files mounting
        }
        {
          name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE'
          value: 'true'  // Enable Azure Files mounting
        }
        {
          name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
        }
      ]
      azureStorageAccounts: {
        workspaces: {
          type: 'AzureFiles'
          accountName: storageAccount.name
          shareName: 'workspaces'
          mountPath: '/workspace'
          accessKey: storageAccount.listKeys().keys[0].value
        }
        tmp: {
          type: 'AzureFiles'
          accountName: storageAccount.name
          shareName: 'tmp'
          mountPath: '/tmp'
          accessKey: storageAccount.listKeys().keys[0].value
        }
      }
    }
  }
}
```

**Performance Implications**:

-   Hot tier: 10,000 IOPS, 300 MiB/s throughput (sufficient for 50-200 orgs)
-   <10ms latency for file operations within same region
-   SMB 3.0 protocol (encrypted in transit)

**Alternatives Considered**:

-   Blob Storage + FUSE mounting → Rejected: More complex, not native to Azure Functions
-   Premium Files tier → Rejected: Overkill for workload, Hot tier sufficient per clarifications

**Key Gotchas**:

-   Must set `WEBSITE_RUN_FROM_PACKAGE=0` (disables ZIP deployment)
-   Must set `WEBSITES_ENABLE_APP_SERVICE_STORAGE=true` (enables custom mounts)
-   Mount path `/tmp` overrides default container `/tmp` (may affect some workflows)
-   Access key rotation requires app restart

---

## Decision 4: Static Web App GitHub Integration

**Chosen**: ARM template with `repositoryUrl` and `repositoryToken` properties

**Rationale**:

-   Static Web App natively supports GitHub Actions CI/CD
-   ARM template creates GitHub Actions workflow automatically in repository
-   No manual GitHub setup required after deployment
-   Frontend automatically rebuilds on push to configured branch

**ARM Template Configuration (Bicep)**:

```bicep
resource staticWebApp 'Microsoft.Web/staticSites@2023-01-01' = {
  name: staticWebAppName
  location: location
  sku: {
    name: 'Free'  // or 'Standard' for custom domains
    tier: 'Free'
  }
  properties: {
    repositoryUrl: frontendGitHubRepoUrl  // e.g., https://github.com/org/repo
    repositoryToken: frontendGitHubToken  // GitHub PAT with repo, workflow scope
    branch: frontendRepoBranch            // e.g., main
    buildProperties: {
      appLocation: '/client'              // Frontend directory
      apiLocation: ''                     // No API (using Azure Functions)
      outputLocation: 'dist'              // Vite/React build output
    }
  }
}
```

**GitHub Token Requirements**:

-   Scopes: `repo`, `workflow` (create/modify workflows)
-   Classic PAT or Fine-grained with "Contents: Read & Write", "Workflows: Read & Write"
-   Store in Key Vault, pass as secure parameter to ARM template

**Generated GitHub Actions Workflow**:
ARM deployment automatically creates `.github/workflows/azure-static-web-apps-<name>.yml`:

```yaml
name: Azure Static Web Apps CI/CD

on:
    push:
        branches:
            - main
    pull_request:
        types: [opened, synchronize, reopened, closed]
        branches:
            - main

jobs:
    build_and_deploy_job:
        runs-on: ubuntu-latest
        name: Build and Deploy Job
        steps:
            - uses: actions/checkout@v3
              with:
                  submodules: true
            - name: Build And Deploy
              uses: Azure/static-web-apps-deploy@v1
              with:
                  azure_static_web_apps_api_token: ${{ secrets.AZURE_STATIC_WEB_APPS_API_TOKEN }}
                  repo_token: ${{ secrets.GITHUB_TOKEN }}
                  action: "upload"
                  app_location: "/client"
                  api_location: ""
                  output_location: "dist"
```

**Alternatives Considered**:

-   Manual GitHub Actions setup → Rejected: ARM template automates this
-   Azure DevOps Pipelines → Rejected: GitHub is primary VCS per spec

**Key Gotchas**:

-   GitHub token must have workflow permissions (not just repo)
-   First deployment takes 5-10 minutes (GitHub Actions cold start)
-   buildProperties paths relative to repository root
-   Free tier limited to 100GB bandwidth/month

---

## Decision 5: GitHub Webhook for Workspace Sync

**Chosen**: Azure Function with HMAC-SHA256 signature verification

**Rationale**:

-   GitHub webhooks use HMAC-SHA256 with shared secret
-   Signature verification prevents unauthorized sync requests
-   Async processing prevents webhook timeouts
-   Idempotency via commit SHA tracking in Table Storage

**Implementation**:

```python
import hashlib
import hmac
import json
from azure.functions import HttpRequest, HttpResponse

async def github_webhook(req: HttpRequest) -> HttpResponse:
    # 1. Verify GitHub signature
    signature = req.headers.get('X-Hub-Signature-256', '')
    if not signature.startswith('sha256='):
        return HttpResponse('Missing signature', status_code=401)

    secret = os.getenv('GITHUB_WEBHOOK_SECRET')
    body_bytes = req.get_body()
    expected_sig = 'sha256=' + hmac.new(
        secret.encode(), body_bytes, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_sig):
        return HttpResponse('Invalid signature', status_code=401)

    # 2. Parse webhook payload
    payload = req.get_json()
    event_type = req.headers.get('X-GitHub-Event')

    if event_type != 'push':
        return HttpResponse('OK', status_code=200)  # Ignore non-push events

    # 3. Check idempotency (already processed this commit?)
    commit_sha = payload['after']
    if await is_commit_processed(commit_sha):
        return HttpResponse('Already processed', status_code=200)

    # 4. Queue sync job (async processing)
    await queue_sync_job({
        'repo_url': payload['repository']['clone_url'],
        'commit_sha': commit_sha,
        'branch': payload['ref'].replace('refs/heads/', ''),
        'timestamp': payload['head_commit']['timestamp']
    })

    return HttpResponse('Sync queued', status_code=202)
```

**Idempotency Pattern**:
Store processed commits in Table Storage:

```python
# Entity: GitHubSyncJobs
# PartitionKey: "SYNC_JOBS"
# RowKey: commit_sha
# Properties: status, timestamp, sync_duration_ms

async def is_commit_processed(commit_sha: str) -> bool:
    table_client = get_table_client('GitHubSyncJobs')
    try:
        entity = await table_client.get_entity('SYNC_JOBS', commit_sha)
        return entity['status'] in ['completed', 'processing']
    except ResourceNotFoundError:
        return False
```

**Alternatives Considered**:

-   No signature verification → Rejected: Security risk
-   Synchronous processing → Rejected: GitHub webhook timeout (10s)
-   Event Grid for async → Rejected: Overkill, Azure Queue simpler

**Key Gotchas**:

-   Must use `hmac.compare_digest()` (timing-attack resistant)
-   Webhook secret stored in Key Vault, loaded at startup
-   Webhook timeouts after 10 seconds (must return 202 quickly)
-   GitHub retries on 5xx errors (exponential backoff, up to 3 attempts)

---

## Decision 6: Rsync-style File Sync Logic

**Chosen**: Three-phase diff algorithm (list, compare, apply)

**Rationale**:

-   Minimize Azure Files API calls (listing is expensive for large trees)
-   Efficiently compute add/modify/delete operations
-   Support --delete behavior (remove files not in GitHub)
-   Preserve performance for 100-1000 files

**Algorithm**:

```python
async def sync_github_to_azure_files(repo_url: str, branch: str, commit_sha: str):
    # Phase 1: Clone GitHub repo to temp directory
    temp_dir = f'/tmp/sync-{commit_sha}'
    subprocess.run(['git', 'clone', '--depth', '1', '--branch', branch, repo_url, temp_dir])

    # Phase 2: Build file trees
    github_files = {}  # path -> hash
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, temp_dir)
            with open(full_path, 'rb') as f:
                content_hash = hashlib.sha256(f.read()).hexdigest()
            github_files[rel_path] = (content_hash, full_path)

    azure_files = {}  # path -> hash
    share_client = ShareClient(account_url, share_name, credential)
    async for item in share_client.list_directories_and_files(directory_path='/'):
        if not item['is_directory']:
            file_client = share_client.get_file_client(item['name'])
            content = await file_client.download_file()
            content_hash = hashlib.sha256(content.readall()).hexdigest()
            azure_files[item['name']] = content_hash

    # Phase 3: Compute and apply diff
    to_add = set(github_files.keys()) - set(azure_files.keys())
    to_delete = set(azure_files.keys()) - set(github_files.keys())
    to_update = [
        path for path in github_files
        if path in azure_files and github_files[path][0] != azure_files[path]
    ]

    # Apply operations
    for path in to_delete:
        file_client = share_client.get_file_client(path)
        await file_client.delete_file()

    for path in to_add.union(to_update):
        file_client = share_client.get_file_client(path)
        with open(github_files[path][1], 'rb') as f:
            await file_client.upload_file(f)

    # Cleanup temp directory
    shutil.rmtree(temp_dir)
```

**Performance Optimization**:

-   Use `git clone --depth 1` (shallow clone, faster)
-   Parallel uploads/deletes with asyncio.gather() (up to 10 concurrent)
-   SHA256 hashing for content comparison (faster than byte-by-byte)
-   Skip hidden files (`.git/`, `.github/`)

**Alternatives Considered**:

-   Full re-upload every time → Rejected: Wasteful for large workspaces
-   Git pull in place → Rejected: Azure Files doesn't support .git metadata
-   Custom differ without hashing → Rejected: File size/mtime unreliable

**Key Gotchas**:

-   `/tmp` in container may be memory-backed (limit repo size <500MB)
-   Azure Files list_directories_and_files() doesn't recurse automatically (must walk tree)
-   Must handle nested directories (create parent before child)
-   Clean up temp directory to avoid disk space issues

---

## Decision 7: Azure Files SDK for Python

**Chosen**: `azure-storage-file-share` SDK with async support

**Rationale**:

-   Official Microsoft SDK for Azure Files (SMB shares)
-   Async API for non-blocking I/O in Azure Functions
-   Supports all required operations (read, write, list, delete, ZIP)
-   Compatible with DefaultAzureCredential (managed identity)

**Installation**:

```bash
pip install azure-storage-file-share azure-identity
```

**Common Operations**:

**List files recursively**:

```python
from azure.storage.fileshare import ShareServiceClient, ShareClient

async def list_all_files(share_name: str, directory_path: str = '/'):
    share_client = ShareServiceClient(account_url, credential).get_share_client(share_name)

    async def walk_directory(path: str):
        files = []
        async for item in share_client.list_directories_and_files(directory_path=path):
            item_path = f'{path}/{item["name"]}'.lstrip('/')
            if item['is_directory']:
                files.extend(await walk_directory(item_path))
            else:
                files.append(item_path)
        return files

    return await walk_directory(directory_path)
```

**Read file**:

```python
async def read_file(share_name: str, file_path: str) -> bytes:
    file_client = share_client.get_file_client(file_path)
    download = await file_client.download_file()
    return download.readall()
```

**Write file**:

```python
async def write_file(share_name: str, file_path: str, content: bytes):
    # Create parent directories if needed
    parts = file_path.split('/')
    for i in range(1, len(parts)):
        dir_path = '/'.join(parts[:i])
        dir_client = share_client.get_directory_client(dir_path)
        try:
            await dir_client.create_directory()
        except ResourceExistsError:
            pass

    # Upload file
    file_client = share_client.get_file_client(file_path)
    await file_client.upload_file(content)
```

**Generate ZIP archive**:

```python
import zipfile
from io import BytesIO

async def create_workspace_zip(share_name: str) -> BytesIO:
    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        files = await list_all_files(share_name, '/')
        for file_path in files:
            content = await read_file(share_name, file_path)
            zip_file.writestr(file_path, content)

    zip_buffer.seek(0)
    return zip_buffer
```

**Alternatives Considered**:

-   REST API directly → Rejected: SDK handles auth, retries, errors
-   Synchronous SDK → Rejected: Blocks event loop in async Azure Functions

**Key Gotchas**:

-   Must explicitly create parent directories before writing files
-   `list_directories_and_files()` doesn't recurse (must implement walker)
-   Share name must be lowercase, 3-63 characters
-   File paths use forward slashes, even on Windows
-   DefaultAzureCredential requires Storage Blob Data Contributor role (RBAC)

---

## Decision 8: Workspace Download as ZIP

**Chosen**: In-memory ZIP generation with streaming response

**Rationale**:

-   Avoids disk I/O in containerized environment
-   Streams directly to HTTP response (memory efficient)
-   Works for workspaces up to ~500MB (typical: 10-50MB)
-   Uses azure-storage-file-share + zipfile (stdlib)

**Implementation**:

```python
from azure.functions import HttpRequest, HttpResponse
import zipfile
from io import BytesIO

async def download_workspace(req: HttpRequest) -> HttpResponse:
    # 1. Create in-memory ZIP
    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # 2. List all files in /workspace share
        files = await list_all_files('workspaces', '/')

        # 3. Add each file to ZIP
        for file_path in files:
            content = await read_file('workspaces', file_path)
            zip_file.writestr(file_path, content)

    # 4. Rewind buffer and return
    zip_buffer.seek(0)
    return HttpResponse(
        body=zip_buffer.getvalue(),
        mimetype='application/zip',
        headers={
            'Content-Disposition': f'attachment; filename=workspace-{datetime.now().strftime("%Y%m%d-%H%M%S")}.zip'
        }
    )
```

**Performance Considerations**:

-   ZIP compression: ~2-5x reduction for text files (Python, YAML)
-   Memory usage: ~2x uncompressed size during generation
-   Typical workspace: 10-50MB → 5-25MB ZIP → 10-50MB peak memory
-   Azure Functions: 1.5GB memory limit (P1v2), sufficient for 500MB workspace

**Alternatives Considered**:

-   Write ZIP to Blob Storage, return URL → Rejected: Slower, requires cleanup
-   Stream ZIP without buffering → Rejected: zipfile.ZipFile requires seekable stream

**Key Gotchas**:

-   Must rewind BytesIO before returning (seek(0))
-   ZIP_DEFLATED requires zlib (included in Python stdlib)
-   Large workspaces (>500MB) may hit memory limits (consider blob storage fallback)
-   Filename should include timestamp to avoid caching issues

---

## Summary of Key Technologies

| Technology               | Version  | Purpose                | Documentation                                                              |
| ------------------------ | -------- | ---------------------- | -------------------------------------------------------------------------- |
| Azure Functions          | v4       | Compute platform       | https://learn.microsoft.com/en-us/azure/azure-functions/                   |
| Python                   | 3.11     | Backend language       | https://docs.python.org/3.11/                                              |
| Docker                   | 24+      | Containerization       | https://docs.docker.com/                                                   |
| Azure Files              | Hot tier | Workspace storage      | https://learn.microsoft.com/en-us/azure/storage/files/                     |
| Bicep                    | latest   | Infrastructure as Code | https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/      |
| azure-storage-file-share | 12.14.1+ | Python SDK             | https://learn.microsoft.com/en-us/python/api/azure-storage-file-share/     |
| debugpy                  | 1.8.0+   | Python debugging       | https://github.com/microsoft/debugpy                                       |
| Azurite                  | 3.28.0+  | Local storage emulator | https://learn.microsoft.com/en-us/azure/storage/common/storage-use-azurite |

---

## Open Questions Resolved

1. **Q**: Can Azure Functions containers mount Azure Files at arbitrary paths like `/workspace`?
   **A**: Yes, via `azureStorageAccounts` property in ARM template with custom `mountPath`.

2. **Q**: Does docker-compose.yml work for both local development and production?
   **A**: No, separate files needed. Dev uses Azurite + volume mounts. Prod uses ARM template with Azure services.

3. **Q**: How to enable VS Code debugging in containerized Azure Functions?
   **A**: Expose port 5678, add debugpy.listen() with ENABLE_DEBUGGING=true guard, use "Attach to Docker" launch config.

4. **Q**: Can Static Web App ARM template trigger GitHub Actions automatically?
   **A**: Yes, ARM deployment creates workflow file in `.github/workflows/` with API token injected as secret.

5. **Q**: How to prevent GitHub webhook replay attacks?
   **A**: HMAC-SHA256 signature verification + idempotency tracking (store processed commit SHAs in Table Storage).

6. **Q**: Is rsync --delete behavior efficient for 1000+ files?
   **A**: Yes, with optimizations: shallow git clone (--depth 1), SHA256 hashing, parallel uploads (asyncio.gather), skip hidden files.

7. **Q**: Can Azure Files SDK generate ZIP archives without disk I/O?
   **A**: Yes, use BytesIO buffer with zipfile.ZipFile in memory mode. Limit: ~500MB workspaces (Azure Functions 1.5GB memory).

8. **Q**: What's the performance impact of Hot tier Azure Files?
   **A**: <10ms latency, 10,000 IOPS, 300 MiB/s throughput. Sufficient for 50-200 orgs with 100-1000 workflow executions/day.

---

## Next Steps (Phase 1)

With all research complete, proceed to Phase 1 design:

1. Generate `data-model.md` (GitHub connection entity, sync job entity)
2. Generate API contracts (GitHub webhook endpoint, workspace files CRUD, download ZIP endpoint)
3. Generate `quickstart.md` (local setup with docker-compose, first deployment with ARM template)
4. Update agent context with new technologies (Docker, Azure Files SDK, Bicep)
