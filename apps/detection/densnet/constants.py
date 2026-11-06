"""Project-wide constants. Class index order must not change."""

from __future__ import annotations

from pathlib import Path

CLASS_NAMES: list[str] = ["dentin", "enamel", "pulp"]  # 0, 1, 2

CLASS_COLORS: dict[str, tuple[int, int, int]] = {
    "dentin": (255, 0, 0),  # red
    "enamel": (0, 255, 0),  # green
    "pulp": (0, 0, 255),  # blue
}

DEFAULT_MODEL_PATH = "slm/resolution_best_densenet_model.pth"


def resolve_model_path(model_path: str | Path = DEFAULT_MODEL_PATH) -> Path:
    """Resolve a checkpoint path against the detection package when needed.

    A path that already exists is returned unchanged. A relative path is then
    resolved next to ``apps/detection``, where ``slm/resolution_best_densenet_model.pth``
    lives, so the API does not depend on the process working directory.

    Args:
        model_path: Absolute path, cwd-relative path, or the packaged default.

    Returns:
        Path to load. May not exist; callers raise if the file is missing.
    """
    path = Path(model_path)
    if path.is_file() or path.is_absolute():
        return path
    return Path(__file__).resolve().parent.parent / path


IMAGE_EXTENSIONS: set[str] = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}

IMAGENET_MEAN: list[float] = [0.485, 0.456, 0.406]
IMAGENET_STD: list[float] = [0.229, 0.224, 0.225]

PREDICTIONS_DIR = "test_predictions"
