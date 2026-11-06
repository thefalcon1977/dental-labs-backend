"""Prometheus metrics endpoint with authentication support."""

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from config.metrics import get_metrics
from config.settings import settings

from ..dependencies.metrics_auth import verify_metrics_access

router = APIRouter()

# Metrics endpoint (if enabled)
if settings.ENABLE_METRICS:

    @router.get(
        "/metrics",
        summary="Prometheus metrics",
        description=(
            "Prometheus metrics endpoint. "
            "Requires authentication if metrics authentication is enabled. "
            "Supports Basic Auth (username/password) or Bearer Token authentication. "
            "Time: O(1) · Space: O(1)"
        ),
        response_class=Response,
        responses={
            200: {"description": "Metrics data in Prometheus format"},
            401: {"description": "Authentication required or invalid credentials"},
        },
    )
    async def metrics(
        _: bool = Depends(verify_metrics_access),
    ) -> Response:
        """Prometheus metrics endpoint.

        Returns metrics in Prometheus text format.
        Authentication is required if metrics authentication is enabled.

        Returns:
            Response with Prometheus metrics data

        Raises:
            UnauthorizedError: If authentication fails (when enabled)
        """
        metrics_data = get_metrics()
        return Response(
            content=metrics_data,
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )
