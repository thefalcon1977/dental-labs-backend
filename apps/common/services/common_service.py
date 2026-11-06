"""Business logic for common API endpoints."""

from fastapi import Request

from apps.core.db import check_db_health
from config.logging import get_logger
from config.settings import settings

from ..types import (
    CacheInfoDict,
    ChecksDict,
    DbHealthResult,
    DbInfoDict,
    EndpointDict,
    KeycloakHealthResult,
    KeycloakInfoDict,
    ReadinessResult,
    S3HealthResult,
    S3InfoDict,
)

logger = get_logger(__name__)


async def check_readiness(request: Request) -> ReadinessResult:
    """Check service readiness by verifying all dependencies.

    Args:
        request: FastAPI request object

    Returns:
        Tuple of (checks dictionary, all_ready boolean)
    """
    checks: ChecksDict = {}
    all_ready = True

    # Check database if enabled
    if settings.database.ENABLED:
        try:
            db_ready = await check_db_health(request.app)
            checks["database"] = db_ready
            if not db_ready:
                all_ready = False
        except Exception:
            # If health check fails, mark as not ready
            checks["database"] = False
            all_ready = False

    # Check cache if enabled
    if settings.redis.ENABLED:
        # TODO: Implement cache health check
        # For now, assume cache is ready if enabled
        checks["cache"] = True

    # Check Keycloak if enabled
    try:
        if hasattr(settings, "keycloak") and getattr(
            settings.keycloak, "ENABLED", False
        ):
            keycloak_ready = await check_keycloak_health()
            checks["keycloak"] = keycloak_ready
            if not keycloak_ready:
                all_ready = False
    except Exception as e:
        logger.warning("Keycloak health check failed", error=str(e))
        checks["keycloak"] = False
        all_ready = False

    # Check S3/MinIO if enabled
    try:
        if hasattr(settings, "s3") and settings.s3.ENABLED:
            s3_ready = await check_s3_health()
            checks["s3"] = s3_ready
            if not s3_ready:
                all_ready = False
    except Exception as e:
        logger.warning("S3/MinIO health check failed", error=str(e))
        checks["s3"] = False
        all_ready = False

    return checks, all_ready


async def get_db_health_status(request: Request) -> DbHealthResult:
    """Get database health status.

    Args:
        request: FastAPI request object

    Returns:
        Tuple of (is_healthy boolean, database info dictionary)
    """
    if not settings.database.ENABLED:
        db_info: DbInfoDict = {
            "enabled": False,
            "host": None,
            "port": None,
            "name": None,
        }
        return False, db_info

    is_healthy = await check_db_health(request.app)
    db_info = {
        "enabled": settings.database.ENABLED,
        "host": settings.database.HOST,
        "port": settings.database.PORT,
        "name": settings.database.NAME,
    }

    return is_healthy, db_info


def get_cache_info() -> CacheInfoDict:
    """Get cache configuration information.

    Returns:
        Dictionary with cache configuration
    """
    return {
        "enabled": settings.redis.ENABLED,
        "host": settings.redis.HOST,
        "port": settings.redis.PORT,
        "db": settings.redis.DB,
    }


async def check_keycloak_health() -> bool:
    """Check Keycloak health by attempting to fetch JWKS.

    Returns:
        True if Keycloak is healthy, False otherwise
    """
    try:
        from apps.auth.keycloak.utils.keycloak_client import get_keycloak_client

        client = get_keycloak_client()
        if client is None:
            return False

        # Try to fetch JWKS as a health check
        await client.get_jwks()
        return True
    except Exception as e:
        logger.warning("Keycloak health check failed", error=str(e))
        return False


async def get_keycloak_health_status() -> KeycloakHealthResult:
    """Get Keycloak health status.

    Returns:
        Tuple of (is_healthy boolean, Keycloak info dictionary)
    """
    try:
        if not hasattr(settings, "keycloak"):
            keycloak_info: KeycloakInfoDict = {
                "enabled": False,
                "server_url": None,
                "realm": None,
            }
            return False, keycloak_info

        # Check if Keycloak is enabled
        keycloak_enabled = getattr(settings.keycloak, "ENABLED", False)
        if not keycloak_enabled:
            keycloak_info_disabled: KeycloakInfoDict = {
                "enabled": False,
                "server_url": settings.keycloak.SERVER_URL,
                "realm": settings.keycloak.REALM,
            }
            return False, keycloak_info_disabled

        is_healthy = await check_keycloak_health()
        keycloak_info_enabled: KeycloakInfoDict = {
            "enabled": True,
            "server_url": settings.keycloak.SERVER_URL,
            "realm": settings.keycloak.REALM,
        }

        return is_healthy, keycloak_info_enabled
    except Exception as e:
        logger.warning("Failed to get Keycloak health status", error=str(e))
        keycloak_info_error: KeycloakInfoDict = {
            "enabled": False,
            "server_url": None,
            "realm": None,
        }
        return False, keycloak_info_error


async def check_s3_health() -> bool:
    """Check S3/MinIO health by attempting to list buckets.

    Returns:
        True if S3 is healthy, False otherwise
    """
    try:
        import asyncio

        from apps.s3.utils.s3_client import get_s3_client

        client = get_s3_client()

        # Check if client is properly initialized (has session attribute)
        if not hasattr(client, "session") or client.session is None:
            logger.warning("S3 client not properly initialized")
            return False

        # Try to list buckets as a health check with timeout
        # Use asyncio.wait_for to prevent hanging
        try:
            await asyncio.wait_for(client.list_buckets(), timeout=5.0)
            return True
        except asyncio.TimeoutError:
            logger.warning("S3/MinIO health check timed out")
            return False
    except AttributeError as e:
        # Client not properly initialized
        logger.warning("S3 client not properly initialized", error=str(e))
        return False
    except Exception as e:
        logger.warning(
            "S3/MinIO health check failed", error=str(e), error_type=type(e).__name__
        )
        return False


async def get_s3_health_status() -> S3HealthResult:
    """Get S3/MinIO health status.

    Returns:
        Tuple of (is_healthy boolean, S3 info dictionary)
    """
    try:
        if not hasattr(settings, "s3") or not settings.s3.ENABLED:
            s3_info_disabled: S3InfoDict = {
                "enabled": False,
                "endpoint_url": None,
                "region": None,
            }
            return False, s3_info_disabled

        is_healthy = await check_s3_health()
        s3_info_enabled: S3InfoDict = {
            "enabled": settings.s3.ENABLED,
            "endpoint_url": settings.s3.ENDPOINT_URL,
            "region": settings.s3.REGION,
        }

        return is_healthy, s3_info_enabled
    except Exception as e:
        logger.warning(
            "Failed to get S3 health status",
            error=str(e),
            error_type=type(e).__name__,
        )
        s3_info_error: S3InfoDict = {
            "enabled": False,
            "endpoint_url": None,
            "region": None,
        }
        return False, s3_info_error


def get_available_endpoints() -> EndpointDict:
    """Get list of available endpoints based on current configuration.

    Returns:
        Dictionary mapping endpoint names to their paths
    """
    endpoints: EndpointDict = {
        "health": "/health",
        "live": "/live",
        "ready": "/ready",
        "version": "/version",
    }

    if settings.ENABLE_METRICS:
        endpoints["metrics"] = "/metrics"

    if settings.DEBUG:
        endpoints.update(
            {
                "docs": "/docs",
                "health_db": "/health/db",
                "health_cache": "/health/cache",
            }
        )
        if hasattr(settings, "keycloak"):
            endpoints["health_keycloak"] = "/health/keycloak"
        if hasattr(settings, "s3") and settings.s3.ENABLED:
            endpoints["health_s3"] = "/health/s3"

    return endpoints
