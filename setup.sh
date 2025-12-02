#!/bin/bash
# Bifrost Setup Script
# Generates .env file with secure random secrets

set -e

ENV_FILE=".env"
ENV_EXAMPLE=".env.example"

echo "Bifrost Setup"
echo "============="
echo ""

# Check if .env already exists
if [ -f "$ENV_FILE" ]; then
    read -p ".env already exists. Overwrite? (y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "Setup cancelled."
        exit 0
    fi
fi

# Check if .env.example exists
if [ ! -f "$ENV_EXAMPLE" ]; then
    echo "Error: $ENV_EXAMPLE not found"
    exit 1
fi

# Copy example
cp "$ENV_EXAMPLE" "$ENV_FILE"

# Generate secure random values (alphanumeric only for compatibility)
POSTGRES_PASS=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)
RABBITMQ_PASS=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)
SECRET_KEY=$(openssl rand -base64 48 | tr -dc 'a-zA-Z0-9' | head -c 48)

# Replace in .env (sed -i.bak works on both Linux and macOS)
sed -i.bak "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$POSTGRES_PASS/" "$ENV_FILE"
sed -i.bak "s/RABBITMQ_PASSWORD=.*/RABBITMQ_PASSWORD=$RABBITMQ_PASS/" "$ENV_FILE"
sed -i.bak "s/BIFROST_SECRET_KEY=.*/BIFROST_SECRET_KEY=$SECRET_KEY/" "$ENV_FILE"
rm -f "$ENV_FILE.bak"

echo "✓ Created .env with secure secrets"
echo ""
echo "Generated:"
echo "  - POSTGRES_PASSWORD (24 chars)"
echo "  - RABBITMQ_PASSWORD (24 chars)"
echo "  - BIFROST_SECRET_KEY (48 chars)"
echo ""
echo "Next steps:"
echo "  docker compose up"
echo ""
echo "Access the platform at http://localhost:3000"
