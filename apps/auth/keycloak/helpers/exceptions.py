"""Authentication-specific exceptions.

All auth-specific exceptions inherit from AuthError (and thus BaseAPIException)
so they are handled by the centralized exception handlers. Never raise raw
Exception or ValueError for domain errors—use these typed exceptions.
"""

from fastapi import status

from apps.core.exceptions import BaseAPIException

from ..types import DetailsDict

# User-facing messages (no technical details or raw errors)
KEYCLOAK_UNAVAILABLE_MESSAGE = (
    "Authentication service is temporarily unavailable. Please try again later."
)
INVALID_TOKEN_MESSAGE = "Invalid or expired token."
AUTHENTICATION_FAILED_MESSAGE = "Authentication failed."


class AuthError(BaseAPIException):
    """Base exception for authentication-related errors."""


class TokenExpiredError(AuthError):
    """Token has expired exception."""

    def __init__(
        self, message: str = "Your session has expired. Please sign in again."
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class InvalidTokenError(AuthError):
    """Token is invalid or malformed exception."""

    def __init__(self, message: str = INVALID_TOKEN_MESSAGE) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class TokenRevokedError(AuthError):
    """Token has been revoked exception."""

    def __init__(
        self, message: str = "Your session has been ended. Please sign in again."
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class InsufficientPermissionsError(AuthError):
    """User lacks required permissions exception."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        details: DetailsDict | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details or {},
        )


class AuthDisabledError(AuthError):
    """Authentication is disabled by configuration."""

    def __init__(self, message: str = "Authentication is disabled.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class KeycloakConnectionError(AuthError):
    """Cannot connect to Keycloak exception."""

    def __init__(self, message: str = KEYCLOAK_UNAVAILABLE_MESSAGE) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


# OTP (design: docs/srs/otp-login-design-and-security.md)

OTP_SESSION_INVALID_MESSAGE = "Invalid or expired session or code."
OTP_SESSION_LOCKED_MESSAGE = "Session locked. Please log in again."
OTP_WINDOW_NOT_EXPIRED_MESSAGE = (
    "A code was already sent. Please wait for it to expire before requesting another."
)
REDIS_UNAVAILABLE_MESSAGE = (
    "Authentication service is temporarily unavailable. Please try again later."
)


class OtpSessionInvalidError(AuthError):
    """OTP session invalid or expired, or OTP code wrong (401)."""

    def __init__(self, message: str = OTP_SESSION_INVALID_MESSAGE) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class OtpSessionLockedError(AuthError):
    """OTP session locked after too many failed attempts (403)."""

    def __init__(self, message: str = OTP_SESSION_LOCKED_MESSAGE) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class OtpWindowNotExpiredError(AuthError):
    """Another OTP was recently sent; request a new one only after it expires (429)."""

    def __init__(
        self,
        message: str = OTP_WINDOW_NOT_EXPIRED_MESSAGE,
        retry_after_seconds: int = 0,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"retry_after_seconds": max(0, retry_after_seconds)},
        )


class RedisUnavailableError(AuthError):
    """Redis (session store) unavailable (503)."""

    def __init__(self, message: str = REDIS_UNAVAILABLE_MESSAGE) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
