"""Validation helpers used before submitting generation jobs."""
from __future__ import annotations

from pathlib import Path


class ValidationError(ValueError):
    pass


def validate_generation(*, prompt: str, width: int, height: int, frames: int, fps: int, input_images: list[Path] | None = None) -> None:
    if not prompt.strip():
        raise ValidationError("Prompt cannot be empty.")
    if not 64 <= width <= 4096 or not 64 <= height <= 4096:
        raise ValidationError("Width and height must be between 64 and 4096.")
    if width % 8 or height % 8:
        raise ValidationError("Width and height must be divisible by 8 for diffusion workflows.")
    if not 1 <= frames <= 1000:
        raise ValidationError("Frames must be between 1 and 1000.")
    if not 1 <= fps <= 120:
        raise ValidationError("FPS must be between 1 and 120.")
    for image in input_images or []:
        if not image.is_file():
            raise ValidationError(f"Input image does not exist: {image}")
        if image.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
            raise ValidationError(f"Unsupported image format: {image.suffix}")
