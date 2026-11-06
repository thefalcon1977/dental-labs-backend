"""Request size limiting middleware.

This middleware rejects requests that declare a `Content-Length` greater than a
configured maximum. It is a coarse but effective protection against oversized
payload attacks.

Limitations:
    The check is based on the `Content-Length` header. If a client streams a
    body without a valid `Content-Length`, this middleware will not enforce a
    hard limit by itself (additional protections may be needed depending on
    deployment).
"""

from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import ORJSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config.logging import get_logger

logger = get_logger(__name__)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request body size.

    Prevents large payload attacks by rejecting requests
    exceeding the configured size limit.
    """

    def __init__(self, app: FastAPI, max_size_bytes: int = 10 * 1024 * 1024) -> None:
        """Initialize request size limit middleware.

        Args:
            app: FastAPI application
            max_size_bytes: Maximum request body size in bytes (default: 10MB)
        """
        super().__init__(app)
        self.max_size_bytes = max_size_bytes

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        """Check request size before processing.

        Args:
            request: FastAPI request object
            call_next: Next middleware/route handler

        Returns:
            Response or size limit error response
        """
        # Check content-length header if present
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_size_bytes:
                    logger.warning(
                        "Request size limit exceeded",
                        content_length=size,
                        max_size=self.max_size_bytes,
                        path=request.url.path,
                    )
                    return ORJSONResponse(
                        content={
                            "error": "Request too large",
                            "message": f"Maximum request size is {self.max_size_bytes / (1024 * 1024):.1f}MB",
                        },
                        status_code=413,
                    )
            except ValueError:
                # Invalid content-length, let it through (will be handled by FastAPI)
                pass

        # Process request
        return await call_next(request)
