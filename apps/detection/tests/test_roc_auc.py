"""One-vs-rest ROC / AUC without a real checkpoint."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import torch
from densnet.constants import CLASS_NAMES
from densnet.roc_auc import (
    AUC_FIELDNAMES,
    PROB_FIELDNAMES,
    build_probability_row,
    collect_multiclass_rows,
    ovr_roc_for_class,
    run_roc_auc,
    scores_matrix,
)
from tests.conftest import write_png
from torch import nn


class ConstantLogits(nn.Module):
    def __init__(self, logits: tuple[float, float, float]) -> None:
        super().__init__()
        self.register_buffer("logits", torch.tensor(logits, dtype=torch.float32))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.logits.to(x.device).unsqueeze(0).expand(x.size(0), -1)


def test_build_probability_row_columns() -> None:
    probs = [0.1, 0.7, 0.2]
    row = build_probability_row("a.png", "pulp", pred_idx=1, probs=probs)
    assert row["true_idx"] == 2
    assert row["true_class"] == "pulp"
    assert row["pred_idx"] == 1
    assert row["pred_label"] == "enamel"
    assert row["prob_dentin"] == pytest.approx(0.1)
    assert row["prob_enamel"] == pytest.approx(0.7)
    assert row["prob_pulp"] == pytest.approx(0.2)
    assert row["probability_sum"] == pytest.approx(1.0)
    assert list(row) == PROB_FIELDNAMES


def test_build_probability_row_unknown_class() -> None:
    with pytest.raises(ValueError, match="Unknown class"):
        build_probability_row("a.png", "cementum", 0, [0.3, 0.3, 0.4])


def test_ovr_auc_perfect_separator() -> None:
    true_indices = np.array([0, 0, 1, 1, 2, 2])
    scores = np.array(
        [
            [0.9, 0.05, 0.05],
            [0.8, 0.1, 0.1],
            [0.05, 0.9, 0.05],
            [0.1, 0.85, 0.05],
            [0.05, 0.05, 0.9],
            [0.1, 0.1, 0.8],
        ]
    )
    for class_idx in range(3):
        _fpr, _tpr, _thr, curve_auc, sklearn_auc = ovr_roc_for_class(
            true_indices, scores, class_idx
        )
        assert curve_auc == pytest.approx(1.0)
        assert sklearn_auc == pytest.approx(1.0)


def test_ovr_auc_constant_scores_are_chance() -> None:
    true_indices = np.array([0, 0, 1, 1])
    scores = np.array(
        [
            [0.5, 0.5, 0.0],
            [0.5, 0.5, 0.0],
            [0.5, 0.5, 0.0],
            [0.5, 0.5, 0.0],
        ]
    )
    _fpr, _tpr, _thr, curve_auc, sklearn_auc = ovr_roc_for_class(
        true_indices, scores, 0
    )
    assert curve_auc == pytest.approx(0.5)
    assert sklearn_auc == pytest.approx(0.5)


def test_ovr_roc_requires_both_classes() -> None:
    true_indices = np.array([0, 0])
    scores = np.array([[0.9, 0.1, 0.0], [0.8, 0.1, 0.1]])
    with pytest.raises(ValueError, match="positives and negatives"):
        ovr_roc_for_class(true_indices, scores, 0)


def test_scores_matrix_shape() -> None:
    rows = [
        build_probability_row("a.png", "dentin", 0, [0.8, 0.1, 0.1]),
        build_probability_row("b.png", "enamel", 1, [0.1, 0.8, 0.1]),
    ]
    true_indices, scores = scores_matrix(rows)
    assert true_indices.tolist() == [0, 1]
    assert scores.shape == (2, 3)


def test_collect_missing_model(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="Model not found"):
        collect_multiclass_rows(tmp_path, model_path=tmp_path / "missing.pth")


def test_collect_missing_class_folder(tmp_path: Path) -> None:
    model = tmp_path / "model.pth"
    model.write_bytes(b"ckpt")
    with pytest.raises(SystemExit, match="Test folder not found"):
        collect_multiclass_rows(tmp_path, model_path=model)


def test_run_roc_auc_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root = tmp_path / "image-testing"
    for name, color in zip(CLASS_NAMES, ["red", "green", "blue"], strict=True):
        write_png(data_root / f"{name}_test" / f"{name}.png", color=color)

    fake_model = tmp_path / "model.pth"
    fake_model.write_bytes(b"ckpt")
    out_dir = tmp_path / "roc_out"

    monkeypatch.setattr(
        "densnet.roc_auc.load_checkpoint",
        lambda *_args, **_kwargs: ConstantLogits((8.0, 0.0, 0.0)),
    )

    written = run_roc_auc(
        data_root=data_root,
        output_dir=out_dir,
        model_path=fake_model,
    )
    assert written == out_dir
    assert (out_dir / "multiclass_probabilities.csv").is_file()
    assert (out_dir / "one_vs_rest_auc_results.csv").is_file()
    assert (out_dir / "roc_auc_summary.csv").is_file()
    assert (out_dir / "one_vs_rest_roc_curves.png").is_file()
    for name in CLASS_NAMES:
        assert (out_dir / f"roc_curve_{name}.csv").is_file()

    header = (out_dir / "multiclass_probabilities.csv").read_text(encoding="utf-8")
    assert ",".join(PROB_FIELDNAMES) in header
    auc_header = (out_dir / "one_vs_rest_auc_results.csv").read_text(encoding="utf-8")
    assert ",".join(AUC_FIELDNAMES) in auc_header
