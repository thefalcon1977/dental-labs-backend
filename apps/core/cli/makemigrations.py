"""Command to create database migrations."""

import typer
from alembic import command

from config.settings import settings

from .utils import get_alembic_config


def makemigrations(
    message: str = typer.Option(..., "--message", "-m", help="Migration message"),
    autogenerate: bool = typer.Option(
        True, "--autogenerate/--no-autogenerate", help="Auto-generate migration"
    ),
) -> None:
    """Create a new migration."""
    if not settings.database.ENABLED:
        typer.echo("[ERROR] Database is not enabled in settings", err=True)
        raise typer.Exit(1)

    alembic_cfg = get_alembic_config()

    if autogenerate:
        command.revision(alembic_cfg, message=message, autogenerate=True)
        typer.echo(f"[OK] Migration created: {message}")
    else:
        command.revision(alembic_cfg, message=message)
        typer.echo(f"[OK] Empty migration created: {message}")
