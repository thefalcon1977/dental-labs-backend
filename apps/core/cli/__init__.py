"""CLI package for the FastAPI application.

This package contains Typer-based CLI commands used via `python manage.py ...`.
Single commands are registered directly on the root CLI, while command groups
(like database commands) use sub-Typer apps.
"""

import typer

from . import db, generate_secret_key, help, runserver

# Create root Typer app for CLI commands
cli = typer.Typer(
    help="CLI commands for the FastAPI application",
    no_args_is_help=False,  # Allow default to runserver
)

# Register single commands directly (not as sub-Typer apps)
cli.command()(runserver.runserver)
cli.command()(help.help)
cli.command(name="generate-secret-key")(generate_secret_key.generate_secret_key)

# Register command groups as sub-Typer apps
cli.add_typer(db.app, name="db")

__all__ = ["cli"]
