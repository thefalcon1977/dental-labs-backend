"""FastAPI application factory with multi-app support.

This module provides the application factory pattern for creating and configuring
FastAPI applications. It handles:

- Application lifecycle management (startup/shutdown)
- Automatic router discovery from apps directory
- Middleware registration
- Exception handler registration
- Database manager initialization
- System information display on startup
- OpenAPI schema customization

The factory supports a multi-app architecture where each app in the `apps/`
directory can have its own routers, which are automatically discovered and
registered with the main FastAPI application.
"""

import os
import platform
import sys
from contextlib import asynccontextmanager
from importlib import import_module
from pathlib import Path
from typing import TypeAlias

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.responses import ORJSONResponse

from apps.core.db import DatabaseManager
from apps.core.exceptions import register_exception_handlers
from apps.core.middleware import register_middleware
from apps.core.system_info import format_system_info
from apps.core.version import __version__
from config.logging import get_logger
from config.metrics import setup_metrics
from config.settings import settings

# Logging is already configured in manage.py, so we just get the logger here
logger = get_logger(__name__)

# Module-level variable to store workers count (set by main.py)
_workers_count: int | None = None
BindInfo: TypeAlias = tuple[str, int]


def _should_log_startup() -> bool:
    """Check if startup logs should be emitted in this process.

    Returns:
        True if startup logs should be emitted, False otherwise.
    """
    parent_pid = os.environ.get("APP_RELOAD_PARENT_PID")
    if parent_pid and parent_pid == str(os.getpid()):
        return False
    return True


def _get_startup_bind() -> BindInfo:
    """Get the host/port used for startup logging.

    Returns:
        Tuple of (host, port) for the running server.
    """
    host = os.environ.get("APP_RUNSERVER_HOST", settings.HOST)
    port_value = os.environ.get("APP_RUNSERVER_PORT")
    try:
        port = int(port_value) if port_value is not None else settings.PORT
    except ValueError:
        port = settings.PORT
    return host, port


def set_workers_count(count: int) -> None:
    """Set the workers count for startup information display.

    This function is called before app creation to store the calculated
    worker count, which is then displayed in startup logs.

    Args:
        count: Number of workers to use for the application.
    """
    global _workers_count
    _workers_count = count


def get_workers_count() -> int:
    """Get the workers count, defaulting to settings if not set.

    Returns the workers count that was set via `set_workers_count()`, or
    falls back to the configured value from settings if not set.

    Returns:
        Number of workers (from set value or settings default).
    """
    global _workers_count
    return _workers_count if _workers_count is not None else settings.uvicorn.WORKERS


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events.

    Handles application lifecycle events:
    - Startup: Initializes database manager, sets up metrics, displays system info
    - Shutdown: Closes database connections and cleans up resources

    Args:
        app: FastAPI application instance

    Yields:
        None: Control is yielded to the application runtime
    """
    # Startup
    if _should_log_startup():
        logger.info("Application startup initiated")

    # Setup Prometheus metrics
    setup_metrics()

    db_manager = DatabaseManager()
    await db_manager.initialize()
    app.state.db_manager = db_manager

    # Redis (optional — used for OTP session store, rate limiting)
    redis_client = None
    if getattr(settings, "redis", None) and getattr(settings.redis, "ENABLED", False):
        try:
            from redis.asyncio import Redis

            redis_client = Redis(
                host=settings.redis.HOST,
                port=settings.redis.PORT,
                db=settings.redis.DB,
                password=settings.redis.PASSWORD or None,
                ssl=settings.redis.SSL,
                socket_timeout=settings.redis.SOCKET_TIMEOUT,
                socket_connect_timeout=settings.redis.SOCKET_CONNECT_TIMEOUT,
                decode_responses=True,
            )
            await redis_client.ping()
            app.state.redis = redis_client
            if _should_log_startup():
                logger.info(
                    "Redis connected",
                    host=settings.redis.HOST,
                    port=settings.redis.PORT,
                )
        except Exception as e:
            if _should_log_startup():
                logger.warning(
                    "Redis connection failed; OTP and rate limiting will be unavailable",
                    error=str(e),
                )
            app.state.redis = None
    else:
        app.state.redis = None

    # Display startup information
    # Get workers count (set by main.py before app creation)
    workers = get_workers_count()
    workers_max = settings.uvicorn.WORKERS_MAX
    pool_size = settings.database.POOL_SIZE if settings.database.ENABLED else 0
    max_overflow = settings.database.MAX_OVERFLOW if settings.database.ENABLED else 0
    host, port = _get_startup_bind()

    # Log system information
    should_log_startup = _should_log_startup()
    startup_info_mode = getattr(
        settings.logging, "STARTUP_INFO_MODE", "minimal"
    ).lower()
    if startup_info_mode not in {"full", "minimal", "off"}:
        startup_info_mode = "minimal"

    if startup_info_mode == "full":
        if settings.DEBUG and should_log_startup:
            # In development, show pretty banner in Typer style
            format_system_info(
                service_name=settings.SERVICE_NAME,
                version=__version__,
                host=host,
                port=port,
                workers=workers,
                workers_max=workers_max,
                pool_size=pool_size,
                max_overflow=max_overflow,
            )
        elif should_log_startup:
            # In production, log as structured JSON
            from apps.core.system_info import get_system_info

            system_info = get_system_info()
            logger.info(
                "Service startup information",
                service_name=settings.SERVICE_NAME,
                version=__version__,
                environment=system_info["platform"]["system"],
                python_version=system_info["python"]["version"],
                host=host,
                port=port,
                cpu_logical_cores=system_info["cpu"]["logical_cores"],
                cpu_physical_cores=system_info["cpu"]["physical_cores"],
                memory_total_gb=system_info["memory"]["total_gb"],
                memory_available_gb=system_info["memory"]["available_gb"],
                memory_used_percent=system_info["memory"]["percent"],
                gpu_count=system_info["gpu"]["count"],
                workers=workers,
                workers_max=workers_max,
                database_pool_size=pool_size,
                database_max_overflow=max_overflow,
                database_max_connections=pool_size + max_overflow,
            )
    elif startup_info_mode == "minimal" and should_log_startup:
        logger.info(
            "Service startup information",
            service_name=settings.SERVICE_NAME,
            version=__version__,
            environment=f"{platform.system()} {platform.release()}",
            python_version=sys.version.split()[0],
            host=host,
            port=port,
            workers=workers,
            workers_max=workers_max,
            database_pool_size=pool_size,
            database_max_overflow=max_overflow,
            database_max_connections=pool_size + max_overflow,
        )

    if _should_log_startup():
        logger.info(
            "Application startup completed",
            service_name=settings.SERVICE_NAME,
            version=__version__,
            workers=workers,
        )

    yield

    # Shutdown
    if _should_log_startup():
        logger.info("Application shutdown initiated")
    await db_manager.close()
    if hasattr(app.state, "db_manager"):
        del app.state.db_manager
    if hasattr(app.state, "redis") and app.state.redis is not None:
        await app.state.redis.close()
        del app.state.redis
    if _should_log_startup():
        logger.info("Application shutdown completed")


def _docs_urls_from_access() -> tuple[str | None, str | None, str | None]:
    """Return (docs_url, redoc_url, openapi_url) from OPENAPI_DOCS_ACCESS.

    Returns:
        Tuple of URLs for docs, redoc, openapi.json; None means endpoint disabled.
    """
    access = settings.OPENAPI_DOCS_ACCESS
    if access == "disabled":
        return None, None, None
    if access == "public":
        return "/docs", "/redoc", "/openapi.json"
    # developer_only: built-in docs disabled; custom router added later
    return None, None, None


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Creates a new FastAPI application instance with:
    - Custom title, description, and version
    - Conditional OpenAPI docs (OPENAPI_DOCS_ACCESS: disabled | public | developer_only)
    - ORJSONResponse as default response class
    - Registered middleware and exception handlers
    - Automatically discovered routers from apps directory
    - Custom OpenAPI schema generation

    Returns:
        Configured FastAPI application instance ready for use.
    """
    docs_url, redoc_url, openapi_url = _docs_urls_from_access()
    app = FastAPI(
        title="Microservices FastAPI Template",
        description="A FastAPI template for microservices",
        version=__version__,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=lifespan,
        default_response_class=ORJSONResponse,
    )

    # Register middleware
    register_middleware(app)

    # Register exception handlers
    register_exception_handlers(app)

    # Load routers from apps
    load_app_routers(app)

    # Log registered routes for debugging
    if settings.DEBUG and _should_log_startup():
        total_routes = len(app.routes)
        logger.info(
            "Application routes loaded",
            total_routes=total_routes,
            s3_enabled=getattr(settings, "s3", {}).get("ENABLED", False),
        )

    # Custom OpenAPI schema
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        # Server URLs for Swagger UI "Try it out"
        openapi_schema["servers"] = [
            {"url": "http://localhost:8000", "description": "Local Development"},
            {
                "url": "http://185.97.116.114:8000",
                "description": "Production Development",
            },
            {
                "url": "https://iticket.mtnirancell.ir",
                "description": "MTN iTicket Platform",
            },
            {
                "url": "https://iticket.ilabs.ir/post-search",
                "description": "iLabs iTicket Platform",
            },
            {
                "url": "https://post.ilabs.ir/post-search",
                "description": "iLabs Post Platform",
            },
        ]

        # Add security schemes if Keycloak is enabled
        if hasattr(settings, "keycloak") and getattr(
            settings.keycloak, "ENABLED", False
        ):
            openapi_schema["components"]["securitySchemes"] = {
                "HTTPBearer": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "Keycloak JWT token authentication. Use the format: Bearer <token>",
                }
            }
            # Apply security to all endpoints by default
            # Individual endpoints can override this if needed
            if "paths" in openapi_schema:
                for path, methods in openapi_schema["paths"].items():
                    for method, details in methods.items():
                        if isinstance(details, dict) and method.lower() in [
                            "get",
                            "post",
                            "put",
                            "patch",
                            "delete",
                        ]:
                            # Only add security if not already present
                            if "security" not in details:
                                details["security"] = [{"HTTPBearer": []}]

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

    # When docs are developer-only, serve /docs, /redoc, /openapi.json with auth
    if settings.OPENAPI_DOCS_ACCESS == "developer_only":
        from apps.core.openapi_docs import router as openapi_docs_router

        app.include_router(openapi_docs_router)

    return app


def load_app_routers(app: FastAPI) -> None:
    """Dynamically load routers from apps directory.

    Automatically discovers and registers routers from all apps in the
    `apps/` directory. Supports multiple router location patterns:

    1. `apps/{app_name}/routers/router.py` (new layered structure)
    2. `apps/{app_name}/routers.py` (legacy structure)
    3. `apps/{app_name}/api.py` (legacy structure)

    Routers are registered with:
    - Prefix: `/{app_name}`
    - Tags: `[app_name]` for OpenAPI grouping

    The `common` app is always loaded first, followed by all other apps.
    The `core` directory is skipped.

    Args:
        app: FastAPI application instance to register routers with

    Note:
        Import errors are silently ignored, allowing apps to exist without
        routers or with different structures.
    """
    apps_dir = Path(__file__).parent.parent

    # Load common app routers (always loaded)
    try:
        common_module = import_module("apps.common.routers.router")
        if hasattr(common_module, "router"):
            app.include_router(common_module.router, tags=["common"])
    except ImportError:
        # Fallback to legacy api structure
        try:
            common_module = import_module("apps.common.api")
            if hasattr(common_module, "router"):
                app.include_router(common_module.router, tags=["common"])
        except ImportError:
            pass

    # Load other app routers
    for app_dir in apps_dir.iterdir():
        if (
            not app_dir.is_dir()
            or app_dir.name.startswith("_")
            or app_dir.name == "common"
        ):
            continue

        # Skip core directory
        if app_dir.name == "core":
            continue

        # Conditional registration: S3/MinIO router only if enabled
        if app_dir.name == "s3":
            try:
                if not settings.s3.ENABLED:
                    if _should_log_startup():
                        logger.debug(
                            "S3/MinIO is disabled, skipping router registration"
                        )
                    continue
                else:
                    if _should_log_startup():
                        logger.info(
                            "S3/MinIO is enabled, attempting to register router"
                        )
            except (AttributeError, KeyError) as e:
                # S3 settings not configured, skip router
                if _should_log_startup():
                    logger.debug(
                        "S3/MinIO settings not found, skipping router registration",
                        error=str(e),
                    )
                continue

        # Try to import router from:
        # 1. app/routers/router.py (new layered structure)
        # 2. app/routers.py (legacy structure)
        # 3. app/api.py (legacy structure)
        router_paths = [
            f"apps.{app_dir.name}.routers.router",  # New structure: routers/router.py
            f"apps.{app_dir.name}.routers",  # Legacy: routers.py
            f"apps.{app_dir.name}.api",  # Legacy: api.py
        ]

        router_registered = False
        last_error: Exception | None = None
        attempted_paths: list[str] = []
        for module_path in router_paths:
            attempted_paths.append(module_path)
            try:
                module = import_module(module_path)
                if hasattr(module, "router"):
                    app.include_router(
                        module.router,
                        prefix=f"/{app_dir.name}",
                        tags=[app_dir.name],
                    )
                    if _should_log_startup():
                        logger.info(
                            "Router registered",
                            app_name=app_dir.name,
                            prefix=f"/{app_dir.name}",
                            module_path=module_path,
                            route_count=len(module.router.routes),
                        )
                    router_registered = True
                    break  # Found router, no need to check other paths
            except (ImportError, ModuleNotFoundError) as e:
                # Store last error for debugging
                last_error = e
                # Don't log individual import failures - we'll log once at the end if all fail
                continue
            except Exception as e:
                # Store last error for debugging
                last_error = e
                logger.error(
                    "Error registering router",
                    app_name=app_dir.name,
                    module_path=module_path,
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )
                continue

        # Only log if router wasn't found after trying all paths
        # Skip logging for apps that don't have routers (common case)
        if not router_registered:
            # For S3, always log errors since it's conditional
            if app_dir.name == "s3":
                error_msg = str(last_error) if last_error else "Unknown error"
                error_type = type(last_error).__name__ if last_error else "Unknown"
                logger.error(
                    "S3 router not registered - router module not found or import failed",
                    app_name=app_dir.name,
                    checked_paths=attempted_paths,
                    last_error=error_msg,
                    last_error_type=error_type,
                )
            # For other apps, only log at DEBUG level if DEBUG is enabled and startup logging is enabled
            # This prevents noise in production logs for apps that simply don't have routers
            elif settings.DEBUG and _should_log_startup():
                logger.debug(
                    "No router found for app",
                    app_name=app_dir.name,
                    checked_paths=attempted_paths,
                )
