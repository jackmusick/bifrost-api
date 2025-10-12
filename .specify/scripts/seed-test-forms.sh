#!/bin/bash

# Seed Test Forms for Workflow Testing
# Creates forms for simple_greeting and queue_processor workflows

set -e

echo "🌱 Seeding test forms for workflow testing..."

# Check if Azurite is running
if ! curl -s http://127.0.0.1:10002/devstoreaccount1?comp=list > /dev/null 2>&1; then
    echo "❌ Azurite is not running. Please start Azurite first:"
    echo "   ./.specify/scripts/start-azurite.sh"
    exit 1
fi

cd "$(dirname "$0")/../.."

# Activate virtual environment if needed
if [ -d "api/venv" ]; then
    source api/venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run Python script to seed forms
python3 - <<'EOF'
import asyncio
from azure.data.tables.aio import TableServiceClient
from datetime import datetime
import uuid
import json

STORAGE_CONN_STR = "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM52j/1EW3LhqZM3j4qLlzlLlzqLqLqLqLqLqLqLqLqLqLqLqLqLqLqLqLqLqLqLqLqLqLqLqLqLqLqLqLqLqL==;TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"

async def seed_forms():
    """Seed test forms for workflows"""

    service_client = TableServiceClient.from_connection_string(STORAGE_CONN_STR)
    forms_table = service_client.get_table_client("Forms")

    # Create Forms table if it doesn't exist
    try:
        await forms_table.create_table()
        print("✅ Created Forms table")
    except Exception:
        print("ℹ️  Forms table already exists")

    # Mock MSP admin user
    admin_user_id = "admin-001"
    org_id = "msp-org-001"

    # Form 1: Simple Greeting (instant response)
    form1_id = str(uuid.uuid4())
    form1 = {
        "PartitionKey": org_id,
        "RowKey": form1_id,
        "id": form1_id,
        "orgId": org_id,
        "name": "Simple Greeting",
        "description": "Test workflow with instant response - perfect for testing form submission",
        "linkedWorkflow": "simple_greeting",
        "formSchema": json.dumps({
            "fields": [
                {
                    "name": "name",
                    "label": "Your Name",
                    "type": "text",
                    "required": True,
                    "placeholder": "Enter your name",
                    "helpText": "Enter your name to receive a personalized greeting"
                },
                {
                    "name": "greeting_type",
                    "label": "Greeting Type",
                    "type": "text",
                    "required": False,
                    "placeholder": "Hello",
                    "defaultValue": "Hello",
                    "helpText": "Type of greeting (Hello, Hi, Welcome, etc.)"
                },
                {
                    "name": "include_time",
                    "label": "Include Timestamp",
                    "type": "checkbox",
                    "required": False,
                    "defaultValue": False,
                    "helpText": "Include current date/time in the greeting"
                }
            ]
        }),
        "isActive": True,
        "isGlobal": True,
        "createdBy": admin_user_id,
        "createdAt": datetime.utcnow().isoformat(),
        "updatedAt": datetime.utcnow().isoformat()
    }

    # Form 2: Queue Processor (delayed response)
    form2_id = str(uuid.uuid4())
    form2 = {
        "PartitionKey": org_id,
        "RowKey": form2_id,
        "id": form2_id,
        "orgId": org_id,
        "name": "Queue Processor",
        "description": "Test workflow with delayed response - perfect for testing async execution tracking",
        "linkedWorkflow": "queue_processor",
        "formSchema": json.dumps({
            "fields": [
                {
                    "name": "item_name",
                    "label": "Item Name",
                    "type": "text",
                    "required": True,
                    "placeholder": "e.g., Report Generation",
                    "helpText": "Name of the item to process"
                },
                {
                    "name": "priority",
                    "label": "Priority",
                    "type": "number",
                    "required": False,
                    "defaultValue": 5,
                    "placeholder": "1-10",
                    "helpText": "Processing priority (1-10, higher = more important)"
                },
                {
                    "name": "delay_seconds",
                    "label": "Processing Delay (seconds)",
                    "type": "number",
                    "required": False,
                    "defaultValue": 5,
                    "placeholder": "5",
                    "helpText": "Simulated processing time in seconds"
                },
                {
                    "name": "description",
                    "label": "Description",
                    "type": "textarea",
                    "required": False,
                    "placeholder": "Optional description...",
                    "helpText": "Optional description of the item"
                }
            ]
        }),
        "isActive": True,
        "isGlobal": True,
        "createdBy": admin_user_id,
        "createdAt": datetime.utcnow().isoformat(),
        "updatedAt": datetime.utcnow().isoformat()
    }

    # Insert forms
    try:
        await forms_table.upsert_entity(form1)
        print(f"✅ Created form: {form1['name']} (ID: {form1_id})")
    except Exception as e:
        print(f"❌ Failed to create Simple Greeting form: {e}")

    try:
        await forms_table.upsert_entity(form2)
        print(f"✅ Created form: {form2['name']} (ID: {form2_id})")
    except Exception as e:
        print(f"❌ Failed to create Queue Processor form: {e}")

    await service_client.close()
    print("\n🎉 Test forms seeded successfully!")
    print(f"\nYou can now test:")
    print(f"1. Navigate to /workflows to see available forms")
    print(f"2. Execute 'Simple Greeting' for instant response")
    print(f"3. Execute 'Queue Processor' for async tracking (5 second delay)")

# Run the async function
asyncio.run(seed_forms())
EOF

echo "✅ Done!"
