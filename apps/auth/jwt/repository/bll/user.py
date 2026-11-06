"""BLL for local users (writes)."""

from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings

from ... import schemas
from ...helpers.exceptions import UserAlreadyExistsError
from ...models import LocalUser, LocalUserProfile
from ...utils.passwords import hash_password
from .. import dal


async def create_user(db: AsyncSession, data: schemas.RegisterRequest) -> LocalUser:
    """Create a local user (with an empty profile) in one transaction.

    The password is hashed and the roles named in ``auth.JWT_DEFAULT_ROLES``
    are granted (names with no matching role are skipped).

    Args:
        db: Database session.
        data: Validated, normalized registration data.

    Returns:
        The created user.

    Raises:
        UserAlreadyExistsError: If the username or email is taken.
    """
    conflict = await dal.get_conflicting_field(db, data.username, data.email)
    if conflict:
        raise UserAlreadyExistsError(conflict)

    user = LocalUser(
        username=data.username,
        email=data.email,
        password_hash=await hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        roles=await dal.get_roles_by_names(db, list(settings.auth.JWT_DEFAULT_ROLES)),
        is_active=True,
        profile=LocalUserProfile(),
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as e:
        # Lost a race with a concurrent registration for the same identity.
        await db.rollback()
        raise UserAlreadyExistsError("username or email") from e
    await db.refresh(user)
    return user


async def record_login(db: AsyncSession, user: LocalUser) -> LocalUser:
    """Stamp the user's last successful login time.

    Args:
        db: Database session.
        user: User who just authenticated.

    Returns:
        The updated user.
    """
    user.last_login_at = datetime.now(UTC)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    await db.refresh(user)
    return user
