"""Current local user's profile endpoints."""

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.keycloak.schemas.user import UserInfo
from apps.common.openapi_responses import RESP_401, RESP_403, RESP_422, RESP_500
from apps.core.db import get_db

from .. import schemas
from ..dependencies.auth import get_current_user
from ..services import auth_service
from ..utils.avatars import delete_avatar, resolve_avatar, save_avatar

router = APIRouter()

_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


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


@router.post(
    "/me/avatar",
    response_model=schemas.ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload my avatar",
    description=(
        "Store a JPEG, PNG, GIF, or WEBP profile photo up to 2 MB and set "
        "`avatar_url` to the public file URL."
    ),
    responses={
        200: {"description": "Profile with the new avatar URL"},
        401: RESP_401,
        403: RESP_403,
        422: RESP_422,
        500: RESP_500,
    },
)
async def upload_my_avatar(
    request: Request,
    file: UploadFile = File(..., description="JPEG, PNG, GIF, or WEBP image"),
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.ProfileResponse:
    """Save an uploaded profile photo and store its public URL.

    Args:
        request: Incoming request, used to build the public URL.
        file: Uploaded image.
        current_user: User from the verified access token (injected).
        db: Database session (injected).

    Returns:
        Updated profile.
    """
    relative = save_avatar(current_user.id, await file.read())
    url = f"{str(request.base_url).rstrip('/')}{relative}"
    return await auth_service.update_profile(
        db,
        current_user.id,
        schemas.ProfileUpdate(avatar_url=url),
    )


@router.delete(
    "/me/avatar",
    response_model=schemas.ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove my avatar",
    description="Delete the stored profile photo and clear `avatar_url`.",
    responses={
        200: {"description": "Profile without an avatar"},
        401: RESP_401,
        403: RESP_403,
        500: RESP_500,
    },
)
async def delete_my_avatar(
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.ProfileResponse:
    """Remove the current user's profile photo.

    Args:
        current_user: User from the verified access token (injected).
        db: Database session (injected).

    Returns:
        Updated profile.
    """
    delete_avatar(current_user.id)
    return await auth_service.update_profile(
        db,
        current_user.id,
        schemas.ProfileUpdate(avatar_url=None),
    )


@router.get(
    "/avatars/{filename}",
    status_code=status.HTTP_200_OK,
    summary="Get an avatar image",
    description="Public profile photo. The file name is the user id plus an image extension.",
    responses={404: {"description": "Avatar not found"}},
)
async def get_avatar(filename: str) -> FileResponse:
    """Serve a stored profile photo.

    Args:
        filename: `{user_id}.jpg`, `.png`, `.gif`, or `.webp`.

    Returns:
        The image file.
    """
    path = resolve_avatar(filename)
    media_type = _MEDIA_TYPES.get(path.suffix, "application/octet-stream")
    return FileResponse(
        path,
        media_type=media_type,
        headers={"Cross-Origin-Resource-Policy": "cross-origin"},
    )
