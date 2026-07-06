"""Single source of truth for application version.

This module reads the version from pyproject.toml, which is the single source of truth.
All other parts of the application should import __version__ from this module.

Usage:
    from apps.core.version import __version__

    print(f"Application version: {__version__}")
"""

import tomllib
from pathlib import Path


def get_version() -> str:
    """Get application version from pyproject.toml.

    The version is read from [project] section in pyproject.toml.
    This ensures a single source of truth for versioning across the project.

    Returns:
        Application version string (e.g., "0.1.0")

    Raises:
        RuntimeError: If version cannot be determined from pyproject.toml
    """
    # Try to read from pyproject.toml (single source of truth)
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"

    if pyproject_path.exists():
        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                version = data.get("project", {}).get("version")
                if version:
                    return version
        except Exception as e:
            raise RuntimeError(
                f"Failed to read version from pyproject.toml: {e}. "
                "Please ensure pyproject.toml exists and contains [project] version."
            )

    # Fallback: try to get from installed package metadata (for installed packages)
    try:
        from importlib.metadata import PackageNotFoundError, version

        return version("microservices-fastapi-template")
    except (PackageNotFoundError, ImportError):
        # Package not installed or importlib.metadata not available
        # This is expected in some environments, continue to final fallback
        pass

    # Final fallback - should not happen in normal operation
    raise RuntimeError(
        "Could not determine application version. "
        "Please ensure pyproject.toml exists with [project] version field."
    )


# Version constant - single source of truth
# Import this in other modules: from apps.core.version import __version__
__version__ = get_version()

__all__ = ["__version__", "get_version"]
