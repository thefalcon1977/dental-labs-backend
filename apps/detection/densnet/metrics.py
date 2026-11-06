"""Evaluation metrics from prediction CSVs."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TypeAlias

from densnet.constants import CLASS_NAMES, PREDICTIONS_DIR

IntList: TypeAlias = list[int]
CountDict: TypeAlias = dict[str, int]
MetricDict: TypeAlias = dict[str, float | int | str]

DEFAULT_INPUT_CSVS: list[str] = [
    str(Path(PREDICTIONS_DIR) / "dentin_test_predictions.csv"),
    str(Path(PREDICTIONS_DIR) / "enamel_test_predictions.csv"),
    str(Path(PREDICTIONS_DIR) / "pulp_test_predictions.csv"),
]


def safe_div(numerator: float, denominator: float) -> float:
    """Divide safely; return 0.0 when denominator is zero."""
    if denominator == 0:
        return 0.0
    return numerator / denominator


def load_predictions(csv_paths: list[str]) -> tuple[IntList, IntList]:
    """Load target and predicted class indices from prediction CSVs."""
    targets: IntList = []
    preds: IntList = []

    for path in csv_paths:
        if not Path(path).is_file():
            raise SystemExit(f"Missing predictions file: {path}")

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                targets.append(int(row["target"]))
                preds.append(int(row["pred_idx"]))

    return targets, preds


def confusion_for_class(
    targets: IntList,
    preds: IntList,
    class_idx: int,
) -> CountDict:
    """Compute one-vs-rest TP/FP/TN/FN for a single class."""
    tp = fp = tn = fn = 0
    for y_true, y_pred in zip(targets, preds, strict=True):
        true_pos = y_true == class_idx
        pred_pos = y_pred == class_idx
        if true_pos and pred_pos:
            tp += 1
        elif (not true_pos) and pred_pos:
            fp += 1
        elif true_pos and (not pred_pos):
            fn += 1
        else:
            tn += 1
    return {"TP": tp, "FP": fp, "TN": tn, "FN": fn}


def metrics_from_counts(counts: CountDict) -> MetricDict:
    """Compute Precision, Recall, Accuracy, F1 from confusion counts."""
    tp, fp, tn, fn = counts["TP"], counts["FP"], counts["TN"], counts["FN"]
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    accuracy = safe_div(tp + tn, tp + tn + fp + fn)
    f1 = safe_div(2 * precision * recall, precision + recall)
    return {
        "TP": tp,
        "FP": fp,
        "TN": tn,
        "FN": fn,
        "precision": precision,
        "recall": recall,
        "accuracy": accuracy,
        "f1": f1,
    }


def overall_accuracy(targets: IntList, preds: IntList) -> float:
    """Multi-class accuracy = correct / total."""
    if not targets:
        return 0.0
    correct = sum(
        1 for y_true, y_pred in zip(targets, preds, strict=True) if y_true == y_pred
    )
    return correct / len(targets)


def confusion_matrix(
    targets: IntList,
    preds: IntList,
    num_classes: int,
) -> list[list[int]]:
    """Build a square confusion matrix [true][pred]."""
    matrix = [[0 for _ in range(num_classes)] for _ in range(num_classes)]
    for y_true, y_pred in zip(targets, preds, strict=True):
        matrix[y_true][y_pred] += 1
    return matrix


def format_pct(value: float) -> str:
    """Format a ratio as a percentage string."""
    return f"{value * 100:.2f}%"


def build_report(
    class_metrics: list[MetricDict],
    macro: MetricDict,
    overall_acc: float,
    matrix: list[list[int]],
    n_samples: int,
) -> str:
    """Build a human-readable evaluation report."""
    lines: list[str] = [
        "=" * 72,
        "DenseNet Tissue Classification — Evaluation Report",
        "=" * 72,
        f"Total samples: {n_samples}",
        f"Overall Accuracy: {format_pct(overall_acc)}",
        "",
        "Formulas:",
        "  Precision = TP / (TP + FP)",
        "  Recall    = TP / (TP + FN)",
        "  Accuracy  = (TP + TN) / (TP + TN + FP + FN)",
        "  F1        = 2 * Precision * Recall / (Precision + Recall)",
        "",
        "-" * 72,
        (
            f"{'Class':<10} {'TP':>4} {'FP':>4} {'TN':>4} {'FN':>4} "
            f"{'Prec':>8} {'Recall':>8} {'Acc':>8} {'F1':>8}"
        ),
        "-" * 72,
    ]

    for m in class_metrics:
        lines.append(
            f"{m['class_name']!s:<10} "
            f"{int(m['TP']):>4} {int(m['FP']):>4} {int(m['TN']):>4} {int(m['FN']):>4} "
            f"{format_pct(float(m['precision'])):>8} "
            f"{format_pct(float(m['recall'])):>8} "
            f"{format_pct(float(m['accuracy'])):>8} "
            f"{format_pct(float(m['f1'])):>8}"
        )

    lines.extend(
        [
            "-" * 72,
            (
                f"{'macro':<10} "
                f"{'':>4} {'':>4} {'':>4} {'':>4} "
                f"{format_pct(float(macro['precision'])):>8} "
                f"{format_pct(float(macro['recall'])):>8} "
                f"{format_pct(float(macro['accuracy'])):>8} "
                f"{format_pct(float(macro['f1'])):>8}"
            ),
            "",
            "Confusion Matrix (rows=true, cols=pred):",
            "true\\pred".ljust(10) + "".join(f"{c:>10}" for c in CLASS_NAMES),
        ]
    )
    for i, row in enumerate(matrix):
        lines.append(CLASS_NAMES[i].ljust(10) + "".join(f"{v:>10}" for v in row))
    lines.append("=" * 72)
    return "\n".join(lines) + "\n"


def run_evaluation(
    csv_paths: list[str] | None = None,
    *,
    metrics_csv: str | Path | None = None,
    report_txt: str | Path | None = None,
) -> str:
    """Evaluate prediction CSVs and write metrics + report.

    Returns:
        Report text.
    """
    paths = csv_paths or DEFAULT_INPUT_CSVS
    metrics_path = Path(metrics_csv or Path(PREDICTIONS_DIR) / "evaluation_metrics.csv")
    report_path = Path(report_txt or Path(PREDICTIONS_DIR) / "evaluation_report.txt")

    targets, preds = load_predictions(paths)
    n_samples = len(targets)
    if n_samples == 0:
        raise SystemExit("No prediction rows found.")

    class_metrics: list[MetricDict] = []
    for idx, name in enumerate(CLASS_NAMES):
        metrics = metrics_from_counts(confusion_for_class(targets, preds, idx))
        metrics["class_name"] = name
        class_metrics.append(metrics)

    macro: MetricDict = {
        "class_name": "macro",
        "TP": "",
        "FP": "",
        "TN": "",
        "FN": "",
        "precision": sum(float(m["precision"]) for m in class_metrics)
        / len(CLASS_NAMES),
        "recall": sum(float(m["recall"]) for m in class_metrics) / len(CLASS_NAMES),
        "accuracy": sum(float(m["accuracy"]) for m in class_metrics) / len(CLASS_NAMES),
        "f1": sum(float(m["f1"]) for m in class_metrics) / len(CLASS_NAMES),
    }

    overall_acc = overall_accuracy(targets, preds)
    matrix = confusion_matrix(targets, preds, len(CLASS_NAMES))

    fieldnames = [
        "class_name",
        "TP",
        "FP",
        "TN",
        "FN",
        "precision",
        "recall",
        "accuracy",
        "f1",
    ]
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    with metrics_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in class_metrics:
            writer.writerow({k: row[k] for k in fieldnames})
        writer.writerow({k: macro[k] for k in fieldnames})
        writer.writerow(
            {
                "class_name": "overall_accuracy",
                "TP": "",
                "FP": "",
                "TN": "",
                "FN": "",
                "precision": "",
                "recall": "",
                "accuracy": overall_acc,
                "f1": "",
            }
        )

    report = build_report(class_metrics, macro, overall_acc, matrix, n_samples)
    report_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote metrics -> {metrics_path}")
    print(f"Wrote report  -> {report_path}")
    return report
