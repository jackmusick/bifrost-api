#!/bin/bash
set -e

# Check prerequisites
if ! command -v az &> /dev/null; then
    echo "Error: Azure CLI not found"
    echo ""
    echo "Install instructions:"
    echo "  macOS:  brew install azure-cli"
    echo "  Linux:  curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
    echo ""
    echo "More info: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo "Error: jq not found"
    echo ""
    echo "Install instructions:"
    echo "  macOS:  brew install jq"
    echo "  Linux:  sudo apt-get install jq"
    exit 1
fi

RESOURCE_GROUP="${1:-bifrost-rg}"
LOCATION="${2:-eastus}"
BASE_NAME="${3:-bifrost}"

echo "Creating resource group: $RESOURCE_GROUP"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

echo "Deploying infrastructure..."
OUTPUTS=$(az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "$(dirname "$0")/azuredeploy.json" \
    --parameters baseName="$BASE_NAME" \
    --query "properties.outputs" -o json)

API_APP_NAME=$(echo "$OUTPUTS" | jq -r '.apiFunctionAppName.value')
API_URL=$(echo "$OUTPUTS" | jq -r '.apiFunctionAppUrl.value')
SWA_NAME=$(echo "$OUTPUTS" | jq -r '.staticWebAppName.value')
SWA_URL=$(echo "$OUTPUTS" | jq -r '.staticWebAppUrl.value')

echo ""
echo "Deployment complete!"
echo "API Function App: $API_APP_NAME"
echo "API URL: $API_URL"
echo "Static Web App: $SWA_NAME"
echo "Static Web App URL: https://$SWA_URL"
echo ""
echo "Fetching GitHub secrets..."

API_PUBLISH_PROFILE=$(az functionapp deployment list-publishing-profiles \
    --name "$API_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --xml)

SWA_API_TOKEN=$(az staticwebapp secrets list \
    --name "$SWA_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.apiKey" -o tsv)

# Display instructions
echo "=========================================="
echo "GitHub Secrets Setup Instructions"
echo "=========================================="
echo ""
echo "Go to your GitHub repository settings:"
echo "Settings → Secrets and variables → Actions → New repository secret"
echo ""
echo "Add the following secrets:"
echo ""
echo "----------------------------------------"
echo "Secret Name: AZURE_API_FUNCTIONAPP_PUBLISH_PROFILE"
echo "----------------------------------------"
echo "$API_PUBLISH_PROFILE"
echo ""
echo "----------------------------------------"
echo "Secret Name: AZURE_STATIC_WEB_APPS_API_TOKEN"
echo "----------------------------------------"
echo "$SWA_API_TOKEN"
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "After adding these secrets to GitHub:"
echo "1. Your GitHub Actions workflows will be able to deploy automatically"
echo "2. Pushes to 'main' branch will trigger deployments"
echo ""
echo "Thank you for using Bifrost Integrations!"
echo ""