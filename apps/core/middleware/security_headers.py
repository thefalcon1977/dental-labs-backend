"""Security headers middleware for consistent response hardening.

This middleware attaches a set of security-focused HTTP headers to every
response (e.g., X-Content-Type-Options, X-Frame-Options, HSTS, CSP).

Configuration:
    Header values can be overridden via `settings.security` when present.
    In DEBUG mode, some headers (e.g., HSTS) default to disabled unless
    explicitly enabled.
"""

from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from config.logging import get_logger
from config.settings import settings

logger = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses.

    Adds comprehensive security headers including:
    - X-Content-Type-Options: Prevent MIME type sniffing
    - X-Frame-Options: Prevent clickjacking
    - X-XSS-Protection: Enable XSS filter
    - Strict-Transport-Security: Force HTTPS
    - Content-Security-Policy: Control resource loading
    - Referrer-Policy: Control referrer information
    - Permissions-Policy: Control browser features
    - Cross-Origin policies: Control cross-origin behavior
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        """Add security headers to response.

        Args:
            request: FastAPI request object
            call_next: Next middleware/route handler

        Returns:
            Response with security headers added
        """
        response = await call_next(request)

        # Get security settings (with defaults if not configured)
        try:
            security = settings.security
        except AttributeError:
            # Security settings not configured, use defaults
            security = type("Security", (), {})()

        # X-Content-Type-Options: Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options: Prevent clickjacking
        frame_options = getattr(security, "X_FRAME_OPTIONS", "DENY")
        response.headers["X-Frame-Options"] = frame_options

        # X-XSS-Protection: Enable XSS filter (legacy, but still useful)
        xss_protection = getattr(security, "X_XSS_PROTECTION", "1; mode=block")
        response.headers["X-XSS-Protection"] = xss_protection

        # Strict-Transport-Security (HSTS): Force HTTPS
        enable_hsts = getattr(security, "ENABLE_HSTS", not settings.DEBUG)
        if enable_hsts:
            hsts_max_age = getattr(security, "HSTS_MAX_AGE", 31536000)  # 1 year
            hsts_include_subdomains = getattr(security, "HSTS_INCLUDE_SUBDOMAINS", True)
            hsts_preload = getattr(security, "HSTS_PRELOAD", False)

            hsts_value = f"max-age={hsts_max_age}"
            if hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if hsts_preload:
                hsts_value += "; preload"

            response.headers["Strict-Transport-Security"] = hsts_value

        # Content-Security-Policy: Control resource loading
        csp = getattr(security, "CONTENT_SECURITY_POLICY", None)
        if csp:
            response.headers["Content-Security-Policy"] = csp

        # Referrer-Policy: Control referrer information
        referrer_policy = getattr(
            security, "REFERRER_POLICY", "strict-origin-when-cross-origin"
        )
        response.headers["Referrer-Policy"] = referrer_policy

        # Permissions-Policy: Control browser features
        permissions_policy = getattr(security, "PERMISSIONS_POLICY", None)
        if permissions_policy:
            response.headers["Permissions-Policy"] = permissions_policy

        # Cross-Origin-Embedder-Policy: Require CORS for embedded resources
        coep = getattr(security, "CROSS_ORIGIN_EMBEDDER_POLICY", None)
        if coep:
            response.headers["Cross-Origin-Embedder-Policy"] = coep

        # Cross-Origin-Opener-Policy: Isolate browsing context
        coop = getattr(security, "CROSS_ORIGIN_OPENER_POLICY", "same-origin")
        response.headers["Cross-Origin-Opener-Policy"] = coop

        # Cross-Origin-Resource-Policy: Control resource loading.
        # A route may opt out, for example a public avatar embedded by the web app.
        if "Cross-Origin-Resource-Policy" not in response.headers:
            corp = getattr(security, "CROSS_ORIGIN_RESOURCE_POLICY", "same-origin")
            response.headers["Cross-Origin-Resource-Policy"] = corp

        return response
