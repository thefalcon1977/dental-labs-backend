"""Authentication service for user authentication orchestration."""

from apps.core.exceptions import UnauthorizedError
from config.logging import get_logger

from ..helpers.config import is_sso_enabled
from ..helpers.exceptions import (
    AuthDisabledError,
    InvalidTokenError,
    KeycloakConnectionError,
    TokenExpiredError,
)
from ..schemas.user import UserInfo
from ..types import TokenDataDict, UserInfoDict
from ..utils.jwt_validator import get_jwt_validator
from .token_service import revoke_token

logger = get_logger(__name__)


async def validate_user_token(token: str) -> UserInfo:
    """Validate user token and return user information.

    Args:
        token: JWT access token

    Returns:
        UserInfo object with user information

    Raises:
        InvalidTokenError: If token is invalid
        TokenExpiredError: If token is expired
    """
    validator = get_jwt_validator()

    logger.debug("Validating user token")
    try:
        # Validate token
        payload = await validator.validate_token(token)

        # Extract user info
        user = validator.get_user_from_token(payload)

        logger.info(
            "User token validated",
            user_id=user.id,
            username=user.username,
        )

        return user

    except (InvalidTokenError, TokenExpiredError):
        raise
    except KeycloakConnectionError:
        raise
    except UnauthorizedError:
        raise
    except Exception as e:
        logger.error(
            "Failed to validate user token",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise


async def get_user_info(token: str) -> UserInfoDict:
    """Get user information from Keycloak.

    Args:
        token: Access token

    Returns:
        User information dictionary from Keycloak

    Raises:
        KeycloakConnectionError: If unable to connect to Keycloak
    """
    from ..utils.keycloak_client import get_keycloak_client

    keycloak_client = get_keycloak_client()
    if keycloak_client is None:
        raise KeycloakConnectionError()

    logger.debug("Fetching user info from Keycloak")
    try:
        user_info = await keycloak_client.get_user_info(token)
        logger.debug(
            "User info fetched",
            user_id=user_info.get("sub"),
            username=user_info.get("preferred_username"),
        )
        return user_info
    except KeycloakConnectionError:
        raise
    except UnauthorizedError:
        raise
    except Exception as e:
        logger.error(
            "Failed to get user info",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise


async def login_user(username: str, password: str) -> TokenDataDict:
    """Login user with username and password.

    Args:
        username: Username for authentication
        password: Password for authentication

    Returns:
        Token response dictionary with access_token, refresh_token, etc.

    Raises:
        UnauthorizedError: If credentials are invalid
        KeycloakConnectionError: If unable to connect to Keycloak
    """
    if not is_sso_enabled():
        raise AuthDisabledError()

    from ..utils.keycloak_client import get_keycloak_client

    keycloak_client = get_keycloak_client()
    if keycloak_client is None:
        raise KeycloakConnectionError()

    logger.debug("Logging in user", username=username)
    try:
        token_data = await keycloak_client.login_with_password(username, password)
        logger.info("User logged in successfully", username=username)
        return token_data
    except UnauthorizedError:
        raise
    except KeycloakConnectionError:
        raise
    except Exception as e:
        logger.error(
            "Failed to login user",
            error=str(e),
            error_type=type(e).__name__,
            username=username,
        )
        raise


async def logout_user(access_token: str, refresh_token: str | None = None) -> None:
    """Handle user logout by revoking tokens.

    Args:
        access_token: Access token to revoke
        refresh_token: Optional refresh token to revoke

    Raises:
        KeycloakConnectionError: If unable to connect to Keycloak
    """
    if not is_sso_enabled():
        raise AuthDisabledError()

    logger.debug("Logging out user")
    try:
        # Revoke access token
        await revoke_token(access_token)

        # Revoke refresh token if provided
        if refresh_token:
            await revoke_token(refresh_token)

        logger.info("User logged out successfully")
    except KeycloakConnectionError:
        raise
    except Exception as e:
        logger.error(
            "Failed to logout user",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise
