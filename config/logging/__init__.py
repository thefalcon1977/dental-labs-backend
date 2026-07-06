"""Professional logging configuration with loguru and structlog.

This module provides a unified logging interface that:
- Uses structlog for structured logging
- Uses loguru as the underlying logger
- Provides readable console output in development
- Provides JSON output in production for Elasticsearch compatibility

The module is organized into separate components:
- interceptor: Handles standard library logging interception
- processors: Configures structlog processors
- handlers: Sets up console handler
- config: Provides context management utilities
"""

import logging

import structlog
from loguru import logger

from config.settings import settings

from .config import add_request_context, clear_request_context, get_request_id
from .handlers import setup_console_handler, setup_third_party_loggers
from .interceptor import InterceptHandler
from .processors import get_processors

# Track if logging has been configured to prevent duplicate setup
_logging_configured = False


def setup_logging() -> None:
    """Configure logging for the application.

    This function is idempotent - it can be called multiple times safely.
    Only the first call will configure logging; subsequent calls are ignored.
    """
    global _logging_configured

    # If already configured, skip
    if _logging_configured:
        return

    # Remove default loguru handler
    logger.remove()

    # Set log level from settings
    log_level = settings.LOG_LEVEL.upper()

    # Intercept standard library logging
    intercept_handler = InterceptHandler()
    logging.basicConfig(handlers=[intercept_handler], level=0, force=True)

    # Set root logger level
    root_logger = logging.getLogger()
    root_logger.handlers = [intercept_handler]
    root_logger.setLevel(log_level)

    # Get processors based on environment
    processors = get_processors()

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Setup handlers (console only; no file logging)
    setup_console_handler(log_level)
    setup_third_party_loggers(intercept_handler, log_level)

    # Mark as configured
    _logging_configured = True

    # Get structlog logger
    struct_logger = structlog.get_logger()
    struct_logger.info(
        "Logging configured",
        environment="development" if settings.DEBUG else "production",
        log_level=log_level,
        format="pretty" if settings.DEBUG else "json",
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a configured structlog logger.

    Args:
        name: Optional logger name. If not provided, uses the calling module's name.

    Returns:
        A configured structlog logger instance.

    Example:
        ```python
        from config.logging import get_logger

        log = get_logger(__name__)
        log.info("User logged in", user_id=123, username="john")
        ```
    """
    return structlog.get_logger(name)


__all__ = [
    "setup_logging",
    "get_logger",
    "add_request_context",
    "clear_request_context",
    "get_request_id",
]
