"""User models for local authentication."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, TypeAlias
from uuid import uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.core.db import Base

from .associations import user_groups_table, user_roles_table

if TYPE_CHECKING:
    from .group import Group
    from .profile import Profile
    from .role import Role

GroupList: TypeAlias = list["Group"]
RoleList: TypeAlias = list["Role"]


class UserBase(Base):
    """Abstract base model for local authenticated users."""

    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    username: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(default=False, nullable=False)
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


class User(UserBase):
    """Concrete local user model with groups and roles."""

    __tablename__ = "auth_users"

    groups: Mapped[GroupList] = relationship(
        "Group",
        secondary=user_groups_table,
        back_populates="users",
    )
    roles: Mapped[RoleList] = relationship(
        "Role",
        secondary=user_roles_table,
        back_populates="users",
    )
    profile: Mapped["Profile | None"] = relationship(
        "Profile",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )


__all__ = ["User", "UserBase"]
