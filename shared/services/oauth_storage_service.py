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
        1. Create OAuthConnection entity in OAuthConnections table
        2. Store client_secret in Config table (Type="secret_ref")
        3. Store metadata in Config table (Type="json")

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

        # Generate config references
        client_secret_ref = f"oauth_{request.connection_name}_client_secret"
        oauth_response_ref = f"oauth_{request.connection_name}_oauth_response"

        # Create OAuth connection model
        # Note: redirect_uri should point to the UI callback page, not the API
        connection = OAuthConnection(
            org_id=org_id,
            connection_name=request.connection_name,
            description=request.description,
            oauth_flow_type=request.oauth_flow_type,
            client_id=request.client_id,
            client_secret_ref=client_secret_ref,
            oauth_response_ref=oauth_response_ref,
            authorization_url=request.authorization_url,
            token_url=request.token_url,
            scopes=request.scopes,
            redirect_uri=f"/oauth/callback/{request.connection_name}",  # UI route, not /api/
            status="not_connected",
            created_by=created_by,
            created_at=now,
            updated_at=now,
            expires_at=None
        )

        # Convert to Table Storage entity
        entity = connection.model_dump()
        entity["PartitionKey"] = org_id
        entity["RowKey"] = request.connection_name

        # Store client_secret in Key Vault and Config table (Type="secret_ref") if provided
        # Value is the Key Vault secret name
        # Note: Client secret is optional for PKCE flow
        if request.client_secret:
            try:
                keyvault = KeyVaultClient()
                assert keyvault._client is not None, "KeyVault client is None"
                # Generate secret name using new bifrost_{scope}_oauth_{name}_{type}_{uuid} convention
                keyvault_secret_name = generate_oauth_secret_name(
                    org_id,
                    request.connection_name,
                    "client-secret"
                )

                keyvault._client.set_secret(keyvault_secret_name, request.client_secret)
                logger.info(f"Stored client_secret in Key Vault: {keyvault_secret_name}")
            except ValueError as e:
                # KeyVault not configured (e.g., in test environment)
                logger.warning(f"KeyVault not available for client_secret storage: {e}")
                logger.warning("Client secret will not be persisted - OAuth connection may not work in production")
            except Exception as e:
                logger.error(f"Failed to store client_secret in Key Vault: {e}")
                raise

            client_secret_config = {
                "PartitionKey": org_id,
                "RowKey": f"config:oauth_{request.connection_name}_client_secret",
                "Value": keyvault_secret_name,
                "Type": "secret_ref",
                "Description": f"OAuth client secret for {request.connection_name}",
                "UpdatedAt": now.isoformat(),
                "UpdatedBy": created_by
            }
            await self.config_table.insert_entity(client_secret_config)
            logger.info(f"Stored client_secret config reference for {request.connection_name}")
        else:
            logger.info(f"No client secret provided (PKCE flow) for {request.connection_name}")

        # Store metadata in Config table (Type="json")
        metadata = {
            "oauth_flow_type": request.oauth_flow_type,
            "client_id": request.client_id,
            "authorization_url": request.authorization_url,
            "token_url": request.token_url,
            "scopes": request.scopes,
            "redirect_uri": connection.redirect_uri,
            "status": connection.status
        }
        metadata_config = {
            "PartitionKey": org_id,
            "RowKey": f"config:oauth_{request.connection_name}_metadata",
            "Value": json.dumps(metadata),
            "Type": "json",
            "Description": f"OAuth metadata for {request.connection_name}",
            "UpdatedAt": now.isoformat(),
            "UpdatedBy": created_by
        }
        await self.config_table.insert_entity(metadata_config)
        logger.info(f"Stored metadata config for {request.connection_name}")

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
        metadata_rowkey = f"config:oauth_{connection_name}_metadata"

        try:
            # First, try org-specific metadata
            metadata_entity = await self.config_table.get_entity(org_id, metadata_rowkey)

            if metadata_entity:
                logger.debug(f"Found org-specific OAuth connection metadata: {connection_name} for org {org_id}")
                return await self._load_oauth_connection_from_config(org_id, connection_name)

            # If not found, try GLOBAL metadata
            if org_id != "GLOBAL":
                global_metadata_entity = await self.config_table.get_entity("GLOBAL", metadata_rowkey)

                if global_metadata_entity:
                    logger.debug(f"Found GLOBAL OAuth connection metadata: {connection_name}")
                    return await self._load_oauth_connection_from_config("GLOBAL", connection_name)
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
            # Query metadata configs for org
            # Note: Azure Table Storage doesn't support startswith/endswith in filter syntax
            # We'll query all configs for org and filter in Python
            org_query_filter = f"PartitionKey eq '{org_id}' and RowKey ge 'config:oauth_' and RowKey lt 'config:oauth~'"
            org_metadata_entities = list(await self.config_table.query_entities(filter=org_query_filter))

            # Process org-specific connections (filter for _metadata suffix)
            for metadata_entity in org_metadata_entities:
                if metadata_entity['RowKey'].endswith('_metadata'):
                    connection_name = metadata_entity['RowKey'].replace('config:oauth_', '').replace('_metadata', '')
                    connection = await self._load_oauth_connection_from_config(org_id, connection_name)
                    if connection:
                        connections.append(connection)

            # Add GLOBAL connections if requested
            if include_global and org_id != "GLOBAL":
                global_query_filter = "PartitionKey eq 'GLOBAL' and RowKey ge 'config:oauth_' and RowKey lt 'config:oauth~'"
                global_metadata_entities = list(await self.config_table.query_entities(filter=global_query_filter))

                for metadata_entity in global_metadata_entities:
                    if metadata_entity['RowKey'].endswith('_metadata'):
                        connection_name = metadata_entity['RowKey'].replace('config:oauth_', '').replace('_metadata', '')
                        connection = await self._load_oauth_connection_from_config("GLOBAL", connection_name)
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
        # Retrieve current metadata
        metadata_rowkey = f"config:oauth_{connection_name}_metadata"
        metadata_entity = await self.config_table.get_entity(org_id, metadata_rowkey)

        if not metadata_entity:
            logger.warning(f"OAuth connection not found for update: {connection_name}")
            return None

        # Retrieve and parse current metadata
        current_metadata = json.loads(metadata_entity['Value'])

        # Update fields if provided
        if request.client_id is not None:
            current_metadata['client_id'] = request.client_id
        if request.authorization_url is not None:
            current_metadata['authorization_url'] = request.authorization_url
        if request.token_url is not None:
            current_metadata['token_url'] = request.token_url
        if request.scopes is not None:
            current_metadata['scopes'] = request.scopes

        # Mark as not connected if significant changes occurred
        if request.client_id or request.client_secret or request.authorization_url or request.token_url:
            current_metadata['status'] = 'not_connected'

        # Update metadata config
        metadata_config = {
            "PartitionKey": org_id,
            "RowKey": metadata_rowkey,
            "Value": json.dumps(current_metadata),
            "Type": "json",
            "Description": f"OAuth metadata for {connection_name}",
            "UpdatedAt": datetime.utcnow().isoformat(),
            "UpdatedBy": updated_by
        }

        await self.config_table.upsert_entity(metadata_config)
        logger.info(f"Updated OAuth connection metadata: {connection_name}")

        return await self._load_oauth_connection_from_config(org_id, connection_name)

    async def _load_oauth_connection_from_config(
        self,
        org_id: str,
        connection_name: str
    ) -> OAuthConnection | None:
        """
        Reconstruct OAuthConnection from Config table entries

        Args:
            org_id: Organization ID
            connection_name: Connection name

        Returns:
            Reconstructed OAuthConnection or None if not found
        """
        metadata_rowkey = f"config:oauth_{connection_name}_metadata"

        try:
            # Fetch metadata
            metadata_entity = await self.config_table.get_entity(org_id, metadata_rowkey)
            if not metadata_entity:
                return None

            metadata = json.loads(metadata_entity['Value'])

            # Use short reference names (not Key Vault secret names)
            # These are used to construct the config table RowKeys
            client_secret_ref = f"oauth_{connection_name}_client_secret"
            oauth_response_ref = f"oauth_{connection_name}_oauth_response"

            now = datetime.utcnow()

            # Parse expires_at from metadata if available
            expires_at_str = metadata.get('expires_at')
            expires_at = None
            if expires_at_str:
                try:
                    expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass

            # Reconstruct OAuthConnection
            return OAuthConnection(
                org_id=org_id,
                connection_name=connection_name,
                description=metadata.get('description'),
                oauth_flow_type=metadata.get('oauth_flow_type', 'standard'),
                client_id=metadata['client_id'],
                client_secret_ref=client_secret_ref,
                oauth_response_ref=oauth_response_ref,
                authorization_url=metadata['authorization_url'],
                token_url=metadata['token_url'],
                scopes=metadata.get('scopes', ''),
                redirect_uri=metadata.get('redirect_uri', f"/oauth/callback/{connection_name}"),
                status=metadata.get('status', 'not_connected'),
                status_message=metadata.get('status_message'),
                expires_at=expires_at,
                created_at=now,  # Default to current time
                created_by=metadata.get('created_by', 'system'),
                updated_at=now
            )

        except Exception as e:
            logger.warning(f"Error loading OAuth connection: {e}")
            return None

    async def _fetch_config_secret(
        self,
        org_id: str,
        rowkey: str
    ) -> str | None:
        """
        Fetch secret reference from Config table

        Args:
            org_id: Organization ID
            rowkey: Row key to look up

        Returns:
            Secret reference or None
        """
        try:
            secret_entity = await self.config_table.get_entity(org_id, rowkey)
            return secret_entity.get('Value') if secret_entity else None
        except Exception:
            return None

    async def delete_connection(
        self,
        org_id: str,
        connection_name: str
    ) -> bool:
        """
        Delete an OAuth connection and its associated configs

        Args:
            org_id: Organization ID
            connection_name: Connection name

        Returns:
            True if deleted, False if not found
        """
        # Delete secrets from Key Vault
        try:
            async with KeyVaultClient() as keyvault:
                secret_keys = [
                    f"oauth-{connection_name}-client-secret",
                    f"oauth-{connection_name}-response"
                ]

                for secret_key in secret_keys:
                    try:
                        await keyvault.delete_secret(org_id, secret_key)
                        logger.debug(f"Deleted Key Vault secret: {org_id}--{secret_key}")
                    except Exception as e:
                        logger.debug(f"Could not delete Key Vault secret {org_id}--{secret_key}: {e}")
        except ValueError as e:
            logger.warning(f"KeyVault not available for secret deletion: {e}")
            logger.debug("Skipping Key Vault secret cleanup")

        # Delete associated configs
        config_keys = [
            f"config:oauth_{connection_name}_client_secret",
            f"config:oauth_{connection_name}_oauth_response",
            f"config:oauth_{connection_name}_metadata"
        ]

        for config_key in config_keys:
            try:
                await self.config_table.delete_entity(org_id, config_key)
                logger.debug(f"Deleted config: {config_key}")
            except Exception as e:
                logger.warning(f"Failed to delete config {config_key}: {e}")

        logger.info(f"Deleted OAuth connection and configs: {connection_name}")
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
        Store OAuth tokens in Config table

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

        # Store OAuth response JSON in Key Vault
        try:
            keyvault = KeyVaultClient()
            assert keyvault._client is not None, "KeyVault client is None"

            # Check if we have an existing oauth_response config to reuse the secret name
            oauth_response_rowkey = f"config:oauth_{connection_name}_oauth_response"
            existing_config = None
            try:
                existing_config = await self.config_table.get_entity(org_id, oauth_response_rowkey)
            except Exception:
                # No existing config, will create new secret
                pass

            if existing_config and existing_config.get('Type') == 'secret_ref':
                # Reuse existing secret name (creates new version in Key Vault)
                keyvault_secret_name = existing_config['Value']
                logger.info(f"Updating existing OAuth token secret '{keyvault_secret_name}' for {connection_name}")
            else:
                # Generate new secret name using bifrost-{scope}-oauth-{name}-{type}-{uuid} convention
                keyvault_secret_name = generate_oauth_secret_name(
                    org_id,
                    connection_name,
                    "response"
                )
                logger.info(f"Creating new OAuth token secret for {connection_name}")

            keyvault._client.set_secret(keyvault_secret_name, json.dumps(oauth_response))
            logger.info(f"Stored OAuth tokens in Key Vault: {keyvault_secret_name}")
        except ValueError as e:
            logger.warning(f"KeyVault not available for OAuth token storage: {e}")
        except Exception as e:
            logger.error(f"Failed to store OAuth tokens in Key Vault: {e}")
            raise

        # Store in Config table (Type="secret_ref")
        oauth_response_config = {
            "PartitionKey": org_id,
            "RowKey": f"config:oauth_{connection_name}_oauth_response",
            "Value": keyvault_secret_name,
            "Type": "secret_ref",
            "Description": f"OAuth tokens for {connection_name}",
            "UpdatedAt": datetime.utcnow().isoformat(),
            "UpdatedBy": updated_by
        }

        await self.config_table.upsert_entity(oauth_response_config)
        logger.info(f"Stored OAuth tokens config reference for {connection_name}")

        # Update connection metadata to reflect new status
        metadata_rowkey = f"config:oauth_{connection_name}_metadata"
        metadata_entity = await self.config_table.get_entity(org_id, metadata_rowkey)

        if metadata_entity:
            current_metadata = json.loads(metadata_entity['Value'])
            current_metadata['status'] = 'completed'
            current_metadata['expires_at'] = expires_at.isoformat()
            current_metadata['last_refresh_at'] = datetime.utcnow().isoformat()

            metadata_config = {
                "PartitionKey": org_id,
                "RowKey": metadata_rowkey,
                "Value": json.dumps(current_metadata),
                "Type": "json",
                "Description": f"OAuth metadata for {connection_name}",
                "UpdatedAt": datetime.utcnow().isoformat(),
                "UpdatedBy": updated_by
            }

            await self.config_table.upsert_entity(metadata_config)

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

            # Get client secret if exists
            client_secret = None
            if connection.client_secret_ref:
                try:
                    # client_secret_ref is the short name like "oauth_{name}_client_secret"
                    # Config table RowKey is "config:oauth_{name}_client_secret"
                    client_secret_key = f"config:{connection.client_secret_ref}"

                    logger.info(f"Looking up client secret with key: {client_secret_key}")
                    client_secret_config = await self.config_table.get_entity(
                        connection.org_id,
                        client_secret_key
                    )

                    if client_secret_config:
                        keyvault_secret_name = client_secret_config.get("Value")
                        if keyvault_secret_name:
                            from shared.keyvault import KeyVaultClient
                            logger.info(f"Retrieving client secret from Key Vault: {keyvault_secret_name}")
                            async with KeyVaultClient() as keyvault:
                                # Extract just the secret key (without org prefix)
                                parts = keyvault_secret_name.split("--", 1)
                                secret_key = parts[1] if len(parts) == 2 else keyvault_secret_name
                                client_secret = await keyvault.get_secret(connection.org_id, secret_key)
                                logger.info("Successfully retrieved client secret")
                        else:
                            logger.warning("Client secret config found but missing Value field")
                    else:
                        logger.warning(f"Client secret config not found for key: {client_secret_key}")
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

                # Get OAuth response config to retrieve current tokens
                # Config table uses RowKey: config:oauth_{connection_name}_oauth_response
                oauth_response_key = f"config:oauth_{connection_name}_oauth_response"
                oauth_response_config = await self.config_table.get_entity(
                    connection.org_id,
                    oauth_response_key
                )

                if not oauth_response_config:
                    logger.error(f"OAuth response config not found: {oauth_response_key}")
                    return False

                # Get Key Vault secret name from config
                keyvault_secret_name = oauth_response_config.get("Value")
                if not keyvault_secret_name:
                    logger.error("OAuth response config missing Key Vault secret name")
                    return False

                # Retrieve current OAuth tokens from Key Vault
                async with KeyVaultClient() as keyvault:
                    # Extract just the secret key (without org prefix)
                    parts = keyvault_secret_name.split("--", 1)
                    secret_key = parts[1] if len(parts) == 2 else keyvault_secret_name
                    oauth_response_json = await keyvault.get_secret(connection.org_id, secret_key)
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

            # Update connection status
            await self.update_connection_status(
                org_id=connection.org_id,
                connection_name=connection_name,
                status="completed",
                status_message="Token refreshed successfully"
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
        metadata_rowkey = f"config:oauth_{connection_name}_metadata"
        metadata_entity = await self.config_table.get_entity(org_id, metadata_rowkey)

        if not metadata_entity:
            logger.warning(f"OAuth connection not found for status update: {connection_name}")
            return False

        current_metadata = json.loads(metadata_entity['Value'])

        current_metadata['status'] = status
        if status_message is not None:
            current_metadata['status_message'] = status_message
        if expires_at is not None:
            current_metadata['expires_at'] = expires_at.isoformat()
        if last_refresh_at is not None:
            current_metadata['last_refresh_at'] = last_refresh_at.isoformat()
        current_metadata['updated_at'] = datetime.utcnow().isoformat()

        metadata_config = {
            "PartitionKey": org_id,
            "RowKey": metadata_rowkey,
            "Value": json.dumps(current_metadata),
            "Type": "json",
            "Description": f"OAuth metadata for {connection_name}",
            "UpdatedAt": datetime.utcnow().isoformat()
        }

        await self.config_table.upsert_entity(metadata_config)
        logger.info(f"Updated OAuth connection status: {connection_name} -> {status}")

        return True

    async def _update_metadata_config(
        self,
        org_id: str,
        connection_name: str,
        entity: dict,
        updated_by: str
    ):
        """Update metadata config when connection details change"""
        metadata = {
            "oauth_flow_type": entity["oauth_flow_type"],
            "client_id": entity["client_id"],
            "authorization_url": entity["authorization_url"],
            "token_url": entity["token_url"],
            "scopes": entity["scopes"],
            "redirect_uri": entity["redirect_uri"],
            "status": entity["status"]
        }

        metadata_config = {
            "PartitionKey": org_id,
            "RowKey": f"config:oauth_{connection_name}_metadata",
            "Value": json.dumps(metadata),
            "Type": "json",
            "Description": f"OAuth metadata for {connection_name}",
            "UpdatedAt": datetime.utcnow().isoformat(),
            "UpdatedBy": updated_by
        }

        await self.config_table.upsert_entity(metadata_config)

    def _entity_to_connection(self, entity: dict) -> OAuthConnection:
        """
        Convert Table Storage entity to OAuthConnection model

        Args:
            entity: Entity from Table Storage

        Returns:
            OAuthConnection model
        """
        # Parse datetime fields
        created_at = entity.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        updated_at = entity.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        elif updated_at is None:
            # Default to created_at if updated_at is missing
            updated_at = created_at if created_at else datetime.utcnow()

        expires_at = entity.get("expires_at")
        if expires_at and isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))

        last_refresh_at = entity.get("last_refresh_at")
        if last_refresh_at and isinstance(last_refresh_at, str):
            last_refresh_at = datetime.fromisoformat(last_refresh_at.replace("Z", "+00:00"))

        last_test_at = entity.get("last_test_at")
        if last_test_at and isinstance(last_test_at, str):
            last_test_at = datetime.fromisoformat(last_test_at.replace("Z", "+00:00"))

        # Parse required fields with assertions for type safety
        client_secret_ref = entity.get("client_secret_ref")
        assert client_secret_ref is not None, "client_secret_ref is required"
        oauth_response_ref = entity.get("oauth_response_ref")
        assert oauth_response_ref is not None, "oauth_response_ref is required"
        assert created_at is not None, "created_at is required"

        return OAuthConnection(
            org_id=entity["PartitionKey"],
            connection_name=entity["RowKey"],
            description=entity.get("description"),
            oauth_flow_type=entity["oauth_flow_type"],
            client_id=entity["client_id"],
            client_secret_ref=client_secret_ref,
            oauth_response_ref=oauth_response_ref,
            authorization_url=entity["authorization_url"],
            token_url=entity["token_url"],
            scopes=entity.get("scopes", ""),
            redirect_uri=entity["redirect_uri"],
            token_type=entity.get("token_type", "Bearer"),
            expires_at=expires_at,
            status=entity["status"],
            status_message=entity.get("status_message"),
            last_refresh_at=last_refresh_at,
            last_test_at=last_test_at,
            created_at=created_at,
            created_by=entity["created_by"],
            updated_at=updated_at
        )

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
