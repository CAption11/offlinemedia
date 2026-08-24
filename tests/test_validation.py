from pathlib import Path

import pytest

from app.core.validation import ValidationError, validate_generation


def test_valid_generation_request():
    validate_generation(prompt="test", width=320, height=240, frames=17, fps=8)


def test_empty_prompt_rejected():
    with pytest.raises(ValidationError):
        validate_generation(prompt=" ", width=320, height=240, frames=17, fps=8)


def test_dimensions_must_be_divisible_by_eight():
    with pytest.raises(ValidationError):
        validate_generation(prompt="test", width=321, height=240, frames=17, fps=8)


def test_missing_input_image_rejected():
    with pytest.raises(ValidationError):
        validate_generation(
            prompt="test",
            width=320,
            height=240,
            frames=17,
            fps=8,
            input_images=[Path("does-not-exist.png")],
        )
