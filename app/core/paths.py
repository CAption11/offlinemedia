"""Application filesystem locations."""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "OfflineMedia"


def data_root() -> Path:
    """Return a writable per-user data directory."""
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA")
        if local:
            return Path(local) / APP_NAME
        return Path.home() / "AppData" / "Local" / APP_NAME

    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / APP_NAME
    return Path.home() / ".local" / "share" / APP_NAME


def ensure_directories() -> dict[str, Path]:
    """Create and return all application-owned directories."""
    root = data_root()
    paths = {
        "root": root,
        "config": root / "config",
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
