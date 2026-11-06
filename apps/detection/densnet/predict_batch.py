"""Batch prediction for image-testing folders → CSV."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TypeAlias

import torch
import torch.nn as nn
from densnet.constants import CLASS_NAMES, DEFAULT_MODEL_PATH, PREDICTIONS_DIR
from densnet.device import describe_device, get_device
from densnet.images import list_images
from densnet.model import load_checkpoint
from densnet.transforms import eval_transform
from PIL import Image

ProbList: TypeAlias = list[float]
RowDict: TypeAlias = dict[str, str | int | float]

CSV_FIELDNAMES = [
    "file",
    "class_name",
    "target",
    "target_label",
    "pred_idx",
    "pred_label",
    "prob_positive",
]


def predict_image(
    model: nn.Module,
    image_path: str | Path,
    *,
    device: torch.device | None = None,
) -> tuple[int, ProbList]:
    """Classify one image.

    Args:
        model: DenseNet in eval mode.
        image_path: Path to RGB image.
        device: Inference device.

    Returns:
        ``(pred_idx, softmax probabilities)``.
    """
    device = device or get_device()
    transform = eval_transform()
    image = Image.open(image_path).convert("RGB")
    input_tensor = transform(image).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(input_tensor)
        probs = torch.nn.functional.softmax(outputs[0], dim=0)

    pred_idx = int(torch.argmax(probs).item())
    return pred_idx, [float(p) for p in probs.cpu().tolist()]


def build_row(
    relative_path: str,
    target_class: str,
    pred_idx: int,
    probs: ProbList,
) -> RowDict:
    """Build one prediction CSV row."""
    target_idx = CLASS_NAMES.index(target_class)
    return {
        "file": relative_path,
        "class_name": target_class,
        "target": target_idx,
        "target_label": target_class,
        "pred_idx": pred_idx,
        "pred_label": CLASS_NAMES[pred_idx],
        "prob_positive": probs[target_idx],
    }


def run_folder_predictions(
    target_class: str,
    *,
    input_dir: str | Path | None = None,
    output_csv: str | Path | None = None,
    model_path: str | Path = DEFAULT_MODEL_PATH,
) -> Path:
    """Classify all images in a tissue test folder and write CSV.

    Args:
        target_class: Ground-truth class (``dentin`` / ``enamel`` / ``pulp``).
        input_dir: Defaults to ``image-testing/{target_class}_test``.
        output_csv: Defaults to ``test_predictions/{target_class}_test_predictions.csv``.
        model_path: Checkpoint path.

    Returns:
        Path to the written CSV.

    Raises:
        SystemExit: On missing model, folder, or empty folder.
        ValueError: If ``target_class`` is not in :data:`CLASS_NAMES`.
    """
    if target_class not in CLASS_NAMES:
        raise ValueError(f"Unknown class: {target_class}")

    target_idx = CLASS_NAMES.index(target_class)
    input_path = Path(input_dir or f"image-testing/{target_class}_test")
    out_path = Path(
        output_csv or Path(PREDICTIONS_DIR) / f"{target_class}_test_predictions.csv"
    )

    device = get_device()
    print(f"Using device: {describe_device(device)}")

    if not Path(model_path).is_file():
        raise SystemExit(f"Model not found: {model_path}")
    if not input_path.is_dir():
        raise SystemExit(f"Input directory not found: {input_path}")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Loading model from {model_path}...")
    model = load_checkpoint(model_path, device=device)
    print("Model loaded.")

    image_names = list_images(input_path)
    if not image_names:
        raise SystemExit(f"No images found in {input_path}")

    print(f"Found {len(image_names)} images in {input_path}")
    rows: list[RowDict] = []
    correct = 0

    for name in image_names:
        image_file = input_path / name
        relative = str(image_file).replace("\\", "/")
        pred_idx, probs = predict_image(model, image_file, device=device)
        rows.append(build_row(relative, target_class, pred_idx, probs))

        is_correct = pred_idx == target_idx
        correct += int(is_correct)
        mark = "OK" if is_correct else "MISS"
        print(
            f"[{mark}] {name:20s}  "
            f"pred={CLASS_NAMES[pred_idx]:6s}  "
            f"P({target_class})={probs[target_idx]:.4f}"
        )

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    accuracy = 100.0 * correct / len(rows)
    print(f"\nWrote {len(rows)} rows -> {out_path}")
    print(f"Accuracy on {input_path.name}: {correct}/{len(rows)} ({accuracy:.1f}%)")
    print(
        f"Note: prob_positive = P({target_class}) for this 3-class model "
        "(dentin / enamel / pulp)."
    )
    return out_path
