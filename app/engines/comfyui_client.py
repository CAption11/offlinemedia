"""Small local ComfyUI API client.

The client talks only to a local ComfyUI server. It handles queueing, status,
input-image upload and copying generated files back into OfflineMedia output.
"""

from __future__ import annotations

import json
import mimetypes
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
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

    def upload_image(self, path: Path, overwrite: bool = False) -> str:
        boundary = f"----OfflineMedia{uuid.uuid4().hex}"
        filename = path.name
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        file_bytes = path.read_bytes()
        parts = [
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{filename}\"\r\nContent-Type: {content_type}\r\n\r\n".encode(),
            file_bytes,
            f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\n{str(overwrite).lower()}\r\n".encode(),
            f"--{boundary}--\r\n".encode(),
        ]
        request = Request(
            f"{self.base_url}/upload/image",
            data=b"".join(parts),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urlopen(request, timeout=max(self.timeout, 30.0)) as response:
            result = json.loads(response.read().decode("utf-8"))
        if not result.get("name"):
            raise RuntimeError(f"ComfyUI image upload failed: {result}")
        return str(result["name"])

    def get_history(self, prompt_id: str) -> dict[str, Any]:
        return self._request_json(f"/history/{prompt_id}")

    def interrupt(self) -> bool:
        try:
            self._request_json("/interrupt", "POST", {})
            return True
        except (OSError, URLError, ValueError):
            return False

    def wait_for_completion(self, prompt_id: str, poll_interval: float = 0.5, timeout: float = 3600) -> dict[str, Any]:
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

    def download_output(self, item: dict[str, Any], destination: Path) -> Path:
        params = {"filename": item.get("filename", ""), "type": item.get("type", "output")}
        if item.get("subfolder"):
            params["subfolder"] = item["subfolder"]
        url = f"{self.base_url}/view?{urlencode(params)}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        request = Request(url, method="GET")
        with urlopen(request, timeout=max(self.timeout, 30.0)) as response:
            destination.write_bytes(response.read())
        return destination

    @staticmethod
    def output_items(history: dict[str, Any]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for node in history.get("outputs", {}).values():
            for key in ("images", "gifs", "videos", "audio"):
                items.extend(node.get(key, []) or [])
        return [item for item in items if item.get("filename")]

    @staticmethod
    def extract_outputs(history: dict[str, Any]) -> list[Path]:
        return [Path(item["filename"]) for item in ComfyUIClient.output_items(history)]

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
