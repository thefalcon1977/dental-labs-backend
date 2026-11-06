"""Token service for token refresh, introspection, and revocation."""

from config.logging import get_logger

from ..helpers.config import is_sso_enabled
from ..helpers.exceptions import AuthDisabledError, KeycloakConnectionError
from ..schemas.token import RefreshTokenResponse
from ..types import IntrospectionDict
from ..utils.keycloak_client import get_keycloak_client

logger = get_logger(__name__)


async def refresh_access_token(refresh_token: str) -> RefreshTokenResponse:
    """Refresh access token using refresh token.

    Args:
        refresh_token: Refresh token

    Returns:
        RefreshTokenResponse with new access and refresh tokens

    Raises:
        KeycloakConnectionError: If unable to connect to Keycloak
    """
    if not is_sso_enabled():
        raise AuthDisabledError()

    keycloak_client = get_keycloak_client()
    if keycloak_client is None:
        raise KeycloakConnectionError()

    logger.debug("Refreshing access token")
    try:
        token_data = await keycloak_client.refresh_token(refresh_token)

        response = RefreshTokenResponse(
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token", refresh_token),
            expires_in=token_data.get("expires_in", 300),
            token_type=token_data.get("token_type", "Bearer"),
        )

        logger.info("Access token refreshed successfully")
        return response

    except Exception as e:
        logger.error(
            "Failed to refresh access token",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise


async def introspect_token(token: str) -> IntrospectionDict:
    """Introspect token to check if it's still valid.

    Args:
        token: Access token to introspect

    Returns:
        Token introspection response

    Raises:
        KeycloakConnectionError: If unable to connect to Keycloak
    """
    keycloak_client = get_keycloak_client()
    if keycloak_client is None:
        raise KeycloakConnectionError()

    logger.debug("Introspecting token")
    try:
        result = await keycloak_client.introspect_token(token)
        logger.debug(
            "Token introspection completed",
            active=result.get("active", False),
        )
        return result
    except Exception as e:
        logger.error(
            "Failed to introspect token",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise


async def revoke_token(token: str) -> None:
    """Revoke token (logout).

    Args:
        token: Token to revoke (can be access or refresh token)

    Raises:
        KeycloakConnectionError: If unable to connect to Keycloak
    """
    if not is_sso_enabled():
        raise AuthDisabledError()

    keycloak_client = get_keycloak_client()
    if keycloak_client is None:
        raise KeycloakConnectionError()

    logger.debug("Revoking token")
    try:
        await keycloak_client.revoke_token(token)
        logger.info("Token revoked successfully")
    except Exception as e:
        logger.error(
            "Failed to revoke token",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise
