"""BLL for groups, roles, permissions, and their assignments (writes)."""

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings

from ... import schemas
from ...helpers.exceptions import ResourceAlreadyExistsError
from ...models import (
    Group,
    Permission,
    Role,
    group_roles,
    role_permissions,
    user_groups,
    user_roles,
)
from .. import dal
from .common import commit, delete_entity, link, save_named, unlink


async def create_permission(
    db: AsyncSession, data: schemas.PermissionCreate
) -> Permission:
    """Create a permission.

    Args:
        db: Database session.
        data: Permission data.

    Returns:
        The created permission.

    Raises:
        ResourceAlreadyExistsError: If the code is taken.
    """
    if await dal.get_permission_by_code(db, data.code):
        raise ResourceAlreadyExistsError("Permission", "code", data.code)
    permission = Permission(code=data.code, description=data.description)
    db.add(permission)
    return await save_named(db, permission, "Permission", "code")


async def update_permission(
    db: AsyncSession, permission: Permission, data: schemas.PermissionUpdate
) -> Permission:
    """Update a permission's description.

    Args:
        db: Database session.
        permission: Permission to update.
        data: Fields to change.

    Returns:
        The updated permission.
    """
    if "description" in data.model_fields_set:
        permission.description = data.description
    await commit(db)
    await db.refresh(permission)
    return permission


async def delete_permission(db: AsyncSession, permission: Permission) -> None:
    """Delete a permission and remove it from every role.

    Args:
        db: Database session.
        permission: Permission to delete.
    """
    await delete_entity(db, permission)


async def create_role(db: AsyncSession, data: schemas.RoleCreate) -> Role:
    """Create a role.

    Args:
        db: Database session.
        data: Role data.

    Returns:
        The created role.

    Raises:
        ResourceAlreadyExistsError: If the name is taken.
    """
    if await dal.get_role_by_name(db, data.name):
        raise ResourceAlreadyExistsError("Role", "name", data.name)
    role = Role(name=data.name, description=data.description)
    db.add(role)
    return await save_named(db, role, "Role", "name")


async def update_role(db: AsyncSession, role: Role, data: schemas.RoleUpdate) -> Role:
    """Rename and/or re-describe a role.

    Args:
        db: Database session.
        role: Role to update.
        data: Fields to change.

    Returns:
        The updated role.

    Raises:
        ResourceAlreadyExistsError: If the new name is taken.
    """
    if data.name is not None and data.name != role.name:
        if await dal.get_role_by_name(db, data.name):
            raise ResourceAlreadyExistsError("Role", "name", data.name)
        role.name = data.name
    if "description" in data.model_fields_set:
        role.description = data.description
    return await save_named(db, role, "Role", "name")


async def delete_role(db: AsyncSession, role: Role) -> None:
    """Delete a role and revoke it from every user and group.

    Args:
        db: Database session.
        role: Role to delete.
    """
    await delete_entity(db, role)


async def add_permission_to_role(
    db: AsyncSession, role_id: str, permission_id: str
) -> None:
    """Grant a permission to a role.

    Args:
        db: Database session.
        role_id: Role identifier.
        permission_id: Permission identifier.
    """
    await link(
        db, role_permissions, {"role_id": role_id, "permission_id": permission_id}
    )


async def remove_permission_from_role(
    db: AsyncSession, role_id: str, permission_id: str
) -> None:
    """Revoke a permission from a role.

    Args:
        db: Database session.
        role_id: Role identifier.
        permission_id: Permission identifier.
    """
    await unlink(
        db, role_permissions, {"role_id": role_id, "permission_id": permission_id}
    )


async def create_group(db: AsyncSession, data: schemas.GroupCreate) -> Group:
    """Create a group.

    Args:
        db: Database session.
        data: Group data.

    Returns:
        The created group.

    Raises:
        ResourceAlreadyExistsError: If the name is taken.
    """
    if await dal.get_group_by_name(db, data.name):
        raise ResourceAlreadyExistsError("Group", "name", data.name)
    group = Group(name=data.name, description=data.description)
    db.add(group)
    return await save_named(db, group, "Group", "name")


async def update_group(
    db: AsyncSession, group: Group, data: schemas.GroupUpdate
) -> Group:
    """Rename and/or re-describe a group.

    Args:
        db: Database session.
        group: Group to update.
        data: Fields to change.

    Returns:
        The updated group.

    Raises:
        ResourceAlreadyExistsError: If the new name is taken.
    """
    if data.name is not None and data.name != group.name:
        if await dal.get_group_by_name(db, data.name):
            raise ResourceAlreadyExistsError("Group", "name", data.name)
        group.name = data.name
    if "description" in data.model_fields_set:
        group.description = data.description
    return await save_named(db, group, "Group", "name")


async def delete_group(db: AsyncSession, group: Group) -> None:
    """Delete a group; members lose the group's roles.

    Args:
        db: Database session.
        group: Group to delete.
    """
    await delete_entity(db, group)


async def add_role_to_group(db: AsyncSession, group_id: str, role_id: str) -> None:
    """Grant a role to a group.

    Args:
        db: Database session.
        group_id: Group identifier.
        role_id: Role identifier.
    """
    await link(db, group_roles, {"group_id": group_id, "role_id": role_id})


async def remove_role_from_group(db: AsyncSession, group_id: str, role_id: str) -> None:
    """Revoke a role from a group.

    Args:
        db: Database session.
        group_id: Group identifier.
        role_id: Role identifier.
    """
    await unlink(db, group_roles, {"group_id": group_id, "role_id": role_id})


async def add_user_to_group(db: AsyncSession, group_id: str, user_id: str) -> None:
    """Add a user to a group.

    Args:
        db: Database session.
        group_id: Group identifier.
        user_id: User identifier.
    """
    await link(db, user_groups, {"user_id": user_id, "group_id": group_id})


async def remove_user_from_group(db: AsyncSession, group_id: str, user_id: str) -> None:
    """Remove a user from a group.

    Args:
        db: Database session.
        group_id: Group identifier.
        user_id: User identifier.
    """
    await unlink(db, user_groups, {"user_id": user_id, "group_id": group_id})


async def add_role_to_user(db: AsyncSession, user_id: str, role_id: str) -> None:
    """Grant a role to a user directly.

    Args:
        db: Database session.
        user_id: User identifier.
        role_id: Role identifier.
    """
    await link(db, user_roles, {"user_id": user_id, "role_id": role_id})


async def remove_role_from_user(db: AsyncSession, user_id: str, role_id: str) -> None:
    """Revoke a role granted to a user directly (group roles are unaffected).

    Args:
        db: Database session.
        user_id: User identifier.
        role_id: Role identifier.
    """
    await unlink(db, user_roles, {"user_id": user_id, "role_id": role_id})


async def ensure_admin_role(db: AsyncSession) -> Role:
    """Get or create the admin role and permission, and link them.

    Uses ``auth.JWT_ADMIN_ROLE`` and ``auth.JWT_ADMIN_PERMISSION``. Safe to run
    repeatedly; the migration normally seeds these already.

    Args:
        db: Database session.

    Returns:
        The admin role.
    """
    code = str(settings.auth.JWT_ADMIN_PERMISSION)
    permission = await dal.get_permission_by_code(db, code)
    if permission is None:
        permission = Permission(code=code, description="Manage access control")
        db.add(permission)
        await db.flush()

    name = str(settings.auth.JWT_ADMIN_ROLE)
    role = await dal.get_role_by_name(db, name)
    if role is None:
        role = Role(name=name, description="Administrator")
        db.add(role)
        await db.flush()

    await db.execute(
        insert(role_permissions)
        .values(role_id=role.id, permission_id=permission.id)
        .on_conflict_do_nothing()
    )
    await commit(db)
    return role
