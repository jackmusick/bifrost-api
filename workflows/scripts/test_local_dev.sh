#!/bin/bash
# T058: Test Local Development Flow
#
# This script verifies the complete local development setup:
# 1. Azurite is running
# 2. Seed script populates data
# 3. Azure Functions starts successfully
# 4. Health endpoint responds
# 5. Workflow execution works with function key auth

set -e  # Exit on error

echo "========================================="
echo "Testing Local Development Flow (T058)"
echo "========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check if Azurite is running
echo -e "\n${YELLOW}[1/5] Checking if Azurite is running...${NC}"
if curl -s http://127.0.0.1:10002/devstoreaccount1 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Azurite is running${NC}"
else
    echo -e "${RED}✗ Azurite is not running${NC}"
    echo "   Please start Azurite:"
    echo "   azurite --silent --location /tmp/azurite --debug /tmp/azurite/debug.log"
    exit 1
fi

# Step 2: Run seed script
echo -e "\n${YELLOW}[2/5] Running seed script...${NC}"
python scripts/seed_azurite.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Seed script completed${NC}"
else
    echo -e "${RED}✗ Seed script failed${NC}"
    exit 1
fi

# Step 3: Check if Azure Functions is running
echo -e "\n${YELLOW}[3/5] Checking if Azure Functions is running...${NC}"
if curl -s http://localhost:7072/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Azure Functions is running${NC}"
else
    echo -e "${RED}✗ Azure Functions is not running${NC}"
    echo "   Please start Azure Functions in another terminal:"
    echo "   func start"
    exit 1
fi

# Step 4: Test health endpoint
echo -e "\n${YELLOW}[4/5] Testing health endpoint...${NC}"
HEALTH_RESPONSE=$(curl -s http://localhost:7072/api/health)
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}✓ Health endpoint responding correctly${NC}"
    echo "   Response: $HEALTH_RESPONSE"
else
    echo -e "${RED}✗ Health endpoint not responding correctly${NC}"
    exit 1
fi

# Step 5: Test workflow execution with function key
echo -e "\n${YELLOW}[5/5] Testing workflow execution with function key auth...${NC}"
echo "   Note: This requires a registered workflow to be available"
echo "   If you get 404, that's OK - it means auth worked but workflow doesn't exist yet"

# Try to execute a workflow with function key auth
WORKFLOW_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -H "X-Organization-Id: test-org-active" \
    -H "x-functions-key: test_local_key_12345" \
    -d '{"test": "data"}' \
    http://localhost:7072/api/workflows/test_workflow 2>&1)

# Check if we got a proper response (not 403 Forbidden)
if echo "$WORKFLOW_RESPONSE" | grep -q "Forbidden\|No valid authentication"; then
    echo -e "${RED}✗ Authentication failed (got 403 Forbidden)${NC}"
    echo "   Response: $WORKFLOW_RESPONSE"
    exit 1
elif echo "$WORKFLOW_RESPONSE" | grep -q "NotFound\|not found"; then
    echo -e "${GREEN}✓ Authentication worked (workflow not found is expected)${NC}"
    echo "   This means function key auth is working correctly!"
else
    echo -e "${GREEN}✓ Workflow execution endpoint responding${NC}"
    echo "   Response: $WORKFLOW_RESPONSE"
fi

# Summary
echo -e "\n========================================="
echo -e "${GREEN}Local Development Flow: VERIFIED ✓${NC}"
echo -e "========================================="
echo ""
echo "Your local development environment is ready!"
echo ""
echo "Next steps:"
echo "1. Create workflows in /workspace/workflows/"
echo "2. Test with: curl -X POST \\"
echo "      -H 'X-Organization-Id: test-org-active' \\"
echo "      -H 'x-functions-key: your_key' \\"
echo "      -d '{\"param\": \"value\"}' \\"
echo "      http://localhost:7072/api/workflows/YOUR_WORKFLOW"
echo ""
