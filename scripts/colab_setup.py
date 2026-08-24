"""Prepare a Google Colab runtime for OfflineMedia integration tests.

This script deliberately does not download large AI model weights. Model
selection and downloads belong to the notebook/user so the runtime can be
changed without modifying the application.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    print("$", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    print("OfflineMedia Colab setup")
    print("Python:", sys.version.split()[0])
    print("CUDA available:", bool(shutil.which("nvidia-smi")))

    requirements = ROOT / "requirements-colab.txt"
    run([sys.executable, "-m", "pip", "install", "-q", "-r", str(requirements)])

    if shutil.which("nvidia-smi"):
        try:
            run(["nvidia-smi"])
        except subprocess.CalledProcessError:
            print("WARNING: nvidia-smi was found but did not execute successfully.")

    print("Setup complete.")
    print("Next: start ComfyUI separately, configure its URL, and run the smoke test.")


if __name__ == "__main__":
    main()
