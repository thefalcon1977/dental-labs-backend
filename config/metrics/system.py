"""System-related Prometheus metrics."""

from prometheus_client import Gauge

# System Metrics
system_cpu_usage_percent = Gauge(
    "system_cpu_usage_percent",
    "System CPU usage percentage",
)

system_memory_usage_bytes = Gauge(
    "system_memory_usage_bytes",
    "System memory usage in bytes",
)

system_memory_available_bytes = Gauge(
    "system_memory_available_bytes",
    "System memory available in bytes",
)

__all__ = [
    "system_cpu_usage_percent",
    "system_memory_usage_bytes",
    "system_memory_available_bytes",
]
