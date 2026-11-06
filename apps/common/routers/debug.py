"""Debug-only endpoints."""

from fastapi import APIRouter, Request, status
from fastapi.responses import ORJSONResponse

from config.logging import get_logger
from config.settings import settings

from .. import services

router = APIRouter()
logger = get_logger(__name__)

# Debug-only endpoints
if settings.DEBUG:

    @router.get(
        "/health/db",
        status_code=status.HTTP_200_OK,
        summary="Database health check (Debug)",
        description="Database connection health check (only available in debug mode)",
    )
    async def health_db(request: Request) -> ORJSONResponse:
        """Database health check endpoint (debug only)."""
        if not settings.database.ENABLED:
            return ORJSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "disabled",
                    "message": "Database is not enabled",
                },
            )

        is_healthy, db_info = await services.get_db_health_status(request)
        status_code = (
            status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        )

        return ORJSONResponse(
            status_code=status_code,
            content={
                "status": "healthy" if is_healthy else "unhealthy",
                "database": db_info,
            },
        )

    @router.get(
        "/health/cache",
        status_code=status.HTTP_200_OK,
        summary="Cache health check (Debug)",
        description="Cache connection health check (only available in debug mode)",
    )
    async def health_cache() -> ORJSONResponse:
        """Cache health check endpoint (debug only)."""
        if not settings.redis.ENABLED:
            return ORJSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "disabled",
                    "message": "Cache is not enabled",
                },
            )

        # TODO: Implement actual Redis health check
        cache_info = services.get_cache_info()
        return ORJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "healthy",
                "cache": cache_info,
            },
        )

    @router.get(
        "/health/keycloak",
        status_code=status.HTTP_200_OK,
        summary="Keycloak health check (Debug)",
        description="Keycloak connection health check (only available in debug mode)",
    )
    async def health_keycloak() -> ORJSONResponse:
        """Keycloak health check endpoint (debug only)."""
        if not hasattr(settings, "keycloak"):
            return ORJSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "disabled",
                    "message": "Keycloak is not configured",
                },
            )

        if not getattr(settings.keycloak, "ENABLED", False):
            return ORJSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "disabled",
                    "message": "Keycloak is not enabled",
                },
            )

        is_healthy, keycloak_info = await services.get_keycloak_health_status()
        status_code = (
            status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        )

        return ORJSONResponse(
            status_code=status_code,
            content={
                "status": "healthy" if is_healthy else "unhealthy",
                "keycloak": keycloak_info,
            },
        )

    @router.get(
        "/health/s3",
        status_code=status.HTTP_200_OK,
        summary="S3/MinIO health check (Debug)",
        description="S3/MinIO connection health check (only available in debug mode)",
    )
    async def health_s3() -> ORJSONResponse:
        """S3/MinIO health check endpoint (debug only)."""
        if not hasattr(settings, "s3") or not settings.s3.ENABLED:
            return ORJSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "disabled",
                    "message": "S3/MinIO is not enabled",
                },
            )

        is_healthy, s3_info = await services.get_s3_health_status()
        status_code = (
            status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        )

        return ORJSONResponse(
            status_code=status_code,
            content={
                "status": "healthy" if is_healthy else "unhealthy",
                "s3": s3_info,
            },
        )
