import json
from pathlib import Path

from app.core.generation import GenerationRequest, GenerationType
from app.engines.workflow import Workflow


def test_text_prompt_and_dimensions_are_bound(tmp_path: Path):
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(json.dumps({
        "1": {"class_type": "CLIPTextEncode", "inputs": {"text": "old prompt"}},
        "2": {"class_type": "EmptyLatentVideo", "inputs": {"width": 64, "height": 64, "length": 8}},
        "3": {"class_type": "KSampler", "inputs": {"seed": 1}},
    }))
    workflow = Workflow.load(workflow_path)
    request = GenerationRequest(
        generation_type=GenerationType.TEXT_TO_VIDEO,
        prompt="new prompt",
        width=320,
        height=240,
        frames=17,
        seed=123,
    )
    values = {"prompt": request.prompt, "negative_prompt": request.negative_prompt, "width": request.width,
              "height": request.height, "frames": request.frames, "fps": request.fps, "seed": request.seed}
    workflow.auto_bind(values)
    graph = workflow.to_dict()
    assert graph["1"]["inputs"]["text"] == "new prompt"
    assert graph["2"]["inputs"]["width"] == 320
    assert graph["2"]["inputs"]["height"] == 240
    assert graph["2"]["inputs"]["length"] == 17
    assert graph["3"]["inputs"]["seed"] == 123


def test_explicit_binding_overrides_auto_binding():
    workflow = Workflow({"1": {"class_type": "CLIPTextEncode", "inputs": {"text": "old"}},
                         "9": {"class_type": "CLIPTextEncode", "inputs": {"text": "other"}}})
    workflow.auto_bind({"prompt": "automatic"})
    workflow.apply_bindings({"prompt": "explicit"}, {"prompt": {"node": "9", "input": "text"}})
    assert workflow.graph["1"]["inputs"]["text"] == "automatic"
    assert workflow.graph["9"]["inputs"]["text"] == "explicit"
