"""Batch prediction CSV rows and folder runner guards."""

from __future__ import annotations

from pathlib import Path

import pytest
import torch
from densnet.constants import CLASS_NAMES
from densnet.predict_batch import build_row, predict_image, run_folder_predictions
from tests.conftest import write_png
from torch import nn


class ConstantLogits(nn.Module):
    def __init__(self, logits: tuple[float, float, float]) -> None:
        super().__init__()
        self.register_buffer("logits", torch.tensor(logits, dtype=torch.float32))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.logits.to(x.device).unsqueeze(0).expand(x.size(0), -1)


def test_build_row_uses_target_class_probability() -> None:
    probs = [0.1, 0.7, 0.2]
    row = build_row("a.png", "pulp", pred_idx=1, probs=probs)
    assert row["class_name"] == "pulp"
    assert row["target"] == 2
    assert row["target_label"] == "pulp"
    assert row["pred_idx"] == 1
    assert row["pred_label"] == "enamel"
    assert row["prob_positive"] == pytest.approx(0.2)


def test_build_row_class_indices_match_class_names() -> None:
    for idx, name in enumerate(CLASS_NAMES):
        row = build_row("x.png", name, pred_idx=idx, probs=[0.9, 0.05, 0.05])
        assert row["target"] == idx
        assert row["pred_label"] == name


def test_predict_image_argmax(tmp_path: Path) -> None:
    path = write_png(tmp_path / "patch.png", size=(64, 64))
    model = ConstantLogits((0.0, 5.0, 0.0))
    pred_idx, probs = predict_image(model, path, device=torch.device("cpu"))
    assert pred_idx == 1
    assert len(probs) == 3
    assert probs[1] == pytest.approx(max(probs))
    assert pytest.approx(sum(probs), rel=1e-5) == 1.0


def test_run_folder_unknown_class() -> None:
    with pytest.raises(ValueError, match="Unknown class"):
        run_folder_predictions("cementum")


def test_run_folder_missing_model(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="Model not found"):
        run_folder_predictions(
            "dentin",
            input_dir=tmp_path,
            output_csv=tmp_path / "out.csv",
            model_path=tmp_path / "missing.pth",
        )


def test_run_folder_missing_input(tmp_path: Path) -> None:
    model = tmp_path / "model.pth"
    model.write_bytes(b"x")
    with pytest.raises(SystemExit, match="Input directory not found"):
        run_folder_predictions(
            "dentin",
            input_dir=tmp_path / "nope",
            output_csv=tmp_path / "out.csv",
            model_path=model,
        )


def test_run_folder_writes_csv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_dir = tmp_path / "dentin_test"
    write_png(input_dir / "a.png")
    write_png(input_dir / "b.png")
    out_csv = tmp_path / "preds.csv"
    fake_model = tmp_path / "model.pth"
    fake_model.write_bytes(b"ckpt")

    monkeypatch.setattr(
        "densnet.predict_batch.load_checkpoint",
        lambda *_args, **_kwargs: ConstantLogits((8.0, 0.0, 0.0)),
    )

    written = run_folder_predictions(
        "dentin",
        input_dir=input_dir,
        output_csv=out_csv,
        model_path=fake_model,
    )
    assert written == out_csv
    text = out_csv.read_text(encoding="utf-8")
    assert (
        "file,class_name,target,target_label,pred_idx,pred_label,prob_positive" in text
    )
    assert "a.png" in text
    assert "b.png" in text
