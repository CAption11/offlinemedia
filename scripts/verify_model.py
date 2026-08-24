"""Verify a local model artifact against a SHA-256 manifest entry."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.model_installer import sha256_file


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("sha256")
    args = parser.parse_args()
    if not args.file.is_file():
        print(f"MISSING: {args.file}")
        return 2
    actual = sha256_file(args.file)
    if actual.lower() != args.sha256.lower():
        print(f"FAIL: {actual}")
        return 1
    print(f"PASS: {actual}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
