"""Workflow loading and safe request patching for ComfyUI."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


class WorkflowError(RuntimeError):
    """Raised when a workflow cannot be loaded or patched."""


class Workflow:
    """Model-agnostic ComfyUI API workflow wrapper.

    Workflows are exported from ComfyUI and stored as API-format JSON. The
    optional ``bindings`` section in a workflow metadata file can map logical
    fields such as prompt, seed and image to node/input locations.
    """

    def __init__(self, graph: dict[str, Any]) -> None:
        self.graph = graph

    @classmethod
    def load(cls, path: Path) -> "Workflow":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkflowError(f"Unable to read workflow: {path}") from exc
        if not isinstance(data, dict) or not data:
            raise WorkflowError("Workflow JSON must contain an object")
        return cls(data)

    def copy(self) -> "Workflow":
        return Workflow(copy.deepcopy(self.graph))

    def set_input(self, node_id: str, input_name: str, value: Any) -> None:
        node = self.graph.get(str(node_id))
        if not isinstance(node, dict):
            raise WorkflowError(f"Workflow node not found: {node_id}")
        inputs = node.setdefault("inputs", {})
        if not isinstance(inputs, dict):
            raise WorkflowError(f"Node {node_id} has invalid inputs")
        inputs[input_name] = value

    def apply_bindings(self, values: dict[str, Any], bindings: dict[str, dict[str, str]]) -> None:
        for logical_name, value in values.items():
            target = bindings.get(logical_name)
            if target and "node" in target and "input" in target and value is not None:
                self.set_input(target["node"], target["input"], value)

    def to_dict(self) -> dict[str, Any]:
        return copy.deepcopy(self.graph)
