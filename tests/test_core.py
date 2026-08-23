from pathlib import Path

from app.core.generation import GenerationRequest, GenerationType
from app.core.paths import ensure_directories
from app.storage.projects import ProjectStore


def test_generation_request_defaults() -> None:
    request = GenerationRequest(GenerationType.TEXT_TO_VIDEO, prompt="test")
    assert request.generation_type is GenerationType.TEXT_TO_VIDEO
    assert request.frames == 49
    assert request.fps == 8


def test_project_store_round_trip(tmp_path: Path) -> None:
    store = ProjectStore(tmp_path)
    directory = store.create("Test Project", {"width": 512})
    payload = store.load(directory)
    assert payload["name"] == "Test Project"
    assert payload["settings"]["width"] == 512
