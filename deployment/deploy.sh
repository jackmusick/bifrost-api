#!/bin/bash
set -e

# Check prerequisites
MISSING_TOOLS=()

if ! command -v az &> /dev/null; then
    MISSING_TOOLS+=("az (Azure CLI)")
fi

if ! command -v jq &> /dev/null; then
    MISSING_TOOLS+=("jq")
fi

if ! command -v func &> /dev/null; then
    MISSING_TOOLS+=("func (Azure Functions Core Tools)")
fi

if ! command -v swa &> /dev/null; then
    MISSING_TOOLS+=("swa (Azure Static Web Apps CLI)")
fi

if [ ${#MISSING_TOOLS[@]} -gt 0 ]; then
    echo "Error: Missing required tools"
    echo ""
    echo "The following tools are required but not installed:"
    for tool in "${MISSING_TOOLS[@]}"; do
        echo "  - $tool"
    done
    echo ""
    echo "Install instructions:"
    echo "  Azure CLI:"
    echo "    macOS:  brew install azure-cli"
    echo "    Linux:  curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
    echo "    More:   https://learn.microsoft.com/en-us/cli/azure/install-azure-cli"
    echo ""
    echo "  jq:"
    echo "    macOS:  brew install jq"
    echo "    Linux:  sudo apt-get install jq"
    echo ""
    echo "  Azure Functions Core Tools:"
    echo "    npm install -g azure-functions-core-tools@4"
    echo ""
    echo "  Azure Static Web Apps CLI:"
    echo "    npm install -g @azure/static-web-apps-cli"
    echo ""
    exit 1
fi

# Parse arguments
RESET=false
RESOURCE_GROUP="bifrost-rg"
LOCATION="eastus"
BASE_NAME="bifrost"

while [[ $# -gt 0 ]]; do
    case $1 in
        --reset)
            RESET=true
            shift
            ;;
        *)
            if [ -z "${RESOURCE_GROUP_SET}" ]; then
                RESOURCE_GROUP="$1"
                RESOURCE_GROUP_SET=true
            elif [ -z "${LOCATION_SET}" ]; then
                LOCATION="$1"
                LOCATION_SET=true
            elif [ -z "${BASE_NAME_SET}" ]; then
                BASE_NAME="$1"
                BASE_NAME_SET=true
            fi
            shift
            ;;
    esac
done

# Handle reset flag
if [ "$RESET" = true ]; then
    echo "Reset flag detected - checking if resource group exists..."
    if [ "$(az group exists --name "$RESOURCE_GROUP" -o tsv)" = "true" ]; then
        echo "WARNING: This will delete ALL resources in resource group: $RESOURCE_GROUP"
        read -p "Are you sure you want to continue? (yes/no): " -r
        if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            echo "Deleting resource group: $RESOURCE_GROUP"
            az group delete --name "$RESOURCE_GROUP" --yes --no-wait
            echo "Waiting for resource group deletion to complete..."
            az group wait --name "$RESOURCE_GROUP" --deleted --timeout 600 2>/dev/null || true
            echo "Resource group deleted successfully"
        else
            echo "Reset cancelled"
            exit 0
        fi
    else
        echo "Resource group does not exist, skipping deletion"
    fi
fi

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
echo "Deploying applications..."

# Deploy Function App
if [ -d "$(dirname "$0")/../api" ]; then
    echo "Deploying Function App from local build..."
    cd "$(dirname "$0")/../api"
    func azure functionapp publish "$API_APP_NAME"
    cd - > /dev/null
else
    echo "WARNING: API directory not found, skipping Function App deployment"
fi

# Deploy Static Web App
if [ -d "$(dirname "$0")/../client/dist" ]; then
    echo "Deploying Static Web App from client/dist..."

    # Get SWA deployment token
    SWA_API_TOKEN=$(az staticwebapp secrets list \
        --name "$SWA_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query "properties.apiKey" -o tsv)

    cd "$(dirname "$0")/../client"
    swa deploy \
        --app-name "$SWA_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --deployment-token "$SWA_API_TOKEN" \
        --env production
    cd - > /dev/null
else
    echo "WARNING: Client dist directory not found, skipping Static Web App deployment"
    echo "Build the client first with: cd client && npm run build"
fi

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "API Function App: $API_APP_NAME"
echo "API URL: $API_URL"
echo "Static Web App: $SWA_NAME"
echo "Static Web App URL: https://$SWA_URL"
echo ""
echo "Thank you for using Bifrost Integrations!"
echo ""