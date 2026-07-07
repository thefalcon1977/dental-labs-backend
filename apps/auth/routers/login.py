"""Login routes for local authentication."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth import schemas
from apps.auth.helpers.exceptions import InactiveUserError, InvalidCredentialsError
from apps.auth.repository.dal import get_user_by_email, get_user_by_username
from apps.auth.utils.jwt_validator import get_jwt_validator
from apps.auth.utils.password import verify_password
from apps.core.db import get_db

router = APIRouter()


@router.post(
    "/login",
    response_model=schemas.TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Log in user",
    description=(
        "Authenticate a local user with email/username and password. "
        "Time: O(1) - Space: O(1)"
    ),
    responses={
        401: {"description": "Invalid credentials"},
        403: {"description": "User account is inactive"},
    },
)
async def login(
    login_data: schemas.LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> schemas.TokenResponse:
    """Authenticate user and return a local access token.

    Args:
        login_data: Login identifier and password.
        db: Database session.

    Returns:
        Access token response.

    Raises:
        InvalidCredentialsError: If credentials are invalid.
        InactiveUserError: If the user account is inactive.
    """
    identifier = login_data.identifier.strip().lower()
    user = await get_user_by_email(db, identifier)
    if user is None:
        user = await get_user_by_username(db, login_data.identifier.strip())

    if user is None or not verify_password(login_data.password, user.hashed_password):
        raise InvalidCredentialsError()

    if not user.is_active:
        raise InactiveUserError()

    roles = [role.name for role in user.roles or [] if role.is_active]
    groups = [group.name for group in user.groups or [] if group.is_active]
    validator = get_jwt_validator()
    access_token = validator.create_access_token(
        subject=user.id,
        extra_claims={
            "email": user.email,
            "username": user.username,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "is_superuser": user.is_superuser,
            "roles": roles,
            "groups": groups,
        },
    )

    return schemas.TokenResponse(
        access_token=access_token,
        expires_in=validator.access_token_expire_minutes * 60,
    )


__all__ = ["router"]
