"""Validate uploaded image bytes."""

_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)


def detect_image_type(data: bytes) -> str:
    """Return the media type for JPEG, PNG, GIF, or WEBP bytes.

    Args:
        data: Raw file contents.

    Returns:
        Detected image media type.

    Raises:
        ValueError: If the bytes are not a supported image.
    """
    for signature, content_type in _SIGNATURES:
        if data.startswith(signature):
            return content_type
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    raise ValueError("Unsupported image type")
