"""Transaction and link-table helpers shared by the BLL modules."""

from typing import TypeAlias

from sqlalchemy import Table, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...helpers.exceptions import ResourceAlreadyExistsError
from ...models import Group, Permission, Role

LinkValues: TypeAlias = dict[str, str]
NamedEntity: TypeAlias = Group | Role | Permission


async def commit(db: AsyncSession) -> None:
    """Commit, rolling back on any failure.

    Args:
        db: Database session.
    """
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise


async def save_named(
    db: AsyncSession, entity: NamedEntity, resource: str, field: str
) -> NamedEntity:
    """Commit a new or renamed group/role/permission, mapping unique violations.

    Args:
        db: Database session.
        entity: Entity to persist (already added to the session).
        resource: Resource label for the error, e.g. ``Role``.
        field: Unique field name, e.g. ``name``.

    Returns:
        The refreshed entity.

    Raises:
        ResourceAlreadyExistsError: If the unique field is taken.
    """
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise ResourceAlreadyExistsError(
            resource, field, str(getattr(entity, field))
        ) from e
    await db.refresh(entity)
    return entity


async def link(db: AsyncSession, table: Table, values: LinkValues) -> None:
    """Insert a link row; already-linked is a no-op (idempotent PUT).

    Args:
        db: Database session.
        table: Many-to-many link table.
        values: Column values for the row.
    """
    await db.execute(insert(table).values(**values).on_conflict_do_nothing())
    await commit(db)


async def unlink(db: AsyncSession, table: Table, values: LinkValues) -> None:
    """Delete a link row; not-linked is a no-op (idempotent DELETE).

    Args:
        db: Database session.
        table: Many-to-many link table.
        values: Column values identifying the row.
    """
    conditions = [table.c[column] == value for column, value in values.items()]
    await db.execute(delete(table).where(*conditions))
    await commit(db)


async def delete_entity(db: AsyncSession, entity: NamedEntity) -> None:
    """Delete an entity; link rows go with it via ``ON DELETE CASCADE``.

    Args:
        db: Database session.
        entity: Entity to delete.
    """
    await db.delete(entity)
    await commit(db)
