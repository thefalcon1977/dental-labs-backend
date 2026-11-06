"""Middleware package for request/response cross-cutting concerns.

This package contains middleware implementations and registration helpers used
by the FastAPI application. Middleware is registered centrally via
`apps.core.middleware.registration.register_middleware()`.

Key behaviors provided by this package include:
- Security headers and trusted host validation
- Request size limiting and in-process rate limiting
- CORS configuration with safe defaults
- Structured request logging with request correlation IDs
- Request timing via `X-Process-Time`
- Optional debug toolbar in development

Note:
    Middleware ordering matters. See `apps.core.middleware.registration` for
    the exact order and rationale.
"""

from .logging import LoggingMiddleware
from .rate_limiting import RateLimitingMiddleware
from .registration import register_middleware
from .request_size_limit import RequestSizeLimitMiddleware
from .security_headers import SecurityHeadersMiddleware
from .timing import TimingMiddleware

# Re-export all middleware classes for backward compatibility
__all__ = [
    "LoggingMiddleware",
    "TimingMiddleware",
    "SecurityHeadersMiddleware",
    "RateLimitingMiddleware",
    "RequestSizeLimitMiddleware",
    "register_middleware",
]
