"""Group model for local authorization."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, TypeAlias
from uuid import uuid4

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.core.db import Base

from .associations import group_roles_table, user_groups_table

if TYPE_CHECKING:
    from .role import Role
    from .user import User

UserList: TypeAlias = list["User"]
RoleList: TypeAlias = list["Role"]


class Group(Base):
    """User group that can aggregate roles for authorization."""

    __tablename__ = "auth_groups"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )

    users: Mapped[UserList] = relationship(
        "User",
        secondary=user_groups_table,
        back_populates="groups",
    )
    roles: Mapped[RoleList] = relationship(
        "Role",
        secondary=group_roles_table,
        back_populates="groups",
    )


__all__ = ["Group"]
