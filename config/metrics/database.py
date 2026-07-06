"""Database-related Prometheus metrics."""

from prometheus_client import Counter, Gauge, Histogram

from config.settings import settings

# Database Metrics (only if database is enabled)
if settings.database.ENABLED:
    db_connections_active = Gauge(
        "db_connections_active",
        "Number of active database connections",
    )

    db_connections_idle = Gauge(
        "db_connections_idle",
        "Number of idle database connections",
    )

    db_query_duration_seconds = Histogram(
        "db_query_duration_seconds",
        "Database query duration in seconds",
        ["operation"],
        buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    )

    db_queries_total = Counter(
        "db_queries_total",
        "Total number of database queries",
        ["operation", "status"],
    )

    db_errors_total = Counter(
        "db_errors_total",
        "Total number of database errors",
        ["operation", "error_type"],
    )

    __all__ = [
        "db_connections_active",
        "db_connections_idle",
        "db_query_duration_seconds",
        "db_queries_total",
        "db_errors_total",
    ]
else:
    __all__ = []
