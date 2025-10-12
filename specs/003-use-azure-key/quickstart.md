# Quickstart: Azure Key Vault Integration for Local Development

**Purpose**: Get up and running with Azure Key Vault secret management in your local development environment.

**Last Updated**: 2025-10-12

## Prerequisites

- Python 3.11+ with project dependencies installed
- Azure CLI installed (`brew install azure-cli` on macOS)
- Access to an Azure Key Vault instance (or use local fallback)

## Option 1: Use Azure Key Vault (Recommended)

This option provides dev/prod parity by using the actual Azure Key Vault in local development.

### Step 1: Authenticate with Azure CLI

```bash
# Login to Azure
az login

# Verify your identity
az account show
```

The `DefaultAzureCredential` will automatically use your Azure CLI credentials for local development.

**Test Your Authentication** (Recommended):

Run the authentication test script to verify everything is working:

```bash
# From project root
python scripts/test-azure-auth.py

# Or specify vault URL directly
python scripts/test-azure-auth.py --vault-url https://your-vault.vault.azure.net/
```

This script will:
- ✓ Verify your Azure authentication is working
- ✓ Test Key Vault connectivity
- ✓ Check your permissions (list, get)
- ✓ Provide troubleshooting guidance if issues are found

### Step 2: Configure Key Vault URL

Edit `workflows/local.settings.json` (or `client/api/local.settings.json`):

```json
{
  "Values": {
    "AZURE_KEY_VAULT_URL": "https://your-actual-keyvault.vault.azure.net/"
  }
}
```

**Important**: Replace `your-actual-keyvault` with your actual Key Vault name.

### Step 3: Verify Access Permissions

Ensure you have the required Key Vault permissions:

- **Secrets: Get** - Read secret values
- **Secrets: List** - List available secrets (optional, for UI dropdown)

To check your permissions:

```bash
az keyvault secret list --vault-name your-keyvault-name
```

If this command succeeds, you're ready to go!

### Step 4: Test Secret Access

Create a test secret in your Key Vault:

```bash
# Create an org-scoped secret
az keyvault secret set --vault-name your-keyvault-name --name "testorg--api-key" --value "test-secret-value"

# Create a global secret
az keyvault secret set --vault-name your-keyvault-name --name "GLOBAL--smtp-password" --value "test-global-secret"
```

### Step 5: Run Your Application

```bash
cd workflows
func start
```

Your application will now use Azure Key Vault for secret resolution!

---

## Option 2: Local Fallback (No Azure Access Required)

If you don't have access to Azure Key Vault or want to develop offline, you can use environment variable fallback.

### Step 1: Configure Local Secrets

Edit `workflows/local.settings.json`:

```json
{
  "Values": {
    "AZURE_KEY_VAULT_URL": "",
    "ORG123__MSGRAPH_CLIENT_SECRET": "local-test-secret",
    "ORG123__API_KEY": "local-api-key",
    "GLOBAL__SMTP_PASSWORD": "local-smtp-password"
  }
}
```

**Naming Pattern**:
- Org-scoped: `{ORG_ID}__{SECRET_KEY}` (e.g., `ORG123__API_KEY`)
- Platform-wide: `GLOBAL__{SECRET_KEY}` (e.g., `GLOBAL__SMTP_PASSWORD`)

**Important**:
- Use uppercase for org IDs and secret keys
- Replace hyphens with underscores
- Example: org `test-org` + secret `client-secret` → `TEST_ORG__CLIENT_SECRET`

### Step 2: Alternative - Use .env File

Create a `.env` file in the project root (already git-ignored):

```bash
# .env file
AZURE_KEY_VAULT_URL=

# Org-scoped secrets
ORG123__MSGRAPH_CLIENT_SECRET=local-test-secret
ORG123__API_KEY=local-api-key

# Global secrets
GLOBAL__SMTP_PASSWORD=local-smtp-password
```

Python's `python-dotenv` package (already installed) will automatically load these variables.

### Step 3: Run Your Application

```bash
cd workflows
func start
```

Your application will use the local environment variables as fallback!

---

## Troubleshooting

### Error: "Authentication failed"

**Problem**: Azure CLI credentials not available

**Solutions**:
1. Run `az login` and complete authentication
2. Run `az account show` to verify you're logged in
3. If using service principal, ensure environment variables are set
4. Use local fallback instead (Option 2)

### Error: "Permission denied"

**Problem**: Your Azure AD identity lacks Key Vault permissions

**Solutions**:
1. Ask your Azure administrator to grant you "Key Vault Secrets User" role
2. Verify permissions with `az keyvault secret list --vault-name your-keyvault-name`
3. Use local fallback instead (Option 2)

### Error: "Secret 'xxx' not found"

**Problem**: Secret doesn't exist in Key Vault or local config

**Solutions**:
1. **Check Key Vault**: `az keyvault secret list --vault-name your-keyvault-name | grep xxx`
2. **Check naming convention**: Secret names use hyphens (e.g., `org123--api-key`)
3. **For local**: Env vars use underscores (e.g., `ORG123__API_KEY`)
4. **Fallback order**: Org-scoped → Global → Error
5. Create the secret if it doesn't exist

### Error: "Key Vault unavailable"

**Problem**: Network connectivity or Key Vault URL misconfigured

**Solutions**:
1. Verify Key Vault URL in `local.settings.json`
2. Check network connectivity: `ping your-keyvault.vault.azure.net`
3. System automatically falls back to local config on connection errors
4. Check logs for warning messages about fallback

---

## Secret Naming Convention

Follow this naming convention for consistent secret management:

### Key Vault Secrets (Production & Local with Azure Access)

```
{org_id}--{secret-name}    # Org-scoped
GLOBAL--{secret-name}       # Platform-wide
```

Examples:
- `org-abc123--msgraph-client-secret`
- `org-abc123--api-key`
- `GLOBAL--smtp-password`

### Environment Variables (Local Fallback)

```
{ORG_ID}__{SECRET_KEY}      # Org-scoped
GLOBAL__{SECRET_KEY}        # Platform-wide
```

Examples:
- `ORG_ABC123__MSGRAPH_CLIENT_SECRET`
- `ORG_ABC123__API_KEY`
- `GLOBAL__SMTP_PASSWORD`

**Conversion Rules**:
- Replace hyphens (`-`) with underscores (`_`)
- Convert to UPPERCASE
- Use double-dash (`--`) in Key Vault
- Use double-underscore (`__`) in environment variables

---

## Configuration in Workflows

Once set up, accessing secrets is transparent:

```python
from engine.shared.context import OrganizationContext

# In your workflow function
def my_workflow(context: OrganizationContext):
    # Automatically resolves secret if config type is 'secret_ref'
    api_key = context.get_config("api_key")

    # Use the secret
    print(f"Using API key: {api_key[:4]}...")  # Only show first 4 chars
```

The system automatically:
1. Detects if config type is `secret_ref`
2. Looks up secret in Key Vault (org-scoped → global fallback)
3. Falls back to environment variables if Key Vault unavailable
4. Caches secret values for 1 hour to minimize API calls
5. Never logs secret values

---

## Next Steps

- [Implementation Plan](./plan.md) - Full technical architecture
- [Research Findings](./research.md) - Detailed design decisions
- [Tasks](./tasks.md) - Implementation task breakdown

For production deployment, see ARM template documentation for Key Vault provisioning and managed identity configuration.
