"""Small local ComfyUI API client.

The client intentionally contains no model-specific workflow logic. Workflows are
loaded from the repository's workflows directory and submitted as JSON payloads.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.core.generation import GenerationRequest, GenerationResult


class ComfyUIClient:
    """HTTP client for a locally running ComfyUI server."""

    def __init__(self, base_url: str = "http://127.0.0.1:8188", timeout: float = 3.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client_id = str(uuid.uuid4())

    def is_available(self) -> bool:
        try:
            request = Request(f"{self.base_url}/system_stats", method="GET")
            with urlopen(request, timeout=self.timeout) as response:
                return response.status == 200
        except (OSError, URLError):
            return False

    def queue_prompt(self, workflow: dict[str, Any]) -> str:
        payload = json.dumps({"prompt": workflow, "client_id": self.client_id}).encode("utf-8")
        request = Request(
            f"{self.base_url}/prompt",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        return str(data["prompt_id"])

    def get_history(self, prompt_id: str) -> dict[str, Any]:
        request = Request(f"{self.base_url}/history/{prompt_id}", method="GET")
        with urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def wait_for_completion(self, prompt_id: str, poll_interval: float = 0.5, timeout: float = 3600) -> dict[str, Any]:
        started = time.monotonic()
        while time.monotonic() - started < timeout:
            history = self.get_history(prompt_id)
            if prompt_id in history:
                return history[prompt_id]
            time.sleep(poll_interval)
        raise TimeoutError(f"ComfyUI job {prompt_id} timed out")

    def load_workflow(self, path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def generate(self, request: GenerationRequest, workflow_path: Path) -> GenerationResult:
        try:
            workflow = self.load_workflow(workflow_path)
            prompt_id = self.queue_prompt(workflow)
            history = self.wait_for_completion(prompt_id)
            outputs: list[Path] = []
            for node in history.get("outputs", {}).values():
                for item in node.get("images", []) + node.get("gifs", []) + node.get("videos", []):
                    filename = item.get("filename")
                    if filename:
                        outputs.append(Path(filename))
            return GenerationResult(True, outputs, job_id=prompt_id)
        except Exception as exc:  # surface backend failures to the UI
            return GenerationResult(False, error=str(exc))
