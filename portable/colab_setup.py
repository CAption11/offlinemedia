"""OfflineMedia Portable runtime setup for Google Colab.

This is a thin Portable entry point. Shared application code remains under
app/. The script prepares a Colab runtime and intentionally does not download
large model weights until an exact workflow/model manifest is selected.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(command))
    return subprocess.run(command, cwd=ROOT, check=check, text=True)


def gpu_available() -> bool:
    return shutil.which("nvidia-smi") is not None


def main() -> int:
    print("=" * 64)
    print("OfflineMedia Portable - Google Colab setup")
    print("=" * 64)
    print("OS:", platform.platform())
    print("Python:", sys.version.split()[0])
    print("Repository:", ROOT)
    print("NVIDIA tool available:", gpu_available())

    requirements = ROOT / "requirements-colab.txt"
    run([sys.executable, "-m", "pip", "install", "-q", "-r", str(requirements)])

    if gpu_available():
        result = run(["nvidia-smi"], check=False)
        if result.returncode != 0:
            print("WARNING: nvidia-smi was found but failed to execute.")
    else:
        print("WARNING: No NVIDIA runtime detected. Real video generation requires a GPU environment.")

    print()
    print("Portable base setup complete.")
    print("Next steps:")
    print("  1. Install/start ComfyUI.")
    print("  2. Install the verified workflow/model requirements.")
    print("  3. Run: python scripts/diagnostics.py")
    print("  4. Run the Portable smoke test.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
