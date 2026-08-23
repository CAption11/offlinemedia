"""Simple JSON project persistence."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ProjectStore:
    """Persist project metadata without requiring a database server."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def create(self, name: str, settings: dict[str, Any] | None = None) -> Path:
        safe_name = "".join(ch if ch.isalnum() or ch in "-_ " else "_" for ch in name).strip() or "Untitled"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        directory = self.root / f"{timestamp}_{safe_name}"
        directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "name": name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "settings": settings or {},
            "assets": [],
            "generations": [],
        }
        (directory / "project.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return directory

    def load(self, directory: Path) -> dict[str, Any]:
        project_file = directory / "project.json"
        if not project_file.exists():
            raise FileNotFoundError(project_file)
        return json.loads(project_file.read_text(encoding="utf-8"))

    def save(self, directory: Path, payload: dict[str, Any]) -> None:
        (directory / "project.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
