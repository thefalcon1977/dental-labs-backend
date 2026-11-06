"""Role-based access control (RBAC) dependencies shared by all auth modes."""

from typing import Annotated, Any

from fastapi import Depends

from apps.core.exceptions import ForbiddenError, ValidationError
from config.logging import get_logger

from .dependencies import get_current_user
from .keycloak.helpers.exceptions import InsufficientPermissionsError
from .keycloak.schemas.user import UserInfo
from .keycloak.types import StringSet

logger = get_logger(__name__)


def require_all_roles(*required_roles: str) -> Any:
    """Require user to have all specified roles.

    Args:
        *required_roles: Required role names (all must be present)

    Returns:
        Dependency function that checks roles

    Example:
        @router.get("/super-admin")
        async def super_admin_endpoint(
            user: UserInfo = Depends(get_current_user),
            _: None = Depends(require_all_roles("admin", "super_admin")),
        ):
            return {"message": "Super admin access"}
    """
    if not required_roles:
        raise ValidationError(
            "At least one role must be specified",
            details={"context": "require_all_roles"},
        )

    async def check_all_roles(
        user: Annotated[UserInfo, Depends(get_current_user)],
    ) -> None:
        """Check if user has all required roles.

        Args:
            user: Authenticated user (injected).
        """
        # Get all user roles
        all_roles: StringSet = set()

        # Add realm roles
        all_roles.update(user.roles.realm_roles)

        # Add client roles
        for client_roles in user.roles.client_roles.values():
            all_roles.update(client_roles)

        # Check if user has all required roles
        missing_roles = set(required_roles) - all_roles

        if missing_roles:
            logger.warning(
                "Access denied: missing required roles",
                user_id=user.id,
                username=user.username,
                user_roles=list(all_roles),
                required_roles=list(required_roles),
                missing_roles=list(missing_roles),
            )
            raise ForbiddenError(f"Missing required roles: {', '.join(missing_roles)}")

        logger.debug(
            "All roles check passed",
            user_id=user.id,
            required_roles=list(required_roles),
        )

    return check_all_roles


def require_roles(*required_roles: str) -> Any:
    """Require user to have at least one of the specified roles.

    Args:
        *required_roles: Required role names

    Returns:
        Dependency function that checks roles

    Example:
        @router.get("/admin")
        async def admin_endpoint(
            user: UserInfo = Depends(get_current_user),
            _: None = Depends(require_roles("admin", "super_admin")),
        ):
            return {"message": "Admin access"}
    """
    if not required_roles:
        raise ValidationError(
            "At least one role must be specified",
            details={"context": "require_roles"},
        )

    async def check_roles(
        user: Annotated[UserInfo, Depends(get_current_user)],
    ) -> None:
        """Check if user has required roles.

        Args:
            user: Authenticated user (injected).
        """
        # Get all user roles
        all_roles: StringSet = set()

        # Add realm roles
        all_roles.update(user.roles.realm_roles)

        # Add client roles
        for client_roles in user.roles.client_roles.values():
            all_roles.update(client_roles)

        # Check if user has any of the required roles
        has_role = any(role in all_roles for role in required_roles)

        if not has_role:
            logger.warning(
                "Access denied: insufficient roles",
                user_id=user.id,
                username=user.username,
                user_roles=list(all_roles),
                required_roles=list(required_roles),
            )
            raise ForbiddenError(f"Required roles: {', '.join(required_roles)}")

        logger.debug(
            "Role check passed",
            user_id=user.id,
            required_roles=list(required_roles),
        )

    return check_roles


def require_any_role(*required_roles: str) -> Any:
    """Require user to have at least one of the specified roles.

    Alias for require_roles for consistency.

    Args:
        *required_roles: Required role names

    Returns:
        Dependency function that checks roles
    """
    return require_roles(*required_roles)


def require_permissions(*required_permissions: str) -> Any:
    """Require user to have at least one of the specified permissions.

    Args:
        *required_permissions: Required permission names

    Returns:
        Dependency function that checks permissions

    Example:
        @router.post("/users")
        async def create_user(
            user: UserInfo = Depends(get_current_user),
            _: None = Depends(require_permissions("users:write", "users:create")),
        ):
            return {"message": "User created"}
    """
    if not required_permissions:
        raise ValidationError(
            "At least one permission must be specified",
            details={"context": "require_permissions"},
        )

    async def check_permissions(
        user: Annotated[UserInfo, Depends(get_current_user)],
    ) -> None:
        """Check if user has required permissions.

        Args:
            user: Authenticated user (injected).
        """
        # Get all user permissions
        all_permissions: StringSet = set(user.permissions.permissions)

        # Check if user has any of the required permissions
        has_permission = any(perm in all_permissions for perm in required_permissions)

        if not has_permission:
            logger.warning(
                "Access denied: insufficient permissions",
                user_id=user.id,
                username=user.username,
                user_permissions=list(all_permissions),
                required_permissions=list(required_permissions),
            )
            raise InsufficientPermissionsError(
                f"Required permissions: {', '.join(required_permissions)}",
                details={
                    "user_permissions": list(all_permissions),
                    "required_permissions": list(required_permissions),
                },
            )

        logger.debug(
            "Permission check passed",
            user_id=user.id,
            required_permissions=list(required_permissions),
        )

    return check_permissions


def require_all_permissions(*required_permissions: str) -> Any:
    """Require user to have all specified permissions.

    Args:
        *required_permissions: Required permission names (all must be present)

    Returns:
        Dependency function that checks permissions
    """
    if not required_permissions:
        raise ValidationError(
            "At least one permission must be specified",
            details={"context": "require_all_permissions"},
        )

    async def check_all_permissions(
        user: Annotated[UserInfo, Depends(get_current_user)],
    ) -> None:
        """Check if user has all required permissions.

        Args:
            user: Authenticated user (injected).
        """
        # Get all user permissions
        all_permissions: StringSet = set(user.permissions.permissions)

        # Check if user has all required permissions
        missing_permissions = set(required_permissions) - all_permissions

        if missing_permissions:
            logger.warning(
                "Access denied: missing required permissions",
                user_id=user.id,
                username=user.username,
                user_permissions=list(all_permissions),
                required_permissions=list(required_permissions),
                missing_permissions=list(missing_permissions),
            )
            raise InsufficientPermissionsError(
                f"Missing required permissions: {', '.join(missing_permissions)}",
                details={
                    "user_permissions": list(all_permissions),
                    "required_permissions": list(required_permissions),
                    "missing_permissions": list(missing_permissions),
                },
            )

        logger.debug(
            "All permissions check passed",
            user_id=user.id,
            required_permissions=list(required_permissions),
        )

    return check_all_permissions


def require_groups(*required_groups: str) -> Any:
    """Require user to be in at least one of the specified groups.

    Args:
        *required_groups: Required group names

    Returns:
        Dependency function that checks groups

    Example:
        @router.get("/gitlab-users")
        async def gitlab_endpoint(
            user: UserInfo = Depends(get_current_user),
            _: None = Depends(require_groups("gitlab-users", "developers")),
        ):
            return {"message": "GitLab user access"}
    """
    if not required_groups:
        raise ValidationError(
            "At least one group must be specified",
            details={"context": "require_groups"},
        )

    async def check_groups(
        user: Annotated[UserInfo, Depends(get_current_user)],
    ) -> None:
        """Check if user is in required groups.

        Args:
            user: Authenticated user (injected).
        """
        # Get all user groups
        user_groups: StringSet = set(user.groups)

        # Check if user is in any of the required groups
        has_group = any(group in user_groups for group in required_groups)

        if not has_group:
            logger.warning(
                "Access denied: insufficient groups",
                user_id=user.id,
                username=user.username,
                user_groups=list(user_groups),
                required_groups=list(required_groups),
            )
            raise ForbiddenError(f"Required groups: {', '.join(required_groups)}")

        logger.debug(
            "Group check passed",
            user_id=user.id,
            required_groups=list(required_groups),
        )

    return check_groups


def require_all_groups(*required_groups: str) -> Any:
    """Require user to be in all specified groups.

    Args:
        *required_groups: Required group names (all must be present)

    Returns:
        Dependency function that checks groups

    Example:
        @router.get("/admin-developers")
        async def admin_dev_endpoint(
            user: UserInfo = Depends(get_current_user),
            _: None = Depends(require_all_groups("admin", "developers")),
        ):
            return {"message": "Admin developer access"}
    """
    if not required_groups:
        raise ValidationError(
            "At least one group must be specified",
            details={"context": "require_all_groups"},
        )

    async def check_all_groups(
        user: Annotated[UserInfo, Depends(get_current_user)],
    ) -> None:
        """Check if user is in all required groups.

        Args:
            user: Authenticated user (injected).
        """
        # Get all user groups
        user_groups: StringSet = set(user.groups)

        # Check if user is in all required groups
        missing_groups = set(required_groups) - user_groups

        if missing_groups:
            logger.warning(
                "Access denied: missing required groups",
                user_id=user.id,
                username=user.username,
                user_groups=list(user_groups),
                required_groups=list(required_groups),
                missing_groups=list(missing_groups),
            )
            raise ForbiddenError(
                f"Missing required groups: {', '.join(missing_groups)}"
            )

        logger.debug(
            "All groups check passed",
            user_id=user.id,
            required_groups=list(required_groups),
        )

    return check_all_groups
