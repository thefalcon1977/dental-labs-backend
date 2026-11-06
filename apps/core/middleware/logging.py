"""Logging middleware for request context and correlation.

This middleware is responsible for:
- Generating a per-request `request_id`
- Adding request context fields to structured logs (method, path, client_host)
- Emitting basic request start/completion logs
- Returning `X-Request-ID` response header for client correlation

Security:
    This middleware must not log secrets (Authorization headers, cookies, etc.).
    It only logs safe metadata and query params.
"""

import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from apps.core.utils.security import redact_sensitive_fields
from config.logging import add_request_context, clear_request_context, get_logger

logger = get_logger(__name__)

# Sensitive query parameter keys that should be redacted
SENSITIVE_QUERY_PARAMS = {
    "password",
    "token",
    "secret",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "authorization",
    "auth",
    "credential",
    "credentials",
}


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to add request context and log request lifecycle.

    The request context is attached using the logging system’s context binding,
    so all logs emitted during a request include correlation fields.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        """Add request context and logging.

        Args:
            request: FastAPI request object
            call_next: Next middleware/route handler

        Returns:
            Response with X-Request-ID header added
        """
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())

        # Add request context to all logs
        add_request_context(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_host=request.client.host if request.client else None,
        )

        try:
            # Log request with redacted sensitive query params
            query_params = dict(request.query_params) if request.query_params else None
            if query_params:
                # Redact sensitive query parameters
                query_params = redact_sensitive_fields(
                    query_params, SENSITIVE_QUERY_PARAMS
                )

            logger.info(
                "Request started",
                query_params=query_params,
            )

            # Process request
            response = await call_next(request)

            # Log response
            logger.info(
                "Request completed",
                status_code=response.status_code,
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as e:
            # Log error
            logger.exception(
                "Request failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
        finally:
            # Clear request context
            clear_request_context()
