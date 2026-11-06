"""DenseNet121 create / load."""

from __future__ import annotations

from pathlib import Path

import pytest
import torch
from densnet.constants import CLASS_NAMES
from densnet.model import create_densenet121, load_checkpoint


@pytest.fixture(scope="module")
def densenet() -> torch.nn.Module:
    return create_densenet121(pretrained=False)


def test_classifier_head_matches_class_count(densenet: torch.nn.Module) -> None:
    assert densenet.classifier.out_features == len(CLASS_NAMES)


def test_forward_pass_shape(densenet: torch.nn.Module) -> None:
    densenet.eval()
    with torch.no_grad():
        logits = densenet(torch.zeros(1, 3, 224, 224))
    assert tuple(logits.shape) == (1, 3)


def test_load_checkpoint_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Model not found"):
        load_checkpoint(tmp_path / "missing.pth", device=torch.device("cpu"))


def test_load_checkpoint_raw_state_dict(
    tmp_path: Path, densenet: torch.nn.Module
) -> None:
    path = tmp_path / "raw.pth"
    torch.save(densenet.state_dict(), path)
    loaded = load_checkpoint(path, device=torch.device("cpu"))
    assert loaded.training is False
    assert next(loaded.parameters()).device.type == "cpu"


def test_load_checkpoint_wrapped_state_dict(
    tmp_path: Path, densenet: torch.nn.Module
) -> None:
    path = tmp_path / "wrapped.pth"
    torch.save({"model_state_dict": densenet.state_dict()}, path)
    loaded = load_checkpoint(path, device=torch.device("cpu"))
    assert loaded.classifier.out_features == 3
