"""Password hashing with stdlib scrypt.

Hashes are stored as ``scrypt$n$r$p$<salt>$<hash>`` (urlsafe base64), so the
cost parameters can be raised later without invalidating existing hashes.
Hashing is CPU-bound, so it runs in a worker thread to keep the event loop free.
"""

import asyncio
import base64
import hashlib
import hmac
import secrets

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 64
SALT_BYTES = 16
SCHEME = "scrypt"


def _b64encode(raw: bytes) -> str:
    """Encode bytes as unpadded urlsafe base64.

    Args:
        raw: Bytes to encode.

    Returns:
        Encoded string.
    """
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64decode(value: str) -> bytes:
    """Decode unpadded urlsafe base64.

    Args:
        value: Encoded string.

    Returns:
        Decoded bytes.
    """
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _derive(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    """Derive the scrypt key for a password.

    Args:
        password: Plain-text password.
        salt: Random salt.
        n: CPU/memory cost.
        r: Block size.
        p: Parallelization.

    Returns:
        Derived key bytes.
    """
    return hashlib.scrypt(
        password.encode(),
        salt=salt,
        n=n,
        r=r,
        p=p,
        maxmem=128 * n * r * p * 2,
        dklen=SCRYPT_DKLEN,
    )


def hash_password_sync(password: str) -> str:
    """Hash a password (blocking).

    Args:
        password: Plain-text password.

    Returns:
        Encoded hash string.
    """
    salt = secrets.token_bytes(SALT_BYTES)
    derived = _derive(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    return (
        f"{SCHEME}${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}"
        f"${_b64encode(salt)}${_b64encode(derived)}"
    )


def verify_password_sync(password: str, encoded: str) -> bool:
    """Check a password against an encoded hash (blocking).

    Args:
        password: Plain-text password.
        encoded: Hash produced by ``hash_password_sync``.

    Returns:
        True if the password matches; False for a mismatch or malformed hash.
    """
    try:
        scheme, n, r, p, salt, expected = encoded.split("$")
        if scheme != SCHEME:
            return False
        derived = _derive(password, _b64decode(salt), int(n), int(r), int(p))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(derived, _b64decode(expected))


async def hash_password(password: str) -> str:
    """Hash a password without blocking the event loop.

    Args:
        password: Plain-text password.

    Returns:
        Encoded hash string.
    """
    return await asyncio.to_thread(hash_password_sync, password)


async def verify_password(password: str, encoded: str) -> bool:
    """Verify a password without blocking the event loop.

    Args:
        password: Plain-text password.
        encoded: Stored hash.

    Returns:
        True if the password matches.
    """
    return await asyncio.to_thread(verify_password_sync, password, encoded)


# Compared against when the user does not exist, so a login for an unknown
# account takes as long as one with a wrong password.
DUMMY_PASSWORD_HASH = hash_password_sync(secrets.token_urlsafe(16))
