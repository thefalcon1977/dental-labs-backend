"""Middleware registration for the FastAPI application.

This module centralizes middleware registration so ordering remains consistent
across environments and services.

Important:
    Middleware order matters. The first middleware added is the *outermost*
    middleware in Starlette/FastAPI and executes last on the way in / first on
    the way out. The docstring on `register_middleware()` documents the chosen
    order.
"""

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from config.logging import get_logger
from config.metrics import PrometheusMiddleware
from config.settings import settings

from .cors import get_cors_config
from .debug_toolbar import setup_debug_toolbar
from .logging import LoggingMiddleware
from .rate_limiting import RateLimitingMiddleware
from .request_size_limit import RequestSizeLimitMiddleware
from .security_headers import SecurityHeadersMiddleware
from .timing import TimingMiddleware

logger = get_logger(__name__)


def register_middleware(app: FastAPI) -> None:
    """Register all middleware with the FastAPI app.

    Middleware order (first added = last executed):
    1. ServerErrorMiddleware - Error handling: catch all unhandled exceptions (add first, executes last)
    2. DebugToolbarMiddleware - Debug: interactive debug toolbar (DEBUG mode only)
    3. TrustedHostMiddleware - Security: validate Host header
    4. RequestSizeLimitMiddleware - Security: limit request size
    5. RateLimitingMiddleware - Security: rate limit requests
    6. CORSMiddleware - CORS: handle cross-origin requests (must run before SecurityHeaders)
    7. SecurityHeadersMiddleware - Security: add security headers
    8. PrometheusMiddleware - Metrics: capture all requests
    9. LoggingMiddleware - Logging: add request context
    10. TimingMiddleware - Timing: add process time header

    Args:
        app: FastAPI application instance
    """
    # Get security settings (with defaults if not configured)
    try:
        security = settings.security
    except AttributeError:
        # Security settings not configured, use defaults
        security = type("Security", (), {})()

    # CORS first (add last so it runs first): ensures preflight OPTIONS gets correct headers
    # before any other middleware that might alter the response
    cors_config = get_cors_config()
    app.add_middleware(
        CORSMiddleware,
        **cors_config,
    )

    # Server error middleware (add first so it executes last and catches all exceptions)
    # Provides debug tracebacks in development mode
    app.add_middleware(
        ServerErrorMiddleware,
        debug=settings.DEBUG,
    )

    # Debug toolbar middleware (development only)
    # Provides interactive debugging interface with request/response inspection
    setup_debug_toolbar(app)

    # Trusted host middleware (security - validate Host header)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
        www_redirect=False,  # Disable www redirect for API endpoints
    )

    # Request size limit middleware (security - limit payload size)
    max_request_size = getattr(security, "MAX_REQUEST_SIZE_MB", 10)
    max_request_size_bytes = max_request_size * 1024 * 1024
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_size_bytes=max_request_size_bytes,
    )

    # Rate limiting middleware (security - prevent abuse)
    enable_rate_limiting = getattr(security, "ENABLE_RATE_LIMITING", True)
    if enable_rate_limiting:
        requests_per_minute = getattr(security, "RATE_LIMIT_REQUESTS_PER_MINUTE", 60)
        app.add_middleware(
            RateLimitingMiddleware,
            requests_per_minute=requests_per_minute,
        )

    # Security headers middleware (add security headers)
    app.add_middleware(SecurityHeadersMiddleware)

    # Prometheus metrics middleware (add early to capture all requests)
    if settings.ENABLE_METRICS:
        app.add_middleware(PrometheusMiddleware)

    # Logging middleware (add to capture all requests)
    app.add_middleware(LoggingMiddleware)

    # Timing middleware (add last to measure total processing time)
    app.add_middleware(TimingMiddleware)
