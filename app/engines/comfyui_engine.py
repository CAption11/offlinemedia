"""ComfyUI engine adapter that turns application requests into workflow jobs."""

from __future__ import annotations

from pathlib import Path

from app.core.generation import GenerationRequest, GenerationResult
from app.engines.comfyui_client import ComfyUIClient
from app.engines.workflow import Workflow, WorkflowError


class ComfyUIEngine:
    """High-level adapter around the local ComfyUI HTTP client."""

    def __init__(self, client: ComfyUIClient, workflow_dir: Path) -> None:
        self.client = client
        self.workflow_dir = workflow_dir

    def is_available(self) -> bool:
        return self.client.is_available()

    def workflow_for(self, request: GenerationRequest) -> Path:
        names = {
            "text_to_video": "text_to_video.json",
            "image_to_video": "image_to_video.json",
            "image_sequence": "image_sequence.json",
        }
        path = self.workflow_dir / names[request.generation_type.value]
        if not path.exists():
            raise WorkflowError(
                f"No workflow installed for {request.generation_type.value}. "
                f"Export an API-format ComfyUI workflow to {path}."
            )
        return path

    def generate(self, request: GenerationRequest) -> GenerationResult:
        try:
            workflow_path = self.workflow_for(request)
            workflow = Workflow.load(workflow_path)
            bindings = request.extra.get("bindings", {})
            values = {
                "prompt": request.prompt,
                "negative_prompt": request.negative_prompt,
                "width": request.width,
                "height": request.height,
                "frames": request.frames,
                "fps": request.fps,
                "seed": request.seed,
            }
            if isinstance(bindings, dict):
                workflow.apply_bindings(values, bindings)
            if request.extra.get("input_image"):
                workflow.apply_bindings(
                    {"image": request.extra["input_image"]},
                    bindings if isinstance(bindings, dict) else {},
                )
            job_id = self.client.queue_prompt(workflow.to_dict())
            history = self.client.wait_for_completion(job_id)
            outputs = self.client.extract_outputs(history)
            return GenerationResult(True, outputs, job_id=job_id)
        except Exception as exc:
            return GenerationResult(False, error=str(exc))

    def cancel(self, job_id: str) -> bool:
        return self.client.interrupt()
