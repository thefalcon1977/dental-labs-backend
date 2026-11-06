"""Command to stamp database with a revision."""

import typer
from alembic import command

from config.settings import settings

from .utils import get_alembic_config


def stamp(
    revision: str = typer.Option(..., "--revision", "-r", help="Revision to stamp"),
) -> None:
    """Stamp the database with a revision without running migrations."""
    if not settings.database.ENABLED:
        typer.echo("[ERROR] Database is not enabled in settings", err=True)
        raise typer.Exit(1)

    alembic_cfg = get_alembic_config()

    command.stamp(alembic_cfg, revision)
    typer.echo(f"[OK] Database stamped with revision: {revision}")
