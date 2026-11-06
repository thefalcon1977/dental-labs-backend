"""OTP two-step login orchestration.

Design: docs/srs/otp-login-design-and-security.md.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any

from jose import jwt

from config.logging import get_logger
from config.settings import settings

from ..helpers.exceptions import (
    OtpSessionInvalidError,
    OtpSessionLockedError,
    OtpWindowNotExpiredError,
    RedisUnavailableError,
)
from ..types import TokenDataDict
from ..utils import otp_session_store
from ..utils.otp_session_store import OtpSessionPayload
from . import otp_sender
from .auth_service import login_user as keycloak_login_user

logger = get_logger(__name__)


def _otp_enabled() -> bool:
    """Return True if OTP two-step login is enabled (requires Redis)."""
    auth = getattr(settings, "auth", None) or getattr(settings, "AUTH", None)
    if auth is None:
        return False
    return bool(getattr(auth, "OTP_ENABLED", False))


def _get_otp_config() -> tuple[int, int, int]:
    """Return (session_ttl, max_attempts, otp_validity_seconds)."""
    auth = getattr(settings, "auth", None) or getattr(settings, "AUTH", None)
    if auth is None:
        return 300, 5, 120
    return (
        getattr(auth, "OTP_SESSION_TTL_SECONDS", 300),
        getattr(auth, "OTP_MAX_ATTEMPTS", 5),
        getattr(auth, "OTP_VALIDITY_SECONDS", 120),
    )


def _get_otp_bypass_config() -> tuple[bool, str]:
    """Return (bypass_enabled, bypass_code).

    Returns:
        Tuple of (bypass_enabled boolean, bypass_code string).
    """
    auth = getattr(settings, "auth", None) or getattr(settings, "AUTH", None)
    if auth is None:
        return False, ""
    return (
        bool(getattr(auth, "OTP_BYPASS_ENABLED", False)),
        str(getattr(auth, "OTP_BYPASS_CODE", "") or "").strip(),
    )


def _user_id_from_access_token(access_token: str) -> str:
    """Extract subject (user id) from JWT access token without verification.

    The token was just issued by Keycloak; we only need sub for session/lock keys.

    Args:
        access_token: JWT access token string.

    Returns:
        sub claim value, or empty string if missing or decode fails.
    """
    try:
        payload = jwt.get_unverified_claims(access_token)
        return (payload.get("sub") or payload.get("user_id") or "").strip()
    except Exception:
        return ""


def _phone_from_access_token(access_token: str) -> str:
    """Extract phone number from JWT access token (e.g. user_info.phoneNumber).

    Args:
        access_token: JWT access token string.

    Returns:
        Phone number string, or empty string if missing or decode fails.
    """
    try:
        payload = jwt.get_unverified_claims(access_token)
        user_info = payload.get("user_info") or {}
        if isinstance(user_info, dict):
            phone = user_info.get("phoneNumber") or user_info.get("phone") or ""
        else:
            phone = ""
        return (phone or "").strip()
    except Exception:
        return ""


async def login_with_otp(
    username: str,
    password: str,
    redis: Any,
) -> dict[str, Any]:
    """Step 1: Validate credentials, create OTP session, send OTP. Return session_id and metadata (no token).

    Args:
        username: Username for authentication.
        password: Password for authentication.
        redis: Async Redis client (required when OTP enabled).

    Returns:
        Dict with session_id, message, expires_in.

    Raises:
        RedisUnavailableError: If Redis is None when OTP is enabled.
        UnauthorizedError: If credentials invalid.
        KeycloakConnectionError: If Keycloak unavailable.
    """
    if not _otp_enabled():
        raise RedisUnavailableError()
    ttl, max_attempts, otp_validity = _get_otp_config()

    token_data = await keycloak_login_user(username, password)
    access_token = token_data.get("access_token") or ""
    user_id = _user_id_from_access_token(access_token)
    phone = _phone_from_access_token(access_token)

    # Block new OTP until the previous one's validity window has expired
    remaining = await otp_session_store.get_last_otp_issued_ttl(redis, user_id)
    if remaining is not None:
        raise OtpWindowNotExpiredError(retry_after_seconds=remaining)

    session_id = secrets.token_urlsafe(32)
    code, code_hash = otp_sender.generate_otp()
    created_at = datetime.now(timezone.utc).isoformat()
    otp_issued_at = created_at

    payload: OtpSessionPayload = {
        "access_token": token_data["access_token"],
        "refresh_token": token_data.get("refresh_token", ""),
        "expires_in": token_data.get("expires_in", 300),
        "token_type": token_data.get("token_type", "Bearer"),
        "otp_hash": code_hash,
        "attempts": 0,
        "created_at": created_at,
        "user_id": user_id,
        "otp_issued_at": otp_issued_at,
        "phone": phone,
    }
    await otp_session_store.create_session(redis, session_id, payload, ttl)
    await otp_session_store.set_last_otp_issued(redis, user_id, otp_validity)
    otp_message = otp_sender.format_otp_message(code)
    await otp_sender.send_otp(phone or "mock", otp_message)

    logger.info("OTP session created", session_id_prefix=session_id[:8])
    result: dict[str, Any] = {
        "session_id": session_id,
        "message": "OTP sent",
        "expires_in": ttl,
    }
    auth = getattr(settings, "auth", None) or getattr(settings, "AUTH", None)
    mock_enabled = bool(getattr(auth, "OTP_SMS_MOCK_ENABLED", True))
    if mock_enabled:
        result["dev_otp_code"] = code
    return result


async def verify_otp(
    session_id: str,
    code: str,
    redis: Any,
) -> TokenDataDict:
    """Step 2: Verify OTP and return tokens; invalidate session on success or lock.

    Args:
        session_id: Opaque session id from Step 1.
        code: User-supplied OTP code.
        redis: Async Redis client.

    Returns:
        Token dict (access_token, refresh_token, expires_in, token_type).

    Raises:
        RedisUnavailableError: If Redis is None.
        OtpSessionInvalidError: If session missing/expired or OTP wrong.
        OtpSessionLockedError: If too many failed attempts.
    """
    ttl, max_attempts, otp_validity = _get_otp_config()

    session = await otp_session_store.get_session(redis, session_id)
    if session is None:
        raise OtpSessionInvalidError()

    # OTP code is valid only for otp_validity seconds after it was issued
    otp_issued_at_str = session.get("otp_issued_at")
    if otp_issued_at_str:
        try:
            otp_issued_at = datetime.fromisoformat(
                otp_issued_at_str.replace("Z", "+00:00")
            )
            elapsed = (datetime.now(timezone.utc) - otp_issued_at).total_seconds()
            if elapsed > otp_validity:
                await otp_session_store.invalidate_session(redis, session_id)
                raise OtpSessionInvalidError()
        except (ValueError, TypeError):
            pass  # malformed timestamp: continue and let hash check fail if wrong

    attempts = int(session.get("attempts", 0))
    if attempts >= max_attempts:
        await otp_session_store.invalidate_session(redis, session_id)
        logger.warning(
            "OTP session locked (max attempts)", session_id_prefix=session_id[:8]
        )
        raise OtpSessionLockedError()

    # Check bypass code if enabled
    bypass_enabled, bypass_code = _get_otp_bypass_config()
    bypass_used = False
    if bypass_enabled and bypass_code and code.strip() == bypass_code.strip():
        bypass_used = True
        logger.info(
            "OTP bypass code used",
            session_id_prefix=session_id[:8],
        )
        # Bypass verification - proceed to return tokens
    else:
        # Normal OTP verification
        stored_hash = session.get("otp_hash") or ""
        if not otp_sender.verify_otp_constant_time(code, stored_hash):
            new_attempts = await otp_session_store.increment_attempts(
                redis, session_id, max_attempts, ttl
            )
            if new_attempts >= max_attempts:
                await otp_session_store.invalidate_session(redis, session_id)
                logger.warning(
                    "OTP session locked (max attempts)",
                    session_id_prefix=session_id[:8],
                )
                raise OtpSessionLockedError()
            raise OtpSessionInvalidError()

    user_id = session.get("user_id") or ""
    await otp_session_store.delete_last_otp_issued(redis, user_id)
    await otp_session_store.invalidate_session(redis, session_id)
    if bypass_used:
        logger.info(
            "OTP verified successfully (bypass)",
            session_id_prefix=session_id[:8],
        )
    else:
        logger.info("OTP verified successfully", session_id_prefix=session_id[:8])
    return {
        "access_token": session["access_token"],
        "refresh_token": session.get("refresh_token", ""),
        "expires_in": session.get("expires_in", 300),
        "token_type": session.get("token_type", "Bearer"),
    }


async def resend_otp(
    session_id: str,
    redis: Any,
) -> dict[str, Any]:
    """Resend OTP for an existing session; updates OTP and resets attempts.

    Args:
        session_id: Opaque session id from Step 1 (login).
        redis: Async Redis client.

    Returns:
        Dict with message, expires_in; dev_otp_code when DEBUG.

    Raises:
        RedisUnavailableError: If Redis is None.
        OtpSessionInvalidError: If session missing or expired.
    """
    if not _otp_enabled():
        raise RedisUnavailableError()
    ttl, _max_attempts, otp_validity = _get_otp_config()

    session = await otp_session_store.get_session(redis, session_id)
    if session is None:
        raise OtpSessionInvalidError()

    # Resend cooldown: per (session_id, otp_issued_at) only. No new OTP for this
    # session until the current OTP's validity window has expired.
    otp_issued_at_str = session.get("otp_issued_at")
    if otp_issued_at_str:
        try:
            otp_issued_at = datetime.fromisoformat(
                otp_issued_at_str.replace("Z", "+00:00")
            )
            elapsed = (datetime.now(timezone.utc) - otp_issued_at).total_seconds()
            if elapsed < otp_validity:
                remaining = int(otp_validity - elapsed)
                raise OtpWindowNotExpiredError(retry_after_seconds=remaining)
        except (ValueError, TypeError):
            pass  # no valid timestamp: allow resend

    user_id = session.get("user_id") or ""
    phone = session.get("phone") or "mock"

    code, code_hash = otp_sender.generate_otp()
    await otp_session_store.update_session_otp(redis, session_id, code_hash, ttl)
    # Refresh per-user lock only when we have a user_id (so user cannot start
    # a new login until this OTP window expires). Skip when user_id empty.
    if user_id:
        await otp_session_store.set_last_otp_issued(redis, user_id, otp_validity)
    otp_message = otp_sender.format_otp_message(code)
    await otp_sender.send_otp(phone, otp_message)

    logger.info("OTP resent", session_id_prefix=session_id[:8])
    result: dict[str, Any] = {
        "message": "OTP resent",
        "expires_in": ttl,
    }
    auth = getattr(settings, "auth", None) or getattr(settings, "AUTH", None)
    mock_enabled = bool(getattr(auth, "OTP_SMS_MOCK_ENABLED", True))
    if mock_enabled:
        result["dev_otp_code"] = code
    return result
