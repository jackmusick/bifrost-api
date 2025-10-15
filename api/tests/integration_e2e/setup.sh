#!/bin/bash
set -e

echo "🚀 Setting up E2E Integration Tests"
echo "===================================="
echo ""

# Check if docker-compose is running
echo "1️⃣  Checking if services are running..."
if ! docker ps | grep -q bifrost-integrations-azurite; then
    echo "   Starting docker-compose services..."
    cd /Users/jack/GitHub/bifrost-integrations
    docker-compose up -d
    echo "   ✓ Services started"
    echo "   ⏳ Waiting 5 seconds for services to initialize..."
    sleep 5
else
    echo "   ✓ Services already running"
fi

echo ""
echo "2️⃣  Setting environment variables..."
export AzureWebJobsStorage="UseDevelopmentStorage=true"
export AZURE_KEY_VAULT_URL="http://localhost:8200"

echo ""
echo "3️⃣  Initializing tables..."
cd /Users/jack/GitHub/bifrost-integrations/api
python shared/init_tables.py

echo ""
echo "4️⃣  Seeding test data..."
python seed_data.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "You can now run the tests with:"
echo "  pytest tests/integration_e2e/ -v"
echo ""
echo "Or run a specific test:"
echo "  pytest tests/integration_e2e/test_organizations_e2e.py::TestOrganizationsE2E::test_list_organizations_as_platform_admin -v"
