"""
Secrets SDK Module

Provides secret management using Azure Key Vault.
Uses the current execution context to access org-scoped secrets.

Usage:
    from bifrost import secrets
    
    # Get secret from Key Vault
    api_key = await secrets.get("api_key")
"""

from ._context import _get_context


class secrets:
    """Secret management SDK."""
    
    @staticmethod
    async def get(key: str) -> str:
        """
        Get secret from Azure Key Vault.
        
        Secrets are scoped to organization: {org_id}--{key}
        
        Args:
            key: Secret key (e.g., "msgraph_client_secret")
            
        Returns:
            Secret value
            
        Raises:
            KeyError: If secret not found
            RuntimeError: If no execution context is available
            
        Example:
            # Get API key from Key Vault
            api_key = await secrets.get("api_key")
        """
        context = _get_context()
        return await context.get_secret(key)
