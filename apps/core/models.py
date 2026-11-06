"""Base models and mixins using SQLAlchemy 2.0 best practices.

This module provides reusable base classes and mixins for database models:

- TimestampMixin: Adds created_at and updated_at timestamp fields
- BaseModel: Base model with UUID primary key and timestamps

These can be used as building blocks for application-specific models,
ensuring consistency across the codebase.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from apps.core.db import Base


class TimestampMixin:
    """Mixin for timestamp fields.

    Provides automatic timestamp tracking with created_at and updated_at fields.
    The created_at field is set automatically on insert, and updated_at is
    updated automatically on record modification.

    Example:
        ```python
        class User(Base, TimestampMixin):
            __tablename__ = "users"
            id: Mapped[str] = mapped_column(String(36), primary_key=True)
            # Automatically has created_at and updated_at fields
        ```
    """

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


class BaseModel(Base, TimestampMixin):
    """Base model with common fields.

    Abstract base model that combines:
    - SQLAlchemy Base for ORM functionality
    - TimestampMixin for automatic timestamp tracking
    - UUID primary key (string format)

    This model is abstract (doesn't create a table) and should be inherited
    by application-specific models.

    Example:
        ```python
        class User(BaseModel):
            __tablename__ = "users"
            email: Mapped[str] = mapped_column(String(255), unique=True)
            # Automatically has: id, created_at, updated_at
        ```
    """

    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        nullable=False,
    )


# Example usage:
# class User(BaseModel):
#     __tablename__ = "users"
#
#     email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
#     name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
#     is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
