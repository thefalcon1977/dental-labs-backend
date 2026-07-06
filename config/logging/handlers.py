"""Log handlers for console output."""

import logging
import sys

from loguru import logger

from config.settings import settings


def setup_console_handler(log_level: str) -> None:
    """Setup console handler based on environment.

    Args:
        log_level: Log level to use.
    """
    if settings.DEBUG:
        # Development: Colorful, readable format
        logger.add(
            sys.stdout,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
            level=log_level,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )
    else:
        # Production: Simple format - structlog JSONRenderer already formats the message
        # We just output the message as-is (which is already JSON from structlog)
        logger.add(
            sys.stdout,
            format="{message}",
            level=log_level,
            colorize=False,
            backtrace=True,
            diagnose=False,
        )


def setup_third_party_loggers(
    intercept_handler: logging.Handler, log_level: str
) -> None:
    """Configure third-party loggers to use intercept handler.

    Args:
        intercept_handler: Handler to intercept standard library logs.
        log_level: Log level to use.
    """
    sqlalchemy_log_level = getattr(settings.logging, "SQLALCHEMY_LOG_LEVEL", log_level)

    for logger_name in [
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "uvicorn.asgi",
        "uvicorn.lifespan",
        "fastapi",
    ]:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [intercept_handler]
        logging_logger.propagate = False
        logging_logger.setLevel(log_level)

    for logger_name in [
        "sqlalchemy",
        "sqlalchemy.engine",
        "sqlalchemy.pool",
    ]:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [intercept_handler]
        logging_logger.propagate = False
        logging_logger.setLevel(sqlalchemy_log_level)


__all__ = [
    "setup_console_handler",
    "setup_third_party_loggers",
]
