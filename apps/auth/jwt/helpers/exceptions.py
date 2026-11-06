"""Exceptions for the local JWT authentication provider.

All exceptions inherit from ``AuthError`` (and thus ``BaseAPIException``) so
they are rendered by the centralized exception handlers.
"""

from fastapi import status

from apps.auth.keycloak.helpers.exceptions import AuthError

INVALID_CREDENTIALS_MESSAGE = "Invalid username or password."


class InvalidCredentialsError(AuthError):
    """Username/email or password is wrong (401)."""

    def __init__(self, message: str = INVALID_CREDENTIALS_MESSAGE) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class InactiveUserError(AuthError):
    """Account exists but is deactivated (403)."""

    def __init__(self, message: str = "User account is inactive.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class RegistrationDisabledError(AuthError):
    """Self-registration is turned off by configuration (403)."""

    def __init__(self, message: str = "User registration is disabled.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class UserAlreadyExistsError(AuthError):
    """Username or email is already taken (409)."""

    def __init__(self, field: str) -> None:
        super().__init__(
            message=f"A user with this {field} already exists.",
            status_code=status.HTTP_409_CONFLICT,
            details={"field": field},
        )


class ResourceAlreadyExistsError(AuthError):
    """A group, role, or permission with this name/code already exists (409)."""

    def __init__(self, resource: str, field: str, value: str) -> None:
        super().__init__(
            message=f"{resource} with this {field} already exists.",
            status_code=status.HTTP_409_CONFLICT,
            details={"resource": resource, "field": field, "value": value},
        )


class ProtectedResourceError(AuthError):
    """The resource is required for administration and cannot be removed (409)."""

    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(
            message=f"{resource} '{identifier}' is protected and cannot be removed.",
            status_code=status.HTTP_409_CONFLICT,
            details={"resource": resource, "identifier": identifier},
        )


__all__ = [
    "INVALID_CREDENTIALS_MESSAGE",
    "InactiveUserError",
    "InvalidCredentialsError",
    "ProtectedResourceError",
    "RegistrationDisabledError",
    "ResourceAlreadyExistsError",
    "UserAlreadyExistsError",
]
