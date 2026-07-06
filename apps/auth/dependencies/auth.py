"""Authentication dependencies for local user auth."""

from collections.abc import Mapping
from datetime import datetime
from typing import TypeAlias

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError as PydanticValidationError

from apps.auth.schemas.user import UserInfo
from apps.core.exceptions import BaseAPIException, UnauthorizedError

StringList: TypeAlias = list[str]

bearer_scheme = HTTPBearer(auto_error=False)


def _name_list(items: object) -> StringList:
    """Extract name values from relationship-like collections.

    Args:
        items: Collection of strings or objects with a name attribute.

    Returns:
        List of names extracted from the collection.
    """
    if not isinstance(items, list):
        return []

    names: StringList = []
    for item in items:
        if isinstance(item, str):
            names.append(item)
            continue

        name = getattr(item, "name", None)
        if isinstance(name, str):
            names.append(name)

    return names


def _state_user_to_schema(raw_user: object) -> UserInfo:
    """Convert request state user data into a dependency schema.

    Args:
        raw_user: User object, user dictionary, or UserInfo schema.

    Returns:
        Authenticated user information.

    Raises:
        UnauthorizedError: If user data cannot be converted.
    """
    if isinstance(raw_user, UserInfo):
        return raw_user

    try:
        if isinstance(raw_user, Mapping):
            return UserInfo.model_validate(raw_user)

        created_at = getattr(raw_user, "created_at", None)
        if not isinstance(created_at, datetime):
            raise UnauthorizedError("Invalid authentication context")

        return UserInfo(
            id=str(getattr(raw_user, "id")),
            email=str(getattr(raw_user, "email")),
            username=str(getattr(raw_user, "username")),
            first_name=getattr(raw_user, "first_name", None),
            last_name=getattr(raw_user, "last_name", None),
            is_active=bool(getattr(raw_user, "is_active")),
            is_verified=bool(getattr(raw_user, "is_verified")),
            is_superuser=bool(getattr(raw_user, "is_superuser")),
            created_at=created_at,
            updated_at=getattr(raw_user, "updated_at", None),
            groups=_name_list(getattr(raw_user, "groups", [])),
            roles=_name_list(getattr(raw_user, "roles", [])),
            permissions=_name_list(getattr(raw_user, "permissions", [])),
        )
    except (PydanticValidationError, AttributeError, TypeError, ValueError) as exc:
        raise UnauthorizedError("Invalid authentication context") from exc


def _get_state_user(request: Request) -> object | None:
    """Get user data from request state.

    Args:
        request: FastAPI request object.

    Returns:
        User data from request state, if available.
    """
    current_user = getattr(request.state, "current_user", None)
    if current_user is not None:
        return current_user
    return getattr(request.state, "user", None)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> UserInfo:
    """Get the current authenticated user.

    This dependency expects an earlier auth layer to validate the bearer token
    and place user data on `request.state.current_user` or `request.state.user`.

    Args:
        request: FastAPI request object.
        credentials: Optional bearer credentials from the Authorization header.

    Returns:
        Authenticated user information.

    Raises:
        UnauthorizedError: If authentication is missing or invalid.
    """
    if credentials is None:
        raise UnauthorizedError("Authentication required")

    raw_user = _get_state_user(request)
    if raw_user is None:
        raise UnauthorizedError("Authentication context unavailable")

    user = _state_user_to_schema(raw_user)
    if not user.is_active:
        raise UnauthorizedError("User account is inactive")

    return user


async def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> UserInfo | None:
    """Get the current user when authentication is available.

    Args:
        request: FastAPI request object.
        credentials: Optional bearer credentials from the Authorization header.

    Returns:
        Authenticated user information, or None.
    """
    try:
        return await get_current_user(request, credentials)
    except BaseAPIException:
        return None


async def verify_token(
    current_user: UserInfo = Depends(get_current_user),
) -> bool:
    """Verify that a request has a valid authenticated user.

    Args:
        current_user: Authenticated user provided by get_current_user.

    Returns:
        True when authentication succeeds.
    """
    return current_user.is_active


__all__ = [
    "get_current_user",
    "get_optional_user",
    "verify_token",
]
