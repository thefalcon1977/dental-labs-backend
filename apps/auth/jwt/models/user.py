"""Local user account model for JWT authentication mode."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.core.models import BaseModel

from .rbac import user_groups, user_roles

if TYPE_CHECKING:
    from .profile import LocalUserProfile
    from .rbac import Group, Role


class LocalUser(BaseModel):
    """User account authenticated by this service (not by Keycloak).

    Usernames and emails are stored lowercase so uniqueness is
    case-insensitive.
    """

    __tablename__ = "auth_users"

    username: Mapped[str] = mapped_column(
        String(150), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # lazy="raise": async sessions can't lazy-load, so related rows are loaded
    # explicitly in the DAL instead of on every login/refresh.
    profile: Mapped["LocalUserProfile | None"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )
    roles: Mapped[list["Role"]] = relationship(
        secondary=user_roles,
        back_populates="users",
        passive_deletes=True,
        lazy="raise",
    )
    groups: Mapped[list["Group"]] = relationship(
        secondary=user_groups,
        back_populates="users",
        passive_deletes=True,
        lazy="raise",
    )
