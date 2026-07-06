"""Role model for local authorization."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, TypeAlias
from uuid import uuid4

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.core.db import Base

from .associations import group_roles_table, user_roles_table

if TYPE_CHECKING:
    from .group import Group
    from .user import User

UserList: TypeAlias = list["User"]
GroupList: TypeAlias = list["Group"]


class Role(Base):
    """Role assigned to users or groups for authorization."""

    __tablename__ = "auth_roles"

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
        secondary=user_roles_table,
        back_populates="roles",
    )
    groups: Mapped[GroupList] = relationship(
        "Group",
        secondary=group_roles_table,
        back_populates="roles",
    )


__all__ = ["Role"]
