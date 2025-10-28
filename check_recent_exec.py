#!/usr/bin/env python3
"""Check most recent execution"""
import asyncio
import os
import json
from shared.async_storage import AsyncTableStorageService

# Load settings
with open('local.settings.json') as f:
    settings = json.load(f)
    for key, value in settings['Values'].items():
        os.environ[key] = value

async def check_recent():
    exec_service = AsyncTableStorageService('Entities')

    # Get WorkflowExecution entities
    query = "PartitionKey eq 'WorkflowExecution'"
    results = await exec_service.query_entities(query)

    if not results:
        print("No WorkflowExecution entities found")
        return

    # Sort by StartedAt descending
    sorted_execs = sorted(
        results,
        key=lambda x: x.get('StartedAt', ''),
        reverse=True
    )

    print(f"Found {len(sorted_execs)} executions")
    print("\nMost recent execution:")

    latest = sorted_execs[0]
    for key, value in latest.items():
        if not key.startswith('odata') and not key.startswith('_'):
            print(f"  {key}: {value}")

if __name__ == '__main__':
    asyncio.run(check_recent())
