"""Data Access Layer for auth user read operations."""

from typing import TypeAlias

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.auth import models
from apps.core.utils import PaginationParams, paginate_query

UserList: TypeAlias = list[models.User]
UserListResult: TypeAlias = tuple[UserList, int]


def _user_detail_options() -> tuple[object, object, object]:
    """Return eager-loading options for user detail queries.

    Returns:
        Tuple of SQLAlchemy loader options for user relationships.
    """
    return (
        selectinload(models.User.profile),
        selectinload(models.User.groups),
        selectinload(models.User.roles),
    )


async def get_user_by_id(
    db: AsyncSession,
    user_id: str,
) -> models.User | None:
    """Get a user by ID with profile, groups, and roles.

    Args:
        db: Database session.
        user_id: User identifier.

    Returns:
        User model instance if found, None otherwise.
    """
    result = await db.execute(
        select(models.User)
        .options(*_user_detail_options())
        .where(models.User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_email(
    db: AsyncSession,
    email: str,
) -> models.User | None:
    """Get a user by normalized email.

    Args:
        db: Database session.
        email: Normalized user email.

    Returns:
        User model instance if found, None otherwise.
    """
    result = await db.execute(
        select(models.User)
        .options(*_user_detail_options())
        .where(models.User.email == email)
    )
    return result.scalar_one_or_none()


async def get_user_by_username(
    db: AsyncSession,
    username: str,
) -> models.User | None:
    """Get a user by username.

    Args:
        db: Database session.
        username: User username.

    Returns:
        User model instance if found, None otherwise.
    """
    result = await db.execute(
        select(models.User)
        .options(*_user_detail_options())
        .where(models.User.username == username)
    )
    return result.scalar_one_or_none()


async def list_users(
    db: AsyncSession,
    pagination: PaginationParams,
    active_only: bool = False,
) -> UserListResult:
    """List users with SQL-level pagination.

    Args:
        db: Database session.
        pagination: Pagination parameters.
        active_only: Whether to include only active users.

    Returns:
        Tuple of users and total item count.
    """
    query = select(models.User).options(*_user_detail_options())

    if active_only:
        query = query.where(models.User.is_active.is_(True))

    query = query.order_by(models.User.created_at.desc())
    users, total_items = await paginate_query(db, query, pagination)
    return users, total_items


__all__ = [
    "UserList",
    "UserListResult",
    "get_user_by_email",
    "get_user_by_id",
    "get_user_by_username",
    "list_users",
]
