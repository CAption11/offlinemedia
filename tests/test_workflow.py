from pathlib import Path

from app.engines.workflow import Workflow


def test_workflow_binding_updates_input(tmp_path: Path) -> None:
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(
        '{"6": {"inputs": {"text": "old"}, "class_type": "CLIPTextEncode"}}',
        encoding="utf-8",
    )

    workflow = Workflow.load(workflow_path)
    workflow.apply_bindings(
        {"prompt": "new prompt"},
        {"prompt": {"node": "6", "input": "text"}},
    )

    assert workflow.to_dict()["6"]["inputs"]["text"] == "new prompt"
