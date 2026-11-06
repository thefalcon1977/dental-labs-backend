"""CLI package for the FastAPI application.

This package contains Typer-based CLI commands used via `python manage.py ...`.
Single commands are registered directly on the root CLI, while command groups
(like database commands) use sub-Typer apps.
"""

import typer

from . import (
    build_docker,
    build_docs,
    create_admin,
    db,
    export_packages,
    generate_secret_key,
    help,
    runserver,
    show_config,
)

# Create root Typer app for CLI commands
cli = typer.Typer(
    help="CLI commands for the FastAPI application",
    no_args_is_help=False,  # Allow default to runserver
)

# Register single commands directly (not as sub-Typer apps)
cli.command()(runserver.runserver)
cli.command()(help.help)
cli.command(name="show-config")(show_config.show_config)
cli.command(name="generate-secret-key")(generate_secret_key.generate_secret_key)
cli.command(name="build-docker")(build_docker.build_docker)
cli.command(name="build-docs")(build_docs.build_docs)
cli.command(name="export-packages")(export_packages.export_packages)
cli.command(name="create-admin")(create_admin.create_admin)

# Register command groups as sub-Typer apps
cli.add_typer(db.app, name="db")

__all__ = ["cli"]
