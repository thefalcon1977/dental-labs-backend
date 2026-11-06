"""Command to build and save Docker images."""

import subprocess
from pathlib import Path

import typer

from apps.core.version import __version__
from config.settings import settings

from . import export_packages


def build_docker(
    tag: str | None = typer.Option(
        None,
        "--tag",
        "-t",
        help="Docker image tag (default: uses version from apps.core.version)",
    ),
    dockerfile: str = typer.Option(
        "Dockerfile",
        "--file",
        "-f",
        help="Path to Dockerfile",
    ),
    no_cache: bool = typer.Option(
        False,
        "--no-cache",
        help="Build without using cache",
    ),
    platform: str | None = typer.Option(
        None,
        "--platform",
        help="Platform to build for (e.g., linux/amd64, linux/arm64)",
    ),
) -> None:
    """Build Docker image and save it to docker-images/ directory.

    Builds a Docker image following best practices:
    - Uses service name from settings (lowercase, hyphenated)
    - Tags with version or custom tag
    - Saves image as tar file to docker-images/ directory (gitignored)
    - Follows Docker naming conventions: service-name:tag

    Examples:
        # Build with version tag
        python manage.py build-docker

        # Build with custom tag
        python manage.py build-docker --tag latest

        # Build for specific platform
        python manage.py build-docker --platform linux/amd64
    """
    # Ensure requirements are exported before building the image
    export_packages.export_packages(target="all")

    # Get service name and normalize it (lowercase, replace underscores with hyphens)
    service_name = settings.SERVICE_NAME.lower().replace("_", "-")

    # Use provided tag or default to version
    image_tag = tag or __version__
    image_name = f"{service_name}:{image_tag}"

    # Create docker-images directory if it doesn't exist
    docker_images_dir = Path("docker-images")
    docker_images_dir.mkdir(exist_ok=True)

    # Build Docker image
    typer.echo(f"[INFO] Building Docker image: {image_name}")
    typer.echo(f"[INFO] Dockerfile: {dockerfile}")

    build_cmd = [
        "docker",
        "build",
        "-t",
        image_name,
        "-f",
        dockerfile,
    ]

    if no_cache:
        build_cmd.append("--no-cache")

    if platform:
        build_cmd.extend(["--platform", platform])

    build_cmd.append(".")

    try:
        result = subprocess.run(
            build_cmd,
            check=True,
            capture_output=False,
            text=True,
        )

        if result.returncode != 0:
            typer.echo("[ERROR] Docker build failed", err=True)
            raise typer.Exit(1)

        typer.echo(f"[OK] Docker image built successfully: {image_name}")

        # Save image to tar file
        # Use sanitized filename (replace : with - for filesystem compatibility)
        filename = image_name.replace(":", "-") + ".tar"
        output_path = docker_images_dir / filename

        typer.echo(f"[INFO] Saving image to: {output_path}")

        save_cmd = ["docker", "save", "-o", str(output_path), image_name]

        save_result = subprocess.run(
            save_cmd,
            check=True,
            capture_output=False,
            text=True,
        )

        if save_result.returncode != 0:
            typer.echo("[ERROR] Failed to save Docker image", err=True)
            raise typer.Exit(1)

        # Get file size for display
        file_size_mb = output_path.stat().st_size / (1024 * 1024)

        typer.echo("[OK] Docker image saved successfully")
        typer.echo(f"[INFO] Image: {image_name}")
        typer.echo(f"[INFO] File: {output_path}")
        typer.echo(f"[INFO] Size: {file_size_mb:.2f} MB")

    except subprocess.CalledProcessError as e:
        typer.echo(f"[ERROR] Docker command failed: {e}", err=True)
        raise typer.Exit(1)
    except FileNotFoundError:
        typer.echo(
            "[ERROR] Docker not found. Please install Docker and ensure it's in your PATH.",
            err=True,
        )
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"[ERROR] Unexpected error: {e}", err=True)
        if settings.DEBUG:
            import traceback

            typer.echo(traceback.format_exc(), err=True)
        raise typer.Exit(1)
