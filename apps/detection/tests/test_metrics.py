"""Precision / Recall / Accuracy / F1 from prediction CSVs."""

from __future__ import annotations

from pathlib import Path

import pytest
from densnet.metrics import (
    confusion_for_class,
    confusion_matrix,
    format_pct,
    load_predictions,
    metrics_from_counts,
    overall_accuracy,
    run_evaluation,
    safe_div,
)
from tests.conftest import write_pred_csv

# targets: dentin, dentin, enamel, enamel, pulp, pulp
# preds:   dentin, enamel, enamel, enamel, pulp, dentin
TARGETS = [0, 0, 1, 1, 2, 2]
PREDS = [0, 1, 1, 1, 2, 0]


def test_safe_div_zero_denominator() -> None:
    assert safe_div(1.0, 0.0) == 0.0
    assert safe_div(0.0, 0.0) == 0.0
    assert safe_div(3.0, 2.0) == 1.5


def test_confusion_for_class_one_vs_rest() -> None:
    dentin = confusion_for_class(TARGETS, PREDS, 0)
    assert dentin == {"TP": 1, "FP": 1, "FN": 1, "TN": 3}

    enamel = confusion_for_class(TARGETS, PREDS, 1)
    assert enamel == {"TP": 2, "FP": 1, "FN": 0, "TN": 3}

    pulp = confusion_for_class(TARGETS, PREDS, 2)
    assert pulp == {"TP": 1, "FP": 0, "FN": 1, "TN": 4}


def test_metrics_from_counts_formulas() -> None:
    metrics = metrics_from_counts({"TP": 1, "FP": 1, "TN": 3, "FN": 1})
    assert metrics["precision"] == pytest.approx(0.5)
    assert metrics["recall"] == pytest.approx(0.5)
    assert metrics["accuracy"] == pytest.approx(4 / 6)
    assert metrics["f1"] == pytest.approx(0.5)


def test_metrics_all_zero_counts() -> None:
    metrics = metrics_from_counts({"TP": 0, "FP": 0, "TN": 0, "FN": 0})
    assert metrics["precision"] == 0.0
    assert metrics["recall"] == 0.0
    assert metrics["accuracy"] == 0.0
    assert metrics["f1"] == 0.0


def test_overall_accuracy() -> None:
    assert overall_accuracy([], []) == 0.0
    assert overall_accuracy(TARGETS, PREDS) == pytest.approx(4 / 6)


def test_confusion_matrix_shape_and_counts() -> None:
    matrix = confusion_matrix(TARGETS, PREDS, 3)
    assert matrix == [
        [1, 1, 0],
        [0, 2, 0],
        [1, 0, 1],
    ]


def test_format_pct() -> None:
    assert format_pct(0.9244) == "92.44%"


def test_load_predictions_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "nope.csv"
    with pytest.raises(SystemExit, match="Missing predictions file"):
        load_predictions([str(missing)])


def test_load_predictions_reads_rows(tmp_path: Path) -> None:
    path = write_pred_csv(tmp_path / "preds.csv", [(0, 1), (2, 2)])
    targets, preds = load_predictions([str(path)])
    assert targets == [0, 2]
    assert preds == [1, 2]


def test_run_evaluation_writes_outputs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    csv_path = write_pred_csv(
        tmp_path / "preds.csv",
        list(zip(TARGETS, PREDS, strict=True)),
    )
    metrics_csv = tmp_path / "metrics.csv"
    report_txt = tmp_path / "report.txt"

    report = run_evaluation(
        [str(csv_path)],
        metrics_csv=metrics_csv,
        report_txt=report_txt,
    )

    assert "Overall Accuracy: 66.67%" in report
    assert "dentin" in report
    assert "enamel" in report
    assert "pulp" in report
    assert metrics_csv.is_file()
    assert report_txt.read_text(encoding="utf-8") == report
    captured = capsys.readouterr()
    assert "Wrote metrics" in captured.out


def test_run_evaluation_empty_csv(tmp_path: Path) -> None:
    path = write_pred_csv(tmp_path / "empty.csv", [])
    with pytest.raises(SystemExit, match="No prediction rows"):
        run_evaluation(
            [str(path)],
            metrics_csv=tmp_path / "m.csv",
            report_txt=tmp_path / "r.txt",
        )
