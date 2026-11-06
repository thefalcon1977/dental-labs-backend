"""BLL for local user profiles (writes)."""

from sqlalchemy.ext.asyncio import AsyncSession

from ... import schemas
from ...models import LocalUserProfile
from .. import dal


async def update_profile(
    db: AsyncSession, user_id: str, data: schemas.ProfileUpdate
) -> LocalUserProfile:
    """Apply a partial profile update, creating the profile if missing.

    Args:
        db: Database session.
        user_id: Owning user identifier.
        data: Fields to change; unset fields are left as they are.

    Returns:
        The updated profile.
    """
    profile = await dal.get_profile_by_user_id(db, user_id)
    if profile is None:
        profile = LocalUserProfile(user_id=user_id)
        db.add(profile)

    for field in data.model_fields_set:
        value = getattr(data, field)
        if field == "avatar_url" and value is not None:
            value = str(value)
        setattr(profile, field, value)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    await db.refresh(profile)
    return profile
