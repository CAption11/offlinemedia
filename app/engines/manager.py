"""Local generation engine registry."""

from __future__ import annotations

import os
from dataclasses import dataclass

from app.core.paths import ensure_directories
from app.core.generation import GenerationRequest, GenerationResult
from app.engines.comfyui_client import ComfyUIClient
from app.engines.comfyui_engine import ComfyUIEngine


@dataclass(slots=True)
class EngineStatus:
    name: str
    available: bool
    endpoint: str


class EngineManager:
    """Own configured local engines and expose one generation entry point."""

    def __init__(self, comfyui_url: str | None = None) -> None:
        paths = ensure_directories()
        url = comfyui_url or os.getenv("OFFLINEMEDIA_COMFYUI_URL", "http://127.0.0.1:8188")
        self.comfyui = ComfyUIClient(base_url=url)
        self.comfyui_engine = ComfyUIEngine(
            self.comfyui,
            paths["workflows"],
            paths["outputs"],
        )

    def statuses(self) -> list[EngineStatus]:
        return [EngineStatus("ComfyUI", self.comfyui.is_available(), self.comfyui.base_url)]

    def any_available(self) -> bool:
        return any(status.available for status in self.statuses())

    def generate(self, request: GenerationRequest) -> GenerationResult:
        return self.comfyui_engine.generate(request)
