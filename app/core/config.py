"""Persistent user configuration for OfflineMedia."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .paths import ensure_directories


@dataclass
class AppConfig:
    comfyui_url: str = "http://127.0.0.1:8188"
    comfyui_root: str = ""
    workflow_dir: str = ""
    output_dir: str = ""
    default_width: int = 320
    default_height: int = 240
    default_frames: int = 17
    default_fps: int = 8


def config_path() -> Path:
    return ensure_directories()["config"] / "settings.json"


def load_config() -> AppConfig:
    path = config_path()
    if not path.exists():
        return AppConfig()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return AppConfig(**{k: v for k, v in data.items() if k in AppConfig.__dataclass_fields__})
    except (OSError, ValueError, TypeError):
        return AppConfig()


def save_config(config: AppConfig) -> Path:
    path = config_path()
    path.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")
    return path
