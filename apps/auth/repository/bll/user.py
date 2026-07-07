"""Business Logic Layer for auth user write operations."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth import models, schemas
from apps.auth.helpers.exceptions import UserAlreadyExistsError
from apps.auth.repository.dal import (
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
)
from apps.auth.utils.password import hash_password


async def create_user(
    db: AsyncSession,
    user_data: schemas.UserCreate,
) -> models.User:
    """Create a user with a default profile in one transaction.

    Args:
        db: Database session.
        user_data: User creation data.

    Returns:
        Created user model with profile.

    Raises:
        UserAlreadyExistsError: If email or username already exists.
    """
    existing_email_user = await get_user_by_email(db, user_data.email)
    if existing_email_user is not None:
        raise UserAlreadyExistsError(field="email", value=user_data.email)

    existing_username_user = await get_user_by_username(db, user_data.username)
    if existing_username_user is not None:
        raise UserAlreadyExistsError(field="username", value=user_data.username)

    user = models.User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hash_password(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
    )
    user.profile = models.Profile(
        display_name=user_data.username,
    )

    try:
        db.add(user)
        await db.commit()
        await db.refresh(user)
    except IntegrityError as exc:
        await db.rollback()
        raise UserAlreadyExistsError(
            field="email",
            value=user_data.email,
        ) from exc
    except Exception:
        await db.rollback()
        raise

    created_user = await get_user_by_id(db, user.id)
    if created_user is None:
        return user
    return created_user


__all__ = ["create_user"]
