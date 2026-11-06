"""OTP login session store in Redis.

Encapsulates Redis key layout, TTL, and serialization for OTP-pending sessions.
Design: docs/srs/otp-login-design-and-security.md
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, TypedDict

from config.logging import get_logger

from ..helpers.exceptions import OtpSessionInvalidError, RedisUnavailableError

logger = get_logger(__name__)

OTP_SESSION_KEY_PREFIX = "auth:otp_session:"
LAST_OTP_ISSUED_KEY_PREFIX = "auth:otp_last_issued:"


class OtpSessionPayload(TypedDict, total=False):
    """Payload stored under auth:otp_session:{session_id}."""

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str
    otp_hash: str
    attempts: int
    created_at: str
    user_id: str
    otp_issued_at: str
    phone: str


def _session_key(session_id: str) -> str:
    """Build Redis key for OTP session."""
    return f"{OTP_SESSION_KEY_PREFIX}{session_id}"


def _last_otp_issued_key(user_id: str) -> str:
    """Build Redis key for per-user last OTP issued lock."""
    return f"{LAST_OTP_ISSUED_KEY_PREFIX}{user_id}"


async def set_last_otp_issued(
    redis: Any,
    user_id: str,
    ttl_seconds: int,
) -> None:
    """Record that an OTP was issued for this user; blocks new login until TTL expires.

    Resend is gated separately by the session's otp_issued_at (per session_id).
    Call only when user_id is non-empty to avoid a shared key blocking all logins.

    Args:
        redis: Async Redis client.
        user_id: User identifier (e.g. Keycloak sub).
        ttl_seconds: TTL for the key (e.g. OTP_VALIDITY_SECONDS).

    Raises:
        RedisUnavailableError: If Redis is None or write fails.
    """
    if redis is None:
        raise RedisUnavailableError()
    if not user_id:
        return
    key = _last_otp_issued_key(user_id)
    try:
        await redis.set(key, "1", ex=ttl_seconds)
    except Exception as e:
        logger.warning(
            "OTP last-issued set failed",
            error=str(e),
            key_prefix=LAST_OTP_ISSUED_KEY_PREFIX,
        )
        raise RedisUnavailableError() from e


async def get_last_otp_issued_ttl(redis: Any, user_id: str) -> int | None:
    """Return remaining TTL in seconds for the per-user OTP lock, or None if no lock.

    Args:
        redis: Async Redis client.
        user_id: User identifier.

    Returns:
        Remaining seconds until lock expires, or None if key does not exist.

    Raises:
        RedisUnavailableError: If Redis is None.
    """
    if redis is None:
        raise RedisUnavailableError()
    key = _last_otp_issued_key(user_id)
    try:
        ttl = await redis.ttl(key)
    except Exception as e:
        logger.warning(
            "OTP last-issued TTL failed",
            error=str(e),
            key_prefix=LAST_OTP_ISSUED_KEY_PREFIX,
        )
        raise RedisUnavailableError() from e
    if ttl < 0:
        return None
    return ttl


async def delete_last_otp_issued(redis: Any, user_id: str) -> None:
    """Remove the per-user OTP issued lock (e.g. after successful verification).

    Args:
        redis: Async Redis client.
        user_id: User identifier (e.g. Keycloak sub).

    Raises:
        RedisUnavailableError: If Redis is None.
    """
    if redis is None:
        raise RedisUnavailableError()
    if not user_id:
        return
    key = _last_otp_issued_key(user_id)
    try:
        await redis.delete(key)
    except Exception as e:
        logger.warning(
            "OTP last-issued delete failed",
            error=str(e),
            key_prefix=LAST_OTP_ISSUED_KEY_PREFIX,
        )
        raise RedisUnavailableError() from e


async def create_session(
    redis: Any,
    session_id: str,
    payload: OtpSessionPayload,
    ttl_seconds: int,
) -> None:
    """Store OTP-pending session in Redis.

    Args:
        redis: Async Redis client (decode_responses=True).
        session_id: Opaque session identifier.
        payload: Session data (tokens, otp_hash, attempts=0, created_at, user_id).
        ttl_seconds: TTL for the key in seconds.

    Raises:
        RedisUnavailableError: If Redis is None or write fails.
    """
    if redis is None:
        raise RedisUnavailableError()
    key = _session_key(session_id)
    value = json.dumps(payload)
    try:
        await redis.set(key, value, ex=ttl_seconds)
    except Exception as e:
        logger.warning(
            "OTP session store create failed",
            error=str(e),
            key_prefix=OTP_SESSION_KEY_PREFIX,
        )
        raise RedisUnavailableError() from e


async def get_session(redis: Any, session_id: str) -> OtpSessionPayload | None:
    """Load OTP-pending session from Redis.

    Args:
        redis: Async Redis client (decode_responses=True).
        session_id: Opaque session identifier.

    Returns:
        Session payload or None if missing/expired.

    Raises:
        RedisUnavailableError: If Redis is None.
    """
    if redis is None:
        raise RedisUnavailableError()
    key = _session_key(session_id)
    try:
        value = await redis.get(key)
    except Exception as e:
        logger.warning(
            "OTP session store get failed",
            error=str(e),
            key_prefix=OTP_SESSION_KEY_PREFIX,
        )
        raise RedisUnavailableError() from e
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


async def invalidate_session(redis: Any, session_id: str) -> None:
    """Delete OTP session from Redis (one-time use after success or lock).

    Args:
        redis: Async Redis client.
        session_id: Opaque session identifier.

    Raises:
        RedisUnavailableError: If Redis is None.
    """
    if redis is None:
        raise RedisUnavailableError()
    key = _session_key(session_id)
    try:
        await redis.delete(key)
    except Exception as e:
        logger.warning(
            "OTP session store delete failed",
            error=str(e),
            key_prefix=OTP_SESSION_KEY_PREFIX,
        )
        raise RedisUnavailableError() from e


async def update_session_otp(
    redis: Any,
    session_id: str,
    otp_hash: str,
    ttl_seconds: int,
) -> None:
    """Update OTP and reset attempts for an existing session (e.g. resend OTP). Preserves TTL.

    Args:
        redis: Async Redis client (decode_responses=True).
        session_id: Opaque session identifier.
        otp_hash: New OTP hash to store.
        ttl_seconds: TTL to use if key has no TTL (fallback).

    Raises:
        RedisUnavailableError: If Redis is None or session missing.
    """
    if redis is None:
        raise RedisUnavailableError()
    key = _session_key(session_id)
    try:
        value = await redis.get(key)
    except Exception as e:
        logger.warning(
            "OTP session store get (update_session_otp) failed", error=str(e)
        )
        raise RedisUnavailableError() from e
    if value is None:
        raise OtpSessionInvalidError()
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        raise RedisUnavailableError()
    payload["otp_hash"] = otp_hash
    payload["attempts"] = 0
    payload["otp_issued_at"] = datetime.now(timezone.utc).isoformat()
    remaining = await redis.ttl(key)
    ex = remaining if remaining > 0 else ttl_seconds
    try:
        await redis.set(key, json.dumps(payload), ex=ex)
    except Exception as e:
        logger.warning(
            "OTP session store set (update_session_otp) failed", error=str(e)
        )
        raise RedisUnavailableError() from e


async def increment_attempts(
    redis: Any,
    session_id: str,
    max_attempts: int,
    ttl_seconds: int,
) -> int:
    """Increment failed OTP attempts for the session. Preserves TTL.

    Args:
        redis: Async Redis client (decode_responses=True).
        session_id: Opaque session identifier.
        max_attempts: Maximum attempts before session is considered locked.
        ttl_seconds: TTL to re-apply if key exists (used when updating).

    Returns:
        New attempts count after increment.

    Raises:
        RedisUnavailableError: If Redis is None or operation fails.
    """
    if redis is None:
        raise RedisUnavailableError()
    key = _session_key(session_id)
    try:
        value = await redis.get(key)
    except Exception as e:
        logger.warning(
            "OTP session store get (increment_attempts) failed", error=str(e)
        )
        raise RedisUnavailableError() from e
    if value is None:
        raise RedisUnavailableError()
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        raise RedisUnavailableError()
    attempts = int(payload.get("attempts", 0)) + 1
    payload["attempts"] = attempts
    remaining = await redis.ttl(key)
    ex = remaining if remaining > 0 else ttl_seconds
    try:
        await redis.set(key, json.dumps(payload), ex=ex)
    except Exception as e:
        logger.warning(
            "OTP session store set (increment_attempts) failed", error=str(e)
        )
        raise RedisUnavailableError() from e
    return attempts
