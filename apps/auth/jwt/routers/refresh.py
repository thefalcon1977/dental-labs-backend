"""Local token refresh endpoint."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.openapi_responses import RESP_401, RESP_403, RESP_422, RESP_500
from apps.core.db import get_db

from .. import schemas
from ..services import auth_service

router = APIRouter()


@router.post(
    "/refresh",
    response_model=schemas.TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description=(
        "Exchange a refresh token for a new access/refresh token pair (JWT mode). "
        "The account is re-checked, so deactivated users cannot refresh. "
        "Time: O(1) primary-key lookup · Space: O(1)"
    ),
    responses={
        200: {"description": "Tokens refreshed"},
        401: RESP_401,
        403: RESP_403,
        422: RESP_422,
        500: RESP_500,
    },
)
async def refresh_token(
    data: schemas.RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> schemas.TokenResponse:
    """Refresh the token pair.

    Args:
        data: Refresh token payload.
        db: Database session (injected).

    Returns:
        New access and refresh tokens.

    Raises:
        InvalidTokenError: If the refresh token is invalid (401).
        TokenExpiredError: If the refresh token has expired (401).
        InactiveUserError: If the account is deactivated (403).
    """
    return await auth_service.refresh(db, data.refresh_token)
