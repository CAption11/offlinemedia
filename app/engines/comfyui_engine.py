"""ComfyUI engine adapter that turns application requests into workflow jobs."""

from __future__ import annotations

from pathlib import Path

from app.core.generation import GenerationRequest, GenerationResult
from app.engines.comfyui_client import ComfyUIClient
from app.engines.workflow import Workflow, WorkflowError


class ComfyUIEngine:
    """High-level adapter around the local ComfyUI HTTP client."""

    def __init__(self, client: ComfyUIClient, workflow_dir: Path, output_dir: Path | None = None) -> None:
        self.client = client
        self.workflow_dir = workflow_dir
        self.output_dir = output_dir or workflow_dir.parent / "outputs"

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
                f"Copy an API or visual ComfyUI workflow to {path}."
            )
        return path

    def generate(self, request: GenerationRequest) -> GenerationResult:
        try:
            workflow_path = self.workflow_for(request)
            workflow = Workflow.load(workflow_path, self.client.object_info())
            bindings = request.extra.get("bindings", {})
            if not isinstance(bindings, dict):
                bindings = {}

            values = {
                "prompt": request.prompt,
                "negative_prompt": request.negative_prompt,
                "width": request.width,
                "height": request.height,
                "frames": request.frames,
                "fps": request.fps,
                "seed": request.seed,
            }
            if request.input_images and request.generation_type.value == "image_to_video":
                values["image"] = self.client.upload_image(request.input_images[0])

            workflow.auto_bind(values)
            workflow.apply_bindings(values, bindings)
            job_id = self.client.queue_prompt(workflow.to_dict())
            history = self.client.wait_for_completion(job_id)

            project_output = self.output_dir / job_id
            outputs: list[Path] = []
            for index, item in enumerate(self.client.output_items(history), start=1):
                suffix = Path(item["filename"]).suffix or ".bin"
                destination = project_output / f"output_{index:03d}{suffix}"
                outputs.append(self.client.download_output(item, destination))

            return GenerationResult(True, outputs, job_id=job_id)
        except Exception as exc:
            return GenerationResult(False, error=str(exc))

    def cancel(self, job_id: str) -> bool:
        return self.client.interrupt()
