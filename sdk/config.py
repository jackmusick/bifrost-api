"""
Configuration SDK Module

Provides configuration management with automatic secret resolution.
Uses the current execution context to access org-scoped configuration.

Usage:
    from bifrost import config
    
    # Get config value with automatic secret resolution
    api_key = config.get("api_key")
    
    # Get with default value
    timeout = config.get("timeout", default=30)
    
    # Check if config exists
    if config.has("api_key"):
        ...
"""

from typing import Any
from ._context import _get_context


class config:
    """Configuration management SDK."""
    
    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """
        Get configuration value with automatic secret resolution.
        
        This method automatically resolves secret references from Azure Key Vault
        based on the configuration type. If the config type is 'secret_ref', it
        retrieves the actual secret value from Key Vault using org-scoped → global fallback.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value (with secret resolved if secret_ref type)
            
        Raises:
            KeyError: If secret reference cannot be resolved from Key Vault
            RuntimeError: If no execution context is available
            
        Example:
            # Get API key (automatically resolves from Key Vault if secret_ref)
            api_key = config.get("api_key")
            
            # Get with default
            timeout = config.get("timeout", default=30)
        """
        context = _get_context()
        return context.get_config(key, default)
    
    @staticmethod
    def has(key: str) -> bool:
        """
        Check if configuration key exists.
        
        Args:
            key: Configuration key
            
        Returns:
            True if configuration key exists, False otherwise
            
        Raises:
            RuntimeError: If no execution context is available
            
        Example:
            if config.has("api_key"):
                api_key = config.get("api_key")
        """
        context = _get_context()
        return context.has_config(key)
