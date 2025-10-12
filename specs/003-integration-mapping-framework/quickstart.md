# Quickstart Guide: Integration Mapping Framework

**Feature**: Integration Mapping Framework
**Audience**: Developers implementing integrations with organization mapping support
**Time**: 30 minutes

## Overview

This guide walks you through implementing organization mapping support for an integration. By the end, you'll have:

1. ✅ Integration that supports organization discovery
2. ✅ UI that displays discovered external organizations
3. ✅ Workflow that uses mapped organization
4. ✅ Test connection functionality

## Prerequisites

- Python 3.11 development environment
- Azure Functions Core Tools v4
- Access to external integration API (or mock)
- Integration credentials stored in Key Vault

## Step 1: Implement Integration Interface (15 min)

### 1.1 Create Integration Class

Create a new file in `workflows/shared/integrations/my_integration.py`:

```python
from shared.integrations.base import BaseIntegration, ExternalOrganization, OrganizationMapping, TestResult
from shared.context import OrganizationContext
from typing import List
import aiohttp

class MyIntegration(BaseIntegration):
    """
    Example integration with organization mapping support.

    Replace 'My' with your integration name (e.g., HaloPSA, NinjaRMM).
    """

    def __init__(self, context: OrganizationContext):
        super().__init__(context)

    def supports_org_mapping(self) -> bool:
        """Enable organization mapping"""
        return True

    async def list_organizations(self) -> List[ExternalOrganization]:
        """
        Fetch organizations from external API.

        Replace this with your integration's API call.
        """
        # Get credentials from Key Vault
        api_key = self.context.get_secret("myintegration_api_key")
        api_url = self.context.get_config("myintegration_api_url") or "https://api.example.com"

        # Call external API
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{api_url}/organizations",
                headers={"Authorization": f"Bearer {api_key}"}
            ) as response:
                response.raise_for_status()
                data = await response.json()

        # Transform to standard format
        return [
            ExternalOrganization(
                id=str(org["id"]),  # External org ID (string)
                name=org["name"],   # Display name
                metadata={          # Optional extra data
                    "code": org.get("code"),
                    "tier": org.get("tier", "standard")
                }
            )
            for org in data["organizations"]
        ]

    async def get_client(self, mapping: OrganizationMapping):
        """
        Get pre-authenticated client for specific org mapping.

        This client will be used by workflows.
        """
        api_key = self.context.get_secret("myintegration_api_key")

        # Get org-specific config from mapping_data
        api_url = mapping.mapping_data.get(
            "api_base_url",
            "https://api.example.com"
        )

        # Return your integration's client class
        return MyIntegrationClient(
            api_key=api_key,
            api_url=api_url,
            organization_id=mapping.external_org_id
        )

    async def test_connection(self, mapping: OrganizationMapping) -> TestResult:
        """
        Test connection by making a lightweight API call.

        This is called when admin clicks "Test Connection" in UI.
        """
        try:
            client = await self.get_client(mapping)

            # Make simple API call to verify connection
            org_details = await client.get_organization_details(
                mapping.external_org_id
            )

            return TestResult(
                success=True,
                message=f"Successfully connected to {org_details['name']}",
                details={
                    "org_name": org_details["name"],
                    "org_id": mapping.external_org_id,
                    "connection_time": "45ms"
                }
            )

        except aiohttp.ClientResponseError as e:
            return TestResult(
                success=False,
                message=f"API error: {e.status} {e.message}",
                details={
                    "error_type": "APIError",
                    "status_code": e.status
                }
            )

        except Exception as e:
            return TestResult(
                success=False,
                message=f"Connection failed: {str(e)}",
                details={
                    "error_type": type(e).__name__
                }
            )


class MyIntegrationClient:
    """
    Client for interacting with external API.

    This is your integration-specific client that workflows will use.
    """

    def __init__(self, api_key: str, api_url: str, organization_id: str):
        self.api_key = api_key
        self.api_url = api_url
        self.organization_id = organization_id

    async def get_organization_details(self, org_id: str):
        """Fetch organization details (for test_connection)"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.api_url}/organizations/{org_id}",
                headers={"Authorization": f"Bearer {self.api_key}"}
            ) as response:
                response.raise_for_status()
                return await response.json()

    async def list_users(self):
        """Example: List users in organization (workflow usage)"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.api_url}/organizations/{self.organization_id}/users",
                headers={"Authorization": f"Bearer {self.api_key}"}
            ) as response:
                response.raise_for_status()
                return await response.json()
```

### 1.2 Register Integration

Add your integration to `workflows/shared/integrations/__init__.py`:

```python
from .my_integration import MyIntegration

INTEGRATION_REGISTRY = {
    # Existing integrations
    "msgraph": MsGraphIntegration,
    "halopsa": HaloPSAIntegration,

    # Your new integration
    "myintegration": MyIntegration,  # Add this line
}

def get_integration_class(integration_name: str):
    """Get integration class by name"""
    if integration_name not in INTEGRATION_REGISTRY:
        raise ValueError(f"Integration '{integration_name}' not found")

    return INTEGRATION_REGISTRY[integration_name]
```

### 1.3 Store Credentials

Store integration credentials in Key Vault:

```bash
# Store API key as global secret (GLOBAL partition)
az keyvault secret set \
  --vault-name your-keyvault \
  --name myintegration-api-key \
  --value "your-api-key-here"

# Or use the admin API
curl -X POST https://api.example.com/api/secrets \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "myintegration_api_key",
    "value": "your-api-key-here",
    "scope": "global"
  }'
```

## Step 2: Test Integration Discovery (5 min)

### 2.1 Start Local Development Server

```bash
# Terminal 1: Start Azurite (if not running)
./specify/scripts/start-azurite.sh

# Terminal 2: Start Workflows Function App
cd workflows
func start --port 7072
```

### 2.2 Test Discovery Endpoint

```bash
# Test organization discovery
curl http://localhost:7072/api/integrations/myintegration/discover?orgId=YOUR_ORG_ID

# Expected response:
# {
#   "organizations": [
#     {
#       "id": "12345",
#       "name": "Acme Corp",
#       "metadata": {"code": "ACME001", "tier": "premium"}
#     },
#     {
#       "id": "67890",
#       "name": "Wayne Enterprises",
#       "metadata": {"code": "WAYNE001", "tier": "enterprise"}
#     }
#   ],
#   "cached_at": "2025-10-11T10:00:00Z",
#   "cache_expires_at": "2025-10-11T11:00:00Z"
# }
```

## Step 3: Create Mapping via UI (5 min)

### 3.1 Navigate to Organizations Page

1. Open browser: `http://localhost:5173`
2. Navigate to **Organizations**
3. Select an organization
4. Click **Integrations** tab

### 3.2 Create Mapping

1. Click **Add Integration Mapping** button
2. Select **MyIntegration** from dropdown
3. Click **Discover Organizations** (loads external orgs)
4. Select **Acme Corp** from dropdown
5. Optional: Add mapping data (e.g., custom API URL)
6. Click **Test Connection** to verify
7. Click **Save**

**Result**: Mapping is now created and ready for workflows to use.

## Step 4: Use Mapping in Workflow (5 min)

### 4.1 Create Workflow

Create `workflows/workflows/sync_users.py`:

```python
from shared.decorators import workflow, param
from shared.context import OrganizationContext

@workflow(
    name="sync_users",
    description="Sync users from MyIntegration to platform",
    category="User Management",
    tags=["sync", "users", "myintegration"]
)
async def sync_users(context: OrganizationContext):
    """
    Sync users from MyIntegration using organization mapping.

    This workflow demonstrates how to retrieve and use an integration mapping.
    """

    # Log workflow start
    await context.log("info", "Starting user sync from MyIntegration")

    try:
        # Get integration mapping (automatically scoped to current org)
        mapping = await context.get_integration_mapping("myintegration")

        await context.log("info", f"Using mapping: {mapping.external_org_name} (ID: {mapping.external_org_id})")

        # Get pre-authenticated client (uses mapping automatically)
        client = await context.get_integration("myintegration", mapping_id=mapping.id)

        # Use client (already scoped to correct external org)
        users = await client.list_users()

        await context.log("info", f"Found {len(users)} users in {mapping.external_org_name}")

        # Process users
        synced_count = 0
        for user in users:
            # Your sync logic here
            await sync_user_to_platform(user)
            synced_count += 1

        await context.log("info", f"Synced {synced_count} users successfully")

        return {
            "success": True,
            "users_synced": synced_count,
            "external_org": mapping.external_org_name
        }

    except MappingNotFoundError:
        # No mapping configured for this org
        await context.log("error", "MyIntegration mapping not configured for this organization")
        return {
            "success": False,
            "error": "Integration mapping not configured"
        }

    except Exception as e:
        await context.log("error", f"User sync failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
```

### 4.2 Test Workflow

```bash
# Execute workflow via API
curl -X POST http://localhost:7071/api/workflows/execute \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: YOUR_ORG_ID" \
  -d '{
    "workflow_name": "sync_users",
    "parameters": {}
  }'

# Check logs
curl http://localhost:7071/api/executions/EXECUTION_ID/logs
```

## Step 5: Handle Multiple Mappings (Optional)

If your integration supports multiple mappings per organization (e.g., multiple M365 tenants):

### 5.1 Create Multiple Mappings

Via UI:
1. Organizations → Integrations tab
2. Add first mapping: "Tenant A" with external_org_id "tenant-a-id"
3. Add second mapping: "Tenant B" with external_org_id "tenant-b-id"

### 5.2 Use Specific Mapping in Workflow

```python
@workflow(name="sync_users_from_tenant")
@param("tenant_name", type="string", label="Tenant", required=True, data_provider="list_tenant_mappings")
async def sync_users_from_tenant(context: OrganizationContext, tenant_name: str):
    """Sync users from specific tenant when multiple mappings exist"""

    # Get specific mapping by ID
    mapping = await context.get_integration_mapping(
        "microsoft_graph",
        mapping_id=tenant_name  # e.g., "mapping_001"
    )

    client = await context.get_integration("microsoft_graph", mapping_id=mapping.id)

    users = await client.list_users()

    return {"users": len(users), "tenant": mapping.external_org_name}
```

### 5.3 Create Data Provider for Mapping Selection

```python
from shared.decorators import data_provider

@data_provider(
    name="list_tenant_mappings",
    description="List all M365 tenant mappings for organization",
    category="Integration Mappings"
)
async def list_tenant_mappings(context: OrganizationContext):
    """
    Returns dropdown options for selecting which M365 tenant to use.

    This data provider enables workflows to let users choose from
    multiple mappings dynamically.
    """
    # Get all mappings for microsoft_graph integration
    mappings = await context.get_org_mappings("microsoft_graph")

    return [
        {
            "label": f"{m.external_org_name} ({m.external_org_id})",
            "value": m.id  # mapping_id
        }
        for m in mappings
    ]
```

## Common Patterns

### Pattern 1: Fallback to Global Credentials

If mapping is optional, fall back to global credentials:

```python
async def my_workflow(context: OrganizationContext):
    try:
        # Try to use org-specific mapping
        mapping = await context.get_integration_mapping("myintegration")
        client = await context.get_integration("myintegration", mapping_id=mapping.id)
    except MappingNotFoundError:
        # Fall back to global credentials
        api_key = context.get_secret("myintegration_api_key_global")
        client = MyIntegrationClient(api_key=api_key, org_id=None)

    # Use client (works with or without mapping)
    data = await client.get_data()
    return data
```

### Pattern 2: Conditional Workflow Based on Mapping

Only run workflow if mapping exists:

```python
@workflow(name="sync_if_mapped")
async def sync_if_mapped(context: OrganizationContext):
    # Check if mapping exists
    try:
        mapping = await context.get_integration_mapping("myintegration")
    except MappingNotFoundError:
        return {
            "success": True,
            "skipped": True,
            "reason": "Integration not configured for this organization"
        }

    # Mapping exists, proceed with sync
    client = await context.get_integration("myintegration")
    # ... sync logic
```

### Pattern 3: Create Mapping from Workflow

Workflows can create mappings programmatically:

```python
@workflow(name="auto_setup_integration")
@param("external_org_id", type="string", required=True)
async def auto_setup_integration(context: OrganizationContext, external_org_id: str):
    """
    Automatically create integration mapping during onboarding.

    Useful for automated provisioning workflows.
    """

    # Create mapping
    mapping = await context.set_integration_mapping(
        integration_name="myintegration",
        external_org_id=external_org_id,
        external_org_name="Auto-configured org",
        mapping_data={
            "api_base_url": "https://custom.example.com",
            "auto_created": True
        }
    )

    # Test connection
    integration = context.get_integration_class("myintegration")(context)
    test_result = await integration.test_connection(mapping)

    if not test_result.success:
        # Delete mapping if test failed
        await context.delete_integration_mapping("myintegration", mapping.id)
        return {"success": False, "error": test_result.message}

    return {"success": True, "mapping_id": mapping.id}
```

## Testing

### Unit Tests

Test integration discovery:

```python
# tests/unit/test_my_integration.py
import pytest
from shared.integrations.my_integration import MyIntegration
from tests.fixtures import mock_context

@pytest.mark.asyncio
async def test_list_organizations(mock_context, mock_api_response):
    integration = MyIntegration(mock_context)

    orgs = await integration.list_organizations()

    assert len(orgs) == 2
    assert orgs[0].name == "Acme Corp"
    assert orgs[0].id == "12345"
```

### Integration Tests

Test end-to-end mapping flow:

```python
# tests/integration/test_integration_mapping_workflow.py
import pytest
from workflows.workflows.sync_users import sync_users
from tests.fixtures import mock_context, azurite_storage

@pytest.mark.asyncio
async def test_sync_users_with_mapping(mock_context, azurite_storage):
    # Setup: Create mapping
    await mock_context.set_integration_mapping(
        integration_name="myintegration",
        external_org_id="12345",
        external_org_name="Acme Corp"
    )

    # Execute: Run workflow
    result = await sync_users(mock_context)

    # Assert: Workflow succeeded
    assert result["success"] is True
    assert result["users_synced"] > 0
```

## Troubleshooting

### Discovery Returns Empty List

**Cause**: API credentials invalid or insufficient permissions

**Fix**:
1. Verify Key Vault secret: `az keyvault secret show --vault-name your-vault --name myintegration-api-key`
2. Test API directly: `curl -H "Authorization: Bearer $API_KEY" https://api.example.com/organizations`
3. Check API permissions (integration may need "read:organizations" scope)

### Test Connection Fails

**Cause**: External org ID doesn't exist or mapping_data is invalid

**Fix**:
1. Verify external org ID exists in integration system
2. Check mapping_data fields match integration requirements
3. Review test_connection() logs for detailed error

### Workflow Can't Find Mapping

**Cause**: Mapping not created or org_id mismatch

**Fix**:
1. Check mapping exists in OrgIntegrationMappings table
2. Verify X-Organization-Id header matches mapping's org_id
3. Ensure mapping is active (is_active=true)

## Next Steps

- **Add more integrations**: Repeat this guide for HaloPSA, NinjaRMM, etc.
- **Build forms**: Create dynamic forms that use integration mappings
- **Monitor health**: Add scheduled workflow to test all mappings weekly
- **Documentation**: Document required mapping_data fields for your integration

## Reference

- **Integration Interface**: `/specs/003-integration-mapping-framework/contracts/integration-interface.py`
- **API Spec**: `/specs/003-integration-mapping-framework/contracts/mapping-api.yaml`
- **Data Model**: `/specs/003-integration-mapping-framework/data-model.md`
- **Architecture**: `/specs/003-integration-mapping-framework/research.md`
