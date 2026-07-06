"""Command to run the FastAPI application server."""

import os

import typer
import uvicorn

from config.logging import get_logger
from config.settings import settings

from .utils import calculate_workers

logger = get_logger(__name__)


def runserver(
    host: str | None = typer.Option(
        None,
        "--host",
        "-h",
        help="Host to bind to (default: from settings.HOST)",
    ),
    port: int | None = typer.Option(
        None,
        "--port",
        "-p",
        help="Port to bind to (default: from settings.PORT)",
        min=1,
        max=65535,
    ),
    reload: bool | None = typer.Option(
        None,
        "--reload/--no-reload",
        help="Enable auto-reload (default: from settings.DEBUG)",
    ),
    workers: int | None = typer.Option(
        None,
        "--workers",
        "-w",
        help="Number of worker processes (overrides calculated workers)",
        min=1,
    ),
    log_level: str | None = typer.Option(
        None,
        "--log-level",
        "-l",
        help="Log level (default: from settings.LOG_LEVEL)",
    ),
) -> None:
    """Run the FastAPI application server.

    Starts the FastAPI application using uvicorn with configurable options.
    Options can override settings from configuration files.

    Examples:
        # Run with default settings
        python manage.py runserver

        # Run on custom host and port
        python manage.py runserver --host 127.0.0.1 --port 9000

        # Run with auto-reload enabled
        python manage.py runserver --reload

        # Run with specific number of workers
        python manage.py runserver --workers 4

        # Run with custom log level
        python manage.py runserver --log-level DEBUG
    """
    import manage

    fastapi_app = manage.app

    # Calculate workers if not provided
    if workers is None:
        workers = calculate_workers()
    fastapi_app.state.workers = workers

    # Build uvicorn config with overrides
    uvicorn_config = {
        "app": "manage:app",
        "host": host or settings.HOST,
        "port": port or settings.PORT,
        "reload": reload if reload is not None else settings.DEBUG,
        "log_level": (log_level or settings.LOG_LEVEL).lower(),
        "access_log": True,
        "log_config": None,  # Use our custom logging configuration
        "timeout_keep_alive": settings.uvicorn.TIMEOUT_KEEP_ALIVE,
        "limit_concurrency": settings.uvicorn.LIMIT_CONCURRENCY,
        "limit_max_requests": settings.uvicorn.LIMIT_MAX_REQUESTS,
        "backlog": settings.uvicorn.BACKLOG,
    }

    # Add workers if not in debug/reload mode
    if not uvicorn_config["reload"] and workers > 1:
        logger.info(
            "Starting application with multiple workers",
            workers=workers,
            max_workers=settings.uvicorn.WORKERS_MAX,
            host=uvicorn_config["host"],
            port=uvicorn_config["port"],
        )
        uvicorn_config["workers"] = workers
    else:
        logger.info(
            "Starting application in single worker mode",
            reason="reload enabled" if uvicorn_config["reload"] else "workers=1",
            host=uvicorn_config["host"],
            port=uvicorn_config["port"],
        )

    os.environ["APP_RUNSERVER_HOST"] = uvicorn_config["host"]
    os.environ["APP_RUNSERVER_PORT"] = str(uvicorn_config["port"])

    uvicorn.run(**uvicorn_config)
