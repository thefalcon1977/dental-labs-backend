"""Service information Prometheus metrics."""

from prometheus_client import Info

from apps.core.version import __version__
from config.settings import settings

# Service information metric
service_info = Info(
    "service_info",
    "Service information",
)


def setup_service_info() -> None:
    """Initialize service information metric."""
    service_info.info(
        {
            "service_name": settings.SERVICE_NAME,
            "version": __version__,
            "environment": settings.current_env or "default",
        }
    )


__all__ = [
    "service_info",
    "setup_service_info",
]
