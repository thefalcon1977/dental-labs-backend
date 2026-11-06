"""FastAPI dependencies for authentication."""

from fastapi import Header, Request
from fastapi.security import HTTPBearer

from apps.core.exceptions import UnauthorizedError
from config.logging import get_logger

from ..helpers.config import build_auth_disabled_user, is_auth_enabled
from ..helpers.exceptions import (
    AUTHENTICATION_FAILED_MESSAGE,
    INVALID_TOKEN_MESSAGE,
    InvalidTokenError,
)
from ..schemas.user import UserInfo
from ..utils.jwt_validator import get_jwt_validator

logger = get_logger(__name__)

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    authorization: str | None = Header(None),
) -> UserInfo:
    """Get current authenticated user from Keycloak SSO bearer token.

    Validates the Keycloak token and extracts user information.

    Args:
        request: FastAPI request object
        authorization: Authorization header value

    Returns:
        UserInfo object with user information

    Raises:
        UnauthorizedError: If token is missing or invalid
    """
    if not is_auth_enabled():
        logger.warning("Authentication bypassed because auth is disabled")
        return build_auth_disabled_user()

    validator = get_jwt_validator()

    try:
        # Extract token from Authorization header
        token = validator.extract_token(authorization)

        # Validate token
        payload = await validator.validate_token(token)

        # Extract user info
        user = validator.get_user_from_token(payload)

        # Log successful authentication
        client_ip = request.client.host if request.client else None
        logger.info(
            "User authenticated",
            user_id=user.id,
            username=user.username,
            client_id=user.client_id,
            client_ip=client_ip,
        )

        return user

    except InvalidTokenError as e:
        client_ip = request.client.host if request.client else None
        logger.warning(
            "Authentication failed: invalid token",
            error=str(e),
            client_ip=client_ip,
        )
        raise UnauthorizedError(INVALID_TOKEN_MESSAGE) from e
    except Exception as e:
        client_ip = request.client.host if request.client else None
        logger.error(
            "Authentication error",
            error=str(e),
            error_type=type(e).__name__,
            client_ip=client_ip,
        )
        raise UnauthorizedError(AUTHENTICATION_FAILED_MESSAGE) from e


async def get_optional_user(
    request: Request,
    authorization: str | None = Header(None),
) -> UserInfo | None:
    """Get current user if authenticated, otherwise return None.

    Useful for endpoints that work with or without authentication.

    Args:
        request: FastAPI request object
        authorization: Authorization header value

    Returns:
        UserInfo object if authenticated, None otherwise
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
    authorization: str | None = Header(None),
) -> bool:
    """Verify Keycloak SSO token is valid without extracting user info.

    Args:
        authorization: Authorization header value

    Returns:
        True if token is valid

    Raises:
        UnauthorizedError: If token is missing or invalid
    """
    if not is_auth_enabled():
        logger.warning("Token verification bypassed because auth is disabled")
        return True

    validator = get_jwt_validator()

    try:
        # Extract token
        token = validator.extract_token(authorization)

        # Validate token
        await validator.validate_token(token)

        logger.debug("Token verified successfully")
        return True

    except InvalidTokenError as e:
        logger.warning("Token verification failed", error=str(e))
        raise UnauthorizedError(INVALID_TOKEN_MESSAGE) from e
    except Exception as e:
        logger.error(
            "Token verification error",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise UnauthorizedError(AUTHENTICATION_FAILED_MESSAGE) from e


async def get_current_user_or_system(
    request: Request,
    authorization: str | None = Header(None),
) -> UserInfo:
    """Authenticate via Keycloak SSO bearer token.

    Kept for compatibility with existing endpoint imports. This project now
    supports only Keycloak SSO authentication when auth is enabled.

    Args:
        request: FastAPI request object.
        authorization: Authorization header value.

    Returns:
        Authenticated Keycloak user information.
    """
    if not is_auth_enabled():
        logger.warning("Authentication bypassed because auth is disabled")
        return build_auth_disabled_user()

    return await get_current_user(request, authorization)
