"""Small local ComfyUI API client.

No cloud services are used. The client talks only to a locally running
ComfyUI instance and leaves model-specific workflow logic to the workflow layer.
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

    def __init__(self, base_url: str = "http://127.0.0.1:8188", timeout: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client_id = str(uuid.uuid4())

    def _request_json(self, path: str, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = None
        headers: dict[str, str] = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(f"{self.base_url}{path}", data=data, headers=headers, method=method)
        with urlopen(request, timeout=self.timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}

    def is_available(self) -> bool:
        try:
            self._request_json("/system_stats")
            return True
        except (OSError, URLError, ValueError):
            return False

    def system_stats(self) -> dict[str, Any]:
        return self._request_json("/system_stats")

    def object_info(self) -> dict[str, Any]:
        return self._request_json("/object_info")

    def queue_prompt(self, workflow: dict[str, Any]) -> str:
        data = self._request_json("/prompt", "POST", {"prompt": workflow, "client_id": self.client_id})
        if "prompt_id" not in data:
            raise RuntimeError(f"ComfyUI rejected the workflow: {data}")
        return str(data["prompt_id"])

    def get_history(self, prompt_id: str) -> dict[str, Any]:
        return self._request_json(f"/history/{prompt_id}")

    def interrupt(self) -> bool:
        try:
            self._request_json("/interrupt", "POST", {})
            return True
        except (OSError, URLError, ValueError):
            return False

    def wait_for_completion(
        self,
        prompt_id: str,
        poll_interval: float = 0.5,
        timeout: float = 3600,
    ) -> dict[str, Any]:
        started = time.monotonic()
        while time.monotonic() - started < timeout:
            history = self.get_history(prompt_id)
            if prompt_id in history:
                result = history[prompt_id]
                status = result.get("status", {})
                if status.get("status_str") == "error":
                    raise RuntimeError(f"ComfyUI generation failed: {status}")
                return result
            time.sleep(poll_interval)
        raise TimeoutError(f"ComfyUI job {prompt_id} timed out after {timeout:.0f}s")

    @staticmethod
    def extract_outputs(history: dict[str, Any]) -> list[Path]:
        outputs: list[Path] = []
        for node in history.get("outputs", {}).values():
            for key in ("images", "gifs", "videos", "audio"):
                for item in node.get(key, []) or []:
                    filename = item.get("filename")
                    if filename:
                        outputs.append(Path(filename))
        return outputs

    def load_workflow(self, path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def generate(self, request: GenerationRequest, workflow_path: Path) -> GenerationResult:
        try:
            workflow = self.load_workflow(workflow_path)
            job_id = self.queue_prompt(workflow)
            history = self.wait_for_completion(job_id)
            return GenerationResult(True, self.extract_outputs(history), job_id=job_id)
        except Exception as exc:
            return GenerationResult(False, error=str(exc))
