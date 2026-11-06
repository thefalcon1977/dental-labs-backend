"""OTP generation and delivery (mock or real SMS via configured URL).

Design: docs/srs/otp-login-design-and-security.md.
Never log the actual OTP value.
"""

from __future__ import annotations

import hashlib
import secrets

import httpx

from config.logging import get_logger
from config.settings import settings

from ..helpers.constants import OTP_MESSAGE_TEMPLATE

logger = get_logger(__name__)

OTP_LENGTH = 6
SMS_HTTP_TIMEOUT_SECONDS = 10


def _get_platform_name() -> str:
    """Get platform name from settings for OTP messages.

    Returns:
        Platform name string (default: "iTicket").
    """
    auth = getattr(settings, "auth", None) or getattr(settings, "AUTH", None)
    if auth is None:
        return "iTicket"
    return str(getattr(auth, "OTP_PLATFORM_NAME", "iTicket"))


def format_otp_message(otp_code: str) -> str:
    """Format OTP code into a user-friendly multiline SMS message.

    Formats the message with the code on its own line for easy selection/copying.
    Uses multiline format for better readability.

    Args:
        otp_code: The OTP code to include in the message.

    Returns:
        Multiline formatted message string with platform name and OTP code.
    """
    platform_name = _get_platform_name()
    return OTP_MESSAGE_TEMPLATE.format(platform_name=platform_name, otp_code=otp_code)


def generate_otp() -> tuple[str, str]:
    """Generate a short-lived OTP and its hash for constant-time verification.

    Returns:
        Tuple of (plain_code, hash_for_storage). Store only the hash in Redis.
    """
    code = "".join(secrets.choice("0123456789") for _ in range(OTP_LENGTH))
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    return code, code_hash


def _otp_sms_mock_enabled() -> bool:
    """Return True if SMS delivery is mocked (no real HTTP call)."""
    auth = getattr(settings, "auth", None) or getattr(settings, "AUTH", None)
    if auth is None:
        return True
    return bool(getattr(auth, "OTP_SMS_MOCK_ENABLED", True))


def _otp_sms_url() -> str:
    """Return configured SMS gateway URL (POST with phone, message)."""
    auth = getattr(settings, "auth", None) or getattr(settings, "AUTH", None)
    if auth is None:
        return ""
    return (getattr(auth, "OTP_SMS_URL", None) or "").strip()


async def send_otp(phone: str, message: str) -> None:
    """Send OTP via mock (log only) or real SMS (POST to configured URL).

    When OTP_SMS_MOCK_ENABLED is true: only logs. When false: POST to OTP_SMS_URL
    with JSON body {"phone": phone, "message": message}.

    Args:
        phone: Recipient phone number.
        message: Formatted OTP message text (use format_otp_message() to format the code).

    Raises:
        RuntimeError: If mock is disabled and OTP_SMS_URL is empty or POST fails.
    """
    if _otp_sms_mock_enabled():
        logger.info(
            "OTP sent (mock)", phone_last4=(phone[-4:] if len(phone) >= 4 else "")
        )
        return
    url = _otp_sms_url()
    if not url:
        logger.error("OTP_SMS_MOCK_ENABLED is false but OTP_SMS_URL is not set")
        raise RuntimeError("SMS URL not configured")
    if not (phone or "").strip():
        logger.error(
            "Real SMS requested but phone number is missing (e.g. not in JWT user_info.phoneNumber)"
        )
        raise RuntimeError("Phone number required for SMS")
    payload = {"phone": phone.strip(), "message": message}
    try:
        async with httpx.AsyncClient(timeout=SMS_HTTP_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("SMS send failed", url=url, error=str(e))
        raise RuntimeError("SMS delivery failed") from e
    logger.info("OTP sent via SMS", phone_last4=(phone[-4:] if len(phone) >= 4 else ""))


def send_otp_mock() -> None:
    """Legacy mock entrypoint: log only. Prefer send_otp(phone, message) for new code."""
    logger.info("OTP sent (mock)")


def verify_otp_constant_time(provided: str, stored_hash: str) -> bool:
    """Verify OTP using constant-time comparison.

    Args:
        provided: User-supplied code (e.g. from request).
        stored_hash: SHA-256 hash stored in session.

    Returns:
        True if provided code matches stored hash.
    """
    provided_normalized = provided.strip()[:OTP_LENGTH]
    if len(provided_normalized) != OTP_LENGTH:
        return False
    computed_hash = hashlib.sha256(provided_normalized.encode()).hexdigest()
    return secrets.compare_digest(computed_hash, stored_hash)
