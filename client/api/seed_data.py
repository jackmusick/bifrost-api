"""
Seed data script for MSP Automation Platform local development
Populates Azurite with realistic sample data for testing

Run this script after initializing tables with init_tables.py
"""

import os
import json
import logging
import uuid
from datetime import datetime, timedelta
from azure.data.tables import TableClient
from azure.core.exceptions import ResourceExistsError

logger = logging.getLogger(__name__)

# Sample data
SAMPLE_ORGS = [
    {
        "PartitionKey": "ORG",
        "RowKey": "org-acme-123",
        "Name": "Covi Development",
        "TenantId": "12345678-1234-1234-1234-123456789012",
        "IsActive": True,
        "CreatedAt": (datetime.utcnow() - timedelta(days=90)).isoformat(),
        "CreatedBy": "jack@gocovi.com",  # Platform admin email
        "UpdatedAt": (datetime.utcnow() - timedelta(days=30)).isoformat(),
    },
]

SAMPLE_ORG_CONFIGS = [
    {
        "PartitionKey": "org-acme-123",
        "RowKey": "config:default_office_location",
        "Value": "New York",
        "Type": "string",
        "Description": "Default office location for new users",
        "UpdatedAt": datetime.utcnow().isoformat(),
        "UpdatedBy": "jack@gocovi.com",  # Platform admin email
    },
    {
        "PartitionKey": "org-acme-123",
        "RowKey": "config:default_license_tier",
        "Value": "Microsoft 365 Business Standard",
        "Type": "string",
        "Description": "Default license for new users",
        "UpdatedAt": datetime.utcnow().isoformat(),
        "UpdatedBy": "jack@gocovi.com",  # Platform admin email
    },
]

SAMPLE_INTEGRATION_CONFIGS = [
    {
        "PartitionKey": "org-acme-123",
        "RowKey": "integration:msgraph",
        "Enabled": True,
        "Settings": json.dumps({
            "tenant_id": "12345678-1234-1234-1234-123456789012",
            "client_id": "app-client-id-123",
            "client_secret_ref": "org-acme-123--msgraph-secret",
        }),
        "UpdatedAt": datetime.utcnow().isoformat(),
        "UpdatedBy": "jack@gocovi.com",  # Platform admin email
    },
]

SAMPLE_USERS = [
    {
        "PartitionKey": "USER",
        "RowKey": "jack@gocovi.com",  # Using email as user ID for consistency with SWA CLI
        "Email": "jack@gocovi.com",
        "DisplayName": "Jack Musick",
        "UserType": "PLATFORM",
        "IsPlatformAdmin": True,
        "IsActive": True,
        "LastLogin": datetime.utcnow().isoformat(),
        "CreatedAt": (datetime.utcnow() - timedelta(days=100)).isoformat(),
    },
    {
        "PartitionKey": "USER",
        "RowKey": "jack@gocovi.dev",  # Using email as user ID for consistency with SWA CLI
        "Email": "jack@gocovi.dev",
        "DisplayName": "Jack Musick",
        "UserType": "ORG",
        "IsPlatformAdmin": False,
        "IsActive": True,
        "LastLogin": datetime.utcnow().isoformat(),
        "CreatedAt": (datetime.utcnow() - timedelta(days=100)).isoformat(),
    },
]

SAMPLE_USER_PERMISSIONS = [
    {
        "PartitionKey": "jack@gocovi.dev",  # Using email as user ID
        "RowKey": "org-acme-123",
        "CanExecuteWorkflows": True,
        "CanManageConfig": False,
        "CanManageForms": False,
        "CanViewHistory": True,
        "GrantedBy": "jack@gocovi.com",  # Platform admin email
        "GrantedAt": (datetime.utcnow() - timedelta(days=90)).isoformat(),
    },
]

SAMPLE_ORG_PERMISSIONS = [
    {
        "PartitionKey": "org-acme-123",
        "RowKey": "jack@gocovi.dev",  # Using email as user ID
        "CanExecuteWorkflows": True,
        "CanManageConfig": False,
        "CanManageForms": False,
        "CanViewHistory": True,
        "GrantedBy": "jack@gocovi.com",  # Platform admin email
        "GrantedAt": (datetime.utcnow() - timedelta(days=90)).isoformat(),
    },
]

SAMPLE_ROLES = [
    {
        "PartitionKey": "ROLES",
        "RowKey": "role:it-managers",
        "Name": "IT Managers",
        "Description": "IT department managers with access to user onboarding and system configuration",
        "IsActive": True,
        "CreatedBy": "jack@gocovi.com",
        "CreatedAt": (datetime.utcnow() - timedelta(days=60)).isoformat(),
        "UpdatedAt": datetime.utcnow().isoformat(),
    },
    {
        "PartitionKey": "ROLES",
        "RowKey": "role:help-desk",
        "Name": "Help Desk",
        "Description": "Help desk staff with limited access to common tasks",
        "IsActive": True,
        "CreatedBy": "jack@gocovi.com",
        "CreatedAt": (datetime.utcnow() - timedelta(days=60)).isoformat(),
        "UpdatedAt": datetime.utcnow().isoformat(),
    },
]

SAMPLE_USER_ROLES = [
    {
        "PartitionKey": "it-managers",
        "RowKey": "user:jack@gocovi.dev",
        "UserId": "jack@gocovi.dev",
        "RoleId": "it-managers",
        "AssignedBy": "jack@gocovi.com",
        "AssignedAt": (datetime.utcnow() - timedelta(days=60)).isoformat(),
    },
]

SAMPLE_FORMS = [
    {
        "PartitionKey": "GLOBAL",
        "RowKey": "form-simple-greeting",
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
        "IsPublic": True,  # Public form - anyone can execute
        "CreatedBy": "jack@gocovi.com",
        "CreatedAt": (datetime.utcnow() - timedelta(days=5)).isoformat(),
        "UpdatedAt": datetime.utcnow().isoformat(),
    },
    {
        "PartitionKey": "org-acme-123",
        "RowKey": "form-user-onboarding",
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
        "IsPublic": False,  # Restricted form - requires group assignment
        "CreatedBy": "jack@gocovi.com",
        "CreatedAt": (datetime.utcnow() - timedelta(days=30)).isoformat(),
        "UpdatedAt": datetime.utcnow().isoformat(),
    },
]

SAMPLE_FORM_ROLES = [
    {
        "PartitionKey": "form-user-onboarding",
        "RowKey": "role:it-managers",
        "FormId": "form-user-onboarding",
        "RoleId": "it-managers",
        "AssignedBy": "jack@gocovi.com",
        "AssignedAt": (datetime.utcnow() - timedelta(days=30)).isoformat(),
    },
]

# Sample workflow executions with reverse timestamp
def generate_sample_executions():
    executions = []
    user_executions = []
    base_time = datetime.utcnow()

    for i in range(5):
        execution_time = base_time - timedelta(minutes=i * 30)
        reverse_ts = 9999999999999 - int(execution_time.timestamp() * 1000)
        exec_id = str(uuid.uuid4())
        row_key = f"{reverse_ts}_{exec_id}"

        status = "Success" if i % 2 == 0 else "Failed"
        workflow = "user_onboarding" if i % 2 == 0 else "license_management"

        execution = {
            "PartitionKey": "org-acme-123",
            "RowKey": row_key,
            "ExecutionId": exec_id,
            "WorkflowName": workflow,
            "FormId": "form-user-onboarding" if workflow == "user_onboarding" else "form-simple-greeting",
            "ExecutedBy": "jack@gocovi.dev",  # Org user email
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
            "ErrorMessage": f"Sample error message for testing" if status == "Failed" else None,
            "DurationMs": 2000 + (i * 100),
            "StartedAt": execution_time.isoformat(),
            "CompletedAt": (execution_time + timedelta(seconds=2 + i * 0.1)).isoformat(),
        }

        user_execution = {
            "PartitionKey": "jack@gocovi.dev",  # Org user email
            "RowKey": row_key,
            "ExecutionId": exec_id,
            "OrgId": "org-acme-123",
            "WorkflowName": workflow,
            "Status": status,
            "StartedAt": execution_time.isoformat(),
        }

        executions.append(execution)
        user_executions.append(user_execution)

    return executions, user_executions


def seed_table(connection_string: str, table_name: str, entities: list):
    """Seed a table with sample data (idempotent)"""
    table_client = TableClient.from_connection_string(connection_string, table_name)

    inserted = 0
    skipped = 0

    for entity in entities:
        try:
            # Try to get entity first
            existing = table_client.get_entity(
                partition_key=entity["PartitionKey"],
                row_key=entity["RowKey"]
            )
            logger.info(f"  ⊘ Skipped {table_name}: {entity['RowKey']} (already exists)")
            skipped += 1
        except:
            # Entity doesn't exist, insert it
            table_client.create_entity(entity)
            logger.info(f"  ✓ Inserted {table_name}: {entity['RowKey']}")
            inserted += 1

    return inserted, skipped


def seed_all_data(connection_string: str = None):
    """Seed all tables with sample data"""
    if connection_string is None:
        connection_string = os.environ.get("TABLE_STORAGE_CONNECTION_STRING")

    if not connection_string:
        raise ValueError("TABLE_STORAGE_CONNECTION_STRING environment variable not set")

    logger.info("Seeding sample data for local development...")
    logger.info("="*60)

    results = {}

    # Seed organizations
    logger.info("\nSeeding Organizations...")
    inserted, skipped = seed_table(connection_string, "Organizations", SAMPLE_ORGS)
    results["Organizations"] = {"inserted": inserted, "skipped": skipped}

    # Seed org configs
    logger.info("\nSeeding Config...")
    inserted, skipped = seed_table(connection_string, "Config", SAMPLE_ORG_CONFIGS)
    results["Config"] = {"inserted": inserted, "skipped": skipped}

    # Seed integration configs
    logger.info("\nSeeding IntegrationConfig...")
    inserted, skipped = seed_table(connection_string, "IntegrationConfig", SAMPLE_INTEGRATION_CONFIGS)
    results["IntegrationConfig"] = {"inserted": inserted, "skipped": skipped}

    # Seed users
    logger.info("\nSeeding Users...")
    inserted, skipped = seed_table(connection_string, "Users", SAMPLE_USERS)
    results["Users"] = {"inserted": inserted, "skipped": skipped}

    # Seed user permissions
    logger.info("\nSeeding UserPermissions...")
    inserted, skipped = seed_table(connection_string, "UserPermissions", SAMPLE_USER_PERMISSIONS)
    results["UserPermissions"] = {"inserted": inserted, "skipped": skipped}

    # Seed org permissions
    logger.info("\nSeeding OrgPermissions...")
    inserted, skipped = seed_table(connection_string, "OrgPermissions", SAMPLE_ORG_PERMISSIONS)
    results["OrgPermissions"] = {"inserted": inserted, "skipped": skipped}

    # Seed roles (groups)
    logger.info("\nSeeding Roles...")
    inserted, skipped = seed_table(connection_string, "Roles", SAMPLE_ROLES)
    results["Roles"] = {"inserted": inserted, "skipped": skipped}

    # Seed user-role assignments
    logger.info("\nSeeding UserRoles...")
    inserted, skipped = seed_table(connection_string, "UserRoles", SAMPLE_USER_ROLES)
    results["UserRoles"] = {"inserted": inserted, "skipped": skipped}

    # Seed forms
    logger.info("\nSeeding Forms...")
    inserted, skipped = seed_table(connection_string, "Forms", SAMPLE_FORMS)
    results["Forms"] = {"inserted": inserted, "skipped": skipped}

    # Seed form-role assignments
    logger.info("\nSeeding FormRoles...")
    inserted, skipped = seed_table(connection_string, "FormRoles", SAMPLE_FORM_ROLES)
    results["FormRoles"] = {"inserted": inserted, "skipped": skipped}

    # Seed workflow executions
    logger.info("\nSeeding WorkflowExecutions and UserExecutions...")
    executions, user_executions = generate_sample_executions()
    inserted, skipped = seed_table(connection_string, "WorkflowExecutions", executions)
    results["WorkflowExecutions"] = {"inserted": inserted, "skipped": skipped}
    inserted, skipped = seed_table(connection_string, "UserExecutions", user_executions)
    results["UserExecutions"] = {"inserted": inserted, "skipped": skipped}

    # Summary
    logger.info("\n" + "="*60)
    logger.info("Seed Data Summary")
    logger.info("="*60)
    total_inserted = sum(r["inserted"] for r in results.values())
    total_skipped = sum(r["skipped"] for r in results.values())

    for table_name, counts in results.items():
        logger.info(f"{table_name}: +{counts['inserted']} new, ⊘{counts['skipped']} existing")

    logger.info(f"\nTotal: {total_inserted} inserted, {total_skipped} skipped")
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
