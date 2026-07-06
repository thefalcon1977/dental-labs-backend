"""Authentication-specific exceptions for local auth."""

from fastapi import status

from apps.core.exceptions import BaseAPIException
from apps.core.types import ExceptionDetailsDict

INVALID_TOKEN_MESSAGE = "Invalid or expired token."
AUTHENTICATION_FAILED_MESSAGE = "Authentication failed."


class AuthError(BaseAPIException):
    """Base exception for authentication-related errors."""


class InvalidCredentialsError(AuthError):
    """Invalid username/email or password exception."""

    def __init__(self, message: str = AUTHENTICATION_FAILED_MESSAGE) -> None:
        """Initialize invalid credentials error.

        Args:
            message: Public error message.
        """
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class TokenExpiredError(AuthError):
    """Token has expired exception."""

    def __init__(
        self,
        message: str = "Your session has expired. Please sign in again.",
    ) -> None:
        """Initialize token expired error.

        Args:
            message: Public error message.
        """
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class InvalidTokenError(AuthError):
    """Token is invalid or malformed exception."""

    def __init__(self, message: str = INVALID_TOKEN_MESSAGE) -> None:
        """Initialize invalid token error.

        Args:
            message: Public error message.
        """
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class TokenRevokedError(AuthError):
    """Token has been revoked exception."""

    def __init__(
        self,
        message: str = "Your session has been ended. Please sign in again.",
    ) -> None:
        """Initialize token revoked error.

        Args:
            message: Public error message.
        """
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class InactiveUserError(AuthError):
    """User account is inactive exception."""

    def __init__(self, message: str = "User account is inactive") -> None:
        """Initialize inactive user error.

        Args:
            message: Public error message.
        """
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class InsufficientPermissionsError(AuthError):
    """User lacks required permissions exception."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        details: ExceptionDetailsDict | None = None,
    ) -> None:
        """Initialize insufficient permissions error.

        Args:
            message: Public error message.
            details: Structured authorization context.
        """
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details or {},
        )


__all__ = [
    "AUTHENTICATION_FAILED_MESSAGE",
    "INVALID_TOKEN_MESSAGE",
    "AuthError",
    "InactiveUserError",
    "InsufficientPermissionsError",
    "InvalidCredentialsError",
    "InvalidTokenError",
    "TokenExpiredError",
    "TokenRevokedError",
]
