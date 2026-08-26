"""Portable entry point for a real ComfyUI generation smoke test.

This delegates to the existing shared generation test so Portable and
Mainload exercise the same generation backend instead of growing two copies.
"""
from __future__ import annotations

import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    runpy.run_path(str(ROOT / "scripts" / "test_generation.py"), run_name="__main__")
