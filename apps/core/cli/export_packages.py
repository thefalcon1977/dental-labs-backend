"""CLI command for exporting Poetry dependencies to requirements files."""

import subprocess
from pathlib import Path
from typing import TypeAlias

import typer

from config.settings import settings

CommandArgs: TypeAlias = list[str]


def _run_poetry_export(command: CommandArgs, description: str) -> None:
    """Run a Poetry export command with consistent error handling.

    Args:
        command: Poetry export command arguments
        description: Description for logging output

    Raises:
        typer.Exit: If the export command fails
    """
    typer.echo(f"[INFO] Exporting {description} requirements")

    try:
        subprocess.run(
            command,
            check=True,
            capture_output=False,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        typer.echo(f"[ERROR] Poetry export failed: {exc}", err=True)
        raise typer.Exit(1)
    except FileNotFoundError:
        typer.echo(
            "[ERROR] Poetry not found. Please install Poetry and ensure it's in PATH.",
            err=True,
        )
        raise typer.Exit(1)
    except Exception as exc:
        typer.echo(f"[ERROR] Unexpected error: {exc}", err=True)
        if settings.DEBUG:
            import traceback

            typer.echo(traceback.format_exc(), err=True)
        raise typer.Exit(1)


def export_packages(
    target: str = typer.Option(
        "all",
        "--target",
        "-t",
        help="Which requirements to export: all, dev, or prod",
    ),
) -> None:
    """Export Poetry dependencies to requirements files.

    Uses the project-defined export rules:
    - dev: main + dev + doc + s3 groups
    - prod: main + doc + s3 groups

    Args:
        target: Export target (all, dev, or prod)
    """
    target_normalized = target.strip().lower()
    if target_normalized not in {"all", "dev", "prod"}:
        typer.echo(
            "[ERROR] Invalid target. Use one of: all, dev, prod.",
            err=True,
        )
        raise typer.Exit(1)

    dev_command: CommandArgs = [
        "poetry",
        "export",
        "-f",
        "requirements.txt",
        "--output",
        str(Path("requirements") / "dev.txt"),
        "--with",
        "dev",
        "--with",
        "doc",
        "--with",
        "s3",
        "--without-hashes",
    ]
    prod_command: CommandArgs = [
        "poetry",
        "export",
        "-f",
        "requirements.txt",
        "--output",
        str(Path("requirements") / "prod.txt"),
        "--with",
        "doc",
        "--with",
        "s3",
        "--without-hashes",
    ]

    if target_normalized in {"all", "dev"}:
        _run_poetry_export(dev_command, "dev")

    if target_normalized in {"all", "prod"}:
        _run_poetry_export(prod_command, "prod")

    typer.echo("[OK] Requirements export completed")
