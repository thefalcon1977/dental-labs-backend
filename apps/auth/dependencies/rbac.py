"""RBAC dependencies for local auth users."""

from collections.abc import Awaitable, Callable
from typing import TypeAlias

from fastapi import Depends

from apps.auth.dependencies.auth import get_current_user
from apps.auth.schemas.user import UserInfo
from apps.core.exceptions import ForbiddenError

AuthDependency: TypeAlias = Callable[..., Awaitable[None]]
StringSet: TypeAlias = set[str]


def _normalize_required(values: tuple[str, ...]) -> StringSet:
    """Normalize required RBAC values.

    Args:
        values: Required role, group, or permission names.

    Returns:
        Set of normalized non-empty values.
    """
    return {value.strip() for value in values if value.strip()}


def _has_any(user_values: StringSet, required_values: StringSet) -> bool:
    """Check whether any required value is present.

    Args:
        user_values: Values assigned to the user.
        required_values: Values required by the dependency.

    Returns:
        True if at least one required value is present.
    """
    if not required_values:
        return True
    return bool(user_values.intersection(required_values))


def _has_all(user_values: StringSet, required_values: StringSet) -> bool:
    """Check whether all required values are present.

    Args:
        user_values: Values assigned to the user.
        required_values: Values required by the dependency.

    Returns:
        True if all required values are present.
    """
    return required_values.issubset(user_values)


def require_roles(*roles: str) -> AuthDependency:
    """Require the current user to have at least one role.

    Args:
        roles: Accepted role names.

    Returns:
        FastAPI dependency function.
    """
    required_roles = _normalize_required(roles)

    async def dependency(
        user: UserInfo = Depends(get_current_user),
    ) -> None:
        """Validate role access for the current user."""
        if user.is_superuser:
            return

        if not _has_any(set(user.roles), required_roles):
            raise ForbiddenError("Insufficient role permissions")

    return dependency


def require_all_roles(*roles: str) -> AuthDependency:
    """Require the current user to have all roles.

    Args:
        roles: Required role names.

    Returns:
        FastAPI dependency function.
    """
    required_roles = _normalize_required(roles)

    async def dependency(
        user: UserInfo = Depends(get_current_user),
    ) -> None:
        """Validate all required roles for the current user."""
        if user.is_superuser:
            return

        if not _has_all(set(user.roles), required_roles):
            raise ForbiddenError("Insufficient role permissions")

    return dependency


def require_groups(*groups: str) -> AuthDependency:
    """Require the current user to belong to at least one group.

    Args:
        groups: Accepted group names.

    Returns:
        FastAPI dependency function.
    """
    required_groups = _normalize_required(groups)

    async def dependency(
        user: UserInfo = Depends(get_current_user),
    ) -> None:
        """Validate group access for the current user."""
        if user.is_superuser:
            return

        if not _has_any(set(user.groups), required_groups):
            raise ForbiddenError("Insufficient group permissions")

    return dependency


def require_all_groups(*groups: str) -> AuthDependency:
    """Require the current user to belong to all groups.

    Args:
        groups: Required group names.

    Returns:
        FastAPI dependency function.
    """
    required_groups = _normalize_required(groups)

    async def dependency(
        user: UserInfo = Depends(get_current_user),
    ) -> None:
        """Validate all required groups for the current user."""
        if user.is_superuser:
            return

        if not _has_all(set(user.groups), required_groups):
            raise ForbiddenError("Insufficient group permissions")

    return dependency


def require_permissions(*permissions: str) -> AuthDependency:
    """Require the current user to have at least one permission.

    Args:
        permissions: Accepted permission names.

    Returns:
        FastAPI dependency function.
    """
    required_permissions = _normalize_required(permissions)

    async def dependency(
        user: UserInfo = Depends(get_current_user),
    ) -> None:
        """Validate permission access for the current user."""
        if user.is_superuser:
            return

        if not _has_any(set(user.permissions), required_permissions):
            raise ForbiddenError("Insufficient permissions")

    return dependency


def require_all_permissions(*permissions: str) -> AuthDependency:
    """Require the current user to have all permissions.

    Args:
        permissions: Required permission names.

    Returns:
        FastAPI dependency function.
    """
    required_permissions = _normalize_required(permissions)

    async def dependency(
        user: UserInfo = Depends(get_current_user),
    ) -> None:
        """Validate all required permissions for the current user."""
        if user.is_superuser:
            return

        if not _has_all(set(user.permissions), required_permissions):
            raise ForbiddenError("Insufficient permissions")

    return dependency


__all__ = [
    "require_all_groups",
    "require_all_permissions",
    "require_all_roles",
    "require_groups",
    "require_permissions",
    "require_roles",
]
