"""Service layer for administering groups, roles, and permissions (JWT mode).

Changes affect a user's access from their next issued access token
(login or refresh), i.e. within ``auth.JWT_ACCESS_TOKEN_EXPIRE_MINUTES``.
"""

from typing import TypeAlias

from sqlalchemy.ext.asyncio import AsyncSession

from apps.core.exceptions import NotFoundError
from apps.core.utils import PaginatedResponse, PaginationParams
from config.logging import get_logger
from config.settings import settings

from .. import schemas
from ..helpers.exceptions import ProtectedResourceError
from ..models import Group, Permission, Role
from ..repository import bll, dal

logger = get_logger(__name__)

PermissionPage: TypeAlias = PaginatedResponse[schemas.PermissionResponse]
RolePage: TypeAlias = PaginatedResponse[schemas.RoleResponse]
GroupPage: TypeAlias = PaginatedResponse[schemas.GroupResponse]
UserPage: TypeAlias = PaginatedResponse[schemas.UserSummaryResponse]


def admin_permission() -> str:
    """Return the permission code required by the admin API.

    Returns:
        Value of ``auth.JWT_ADMIN_PERMISSION``.
    """
    return str(settings.auth.JWT_ADMIN_PERMISSION)


def admin_role() -> str:
    """Return the name of the built-in admin role.

    Returns:
        Value of ``auth.JWT_ADMIN_ROLE``.
    """
    return str(settings.auth.JWT_ADMIN_ROLE)


# Lookups that raise 404


async def _require_permission(db: AsyncSession, permission_id: str) -> Permission:
    """Load a permission or raise 404.

    Args:
        db: Database session.
        permission_id: Permission identifier.

    Returns:
        The permission.

    Raises:
        NotFoundError: If it does not exist.
    """
    permission = await dal.get_permission(db, permission_id)
    if permission is None:
        raise NotFoundError(resource="Permission", identifier=permission_id)
    return permission


async def _require_role(
    db: AsyncSession, role_id: str, with_permissions: bool = False
) -> Role:
    """Load a role or raise 404.

    Args:
        db: Database session.
        role_id: Role identifier.
        with_permissions: Eager-load permissions.

    Returns:
        The role.

    Raises:
        NotFoundError: If it does not exist.
    """
    role = await dal.get_role(db, role_id, with_permissions=with_permissions)
    if role is None:
        raise NotFoundError(resource="Role", identifier=role_id)
    return role


async def _require_group(
    db: AsyncSession, group_id: str, with_roles: bool = False
) -> Group:
    """Load a group or raise 404.

    Args:
        db: Database session.
        group_id: Group identifier.
        with_roles: Eager-load roles.

    Returns:
        The group.

    Raises:
        NotFoundError: If it does not exist.
    """
    group = await dal.get_group(db, group_id, with_roles=with_roles)
    if group is None:
        raise NotFoundError(resource="Group", identifier=group_id)
    return group


async def _require_user(db: AsyncSession, user_id: str) -> None:
    """Raise 404 unless the user exists.

    Args:
        db: Database session.
        user_id: User identifier.

    Raises:
        NotFoundError: If it does not exist.
    """
    if not await dal.user_exists(db, user_id):
        raise NotFoundError(resource="User", identifier=user_id)


# Permissions


async def list_permissions(
    db: AsyncSession, pagination: PaginationParams, search: str | None
) -> PermissionPage:
    """List permissions.

    Args:
        db: Database session.
        pagination: Page parameters.
        search: Optional code prefix.

    Returns:
        A page of permissions.
    """
    items, total = await dal.list_permissions(db, pagination, search)
    return PaginatedResponse.create(
        items=[schemas.PermissionResponse.model_validate(p) for p in items],
        page=pagination.page,
        page_size=pagination.page_size,
        total_items=total,
    )


async def create_permission(
    db: AsyncSession, data: schemas.PermissionCreate
) -> schemas.PermissionResponse:
    """Create a permission.

    Args:
        db: Database session.
        data: Permission data.

    Returns:
        The created permission.
    """
    permission = await bll.create_permission(db, data)
    logger.info("Permission created", permission_id=permission.id, code=permission.code)
    return schemas.PermissionResponse.model_validate(permission)


async def update_permission(
    db: AsyncSession, permission_id: str, data: schemas.PermissionUpdate
) -> schemas.PermissionResponse:
    """Update a permission.

    Args:
        db: Database session.
        permission_id: Permission identifier.
        data: Fields to change.

    Returns:
        The updated permission.
    """
    permission = await _require_permission(db, permission_id)
    permission = await bll.update_permission(db, permission, data)
    return schemas.PermissionResponse.model_validate(permission)


async def delete_permission(db: AsyncSession, permission_id: str) -> None:
    """Delete a permission.

    Args:
        db: Database session.
        permission_id: Permission identifier.

    Raises:
        ProtectedResourceError: If it is the admin permission.
    """
    permission = await _require_permission(db, permission_id)
    if permission.code == admin_permission():
        raise ProtectedResourceError("Permission", permission.code)
    await bll.delete_permission(db, permission)
    logger.info("Permission deleted", permission_id=permission_id)


# Roles


async def list_roles(
    db: AsyncSession, pagination: PaginationParams, search: str | None
) -> RolePage:
    """List roles.

    Args:
        db: Database session.
        pagination: Page parameters.
        search: Optional name prefix.

    Returns:
        A page of roles.
    """
    items, total = await dal.list_roles(db, pagination, search)
    return PaginatedResponse.create(
        items=[schemas.RoleResponse.model_validate(r) for r in items],
        page=pagination.page,
        page_size=pagination.page_size,
        total_items=total,
    )


async def get_role(db: AsyncSession, role_id: str) -> schemas.RoleDetailResponse:
    """Get a role with its permissions.

    Args:
        db: Database session.
        role_id: Role identifier.

    Returns:
        The role and its permissions.
    """
    role = await _require_role(db, role_id, with_permissions=True)
    return schemas.RoleDetailResponse.model_validate(role)


async def create_role(
    db: AsyncSession, data: schemas.RoleCreate
) -> schemas.RoleResponse:
    """Create a role.

    Args:
        db: Database session.
        data: Role data.

    Returns:
        The created role.
    """
    role = await bll.create_role(db, data)
    logger.info("Role created", role_id=role.id, role_name=role.name)
    return schemas.RoleResponse.model_validate(role)


async def update_role(
    db: AsyncSession, role_id: str, data: schemas.RoleUpdate
) -> schemas.RoleResponse:
    """Update a role.

    Args:
        db: Database session.
        role_id: Role identifier.
        data: Fields to change.

    Returns:
        The updated role.

    Raises:
        ProtectedResourceError: If renaming the admin role.
    """
    role = await _require_role(db, role_id)
    if role.name == admin_role() and data.name not in (None, role.name):
        raise ProtectedResourceError("Role", role.name)
    role = await bll.update_role(db, role, data)
    return schemas.RoleResponse.model_validate(role)


async def delete_role(db: AsyncSession, role_id: str) -> None:
    """Delete a role.

    Args:
        db: Database session.
        role_id: Role identifier.

    Raises:
        ProtectedResourceError: If it is the admin role.
    """
    role = await _require_role(db, role_id)
    if role.name == admin_role():
        raise ProtectedResourceError("Role", role.name)
    await bll.delete_role(db, role)
    logger.info("Role deleted", role_id=role_id)


async def add_permission_to_role(
    db: AsyncSession, role_id: str, permission_id: str
) -> schemas.RoleDetailResponse:
    """Grant a permission to a role.

    Args:
        db: Database session.
        role_id: Role identifier.
        permission_id: Permission identifier.

    Returns:
        The role with its permissions.
    """
    await _require_role(db, role_id)
    await _require_permission(db, permission_id)
    await bll.add_permission_to_role(db, role_id, permission_id)
    logger.info(
        "Permission granted to role", role_id=role_id, permission_id=permission_id
    )
    return await get_role(db, role_id)


async def remove_permission_from_role(
    db: AsyncSession, role_id: str, permission_id: str
) -> schemas.RoleDetailResponse:
    """Revoke a permission from a role.

    Args:
        db: Database session.
        role_id: Role identifier.
        permission_id: Permission identifier.

    Returns:
        The role with its permissions.

    Raises:
        ProtectedResourceError: If removing the admin permission from the admin role.
    """
    role = await _require_role(db, role_id)
    permission = await _require_permission(db, permission_id)
    if role.name == admin_role() and permission.code == admin_permission():
        raise ProtectedResourceError("Permission", permission.code)
    await bll.remove_permission_from_role(db, role_id, permission_id)
    logger.info(
        "Permission revoked from role", role_id=role_id, permission_id=permission_id
    )
    return await get_role(db, role_id)


# Groups


async def list_groups(
    db: AsyncSession, pagination: PaginationParams, search: str | None
) -> GroupPage:
    """List groups.

    Args:
        db: Database session.
        pagination: Page parameters.
        search: Optional name prefix.

    Returns:
        A page of groups.
    """
    items, total = await dal.list_groups(db, pagination, search)
    return PaginatedResponse.create(
        items=[schemas.GroupResponse.model_validate(g) for g in items],
        page=pagination.page,
        page_size=pagination.page_size,
        total_items=total,
    )


async def get_group(db: AsyncSession, group_id: str) -> schemas.GroupDetailResponse:
    """Get a group with its roles.

    Args:
        db: Database session.
        group_id: Group identifier.

    Returns:
        The group and its roles.
    """
    group = await _require_group(db, group_id, with_roles=True)
    return schemas.GroupDetailResponse.model_validate(group)


async def create_group(
    db: AsyncSession, data: schemas.GroupCreate
) -> schemas.GroupResponse:
    """Create a group.

    Args:
        db: Database session.
        data: Group data.

    Returns:
        The created group.
    """
    group = await bll.create_group(db, data)
    logger.info("Group created", group_id=group.id, group_name=group.name)
    return schemas.GroupResponse.model_validate(group)


async def update_group(
    db: AsyncSession, group_id: str, data: schemas.GroupUpdate
) -> schemas.GroupResponse:
    """Update a group.

    Args:
        db: Database session.
        group_id: Group identifier.
        data: Fields to change.

    Returns:
        The updated group.
    """
    group = await _require_group(db, group_id)
    group = await bll.update_group(db, group, data)
    return schemas.GroupResponse.model_validate(group)


async def delete_group(db: AsyncSession, group_id: str) -> None:
    """Delete a group.

    Args:
        db: Database session.
        group_id: Group identifier.
    """
    group = await _require_group(db, group_id)
    await bll.delete_group(db, group)
    logger.info("Group deleted", group_id=group_id)


async def add_role_to_group(
    db: AsyncSession, group_id: str, role_id: str
) -> schemas.GroupDetailResponse:
    """Grant a role to a group.

    Args:
        db: Database session.
        group_id: Group identifier.
        role_id: Role identifier.

    Returns:
        The group with its roles.
    """
    await _require_group(db, group_id)
    await _require_role(db, role_id)
    await bll.add_role_to_group(db, group_id, role_id)
    logger.info("Role granted to group", group_id=group_id, role_id=role_id)
    return await get_group(db, group_id)


async def remove_role_from_group(
    db: AsyncSession, group_id: str, role_id: str
) -> schemas.GroupDetailResponse:
    """Revoke a role from a group.

    Args:
        db: Database session.
        group_id: Group identifier.
        role_id: Role identifier.

    Returns:
        The group with its roles.
    """
    await _require_group(db, group_id)
    await _require_role(db, role_id)
    await bll.remove_role_from_group(db, group_id, role_id)
    logger.info("Role revoked from group", group_id=group_id, role_id=role_id)
    return await get_group(db, group_id)


async def list_group_members(
    db: AsyncSession, group_id: str, pagination: PaginationParams
) -> UserPage:
    """List a group's members.

    Args:
        db: Database session.
        group_id: Group identifier.
        pagination: Page parameters.

    Returns:
        A page of members.
    """
    await _require_group(db, group_id)
    items, total = await dal.list_group_members(db, group_id, pagination)
    return PaginatedResponse.create(
        items=[schemas.UserSummaryResponse.model_validate(u) for u in items],
        page=pagination.page,
        page_size=pagination.page_size,
        total_items=total,
    )


async def add_user_to_group(db: AsyncSession, group_id: str, user_id: str) -> None:
    """Add a user to a group.

    Args:
        db: Database session.
        group_id: Group identifier.
        user_id: User identifier.
    """
    await _require_group(db, group_id)
    await _require_user(db, user_id)
    await bll.add_user_to_group(db, group_id, user_id)
    logger.info("User added to group", group_id=group_id, user_id=user_id)


async def remove_user_from_group(db: AsyncSession, group_id: str, user_id: str) -> None:
    """Remove a user from a group.

    Args:
        db: Database session.
        group_id: Group identifier.
        user_id: User identifier.
    """
    await _require_group(db, group_id)
    await _require_user(db, user_id)
    await bll.remove_user_from_group(db, group_id, user_id)
    logger.info("User removed from group", group_id=group_id, user_id=user_id)


# Users


async def list_users(
    db: AsyncSession, pagination: PaginationParams, search: str | None
) -> UserPage:
    """List local users.

    Args:
        db: Database session.
        pagination: Page parameters.
        search: Optional username/email prefix.

    Returns:
        A page of users.
    """
    items, total = await dal.list_users(db, pagination, search)
    return PaginatedResponse.create(
        items=[schemas.UserSummaryResponse.model_validate(u) for u in items],
        page=pagination.page,
        page_size=pagination.page_size,
        total_items=total,
    )


async def get_user_access(db: AsyncSession, user_id: str) -> schemas.UserAccessResponse:
    """Get a user's direct roles, groups, and effective access.

    Args:
        db: Database session.
        user_id: User identifier.

    Returns:
        Direct and effective access.
    """
    await _require_user(db, user_id)
    access = await dal.get_user_access(db, user_id)
    return schemas.UserAccessResponse(
        user_id=user_id,
        direct_roles=await dal.get_user_direct_role_names(db, user_id),
        groups=access.groups,
        effective_roles=access.roles,
        permissions=access.permissions,
    )


async def add_role_to_user(
    db: AsyncSession, user_id: str, role_id: str
) -> schemas.UserAccessResponse:
    """Grant a role to a user directly.

    Args:
        db: Database session.
        user_id: User identifier.
        role_id: Role identifier.

    Returns:
        The user's updated access.
    """
    await _require_user(db, user_id)
    await _require_role(db, role_id)
    await bll.add_role_to_user(db, user_id, role_id)
    logger.info("Role granted to user", user_id=user_id, role_id=role_id)
    return await get_user_access(db, user_id)


async def remove_role_from_user(
    db: AsyncSession, user_id: str, role_id: str
) -> schemas.UserAccessResponse:
    """Revoke a directly granted role from a user.

    Args:
        db: Database session.
        user_id: User identifier.
        role_id: Role identifier.

    Returns:
        The user's updated access.
    """
    await _require_user(db, user_id)
    await _require_role(db, role_id)
    await bll.remove_role_from_user(db, user_id, role_id)
    logger.info("Role revoked from user", user_id=user_id, role_id=role_id)
    return await get_user_access(db, user_id)


# Bootstrap


async def create_admin(
    db: AsyncSession, data: schemas.RegisterRequest
) -> schemas.UserAccessResponse:
    """Create (or reuse) a local user and grant them the admin role.

    If a user with the given username already exists, their password is left
    unchanged and only the admin role is granted. Registration settings do not
    apply; this is meant for operators (``python main.py create-admin``).

    Args:
        db: Database session.
        data: Username, email, and password for a new user.

    Returns:
        The admin user's access.

    Raises:
        UserAlreadyExistsError: If only the email is taken by another user.
    """
    user = await dal.get_user_by_login(db, data.username)
    if user is None:
        user = await bll.create_user(db, data)
    role = await bll.ensure_admin_role(db)
    await bll.add_role_to_user(db, user.id, role.id)
    logger.info("Admin role granted", user_id=user.id, role_id=role.id)
    return await get_user_access(db, user.id)
