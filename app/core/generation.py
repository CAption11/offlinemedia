"""Core generation models and engine contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol


class GenerationType(str, Enum):
    TEXT_TO_VIDEO = "text_to_video"
    IMAGE_TO_VIDEO = "image_to_video"
    IMAGE_SEQUENCE = "image_sequence"


@dataclass(slots=True)
class GenerationRequest:
    """A model-independent generation request."""

    generation_type: GenerationType
    prompt: str = ""
    negative_prompt: str = ""
    input_images: list[Path] = field(default_factory=list)
    width: int = 512
    height: int = 512
    frames: int = 49
    fps: int = 8
    seed: int | None = None
    model: str | None = None
    output_dir: Path = Path("projects")
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GenerationResult:
    """Result returned by an engine after a generation job."""

    success: bool
    output_files: list[Path] = field(default_factory=list)
    error: str | None = None
    job_id: str | None = None


class GenerationEngine(Protocol):
    """Interface implemented by local generation backends."""

    def is_available(self) -> bool: ...

    def generate(self, request: GenerationRequest) -> GenerationResult: ...

    def cancel(self, job_id: str) -> bool: ...
