"""Structlog processors configuration."""

import structlog
from structlog.types import Processor

from config.settings import settings


def get_processors() -> list[Processor]:
    """Get structlog processors based on environment.

    Returns:
        List of structlog processors.
    """
    if settings.DEBUG:
        # Development: Pretty console output
        return [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # Production: JSON output for Elasticsearch
        return [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]


__all__ = ["get_processors"]
