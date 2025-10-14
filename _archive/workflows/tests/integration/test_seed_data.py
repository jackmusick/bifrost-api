"""
Integration Test: Azurite Seed Data (T040)

Tests the seed_azurite.py script that populates local Azurite storage with:
- Test organizations (2-3 orgs: active/inactive)
- Test users (3-5 users: PlatformAdmin, OrgUser roles)
- Test configurations (5-10 config entries: global + org-specific)

Verifies idempotent upsert pattern and <5s execution time.
"""

import pytest
import os
import time
from datetime import datetime, timezone
from azure.data.tables import TableServiceClient
from azure.core.exceptions import ResourceNotFoundError


@pytest.mark.integration
class TestAzuriteSeedData:
    """Test Azurite seed script functionality"""

    @pytest.fixture
    def table_service_client(self):
        """Create TableServiceClient for Azurite"""
        connection_string = os.environ.get(
            "AzureWebJobsStorage",
            "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
            "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
            "TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
        )
        return TableServiceClient.from_connection_string(connection_string)

    @pytest.fixture
    def cleanup_tables(self, table_service_client):
        """Clean up test tables before and after test"""
        tables_to_clean = ["Organizations", "Users", "Configuration"]

        # Clean before test
        for table_name in tables_to_clean:
            try:
                table_client = table_service_client.get_table_client(
                    table_name)
                # Delete all entities
                entities = table_client.list_entities()
                for entity in entities:
                    table_client.delete_entity(
                        partition_key=entity['PartitionKey'],
                        row_key=entity['RowKey']
                    )
            except ResourceNotFoundError:
                pass  # Table doesn't exist yet

        yield

        # Clean after test (optional - seed script is idempotent)

    @pytest.mark.asyncio
    async def test_seed_script_creates_organizations(
        self, table_service_client, cleanup_tables
    ):
        """
        Test that seed script creates 2-3 test organizations

        Should create orgs with varying states (active/inactive).
        """
        from scripts.seed_azurite import seed_organizations

        # Run seed function
        await seed_organizations(table_service_client)

        # Verify organizations created
        org_table = table_service_client.get_table_client("Organizations")
        orgs = list(org_table.query_entities("PartitionKey eq 'ORG'"))

        # Assert 2-3 organizations created
        assert len(orgs) >= 2
        assert len(orgs) <= 3

        # Assert at least one active and one inactive
        active_orgs = [org for org in orgs if org.get('IsActive', False)]
        inactive_orgs = [org for org in orgs if not org.get('IsActive', False)]

        assert len(active_orgs) >= 1, "Should have at least one active org"
        assert len(inactive_orgs) >= 1, "Should have at least one inactive org"

        # Assert required fields present
        for org in orgs:
            assert 'Name' in org
            assert 'TenantId' in org
            'IsActive' in org
            assert org['PartitionKey'] == 'ORG'

    @pytest.mark.asyncio
    async def test_seed_script_creates_users(
        self, table_service_client, cleanup_tables
    ):
        """
        Test that seed script creates 3-5 test users

        Should create users with different roles (PlatformAdmin, OrgUser).
        """
        from scripts.seed_azurite import seed_users

        # Seed organizations first (users reference orgs)
        from scripts.seed_azurite import seed_organizations
        await seed_organizations(table_service_client)

        # Run user seed function
        await seed_users(table_service_client)

        # Verify users created
        user_table = table_service_client.get_table_client("Users")
        users = list(user_table.query_entities("PartitionKey eq 'USER'"))

        # Assert 3-5 users created
        assert len(users) >= 3
        assert len(users) <= 5

        # Assert different roles present
        platform_admins = [
            u for u in users if 'PlatformAdmin' in u.get('Roles', [])]
        org_users = [u for u in users if 'OrgUser' in u.get('Roles', [])]

        assert len(platform_admins) >= 1, "Should have at least one PlatformAdmin"
        assert len(org_users) >= 1, "Should have at least one OrgUser"

        # Assert required fields present
        for user in users:
            assert 'Email' in user
            assert 'DisplayName' in user
            assert 'Roles' in user
            assert 'OrgId' in user  # Users belong to orgs
            assert user['PartitionKey'] == 'USER'

    @pytest.mark.asyncio
    async def test_seed_script_creates_configuration(
        self, table_service_client, cleanup_tables
    ):
        """
        Test that seed script creates 5-10 configuration entries

        Should create both global and org-specific config.
        """
        from scripts.seed_azurite import seed_configuration

        # Seed organizations first (config references orgs)
        from scripts.seed_azurite import seed_organizations
        await seed_organizations(table_service_client)

        # Run configuration seed function
        await seed_configuration(table_service_client)

        # Verify configuration created
        config_table = table_service_client.get_table_client("Configuration")
        configs = list(config_table.list_entities())

        # Assert 5-10 config entries created
        assert len(configs) >= 5
        assert len(configs) <= 10

        # Assert both global and org-specific config present
        global_configs = [c for c in configs if c['PartitionKey'] == 'GLOBAL']
        org_configs = [c for c in configs if c['PartitionKey'] != 'GLOBAL']

        assert len(global_configs) >= 1, "Should have global config"
        assert len(org_configs) >= 1, "Should have org-specific config"

        # Assert required fields present
        for config in configs:
            assert 'RowKey' in config
            assert config['RowKey'].startswith('config:')
            assert 'Value' in config
            assert 'Type' in config  # string, json, int, etc.

    @pytest.mark.asyncio
    async def test_seed_script_is_idempotent(
        self, table_service_client, cleanup_tables
    ):
        """
        Test that seed script can be run multiple times safely

        Should use upsert pattern - running twice should not duplicate entities.
        """
        from scripts.seed_azurite import seed_all

        # Run seed script first time
        await seed_all(table_service_client)

        # Count entities
        org_table = table_service_client.get_table_client("Organizations")
        orgs_first = list(org_table.query_entities("PartitionKey eq 'ORG'"))
        first_count = len(orgs_first)

        # Run seed script second time
        await seed_all(table_service_client)

        # Count entities again
        orgs_second = list(org_table.query_entities("PartitionKey eq 'ORG'"))
        second_count = len(orgs_second)

        # Assert no duplicates
        assert first_count == second_count, "Seed script should be idempotent"

        # Assert entities were updated (not duplicated)
        assert first_count > 0, "Should have seeded some orgs"

    @pytest.mark.asyncio
    async def test_seed_script_execution_time(
        self, table_service_client, cleanup_tables
    ):
        """
        Test that seed script completes in <5 seconds

        Performance requirement for fast local development setup.
        """
        from scripts.seed_azurite import seed_all

        # Measure execution time
        start_time = time.time()
        await seed_all(table_service_client)
        elapsed_time = time.time() - start_time

        # Assert <5 second execution
        assert elapsed_time < 5.0, f"Seed script took {elapsed_time:.2f}s (target: <5s)"

    @pytest.mark.asyncio
    async def test_seeded_orgs_have_valid_structure(
        self, table_service_client, cleanup_tables
    ):
        """
        Test that seeded organizations have correct schema

        Verifies all required fields and data types.
        """
        from scripts.seed_azurite import seed_organizations

        await seed_organizations(table_service_client)

        org_table = table_service_client.get_table_client("Organizations")
        orgs = list(org_table.query_entities("PartitionKey eq 'ORG'"))

        for org in orgs:
            # Assert partition/row keys
            assert org['PartitionKey'] == 'ORG'
            # UUIDs are used now, not test-org- prefixes

            # Assert required fields and types
            assert isinstance(org['Name'], str)
            assert len(org['Name']) > 0
            assert isinstance(org['TenantId'], str)
            assert isinstance(org['IsActive'], bool)

            # Assert timestamps
            assert 'CreatedAt' in org
            assert 'UpdatedAt' in org
            # Note: Azure Tables' 'Timestamp' field is automatically added by the service
            # but may not appear in the entity dict immediately after insert

    @pytest.mark.asyncio
    async def test_seeded_users_belong_to_seeded_orgs(
        self, table_service_client, cleanup_tables
    ):
        """
        Test referential integrity: users reference valid organizations

        All seeded users should have OrgId matching a seeded organization.
        """
        from scripts.seed_azurite import seed_organizations, seed_users

        # Seed orgs and users
        await seed_organizations(table_service_client)
        await seed_users(table_service_client)

        # Get all org IDs
        org_table = table_service_client.get_table_client("Organizations")
        orgs = list(org_table.query_entities("PartitionKey eq 'ORG'"))
        org_ids = {org['RowKey'] for org in orgs}

        # Get all users
        user_table = table_service_client.get_table_client("Users")
        users = list(user_table.query_entities("PartitionKey eq 'USER'"))

        # Assert all users belong to valid orgs
        for user in users:
            assert user['OrgId'] in org_ids, \
                f"User {user['RowKey']} references invalid org {user['OrgId']}"

    @pytest.mark.asyncio
    async def test_seed_script_cli_entry_point(self, cleanup_tables):
        """
        Test that seed script can be run from command line

        Verifies scripts/seed_azurite.py main() function works.
        """
        import subprocess
        import sys

        # Run seed script as subprocess
        result = subprocess.run(
            [sys.executable, "scripts/seed_azurite.py"],
            cwd="/Users/jack/GitHub/bifrost-integrations/workflows",
            capture_output=True,
            text=True,
            timeout=10
        )

        # Assert script succeeded
        assert result.returncode == 0, f"Seed script failed: {result.stderr}"

        # Assert informative output
        assert "Seeding" in result.stdout or "completed" in result.stdout.lower()
