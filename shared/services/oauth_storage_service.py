"""
OAuth Storage Service
Handles CRUD operations for OAuth connections with Config table integration
"""

import json
import logging
from datetime import datetime

from shared.models import CreateOAuthConnectionRequest, OAuthConnection, UpdateOAuthConnectionRequest
from shared.keyvault import KeyVaultClient
from shared.async_storage import AsyncTableStorageService
from shared.secret_naming import generate_oauth_secret_name

logger = logging.getLogger(__name__)


class OAuthStorageService:
    """
    Service for managing OAuth connections in Table Storage and Config table

    Responsibilities:
    - CRUD operations for OAuthConnections table
    - Store client_secret in Config table with Type="secret_ref"
    - Store OAuth response tokens in Config table with Type="secret_ref"
    - Store metadata in Config table with Type="json"
    - Implement org→GLOBAL fallback pattern
    """

    def __init__(self, connection_string: str | None = None):
        """
        Initialize OAuth storage service

        Args:
            connection_string: Optional Azure Storage connection string override
        """
        self.config_table = AsyncTableStorageService("Config", connection_string or None)

        logger.info("OAuthStorageService initialized with Config table only")

    async def create_connection(
        self,
        org_id: str,
        request: CreateOAuthConnectionRequest,
        created_by: str
    ) -> OAuthConnection:
        """
        Create a new OAuth connection

        Process:
        1. Create OAuth entity with oauth: prefix
        2. Store client_secret in Key Vault (if provided)
        3. Store metadata in OAuth entity with direct refs

        Args:
            org_id: Organization ID or "GLOBAL"
            request: OAuth connection creation request
            created_by: User ID creating the connection

        Returns:
            Created OAuthConnection

        Raises:
            ResourceExistsError: If connection with same name already exists
        """
        now = datetime.utcnow()

        # Generate Key Vault secret names
        client_secret_ref = None
        if request.client_secret:
            try:
                async with KeyVaultClient() as keyvault:
                    # Generate full KV secret name using bifrost_{scope}_oauth_{name}_{type}_{uuid}
                    client_secret_ref = generate_oauth_secret_name(
                        org_id,
                        request.connection_name,
                        "client-secret"
                    )
                    await keyvault.set_secret(client_secret_ref, request.client_secret)
                    logger.info(f"Stored client_secret in Key Vault: {client_secret_ref}")
            except ValueError as e:
                # KeyVault not configured (e.g., in test environment)
                logger.warning(f"KeyVault not available for client_secret storage: {e}")
                logger.warning("Client secret will not be persisted - OAuth connection may not work in production")
            except Exception as e:
                logger.error(f"Failed to store client_secret in Key Vault: {e}")
                raise
        else:
            logger.info(f"No client secret provided (PKCE flow) for {request.connection_name}")

        # Store OAuth entity with oauth: prefix
        oauth_entity = {
            "PartitionKey": org_id,
            "RowKey": f"oauth:{request.connection_name}",
            "Type": "oauth",
            "Description": request.description or f"OAuth connection: {request.connection_name}",
            "OAuthFlowType": request.oauth_flow_type,
            "ClientId": request.client_id,
            "ClientSecretRef": client_secret_ref,  # Full KV secret name or None
            "OAuthResponseRef": None,  # Will be set when tokens are stored
            "AuthorizationUrl": request.authorization_url,
            "TokenUrl": request.token_url,
            "Scopes": request.scopes,
            "RedirectUri": f"/oauth/callback/{request.connection_name}",
            "Status": "not_connected",
            "CreatedBy": created_by,
            "CreatedAt": now.isoformat(),
            "UpdatedAt": now.isoformat()
        }

        await self.config_table.insert_entity(oauth_entity)
        logger.info(f"Created OAuth connection: {request.connection_name}")

        # Create OAuth connection model
        connection = OAuthConnection(
            org_id=org_id,
            connection_name=request.connection_name,
            description=request.description,
            oauth_flow_type=request.oauth_flow_type,
            client_id=request.client_id,
            client_secret_ref=client_secret_ref or "",
            oauth_response_ref="",
            authorization_url=request.authorization_url,
            token_url=request.token_url,
            scopes=request.scopes,
            redirect_uri=f"/oauth/callback/{request.connection_name}",
            status="not_connected",
            created_by=created_by,
            created_at=now,
            updated_at=now,
            expires_at=None
        )

        return connection

    async def get_connection(
        self,
        org_id: str,
        connection_name: str
    ) -> OAuthConnection | None:
        """
        Get OAuth connection with org→GLOBAL fallback

        Args:
            org_id: Organization ID
            connection_name: Connection name

        Returns:
            OAuthConnection or None if not found
        """
        oauth_rowkey = f"oauth:{connection_name}"

        try:
            # First, try org-specific OAuth entity
            oauth_entity = await self.config_table.get_entity(org_id, oauth_rowkey)

            if oauth_entity:
                logger.debug(f"Found org-specific OAuth connection: {connection_name} for org {org_id}")
                return self._entity_to_oauth_connection(oauth_entity)

            # If not found, try GLOBAL
            if org_id != "GLOBAL":
                global_oauth_entity = await self.config_table.get_entity("GLOBAL", oauth_rowkey)

                if global_oauth_entity:
                    logger.debug(f"Found GLOBAL OAuth connection: {connection_name}")
                    return self._entity_to_oauth_connection(global_oauth_entity)
        except Exception as e:
            logger.warning(f"Error retrieving OAuth connection: {e}")

        logger.debug(f"OAuth connection not found: {connection_name} (org: {org_id})")
        return None

    async def list_connections(
        self,
        org_id: str,
        include_global: bool = True
    ) -> list[OAuthConnection]:
        """
        List OAuth connections for an organization

        Args:
            org_id: Organization ID
            include_global: Whether to include GLOBAL connections

        Returns:
            List of OAuthConnection
        """
        connections = []

        try:
            # Query OAuth entities for org
            org_query_filter = f"PartitionKey eq '{org_id}' and RowKey ge 'oauth:' and RowKey lt 'oauth;'"
            org_oauth_entities = list(await self.config_table.query_entities(filter=org_query_filter))

            # Process org-specific connections
            for oauth_entity in org_oauth_entities:
                connection = self._entity_to_oauth_connection(oauth_entity)
                if connection:
                    connections.append(connection)

            # Add GLOBAL connections if requested
            if include_global and org_id != "GLOBAL":
                global_query_filter = "PartitionKey eq 'GLOBAL' and RowKey ge 'oauth:' and RowKey lt 'oauth;'"
                global_oauth_entities = list(await self.config_table.query_entities(filter=global_query_filter))

                for oauth_entity in global_oauth_entities:
                    connection = self._entity_to_oauth_connection(oauth_entity)
                    if connection:
                        connections.append(connection)

            logger.info(f"Listed {len(connections)} OAuth connections for org {org_id} (include_global={include_global})")

        except Exception as e:
            logger.warning(f"Error listing OAuth connections: {e}")

        return connections

    async def update_connection(
        self,
        org_id: str,
        connection_name: str,
        request: UpdateOAuthConnectionRequest,
        updated_by: str
    ) -> OAuthConnection | None:
        """
        Update an existing OAuth connection

        Args:
            org_id: Organization ID
            connection_name: Connection name
            request: Update request with optional fields
            updated_by: User ID making the update

        Returns:
            Updated OAuthConnection or None if not found
        """
        # Retrieve current OAuth entity
        oauth_rowkey = f"oauth:{connection_name}"
        oauth_entity = await self.config_table.get_entity(org_id, oauth_rowkey)

        if not oauth_entity:
            logger.warning(f"OAuth connection not found for update: {connection_name}")
            return None

        # Update fields if provided
        if request.client_id is not None:
            oauth_entity['ClientId'] = request.client_id
        if request.authorization_url is not None:
            oauth_entity['AuthorizationUrl'] = request.authorization_url
        if request.token_url is not None:
            oauth_entity['TokenUrl'] = request.token_url
        if request.scopes is not None:
            oauth_entity['Scopes'] = request.scopes

        # Update client_secret if provided - version the existing ref
        if request.client_secret is not None:
            try:
                async with KeyVaultClient() as keyvault:
                    # Get existing ref or generate new one if none exists
                    client_secret_ref = oauth_entity.get('ClientSecretRef')

                    if not client_secret_ref:
                        # First time setting client secret - generate new ref
                        client_secret_ref = generate_oauth_secret_name(
                            org_id,
                            connection_name,
                            "client-secret"
                        )
                        oauth_entity['ClientSecretRef'] = client_secret_ref
                        logger.info(f"Creating new client_secret in Key Vault: {client_secret_ref}")
                    else:
                        # Reuse existing ref - this creates a new version in Key Vault
                        logger.info(f"Updating client_secret (new version) in Key Vault: {client_secret_ref}")

                    await keyvault.set_secret(client_secret_ref, request.client_secret)
            except ValueError as e:
                # KeyVault not configured (e.g., in test environment)
                logger.warning(f"KeyVault not available for client_secret update: {e}")
                logger.warning("Client secret will not be persisted - OAuth connection may not work in production")
            except Exception as e:
                logger.error(f"Failed to update client_secret in Key Vault: {e}")
                raise

        # Mark as not connected if significant changes occurred
        if request.client_id or request.client_secret or request.authorization_url or request.token_url:
            oauth_entity['Status'] = 'not_connected'

        # Update timestamps
        oauth_entity['UpdatedAt'] = datetime.utcnow().isoformat()
        oauth_entity['UpdatedBy'] = updated_by

        await self.config_table.upsert_entity(oauth_entity)
        logger.info(f"Updated OAuth connection: {connection_name}")

        return self._entity_to_oauth_connection(oauth_entity)

    def _entity_to_oauth_connection(self, entity: dict) -> OAuthConnection | None:
        """
        Convert Table Storage entity to OAuthConnection model

        Args:
            entity: OAuth entity from Table Storage

        Returns:
            OAuthConnection model or None if conversion fails
        """
        try:
            # Parse datetime fields
            created_at_str = entity.get("CreatedAt")
            created_at = datetime.utcnow()
            if created_at_str and isinstance(created_at_str, str):
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError, TypeError):
                    pass
            elif isinstance(created_at_str, datetime):
                created_at = created_at_str

            updated_at_str = entity.get("UpdatedAt")
            updated_at = created_at
            if updated_at_str and isinstance(updated_at_str, str):
                try:
                    updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError, TypeError):
                    pass
            elif isinstance(updated_at_str, datetime):
                updated_at = updated_at_str

            expires_at = None
            expires_at_str = entity.get("ExpiresAt")
            if expires_at_str and isinstance(expires_at_str, str):
                try:
                    expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError, TypeError):
                    pass
            elif isinstance(expires_at_str, datetime):
                expires_at = expires_at_str

            # Extract connection name from RowKey (remove "oauth:" prefix)
            connection_name = entity["RowKey"].replace("oauth:", "", 1)

            # Get oauth_flow_type, default to authorization_code if not set
            oauth_flow_type = entity.get("OAuthFlowType", "authorization_code")

            # Get URLs - use None instead of empty string for optional authorization_url
            authorization_url = entity.get("AuthorizationUrl") or None
            token_url = entity.get("TokenUrl")

            # Token URL is required, must be https
            if not token_url or not token_url.startswith("https://"):
                logger.warning(f"Invalid or missing token_url for OAuth connection {connection_name}, skipping")
                return None

            return OAuthConnection(
                org_id=entity["PartitionKey"],
                connection_name=connection_name,
                description=entity.get("Description"),
                oauth_flow_type=oauth_flow_type,
                client_id=entity.get("ClientId", ""),
                client_secret_ref=entity.get("ClientSecretRef") or "",
                oauth_response_ref=entity.get("OAuthResponseRef") or "",
                authorization_url=authorization_url,
                token_url=token_url,
                scopes=entity.get("Scopes", ""),
                redirect_uri=entity.get("RedirectUri", f"/oauth/callback/{connection_name}"),
                status=entity.get("Status", "not_connected"),
                status_message=entity.get("StatusMessage"),
                expires_at=expires_at,
                created_at=created_at,
                created_by=entity.get("CreatedBy", "system"),
                updated_at=updated_at
            )
        except Exception as e:
            logger.error(f"Failed to convert OAuth entity to model: {e}", exc_info=True)
            return None

    async def delete_connection(
        self,
        org_id: str,
        connection_name: str
    ) -> bool:
        """
        Delete an OAuth connection and its associated secrets

        Args:
            org_id: Organization ID
            connection_name: Connection name

        Returns:
            True if deleted, False if not found
        """
        # Get the OAuth entity to find secret refs
        oauth_rowkey = f"oauth:{connection_name}"
        oauth_entity = await self.config_table.get_entity(org_id, oauth_rowkey)

        if not oauth_entity:
            logger.warning(f"OAuth connection not found for deletion: {connection_name}")
            return False

        # Delete secrets from Key Vault using direct refs
        try:
            async with KeyVaultClient() as keyvault:
                client_secret_ref = oauth_entity.get("ClientSecretRef")
                oauth_response_ref = oauth_entity.get("OAuthResponseRef")

                if client_secret_ref:
                    try:
                        await keyvault.delete_secret(client_secret_ref)
                        logger.debug(f"Deleted Key Vault secret: {client_secret_ref}")
                    except Exception as e:
                        logger.debug(f"Could not delete Key Vault secret {client_secret_ref}: {e}")

                if oauth_response_ref:
                    try:
                        await keyvault.delete_secret(oauth_response_ref)
                        logger.debug(f"Deleted Key Vault secret: {oauth_response_ref}")
                    except Exception as e:
                        logger.debug(f"Could not delete Key Vault secret {oauth_response_ref}: {e}")
        except ValueError as e:
            logger.warning(f"KeyVault not available for secret deletion: {e}")
            logger.debug("Skipping Key Vault secret cleanup")

        # Delete OAuth entity
        try:
            await self.config_table.delete_entity(org_id, oauth_rowkey)
            logger.debug(f"Deleted OAuth entity: {oauth_rowkey}")
        except Exception as e:
            logger.warning(f"Failed to delete OAuth entity {oauth_rowkey}: {e}")

        logger.info(f"Deleted OAuth connection: {connection_name}")
        return True

    async def store_tokens(
        self,
        org_id: str,
        connection_name: str,
        access_token: str,
        refresh_token: str | None,
        expires_at: datetime,
        token_type: str = "Bearer",
        updated_by: str = "system"
    ) -> bool:
        """
        Store OAuth tokens directly in OAuth entity

        Args:
            org_id: Organization ID
            connection_name: Connection name
            access_token: OAuth access token
            refresh_token: Optional refresh token
            expires_at: Token expiration datetime
            token_type: Token type (usually "Bearer")
            updated_by: User ID storing tokens

        Returns:
            True if stored successfully
        """
        # Prepare OAuth response JSON
        oauth_response = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": token_type,
            "expires_at": expires_at.isoformat()
        }

        # Get OAuth entity to check for existing response ref
        oauth_rowkey = f"oauth:{connection_name}"
        oauth_entity = await self.config_table.get_entity(org_id, oauth_rowkey)

        if not oauth_entity:
            logger.error(f"OAuth connection not found: {connection_name}")
            return False

        # Store OAuth response JSON in Key Vault
        oauth_response_ref = oauth_entity.get("OAuthResponseRef")

        try:
            async with KeyVaultClient() as keyvault:
                if oauth_response_ref:
                    # Reuse existing ref (creates new version in Key Vault)
                    await keyvault.set_secret(oauth_response_ref, json.dumps(oauth_response))
                    logger.info(f"Updated existing OAuth token secret: {oauth_response_ref}")
                else:
                    # Generate new secret ref
                    oauth_response_ref = generate_oauth_secret_name(
                        org_id,
                        connection_name,
                        "response"
                    )
                    await keyvault.set_secret(oauth_response_ref, json.dumps(oauth_response))
                    logger.info(f"Created new OAuth token secret: {oauth_response_ref}")

                    # Update entity with new ref
                    oauth_entity["OAuthResponseRef"] = oauth_response_ref
        except ValueError as e:
            logger.warning(f"KeyVault not available for OAuth token storage: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to store OAuth tokens in Key Vault: {e}")
            raise

        # Update OAuth entity with new status and expiration
        oauth_entity["Status"] = "completed"
        oauth_entity["ExpiresAt"] = expires_at.isoformat()
        oauth_entity["UpdatedAt"] = datetime.utcnow().isoformat()
        oauth_entity["UpdatedBy"] = updated_by

        await self.config_table.upsert_entity(oauth_entity)
        logger.info(f"Updated OAuth connection status to completed: {connection_name}")

        return True

    async def refresh_token(
        self,
        org_id: str,
        connection_name: str
    ) -> bool:
        """
        Refresh OAuth access token for any flow type

        Handles both authorization_code (uses refresh_token) and
        client_credentials (gets new token with client_id + client_secret)

        Args:
            org_id: Organization ID
            connection_name: Connection name

        Returns:
            True if refreshed successfully, False otherwise
        """
        from shared.services.oauth_provider import OAuthProviderClient
        import json

        try:
            # Get connection
            connection = await self.get_connection(org_id, connection_name)
            if not connection:
                logger.error(f"Connection not found for refresh: {connection_name}")
                return False

            logger.info(f"Refreshing OAuth connection: {connection_name} (flow={connection.oauth_flow_type})")

            # Get client secret if exists using direct ref
            client_secret = None
            if connection.client_secret_ref:
                try:
                    async with KeyVaultClient() as keyvault:
                        client_secret = await keyvault.get_secret(connection.client_secret_ref)
                        logger.info("Successfully retrieved client secret")
                except Exception as e:
                    logger.error(f"Could not retrieve client_secret: {e}", exc_info=True)

            # Refresh based on flow type
            oauth_provider = OAuthProviderClient()

            if connection.oauth_flow_type == "client_credentials":
                # Client credentials: get new token with client_id + client_secret
                logger.info(f"Refreshing client_credentials token for {connection_name}")

                if not client_secret:
                    raise Exception("Client credentials flow requires client_secret")

                success, result = await oauth_provider.get_client_credentials_token(
                    token_url=connection.token_url,
                    client_id=connection.client_id,
                    client_secret=client_secret,
                    scopes=connection.scopes
                )

                if not success:
                    error_msg = result.get("error_description", result.get("error", "Token refresh failed"))
                    logger.error(f"Failed to refresh token: {error_msg}")
                    return False

                # Client credentials doesn't have refresh token
                new_refresh_token = None

            else:
                # Authorization code flow: use refresh_token
                logger.info(f"Refreshing authorization_code token for {connection_name}")

                # Get OAuth response from Key Vault using direct ref
                if not connection.oauth_response_ref:
                    logger.error(f"No oauth_response_ref found for {connection_name}")
                    return False

                async with KeyVaultClient() as keyvault:
                    oauth_response_json = await keyvault.get_secret(connection.oauth_response_ref)
                    assert oauth_response_json is not None, "OAuth response is None"
                    oauth_response = json.loads(oauth_response_json)

                refresh_token = oauth_response.get("refresh_token")

                if not refresh_token:
                    logger.error(f"No refresh token available for {connection_name}")
                    return False

                success, result = await oauth_provider.refresh_access_token(
                    token_url=connection.token_url,
                    refresh_token=refresh_token,
                    client_id=connection.client_id,
                    client_secret=client_secret
                )

                if not success:
                    error_msg = result.get("error_description", result.get("error", "Token refresh failed"))
                    logger.error(f"Failed to refresh token: {error_msg}")
                    return False

                # Preserve old refresh_token if new one not provided
                new_refresh_token = result.get("refresh_token") or refresh_token

            # Store refreshed tokens
            await self.store_tokens(
                org_id=connection.org_id,
                connection_name=connection_name,
                access_token=result["access_token"],
                refresh_token=new_refresh_token,
                expires_at=result["expires_at"],
                token_type=result["token_type"],
                updated_by="system"
            )

            logger.info(f"Successfully refreshed token for {connection_name}")
            return True

        except Exception as e:
            logger.error(f"Error refreshing token for {connection_name}: {e}", exc_info=True)
            return False

    async def update_connection_status(
        self,
        org_id: str,
        connection_name: str,
        status: str,
        status_message: str | None = None,
        expires_at: datetime | None = None,
        last_refresh_at: datetime | None = None
    ) -> bool:
        """
        Update OAuth connection status

        Args:
            org_id: Organization ID
            connection_name: Connection name
            status: New status
            status_message: Optional status message
            expires_at: Optional new expiration time
            last_refresh_at: Optional last refresh timestamp

        Returns:
            True if updated successfully
        """
        oauth_rowkey = f"oauth:{connection_name}"
        oauth_entity = await self.config_table.get_entity(org_id, oauth_rowkey)

        if not oauth_entity:
            logger.warning(f"OAuth connection not found for status update: {connection_name}")
            return False

        oauth_entity['Status'] = status
        if status_message is not None:
            oauth_entity['StatusMessage'] = status_message
        if expires_at is not None:
            oauth_entity['ExpiresAt'] = expires_at.isoformat()
        oauth_entity['UpdatedAt'] = datetime.utcnow().isoformat()

        await self.config_table.upsert_entity(oauth_entity)
        logger.info(f"Updated OAuth connection status: {connection_name} -> {status}")

        return True

    async def run_refresh_job(
        self,
        trigger_type: str = "automatic",
        trigger_user: str | None = None,
        refresh_threshold_minutes: int | None = None
    ) -> dict:
        """
        Run the OAuth token refresh job

        This method contains the shared logic for refreshing expiring OAuth tokens.
        Can be called by both the timer trigger and HTTP endpoint.

        Args:
            trigger_type: Type of trigger ("automatic" or "manual")
            trigger_user: Email of user who triggered (for manual triggers)
            refresh_threshold_minutes: Override threshold in minutes (default: 30 for automatic, None for manual to refresh all)

        Returns:
            Dictionary with job results including:
            - total_connections: Total OAuth connections found
            - needs_refresh: Connections that need refresh
            - refreshed_successfully: Successfully refreshed count
            - refresh_failed: Failed refresh count
            - errors: List of error details
            - duration_seconds: Job duration
        """
        from datetime import timedelta

        start_time = datetime.utcnow()

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
            global_connections = await self.list_connections("GLOBAL", include_global=False)
            all_connections.extend(global_connections)

            results["total_connections"] = len(all_connections)
            logger.info(f"Found {len(all_connections)} total OAuth connections")

            # Filter connections that need refresh
            now = datetime.utcnow()

            # Determine refresh threshold
            # Default: 30 minutes for automatic, no threshold (refresh all completed) for manual
            if refresh_threshold_minutes is not None:
                refresh_threshold = now + timedelta(minutes=refresh_threshold_minutes)
                logger.info(f"Using custom refresh threshold: {refresh_threshold_minutes} minutes")
            elif trigger_type == "automatic":
                refresh_threshold = now + timedelta(minutes=30)
                logger.info("Using automatic refresh threshold: 30 minutes")
            else:
                # Manual trigger with no threshold - refresh all completed connections
                refresh_threshold = None
                logger.info("Manual trigger: refreshing all completed connections")

            connections_to_refresh = []
            for conn in all_connections:
                # Only refresh completed connections with tokens
                if conn.status != "completed":
                    continue

                # Check if token expires soon (or refresh all if no threshold)
                if refresh_threshold is None:
                    # Manual trigger with no threshold - refresh all completed connections
                    connections_to_refresh.append(conn)
                elif conn.expires_at and conn.expires_at <= refresh_threshold:
                    connections_to_refresh.append(conn)

            results["needs_refresh"] = len(connections_to_refresh)
            logger.info(f"Found {len(connections_to_refresh)} connections needing refresh")

            # Refresh each connection
            for connection in connections_to_refresh:
                try:
                    # Use the centralized refresh_token method
                    success = await self.refresh_token(
                        org_id=connection.org_id,
                        connection_name=connection.connection_name
                    )

                    if success:
                        results["refreshed_successfully"] += 1
                        logger.info(f"Successfully refreshed: {connection.connection_name}")
                    else:
                        results["refresh_failed"] += 1
                        logger.error(f"Failed to refresh: {connection.connection_name}")

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
                        await self.update_connection_status(
                            org_id=connection.org_id,
                            connection_name=connection.connection_name,
                            status="failed",
                            status_message=f"{trigger_type.capitalize()} refresh failed: {str(e)}"
                        )
                    except Exception as status_error:
                        logger.error(f"Could not update status: {status_error}")

            # Calculate duration
            end_time = datetime.utcnow()
            duration_seconds = (end_time - start_time).total_seconds()
            results["duration_seconds"] = duration_seconds

            # Store job status in Config table
            job_status_entity = {
                "PartitionKey": "SYSTEM",
                "RowKey": "jobstatus:TokenRefreshJob",
                "StartTime": start_time.isoformat(),
                "EndTime": end_time.isoformat(),
                "DurationSeconds": duration_seconds,
                "Status": "completed",
                "TriggerType": trigger_type,
                "TotalConnections": results["total_connections"],
                "NeedsRefresh": results["needs_refresh"],
                "RefreshedSuccessfully": results["refreshed_successfully"],
                "RefreshFailed": results["refresh_failed"],
                "Errors": json.dumps(results["errors"]) if results["errors"] else None
            }

            if trigger_user:
                job_status_entity["TriggerUser"] = trigger_user

            await self.config_table.upsert_entity(job_status_entity)

            # Log summary
            logger.info(
                f"{trigger_type.capitalize()} OAuth token refresh completed in {duration_seconds:.2f}s: "
                f"Total={results['total_connections']}, "
                f"NeedsRefresh={results['needs_refresh']}, "
                f"Success={results['refreshed_successfully']}, "
                f"Failed={results['refresh_failed']}"
            )

            return results

        except Exception as e:
            logger.error(f"OAuth refresh job failed: {str(e)}", exc_info=True)

            # Store failed job status
            end_time = datetime.utcnow()
            duration_seconds = (end_time - start_time).total_seconds()

            job_status_entity = {
                "PartitionKey": "SYSTEM",
                "RowKey": "jobstatus:TokenRefreshJob",
                "StartTime": start_time.isoformat(),
                "EndTime": end_time.isoformat(),
                "DurationSeconds": duration_seconds,
                "Status": "failed",
                "TriggerType": trigger_type,
                "ErrorMessage": str(e),
                "TotalConnections": 0,
                "NeedsRefresh": 0,
                "RefreshedSuccessfully": 0,
                "RefreshFailed": 0,
                "Errors": None
            }

            if trigger_user:
                job_status_entity["TriggerUser"] = trigger_user

            try:
                await self.config_table.upsert_entity(job_status_entity)
            except Exception:
                pass

            raise
