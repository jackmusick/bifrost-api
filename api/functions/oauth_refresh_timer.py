"""
OAuth Token Refresh Timer
Scheduled job that automatically refreshes expiring OAuth tokens
"""

import json
import logging
from datetime import datetime, timedelta

import azure.functions as func

from services.oauth_provider import OAuthProviderClient
from services.oauth_storage_service import OAuthStorageService
from shared.keyvault import KeyVaultClient
from shared.storage import TableStorageService

logger = logging.getLogger(__name__)

# Create blueprint for timer function
bp = func.Blueprint()


@bp.function_name("oauth_refresh_timer")
@bp.timer_trigger(schedule="0 */15 * * * *", arg_name="timer", run_on_startup=True)
async def oauth_refresh_timer(timer: func.TimerRequest) -> None:
    """
    Timer trigger that runs every 15 minutes to refresh expiring OAuth tokens

    Schedule: "0 */15 * * * *" = Every 15 minutes at minute 0, 15, 30, 45

    Process:
    1. Query all OAuth connections
    2. Find tokens expiring within next 30 minutes
    3. Refresh tokens using refresh_token or client_credentials
    4. Update stored tokens and connection status
    5. Log results for monitoring
    """
    start_time = datetime.utcnow()
    logger.info(f"OAuth token refresh job started at {start_time.isoformat()}")

    # Initialize services
    oauth_service = OAuthStorageService()
    oauth_provider = OAuthProviderClient()
    config_service = TableStorageService("Config")
    keyvault = KeyVaultClient()
    system_config_table = TableStorageService("SystemConfig")

    # Ensure SystemConfig table exists
    try:
        system_config_table.table_client.create_table()
        logger.info("Created SystemConfig table")
    except Exception:
        # Table already exists
        pass

    # Track results
    results = {
        "total_connections": 0,
        "needs_refresh": 0,
        "refreshed_successfully": 0,
        "refresh_failed": 0,
        "errors": []
    }

    try:
        # Get all OAuth connections from all orgs
        all_connections = []

        # Query GLOBAL connections
        global_connections = await oauth_service.list_connections("GLOBAL", include_global=False)
        all_connections.extend(global_connections)

        # TODO: Query org-specific connections (would need to enumerate orgs)
        # For now, GLOBAL connections cover most use cases

        results["total_connections"] = len(all_connections)
        logger.info(f"Found {len(all_connections)} total OAuth connections")

        # Filter connections that need refresh
        now = datetime.utcnow()
        refresh_threshold = now + timedelta(minutes=30)

        connections_to_refresh = []
        for conn in all_connections:
            # Only refresh completed connections with tokens
            if conn.status != "completed":
                continue

            # Check if token expires soon
            if conn.expires_at and conn.expires_at <= refresh_threshold:
                connections_to_refresh.append(conn)

        results["needs_refresh"] = len(connections_to_refresh)
        logger.info(f"Found {len(connections_to_refresh)} connections needing refresh")

        # Refresh each connection
        for connection in connections_to_refresh:
            try:
                logger.info(f"Refreshing OAuth connection: {connection.connection_name}")

                # Get OAuth response config to retrieve tokens
                oauth_response_key = f"config:{connection.oauth_response_ref}"
                oauth_response_config = config_service.get_entity(
                    connection.org_id,
                    oauth_response_key
                )

                if not oauth_response_config:
                    raise Exception(f"OAuth response config not found: {oauth_response_key}")

                # Get Key Vault secret name
                keyvault_secret_name = oauth_response_config.get("Value")

                if not keyvault_secret_name:
                    raise Exception("OAuth response config missing Key Vault secret name")

                # Retrieve OAuth tokens from Key Vault
                try:
                    secret = keyvault._client.get_secret(keyvault_secret_name)
                    oauth_response_json = secret.value
                    oauth_response = json.loads(oauth_response_json)
                except Exception as e:
                    raise Exception(f"Failed to retrieve OAuth tokens from Key Vault: {e}") from e

                # Get refresh token
                refresh_token = oauth_response.get("refresh_token")

                if not refresh_token:
                    raise Exception(
                        "No refresh token available - reconnection required to obtain new credentials"
                    )

                # Get client secret if exists (for non-PKCE flows)
                client_secret = None
                if connection.client_secret_ref:
                    try:
                        client_secret_key = f"config:{connection.client_secret_ref}"
                        client_secret_config = config_service.get_entity(
                            connection.org_id,
                            client_secret_key
                        )

                        if client_secret_config:
                            keyvault_secret_name = client_secret_config.get("Value")
                            if keyvault_secret_name:
                                secret = keyvault._client.get_secret(keyvault_secret_name)
                                client_secret = secret.value
                    except Exception as e:
                        logger.warning(f"Could not retrieve client_secret: {e}")

                # Refresh the access token
                success, result = await oauth_provider.refresh_access_token(
                    token_url=connection.token_url,
                    refresh_token=refresh_token,
                    client_id=connection.client_id,
                    client_secret=client_secret
                )

                if not success:
                    error_msg = result.get("error_description", result.get("error", "Token refresh failed"))
                    raise Exception(f"Token refresh failed: {error_msg}")

                # Store refreshed tokens (preserve old refresh_token if new one not provided)
                new_refresh_token = result.get("refresh_token") or refresh_token

                await oauth_service.store_tokens(
                    org_id=connection.org_id,
                    connection_name=connection.connection_name,
                    access_token=result["access_token"],
                    refresh_token=new_refresh_token,
                    expires_at=result["expires_at"],
                    token_type=result["token_type"],
                    updated_by="system:oauth_refresh_timer"
                )

                # Update connection status
                await oauth_service.update_connection_status(
                    org_id=connection.org_id,
                    connection_name=connection.connection_name,
                    status="completed",
                    status_message="Token refreshed by scheduled job",
                    expires_at=result["expires_at"],
                    last_refresh_at=datetime.utcnow()
                )

                results["refreshed_successfully"] += 1
                logger.info(f"Successfully refreshed: {connection.connection_name}")

            except Exception as e:
                results["refresh_failed"] += 1
                error_info = {
                    "connection_name": connection.connection_name,
                    "org_id": connection.org_id,
                    "error": str(e)
                }
                results["errors"].append(error_info)

                logger.error(
                    f"Failed to refresh {connection.connection_name}: {str(e)}",
                    extra=error_info
                )

                # Update connection status to failed
                try:
                    await oauth_service.update_connection_status(
                        org_id=connection.org_id,
                        connection_name=connection.connection_name,
                        status="failed",
                        status_message=f"Automatic refresh failed: {str(e)}"
                    )
                except Exception as status_error:
                    logger.error(f"Could not update status: {status_error}")

        # Calculate duration
        end_time = datetime.utcnow()
        duration_seconds = (end_time - start_time).total_seconds()

        # Store job status in SystemConfig table
        job_status_entity = {
            "PartitionKey": "OAuthJobStatus",
            "RowKey": "TokenRefreshJob",
            "StartTime": start_time.isoformat(),
            "EndTime": end_time.isoformat(),
            "DurationSeconds": duration_seconds,
            "Status": "completed",
            "TotalConnections": results["total_connections"],
            "NeedsRefresh": results["needs_refresh"],
            "RefreshedSuccessfully": results["refreshed_successfully"],
            "RefreshFailed": results["refresh_failed"],
            "Errors": json.dumps(results["errors"]) if results["errors"] else None
        }
        system_config_table.upsert_entity(job_status_entity)

        # Log summary
        logger.info(
            f"OAuth token refresh job completed in {duration_seconds:.2f}s: "
            f"Total={results['total_connections']}, "
            f"NeedsRefresh={results['needs_refresh']}, "
            f"Success={results['refreshed_successfully']}, "
            f"Failed={results['refresh_failed']}"
        )

    except Exception as e:
        logger.error(f"OAuth refresh job failed: {str(e)}", exc_info=True)

        # Store failed job status
        end_time = datetime.utcnow()
        duration_seconds = (end_time - start_time).total_seconds()

        job_status_entity = {
            "PartitionKey": "OAuthJobStatus",
            "RowKey": "TokenRefreshJob",
            "StartTime": start_time.isoformat(),
            "EndTime": end_time.isoformat(),
            "DurationSeconds": duration_seconds,
            "Status": "failed",
            "ErrorMessage": str(e),
            "TotalConnections": 0,
            "NeedsRefresh": 0,
            "RefreshedSuccessfully": 0,
            "RefreshFailed": 0,
            "Errors": None
        }

        try:
            system_config_table = TableStorageService("SystemConfig")
            system_config_table.upsert_entity(job_status_entity)
        except Exception:
            pass
