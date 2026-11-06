"""Shared library for densNet dental tissue classification."""

from __future__ import annotations

from densnet.constants import CLASS_COLORS, CLASS_NAMES, DEFAULT_MODEL_PATH
from densnet.device import get_device

__all__ = [
    "CLASS_COLORS",
    "CLASS_NAMES",
    "DEFAULT_MODEL_PATH",
    "get_device",
]
