"""One-vs-rest ROC curves and AUC for the 3-class classifier."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TypeAlias

import numpy as np
from densnet.constants import CLASS_NAMES, DEFAULT_MODEL_PATH, PREDICTIONS_DIR
from densnet.device import describe_device, get_device
from densnet.images import list_images
from densnet.model import load_checkpoint
from densnet.predict_batch import predict_image
from sklearn.metrics import auc, roc_auc_score, roc_curve

ProbList: TypeAlias = list[float]
ProbRow: TypeAlias = dict[str, str | int | float]
AucRow: TypeAlias = dict[str, str | int | float]

PROB_FIELDNAMES = [
    "file",
    "true_idx",
    "true_class",
    "pred_idx",
    "pred_label",
    *[f"prob_{name}" for name in CLASS_NAMES],
    "probability_sum",
]
"""CSV columns for :file:`multiclass_probabilities.csv`."""

AUC_FIELDNAMES = [
    "class",
    "comparison",
    "n_positive",
    "n_negative",
    "auc",
    "auc_sklearn_check",
]
"""CSV columns for :file:`one_vs_rest_auc_results.csv`."""


def build_probability_row(
    relative_path: str,
    true_class: str,
    pred_idx: int,
    probs: ProbList,
) -> ProbRow:
    """Build one multiclass-probability CSV row.

    Args:
        relative_path: Image path written to the CSV.
        true_class: Ground-truth class name.
        pred_idx: Argmax class index.
        probs: Softmax probabilities in ``CLASS_NAMES`` order.

    Returns:
        Row with per-class probabilities and their sum.

    Raises:
        ValueError: If ``true_class`` is unknown or ``probs`` length mismatches.
    """
    if true_class not in CLASS_NAMES:
        raise ValueError(f"Unknown class: {true_class}")
    if len(probs) != len(CLASS_NAMES):
        raise ValueError(f"Expected {len(CLASS_NAMES)} probabilities, got {len(probs)}")

    true_idx = CLASS_NAMES.index(true_class)
    row: ProbRow = {
        "file": relative_path,
        "true_idx": true_idx,
        "true_class": true_class,
        "pred_idx": pred_idx,
        "pred_label": CLASS_NAMES[pred_idx],
    }
    for name, prob in zip(CLASS_NAMES, probs, strict=True):
        row[f"prob_{name}"] = float(prob)
    row["probability_sum"] = float(sum(probs))
    return row


def scores_matrix(rows: list[ProbRow]) -> tuple[np.ndarray, np.ndarray]:
    """Stack true indices and class scores from probability rows.

    Args:
        rows: Output of :func:`build_probability_row`.

    Returns:
        ``(true_indices, scores)`` where ``scores`` has shape ``(n, 3)``.
    """
    true_indices = np.array([int(row["true_idx"]) for row in rows], dtype=int)
    scores = np.array(
        [[float(row[f"prob_{name}"]) for name in CLASS_NAMES] for row in rows],
        dtype=float,
    )
    return true_indices, scores


def ovr_roc_for_class(
    true_indices: np.ndarray,
    scores: np.ndarray,
    class_idx: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
    """One-vs-rest ROC curve and AUC for a single class.

    Args:
        true_indices: Integer labels in ``0 .. n_classes-1``.
        scores: Softmax matrix with shape ``(n_samples, n_classes)``.
        class_idx: Column / class to treat as the positive class.

    Returns:
        ``(fpr, tpr, thresholds, auc_from_curve, sklearn_auc)``.

    Raises:
        ValueError: If the class has no positives or no negatives.
    """
    y_true = (true_indices == class_idx).astype(int)
    y_score = scores[:, class_idx]
    n_positive = int(y_true.sum())
    n_negative = int(len(y_true) - n_positive)
    if n_positive == 0 or n_negative == 0:
        name = (
            CLASS_NAMES[class_idx] if class_idx < len(CLASS_NAMES) else str(class_idx)
        )
        raise ValueError(
            f"Need both positives and negatives for {name} ROC "
            f"(n_positive={n_positive}, n_negative={n_negative})"
        )

    fpr, tpr, thresholds = roc_curve(y_true, y_score)
    curve_auc = float(auc(fpr, tpr))
    sklearn_auc = float(roc_auc_score(y_true, y_score))
    return fpr, tpr, thresholds, curve_auc, sklearn_auc


def collect_multiclass_rows(
    data_root: str | Path,
    *,
    model_path: str | Path = DEFAULT_MODEL_PATH,
) -> list[ProbRow]:
    """Classify every image under ``{class}_test`` folders.

    Args:
        data_root: Parent of ``dentin_test`` / ``enamel_test`` / ``pulp_test``.
        model_path: Checkpoint path.

    Returns:
        One row per image.

    Raises:
        SystemExit: On missing model, folder, or empty result set.
    """
    root = Path(data_root)
    if not Path(model_path).is_file():
        raise SystemExit(f"Model not found: {model_path}")

    class_dirs = [root / f"{name}_test" for name in CLASS_NAMES]
    for image_dir in class_dirs:
        if not image_dir.is_dir():
            raise SystemExit(f"Test folder not found: {image_dir}")

    device = get_device()
    print(f"Using device: {describe_device(device)}")
    print(f"Loading model from {model_path}...")
    model = load_checkpoint(model_path, device=device)
    print("Model loaded.")

    rows: list[ProbRow] = []
    for class_name, image_dir in zip(CLASS_NAMES, class_dirs, strict=True):
        image_names = list_images(image_dir)
        print(f"Found {len(image_names)} images in {image_dir}")
        for name in image_names:
            image_file = image_dir / name
            relative = str(image_file).replace("\\", "/")
            pred_idx, probs = predict_image(model, image_file, device=device)
            rows.append(build_probability_row(relative, class_name, pred_idx, probs))

    if not rows:
        raise SystemExit(f"No images found under {root}")
    return rows


def _write_csv(path: Path, fieldnames: list[str], rows: list[ProbRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_roc_curve_csv(
    path: Path,
    fpr: np.ndarray,
    tpr: np.ndarray,
    thresholds: np.ndarray,
) -> None:
    rows: list[ProbRow] = [
        {
            "false_positive_rate": float(fp),
            "true_positive_rate": float(tp),
            "threshold": float(thr),
        }
        for fp, tp, thr in zip(fpr, tpr, thresholds, strict=True)
    ]
    _write_csv(
        path,
        ["false_positive_rate", "true_positive_rate", "threshold"],
        rows,
    )


def _save_roc_plot(
    path: Path,
    curves: list[tuple[str, np.ndarray, np.ndarray, float]],
) -> None:
    import matplotlib.pyplot as plt

    plt.figure(figsize=(7, 6))
    for class_name, fpr, tpr, class_auc in curves:
        plt.plot(fpr, tpr, lw=2, label=f"{class_name} (AUC = {class_auc:.3f})")
    plt.plot([0, 1], [0, 1], "k--", lw=1, label="Chance")
    plt.xlim([0, 1])
    plt.ylim([0, 1.05])
    plt.xlabel("False positive rate (1 - specificity)")
    plt.ylabel("True positive rate (sensitivity)")
    plt.title("One-vs-rest ROC curves")
    plt.legend(loc="lower right")
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=300)
    plt.close()


def run_roc_auc(
    *,
    data_root: str | Path = "image-testing",
    output_dir: str | Path | None = None,
    model_path: str | Path = DEFAULT_MODEL_PATH,
) -> Path:
    """Score test folders, write OvR ROC/AUC tables, and save a plot.

    Args:
        data_root: Parent of ``{class}_test`` folders.
        output_dir: Defaults to :data:`PREDICTIONS_DIR`.
        model_path: Checkpoint path.

    Returns:
        Directory where CSV and PNG outputs were written.
    """
    out_dir = Path(output_dir or PREDICTIONS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = collect_multiclass_rows(data_root, model_path=model_path)
    _write_csv(out_dir / "multiclass_probabilities.csv", PROB_FIELDNAMES, rows)

    true_indices, scores = scores_matrix(rows)
    auc_rows: list[AucRow] = []
    plot_curves: list[tuple[str, np.ndarray, np.ndarray, float]] = []

    for class_idx, class_name in enumerate(CLASS_NAMES):
        fpr, tpr, thresholds, curve_auc, sklearn_auc = ovr_roc_for_class(
            true_indices, scores, class_idx
        )
        _write_roc_curve_csv(
            out_dir / f"roc_curve_{class_name}.csv", fpr, tpr, thresholds
        )
        y_true = (true_indices == class_idx).astype(int)
        auc_rows.append(
            {
                "class": class_name,
                "comparison": f"{class_name} vs rest",
                "n_positive": int(y_true.sum()),
                "n_negative": int(len(y_true) - y_true.sum()),
                "auc": curve_auc,
                "auc_sklearn_check": sklearn_auc,
            }
        )
        plot_curves.append((class_name, fpr, tpr, curve_auc))
        print(f"{class_name:8s} vs rest  AUC={curve_auc:.4f}")

    _write_csv(out_dir / "one_vs_rest_auc_results.csv", AUC_FIELDNAMES, auc_rows)

    macro_auc = float(
        roc_auc_score(true_indices, scores, multi_class="ovr", average="macro")
    )
    weighted_auc = float(
        roc_auc_score(true_indices, scores, multi_class="ovr", average="weighted")
    )
    sums = [float(row["probability_sum"]) for row in rows]
    summary: list[ProbRow] = [
        {
            "n_images": len(rows),
            "model_class_order": "; ".join(CLASS_NAMES),
            "macro_auc_ovr": macro_auc,
            "weighted_auc_ovr": weighted_auc,
            "minimum_probability_sum": min(sums),
            "maximum_probability_sum": max(sums),
        }
    ]
    _write_csv(
        out_dir / "roc_auc_summary.csv",
        [
            "n_images",
            "model_class_order",
            "macro_auc_ovr",
            "weighted_auc_ovr",
            "minimum_probability_sum",
            "maximum_probability_sum",
        ],
        summary,
    )

    plot_path = out_dir / "one_vs_rest_roc_curves.png"
    _save_roc_plot(plot_path, plot_curves)

    print(
        f"\nWrote {len(rows)} probability rows -> {out_dir / 'multiclass_probabilities.csv'}"
    )
    print(f"Macro AUC (OvR): {macro_auc:.4f}")
    print(f"Weighted AUC (OvR): {weighted_auc:.4f}")
    print(f"ROC plot -> {plot_path}")
    return out_dir
