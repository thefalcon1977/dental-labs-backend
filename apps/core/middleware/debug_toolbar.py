"""Debug toolbar middleware configuration for development.

When enabled, this integrates `fastapi-debug-toolbar` to provide a developer
toolbar for request/response inspection and optional SQL query profiling.

The toolbar is only enabled when `settings.DEBUG` is true.
"""

from fastapi import FastAPI

from config.logging import get_logger
from config.settings import settings

logger = get_logger(__name__)

# Track if debug toolbar has been set up to prevent duplicate registration
_debug_toolbar_setup = False


def setup_debug_toolbar(app: FastAPI) -> None:
    """Setup FastAPI Debug Toolbar for development mode.

    This function is idempotent - it can be called multiple times safely.
    Only the first call will set up the toolbar; subsequent calls are ignored.

    The debug toolbar provides:
    - Request/Response inspection
    - SQL query profiling (if SQLAlchemy panel is configured)
    - Performance metrics
    - Template debugging
    - Interactive debugger

    Args:
        app: FastAPI application instance
    """
    global _debug_toolbar_setup

    if not settings.DEBUG:
        logger.debug("Debug toolbar disabled (not in DEBUG mode)")
        return

    # If already set up, skip
    if _debug_toolbar_setup:
        return

    try:
        # Import DebugToolbarMiddleware from fastapi-debug-toolbar
        # The package uses debug_toolbar namespace (compatible with Django Debug Toolbar)
        from debug_toolbar.middleware import DebugToolbarMiddleware  # noqa: PLC0415

        # Configure panels for SQLAlchemy if database is enabled
        panels = None
        if settings.database.ENABLED:
            try:
                # Add SQLAlchemy panel for query profiling
                panels = ["debug_toolbar.panels.sqlalchemy.SQLAlchemyPanel"]
            except (ImportError, AttributeError):
                # SQLAlchemy panel not available, use default panels
                logger.debug("SQLAlchemy panel not available for debug toolbar")

        # Add debug toolbar middleware
        # It should be added early in the middleware stack to capture all requests
        if panels:
            app.add_middleware(DebugToolbarMiddleware, panels=panels)
        else:
            app.add_middleware(DebugToolbarMiddleware)

        # Mark as set up
        _debug_toolbar_setup = True

        logger.info("FastAPI Debug Toolbar enabled")
    except ImportError as e:
        logger.warning(
            "fastapi-debug-toolbar not installed or import failed. "
            "Install it with: poetry add --group dev fastapi-debug-toolbar",
            error=str(e),
        )
