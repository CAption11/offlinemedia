"""Validate a ComfyUI API workflow before a generation run."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workflow", type=Path)
    args = parser.parse_args()

    try:
        data = json.loads(args.workflow.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"INVALID: {exc}")
        return 2

    if not isinstance(data, dict) or not data:
        print("INVALID: workflow must be a non-empty JSON object")
        return 2

    errors = []
    for node_id, node in data.items():
        if not isinstance(node, dict):
            errors.append(f"node {node_id}: expected object")
            continue
        if not node.get("class_type"):
            errors.append(f"node {node_id}: missing class_type")
        if not isinstance(node.get("inputs", {}), dict):
            errors.append(f"node {node_id}: inputs must be an object")

    if errors:
        print("INVALID WORKFLOW")
        for error in errors:
            print("-", error)
        return 1

    print(f"VALID: {len(data)} nodes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
