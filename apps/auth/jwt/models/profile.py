"""Profile details for local JWT users (one-to-one with ``LocalUser``)."""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.core.models import BaseModel

if TYPE_CHECKING:
    from .user import LocalUser


class LocalUserProfile(BaseModel):
    """Optional personal details kept apart from credentials and identity.

    Created empty at registration; every field is nullable.
    """

    __tablename__ = "auth_user_profiles"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bio: Mapped[str | None] = mapped_column(String(500), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    locale: Mapped[str | None] = mapped_column(String(16), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user: Mapped["LocalUser"] = relationship(back_populates="profile", lazy="raise")
