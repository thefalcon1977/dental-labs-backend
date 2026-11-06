"""Timing middleware for request processing time.

This middleware measures end-to-end request latency within the application and
adds it to the response as the `X-Process-Time` header (in seconds).

Observability:
    The value is useful for quick inspection and can complement metrics and
    tracing. It is not a substitute for histogram-based latency metrics.
"""

import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from config.logging import get_logger

logger = get_logger(__name__)


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to add request timing information to responses and logs."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        """Add request timing information to response headers.

        Args:
            request: FastAPI request object
            call_next: Next middleware/route handler

        Returns:
            Response with X-Process-Time header added
        """
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        # Log timing information
        logger.debug(
            "Request timing",
            process_time=process_time,
        )

        return response
