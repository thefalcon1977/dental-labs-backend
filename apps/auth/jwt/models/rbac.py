"""Groups, roles, and permissions for local JWT users (Keycloak-style RBAC).

- Users belong to many groups; groups have many users.
- Roles are granted directly to users and to groups.
- Roles bundle permissions.

A user's effective roles are their own plus their groups' roles; effective
permissions are the union of those roles' permissions.
"""

from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.core.db import Base
from apps.core.models import BaseModel

if TYPE_CHECKING:
    from .user import LocalUser


def _link_table(name: str, left: str, left_fk: str, right: str, right_fk: str) -> Table:
    """Build a many-to-many link table with cascading foreign keys.

    The composite primary key indexes ``left``; ``right`` gets its own index
    for reverse lookups.

    Args:
        name: Table name.
        left: Left column name.
        left_fk: Left foreign key target (``table.column``).
        right: Right column name.
        right_fk: Right foreign key target (``table.column``).

    Returns:
        The link table.
    """
    return Table(
        name,
        Base.metadata,
        Column(
            left,
            String(36),
            ForeignKey(left_fk, ondelete="CASCADE"),
            primary_key=True,
        ),
        Column(
            right,
            String(36),
            ForeignKey(right_fk, ondelete="CASCADE"),
            primary_key=True,
            index=True,
        ),
    )


user_groups = _link_table(
    "auth_user_groups", "user_id", "auth_users.id", "group_id", "auth_groups.id"
)
user_roles = _link_table(
    "auth_user_roles", "user_id", "auth_users.id", "role_id", "auth_roles.id"
)
group_roles = _link_table(
    "auth_group_roles", "group_id", "auth_groups.id", "role_id", "auth_roles.id"
)
role_permissions = _link_table(
    "auth_role_permissions",
    "role_id",
    "auth_roles.id",
    "permission_id",
    "auth_permissions.id",
)


class Permission(BaseModel):
    """A single grantable capability, e.g. ``orders:read``."""

    __tablename__ = "auth_permissions"

    code: Mapped[str] = mapped_column(
        String(150), unique=True, index=True, nullable=False
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    roles: Mapped[list["Role"]] = relationship(
        secondary=role_permissions,
        back_populates="permissions",
        passive_deletes=True,
        lazy="raise",
    )


class Role(BaseModel):
    """A named bundle of permissions, granted to users or groups."""

    __tablename__ = "auth_roles"

    name: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    permissions: Mapped[list[Permission]] = relationship(
        secondary=role_permissions,
        back_populates="roles",
        passive_deletes=True,
        lazy="raise",
    )
    groups: Mapped[list["Group"]] = relationship(
        secondary=group_roles,
        back_populates="roles",
        passive_deletes=True,
        lazy="raise",
    )
    users: Mapped[list["LocalUser"]] = relationship(
        secondary=user_roles,
        back_populates="roles",
        passive_deletes=True,
        lazy="raise",
    )


class Group(BaseModel):
    """A set of users that share the group's roles."""

    __tablename__ = "auth_groups"

    name: Mapped[str] = mapped_column(
        String(150), unique=True, index=True, nullable=False
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    roles: Mapped[list[Role]] = relationship(
        secondary=group_roles,
        back_populates="groups",
        passive_deletes=True,
        lazy="raise",
    )
    users: Mapped[list["LocalUser"]] = relationship(
        secondary=user_groups,
        back_populates="groups",
        passive_deletes=True,
        lazy="raise",
    )
