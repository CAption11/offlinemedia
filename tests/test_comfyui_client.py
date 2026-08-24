from pathlib import Path

from app.engines.comfyui_client import ComfyUIClient


def test_client_accepts_host_and_port() -> None:
    client = ComfyUIClient(host="127.0.0.1", port=9999)
    assert client.base_url == "http://127.0.0.1:9999"


def test_client_accepts_full_url() -> None:
    client = ComfyUIClient(base_url="http://localhost:8188/")
    assert client.base_url == "http://localhost:8188"


def test_output_items_extracts_all_supported_media() -> None:
    history = {
        "outputs": {
            "1": {"gifs": [{"filename": "clip.webp"}]},
            "2": {"videos": [{"filename": "clip.mp4"}], "audio": [{"filename": "audio.wav"}]},
            "3": {"images": [{"filename": "preview.png"}]},
        }
    }
    names = {item["filename"] for item in ComfyUIClient.output_items(history)}
    assert names == {"clip.webp", "clip.mp4", "audio.wav", "preview.png"}


def test_output_download_requires_filename(tmp_path: Path) -> None:
    # The method should fail before attempting network access for malformed output metadata.
    client = ComfyUIClient()
    try:
        client.download_output({}, tmp_path / "x.bin")
    except Exception as exc:
        assert "filename" in str(exc).lower()
    else:
        raise AssertionError("Expected malformed output metadata to fail")
