"""Detection-specific exceptions."""

from typing import Any

from fastapi import status

from apps.core.exceptions import BaseAPIException


class DetectionError(BaseAPIException):
    """Base exception for image detection errors."""


class UnsupportedImageError(DetectionError):
    """The upload is empty or not a supported image."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details or {},
        )


class ImageTooLargeError(DetectionError):
    """The upload exceeds the configured size limit."""

    def __init__(self, size_bytes: int, max_bytes: int) -> None:
        super().__init__(
            message="Image exceeds the maximum upload size",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            details={"size_bytes": size_bytes, "max_bytes": max_bytes},
        )


class ModelNotFoundError(DetectionError):
    """The DenseNet checkpoint is not on disk."""

    def __init__(self, model_path: str) -> None:
        super().__init__(
            message=f"Detection model not found: {model_path}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"model_path": model_path},
        )
