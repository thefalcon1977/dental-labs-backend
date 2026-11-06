"""Image-folder listing."""

from __future__ import annotations

from pathlib import Path

from densnet.images import list_images
from PIL import Image


def test_list_images_filters_and_sorts_case_insensitive(tmp_path: Path) -> None:
    Image.new("RGB", (8, 8)).save(tmp_path / "b.PNG")
    Image.new("RGB", (8, 8)).save(tmp_path / "A.jpg")
    (tmp_path / "readme.txt").write_text("skip", encoding="utf-8")
    (tmp_path / "nested").mkdir()
    Image.new("RGB", (8, 8)).save(tmp_path / "nested" / "hidden.png")

    assert list_images(tmp_path) == ["A.jpg", "b.PNG"]


def test_list_images_empty_directory(tmp_path: Path) -> None:
    assert list_images(tmp_path) == []
