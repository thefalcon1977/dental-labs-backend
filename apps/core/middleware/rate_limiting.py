"""Rate limiting middleware to prevent abuse and basic DoS attempts.

Implements a simple per-IP, in-memory rate limiter.

Operational notes:
    - This implementation is process-local. In multi-worker deployments,
      limits apply per worker process.
    - For production-grade, shared limits across workers/instances, prefer a
      distributed store (e.g., Redis) or an API gateway rate limiter.
"""

import time
from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import ORJSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from apps.core.types import RequestCountsDict
from config.logging import get_logger

logger = get_logger(__name__)


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Middleware to implement rate limiting per IP address.

    Uses in-memory storage for rate limiting. For production,
    consider using Redis for distributed rate limiting.
    """

    def __init__(self, app: FastAPI, requests_per_minute: int = 60) -> None:
        """Initialize rate limiting middleware.

        Args:
            app: FastAPI application
            requests_per_minute: Maximum requests per minute per IP
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts: RequestCountsDict = {}

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        """Apply rate limiting to request.

        Args:
            request: FastAPI request object
            call_next: Next middleware/route handler

        Returns:
            Response or rate limit error response
        """
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Clean old entries (older than 1 minute)
        current_time = time.time()
        if client_ip in self.request_counts:
            self.request_counts[client_ip] = [
                timestamp
                for timestamp in self.request_counts[client_ip]
                if current_time - timestamp < 60
            ]

        # Check rate limit
        if client_ip in self.request_counts:
            request_count = len(self.request_counts[client_ip])
            if request_count >= self.requests_per_minute:
                logger.warning(
                    "Rate limit exceeded",
                    client_ip=client_ip,
                    requests=request_count,
                    limit=self.requests_per_minute,
                )
                return ORJSONResponse(
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"Maximum {self.requests_per_minute} requests per minute allowed",
                    },
                    status_code=429,
                    headers={
                        "Retry-After": "60",
                        "X-RateLimit-Limit": str(self.requests_per_minute),
                        "X-RateLimit-Remaining": "0",
                    },
                )

        # Add current request timestamp
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []
        self.request_counts[client_ip].append(current_time)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = self.requests_per_minute - len(
            self.request_counts.get(client_ip, [])
        )
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))

        return response
