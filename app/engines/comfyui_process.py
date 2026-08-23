"""Start and stop a local ComfyUI installation without requiring admin rights."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


class ComfyUIProcessManager:
    """Manage a user-owned ComfyUI process."""

    def __init__(self, install_dir: Path | None = None) -> None:
        self.install_dir = install_dir
        self.process: subprocess.Popen | None = None

    def discover_launcher(self) -> Path | None:
        if not self.install_dir or not self.install_dir.exists():
            return None
        candidates = (
            "run_cpu.bat",
            "run_cpu.bat",
            "run_nvidia_gpu.bat",
            "run_amdgpu.bat",
            "run_amd_gpu.bat",
        )
        for name in candidates:
            candidate = self.install_dir / name
            if candidate.exists():
                return candidate
        main = self.install_dir / "main.py"
        return main if main.exists() else None

    def start(self) -> None:
        launcher = self.discover_launcher()
        if launcher is None:
            raise FileNotFoundError("No ComfyUI launcher was found in the configured installation directory")
        if self.is_running():
            return

        if launcher.suffix.lower() == ".bat":
            command = ["cmd.exe", "/c", str(launcher)]
        else:
            command = ["python", str(launcher)]

        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

        self.process = subprocess.Popen(
            command,
            cwd=str(self.install_dir),
            creationflags=creationflags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def stop(self) -> None:
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.terminate()
        self.process = None

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None
