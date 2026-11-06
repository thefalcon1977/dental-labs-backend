"""Command to show applied migrations."""

import asyncio

import typer
from sqlalchemy import text

from apps.core.db import DatabaseManager
from config.settings import settings


def show_applied() -> None:
    """Show applied migrations."""
    if not settings.database.ENABLED:
        typer.echo("[ERROR] Database is not enabled in settings", err=True)
        raise typer.Exit(1)

    async def show_current() -> None:
        db_manager = DatabaseManager()
        await db_manager.initialize()

        try:
            engine = db_manager.get_engine()
            async with engine.begin() as conn:
                result = await conn.execute(
                    text("SELECT version_num FROM alembic_version")
                )
                row = result.fetchone()
                if row:
                    typer.echo(f"[OK] Current revision: {row[0]}")
                else:
                    typer.echo("[WARN] No migrations applied yet")
        except Exception as e:
            typer.echo(f"[ERROR] Error checking migrations: {e}", err=True)
            raise typer.Exit(1)
        finally:
            await db_manager.close()

    asyncio.run(show_current())
