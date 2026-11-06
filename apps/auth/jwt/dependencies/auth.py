"""Bearer-token dependency for local JWT mode.

Validation is stateless (signature, expiry, issuer, type), so authenticated
requests do not hit the database.
"""

from fastapi import Header, Request

from apps.auth.keycloak.helpers.exceptions import (
    AUTHENTICATION_FAILED_MESSAGE,
    INVALID_TOKEN_MESSAGE,
    InvalidTokenError,
    TokenExpiredError,
)
from apps.auth.keycloak.schemas.user import UserInfo
from apps.core.exceptions import UnauthorizedError
from config.logging import get_logger

from ..utils import tokens

logger = get_logger(__name__)


async def get_current_user(
    request: Request,
    authorization: str | None = Header(None),
) -> UserInfo:
    """Authenticate a request with a locally issued access token.

    Args:
        request: FastAPI request object.
        authorization: ``Authorization`` header value.

    Returns:
        User information from the token claims.

    Raises:
        TokenExpiredError: If the access token has expired.
        UnauthorizedError: If the token is missing or invalid.
    """
    client_ip = request.client.host if request.client else None
    try:
        token = tokens.extract_bearer_token(authorization)
        claims = tokens.decode_token(token, tokens.ACCESS_TOKEN_TYPE)
        return tokens.user_info_from_claims(claims)
    except TokenExpiredError:
        logger.info("Authentication failed: token expired", client_ip=client_ip)
        raise
    except InvalidTokenError as e:
        logger.warning("Authentication failed: invalid token", client_ip=client_ip)
        raise UnauthorizedError(INVALID_TOKEN_MESSAGE) from e
    except Exception as e:
        logger.error(
            "Authentication error",
            error_type=type(e).__name__,
            client_ip=client_ip,
        )
        raise UnauthorizedError(AUTHENTICATION_FAILED_MESSAGE) from e
