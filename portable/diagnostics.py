"""Portable runtime diagnostics.

The command is intentionally useful in a fresh Google Colab runtime and
returns a non-zero status when a required base capability is missing.
"""
from __future__ import annotations

import importlib.util
import platform
import shutil
import subprocess
import sys


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def main() -> int:
    print("OfflineMedia Portable diagnostics")
    print("Python:", sys.version.split()[0])
    print("Platform:", platform.platform())

    checks = {
        "nvidia-smi": command_exists("nvidia-smi"),
        "git": command_exists("git"),
        "ffmpeg": command_exists("ffmpeg"),
        "httpx": importlib.util.find_spec("httpx") is not None,
        "Pillow": importlib.util.find_spec("PIL") is not None,
        "psutil": importlib.util.find_spec("psutil") is not None,
    }

    for name, available in checks.items():
        print(f"{'PASS' if available else 'FAIL'}: {name}")

    if checks["nvidia-smi"]:
        print("\nGPU information:")
        subprocess.run(["nvidia-smi"], check=False)
    else:
        print("\nNo NVIDIA GPU runtime detected.")

    required = ("git", "httpx", "Pillow", "psutil")
    missing = [name for name in required if not checks[name]]
    if missing:
        print("Missing Portable requirements:", ", ".join(missing))
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
