"""
Seed data script for Bifrost Integrations local development
Populates Azurite with realistic sample data for testing
All data follows Pydantic models from shared/models.py
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta

from azure.data.tables import TableClient, TableServiceClient

logger = logging.getLogger(__name__)

# Use stable UUIDs for development (consistent across seed runs)
ORG_COVI_DEV_ID = str(uuid.uuid4())
FORM_GREETING_ID = str(uuid.uuid4())
FORM_ONBOARDING_ID = str(uuid.uuid4())
FORM_GITHUB_WORKFLOW_ID = str(uuid.uuid4())  # T042: Form with data provider inputs

logger.info("Seed data UUIDs:")
logger.info(f"  Org Covi Development: {ORG_COVI_DEV_ID}")
logger.info(f"  Form Simple Greeting: {FORM_GREETING_ID}")
logger.info(f"  Form User Onboarding: {FORM_ONBOARDING_ID}")
logger.info(f"  Form GitHub Workflow: {FORM_GITHUB_WORKFLOW_ID}")

# ==================== TABLE 1: CONFIG ====================

SAMPLE_CONFIG_ENTITIES = [
    # System config (GLOBAL partition)
    {
        "PartitionKey": "GLOBAL",
        "RowKey": "system:version",
        "Key": "version",
        "Value": "1.0.0",
        "Type": "string",
        "Scope": "GLOBAL",
        "Description": "Platform version",
        "UpdatedAt": datetime.utcnow().isoformat(),
        "UpdatedBy": "system",
    },
    {
        "PartitionKey": "GLOBAL",
        "RowKey": "system:maintenance_mode",
        "Key": "maintenance_mode",
        "Value": "false",
        "Type": "boolean",
        "Scope": "GLOBAL",
        "Description": "System maintenance mode flag",
        "UpdatedAt": datetime.utcnow().isoformat(),
        "UpdatedBy": "system",
    },
    # Org-specific config (matches Config model from models.py)
    {
        "PartitionKey": ORG_COVI_DEV_ID,
        "RowKey": "config:default_office_location",
        "Key": "default_office_location",
        "Value": "New York",
        "Type": "string",
        "Scope": ORG_COVI_DEV_ID,
        "Description": "Default office location for new users",
        "UpdatedAt": datetime.utcnow().isoformat(),
        "UpdatedBy": "jack@gocovi.dev",
    },
    {
        "PartitionKey": ORG_COVI_DEV_ID,
        "RowKey": "config:default_license_tier",
        "Key": "default_license_tier",
        "Value": "Microsoft 365 Business Standard",
        "Type": "string",
        "Scope": ORG_COVI_DEV_ID,
        "Description": "Default license for new users",
        "UpdatedAt": datetime.utcnow().isoformat(),
        "UpdatedBy": "jack@gocovi.dev",
    },
    {
        "PartitionKey": "6c600874-458f-462e-8a8d-3d71f7889beb",  # Contoso Ltd org ID
        "RowKey": "config:default_license_tier",
        "Key": "default_license_tier",
        "Value": "Microsoft 365 Business Premium",
        "Type": "string",
        "Scope": "6c600874-458f-462e-8a8d-3d71f7889beb",
        "Description": "Default license for new users",
        "UpdatedAt": datetime.utcnow().isoformat(),
        "UpdatedBy": "jack@gocovi.dev",
    },
    {
        "PartitionKey": "6c600874-458f-462e-8a8d-3d71f7889beb",  # Contoso Ltd org ID
        "RowKey": "config:default_office_location",
        "Key": "default_office_location",
        "Value": "Boston",
        "Type": "string",
        "Scope": "6c600874-458f-462e-8a8d-3d71f7889beb",
        "Description": "Default office location for new users",
        "UpdatedAt": datetime.utcnow().isoformat(),
        "UpdatedBy": "jack@gocovi.dev",
    },
]

# ==================== TABLE 2: ENTITIES ====================

SAMPLE_ENTITIES = [
    # Organizations (matches Organization model from models.py)
    {
        "PartitionKey": "GLOBAL",
        "RowKey": f"org:{ORG_COVI_DEV_ID}",
        "Name": "Covi Development",
        "Domain": "dev",
        "IsActive": True,
        "CreatedAt": (datetime.utcnow() - timedelta(days=90)).isoformat(),
        "CreatedBy": "jack@gocovi.com",
        "UpdatedAt": (datetime.utcnow() - timedelta(days=30)).isoformat(),
    },
    {
        "PartitionKey": "GLOBAL",
        "RowKey": f"org:{str(uuid.uuid4())}",
        "Name": "Contoso Ltd",
        "Domain": "contoso.com",
        "IsActive": True,
        "CreatedAt": (datetime.utcnow() - timedelta(days=60)).isoformat(),
        "CreatedBy": "jack@gocovi.com",
        "UpdatedAt": (datetime.utcnow() - timedelta(days=15)).isoformat(),
    },
    # Forms (matches Form model from models.py)
    # Global public form - anyone can see and execute
    {
        "PartitionKey": "GLOBAL",
        "RowKey": f"form:{FORM_GREETING_ID}",
        "Name": "Simple Greeting",
        "Description": "Generate a personalized greeting message (instant response)",
        "FormSchema": json.dumps({
            "fields": [
                {
                    "name": "name",
                    "label": "Your Name",
                    "type": "text",
                    "required": True,
                    "placeholder": "John",
                },
                {
                    "name": "greeting_type",
                    "label": "Greeting Type",
                    "type": "text",
                    "required": False,
                    "defaultValue": "Hello",
                },
                {
                    "name": "include_time",
                    "label": "Include Timestamp",
                    "type": "checkbox",
                    "required": False,
                    "defaultValue": False,
                },
            ]
        }),
        "LinkedWorkflow": "simple_greeting",
        "IsActive": True,
        "IsPublic": True,
        "CreatedBy": "jack@gocovi.com",
        "CreatedAt": (datetime.utcnow() - timedelta(days=5)).isoformat(),
        "UpdatedAt": datetime.utcnow().isoformat(),
    },
    # Org-scoped form - only visible to users in that org
    {
        "PartitionKey": ORG_COVI_DEV_ID,
        "RowKey": f"form:{FORM_ONBOARDING_ID}",
        "Name": "New User Onboarding",
        "Description": "Creates a new Microsoft 365 user with licenses",
        "FormSchema": json.dumps({
            "fields": [
                {
                    "name": "first_name",
                    "label": "First Name",
                    "type": "text",
                    "required": True,
                    "placeholder": "John",
                },
                {
                    "name": "last_name",
                    "label": "Last Name",
                    "type": "text",
                    "required": True,
                    "placeholder": "Doe",
                },
                {
                    "name": "email",
                    "label": "Email Address",
                    "type": "email",
                    "required": True,
                    "placeholder": "john.doe@gocovi.dev",
                },
            ]
        }),
        "LinkedWorkflow": "user_onboarding",
        "IsActive": True,
        "IsPublic": False,
        "CreatedBy": "jack@gocovi.dev",
        "CreatedAt": (datetime.utcnow() - timedelta(days=30)).isoformat(),
        "UpdatedAt": datetime.utcnow().isoformat(),
    },
    # T042: Form with static data provider inputs
    {
        "PartitionKey": "GLOBAL",
        "RowKey": f"form:{FORM_GITHUB_WORKFLOW_ID}",
        "Name": "GitHub Repository Workflow",
        "Description": "Create a workflow for a GitHub repository (demonstrates data provider inputs)",
        "FormSchema": json.dumps({
            "fields": [
                {
                    "name": "github_token",
                    "label": "GitHub Personal Access Token",
                    "type": "text",
                    "required": True,
                    "placeholder": "ghp_xxxxxxxxxxxx",
                    "helpText": "GitHub PAT with repo access"
                },
                {
                    "name": "repository",
                    "label": "Select Repository",
                    "type": "select",
                    "required": True,
                    "dataProvider": "get_github_repos",
                    "dataProviderInputs": {
                        "token": {
                            "mode": "static",
                            "value": "ghp_demo_token_for_testing_12345"
                        },
                        "org": {
                            "mode": "static",
                            "value": "gocovi"
                        }
                    }
                },
                {
                    "name": "branch",
                    "label": "Select Branch",
                    "type": "select",
                    "required": True,
                    "dataProvider": "get_github_branches",
                    "dataProviderInputs": {
                        "token": {
                            "mode": "static",
                            "value": "ghp_demo_token_for_testing_12345"
                        },
                        "repo": {
                            "mode": "static",
                            "value": "gocovi/bifrost-api"
                        }
                    }
                },
                {
                    "name": "workflow_name",
                    "label": "Workflow Name",
                    "type": "text",
                    "required": True,
                    "placeholder": "CI Pipeline"
                }
            ]
        }),
        "LinkedWorkflow": "create_github_workflow",
        "IsActive": True,
        "IsPublic": True,
        "CreatedBy": "jack@gocovi.com",
        "CreatedAt": (datetime.utcnow() - timedelta(days=2)).isoformat(),
        "UpdatedAt": datetime.utcnow().isoformat(),
    },
    # Users (from SAMPLE_USERS, now integrated into Entities)
    {
        "PartitionKey": "GLOBAL",
        "RowKey": "user:jack@gocovi.com",
        "Email": "jack@gocovi.com",
        "DisplayName": "Jack Musick",
        "UserType": "PLATFORM",
        "IsPlatformAdmin": True,
        "IsActive": True,
        "LastLogin": datetime.utcnow().isoformat(),
        "CreatedAt": (datetime.utcnow() - timedelta(days=100)).isoformat(),
        "EntraUserId": "00000000-0000-0000-0001-000000000001",
        "LastEntraIdSync": datetime.utcnow().isoformat(),
    },
    {
        "PartitionKey": "GLOBAL",
        "RowKey": "user:jack@gocovi.dev",
        "Email": "jack@gocovi.dev",
        "DisplayName": "Jack Musick",
        "UserType": "ORG",
        "IsPlatformAdmin": False,
        "IsActive": True,
        "LastLogin": datetime.utcnow().isoformat(),
        "CreatedAt": (datetime.utcnow() - timedelta(days=100)).isoformat(),
        "EntraUserId": "00000000-0000-0000-0002-000000000001",
        "LastEntraIdSync": datetime.utcnow().isoformat(),
    },
]


def generate_sample_executions():
    """Generate sample workflow executions with reverse timestamps"""
    entities_executions = []
    relationships_executions = []
    base_time = datetime.utcnow()

    for i in range(5):
        execution_time = base_time - timedelta(minutes=i * 30)
        reverse_ts = 9999999999999 - int(execution_time.timestamp() * 1000)
        exec_id = str(uuid.uuid4())

        status = "Success" if i % 2 == 0 else "Failed"
        workflow = "user_onboarding" if i % 2 == 0 else "simple_greeting"

        # Entities table (org-scoped execution)
        # Matches structure used by ExecutionLogger in shared/execution_logger.py
        execution_entity = {
            "PartitionKey": ORG_COVI_DEV_ID,
            "RowKey": f"execution:{reverse_ts}_{exec_id}",
            "ExecutionId": exec_id,
            "WorkflowName": workflow,
            "FormId": FORM_ONBOARDING_ID if workflow == "user_onboarding" else FORM_GREETING_ID,
            "ExecutedBy": "jack@gocovi.dev",
            "ExecutedByName": "Jack Musick",
            "Status": status,
            "InputData": json.dumps({
                "first_name": "Test",
                "last_name": f"User{i+1}",
                "email": f"test{i+1}@gocovi.dev",
            }) if workflow == "user_onboarding" else json.dumps({
                "name": f"Test User {i+1}",
                "greeting_type": "Hello",
                "include_time": True,
            }),
            "Result": json.dumps({"success": True, "message": f"Test result {i+1}"}) if status == "Success" else None,
            "ResultInBlob": False,
            "ErrorMessage": "Sample error for testing" if status == "Failed" else None,
            "ErrorType": "ValidationError" if status == "Failed" else None,
            "ErrorDetails": None,
            "DurationMs": 2000 + (i * 100),
            "StartedAt": execution_time.isoformat(),
            "CompletedAt": (execution_time + timedelta(seconds=2 + i * 0.1)).isoformat(),
            "IntegrationCalls": None,
            "Variables": None,
        }

        # Relationships table (user → execution dual index)
        user_exec_entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"userexec:jack@gocovi.dev:{exec_id}",
            "ExecutionId": exec_id,
            "UserId": "jack@gocovi.dev",
            "OrgId": ORG_COVI_DEV_ID,
            "WorkflowName": workflow,
            "Status": status,
            "StartedAt": execution_time.isoformat(),
        }

        entities_executions.append(execution_entity)
        relationships_executions.append(user_exec_entity)

    return entities_executions, relationships_executions


# ==================== TABLE 3: RELATIONSHIPS ====================

SAMPLE_RELATIONSHIPS = [
    # User-to-Org permissions (dual indexed)
    # This gives jack@gocovi.dev access to Covi Development org
    {
        "PartitionKey": "GLOBAL",
        "RowKey": f"userperm:jack@gocovi.dev:{ORG_COVI_DEV_ID}",
        "UserId": "jack@gocovi.dev",
        "OrganizationId": ORG_COVI_DEV_ID,
        "GrantedBy": "jack@gocovi.com",
        "GrantedAt": (datetime.utcnow() - timedelta(days=90)).isoformat(),
    },
    {
        "PartitionKey": "GLOBAL",
        "RowKey": f"orgperm:{ORG_COVI_DEV_ID}:jack@gocovi.dev",
        "UserId": "jack@gocovi.dev",
        "OrganizationId": ORG_COVI_DEV_ID,
        "GrantedBy": "jack@gocovi.com",
        "GrantedAt": (datetime.utcnow() - timedelta(days=90)).isoformat(),
    },
]

# Users are now in the Entities table, added to SAMPLE_ENTITIES array


def is_development_storage(connection_string: str) -> bool:
    """Check if using development storage (Azurite)"""
    return "UseDevelopmentStorage=true" in connection_string or "devstoreaccount1" in connection_string


def delete_all_tables(connection_string: str, table_names: list[str]):
    """Delete all tables (only for development storage)"""
    if not is_development_storage(connection_string):
        logger.warning(
            "⚠️  Refusing to delete tables - not using development storage")
        return

    logger.info("Deleting all tables (development storage only)...")
    service_client = TableServiceClient.from_connection_string(
        connection_string)

    for table_name in table_names:
        try:
            service_client.delete_table(table_name)
            logger.info(f"  ✓ Deleted table: {table_name}")
        except Exception as e:
            if "TableNotFound" in str(e) or "ResourceNotFound" in str(e):
                logger.info(f"  ⊘ Table doesn't exist: {table_name}")
            else:
                logger.warning(f"  ⚠️  Error deleting {table_name}: {e}")


def create_all_tables(connection_string: str, table_names: list[str]):
    """Create all tables (only for development storage)"""
    if not is_development_storage(connection_string):
        logger.warning(
            "⚠️  Refusing to create tables - not using development storage")
        return

    logger.info("Creating all tables (development storage only)...")
    service_client = TableServiceClient.from_connection_string(
        connection_string)

    for table_name in table_names:
        try:
            service_client.create_table(table_name)
            logger.info(f"  ✓ Created table: {table_name}")
        except Exception as e:
            if "TableAlreadyExists" in str(e) or "already exists" in str(e).lower():
                logger.info(f"  ⊘ Table already exists: {table_name}")
            else:
                logger.error(f"  ✗ Error creating {table_name}: {e}")
                raise


def seed_table(connection_string: str, table_name: str, entities: list):
    """Seed a table with sample data (idempotent)"""
    table_client = TableClient.from_connection_string(
        connection_string, table_name)

    inserted = 0
    skipped = 0

    for entity in entities:
        try:
            # Try to get entity first
            table_client.get_entity(
                partition_key=entity["PartitionKey"],
                row_key=entity["RowKey"]
            )
            logger.info(
                f"  ⊘ Skipped {table_name}: {entity['RowKey'][:50]}... (already exists)")
            skipped += 1
        except Exception:
            # Entity doesn't exist, insert it
            table_client.create_entity(entity)
            logger.info(
                f"  ✓ Inserted {table_name}: {entity['RowKey'][:50]}...")
            inserted += 1

    return inserted, skipped


def seed_all_data(connection_string: str = None):
    """Seed all tables with sample data"""
    if connection_string is None:
        connection_string = os.environ.get("AzureWebJobsStorage")

    if not connection_string:
        raise ValueError(
            "AzureWebJobsStorage environment variable not set")

    logger.info(
        "Seeding sample data for local development (4-table structure)...")
    logger.info("="*60)

    # Define all table names
    table_names = ["Config", "Entities", "Relationships"]

    # For development storage only: delete and recreate all tables
    if is_development_storage(connection_string):
        logger.info("\n🔄 Development storage detected - resetting tables...")
        delete_all_tables(connection_string, table_names)
        create_all_tables(connection_string, table_names)
        logger.info("✓ Tables reset complete\n")
    else:
        logger.info(
            "\n⚠️  Production storage detected - tables will not be reset")
        logger.info("    Only missing entities will be inserted\n")

    results = {}

    # Seed Config table
    logger.info("\nSeeding Config table...")
    inserted, skipped = seed_table(
        connection_string, "Config", SAMPLE_CONFIG_ENTITIES)
    results["Config"] = {"inserted": inserted, "skipped": skipped}

    # Seed Entities table
    logger.info("\nSeeding Entities table...")
    entities_executions, relationships_executions = generate_sample_executions()
    all_entities = SAMPLE_ENTITIES + entities_executions
    inserted, skipped = seed_table(
        connection_string, "Entities", all_entities)
    results["Entities"] = {"inserted": inserted, "skipped": skipped}

    # Seed Relationships table
    logger.info("\nSeeding Relationships table...")
    all_relationships = SAMPLE_RELATIONSHIPS + relationships_executions
    inserted, skipped = seed_table(
        connection_string, "Relationships", all_relationships)
    results["Relationships"] = {"inserted": inserted, "skipped": skipped}

    # Summary
    logger.info("\n" + "="*60)
    logger.info("Seed Data Summary")
    logger.info("="*60)
    total_inserted = sum(r["inserted"] for r in results.values())
    total_skipped = sum(r["skipped"] for r in results.values())

    for table_name, counts in results.items():
        logger.info(
            f"{table_name}: +{counts['inserted']} new, ⊘{counts['skipped']} existing")

    logger.info(f"\nTotal: {total_inserted} inserted, {total_skipped} skipped")
    logger.info("\nSeed data UUIDs (for testing):")
    logger.info(f"  ORG_COVI_DEV_ID = '{ORG_COVI_DEV_ID}'")
    logger.info(f"  FORM_GREETING_ID = '{FORM_GREETING_ID}'")
    logger.info(f"  FORM_ONBOARDING_ID = '{FORM_ONBOARDING_ID}'")
    logger.info(f"  FORM_GITHUB_WORKFLOW_ID = '{FORM_GITHUB_WORKFLOW_ID}'")
    logger.info("="*60)

    return results


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Allow override via command line argument
    conn_str = sys.argv[1] if len(sys.argv) > 1 else None

    try:
        seed_all_data(conn_str)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error during data seeding: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
