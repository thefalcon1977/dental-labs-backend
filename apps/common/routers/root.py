"""Root and version endpoints."""

from fastapi import APIRouter, status

from apps.core.version import __version__
from config.logging import get_logger
from config.settings import settings

from .. import schemas, services

router = APIRouter()
logger = get_logger(__name__)


@router.get(
    "/",
    response_model=schemas.RootResponse,
    status_code=status.HTTP_200_OK,
    summary="Root endpoint",
    description="Returns available endpoints",
)
async def root() -> schemas.RootResponse:
    """Root endpoint with available routes."""
    logger.debug("Root endpoint accessed")

    endpoints = services.get_available_endpoints()
    logger.info("Root endpoint response prepared", endpoint_count=len(endpoints))

    return schemas.RootResponse(
        message="Microservices FastAPI Template",
        endpoints=endpoints,
    )


@router.get(
    "/version",
    response_model=schemas.VersionResponse,
    status_code=status.HTTP_200_OK,
    summary="Version information",
    description="Get application version and environment information",
)
async def version() -> schemas.VersionResponse:
    """Version information endpoint."""
    return schemas.VersionResponse(
        version=__version__,
        environment=settings.current_env or "default",
        debug=settings.DEBUG,
    )
