"""Metrics authentication dependency for Prometheus/Grafana access.

This module provides authentication for metrics endpoints using either:
- Basic Authentication (username/password) - recommended for Prometheus scraping
- Bearer Token Authentication (static token) - alternative method

This is separate from user authentication and designed for system-to-system
communication between Prometheus/Grafana and the metrics endpoint.
"""

from typing import Annotated

from fastapi import Header, Request, Security
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
)

from apps.core.exceptions import UnauthorizedError
from config.logging import get_logger
from config.settings import settings

logger = get_logger(__name__)

# Security schemes
_http_basic = HTTPBasic(auto_error=False)
_http_bearer = HTTPBearer(auto_error=False)


async def verify_metrics_access(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    credentials: HTTPBasicCredentials | None = Security(_http_basic),
    bearer_token: HTTPAuthorizationCredentials | None = Security(_http_bearer),
) -> bool:
    """Verify access to metrics endpoint.

    Supports both Basic Authentication and Bearer Token authentication.
    This is separate from user authentication and designed for Prometheus/Grafana.

    Args:
        request: FastAPI request object
        authorization: Authorization header value (for manual parsing if needed)
        credentials: HTTP Basic credentials (if using Basic Auth)
        bearer_token: HTTP Bearer token (if using Bearer Auth)

    Returns:
        True if authentication is successful

    Raises:
        UnauthorizedError: If authentication fails or is missing

    Note:
        - If AUTH_ENABLED is False, authentication is bypassed
        - Basic Auth: Use username/password from settings
        - Bearer Auth: Use static token from settings
    """
    # If metrics auth is disabled, allow access
    try:
        auth_enabled = settings.metrics.AUTH_ENABLED
    except AttributeError:
        # Metrics section not configured, allow access
        return True

    if not auth_enabled:
        return True

    try:
        auth_method = settings.metrics.AUTH_METHOD
    except AttributeError:
        auth_method = "basic"

    client_ip = request.client.host if request.client else None

    # Basic Authentication
    if auth_method == "basic":
        if not credentials:
            logger.warning(
                "Metrics access denied: missing Basic Auth credentials",
                client_ip=client_ip,
            )
            raise UnauthorizedError(
                message="Metrics endpoint requires Basic Authentication",
                details={"method": "basic"},
            )

        try:
            expected_username = settings.metrics.AUTH_USERNAME
            expected_password = settings.metrics.AUTH_PASSWORD
        except AttributeError:
            logger.error(
                "Metrics Basic Auth not configured",
                client_ip=client_ip,
            )
            raise UnauthorizedError(
                message="Metrics authentication misconfigured",
                details={"method": "basic"},
            )

        # Normalize values: convert to string and strip whitespace
        # This handles cases where env vars might have trailing spaces or type mismatches
        expected_username_str = (
            str(expected_username).strip() if expected_username else ""
        )
        expected_password_str = (
            str(expected_password).strip() if expected_password else ""
        )
        provided_username_str = (
            credentials.username.strip() if credentials.username else ""
        )
        provided_password_str = (
            credentials.password.strip() if credentials.password else ""
        )

        # Debug logging (only in debug mode to avoid logging passwords in production)
        if settings.DEBUG:
            logger.debug(
                "Metrics auth validation",
                client_ip=client_ip,
                provided_username=provided_username_str,
                expected_username=expected_username_str,
                username_match=provided_username_str == expected_username_str,
                password_match=provided_password_str == expected_password_str,
                expected_password_length=len(expected_password_str),
                provided_password_length=len(provided_password_str),
                expected_password_type=type(expected_password).__name__,
                provided_password_type=type(credentials.password).__name__,
                expected_password_repr=repr(expected_password_str[:3]) + "..."
                if len(expected_password_str) > 3
                else repr(expected_password_str),
                provided_password_repr=repr(provided_password_str[:3]) + "..."
                if len(provided_password_str) > 3
                else repr(provided_password_str),
            )

        # Validate credentials (using normalized strings)
        if (
            provided_username_str != expected_username_str
            or provided_password_str != expected_password_str
        ):
            logger.warning(
                "Metrics access denied: invalid Basic Auth credentials",
                client_ip=client_ip,
                username=credentials.username,
                expected_username=expected_username,
                username_match=credentials.username == expected_username,
            )
            raise UnauthorizedError(
                message="Invalid metrics credentials",
                details={"method": "basic"},
            )

        logger.debug(
            "Metrics access granted via Basic Auth",
            client_ip=client_ip,
            username=credentials.username,
        )
        return True

    # Bearer Token Authentication
    elif auth_method == "bearer":
        if not bearer_token:
            # Try manual parsing from Authorization header
            if authorization and authorization.startswith("Bearer "):
                token = authorization.replace("Bearer ", "").strip()
            else:
                logger.warning(
                    "Metrics access denied: missing Bearer token",
                    client_ip=client_ip,
                )
                raise UnauthorizedError(
                    message="Metrics endpoint requires Bearer Token authentication",
                    details={"method": "bearer"},
                )
        else:
            # HTTPBearer returns HTTPAuthorizationCredentials with .credentials attribute
            token = bearer_token.credentials

        try:
            expected_token = settings.metrics.AUTH_BEARER_TOKEN
        except AttributeError:
            expected_token = ""

        if not expected_token:
            logger.error(
                "Metrics Bearer token not configured",
                client_ip=client_ip,
            )
            raise UnauthorizedError(
                message="Metrics authentication misconfigured",
                details={"method": "bearer"},
            )

        if token != expected_token:
            logger.warning(
                "Metrics access denied: invalid Bearer token",
                client_ip=client_ip,
            )
            raise UnauthorizedError(
                message="Invalid metrics token",
                details={"method": "bearer"},
            )

        logger.debug(
            "Metrics access granted via Bearer token",
            client_ip=client_ip,
        )
        return True

    else:
        logger.error(
            "Invalid metrics authentication method",
            method=auth_method,
            client_ip=client_ip,
        )
        raise UnauthorizedError(
            message="Metrics authentication misconfigured",
            details={"method": auth_method},
        )
