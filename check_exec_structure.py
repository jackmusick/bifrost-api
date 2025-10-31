#!/usr/bin/env python3
"""Check execution structure"""
import json
from azure.data.tables import TableServiceClient

# Load settings
with open('local.settings.json') as f:
    settings = json.load(f)
    conn_str = settings['Values']['AzureWebJobsStorage']

def check_execs():
    table_service = TableServiceClient.from_connection_string(conn_str)
    table_client = table_service.get_table_client('Entities')

    # Get entities with 'execution' in RowKey
    entities = list(table_client.query_entities("RowKey ge 'execution:'"))

    print(f"Found {len(entities)} entities with execution prefix")

    if entities:
        print("\nMost recent 3 executions:")
        # Sort by timestamp descending
        sorted_entities = sorted(
            entities,
            key=lambda x: x.get('Timestamp', x.get('StartedAt', '')),
            reverse=True
        )

        for entity in sorted_entities[:3]:
            pk = entity.get('PartitionKey', 'N/A')
            rk = entity.get('RowKey', 'N/A')
            started = entity.get('StartedAt', 'N/A')
            status = entity.get('Status', 'N/A')
            workflow = entity.get('WorkflowName', 'N/A')
            print(f"\nPartitionKey: {pk}")
            print(f"RowKey: {rk}")
            print(f"WorkflowName: {workflow}")
            print(f"StartedAt: {started}")
            print(f"Status: {status}")

if __name__ == '__main__':
    check_execs()
