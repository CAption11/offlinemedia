"""Runtime discovery for Windows and Google Colab/Linux."""
from __future__ import annotations

import os
import platform
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RuntimeInfo:
    os_name: str
    python: str
    ffmpeg: str | None
    nvidia_smi: str | None
    comfyui_url: str
    is_colab: bool


def detect(comfyui_url: str | None = None) -> RuntimeInfo:
    return RuntimeInfo(
        os_name=platform.system(),
        python=platform.python_version(),
        ffmpeg=shutil.which("ffmpeg"),
        nvidia_smi=shutil.which("nvidia-smi"),
        comfyui_url=comfyui_url or os.environ.get("OFFLINEMEDIA_COMFYUI_URL", "http://127.0.0.1:8188"),
        is_colab=Path("/content").is_dir() and bool(os.environ.get("COLAB_GPU") or os.environ.get("COLAB_JUPYTER_IP")),
    )


def summary(info: RuntimeInfo) -> str:
    return "\n".join([
        f"OS: {info.os_name}",
        f"Python: {info.python}",
        f"FFmpeg: {info.ffmpeg or 'not found'}",
        f"NVIDIA tools: {info.nvidia_smi or 'not found'}",
        f"ComfyUI: {info.comfyui_url}",
        f"Colab: {'yes' if info.is_colab else 'no'}",
    ])
