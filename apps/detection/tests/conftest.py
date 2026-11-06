"""Shared pytest fixtures for densNet tests."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from densnet.constants import CLASS_NAMES
from PIL import Image


def write_png(
    path: Path, size: tuple[int, int] = (32, 32), color: str = "white"
) -> Path:
    """Write a tiny RGB PNG and return ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=color).save(path)
    return path


@pytest.fixture
def class_folders(tmp_path: Path) -> Path:
    """``{class}/image.png`` tree matching ``DentalRadiographyDataset`` layout."""
    colors = {"dentin": "red", "enamel": "green", "pulp": "blue"}
    for name in CLASS_NAMES:
        write_png(tmp_path / name / f"{name}_1.png", color=colors[name])
    (tmp_path / "dentin" / "notes.txt").write_text("not an image", encoding="utf-8")
    return tmp_path


def write_pred_csv(path: Path, pairs: list[tuple[int, int]]) -> Path:
    """Write a minimal prediction CSV with ``target`` / ``pred_idx`` columns."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["target", "pred_idx"])
        writer.writeheader()
        for target, pred_idx in pairs:
            writer.writerow({"target": target, "pred_idx": pred_idx})
    return path
