#!/usr/bin/env python3
"""Check all table contents"""
import asyncio
import json
from azure.data.tables import TableServiceClient

# Load settings
with open('local.settings.json') as f:
    settings = json.load(f)
    conn_str = settings['Values']['AzureWebJobsStorage']

async def check_tables():
    table_service = TableServiceClient.from_connection_string(conn_str)

    # List all tables
    tables = list(table_service.list_tables())
    print(f"Found {len(tables)} tables:")
    for table in tables:
        print(f"  - {table.name}")

    print("\n" + "="*80 + "\n")

    # Check each table for entities
    for table in tables:
        table_client = table_service.get_table_client(table.name)
        try:
            entities = list(table_client.list_entities())
            print(f"{table.name}: {len(entities)} entities")

            if entities and len(entities) > 0:
                # Show first few entities
                print("  Sample entities:")
                for entity in entities[:3]:
                    pk = entity.get('PartitionKey', 'N/A')
                    rk = entity.get('RowKey', 'N/A')
                    print(f"    {pk} / {rk}")

        except Exception as e:
            print(f"{table.name}: Error - {e}")

if __name__ == '__main__':
    asyncio.run(check_tables())
