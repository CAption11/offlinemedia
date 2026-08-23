"""Application filesystem locations."""

from __future__ import annotations

import os
from pathlib import Path


APP_NAME = "OfflineMedia"


def data_root() -> Path:
    """Return a writable per-user data directory on Windows."""
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / APP_NAME
    return Path.home() / f".{APP_NAME.lower()}"


def ensure_directories() -> dict[str, Path]:
    root = data_root()
    paths = {
        "root": root,
        "models": root / "models",
        "workflows": root / "workflows",
        "projects": root / "projects",
        "outputs": root / "outputs",
        "logs": root / "logs",
        "cache": root / "cache",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths
