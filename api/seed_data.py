"""
Seed data script for Bifrost Integrations local development (4-table structure with UUIDs)
Populates Azurite with realistic sample data for testing

Run this script after initializing tables with init_tables.py
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta

from azure.data.tables import TableClient

logger = logging.getLogger(__name__)

# Use stable UUIDs for development (consistent across seed runs)
ORG_ACME_ID = "acme-org-1111-1111-1111-111111111111"
ORG_CONTOSO_ID = "contoso-2222-2222-2222-222222222222"
FORM_GREETING_ID = "greeting-form-3333-3333-333333333333"
FORM_ONBOARDING_ID = "onboarding-form-4444-444444444444"
ROLE_IT_MANAGERS_ID = "it-managers-role-5555-555555555555"
ROLE_HELP_DESK_ID = "helpdesk-role-6666-6666-666666666666"

logger.info("Generated UUIDs for seed data:")
logger.info(f"  Org ACME: {ORG_ACME_ID}")
logger.info(f"  Org Contoso: {ORG_CONTOSO_ID}")
logger.info(f"  Form Greeting: {FORM_GREETING_ID}")
logger.info(f"  Form Onboarding: {FORM_ONBOARDING_ID}")
logger.info(f"  Role IT Managers: {ROLE_IT_MANAGERS_ID}")
logger.info(f"  Role Help Desk: {ROLE_HELP_DESK_ID}")

# ==================== TABLE 1: CONFIG ====================

SAMPLE_CONFIG_ENTITIES = [
    # System config (GLOBAL)
    {
        "PartitionKey": "GLOBAL",
        "RowKey": "system:version",
        "Value": "1.0.0",
        "Type": "string",
        "Description": "Platform version",
        "UpdatedAt": datetime.utcnow().isoformat(),
        "UpdatedBy": "system",
    },
    {
        "PartitionKey": "GLOBAL",
        "RowKey": "system:maintenance_mode",
        "Value": "false",
        "Type": "bool",
        "Description": "System maintenance mode flag",
        "UpdatedAt": datetime.utcnow().isoformat(),
        "UpdatedBy": "system",
    },
    # Org-specific config
    {
        "PartitionKey": ORG_ACME_ID,
        "RowKey": "config:default_office_location",
        "Value": "New York",
        "Type": "string",
        "Description": "Default office location for new users",
        "UpdatedAt": datetime.utcnow().isoformat(),
        "UpdatedBy": "jack@gocovi.com",
    },
    {
        "PartitionKey": ORG_ACME_ID,
        "RowKey": "config:default_license_tier",
        "Value": "Microsoft 365 Business Standard",
        "Type": "string",
        "Description": "Default license for new users",
        "UpdatedAt": datetime.utcnow().isoformat(),
        "UpdatedBy": "jack@gocovi.com",
    },
    # Integration config
    {
        "PartitionKey": ORG_ACME_ID,
        "RowKey": "integration:msgraph",
        "Enabled": True,
        "Settings": json.dumps({
            "tenant_id": "12345678-1234-1234-1234-123456789012",
            "client_id": "app-client-id-123",
            "client_secret_ref": f"{ORG_ACME_ID}--msgraph-secret",
        }),
        "UpdatedAt": datetime.utcnow().isoformat(),
        "UpdatedBy": "jack@gocovi.com",
    },
    # OAuth config (example - would be encrypted in production)
    {
        "PartitionKey": ORG_ACME_ID,
        "RowKey": "oauth:microsoft",
        "AccessToken": "sample_encrypted_access_token",
        "RefreshToken": "sample_encrypted_refresh_token",
        "ExpiresAt": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        "UpdatedAt": datetime.utcnow().isoformat(),
    },
]

# ==================== TABLE 2: ENTITIES ====================

SAMPLE_ENTITIES = [
    # Organizations (GLOBAL partition)
    {
        "PartitionKey": "GLOBAL",
        "RowKey": f"org:{ORG_ACME_ID}",
        "Name": "Covi Development",
        "Domain": "gocovi.dev",
        "TenantId": "12345678-1234-1234-1234-123456789012",
        "IsActive": True,
        "CreatedAt": (datetime.utcnow() - timedelta(days=90)).isoformat(),
        "CreatedBy": "jack@gocovi.com",
        "UpdatedAt": (datetime.utcnow() - timedelta(days=30)).isoformat(),
    },
    {
        "PartitionKey": "GLOBAL",
        "RowKey": f"org:{ORG_CONTOSO_ID}",
        "Name": "Contoso Ltd",
        "Domain": "contoso.com",
        "TenantId": "87654321-4321-4321-4321-210987654321",
        "IsActive": True,
        "CreatedAt": (datetime.utcnow() - timedelta(days=60)).isoformat(),
        "CreatedBy": "jack@gocovi.com",
        "UpdatedAt": (datetime.utcnow() - timedelta(days=20)).isoformat(),
    },
    # Forms (GLOBAL and org-scoped)
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
        "IsGlobal": True,
        "IsPublic": True,  # Public form - anyone can execute
        "CreatedBy": "jack@gocovi.com",
        "CreatedAt": (datetime.utcnow() - timedelta(days=5)).isoformat(),
        "UpdatedAt": datetime.utcnow().isoformat(),
    },
    {
        "PartitionKey": ORG_ACME_ID,
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
                    "placeholder": "john.doe@acmecorp.com",
                },
            ]
        }),
        "LinkedWorkflow": "user_onboarding",
        "IsActive": True,
        "IsGlobal": False,
        "IsPublic": False,  # Restricted form - requires role assignment
        "CreatedBy": "jack@gocovi.com",
        "CreatedAt": (datetime.utcnow() - timedelta(days=30)).isoformat(),
        "UpdatedAt": datetime.utcnow().isoformat(),
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
        workflow = "user_onboarding" if i % 2 == 0 else "license_management"

        # Entities table (org-scoped execution)
        execution_entity = {
            "PartitionKey": ORG_ACME_ID,
            "RowKey": f"execution:{reverse_ts}_{exec_id}",
            "ExecutionId": exec_id,
            "WorkflowName": workflow,
            "FormId": FORM_ONBOARDING_ID if workflow == "user_onboarding" else FORM_GREETING_ID,
            "ExecutedBy": "jack@gocovi.dev",
            "Status": status,
            "InputData": json.dumps({
                "first_name": "Test",
                "last_name": f"User{i+1}",
                "email": f"test{i+1}@acmecorp.com",
                "license": "Microsoft 365 Business Standard",
            }) if workflow == "user_onboarding" else json.dumps({
                "user_email": f"existing{i+1}@acmecorp.com",
                "action": "assign",
                "license": "Microsoft 365 Business Premium",
            }),
            "Result": json.dumps({"success": True, "user_id": f"new-user-{i+1}"}) if status == "Success" else None,
            "ErrorMessage": "Sample error message for testing" if status == "Failed" else None,
            "DurationMs": 2000 + (i * 100),
            "StartedAt": execution_time.isoformat(),
            "CompletedAt": (execution_time + timedelta(seconds=2 + i * 0.1)).isoformat(),
        }

        # Relationships table (user → execution dual index)
        user_exec_entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"userexec:jack@gocovi.dev:{reverse_ts}_{exec_id}",
            "ExecutionId": exec_id,
            "OrgId": ORG_ACME_ID,
            "WorkflowName": workflow,
            "Status": status,
            "StartedAt": execution_time.isoformat(),
        }

        entities_executions.append(execution_entity)
        relationships_executions.append(user_exec_entity)

    return entities_executions, relationships_executions


# ==================== TABLE 3: RELATIONSHIPS ====================

SAMPLE_RELATIONSHIPS = [
    # Roles
    {
        "PartitionKey": "GLOBAL",
        "RowKey": f"role:{ROLE_IT_MANAGERS_ID}",
        "Name": "IT Managers",
        "Description": "IT department managers with access to user onboarding and system configuration",
        "IsActive": True,
        "CreatedBy": "jack@gocovi.com",
        "CreatedAt": (datetime.utcnow() - timedelta(days=60)).isoformat(),
        "UpdatedAt": datetime.utcnow().isoformat(),
    },
    {
        "PartitionKey": "GLOBAL",
        "RowKey": f"role:{ROLE_HELP_DESK_ID}",
        "Name": "Help Desk",
        "Description": "Help desk staff with limited access to common tasks",
        "IsActive": True,
        "CreatedBy": "jack@gocovi.com",
        "CreatedAt": (datetime.utcnow() - timedelta(days=60)).isoformat(),
        "UpdatedAt": datetime.utcnow().isoformat(),
    },
    # User-to-Role assignments (dual indexed)
    {
        "PartitionKey": "GLOBAL",
        "RowKey": f"assignedrole:{ROLE_IT_MANAGERS_ID}:jack@gocovi.dev",
        "AssignedBy": "jack@gocovi.com",
        "AssignedAt": (datetime.utcnow() - timedelta(days=60)).isoformat(),
    },
    {
        "PartitionKey": "GLOBAL",
        "RowKey": f"userrole:jack@gocovi.dev:{ROLE_IT_MANAGERS_ID}",
        "AssignedBy": "jack@gocovi.com",
        "AssignedAt": (datetime.utcnow() - timedelta(days=60)).isoformat(),
    },
    # Form-to-Role assignments (dual indexed)
    {
        "PartitionKey": "GLOBAL",
        "RowKey": f"formrole:{FORM_ONBOARDING_ID}:{ROLE_IT_MANAGERS_ID}",
        "AssignedBy": "jack@gocovi.com",
        "AssignedAt": (datetime.utcnow() - timedelta(days=30)).isoformat(),
    },
    {
        "PartitionKey": "GLOBAL",
        "RowKey": f"roleform:{ROLE_IT_MANAGERS_ID}:{FORM_ONBOARDING_ID}",
        "AssignedBy": "jack@gocovi.com",
        "AssignedAt": (datetime.utcnow() - timedelta(days=30)).isoformat(),
    },
    # User-to-Org permissions (dual indexed)
    {
        "PartitionKey": "GLOBAL",
        "RowKey": f"userperm:jack@gocovi.dev:{ORG_ACME_ID}",
        "GrantedBy": "jack@gocovi.com",
        "GrantedAt": (datetime.utcnow() - timedelta(days=90)).isoformat(),
    },
    {
        "PartitionKey": "GLOBAL",
        "RowKey": f"orgperm:{ORG_ACME_ID}:jack@gocovi.dev",
        "GrantedBy": "jack@gocovi.com",
        "GrantedAt": (datetime.utcnow() - timedelta(days=90)).isoformat(),
    },
]

# ==================== TABLE 4: USERS ====================

SAMPLE_USERS = [
    {
        "PartitionKey": "jack@gocovi.com",
        "RowKey": "user",
        "Email": "jack@gocovi.com",
        "DisplayName": "Jack Musick (Admin)",
        "UserType": "PLATFORM",
        "IsPlatformAdmin": True,
        "IsActive": True,
        "LastLogin": datetime.utcnow().isoformat(),
        "CreatedAt": (datetime.utcnow() - timedelta(days=100)).isoformat(),
    },
    {
        "PartitionKey": "jack@gocovi.dev",
        "RowKey": "user",
        "Email": "jack@gocovi.dev",
        "DisplayName": "Jack Musick (Org User)",
        "UserType": "ORG",
        "IsPlatformAdmin": False,
        "IsActive": True,
        "LastLogin": datetime.utcnow().isoformat(),
        "CreatedAt": (datetime.utcnow() - timedelta(days=100)).isoformat(),
    },
]


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
            logger.info(f"  ✓ Inserted {table_name}: {entity['RowKey'][:50]}...")
            inserted += 1

    return inserted, skipped


def seed_all_data(connection_string: str = None):
    """Seed all tables with sample data"""
    if connection_string is None:
        connection_string = os.environ.get("AzureWebJobsStorage")

    if not connection_string:
        raise ValueError(
            "AzureWebJobsStorage environment variable not set")

    logger.info("Seeding sample data for local development (4-table structure)...")
    logger.info("="*60)

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

    # Seed Users table
    logger.info("\nSeeding Users table...")
    inserted, skipped = seed_table(connection_string, "Users", SAMPLE_USERS)
    results["Users"] = {"inserted": inserted, "skipped": skipped}

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
    logger.info("\nGenerated UUIDs (save these for testing):")
    logger.info(f"  ORG_ACME_ID = '{ORG_ACME_ID}'")
    logger.info(f"  ORG_CONTOSO_ID = '{ORG_CONTOSO_ID}'")
    logger.info(f"  FORM_GREETING_ID = '{FORM_GREETING_ID}'")
    logger.info(f"  FORM_ONBOARDING_ID = '{FORM_ONBOARDING_ID}'")
    logger.info(f"  ROLE_IT_MANAGERS_ID = '{ROLE_IT_MANAGERS_ID}'")
    logger.info(f"  ROLE_HELP_DESK_ID = '{ROLE_HELP_DESK_ID}'")
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
