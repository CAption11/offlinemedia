"""OfflineMedia environment diagnostics.

Works on Windows, Linux and Google Colab. It does not generate media; it
checks the pieces required before a real generation test.
"""
from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import sys
from pathlib import Path


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL':4}  {label:22} {detail}")


def main() -> int:
    print("OfflineMedia diagnostics")
    print("=" * 60)
    print(f"OS:      {platform.platform()}")
    print(f"Python:  {platform.python_version()}")
    print(f"Machine: {platform.machine()}")
    print()

    check("Python", sys.version_info >= (3, 10), sys.version.split()[0])
    check("httpx", importlib.util.find_spec("httpx") is not None)
    check("Pillow", importlib.util.find_spec("PIL") is not None)
    check("FFmpeg", shutil.which("ffmpeg") is not None, shutil.which("ffmpeg") or "not on PATH")
    check("Git", shutil.which("git") is not None, shutil.which("git") or "not on PATH")
    check("NVIDIA tools", shutil.which("nvidia-smi") is not None)

    try:
        import psutil
        memory_gb = psutil.virtual_memory().total / (1024 ** 3)
        check("System memory", memory_gb >= 8, f"{memory_gb:.1f} GB")
    except ImportError:
        check("System memory", False, "psutil unavailable")

    print()
    print("No AI model was loaded by this diagnostic.")
    print("Use test_generation.py after ComfyUI is running.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
