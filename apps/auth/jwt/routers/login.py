"""Local login endpoint."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.openapi_responses import RESP_401, RESP_403, RESP_422, RESP_500
from apps.core.db import get_db

from .. import schemas
from ..services import auth_service

router = APIRouter()


@router.post(
    "/login",
    response_model=schemas.TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Log in",
    description=(
        "Authenticate with username (or email) and password and receive an "
        "access/refresh token pair signed by this service (JWT mode). "
        "Time: O(log n) indexed lookup, n = users · Space: O(1)"
    ),
    responses={
        200: {"description": "Authenticated"},
        401: RESP_401,
        403: RESP_403,
        422: RESP_422,
        500: RESP_500,
    },
)
async def login(
    data: schemas.LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> schemas.TokenResponse:
    """Log in with local credentials.

    Args:
        data: Login payload.
        db: Database session (injected).

    Returns:
        Access and refresh tokens plus user info.

    Raises:
        InvalidCredentialsError: If the login or password is wrong (401).
        InactiveUserError: If the account is deactivated (403).
    """
    return await auth_service.login(db, data)
