"""Sliding-window helpers and detection without a real checkpoint."""

from __future__ import annotations

from pathlib import Path

import pytest
import torch
from densnet.detect import (
    _slide_positions,
    detect,
    draw_detections,
    non_max_suppression,
)
from PIL import Image
from tests.conftest import write_png
from torch import nn


class ConstantLogits(nn.Module):
    """Return a fixed logit vector for every batch item."""

    def __init__(self, logits: tuple[float, float, float]) -> None:
        super().__init__()
        self.register_buffer("logits", torch.tensor(logits, dtype=torch.float32))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.logits.to(x.device).unsqueeze(0).expand(x.size(0), -1)


def test_slide_positions_single_patch() -> None:
    assert _slide_positions(224, 224, 56) == [0]


def test_slide_positions_includes_last_window() -> None:
    assert _slide_positions(300, 224, 56) == [0, 56, 76]


def test_nms_keeps_highest_of_overlapping_boxes() -> None:
    high = (0, 0, 100, 100, "dentin", 0.99)
    low = (10, 10, 110, 110, "dentin", 0.91)
    kept = non_max_suppression([low, high], iou_threshold=0.35)
    assert kept == [high]


def test_nms_keeps_non_overlapping_boxes() -> None:
    a = (0, 0, 10, 10, "dentin", 0.9)
    b = (50, 50, 60, 60, "enamel", 0.8)
    kept = non_max_suppression([a, b], iou_threshold=0.35)
    assert kept == [a, b]


def test_nms_empty() -> None:
    assert non_max_suppression([]) == []


def test_draw_detections_preserves_size() -> None:
    image = Image.new("RGB", (80, 60), color="black")
    detections = [(5, 5, 40, 40, "pulp", 0.95)]
    drawn = draw_detections(image, detections)
    assert drawn.size == image.size
    assert drawn is not image


def test_detect_no_hits_below_threshold(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "densnet.detect.get_model",
        lambda *_args, **_kwargs: ConstantLogits((0.0, 0.0, 0.0)),
    )
    path = write_png(tmp_path / "xray.png", size=(224, 224), color="gray")
    _image, detections = detect(path, confidence_threshold=0.90)
    assert detections == []


def test_detect_returns_dentin_box(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "densnet.detect.get_model",
        lambda *_args, **_kwargs: ConstantLogits((20.0, 0.0, 0.0)),
    )
    path = write_png(tmp_path / "xray.png", size=(224, 224), color="gray")
    image, detections = detect(path, confidence_threshold=0.90)
    assert len(detections) == 1
    x1, y1, x2, y2, class_name, conf = detections[0]
    assert (x1, y1, x2, y2) == (0, 0, 224, 224)
    assert class_name == "dentin"
    assert conf > 0.99
    assert image.size == (224, 224)
