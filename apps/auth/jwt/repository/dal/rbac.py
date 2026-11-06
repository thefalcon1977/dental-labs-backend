"""DAL for groups, roles, permissions, and effective access (reads)."""

from typing import TypeAlias

from sqlalchemy import Subquery, select, union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.core.utils import PaginationParams, paginate_query

from ...models import (
    Group,
    LocalUser,
    Permission,
    Role,
    group_roles,
    role_permissions,
    user_groups,
    user_roles,
)
from ...types import NameList, UserAccess
from .common import LIKE_ESCAPE, like_prefix
from .user import UserListResult

RoleList: TypeAlias = list[Role]
GroupListResult: TypeAlias = tuple[list[Group], int]
RoleListResult: TypeAlias = tuple[list[Role], int]
PermissionListResult: TypeAlias = tuple[list[Permission], int]


# Effective access


def _effective_role_ids(user_id: str) -> Subquery:
    """Build a subquery of role ids granted directly or through groups.

    Args:
        user_id: User identifier.

    Returns:
        Selectable of distinct ``role_id`` values.
    """
    direct = select(user_roles.c.role_id).where(user_roles.c.user_id == user_id)
    via_groups = (
        select(group_roles.c.role_id)
        .join(user_groups, user_groups.c.group_id == group_roles.c.group_id)
        .where(user_groups.c.user_id == user_id)
    )
    return union(direct, via_groups).subquery()


async def get_user_access(db: AsyncSession, user_id: str) -> UserAccess:
    """Resolve a user's effective roles, groups, and permissions (3 queries).

    Args:
        db: Database session.
        user_id: User identifier.

    Returns:
        Sorted role names, group names, and permission codes.
    """
    role_ids = _effective_role_ids(user_id)
    roles = await db.scalars(
        select(Role.name).where(Role.id.in_(select(role_ids.c.role_id)))
    )
    permissions = await db.scalars(
        select(Permission.code)
        .join(role_permissions, role_permissions.c.permission_id == Permission.id)
        .where(role_permissions.c.role_id.in_(select(role_ids.c.role_id)))
        .distinct()
    )
    groups = await db.scalars(
        select(Group.name)
        .join(user_groups, user_groups.c.group_id == Group.id)
        .where(user_groups.c.user_id == user_id)
    )
    return UserAccess(
        roles=sorted(roles),
        groups=sorted(groups),
        permissions=sorted(permissions),
    )


async def get_user_direct_role_names(db: AsyncSession, user_id: str) -> NameList:
    """Get names of roles granted to the user directly (not via groups).

    Args:
        db: Database session.
        user_id: User identifier.

    Returns:
        Sorted role names.
    """
    names = await db.scalars(
        select(Role.name)
        .join(user_roles, user_roles.c.role_id == Role.id)
        .where(user_roles.c.user_id == user_id)
        .order_by(Role.name)
    )
    return list(names)


# Permissions


async def get_permission(db: AsyncSession, permission_id: str) -> Permission | None:
    """Get a permission by id.

    Args:
        db: Database session.
        permission_id: Permission identifier.

    Returns:
        The permission, or None.
    """
    return await db.get(Permission, permission_id)


async def get_permission_by_code(db: AsyncSession, code: str) -> Permission | None:
    """Get a permission by its unique code.

    Args:
        db: Database session.
        code: Permission code.

    Returns:
        The permission, or None.
    """
    return await db.scalar(select(Permission).where(Permission.code == code))


async def list_permissions(
    db: AsyncSession, pagination: PaginationParams, search: str | None = None
) -> PermissionListResult:
    """List permissions ordered by code, optionally by code prefix.

    Args:
        db: Database session.
        pagination: Page parameters.
        search: Code prefix.

    Returns:
        Tuple of (permissions on this page, total).
    """
    query = select(Permission).order_by(Permission.code)
    if search:
        query = query.where(
            Permission.code.like(like_prefix(search), escape=LIKE_ESCAPE)
        )
    return await paginate_query(db, query, pagination)


# Roles


async def get_role(
    db: AsyncSession, role_id: str, with_permissions: bool = False
) -> Role | None:
    """Get a role by id.

    Args:
        db: Database session.
        role_id: Role identifier.
        with_permissions: Eager-load the role's permissions.

    Returns:
        The role, or None.
    """
    query = select(Role).where(Role.id == role_id)
    if with_permissions:
        # populate_existing: the role may already be in the session with a
        # stale collection after a link/unlink in the same request.
        query = query.options(selectinload(Role.permissions)).execution_options(
            populate_existing=True
        )
    return await db.scalar(query)


async def get_role_by_name(db: AsyncSession, name: str) -> Role | None:
    """Get a role by its unique name.

    Args:
        db: Database session.
        name: Role name.

    Returns:
        The role, or None.
    """
    return await db.scalar(select(Role).where(Role.name == name))


async def get_roles_by_names(db: AsyncSession, names: NameList) -> RoleList:
    """Get the roles whose names are in ``names`` (unknown names are skipped).

    Args:
        db: Database session.
        names: Role names.

    Returns:
        Matching roles.
    """
    if not names:
        return []
    return list(await db.scalars(select(Role).where(Role.name.in_(names))))


async def list_roles(
    db: AsyncSession, pagination: PaginationParams, search: str | None = None
) -> RoleListResult:
    """List roles ordered by name, optionally by name prefix.

    Args:
        db: Database session.
        pagination: Page parameters.
        search: Name prefix.

    Returns:
        Tuple of (roles on this page, total).
    """
    query = select(Role).order_by(Role.name)
    if search:
        query = query.where(
            Role.name.like(like_prefix(search, lowercase=False), escape=LIKE_ESCAPE)
        )
    return await paginate_query(db, query, pagination)


# Groups


async def get_group(
    db: AsyncSession, group_id: str, with_roles: bool = False
) -> Group | None:
    """Get a group by id.

    Args:
        db: Database session.
        group_id: Group identifier.
        with_roles: Eager-load the group's roles.

    Returns:
        The group, or None.
    """
    query = select(Group).where(Group.id == group_id)
    if with_roles:
        query = query.options(selectinload(Group.roles)).execution_options(
            populate_existing=True
        )
    return await db.scalar(query)


async def get_group_by_name(db: AsyncSession, name: str) -> Group | None:
    """Get a group by its unique name.

    Args:
        db: Database session.
        name: Group name.

    Returns:
        The group, or None.
    """
    return await db.scalar(select(Group).where(Group.name == name))


async def list_groups(
    db: AsyncSession, pagination: PaginationParams, search: str | None = None
) -> GroupListResult:
    """List groups ordered by name, optionally by name prefix.

    Args:
        db: Database session.
        pagination: Page parameters.
        search: Name prefix.

    Returns:
        Tuple of (groups on this page, total).
    """
    query = select(Group).order_by(Group.name)
    if search:
        query = query.where(
            Group.name.like(like_prefix(search, lowercase=False), escape=LIKE_ESCAPE)
        )
    return await paginate_query(db, query, pagination)


async def list_group_members(
    db: AsyncSession, group_id: str, pagination: PaginationParams
) -> UserListResult:
    """List a group's members ordered by username.

    Args:
        db: Database session.
        group_id: Group identifier.
        pagination: Page parameters.

    Returns:
        Tuple of (members on this page, total members).
    """
    query = (
        select(LocalUser)
        .join(user_groups, user_groups.c.user_id == LocalUser.id)
        .where(user_groups.c.group_id == group_id)
        .order_by(LocalUser.username)
    )
    return await paginate_query(db, query, pagination)
