"""Robust local ComfyUI HTTP client.

The client talks only to a configured ComfyUI server. It supports queueing,
health checks, workflow metadata, image upload, progress polling and output
retrieval. It deliberately has no cloud dependency.
"""

from __future__ import annotations

import json
import mimetypes
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.generation import GenerationRequest, GenerationResult


class ComfyUIError(RuntimeError):
    """A ComfyUI communication or protocol error."""


class ComfyUIClient:
    """Small dependency-free HTTP client for a local ComfyUI server."""

    def __init__(self, base_url: str | None = None, timeout: float = 10.0, *, host: str | None = None, port: int = 8188) -> None:
        if base_url is None:
            host = host or "127.0.0.1"
            base_url = host if "://" in host else f"http://{host}:{port}"
        self.base_url = base_url.rstrip("/")
        self.timeout = max(1.0, timeout)
        self.client_id = str(uuid.uuid4())

    def _request(self, path: str, method: str = "GET", payload: dict[str, Any] | None = None) -> bytes:
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(f"{self.base_url}{path}", data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return response.read()
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise ComfyUIError(f"HTTP {exc.code} from ComfyUI {path}: {body[:500]}") from exc
        except URLError as exc:
            raise ComfyUIError(f"Cannot reach ComfyUI at {self.base_url}: {exc.reason}") from exc
        except TimeoutError as exc:
            raise ComfyUIError(f"ComfyUI request timed out: {path}") from exc

    def _request_json(self, path: str, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
        raw = self._request(path, method, payload)
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ComfyUIError(f"ComfyUI returned invalid JSON from {path}") from exc
        if not isinstance(data, dict):
            raise ComfyUIError(f"Unexpected JSON response from {path}")
        return data

    def is_available(self) -> bool:
        try:
            self._request_json("/system_stats")
            return True
        except (ComfyUIError, OSError, ValueError):
            return False

    def system_stats(self) -> dict[str, Any]:
        return self._request_json("/system_stats")

    def object_info(self) -> dict[str, Any]:
        return self._request_json("/object_info")

    def queue_prompt(self, workflow: dict[str, Any]) -> str:
        data = self._request_json("/prompt", "POST", {"prompt": workflow, "client_id": self.client_id})
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise ComfyUIError(f"ComfyUI rejected the workflow: {data}")
        return str(prompt_id)

    def upload_image(self, path: Path, overwrite: bool = False) -> str:
        if not path.is_file():
            raise FileNotFoundError(path)
        boundary = f"----OfflineMedia{uuid.uuid4().hex}"
        filename = path.name
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        parts = [
            (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{filename}\"\r\n"
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode(),
            path.read_bytes(),
            (
                f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\n"
                f"{str(overwrite).lower()}\r\n--{boundary}--\r\n"
            ).encode(),
        ]
        request = Request(
            f"{self.base_url}/upload/image", data=b"".join(parts),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=max(self.timeout, 30.0)) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ComfyUIError(f"ComfyUI image upload failed: {exc}") from exc
        if not isinstance(result, dict) or not result.get("name"):
            raise ComfyUIError(f"ComfyUI image upload failed: {result}")
        return str(result["name"])

    def get_history(self, prompt_id: str) -> dict[str, Any]:
        return self._request_json(f"/history/{prompt_id}")

    def get_queue(self) -> dict[str, Any]:
        return self._request_json("/queue")

    def interrupt(self) -> bool:
        try:
            self._request_json("/interrupt", "POST", {})
            return True
        except ComfyUIError:
            return False

    def wait_for_completion(self, prompt_id: str, poll_interval: float = 0.75, timeout: float = 3600) -> dict[str, Any]:
        started = time.monotonic()
        while time.monotonic() - started < timeout:
            history = self.get_history(prompt_id)
            result = history.get(prompt_id)
            if isinstance(result, dict):
                status = result.get("status", {})
                if isinstance(status, dict):
                    status_str = status.get("status_str")
                    if status_str in {"error", "failed"}:
                        raise ComfyUIError(f"ComfyUI generation failed: {status}")
                    if status.get("completed") is False and status.get("messages"):
                        raise ComfyUIError(f"ComfyUI generation failed: {status}")
                return result
            time.sleep(max(0.1, poll_interval))
        raise TimeoutError(f"ComfyUI job {prompt_id} timed out after {timeout:.0f}s")

    def download_output(self, item: dict[str, Any], destination: Path) -> Path:
        filename = item.get("filename")
        if not filename:
            raise ComfyUIError("ComfyUI output item has no filename")
        params = {"filename": filename, "type": item.get("type", "output")}
        if item.get("subfolder"):
            params["subfolder"] = item["subfolder"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        request = Request(f"{self.base_url}/view?{urlencode(params)}", headers={"Accept": "application/octet-stream"})
        temporary = destination.with_suffix(destination.suffix + ".part")
        try:
            with urlopen(request, timeout=max(self.timeout, 30.0)) as response, temporary.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            temporary.replace(destination)
        except (HTTPError, URLError, TimeoutError) as exc:
            temporary.unlink(missing_ok=True)
            raise ComfyUIError(f"Unable to download ComfyUI output {filename}: {exc}") from exc
        return destination

    @staticmethod
    def output_items(history: dict[str, Any]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for node in history.get("outputs", {}).values():
            if not isinstance(node, dict):
                continue
            for key in ("images", "gifs", "videos", "audio"):
                values = node.get(key, []) or []
                if isinstance(values, list):
                    items.extend(item for item in values if isinstance(item, dict) and item.get("filename"))
        return items

    def load_workflow(self, path: Path) -> dict[str, Any]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ComfyUIError(f"Unable to load workflow {path}") from exc
        if not isinstance(data, dict):
            raise ComfyUIError("Workflow must be a JSON object")
        return data

    def generate(self, request: GenerationRequest, workflow_path: Path) -> GenerationResult:
        try:
            workflow = self.load_workflow(workflow_path)
            job_id = self.queue_prompt(workflow)
            history = self.wait_for_completion(job_id)
            return GenerationResult(True, [Path(item["filename"]) for item in self.output_items(history)], job_id=job_id)
        except Exception as exc:
            return GenerationResult(False, error=str(exc))
