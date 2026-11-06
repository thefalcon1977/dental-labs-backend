"""CORS configuration helper functions.

This module builds Starlette/FastAPI CORS middleware configuration from
Dynaconf settings, with basic safety checks.

Security:
    `allow_credentials=True` must not be combined with wildcard origins.
    If `*` is configured while credentials are enabled, credentials are
    disabled and a warning is logged.
"""

from apps.core.types import CorsConfigDict
from config.logging import get_logger
from config.settings import settings

logger = get_logger(__name__)


def _normalize_origins(value: list | str) -> list[str]:
    """Convert origins to list. Handles comma-separated string from .env (no @json)."""
    if isinstance(value, list):
        return list(value)
    if isinstance(value, str):
        return [x.strip() for x in value.split(",") if x.strip()]
    return ["*"]


def get_cors_config() -> CorsConfigDict:
    """Get CORS configuration from settings with security validation.

    Returns:
        Dictionary with CORS middleware configuration
    """
    raw = getattr(settings.cors, "ORIGINS", ["*"])
    cors_origins = _normalize_origins(raw)
    # Fallback: if parsing produced no valid origins, allow all (dev safety)
    if not cors_origins:
        cors_origins = ["*"]
    allow_wildcard = "*" in cors_origins

    # Get CORS settings from configuration
    allow_credentials = settings.cors.ALLOW_CREDENTIALS
    allowed_methods = settings.cors.ALLOWED_METHODS
    allowed_headers = settings.cors.ALLOWED_HEADERS
    # Normalize: allow_headers may be str from env; must be list. Use * in DEBUG to allow any header
    if isinstance(allowed_headers, str):
        allowed_headers = [
            x.strip() for x in allowed_headers.split(",") if x.strip()
        ] or ["*"]
    if settings.DEBUG and "*" not in allowed_headers:
        allowed_headers = ["*"]  # Allow any header in dev to avoid preflight issues.
    exposed_headers = settings.cors.EXPOSED_HEADERS
    max_age = settings.cors.MAX_AGE

    # Security: Cannot use allow_credentials=True with allow_origins=["*"]
    # If wildcard is used, disable credentials for security
    if allow_wildcard and allow_credentials:
        logger.warning(
            "CORS wildcard origin detected with credentials enabled",
            message="Wildcard origins cannot be used with credentials. "
            "Credentials will be disabled for security.",
        )
        allow_credentials = False

    logger.info(
        "CORS config",
        allow_origins=cors_origins,
        allow_credentials=allow_credentials,
    )
    return {
        "allow_origins": cors_origins,
        "allow_credentials": allow_credentials,
        "allow_methods": allowed_methods,
        "allow_headers": allowed_headers,
        "expose_headers": exposed_headers,
        "max_age": max_age,
    }
