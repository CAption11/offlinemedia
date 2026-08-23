"""Persistent user settings for OfflineMedia."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class AppSettings:
    comfyui_url: str = "http://127.0.0.1:8188"
    comfyui_install_dir: str = ""
    workflow_dir: str = ""
    output_dir: str = ""


class SettingsStore:
    """Small JSON settings store under the user's OfflineMedia data directory."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> AppSettings:
        if not self.path.exists():
            return AppSettings()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return AppSettings(**{key: value for key, value in data.items() if key in AppSettings.__dataclass_fields__})
        except (OSError, ValueError, TypeError):
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
