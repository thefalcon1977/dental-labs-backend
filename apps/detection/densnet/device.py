"""Device selection: CUDA → MPS → CPU."""

from __future__ import annotations

import torch


def get_device() -> torch.device:
    """Return the best available torch device.

    Returns:
        CUDA if available, else MPS, else CPU.
    """
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def describe_device(device: torch.device | None = None) -> str:
    """Human-readable device description for CLI logs.

    Args:
        device: Device to describe; defaults to :func:`get_device`.

    Returns:
        Short description string.
    """
    device = device or get_device()
    if device.type == "cuda":
        return f"cuda ({torch.cuda.get_device_name(0)})"
    if device.type == "mps":
        return "mps (Metal Performance Shaders)"
    return "cpu"
