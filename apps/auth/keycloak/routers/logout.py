"""Logout endpoint for user session termination."""

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import ORJSONResponse

from apps.common.openapi_responses import RESP_401, RESP_403, RESP_500
from config.logging import get_logger

from ..dependencies.auth import get_current_user_or_system
from ..schemas.user import UserInfo
from ..services import auth_service
from ..utils.jwt_validator import get_jwt_validator

router = APIRouter(tags=["auth"])
logger = get_logger(__name__)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout user",
    description=(
        "Logout by revoking access and refresh tokens. "
        "Uses Keycloak SSO when authentication is enabled. "
        "Time: O(1) · Space: O(1)"
    ),
    responses={
        200: {"description": "Logged out successfully"},
        401: RESP_401,
        403: RESP_403,
        500: RESP_500,
    },
)
async def logout(
    request: Request,
    current_user: UserInfo = Depends(get_current_user_or_system),
    authorization: str | None = Header(None),
    refresh_token: str | None = Header(None, alias="X-Refresh-Token"),
) -> ORJSONResponse:
    """Logout user endpoint.

    Revokes the access token and optionally the refresh token to terminate the user session.
    Requires a valid Bearer token.

    Args:
        request: FastAPI request object
        current_user: Authenticated user (injected)
        authorization: Authorization header with Bearer token
        refresh_token: Optional refresh token in X-Refresh-Token header

    Returns:
        ORJSONResponse with logout confirmation message
    """
    validator = get_jwt_validator()

    try:
        access_token = validator.extract_token(authorization) or ""

        # Logout user
        await auth_service.logout_user(
            access_token=access_token,
            refresh_token=refresh_token,
        )

        logger.info("User logged out successfully")
        return ORJSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Logged out successfully"},
        )
    except Exception as e:
        logger.error(
            "Failed to logout user",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise
