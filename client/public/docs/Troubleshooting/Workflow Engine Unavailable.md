# Workflow Engine Unavailable

The workflow engine is a critical component that executes workflows and forms. When it's unavailable, workflow-dependent features will be disabled.

## Production

### Check Azure Function App Status

1. Navigate to the Azure Portal
2. Find your workflow engine Function App
3. Check the **Overview** page for:
    - Status (should be "Running")
    - Recent errors in the logs
    - HTTP trigger status

### Verify Function App Configuration

1. Check **Configuration** > **Application settings**:

    - `AZURE_STORAGE_ACCOUNT_NAME` - should point to your storage account
    - `KEYVAULT_URL` - should be set to your Key Vault URL
    - `AZURE_TABLES_CONNECTION_STRING` - should be valid

2. Verify **Identity** is enabled:
    - System-assigned managed identity should be **On**
    - This identity needs Key Vault access

### Check Function App Logs

1. Go to **Monitoring** > **Log stream**
2. Look for startup errors or exceptions
3. Common issues:
    - Storage account connection failures
    - Key Vault access denied
    - Missing environment variables

### Verify Network Connectivity

1. If using VNet integration, check:

    - VNet configuration is correct
    - Network security groups allow traffic
    - Private endpoints are configured properly

2. Test the health endpoint:
    ```bash
    curl https://your-workflow-engine.azurewebsites.net/api/health
    ```

### Check CORS Configuration

If the workflow engine is running but the client can't connect:

1. Go to **API** > **CORS**
2. Ensure your client domain is in the allowed origins list
3. Or use `*` for development (not recommended for production)

## Development

### Start the Local Workflow Engine

1. Navigate to the workflows directory:

    ```bash
    cd workflows
    ```

2. Start Azurite (local storage emulator):

    ```bash
    # In a separate terminal
    azurite --silent --location azurite --debug azurite\debug.log
    ```

3. Start the Function App:

    ```bash
    func start
    ```

4. Verify it's running:
    ```bash
    curl http://localhost:7071/api/health
    ```

### Common Development Issues

#### Port Already in Use

If port 7071 is already in use:

```bash
# Find the process
lsof -i :7071

# Kill it
kill -9 <PID>
```

#### Missing Dependencies

Ensure all Python dependencies are installed:

```bash
pip install -r requirements.txt
```

#### Storage Emulator Not Running

If you see storage connection errors:

1. Start Azurite:

    ```bash
    azurite --silent --location azurite --debug azurite\debug.log
    ```

2. Verify it's running on the default ports (10000, 10001, 10002)

#### Environment Variables

Check your `local.settings.json`:

```json
{
    "IsEncrypted": false,
    "Values": {
        "AzureWebJobsStorage": "UseDevelopmentStorage=true",
        "FUNCTIONS_WORKER_RUNTIME": "python",
        "AZURE_STORAGE_ACCOUNT_NAME": "devstoreaccount1",
        "KEYVAULT_URL": "your-keyvault-url",
        "AZURE_TABLES_CONNECTION_STRING": "UseDevelopmentStorage=true"
    }
}
```

#### Python Version

Ensure you're using Python 3.11:

```bash
python --version  # Should show 3.11.x
```

### Testing the Connection

From the client directory, test the proxy endpoint:

```bash
curl http://localhost:5173/api/workflows/health
```

This should proxy through the client API to the workflow engine.
