"""Sliding-window tissue detection on full radiographs."""

from __future__ import annotations

from pathlib import Path
from typing import TypeAlias

import torch
from densnet.constants import CLASS_COLORS, CLASS_NAMES, DEFAULT_MODEL_PATH
from densnet.device import get_device
from densnet.model import load_checkpoint
from densnet.transforms import eval_transform
from PIL import Image, ImageDraw, ImageFont

Detection: TypeAlias = tuple[int, int, int, int, str, float]

PATCH_SIZE = 224
STRIDE = 56
CONFIDENCE_THRESHOLD = 0.90
NMS_IOU_THRESHOLD = 0.35

_model_cache: torch.nn.Module | None = None


def get_model(model_path: str | Path = DEFAULT_MODEL_PATH) -> torch.nn.Module:
    """Return a cached eval model, loading on first use."""
    global _model_cache
    if _model_cache is None:
        _model_cache = load_checkpoint(model_path)
    return _model_cache


def _slide_positions(length: int, patch_size: int, stride: int) -> list[int]:
    if length <= patch_size:
        return [0]
    positions = list(range(0, length - patch_size + 1, stride))
    last = length - patch_size
    if positions[-1] != last:
        positions.append(last)
    return positions


def _box_iou(box_a: Detection, box_b: Detection) -> float:
    ax1, ay1, ax2, ay2 = box_a[:4]
    bx1, by1, bx2, by2 = box_b[:4]
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
        return 0.0
    inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter_area / (area_a + area_b - inter_area)


def non_max_suppression(
    detections: list[Detection],
    iou_threshold: float = NMS_IOU_THRESHOLD,
) -> list[Detection]:
    """Keep high-confidence boxes; suppress overlapping duplicates."""
    if not detections:
        return []
    detections = sorted(detections, key=lambda d: d[5], reverse=True)
    kept: list[Detection] = []
    for det in detections:
        if all(_box_iou(det, k) < iou_threshold for k in kept):
            kept.append(det)
    return kept


def _get_font(size: int = 14) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    font_paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in font_paths:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def draw_detections(
    image: Image.Image,
    detections: list[Detection],
) -> Image.Image:
    """Draw colored boxes and labels onto a copy of ``image``."""
    result = image.copy()
    draw = ImageDraw.Draw(result)
    font = _get_font()

    for x1, y1, x2, y2, class_name, conf in detections:
        color = CLASS_COLORS[class_name]
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
        label_text = f"{class_name.upper()} {conf * 100:.0f}%"
        bbox = draw.textbbox((0, 0), label_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        label_y = max(0, y1 - text_height - 4)
        draw.rectangle([x1, label_y, x1 + text_width + 8, y1], fill=color)
        draw.text((x1 + 4, label_y), label_text, fill=(255, 255, 255), font=font)
    return result


def scan_image(
    image: Image.Image,
    *,
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
    model_path: str | Path = DEFAULT_MODEL_PATH,
) -> list[Detection]:
    """Scan an in-memory radiograph with a sliding window.

    Args:
        image: RGB radiograph.
        confidence_threshold: Minimum softmax confidence to keep a patch.
        model_path: Checkpoint path. Relative paths resolve under ``apps/detection``.

    Returns:
        Detections ``(x1, y1, x2, y2, class_name, confidence)`` on the original image.
    """
    device = get_device()
    transform = eval_transform()
    source = image.convert("RGB")
    w, h = source.size

    work_image = source
    scale = 1.0
    if w < PATCH_SIZE or h < PATCH_SIZE:
        scale = max(PATCH_SIZE / w, PATCH_SIZE / h)
        work_image = source.resize((int(w * scale), int(h * scale)), Image.BICUBIC)
        w, h = work_image.size

    detections: list[Detection] = []
    model = get_model(model_path)

    for y in _slide_positions(h, PATCH_SIZE, STRIDE):
        for x in _slide_positions(w, PATCH_SIZE, STRIDE):
            patch = work_image.crop((x, y, x + PATCH_SIZE, y + PATCH_SIZE))
            input_tensor = transform(patch).unsqueeze(0).to(device)
            with torch.no_grad():
                outputs = model(input_tensor)
                probs = torch.nn.functional.softmax(outputs[0], dim=0)
                conf, pred = torch.max(probs, 0)

            if conf.item() >= confidence_threshold:
                class_name = CLASS_NAMES[int(pred.item())]
                if scale != 1.0:
                    x1 = int(x / scale)
                    y1 = int(y / scale)
                    x2 = int((x + PATCH_SIZE) / scale)
                    y2 = int((y + PATCH_SIZE) / scale)
                else:
                    x1, y1, x2, y2 = x, y, x + PATCH_SIZE, y + PATCH_SIZE
                detections.append((x1, y1, x2, y2, class_name, conf.item()))

    return non_max_suppression(detections)


def detect(
    image_path: str | Path,
    *,
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
    model_path: str | Path = DEFAULT_MODEL_PATH,
) -> tuple[Image.Image, list[Detection]]:
    """Scan a radiograph with a sliding window.

    Args:
        image_path: Full radiograph path.
        confidence_threshold: Minimum softmax confidence to keep a patch.
        model_path: Checkpoint path.

    Returns:
        ``(annotated_image, detections)`` where each detection is
        ``(x1, y1, x2, y2, class_name, confidence)``.
    """
    image = Image.open(image_path).convert("RGB")
    w, h = image.size
    print(f"Image size: {w}x{h}")
    print("Scanning image...")
    detections = scan_image(
        image,
        confidence_threshold=confidence_threshold,
        model_path=model_path,
    )
    print(f"Detections: {len(detections)}")

    if not detections:
        print(
            f"❌ No detections found with confidence >= "
            f"{confidence_threshold * 100:.0f}%"
        )
        return image, []

    print(
        f"\n✅ Found {len(detections)} region(s) "
        f"(>= {confidence_threshold * 100:.0f}% confidence):"
    )
    for i, (x1, y1, x2, y2, class_name, conf) in enumerate(detections, 1):
        print(
            f"   [{i}] {class_name.upper():6s}  {conf * 100:5.1f}%  "
            f"box=({x1}, {y1})-({x2}, {y2})"
        )

    return draw_detections(image, detections), detections


def run_detect_cli(image_path: str | Path | None = None) -> None:
    """Load model, run detection, and display the annotated image.

    Args:
        image_path: Radiograph path; prompts on stdin if omitted.
    """
    import matplotlib.pyplot as plt
    from densnet.device import describe_device

    device = get_device()
    print(f"Using device: {describe_device(device)}")
    print("Loading model...")
    get_model()
    print("✅ Model loaded!")

    path = Path(
        str(image_path).strip() if image_path else input("Enter image path: ").strip()
    )
    if not path.is_file():
        raise SystemExit(f"❌ Image not found: {path}")

    result, detections = detect(path)

    plt.figure(figsize=(14, 8))
    plt.imshow(result)
    plt.axis("off")
    if detections:
        summary = ", ".join(f"{d[4]}({d[5] * 100:.0f}%)" for d in detections)
        plt.title(
            f"Detections ({len(detections)}): {summary}",
            fontsize=12,
            fontweight="bold",
        )
    else:
        plt.title("No detections found", fontsize=14)
    plt.tight_layout()
    plt.show()
    print("\n✅ Image displayed!")
