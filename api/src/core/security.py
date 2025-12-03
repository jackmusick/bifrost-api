"""
Security Utilities

Password hashing and JWT token handling using industry-standard libraries.
Based on FastAPI's official security tutorial patterns.

Uses pwdlib (modern replacement for unmaintained passlib) for password hashing.
"""

import base64
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher

from src.config import get_settings

# Password hashing using pwdlib with bcrypt
# This is the modern replacement for passlib, recommended by FastAPI
# We explicitly use BcryptHasher to avoid requiring argon2 dependency
password_hash = PasswordHash((BcryptHasher(),))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: The password to verify
        hashed_password: The hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password string
    """
    return password_hash.hash(password)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary of claims to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    settings = get_settings()

    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )

    return encoded_jwt


def create_refresh_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None
) -> str:
    """
    Create a JWT refresh token.

    Refresh tokens have longer expiration and are used to obtain new access tokens.

    Args:
        data: Dictionary of claims to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    settings = get_settings()

    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days
        )

    to_encode.update({
        "exp": expire,
        "type": "refresh"  # Mark as refresh token
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )

    return encoded_jwt


def decode_token(token: str) -> dict[str, Any] | None:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string to decode

    Returns:
        Decoded token payload or None if invalid/expired
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def create_mfa_token(user_id: str, purpose: str = "mfa_verify") -> str:
    """
    Create a short-lived token for MFA verification step.

    This token is returned after password verification and must be
    provided along with the MFA code to complete login.

    Args:
        user_id: User ID
        purpose: Token purpose (mfa_verify, mfa_setup)

    Returns:
        Encoded JWT token string
    """
    settings = get_settings()

    expire = datetime.now(timezone.utc) + timedelta(minutes=5)

    to_encode = {
        "sub": user_id,
        "type": purpose,
        "exp": expire,
    }

    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_mfa_token(token: str, expected_purpose: str = "mfa_verify") -> dict[str, Any] | None:
    """
    Decode and validate an MFA token.

    Args:
        token: JWT token string to decode
        expected_purpose: Expected token purpose

    Returns:
        Decoded token payload or None if invalid/expired/wrong type
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        if payload.get("type") != expected_purpose:
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# =============================================================================
# Secret Encryption (for storing secrets in database)
# =============================================================================


def _get_fernet_key() -> bytes:
    """
    Derive a Fernet-compatible key from the application secret.

    Returns:
        32-byte key suitable for Fernet encryption
    """
    settings = get_settings()

    # Use PBKDF2 to derive a key from the secret
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"bifrost_secrets_v1",  # Fixed salt for consistency
        iterations=100000,
    )

    key = base64.urlsafe_b64encode(kdf.derive(settings.secret_key.encode()))
    return key


def encrypt_secret(plaintext: str) -> str:
    """
    Encrypt a secret value for storage in the database.

    Args:
        plaintext: The secret value to encrypt

    Returns:
        Base64-encoded encrypted value
    """
    key = _get_fernet_key()
    f = Fernet(key)
    encrypted = f.encrypt(plaintext.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_secret(encrypted: str) -> str:
    """
    Decrypt a secret value from the database.

    Args:
        encrypted: Base64-encoded encrypted value

    Returns:
        Decrypted plaintext value
    """
    key = _get_fernet_key()
    f = Fernet(key)
    encrypted_bytes = base64.urlsafe_b64decode(encrypted.encode())
    decrypted = f.decrypt(encrypted_bytes)
    return decrypted.decode()
