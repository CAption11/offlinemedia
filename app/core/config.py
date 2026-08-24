"""Persistent user configuration for OfflineMedia."""
from __future__ import annotations

import json
import os
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


def default_config() -> AppConfig:
    paths = ensure_directories()
    return AppConfig(
        comfyui_url=os.environ.get("OFFLINEMEDIA_COMFYUI_URL", "http://127.0.0.1:8188"),
        workflow_dir=str(paths["workflows"]),
        output_dir=str(paths["outputs"]),
    )


def load_config() -> AppConfig:
    path = config_path()
    defaults = default_config()
    if not path.exists():
        return defaults
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return defaults
        values = asdict(defaults)
        values.update({k: v for k, v in data.items() if k in AppConfig.__dataclass_fields__})
        config = AppConfig(**values)
        if config.default_width <= 0 or config.default_height <= 0 or config.default_frames <= 0 or config.default_fps <= 0:
            return defaults
        return config
    except (OSError, ValueError, TypeError):
        return defaults


def save_config(config: AppConfig) -> Path:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")
    temporary.replace(path)
    return path
