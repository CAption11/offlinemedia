from pathlib import Path

import app.core.config as config_module
from app.core.config import AppConfig, load_config, save_config


def _mock_directories(root: Path) -> dict:
    """Create a mock directory structure with all required keys."""
    return {
        "root": root,
        "config": root / "config",
        "models": root / "models",
        "workflows": root / "workflows",
        "projects": root / "projects",
        "outputs": root / "outputs",
        "logs": root / "logs",
        "cache": root / "cache",
    }


def test_config_round_trip(tmp_path, monkeypatch):
    root = tmp_path / "OfflineMedia"
    monkeypatch.setattr(config_module, "ensure_directories", lambda: _mock_directories(root))

    original = AppConfig(comfyui_url="http://127.0.0.1:9000", default_frames=25)
    save_config(original)
    loaded = load_config()

    assert loaded.comfyui_url == original.comfyui_url
    assert loaded.default_frames == original.default_frames


def test_corrupt_config_falls_back_to_defaults(tmp_path, monkeypatch):
    root = tmp_path / "OfflineMedia"
    config_dir = root / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "settings.json").write_text("not-json", encoding="utf-8")
    monkeypatch.setattr(config_module, "ensure_directories", lambda: _mock_directories(root))

    loaded = load_config()
    assert loaded.comfyui_url == "http://127.0.0.1:8188"
