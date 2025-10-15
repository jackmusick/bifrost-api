"""
Mock Authentication Helpers for Testing

Provides reusable helpers to create mock authentication data for different user types:
- Platform Admin (GLOBAL scope access)
- Organization User (tied to specific organization)
- Function Key (system-to-system authentication)

These helpers generate the X-MS-CLIENT-PRINCIPAL header format that Azure Static Web Apps uses.
"""

import base64
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


class MockAuthHelper:
    """Helper class for creating mock authentication data for tests"""

    @staticmethod
    def create_platform_admin_principal(
        user_id: Optional[str] = None,
        email: str = "admin@test.com",
        name: str = "Test Platform Admin"
    ) -> str:
        """
        Create a base64-encoded X-MS-CLIENT-PRINCIPAL header for a platform admin.
        
        Platform admins have:
        - UserType: "PLATFORM"
        - IsPlatformAdmin: True
        - Can access GLOBAL scope and any org scope
        
        Args:
            user_id: Optional user ID (generates UUID if not provided)
            email: User email
            name: User display name
            
        Returns:
            Base64-encoded principal data for X-MS-CLIENT-PRINCIPAL header
        """
        if user_id is None:
            user_id = str(uuid.uuid4())
            
        principal_data = {
            "userId": user_id,
            "userDetails": email,
            "userRoles": ["anonymous"],
            "identityProvider": "aad"
        }
        
        return base64.b64encode(json.dumps(principal_data).encode('utf-8')).decode('utf-8')

    @staticmethod
    def create_org_user_principal(
        org_id: str,
        user_id: Optional[str] = None,
        email: str = "user@test.com",
        name: str = "Test Org User"
    ) -> str:
        """
        Create a base64-encoded X-MS-CLIENT-PRINCIPAL header for an organization user.
        
        Org users have:
        - UserType: "ORG"
        - IsPlatformAdmin: False
        - Fixed org_id (cannot override via headers)
        - Can only access their assigned org
        
        Args:
            org_id: Organization ID the user belongs to
            user_id: Optional user ID (generates UUID if not provided)
            email: User email
            name: User display name
            
        Returns:
            Base64-encoded principal data for X-MS-CLIENT-PRINCIPAL header
        """
        if user_id is None:
            user_id = str(uuid.uuid4())
            
        principal_data = {
            "userId": user_id,
            "userDetails": email,
            "userRoles": ["anonymous"],
            "identityProvider": "aad"
        }
        
        return base64.b64encode(json.dumps(principal_data).encode('utf-8')).decode('utf-8')

    @staticmethod
    def create_function_key_headers(
        org_id: Optional[str] = None,
        key_name: str = "test-key"
    ) -> Dict[str, str]:
        """
        Create headers for function key authentication.
        
        Function keys have:
        - is_function_key: True
        - user_id: "system"
        - Can set org_id via X-Organization-Id header (optional)
        - Admin privileges within specified scope
        
        Args:
            org_id: Optional organization ID for scoping
            key_name: Name of the function key
            
        Returns:
            Dictionary of headers for function key authentication
        """
        headers = {
            "x-functions-key": f"test-function-key-{key_name}",
            "Content-Type": "application/json"
        }
        
        if org_id:
            headers["X-Organization-Id"] = org_id
            
        return headers

    @staticmethod
    def create_anonymous_headers() -> Dict[str, str]:
        """
        Create headers for anonymous access (no authentication).
        
        Returns:
            Dictionary of headers for anonymous requests
        """
        return {
            "Content-Type": "application/json"
        }

    @staticmethod
    def create_user_with_roles_principal(
        org_id: str,
        roles: list,
        user_id: Optional[str] = None,
        email: str = "user@test.com",
        name: str = "Test User with Roles"
    ) -> str:
        """
        Create a base64-encoded X-MS-CLIENT-PRINCIPAL header for a user with specific roles.
        
        Args:
            org_id: Organization ID the user belongs to
            roles: List of role names the user has
            user_id: Optional user ID (generates UUID if not provided)
            email: User email
            name: User display name
            
        Returns:
            Base64-encoded principal data for X-MS-CLIENT-PRINCIPAL header
        """
        if user_id is None:
            user_id = str(uuid.uuid4())
            
        principal_data = {
            "auth_typ": "aad",
            "claims": [
                {"typ": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier", "val": user_id},
                {"typ": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress", "val": email},
                {"typ": "name", "val": name},
                {"typ": "http://schemas.microsoft.com/claims/authnclassreference", "val": "1"},
                {"typ": "http://schemas.microsoft.com/claims/authnmethodsreferences", "val": "pwd"},
                {"typ": "http://schemas.microsoft.com/claims/identityprovider", "val": "https://sts.windows.net/test-tenant-id/"},
                {"typ": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/upn", "val": email},
                {"typ": "http://schemas.microsoft.com/identity/claims/objectidentifier", "val": user_id},
                {"typ": "http://schemas.microsoft.com/claims/tenantid", "val": "test-tenant-id"},
                {"typ": "uti", "val": str(uuid.uuid4())},
                {"typ": "ver", "val": "2.0"}
            ],
            "name_typ": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
            "role_typ": "http://schemas.microsoft.com/ws/2008/06/identity/claims/role"
        }
        
        # Add role claims
        for role in roles:
            principal_data["claims"].append({
                "typ": "http://schemas.microsoft.com/ws/2008/06/identity/claims/role",
                "val": role
            })
        
        return base64.b64encode(json.dumps(principal_data).encode('utf-8')).decode('utf-8')


# Pre-configured test users for convenience
class TestUsers:
    """Pre-configured test users for common scenarios"""
    
    # Platform admin user
    PLATFORM_ADMIN = {
        "user_id": "admin-user-12345",
        "email": "admin@test.com",
        "name": "Test Platform Admin",
        "is_platform_admin": True,
        "org_id": None  # GLOBAL scope
    }
    
    # Organization user
    ORG_USER = {
        "user_id": "org-user-67890",
        "email": "user@test.com", 
        "name": "Test Org User",
        "is_platform_admin": False,
        "org_id": "test-org-12345"
    }
    
    # Second org user for multi-user tests
    ORG_USER_2 = {
        "user_id": "org-user-11111",
        "email": "user2@test.com",
        "name": "Test Org User 2", 
        "is_platform_admin": False,
        "org_id": "test-org-12345"
    }
    
    # User from different org for isolation tests
    OTHER_ORG_USER = {
        "user_id": "other-user-22222",
        "email": "other@test.com",
        "name": "Other Org User",
        "is_platform_admin": False,
        "org_id": "other-org-67890"
    }


# Convenience functions for common scenarios
def create_platform_admin_headers(org_id: Optional[str] = None) -> Dict[str, str]:
    """Create headers for platform admin authentication"""
    principal = MockAuthHelper.create_platform_admin_principal(
        user_id=TestUsers.PLATFORM_ADMIN["user_id"],
        email=TestUsers.PLATFORM_ADMIN["email"],
        name=TestUsers.PLATFORM_ADMIN["name"]
    )
    
    headers = {
        "X-MS-CLIENT-PRINCIPAL": principal,
        "Content-Type": "application/json"
    }
    
    if org_id:
        headers["X-Organization-Id"] = org_id
        
    return headers


def create_org_user_headers(org_id: Optional[str] = None) -> Dict[str, str]:
    """Create headers for organization user authentication"""
    if org_id is None:
        org_id = TestUsers.ORG_USER["org_id"]
    
    # Ensure org_id is a string for type safety
    org_id = str(org_id) if org_id else TestUsers.ORG_USER["org_id"]
        
    principal = MockAuthHelper.create_org_user_principal(
        org_id=org_id,
        user_id=TestUsers.ORG_USER["user_id"],
        email=TestUsers.ORG_USER["email"],
        name=TestUsers.ORG_USER["name"]
    )
    
    return {
        "X-MS-CLIENT-PRINCIPAL": principal,
        "Content-Type": "application/json"
    }


def create_function_key_headers(org_id: Optional[str] = None) -> Dict[str, str]:
    """Create headers for function key authentication"""
    return MockAuthHelper.create_function_key_headers(org_id=org_id)