"""Prometheus metrics configuration and collection.

This module provides a unified interface for all Prometheus metrics.
Metrics are organized into separate modules:
- http: HTTP request/response metrics
- database: Database operation metrics
- system: System resource metrics
- service: Service information metrics
"""

from prometheus_client import REGISTRY, generate_latest

from config.metrics.database import *  # noqa: F403, F401
from config.metrics.http import *  # noqa: F403, F401
from config.metrics.middleware import PrometheusMiddleware
from config.metrics.service import service_info, setup_service_info
from config.metrics.system import *  # noqa: F403, F401
from config.settings import settings


def setup_metrics() -> None:
    """Initialize and setup Prometheus metrics."""
    if not settings.ENABLE_METRICS:
        return

    setup_service_info()


def get_metrics() -> bytes:
    """Get Prometheus metrics in text format."""
    if not settings.ENABLE_METRICS:
        return b"# Metrics are disabled\n"

    return generate_latest(REGISTRY)


__all__ = [
    "setup_metrics",
    "get_metrics",
    "PrometheusMiddleware",
    "service_info",
    # HTTP metrics (imported via star import from config.metrics.http)
    "http_requests_total",  # noqa: F405
    "http_request_duration_seconds",  # noqa: F405
    "http_request_size_bytes",  # noqa: F405
    "http_response_size_bytes",  # noqa: F405
    "http_errors_total",  # noqa: F405
    "active_requests",  # noqa: F405
    # System metrics (imported via star import from config.metrics.system)
    "system_cpu_usage_percent",  # noqa: F405
    "system_memory_usage_bytes",  # noqa: F405
    "system_memory_available_bytes",  # noqa: F405
]

# Add database metrics to __all__ if database is enabled (imported via star import from config.metrics.database)
if settings.database.ENABLED:
    __all__.extend(
        [
            "db_connections_active",  # noqa: F405
            "db_connections_idle",  # noqa: F405
            "db_query_duration_seconds",  # noqa: F405
            "db_queries_total",  # noqa: F405
            "db_errors_total",  # noqa: F405
        ]
    )
