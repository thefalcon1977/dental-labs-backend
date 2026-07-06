"""Password hashing utilities for local authentication."""

import hashlib
import hmac
import secrets
from typing import Final

ALGORITHM: Final[str] = "pbkdf2_sha256"
ITERATIONS: Final[int] = 600_000
SALT_BYTES: Final[int] = 16


def hash_password(password: str) -> str:
    """Hash a plaintext password using PBKDF2-HMAC-SHA256.

    Args:
        password: Plaintext password to hash.

    Returns:
        Encoded password hash string.
    """
    salt = secrets.token_hex(SALT_BYTES)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        ITERATIONS,
    ).hex()
    return f"{ALGORITHM}${ITERATIONS}${salt}${password_hash}"


def verify_password(password: str, encoded_hash: str) -> bool:
    """Verify a plaintext password against an encoded hash.

    Args:
        password: Plaintext password to verify.
        encoded_hash: Encoded hash produced by hash_password.

    Returns:
        True when the password matches, False otherwise.
    """
    try:
        algorithm, iterations_value, salt, expected_hash = encoded_hash.split("$", 3)
        iterations = int(iterations_value)
    except (ValueError, TypeError):
        return False

    if algorithm != ALGORITHM:
        return False

    actual_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return hmac.compare_digest(actual_hash, expected_hash)


__all__ = [
    "hash_password",
    "verify_password",
]
