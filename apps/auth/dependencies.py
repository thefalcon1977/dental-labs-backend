"""Authentication dependencies for use by any app.

These dispatch to the provider selected by ``auth.MODE`` (``sso`` for Keycloak,
``jwt`` for local accounts). Both return the same ``UserInfo`` shape, so
endpoints don't need to know which provider is active.
"""

from fastapi import Header, Request

from apps.core.exceptions import UnauthorizedError
from config.logging import get_logger

from .config import AuthMode, build_auth_disabled_user, get_auth_mode, is_auth_enabled
from .jwt.dependencies import auth as jwt_auth
from .keycloak.dependencies import auth as keycloak_auth
from .keycloak.schemas.user import UserInfo

logger = get_logger(__name__)


async def get_current_user(
    request: Request,
    authorization: str | None = Header(None),
) -> UserInfo:
    """Authenticate the request with the configured provider.

    Args:
        request: FastAPI request object.
        authorization: ``Authorization`` header value.

    Returns:
        Authenticated user, or a synthetic user when auth is disabled.

    Raises:
        UnauthorizedError: If the token is missing or invalid.
        TokenExpiredError: If a local JWT access token has expired.
    """
    if not is_auth_enabled():
        logger.warning("Authentication bypassed because auth is disabled")
        return build_auth_disabled_user()

    if get_auth_mode() is AuthMode.JWT:
        return await jwt_auth.get_current_user(request, authorization)
    return await keycloak_auth.get_current_user(request, authorization)


async def get_optional_user(
    request: Request,
    authorization: str | None = Header(None),
) -> UserInfo | None:
    """Return the authenticated user, or None when no valid token is sent.

    Args:
        request: FastAPI request object.
        authorization: ``Authorization`` header value.

    Returns:
        Authenticated user or None.
    """
    if not is_auth_enabled():
        return build_auth_disabled_user()
    if not authorization:
        return None
    try:
        return await get_current_user(request, authorization)
    except UnauthorizedError:
        return None


async def verify_token(
    request: Request,
    authorization: str | None = Header(None),
) -> bool:
    """Require a valid token without using the user.

    Args:
        request: FastAPI request object.
        authorization: ``Authorization`` header value.

    Returns:
        True when the token is valid (or auth is disabled).

    Raises:
        UnauthorizedError: If the token is missing or invalid.
    """
    await get_current_user(request, authorization)
    return True


__all__ = [
    "UserInfo",
    "get_current_user",
    "get_optional_user",
    "verify_token",
]
