"""Filesystem helpers for image folders."""

from __future__ import annotations

from pathlib import Path

from densnet.constants import IMAGE_EXTENSIONS


def list_images(input_dir: str | Path) -> list[str]:
    """List image filenames in a directory (sorted, case-insensitive).

    Args:
        input_dir: Directory containing images.

    Returns:
        Sorted list of filenames (not full paths).
    """
    directory = Path(input_dir)
    files: list[str] = []
    for path in directory.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            files.append(path.name)
    return sorted(files, key=str.lower)
