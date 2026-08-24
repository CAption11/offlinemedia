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


def test_ui_workflow_preserves_ksampler_control_after_generate():
    """ComfyUI can omit the seed-control widget from input_order.

    The UI workflow still stores it in widgets_values immediately after seed.
    The converter must not shift that value into steps.
    """
    data = {
        "nodes": [{
            "id": 3,
            "type": "KSampler",
            "inputs": [
                {"name": "model", "link": 1},
                {"name": "positive", "link": 2},
                {"name": "negative", "link": 3},
                {"name": "latent_image", "link": 4},
            ],
            "widgets_values": [123, "randomize", 30, 6, "uni_pc", "simple", 1],
            "properties": {"Node name for S&R": "KSampler"},
        }],
        "links": [
            [1, 10, 0, 3, 0, "MODEL"],
            [2, 11, 0, 3, 1, "CONDITIONING"],
            [3, 12, 0, 3, 2, "CONDITIONING"],
            [4, 13, 0, 3, 3, "LATENT"],
        ],
    }
    object_info = {
        "KSampler": {
            "input": {
                "required": {
                    "model": ["MODEL", {}],
                    "positive": ["CONDITIONING", {}],
                    "negative": ["CONDITIONING", {}],
                    "latent_image": ["LATENT", {}],
                    "seed": ["INT", {"control_after_generate": True}],
                    "steps": ["INT", {"default": 20}],
                    "cfg": ["FLOAT", {"default": 8}],
                    "sampler_name": ["COMBO", {}],
                    "scheduler": ["COMBO", {}],
                    "denoise": ["FLOAT", {"default": 1}],
                },
                "optional": {},
            },
            "input_order": {
                "required": [
                    "model", "positive", "negative", "latent_image",
                    "seed", "steps", "cfg", "sampler_name", "scheduler", "denoise",
                ],
                "optional": [],
            },
        }
    }

    workflow = Workflow.from_ui_workflow(data, object_info)
    inputs = workflow.graph["3"]["inputs"]
    assert inputs["seed"] == 123
    assert inputs["control_after_generate"] == "randomize"
    assert inputs["steps"] == 30
    assert inputs["cfg"] == 6
    assert inputs["sampler_name"] == "uni_pc"
    assert inputs["scheduler"] == "simple"
    assert inputs["denoise"] == 1
