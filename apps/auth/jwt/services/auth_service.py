"""Service layer for local JWT registration, login, refresh, and profile."""

from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.config import is_jwt_mode
from apps.auth.keycloak.helpers.exceptions import AuthDisabledError, InvalidTokenError
from apps.auth.keycloak.schemas.user import UserInfo, UserPermissions, UserRoles
from config.logging import get_logger
from config.settings import settings

from .. import schemas
from ..helpers.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
    RegistrationDisabledError,
)
from ..models import LocalUser
from ..repository import bll, dal
from ..types import UserAccess
from ..utils import tokens
from ..utils.passwords import DUMMY_PASSWORD_HASH, verify_password

logger = get_logger(__name__)


def _ensure_enabled() -> None:
    """Reject calls when local JWT auth is not the active provider.

    Raises:
        AuthDisabledError: If auth is disabled or ``auth.MODE`` is not ``jwt``.
    """
    if not is_jwt_mode():
        raise AuthDisabledError()


def build_user_info(user: LocalUser, access: UserAccess) -> UserInfo:
    """Convert a stored user into the shared ``UserInfo`` shape.

    Args:
        user: Local user model.
        access: The user's effective roles, groups, and permissions.

    Returns:
        User information identical in shape to Keycloak mode.
    """
    full_name = " ".join(p for p in (user.first_name, user.last_name) if p) or None
    return UserInfo(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=full_name,
        roles=UserRoles(realm_roles=access.roles, client_roles={}),
        permissions=UserPermissions(permissions=access.permissions),
        groups=access.groups,
        client_id=None,
        realm=None,
        claims={},
    )


async def _issue_tokens(db: AsyncSession, user: LocalUser) -> schemas.TokenResponse:
    """Resolve the user's current access and issue a fresh token pair.

    Args:
        db: Database session.
        user: Authenticated, active user.

    Returns:
        Token response including the user's info.
    """
    access = await dal.get_user_access(db, user.id)
    access_token, expires_in = tokens.create_access_token(user, access)
    refresh_token, refresh_expires_in = tokens.create_refresh_token(user)
    return schemas.TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        refresh_expires_in=refresh_expires_in,
        user=build_user_info(user, access),
    )


async def register_user(
    db: AsyncSession, data: schemas.RegisterRequest
) -> schemas.LocalUserResponse:
    """Register a new local account.

    Args:
        db: Database session.
        data: Registration payload.

    Returns:
        The created account.

    Raises:
        AuthDisabledError: If JWT mode is not active.
        RegistrationDisabledError: If ``auth.JWT_REGISTRATION_ENABLED`` is false.
        UserAlreadyExistsError: If the username or email is taken.
    """
    _ensure_enabled()
    if not settings.auth.JWT_REGISTRATION_ENABLED:
        raise RegistrationDisabledError()

    user = await bll.create_user(db, data)
    logger.info("Local user registered", user_id=user.id)
    return schemas.LocalUserResponse.model_validate(user)


async def login(db: AsyncSession, data: schemas.LoginRequest) -> schemas.TokenResponse:
    """Authenticate with username/email and password.

    Args:
        db: Database session.
        data: Login payload.

    Returns:
        Access and refresh tokens.

    Raises:
        AuthDisabledError: If JWT mode is not active.
        InvalidCredentialsError: If the login or password is wrong.
        InactiveUserError: If the account is deactivated.
    """
    _ensure_enabled()
    user = await dal.get_user_by_login(db, data.username)
    password_ok = await verify_password(
        data.password, user.password_hash if user else DUMMY_PASSWORD_HASH
    )
    if user is None or not password_ok:
        logger.warning("Local login failed", reason="invalid_credentials")
        raise InvalidCredentialsError()
    if not user.is_active:
        logger.warning("Local login rejected", user_id=user.id, reason="inactive")
        raise InactiveUserError()

    user = await bll.record_login(db, user)
    logger.info("Local user logged in", user_id=user.id)
    return await _issue_tokens(db, user)


async def refresh(db: AsyncSession, refresh_token: str) -> schemas.TokenResponse:
    """Exchange a refresh token for a new token pair.

    The user is re-loaded so deactivated or deleted accounts cannot refresh.

    Args:
        db: Database session.
        refresh_token: Refresh token from a previous login or refresh.

    Returns:
        New access and refresh tokens.

    Raises:
        AuthDisabledError: If JWT mode is not active.
        InvalidTokenError: If the token is invalid or the user no longer exists.
        TokenExpiredError: If the refresh token has expired.
        InactiveUserError: If the account is deactivated.
    """
    _ensure_enabled()
    claims = tokens.decode_token(refresh_token, tokens.REFRESH_TOKEN_TYPE)
    user = await dal.get_user_by_id(db, claims["sub"])
    if user is None:
        raise InvalidTokenError()
    if not user.is_active:
        raise InactiveUserError()
    return await _issue_tokens(db, user)


async def get_profile(db: AsyncSession, user_id: str) -> schemas.ProfileResponse:
    """Return the user's profile (empty for accounts created before profiles).

    Args:
        db: Database session.
        user_id: ``sub`` of the verified access token.

    Returns:
        Profile response.
    """
    profile = await dal.get_profile_by_user_id(db, user_id)
    if profile is None:
        return schemas.ProfileResponse(user_id=user_id)
    return schemas.ProfileResponse.model_validate(profile)


async def update_profile(
    db: AsyncSession, user_id: str, data: schemas.ProfileUpdate
) -> schemas.ProfileResponse:
    """Update the user's profile.

    Args:
        db: Database session.
        user_id: ``sub`` of the verified access token.
        data: Partial profile update.

    Returns:
        Updated profile.

    Raises:
        InvalidTokenError: If the user no longer exists.
        InactiveUserError: If the account is deactivated.
    """
    user = await dal.get_user_by_id(db, user_id)
    if user is None:
        raise InvalidTokenError()
    if not user.is_active:
        raise InactiveUserError()

    profile = await bll.update_profile(db, user_id, data)
    logger.info(
        "Local user profile updated",
        user_id=user_id,
        fields=sorted(data.model_fields_set),
    )
    return schemas.ProfileResponse.model_validate(profile)


async def get_me(db: AsyncSession, user_id: str) -> UserInfo:
    """Load the current user's up-to-date profile.

    Args:
        db: Database session.
        user_id: ``sub`` of the verified access token.

    Returns:
        Current user information.

    Raises:
        InvalidTokenError: If the user no longer exists.
        InactiveUserError: If the account is deactivated.
    """
    user = await dal.get_user_by_id(db, user_id)
    if user is None:
        raise InvalidTokenError()
    if not user.is_active:
        raise InactiveUserError()
    return build_user_info(user, await dal.get_user_access(db, user.id))
