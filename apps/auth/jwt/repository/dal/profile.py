"""DAL for local user profiles (reads)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import LocalUserProfile


async def get_profile_by_user_id(
    db: AsyncSession, user_id: str
) -> LocalUserProfile | None:
    """Get a user's profile via the unique ``user_id`` index.

    Args:
        db: Database session.
        user_id: Owning user identifier.

    Returns:
        The profile, or None if the user has none yet.
    """
    result = await db.execute(
        select(LocalUserProfile).where(LocalUserProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()
