"""Current local user's profile endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.keycloak.schemas.user import UserInfo
from apps.common.openapi_responses import RESP_401, RESP_403, RESP_422, RESP_500
from apps.core.db import get_db

from .. import schemas
from ..dependencies.auth import get_current_user
from ..services import auth_service

router = APIRouter()


@router.get(
    "/me/profile",
    response_model=schemas.ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get my profile",
    description=(
        "Return the authenticated user's profile (JWT mode). Fields the user "
        "has not set are null. Time: O(1) indexed lookup · Space: O(1)"
    ),
    responses={
        200: {"description": "Profile"},
        401: RESP_401,
        500: RESP_500,
    },
)
async def get_my_profile(
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.ProfileResponse:
    """Get the current user's profile.

    Args:
        current_user: User from the verified access token (injected).
        db: Database session (injected).

    Returns:
        Profile response.

    Raises:
        UnauthorizedError: If the token is missing or invalid (401).
    """
    return await auth_service.get_profile(db, current_user.id)


@router.patch(
    "/me/profile",
    response_model=schemas.ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update my profile",
    description=(
        "Partially update the authenticated user's profile (JWT mode). Only "
        "fields present in the body change; send `null` to clear a field. "
        "`timezone` must be an IANA name (e.g. `Asia/Tehran`). "
        "Time: O(1) indexed lookup and update · Space: O(1)"
    ),
    responses={
        200: {"description": "Profile updated"},
        401: RESP_401,
        403: RESP_403,
        422: RESP_422,
        500: RESP_500,
    },
)
async def update_my_profile(
    data: schemas.ProfileUpdate,
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.ProfileResponse:
    """Update the current user's profile.

    Args:
        data: Partial profile update.
        current_user: User from the verified access token (injected).
        db: Database session (injected).

    Returns:
        Updated profile.

    Raises:
        UnauthorizedError: If the token is missing or invalid (401).
        InactiveUserError: If the account is deactivated (403).
    """
    return await auth_service.update_profile(db, current_user.id, data)
