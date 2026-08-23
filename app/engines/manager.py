"""Local generation engine registry."""

from __future__ import annotations

from dataclasses import dataclass

from app.engines.comfyui_client import ComfyUIClient


@dataclass(slots=True)
class EngineStatus:
    name: str
    available: bool
    endpoint: str


class EngineManager:
    """Owns the configured local engines and reports their state."""

    def __init__(self) -> None:
        self.comfyui = ComfyUIClient()

    def statuses(self) -> list[EngineStatus]:
        return [
            EngineStatus("ComfyUI", self.comfyui.is_available(), self.comfyui.base_url),
        ]

    def any_available(self) -> bool:
        return any(status.available for status in self.statuses())
