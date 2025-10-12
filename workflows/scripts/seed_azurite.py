#!/usr/bin/env python3
"""
Azurite Seed Script (T042-T047)

Populates local Azurite Table Storage with test data for local development:
- Organizations (2-3 test orgs: active/inactive)
- Users (3-5 users: PlatformAdmin, OrgUser roles)
- Configuration (5-10 config entries: global + org-specific)

Features:
- Idempotent upsert pattern (can run multiple times safely)
- Execution time reporting (<5s target)
- Clear console output

Usage:
    python scripts/seed_azurite.py
"""

import asyncio
import os
import sys
import time
from datetime import datetime, timezone
from typing import List, Dict, Any

from azure.data.tables import TableServiceClient
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError


# ANSI color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(message: str) -> None:
    """Print colored header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{message}{Colors.RESET}")


def print_success(message: str) -> None:
    """Print success message"""
    print(f"{Colors.GREEN}✓{Colors.RESET} {message}")


def print_info(message: str) -> None:
    """Print info message"""
    print(f"{Colors.YELLOW}→{Colors.RESET} {message}")


def print_error(message: str) -> None:
    """Print error message"""
    print(f"{Colors.RED}✗{Colors.RESET} {message}")


# T043: Organization test data
SEED_ORGANIZATIONS = [
    {
        'PartitionKey': 'org',
        'RowKey': 'test-org-active',
        'Name': 'Active Test Organization',
        'TenantId': 'tenant-active-123',
        'IsActive': True
    },
    {
        'PartitionKey': 'org',
        'RowKey': 'test-org-inactive',
        'Name': 'Inactive Test Organization',
        'TenantId': 'tenant-inactive-456',
        'IsActive': False
    },
    {
        'PartitionKey': 'org',
        'RowKey': 'test-org-demo',
        'Name': 'Demo Organization',
        'TenantId': 'tenant-demo-789',
        'IsActive': True
    }
]


# T044: User test data
SEED_USERS = [
    {
        'PartitionKey': 'user',
        'RowKey': 'user-platform-admin',
        'Email': 'admin@platform.local',
        'Name': 'Platform Administrator',
        'Roles': ['PlatformAdmin'],
        'OrgId': 'test-org-active'  # PlatformAdmin belongs to active org
    },
    {
        'PartitionKey': 'user',
        'RowKey': 'user-org-user-1',
        'Email': 'user1@testorg.local',
        'Name': 'Test User 1',
        'Roles': ['OrgUser'],
        'OrgId': 'test-org-active'
    },
    {
        'PartitionKey': 'user',
        'RowKey': 'user-org-user-2',
        'Email': 'user2@testorg.local',
        'Name': 'Test User 2',
        'Roles': ['OrgUser'],
        'OrgId': 'test-org-active'
    },
    {
        'PartitionKey': 'user',
        'RowKey': 'user-demo-admin',
        'Email': 'admin@demo.local',
        'Name': 'Demo Admin',
        'Roles': ['OrgUser', 'OrgAdmin'],
        'OrgId': 'test-org-demo'
    },
    {
        'PartitionKey': 'user',
        'RowKey': 'user-inactive-org',
        'Email': 'user@inactive.local',
        'Name': 'Inactive Org User',
        'Roles': ['OrgUser'],
        'OrgId': 'test-org-inactive'
    }
]


# T045: Configuration test data (global + org-specific)
SEED_CONFIGURATION = [
    # Global configuration
    {
        'PartitionKey': 'global',
        'RowKey': 'config:platform_name',
        'Value': 'Bifrost Integrations',
        'Type': 'string'
    },
    {
        'PartitionKey': 'global',
        'RowKey': 'config:max_workflow_timeout',
        'Value': '300',
        'Type': 'int'
    },
    {
        'PartitionKey': 'global',
        'RowKey': 'config:feature_flags',
        'Value': '{"webhooks": true, "analytics": false, "beta_features": true}',
        'Type': 'json'
    },

    # Org-specific configuration (test-org-active)
    {
        'PartitionKey': 'test-org-active',
        'RowKey': 'config:api_endpoint',
        'Value': 'https://api.testorg.local',
        'Type': 'string'
    },
    {
        'PartitionKey': 'test-org-active',
        'RowKey': 'config:automation_enabled',
        'Value': 'true',
        'Type': 'bool'
    },
    {
        'PartitionKey': 'test-org-active',
        'RowKey': 'config:integrations',
        'Value': '{"slack": true, "teams": true, "email": true}',
        'Type': 'json'
    },

    # Org-specific configuration (test-org-demo)
    {
        'PartitionKey': 'test-org-demo',
        'RowKey': 'config:api_endpoint',
        'Value': 'https://api.demo.local',
        'Type': 'string'
    },
    {
        'PartitionKey': 'test-org-demo',
        'RowKey': 'config:demo_mode',
        'Value': 'true',
        'Type': 'bool'
    },
    {
        'PartitionKey': 'test-org-demo',
        'RowKey': 'config:rate_limits',
        'Value': '{"requests_per_hour": 100, "workflows_per_day": 50}',
        'Type': 'json'
    },

    # Org-specific configuration (test-org-inactive)
    {
        'PartitionKey': 'test-org-inactive',
        'RowKey': 'config:api_endpoint',
        'Value': 'https://api.inactive.local',
        'Type': 'string'
    }
]


async def ensure_table_exists(
    service_client: TableServiceClient,
    table_name: str
) -> None:
    """
    Ensure table exists, create if not.

    Args:
        service_client: Azure Table Storage service client
        table_name: Name of table to create
    """
    try:
        service_client.create_table(table_name)
        print_info(f"Created table: {table_name}")
    except ResourceExistsError:
        print_info(f"Table already exists: {table_name}")


async def seed_organizations(service_client: TableServiceClient) -> int:
    """
    T043: Seed test organizations (2-3 orgs: active/inactive)

    Args:
        service_client: Azure Table Storage service client

    Returns:
        Number of organizations seeded
    """
    print_header("Seeding Organizations")

    await ensure_table_exists(service_client, "Organizations")
    table_client = service_client.get_table_client("Organizations")

    count = 0
    for org_data in SEED_ORGANIZATIONS:
        # T046: Idempotent upsert pattern
        table_client.upsert_entity(org_data)

        status = "active" if org_data['IsActive'] else "inactive"
        print_success(
            f"  {org_data['Name']} ({org_data['RowKey']}) - {status}")
        count += 1

    return count


async def seed_users(service_client: TableServiceClient) -> int:
    """
    T044: Seed test users (3-5 users: PlatformAdmin, OrgUser roles)

    Args:
        service_client: Azure Table Storage service client

    Returns:
        Number of users seeded
    """
    print_header("Seeding Users")

    await ensure_table_exists(service_client, "Users")
    table_client = service_client.get_table_client("Users")

    count = 0
    for user_data in SEED_USERS:
        # T046: Idempotent upsert pattern
        # Note: Roles need to be JSON-serialized for Table Storage
        import json
        entity = user_data.copy()
        entity['Roles'] = json.dumps(user_data['Roles'])

        table_client.upsert_entity(entity)

        roles_str = ", ".join(user_data['Roles'])
        print_success(
            f"  {user_data['Name']} ({user_data['Email']}) - {roles_str}")
        count += 1

    return count


async def seed_configuration(service_client: TableServiceClient) -> int:
    """
    T045: Seed configuration entries (5-10 entries: global + org-specific)

    Args:
        service_client: Azure Table Storage service client

    Returns:
        Number of configuration entries seeded
    """
    print_header("Seeding Configuration")

    await ensure_table_exists(service_client, "Configuration")
    table_client = service_client.get_table_client("Configuration")

    count = 0
    for config_data in SEED_CONFIGURATION:
        # T046: Idempotent upsert pattern
        table_client.upsert_entity(config_data)

        scope = "global" if config_data['PartitionKey'] == 'global' else config_data['PartitionKey']
        key = config_data['RowKey'].replace('config:', '')
        print_success(f"  [{scope}] {key} = {config_data['Value'][:50]}...")
        count += 1

    return count


async def seed_all(service_client: TableServiceClient) -> Dict[str, int]:
    """
    Seed all test data (organizations, users, configuration)

    Args:
        service_client: Azure Table Storage service client

    Returns:
        Dictionary with counts: {'orgs': N, 'users': N, 'configs': N}
    """
    org_count = await seed_organizations(service_client)
    user_count = await seed_users(service_client)
    config_count = await seed_configuration(service_client)

    return {
        'organizations': org_count,
        'users': user_count,
        'configurations': config_count
    }


def get_connection_string() -> str:
    """
    Get Azurite connection string from environment or use default

    Returns:
        Azure Storage connection string
    """
    return os.environ.get(
        "TABLE_STORAGE_CONNECTION_STRING",
        # Default Azurite connection string
        "DefaultEndpointsProtocol=http;"
        "AccountName=devstoreaccount1;"
        "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
        "TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
    )


async def main() -> int:
    """
    Main entry point for seed script

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    print_header("═" * 60)
    print_header("Azurite Seed Script - Local Development Data")
    print_header("═" * 60)

    # T047: Execution time reporting
    start_time = time.time()

    try:
        # Get connection string
        connection_string = get_connection_string()
        print_info(f"Connecting to Azurite...")

        # Create service client
        service_client = TableServiceClient.from_connection_string(
            connection_string)

        # Seed all data
        counts = await seed_all(service_client)

        # Calculate elapsed time
        elapsed_time = time.time() - start_time

        # Print summary
        print_header("\n" + "═" * 60)
        print_header("Seeding Complete!")
        print_header("═" * 60)
        print_success(f"Organizations: {counts['organizations']}")
        print_success(f"Users: {counts['users']}")
        print_success(f"Configurations: {counts['configurations']}")
        print_info(f"\nExecution time: {elapsed_time:.2f}s (target: <5s)")

        # Warn if execution took too long
        if elapsed_time >= 5.0:
            print_error(f"⚠ Execution time exceeded 5s target!")

        print_header("\n✓ Ready for local development!")
        print_info("Start Azure Functions: func start")
        print_info("Test endpoint: curl http://localhost:7072/api/health\n")

        return 0

    except Exception as e:
        print_error(f"\nSeeding failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    # Run async main
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
