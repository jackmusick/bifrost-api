#!/bin/bash

# Bifrost Integrations - Production Deployment Script
# Deploys all Azure resources via Bicep templates

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_DIR="$PROJECT_ROOT/deployment"

# Default values
ENVIRONMENT="${ENVIRONMENT:-prod}"
RESOURCE_GROUP_NAME="${RESOURCE_GROUP_NAME:-bifrost-${ENVIRONMENT}-rg}"
LOCATION="${LOCATION:-eastus2}"
PARAMETER_FILE="${PARAMETER_FILE:-$DEPLOYMENT_DIR/parameters/${ENVIRONMENT}.json}"

echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Bifrost Integrations Deployment Script    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}→ Checking prerequisites...${NC}"

if ! command -v az &> /dev/null; then
    echo -e "${RED}✗ Azure CLI not found. Please install it: https://aka.ms/azure-cli${NC}"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found. Please install Docker Desktop${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites check passed${NC}"
echo ""

# Check Azure login
echo -e "${YELLOW}→ Checking Azure login...${NC}"
if ! az account show &> /dev/null; then
    echo -e "${YELLOW}⚠ Not logged in to Azure. Running 'az login'...${NC}"
    az login
fi

SUBSCRIPTION_NAME=$(az account show --query name -o tsv)
echo -e "${GREEN}✓ Logged in to Azure${NC}"
echo -e "${BLUE}  Subscription: ${SUBSCRIPTION_NAME}${NC}"
echo ""

# Prompt for confirmation
echo -e "${YELLOW}Deployment Configuration:${NC}"
echo -e "  Environment:      ${ENVIRONMENT}"
echo -e "  Resource Group:   ${RESOURCE_GROUP_NAME}"
echo -e "  Location:         ${LOCATION}"
echo -e "  Parameter File:   ${PARAMETER_FILE}"
echo ""

read -p "$(echo -e ${YELLOW}Continue with deployment? [y/N]: ${NC})" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}✗ Deployment cancelled${NC}"
    exit 1
fi

# Create resource group
echo ""
echo -e "${YELLOW}→ Creating resource group '${RESOURCE_GROUP_NAME}'...${NC}"
az group create \
  --name "$RESOURCE_GROUP_NAME" \
  --location "$LOCATION" \
  --output none

echo -e "${GREEN}✓ Resource group created${NC}"

# Deploy ARM template
echo ""
echo -e "${YELLOW}→ Deploying ARM template...${NC}"
echo -e "${BLUE}  This may take 10-15 minutes...${NC}"
echo ""

DEPLOYMENT_NAME="bifrost-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)"

if az deployment group create \
  --name "$DEPLOYMENT_NAME" \
  --resource-group "$RESOURCE_GROUP_NAME" \
  --template-file "$DEPLOYMENT_DIR/azuredeploy.json" \
  --parameters "$PARAMETER_FILE" \
  --output json > /tmp/deployment-output.json 2>&1; then

    echo ""
    echo -e "${GREEN}✓ Deployment successful!${NC}"
else
    echo ""
    echo -e "${RED}✗ Deployment failed. Check output below:${NC}"
    cat /tmp/deployment-output.json
    exit 1
fi

# Extract outputs
echo ""
echo -e "${YELLOW}→ Extracting deployment outputs...${NC}"

API_FUNCTION_APP_URL=$(jq -r '.properties.outputs.apiFunctionAppUrl.value' /tmp/deployment-output.json)
API_FUNCTION_APP_NAME=$(jq -r '.properties.outputs.apiFunctionAppName.value' /tmp/deployment-output.json)
WORKFLOWS_FUNCTION_APP_URL=$(jq -r '.properties.outputs.workflowsFunctionAppUrl.value' /tmp/deployment-output.json)
WORKFLOWS_FUNCTION_APP_NAME=$(jq -r '.properties.outputs.workflowsFunctionAppName.value' /tmp/deployment-output.json)
STATIC_WEB_APP_URL=$(jq -r '.properties.outputs.staticWebAppUrl.value' /tmp/deployment-output.json)
STATIC_WEB_APP_NAME=$(jq -r '.properties.outputs.staticWebAppName.value' /tmp/deployment-output.json)
GITHUB_WEBHOOK_URL=$(jq -r '.properties.outputs.githubWebhookUrl.value' /tmp/deployment-output.json)
STORAGE_ACCOUNT_NAME=$(jq -r '.properties.outputs.storageAccountName.value' /tmp/deployment-output.json)
KEY_VAULT_NAME=$(jq -r '.properties.outputs.keyVaultName.value' /tmp/deployment-output.json)

# Display results
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Deployment Complete! 🎉             ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📍 URLs:${NC}"
echo -e "   Static Web App:       ${STATIC_WEB_APP_URL}"
echo -e "   API Function App:     ${API_FUNCTION_APP_URL}"
echo -e "   Workflows Function:   ${WORKFLOWS_FUNCTION_APP_URL}"
echo -e "   GitHub Webhook:       ${GITHUB_WEBHOOK_URL}"
echo ""
echo -e "${BLUE}📦 Resources:${NC}"
echo -e "   Static Web App:       ${STATIC_WEB_APP_NAME}"
echo -e "   API Function App:     ${API_FUNCTION_APP_NAME}"
echo -e "   Workflows Function:   ${WORKFLOWS_FUNCTION_APP_NAME}"
echo -e "   Storage Account:      ${STORAGE_ACCOUNT_NAME}"
echo -e "   Key Vault:            ${KEY_VAULT_NAME}"
echo ""
echo -e "${BLUE}🔍 Verify Deployment:${NC}"
echo -e "   curl ${API_FUNCTION_APP_URL}/api/health"
echo -e "   curl ${WORKFLOWS_FUNCTION_APP_URL}/api/health"
echo ""
echo -e "${BLUE}📝 Next Steps:${NC}"
echo -e "   1. Configure GitHub Actions deployment (see below)"
echo -e "   2. Upload OAuth credentials to Key Vault"
echo -e "   3. Configure organization settings via UI"
echo -e "   4. Test workflow execution"
echo ""

# Save outputs to file
OUTPUT_FILE="$PROJECT_ROOT/deployment-outputs-${ENVIRONMENT}.json"
cat /tmp/deployment-output.json > "$OUTPUT_FILE"
echo -e "${GREEN}✓ Deployment outputs saved to: ${OUTPUT_FILE}${NC}"
echo ""

# Configure API Function App with Workflows function key
echo -e "${YELLOW}→ Configuring inter-app communication...${NC}"
echo ""

# Wait for Workflows Function App to be ready
echo "Waiting for Workflows Function App runtime to initialize..."
sleep 30

# Get the workflows function key
WORKFLOWS_FUNCTION_KEY=$(az functionapp keys list \
  --name "$WORKFLOWS_FUNCTION_APP_NAME" \
  --resource-group "$RESOURCE_GROUP_NAME" \
  --query "functionKeys.default" -o tsv 2>/dev/null)

if [ -n "$WORKFLOWS_FUNCTION_KEY" ]; then
    # Set the function key in API Function App
    az functionapp config appsettings set \
      --name "$API_FUNCTION_APP_NAME" \
      --resource-group "$RESOURCE_GROUP_NAME" \
      --settings "WORKFLOWS_ENGINE_FUNCTION_KEY=$WORKFLOWS_FUNCTION_KEY" \
      --output none

    echo -e "${GREEN}✓ Inter-app communication configured${NC}"
else
    echo -e "${YELLOW}⚠ Could not retrieve Workflows function key. You may need to set WORKFLOWS_ENGINE_FUNCTION_KEY manually.${NC}"
fi
echo ""

# Extract deployment credentials
echo -e "${YELLOW}→ Extracting deployment credentials...${NC}"
echo ""

# Get API Function App publish profile
API_PUBLISH_PROFILE=$(az functionapp deployment list-publishing-profiles \
  --name "$API_FUNCTION_APP_NAME" \
  --resource-group "$RESOURCE_GROUP_NAME" \
  --xml 2>/dev/null)

# Get Workflows Function App publish profile
WORKFLOWS_PUBLISH_PROFILE=$(az functionapp deployment list-publishing-profiles \
  --name "$WORKFLOWS_FUNCTION_APP_NAME" \
  --resource-group "$RESOURCE_GROUP_NAME" \
  --xml 2>/dev/null)

# Get Static Web App deployment token
SWA_DEPLOYMENT_TOKEN=$(az staticwebapp secrets list \
  --name "$STATIC_WEB_APP_NAME" \
  --resource-group "$RESOURCE_GROUP_NAME" \
  --query "properties.apiKey" -o tsv 2>/dev/null)

# Detect GitHub repository
GITHUB_REPO=""
if [ -d "$PROJECT_ROOT/.git" ]; then
    GITHUB_REPO=$(cd "$PROJECT_ROOT" && git config --get remote.origin.url | sed 's/.*github.com[:/]\(.*\)\.git/\1/' 2>/dev/null || echo "")
fi

if [ -z "$GITHUB_REPO" ]; then
    GITHUB_REPO="your-username/your-repo"
fi

# Display GitHub Actions configuration instructions
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          GitHub Actions Configuration Required              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Your infrastructure is deployed, but GitHub Actions needs secrets${NC}"
echo -e "${BLUE}to deploy your application code.${NC}"
echo ""
echo -e "${YELLOW}Step 1: Go to your GitHub repository secrets page:${NC}"
echo -e "   https://github.com/${GITHUB_REPO}/settings/secrets/actions"
echo ""
echo -e "${YELLOW}Step 2: Click 'New repository secret' and add these 3 secrets:${NC}"
echo ""

# Save secrets to a temporary file for easy copying
SECRETS_FILE="/tmp/bifrost-github-secrets-${ENVIRONMENT}.txt"
cat > "$SECRETS_FILE" << EOF
# GitHub Secrets for Bifrost Integrations Deployment
# Add these at: https://github.com/${GITHUB_REPO}/settings/secrets/actions

# Secret 1: AZURE_API_FUNCTIONAPP_PUBLISH_PROFILE
${API_PUBLISH_PROFILE}

# Secret 2: AZURE_WORKFLOWS_FUNCTIONAPP_PUBLISH_PROFILE
${WORKFLOWS_PUBLISH_PROFILE}

# Secret 3: AZURE_STATIC_WEB_APPS_API_TOKEN
${SWA_DEPLOYMENT_TOKEN}
EOF

echo -e "${BLUE}Secret Name:${NC} AZURE_API_FUNCTIONAPP_PUBLISH_PROFILE"
echo -e "${BLUE}Secret Value:${NC} (Saved to secrets file - see below)"
echo ""
echo -e "${BLUE}Secret Name:${NC} AZURE_WORKFLOWS_FUNCTIONAPP_PUBLISH_PROFILE"
echo -e "${BLUE}Secret Value:${NC} (Saved to secrets file - see below)"
echo ""
echo -e "${BLUE}Secret Name:${NC} AZURE_STATIC_WEB_APPS_API_TOKEN"
echo -e "${BLUE}Secret Value:${NC} ${SWA_DEPLOYMENT_TOKEN}"
echo ""

echo -e "${GREEN}✓ All secret values saved to: ${SECRETS_FILE}${NC}"
echo ""
echo -e "${YELLOW}To copy a secret value:${NC}"
echo -e "   cat ${SECRETS_FILE}"
echo ""
echo -e "${YELLOW}Step 3: After adding all secrets, push to 'main' branch to trigger deployment${NC}"
echo ""
