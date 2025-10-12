#!/bin/bash

# Seed Azurite with sample data for local development
# Run this after starting Azurite and initializing tables

echo "Seeding local development data..."
echo "=================================="
echo ""

# Navigate to api directory and run seed script
cd "$(dirname "$0")/../../api" || exit 1

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating Python virtual environment..."
    source .venv/bin/activate
fi

# Run seed script
python3 seed_data.py "UseDevelopmentStorage=true"

RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo ""
    echo "✅ Sample data seeded successfully!"
    echo ""
    echo "Test users (use email as User ID when logging into SWA CLI):"
    echo "  Platform Admin:"
    echo "    - User ID: jack@gocovi.com"
    echo "    - Email: jack@gocovi.com"
    echo "    - Display Name: Jack Musick"
    echo "    - Type: PLATFORM"
    echo "    - Is Platform Admin: true"
    echo ""
    echo "  Organization User:"
    echo "    - User ID: jack@gocovi.dev"
    echo "    - Email: jack@gocovi.dev"
    echo "    - Display Name: Jack Musick"
    echo "    - Type: ORG"
    echo "    - Permissions: Can execute workflows, view history (cannot manage forms/config)"
    echo ""
    echo "Sample organization:"
    echo "  - Covi Development (org-acme-123)"
else
    echo ""
    echo "❌ Failed to seed data. Check logs above."
    exit 1
fi
