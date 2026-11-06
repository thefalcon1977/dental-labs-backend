"""Database command group for migration operations."""

import typer

from . import downgrade, history, makemigrations, migrate, show_applied, stamp

# Create Typer app for database command group
app = typer.Typer(
    help="Database migration commands",
    no_args_is_help=True,
)

# Register all database commands directly (not as sub-Typer apps)
# This ensures options/switches are shown in help
app.command()(makemigrations.makemigrations)
app.command()(migrate.migrate)
app.command()(downgrade.downgrade)
app.command()(history.history)
app.command(name="show-applied")(show_applied.show_applied)
app.command()(stamp.stamp)
