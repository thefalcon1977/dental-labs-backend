"""Command to downgrade database migrations."""

import typer
from alembic import command

from config.settings import settings

from .utils import get_alembic_config


def downgrade(
    revision: str = typer.Option(
        ..., "--revision", "-r", help="Target revision to downgrade to"
    ),
) -> None:
    """Downgrade migrations."""
    if not settings.database.ENABLED:
        typer.echo("[ERROR] Database is not enabled in settings", err=True)
        raise typer.Exit(1)

    alembic_cfg = get_alembic_config()

    # Run downgrade (Alembic handles async via env.py)
    command.downgrade(alembic_cfg, revision)
    typer.echo(f"[OK] Migrations downgraded to: {revision}")
