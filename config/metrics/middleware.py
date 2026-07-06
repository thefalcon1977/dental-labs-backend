"""Prometheus metrics middleware for FastAPI."""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from config.metrics.http import (
    active_requests,
    http_errors_total,
    http_request_duration_seconds,
    http_request_size_bytes,
    http_requests_total,
    http_response_size_bytes,
)
from config.settings import settings


def get_endpoint_name(request: Request) -> str:
    """Extract endpoint name from request route."""
    if not request.scope.get("route"):
        return request.url.path

    route = request.scope["route"]
    if hasattr(route, "path") and route.path:
        return route.path

    # Try to get route name
    if hasattr(route, "name") and route.name:
        return route.name

    return request.url.path


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics for HTTP requests."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        """Process request and collect metrics."""
        if not settings.ENABLE_METRICS:
            return await call_next(request)

        # Skip metrics and documentation endpoints to avoid noise
        # Exclude exact paths and path prefixes for documentation
        excluded_paths = [
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]
        # Also exclude documentation static assets (e.g., /docs/static/...)
        excluded_prefixes = [
            "/docs/",
            "/redoc/",
        ]

        path = request.url.path
        if path in excluded_paths or any(
            path.startswith(prefix) for prefix in excluded_prefixes
        ):
            return await call_next(request)

        # Get endpoint name
        endpoint = get_endpoint_name(request)
        method = request.method

        # Track active requests
        active_requests.inc()

        try:
            # Get request size
            request_size = 0
            if hasattr(request, "_body"):
                request_size = len(request._body) if request._body else 0
            elif request.headers.get("content-length"):
                try:
                    request_size = int(request.headers.get("content-length", 0))
                except (ValueError, TypeError):
                    request_size = 0

            # Record request size
            if request_size > 0:
                http_request_size_bytes.labels(
                    method=method,
                    endpoint=endpoint,
                ).observe(request_size)

            # Start timing
            start_time = time.time()

            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Get response size
            response_size = 0
            if hasattr(response, "body"):
                response_size = len(response.body) if response.body else 0
            elif response.headers.get("content-length"):
                try:
                    response_size = int(response.headers.get("content-length", 0))
                except (ValueError, TypeError):
                    response_size = 0

            # Get status code
            status_code = response.status_code

            # Record metrics
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
            ).observe(duration)

            if response_size > 0:
                http_response_size_bytes.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code,
                ).observe(response_size)

            # Track errors (4xx and 5xx)
            if status_code >= 400:
                error_type = (
                    "client_error" if 400 <= status_code < 500 else "server_error"
                )
                http_errors_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code,
                    error_type=error_type,
                ).inc()

            return response

        except Exception as e:
            # Track exception as error
            error_type = type(e).__name__
            status_code = 500

            http_errors_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                error_type=error_type,
            ).inc()

            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
            ).inc()

            raise

        finally:
            # Decrement active requests
            active_requests.dec()
