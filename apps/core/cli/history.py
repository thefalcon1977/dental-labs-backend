"""Command to show migration history."""

import typer
from alembic import command

from config.settings import settings

from .utils import get_alembic_config


def history() -> None:
    """Show migration history."""
    if not settings.database.ENABLED:
        typer.echo("[ERROR] Database is not enabled in settings", err=True)
        raise typer.Exit(1)

    alembic_cfg = get_alembic_config()
    command.history(alembic_cfg)
