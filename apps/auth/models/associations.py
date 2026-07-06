"""Association tables for auth user, group, and role models."""

from sqlalchemy import Column, ForeignKey, Table

from apps.core.db import Base

user_groups_table = Table(
    "auth_user_groups",
    Base.metadata,
    Column(
        "user_id",
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "group_id",
        ForeignKey("auth_groups.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
"""Many-to-many association table between users and groups."""

user_roles_table = Table(
    "auth_user_roles",
    Base.metadata,
    Column(
        "user_id",
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "role_id",
        ForeignKey("auth_roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
"""Many-to-many association table between users and roles."""

group_roles_table = Table(
    "auth_group_roles",
    Base.metadata,
    Column(
        "group_id",
        ForeignKey("auth_groups.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "role_id",
        ForeignKey("auth_roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
"""Many-to-many association table between groups and roles."""

__all__ = [
    "group_roles_table",
    "user_groups_table",
    "user_roles_table",
]
