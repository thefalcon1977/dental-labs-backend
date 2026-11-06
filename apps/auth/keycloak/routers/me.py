"""Get current user endpoint."""

from fastapi import APIRouter, Depends, status

from apps.common.openapi_responses import RESP_401
from config.logging import get_logger

from ..dependencies.auth import get_current_user_or_system
from ..schemas.user import UserInfo

router = APIRouter(tags=["auth"])
logger = get_logger(__name__)


@router.get(
    "/me",
    response_model=UserInfo,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Get current authenticated user information",
    responses={
        200: {"description": "Current user info"},
        401: RESP_401,
    },
)
async def get_me(
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> UserInfo:
    """Get current authenticated user information.

    Returns the authenticated user's information extracted from the Keycloak token.

    Args:
        current_user: Current authenticated user (injected via dependency)

    Returns:
        UserInfo object with user information
    """
    logger.debug("Getting current user", user_id=current_user.id)
    return current_user
