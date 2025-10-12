#!/bin/bash

# Start Azurite for local Azure Storage emulation
# This provides Table Storage, Blob Storage, and Queue Storage locally

AZURITE_DIR=~/azurite

# Create directory if it doesn't exist
mkdir -p "$AZURITE_DIR"

echo "Starting Azurite..."
echo "Storage location: $AZURITE_DIR"
echo "Debug log: $AZURITE_DIR/debug.log"
echo ""
echo "Table Storage:  http://127.0.0.1:10002"
echo "Blob Storage:   http://127.0.0.1:10000"
echo "Queue Storage:  http://127.0.0.1:10001"
echo ""

# Start Azurite in the background
azurite --silent --location "$AZURITE_DIR" --debug "$AZURITE_DIR/debug.log" &

# Get the PID
AZURITE_PID=$!
echo "Azurite started with PID: $AZURITE_PID"
echo "To stop: kill $AZURITE_PID"
echo ""
echo "Connection string for local.settings.json:"
echo "UseDevelopmentStorage=true"
