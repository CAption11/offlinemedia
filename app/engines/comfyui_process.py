"""Start and stop a local ComfyUI installation without admin rights."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


class ComfyUIProcessManager:
    """Manage a user-owned ComfyUI process."""

    def __init__(self, install_dir: Path | None = None, python_executable: str | None = None) -> None:
        self.install_dir = install_dir
        self.python_executable = python_executable or "python"
        self.process: subprocess.Popen | None = None

    def discover_launcher(self) -> Path | None:
        if not self.install_dir or not self.install_dir.exists():
            return None
        candidates = (
            "run_nvidia_gpu.bat",
            "run_cpu.bat",
            "run_amd_gpu.bat",
            "run_amdgpu.bat",
            "run_directml.bat",
            "run.py",
            "main.py",
        )
        for name in candidates:
            candidate = self.install_dir / name
            if candidate.exists():
                return candidate
        return None

    def start(self) -> None:
        launcher = self.discover_launcher()
        if launcher is None:
            raise FileNotFoundError(
                "No ComfyUI launcher found. Select a ComfyUI installation directory first."
            )
        if self.is_running():
            return

        if launcher.suffix.lower() == ".bat":
            command = ["cmd.exe", "/c", str(launcher)]
        else:
            command = [self.python_executable, str(launcher)]

        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
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
            if os.name == "nt":
                self.process.send_signal(subprocess.CTRL_BREAK_EVENT)
            else:
                self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None
