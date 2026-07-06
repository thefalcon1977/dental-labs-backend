"""Main entry point for the FastAPI application and CLI commands."""

import os
import sys
from typing import TypeAlias

from apps.core.app_factory import create_app, set_workers_count
from apps.core.cli import cli
from apps.core.cli.utils import calculate_workers
from config.logging import setup_logging
from config.settings import settings

ArgsList: TypeAlias = list[str]


def _is_runserver_invocation(args: ArgsList) -> bool:
    """Check whether the command invocation targets runserver.

    Args:
        args: Command-line arguments.

    Returns:
        True when runserver is the target command.
    """
    if len(args) == 1:
        return True
    return args[1] == "runserver"


def _is_reload_enabled(args: ArgsList) -> bool:
    """Determine whether reload is enabled for this invocation.

    Args:
        args: Command-line arguments.

    Returns:
        True when reload is enabled, False otherwise.
    """
    if "--no-reload" in args:
        return False
    if "--reload" in args:
        return True
    return settings.DEBUG


if (
    _is_runserver_invocation(sys.argv)
    and _is_reload_enabled(sys.argv)
    and "APP_RELOAD_PARENT_PID" not in os.environ
):
    os.environ["APP_RELOAD_PARENT_PID"] = str(os.getpid())

# Setup logging before creating app
setup_logging()

# Calculate and set workers count before creating app
workers = calculate_workers()
set_workers_count(workers)

# Create FastAPI app instance
app = create_app()


if __name__ == "__main__":
    # If no arguments provided, default to 'runserver' command
    if len(sys.argv) == 1:
        # No arguments - run the server
        from apps.core.cli.runserver import runserver

        runserver()
    else:
        # Arguments provided - use CLI
        cli()
