"""DenseNet121 create / load helpers."""

from __future__ import annotations

from pathlib import Path

import torch
import torch.nn as nn
from densnet.constants import CLASS_NAMES, DEFAULT_MODEL_PATH, resolve_model_path
from densnet.device import get_device
from torchvision import models


def create_densenet121(
    num_classes: int | None = None,
    *,
    pretrained: bool = False,
) -> nn.Module:
    """Build DenseNet121 with a 3-class (or custom) classifier head.

    Args:
        num_classes: Output classes; defaults to ``len(CLASS_NAMES)``.
        pretrained: If True, load ImageNet weights before replacing the head.

    Returns:
        DenseNet121 module (not moved to device).
    """
    if num_classes is None:
        num_classes = len(CLASS_NAMES)

    weights = models.DenseNet121_Weights.IMAGENET1K_V1 if pretrained else None
    model = models.densenet121(weights=weights)
    model.classifier = nn.Linear(model.classifier.in_features, num_classes)
    return model


def load_checkpoint(
    model_path: str | Path = DEFAULT_MODEL_PATH,
    *,
    device: torch.device | None = None,
    pretrained_backbone: bool = False,
) -> nn.Module:
    """Load a DenseNet121 checkpoint into eval mode on ``device``.

    Supports raw ``state_dict`` or ``{"model_state_dict": ...}`` wrappers.

    Args:
        model_path: Path to ``.pth`` checkpoint.
        device: Target device; defaults to :func:`get_device`.
        pretrained_backbone: Ignored for weight init when loading a checkpoint;
            kept for API symmetry with :func:`create_densenet121`.

    Returns:
        Model in eval mode on the selected device.

    Raises:
        FileNotFoundError: If ``model_path`` does not exist.
    """
    del pretrained_backbone  # checkpoint weights replace any backbone init
    path = resolve_model_path(model_path)
    if not path.is_file():
        raise FileNotFoundError(f"Model not found: {path}")

    device = device or get_device()
    model = create_densenet121(pretrained=False)
    checkpoint = torch.load(path, map_location=device, weights_only=False)
    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        model.load_state_dict(checkpoint["model_state_dict"])
    else:
        model.load_state_dict(checkpoint)

    model = model.to(device)
    model.eval()
    return model
