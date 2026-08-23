"""Abstract interface for local generation engines."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class GenerationRequest:
    """Common request fields shared by local generation engines."""

    mode: str
    prompt: str = ""
    image: Path | None = None
    width: int = 512
    height: int = 512
    frames: int = 49
    fps: int = 8
    seed: int | None = None
    options: dict[str, Any] | None = None


@dataclass(slots=True)
class GenerationResult:
    """Result returned by a generation engine."""

    success: bool
    output: Path | None = None
    error: str | None = None


class GenerationEngine(ABC):
    """Contract implemented by each local AI backend."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return whether the backend is reachable."""

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Execute a generation request."""

    @abstractmethod
    def cancel(self) -> None:
        """Cancel the active generation if possible."""
