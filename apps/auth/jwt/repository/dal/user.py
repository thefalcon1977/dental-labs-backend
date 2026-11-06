"""DAL for local users (reads)."""

from typing import TypeAlias

from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.core.utils import PaginationParams, paginate_query

from ...models import LocalUser
from .common import LIKE_ESCAPE, like_prefix

UserListResult: TypeAlias = tuple[list[LocalUser], int]


async def get_user_by_id(db: AsyncSession, user_id: str) -> LocalUser | None:
    """Get a user by primary key.

    Args:
        db: Database session.
        user_id: User identifier.

    Returns:
        The user, or None if not found.
    """
    return await db.get(LocalUser, user_id)


async def get_user_by_login(db: AsyncSession, login: str) -> LocalUser | None:
    """Get a user by username or email (both stored lowercase, both indexed).

    Args:
        db: Database session.
        login: Username or email, any case.

    Returns:
        The user, or None if not found.
    """
    value = login.strip().lower()
    result = await db.execute(
        select(LocalUser).where(
            or_(LocalUser.username == value, LocalUser.email == value)
        )
    )
    return result.scalars().first()


async def get_conflicting_field(
    db: AsyncSession, username: str, email: str
) -> str | None:
    """Return which unique field is already taken, if any.

    Args:
        db: Database session.
        username: Normalized username.
        email: Normalized email.

    Returns:
        ``"username"``, ``"email"``, or None when both are free.
    """
    result = await db.execute(
        select(LocalUser.username, LocalUser.email)
        .where(or_(LocalUser.username == username, LocalUser.email == email))
        .limit(1)
    )
    row = result.first()
    if row is None:
        return None
    return "username" if row.username == username else "email"


async def user_exists(db: AsyncSession, user_id: str) -> bool:
    """Check whether a user exists.

    Args:
        db: Database session.
        user_id: User identifier.

    Returns:
        True if the user exists.
    """
    return bool(await db.scalar(select(exists().where(LocalUser.id == user_id))))


async def list_users(
    db: AsyncSession, pagination: PaginationParams, search: str | None = None
) -> UserListResult:
    """List users ordered by username, optionally by username/email prefix.

    Args:
        db: Database session.
        pagination: Page parameters.
        search: Case-insensitive prefix of username or email.

    Returns:
        Tuple of (users on this page, total matching users).
    """
    query = select(LocalUser).order_by(LocalUser.username)
    if search:
        prefix = like_prefix(search)
        query = query.where(
            or_(
                LocalUser.username.like(prefix, escape=LIKE_ESCAPE),
                LocalUser.email.like(prefix, escape=LIKE_ESCAPE),
            )
        )
    return await paginate_query(db, query, pagination)
