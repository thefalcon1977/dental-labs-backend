"""Health check endpoints."""

from fastapi import APIRouter, Request, status
from fastapi.responses import ORJSONResponse

from apps.core.version import __version__
from config.logging import get_logger

from .. import schemas, services

router = APIRouter()
logger = get_logger(__name__)


@router.get(
    "/health",
    response_model=schemas.HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Basic health check endpoint",
)
async def health() -> schemas.HealthResponse:
    """Health check endpoint."""
    return schemas.HealthResponse(status="healthy", version=__version__)


@router.get(
    "/live",
    response_model=schemas.LiveResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
    description="Kubernetes liveness probe endpoint",
)
async def live() -> schemas.LiveResponse:
    """Liveness check endpoint."""
    return schemas.LiveResponse(status="alive")


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Kubernetes readiness probe endpoint. Returns 200 if ready, 503 if not ready.",
    responses={
        200: {"description": "Service is ready to accept traffic"},
        503: {"description": "Service is not ready (dependencies unavailable)"},
    },
)
async def ready(request: Request) -> ORJSONResponse:
    """Readiness check endpoint for Kubernetes.

    Returns:
        - 200 OK: Service is ready to accept traffic
        - 503 Service Unavailable: Service is not ready (dependencies unavailable)

    Kubernetes will:
        - Remove pod from service endpoints if 503 is returned
        - Only count pods returning 200 as ready for HPA scaling
    """
    checks, all_ready = await services.check_readiness(request)

    # Return appropriate status code for Kubernetes
    if all_ready:
        return ORJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ready",
                "checks": checks,
            },
        )
    else:
        return ORJSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "checks": checks,
            },
        )
