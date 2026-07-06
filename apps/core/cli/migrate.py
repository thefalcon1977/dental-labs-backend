"""Command to apply database migrations."""

import typer
from alembic import command

from config.settings import settings

from .utils import get_alembic_config


def migrate(
    revision: str = typer.Option("head", "--revision", "-r", help="Target revision"),
) -> None:
    """Apply migrations."""
    if not settings.database.ENABLED:
        typer.echo("[ERROR] Database is not enabled in settings", err=True)
        raise typer.Exit(1)

    alembic_cfg = get_alembic_config()

    # Run migration (Alembic handles async via env.py)
    command.upgrade(alembic_cfg, revision)
    typer.echo(f"[OK] Migrations applied up to: {revision}")
