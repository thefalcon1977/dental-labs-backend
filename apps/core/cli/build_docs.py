"""Command to build Sphinx documentation."""

import shutil
import subprocess
import sys
from pathlib import Path

import typer

from config.settings import settings


def build_docs(
    builder: str = typer.Option(
        "html",
        "--builder",
        "-b",
        help="Sphinx builder to use (e.g., html, latex, epub)",
    ),
    source_dir: str = typer.Option(
        "docs/source",
        "--source",
        "-s",
        help="Source directory containing documentation",
    ),
    build_dir: str = typer.Option(
        "docs/build",
        "--build",
        "-d",
        help="Build directory for output",
    ),
    clean: bool = typer.Option(
        True,
        "--clean/--no-clean",
        help="Remove build directory before building",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Run in verbose mode",
    ),
) -> None:
    """Build Sphinx documentation.

    Removes the build directory (if it exists) and rebuilds the documentation
    from the source directory. This ensures a clean build with all updates.

    Examples:
        # Build HTML documentation (default)
        python manage.py build-docs

        # Build without cleaning first
        python manage.py build-docs --no-clean

        # Build with verbose output
        python manage.py build-docs --verbose

        # Build for different output format
        python manage.py build-docs --builder latex
    """
    source_path = Path(source_dir)
    build_path = Path(build_dir)

    # Check if source directory exists
    if not source_path.exists():
        typer.echo(
            f"[ERROR] Source directory not found: {source_path}",
            err=True,
        )
        typer.echo(
            "[INFO] Please ensure Sphinx is initialized in the docs directory.",
            err=True,
        )
        raise typer.Exit(1)

    # Check if conf.py exists in source directory
    conf_py = source_path / "conf.py"
    if not conf_py.exists():
        typer.echo(
            f"[ERROR] Sphinx configuration not found: {conf_py}",
            err=True,
        )
        typer.echo(
            "[INFO] Please run 'sphinx-quickstart' to initialize Sphinx.",
            err=True,
        )
        raise typer.Exit(1)

    # Remove build directory if clean is enabled
    if clean and build_path.exists():
        typer.echo(f"[INFO] Removing build directory: {build_path}")
        try:
            shutil.rmtree(build_path)
            typer.echo("[OK] Build directory removed")
        except Exception as e:
            typer.echo(
                f"[ERROR] Failed to remove build directory: {e}",
                err=True,
            )
            raise typer.Exit(1)

    # Create build directory if it doesn't exist
    build_path.mkdir(parents=True, exist_ok=True)

    # Build documentation using sphinx-build
    typer.echo("[INFO] Building documentation...")
    typer.echo(f"[INFO] Source: {source_path}")
    typer.echo(f"[INFO] Build: {build_path}")
    typer.echo(f"[INFO] Builder: {builder}")

    build_cmd = [
        sys.executable,
        "-m",
        "sphinx",
        "-b",
        builder,
        str(source_path),
        str(build_path),
    ]

    if verbose:
        build_cmd.append("-v")

    try:
        result = subprocess.run(
            build_cmd,
            check=True,
            capture_output=not verbose,
            text=True,
        )

        if result.returncode != 0:
            typer.echo("[ERROR] Documentation build failed", err=True)
            if not verbose and result.stderr:
                typer.echo(result.stderr, err=True)
            raise typer.Exit(1)

        typer.echo("[OK] Documentation built successfully")
        typer.echo(f"[INFO] Output location: {build_path}")

        # Show output location based on builder
        if builder == "html":
            html_index = build_path / "html" / "index.html"
            if html_index.exists():
                typer.echo(f"[INFO] Open in browser: {html_index.absolute()}")

    except subprocess.CalledProcessError as e:
        typer.echo(f"[ERROR] Sphinx build command failed: {e}", err=True)
        if not verbose and e.stderr:
            typer.echo(e.stderr, err=True)
        raise typer.Exit(1)
    except FileNotFoundError:
        typer.echo(
            "[ERROR] Sphinx not found. Please install Sphinx: pip install sphinx",
            err=True,
        )
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"[ERROR] Unexpected error: {e}", err=True)
        if settings.DEBUG:
            import traceback

            typer.echo(traceback.format_exc(), err=True)
        raise typer.Exit(1)
