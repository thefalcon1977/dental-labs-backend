"""Refresh token endpoint."""

from fastapi import APIRouter, status

from apps.common.openapi_responses import (
    RESP_401,
    RESP_403,
    RESP_422,
    RESP_500,
    RESP_503,
)
from config.logging import get_logger

from ..schemas.token import RefreshTokenRequest, RefreshTokenResponse
from ..services import token_service

router = APIRouter(tags=["auth"])
logger = get_logger(__name__)


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description=(
        "Refresh an access token using a Keycloak refresh token. "
        "Uses Keycloak SSO when authentication is enabled. "
        "Time: O(1) · Space: O(1)"
    ),
    responses={
        200: {"description": "Token refreshed successfully"},
        401: RESP_401,
        403: RESP_403,
        422: RESP_422,
        500: RESP_500,
        503: RESP_503,
    },
)
async def refresh_token(
    request: RefreshTokenRequest,
) -> RefreshTokenResponse:
    """Refresh access token endpoint.

    Refreshes an expired access token using a valid refresh token.

    Args:
        request: Refresh token request with refresh token

    Returns:
        Refresh token response with new access token and refresh token

    Raises:
        InvalidTokenError: If refresh token is invalid
        KeycloakConnectionError: If unable to connect to Keycloak
    """
    logger.debug("Refreshing token")
    try:
        response = await token_service.refresh_access_token(request.refresh_token)
        logger.info("Token refreshed successfully")
        return response
    except Exception as e:
        logger.error(
            "Failed to refresh token",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise
