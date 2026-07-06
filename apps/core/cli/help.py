"""Command to display help information."""

from typing import TYPE_CHECKING

import typer
from click.formatting import HelpFormatter
from typer.main import get_command

if TYPE_CHECKING:
    pass


def help() -> None:
    """Show help information and available commands.

    This command behaves exactly like `--help`, displaying Typer's
    built-in help output with all available commands and options.
    """
    # Import cli here to avoid circular import
    from . import cli as cli_app

    # Get the root CLI command (Typer wraps Click commands)
    command = get_command(cli_app)
    # Create a context and format help exactly like --help does
    ctx = command.make_context("help", ["--help"])
    # Create formatter and format help
    formatter = HelpFormatter()
    command.format_help(ctx, formatter)
    # Print the formatted help
    typer.echo(formatter.getvalue())
