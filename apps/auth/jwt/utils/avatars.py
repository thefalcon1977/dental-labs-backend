"""Store and resolve local profile photos."""

from __future__ import annotations

import re
import time
from pathlib import Path

from apps.core.exceptions import NotFoundError, ValidationError

AVATAR_MAX_BYTES = 2 * 1024 * 1024
_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}
_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)
_USER_ID = re.compile(r"^[A-Za-z0-9-]{1,64}$")
_FILENAME = re.compile(r"^[A-Za-z0-9-]{1,64}\.(?:jpg|png|gif|webp)$")


def avatar_directory() -> Path:
    """Return the directory that holds profile photos, creating it if needed.

    Returns:
        Absolute directory path.
    """
    path = Path(__file__).resolve().parents[4] / "var" / "avatars"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _image_type(data: bytes) -> str:
    for signature, content_type in _SIGNATURES:
        if data.startswith(signature):
            return content_type
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    raise ValidationError("Image must be JPEG, PNG, GIF, or WEBP")


def save_avatar(user_id: str, data: bytes) -> str:
    """Write a profile photo and return its public path.

    Args:
        user_id: Owning user identifier.
        data: Raw image bytes.

    Returns:
        Path beginning with ``/auth/avatars/``, including a cache-busting query.

    Raises:
        ValidationError: If the user id or image is not acceptable.
    """
    if not data:
        raise ValidationError("Image file is empty")
    if not _USER_ID.fullmatch(user_id):
        raise ValidationError("User id cannot be used as an avatar name")
    if len(data) > AVATAR_MAX_BYTES:
        raise ValidationError("Image must be 2 MB or smaller")

    extension = _EXTENSIONS[_image_type(data)]
    directory = avatar_directory()
    for other in _EXTENSIONS.values():
        stale = directory / f"{user_id}{other}"
        if other != extension and stale.is_file():
            stale.unlink()
    (directory / f"{user_id}{extension}").write_bytes(data)
    return f"/auth/avatars/{user_id}{extension}?v={int(time.time())}"


def delete_avatar(user_id: str) -> None:
    """Remove every stored photo for a user.

    Args:
        user_id: Owning user identifier.
    """
    if not _USER_ID.fullmatch(user_id):
        return
    directory = avatar_directory()
    for extension in _EXTENSIONS.values():
        path = directory / f"{user_id}{extension}"
        if path.is_file():
            path.unlink()


def resolve_avatar(filename: str) -> Path:
    """Resolve a public avatar filename to a file inside the avatar directory.

    Args:
        filename: Name from the URL, such as ``{user_id}.png``.

    Returns:
        Absolute file path.

    Raises:
        NotFoundError: If the name is invalid or the file is missing.
    """
    if not _FILENAME.fullmatch(filename):
        raise NotFoundError("Avatar", filename)
    directory = avatar_directory().resolve()
    path = (directory / filename).resolve()
    if path.parent != directory or not path.is_file():
        raise NotFoundError("Avatar", filename)
    return path
