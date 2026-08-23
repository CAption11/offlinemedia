"""Local generation engine registry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.paths import ensure_directories
from app.engines.comfyui_client import ComfyUIClient
from app.engines.comfyui_engine import ComfyUIEngine


@dataclass(slots=True)
class EngineStatus:
    name: str
    available: bool
    endpoint: str


class EngineManager:
    """Owns configured local engines and exposes one generation entry point."""

    def __init__(self) -> None:
        paths = ensure_directories()
        self.comfyui = ComfyUIClient()
        self.comfyui_engine = ComfyUIEngine(self.comfyui, paths["workflows"])

    def statuses(self) -> list[EngineStatus]:
        return [EngineStatus("ComfyUI", self.comfyui.is_available(), self.comfyui.base_url)]

    def any_available(self) -> bool:
        return any(status.available for status in self.statuses())

    def generate(self, request):
        return self.comfyui_engine.generate(request)
