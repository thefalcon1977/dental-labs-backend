"""Run an uploaded image through the local DenseNet checkpoint."""

import asyncio
from io import BytesIO

from densnet.constants import DEFAULT_MODEL_PATH, resolve_model_path
from densnet.detect import CONFIDENCE_THRESHOLD, scan_image
from PIL import Image, UnidentifiedImageError

from config.settings import settings

from ..helpers.exceptions import (
    ImageTooLargeError,
    ModelNotFoundError,
    UnsupportedImageError,
)
from ..schemas import DetectionResponse, RegionDetection
from ..utils.images import detect_image_type


async def analyze_image(
    *,
    filename: str,
    data: bytes,
) -> DetectionResponse:
    """Validate an uploaded image and detect dentin, enamel, and pulp.

    Args:
        filename: Original upload name.
        data: Raw image bytes.

    Returns:
        Detection boxes from ``resolution_best_densenet_model.pth``.

    Raises:
        UnsupportedImageError: If the file is empty or not a supported image.
        ImageTooLargeError: If the file exceeds the configured limit.
        ModelNotFoundError: If the checkpoint file is missing.
    """
    if not data:
        raise UnsupportedImageError("Image file is empty")

    max_bytes = int(settings.detection.MAX_IMAGE_SIZE_MB) * 1024 * 1024
    if len(data) > max_bytes:
        raise ImageTooLargeError(size_bytes=len(data), max_bytes=max_bytes)

    try:
        content_type = detect_image_type(data)
        image = Image.open(BytesIO(data)).convert("RGB")
    except (ValueError, UnidentifiedImageError) as exc:
        raise UnsupportedImageError(
            "Image must be JPEG, PNG, GIF, or WEBP",
            details={"filename": filename},
        ) from exc

    model_path = resolve_model_path(DEFAULT_MODEL_PATH)
    if not model_path.is_file():
        raise ModelNotFoundError(str(model_path))

    threshold = float(
        getattr(settings.detection, "CONFIDENCE_THRESHOLD", CONFIDENCE_THRESHOLD)
    )
    detections = await asyncio.to_thread(
        scan_image,
        image,
        confidence_threshold=threshold,
        model_path=model_path,
    )
    return DetectionResponse(
        model=model_path.name,
        filename=filename or "image",
        content_type=content_type,
        detections=[
            RegionDetection(
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                class_name=class_name,
                confidence=round(confidence, 4),
            )
            for x1, y1, x2, y2, class_name, confidence in detections
        ],
    )
