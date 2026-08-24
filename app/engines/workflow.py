"""Workflow loading and safe request patching for ComfyUI."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


class WorkflowError(RuntimeError):
    """Raised when a workflow cannot be loaded or converted."""


class Workflow:
    """Wrapper around a ComfyUI API-format workflow graph."""

    def __init__(self, graph: dict[str, Any]) -> None:
        self.graph = graph

    @classmethod
    def load(cls, path: Path, object_info: dict[str, Any] | None = None) -> "Workflow":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkflowError(f"Unable to read workflow: {path}") from exc
        if not isinstance(data, dict) or not data:
            raise WorkflowError("Workflow JSON must contain an object")
        if "nodes" in data and isinstance(data["nodes"], list):
            if object_info is None:
                raise WorkflowError("A visual ComfyUI workflow requires /object_info to convert it")
            return cls.from_ui_workflow(data, object_info)
        return cls(data)

    @staticmethod
    def _has_control_after_generate(input_def: Any) -> bool:
        """Return whether an INT input exposes ComfyUI's seed-control widget."""
        if not isinstance(input_def, (list, tuple)) or len(input_def) < 2:
            return False
        options = input_def[1]
        return isinstance(options, dict) and bool(options.get("control_after_generate"))

    @classmethod
    def from_ui_workflow(cls, data: dict[str, Any], object_info: dict[str, Any]) -> "Workflow":
        links = {
            str(link[0]): link
            for link in data.get("links", [])
            if isinstance(link, list) and len(link) >= 6
        }
        graph: dict[str, Any] = {}
        for node in data.get("nodes", []):
            if not isinstance(node, dict):
                continue
            node_id = str(node.get("id"))
            class_type = str(node.get("type", ""))
            if not node_id or not class_type:
                continue

            definition = object_info.get(class_type, {})
            input_def = definition.get("input", {}) if isinstance(definition, dict) else {}
            required = input_def.get("required", {}) if isinstance(input_def, dict) else {}
            optional = input_def.get("optional", {}) if isinstance(input_def, dict) else {}
            input_order = definition.get("input_order", {}) if isinstance(definition, dict) else {}

            ordered_names: list[str] = []
            for group, source in (("required", required), ("optional", optional)):
                names = input_order.get(group, []) if isinstance(input_order, dict) else []
                ordered_names.extend(str(name) for name in (names or source.keys()))

            # KSampler's seed control is a UI-only widget. In ComfyUI API
            # format, the workflow stores two widget values for this concept:
            # seed followed by control_after_generate (for example
            # [123, "randomize", 30, 6, ...]). Some /object_info versions omit
            # that synthetic widget from input_order, which would otherwise
            # shift every subsequent value left and send "randomize" to steps.
            # Insert it using the authoritative node metadata instead of
            # hard-coding KSampler node IDs or widget positions.
            expanded_names: list[str] = []
            for name in ordered_names:
                expanded_names.append(name)
                definition_for_name = required.get(name, optional.get(name))
                if self_has_control := cls._has_control_after_generate(definition_for_name):
                    if "control_after_generate" not in expanded_names:
                        expanded_names.append("control_after_generate")

            api_inputs: dict[str, Any] = {}
            linked_names: set[str] = set()
            for ui_input in node.get("inputs", []) or []:
                if not isinstance(ui_input, dict) or ui_input.get("link") is None:
                    continue
                link = links.get(str(ui_input["link"]))
                if not link:
                    continue
                name = str(ui_input.get("name", ""))
                if name:
                    api_inputs[name] = [str(link[1]), int(link[2])]
                    linked_names.add(name)

            # widgets_values contains only values for non-linked widget inputs.
            # Match those values against explicit UI widget names first, then
            # fall back to ComfyUI's object_info ordering. When a frontend
            # exports widgets_values_named, prefer it because it is the most
            # precise mapping available.
            widgets_named = node.get("widgets_values_named")
            if isinstance(widgets_named, dict):
                for name, value in widgets_named.items():
                    name = str(name)
                    if name not in linked_names:
                        api_inputs[name] = value
            else:
                widgets = list(node.get("widgets_values", []) or [])
                widget_names = [
                    str(ui_input.get("name"))
                    for ui_input in (node.get("inputs", []) or [])
                    if isinstance(ui_input, dict)
                    and ui_input.get("link") is None
                    and ui_input.get("name")
                ]
                names = widget_names or [name for name in expanded_names if name not in linked_names]
                for name, value in zip(names, widgets):
                    if name not in linked_names:
                        api_inputs[name] = value

            graph[node_id] = {"inputs": api_inputs, "class_type": class_type}
            title = node.get("properties", {}).get("Node name for S&R")
            if title:
                graph[node_id]["_meta"] = {"title": title}

        if not graph:
            raise WorkflowError("Visual workflow contains no nodes")
        return cls(graph)

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

    def _nodes_with_input(self, input_name: str) -> list[str]:
        return [
            node_id
            for node_id, node in self.graph.items()
            if isinstance(node, dict) and input_name in node.get("inputs", {})
        ]

    def auto_bind(self, values: dict[str, Any]) -> None:
        """Apply common controls while preserving model-specific workflows."""
        prompt_nodes = self._nodes_with_input("text")
        if values.get("prompt") is not None and prompt_nodes:
            self.set_input(prompt_nodes[0], "text", values["prompt"])
        if values.get("negative_prompt") is not None and len(prompt_nodes) > 1:
            self.set_input(prompt_nodes[1], "text", values["negative_prompt"])

        aliases = {
            "width": ("width",),
            "height": ("height",),
            "frames": ("frames", "length", "num_frames", "video_length"),
            "fps": ("fps", "frame_rate"),
            "seed": ("seed",),
        }
        for logical_name, input_names in aliases.items():
            value = values.get(logical_name)
            if value is None:
                continue
            for input_name in input_names:
                nodes = self._nodes_with_input(input_name)
                if nodes:
                    self.set_input(nodes[0], input_name, value)
                    break

        image_nodes = self._nodes_with_input("image")
        if values.get("image") is not None and image_nodes:
            self.set_input(image_nodes[0], "image", values["image"])

    def apply_bindings(self, values: dict[str, Any], bindings: dict[str, dict[str, str]]) -> None:
        for logical_name, value in values.items():
            target = bindings.get(logical_name)
            if target and "node" in target and "input" in target and value is not None:
                self.set_input(target["node"], target["input"], value)

    def to_dict(self) -> dict[str, Any]:
        return copy.deepcopy(self.graph)
