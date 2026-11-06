"""Class-order and path contracts."""

from __future__ import annotations

from densnet import CLASS_COLORS, CLASS_NAMES, DEFAULT_MODEL_PATH
from densnet.constants import IMAGE_EXTENSIONS


def test_class_index_order() -> None:
    assert CLASS_NAMES == ["dentin", "enamel", "pulp"]
    assert list(CLASS_NAMES).index("dentin") == 0
    assert list(CLASS_NAMES).index("enamel") == 1
    assert list(CLASS_NAMES).index("pulp") == 2


def test_class_colors_match_class_names() -> None:
    assert set(CLASS_COLORS) == set(CLASS_NAMES)
    assert CLASS_COLORS["dentin"] == (255, 0, 0)
    assert CLASS_COLORS["enamel"] == (0, 255, 0)
    assert CLASS_COLORS["pulp"] == (0, 0, 255)


def test_default_checkpoint_path() -> None:
    assert DEFAULT_MODEL_PATH == "slm/resolution_best_densenet_model.pth"


def test_image_extensions_include_common_formats() -> None:
    assert {".png", ".jpg", ".jpeg"} <= IMAGE_EXTENSIONS
