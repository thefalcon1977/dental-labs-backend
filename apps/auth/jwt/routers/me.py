"""Current local user endpoint."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.keycloak.schemas.user import UserInfo
from apps.common.openapi_responses import RESP_401, RESP_403, RESP_500
from apps.core.db import get_db

from ..dependencies.auth import get_current_user
from ..services import auth_service

router = APIRouter()


@router.get(
    "/me",
    response_model=UserInfo,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description=(
        "Return the authenticated user's current profile from the database "
        "(JWT mode). Requires a bearer access token. "
        "Time: O(1) primary-key lookup · Space: O(1)"
    ),
    responses={
        200: {"description": "Current user info"},
        401: RESP_401,
        403: RESP_403,
        500: RESP_500,
    },
)
async def get_me(
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserInfo:
    """Get the current user's profile.

    Args:
        current_user: User from the verified access token (injected).
        db: Database session (injected).

    Returns:
        Up-to-date user information.

    Raises:
        UnauthorizedError: If the token is missing or invalid (401).
        InactiveUserError: If the account is deactivated (403).
    """
    return await auth_service.get_me(db, current_user.id)
