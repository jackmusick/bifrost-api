"""
TOTP Helper for Testing

Provides utilities for generating TOTP codes during E2E testing.
"""

import pyotp


def generate_totp_code(secret: str) -> str:
    """
    Generate a valid 6-digit TOTP code from a base32 secret.

    Args:
        secret: Base32-encoded TOTP secret from MFA setup

    Returns:
        6-digit TOTP code as string
    """
    return pyotp.TOTP(secret).now()


def create_totp(secret: str) -> pyotp.TOTP:
    """
    Create a TOTP instance for repeated code generation.

    Args:
        secret: Base32-encoded TOTP secret from MFA setup

    Returns:
        pyotp.TOTP instance
    """
    return pyotp.TOTP(secret)


def verify_totp_code(secret: str, code: str) -> bool:
    """
    Verify a TOTP code against a secret.

    Args:
        secret: Base32-encoded TOTP secret
        code: 6-digit TOTP code to verify

    Returns:
        True if valid, False otherwise
    """
    return pyotp.TOTP(secret).verify(code)
