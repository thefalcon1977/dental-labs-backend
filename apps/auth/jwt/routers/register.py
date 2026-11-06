"""Local account registration endpoint."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.openapi_responses import RESP_403, RESP_409, RESP_422, RESP_500
from apps.core.db import get_db

from .. import schemas
from ..services import auth_service

router = APIRouter()


@router.post(
    "/register",
    response_model=schemas.LocalUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register local user",
    description=(
        "Create a local account (JWT mode only). Username and email are "
        "case-insensitive and must be unique. New users get "
        "`auth.JWT_DEFAULT_ROLES`. Disabled when "
        "`auth.JWT_REGISTRATION_ENABLED` is false. "
        "Time: O(log n) indexed uniqueness check, n = users · Space: O(1)"
    ),
    responses={
        201: {"description": "User registered"},
        403: RESP_403,
        409: RESP_409,
        422: RESP_422,
        500: RESP_500,
    },
)
async def register(
    data: schemas.RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> schemas.LocalUserResponse:
    """Register a new local account.

    Args:
        data: Registration payload.
        db: Database session (injected).

    Returns:
        The created account.

    Raises:
        RegistrationDisabledError: If self-registration is disabled (403).
        UserAlreadyExistsError: If the username or email is taken (409).
    """
    return await auth_service.register_user(db, data)
