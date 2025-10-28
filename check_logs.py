#!/usr/bin/env python3
"""Check ExecutionLogs table contents"""
import asyncio
import os
import json
from shared.async_storage import AsyncTableStorageService

# Load settings from local.settings.json
with open('local.settings.json') as f:
    settings = json.load(f)
    for key, value in settings['Values'].items():
        os.environ[key] = value

async def check_logs():
    logs_service = AsyncTableStorageService('ExecutionLogs')

    try:
        # Query all logs
        query = "PartitionKey ne ''"
        results = await logs_service.query_entities(query)
        print(f'ExecutionLogs table has {len(results)} entries')

        if results:
            print('\nSample log entries:')
            for log in results[:10]:
                exec_id = log.get('PartitionKey', 'N/A')
                row_key = log.get('RowKey', 'N/A')
                message = log.get('Message', 'N/A')
                level = log.get('Level', 'N/A')
                print(f"  [{level}] {exec_id[:8]}... @ {row_key}: {message[:80]}")
        else:
            print('\nNo log entries found in ExecutionLogs table.')

        # Check recent executions
        exec_service = AsyncTableStorageService('Entities')
        exec_query = "PartitionKey eq 'WorkflowExecution'"
        exec_results = await exec_service.query_entities(exec_query)

        sorted_execs = sorted(
            exec_results,
            key=lambda x: x.get('StartedAt', ''),
            reverse=True
        )

        print(f'\n\nFound {len(exec_results)} total executions')
        print('Most recent 5 executions:')
        for ex in sorted_execs[:5]:
            exec_id = ex.get('RowKey', 'N/A')
            workflow = ex.get('WorkflowName', 'N/A')
            started = ex.get('StartedAt', 'N/A')
            status = ex.get('Status', 'N/A')
            print(f"  - {exec_id[:12]}... {workflow} @ {started} [{status}]")

    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(check_logs())
