"""Redis and request context dependencies for auth (OTP)."""

from typing import Any

from fastapi import Request

from config.logging import get_logger

logger = get_logger(__name__)


async def get_redis(request: Request) -> Any:
    """Get async Redis client from app state.

    Returns None if Redis is not enabled or connection failed at startup.
    Used by OTP session store.

    Args:
        request: FastAPI request (used to access app.state)

    Returns:
        Redis async client or None
    """
    return getattr(request.app.state, "redis", None)


def get_client_ip(request: Request) -> str:
    """Get client IP for audit and logging.

    Prefers X-Forwarded-For when present (first hop), otherwise request.client.host.

    Args:
        request: FastAPI request

    Returns:
        Client IP string
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
