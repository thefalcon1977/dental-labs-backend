"""Database command group for Alembic operations."""

import typer

from .downgrade import downgrade
from .makemigrations import makemigrations
from .migrate import migrate

app = typer.Typer(help="Database migration commands")

app.command()(migrate)
app.command()(makemigrations)
app.command()(downgrade)

__all__ = ["app"]
