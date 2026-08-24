"""Fetch the official Wan 2.1 ComfyUI example workflows.

The repository stores our application metadata and manifests, but does not
vendor upstream workflow blobs that can change. This script downloads the
current official example workflows into a runtime directory for validation.
"""
from __future__ import annotations

from pathlib import Path
from urllib.request import Request, urlopen

WORKFLOW_URLS = {
    "text_to_video.json": "https://comfyanonymous.github.io/ComfyUI_examples/wan/text_to_video_wan.json",
    "image_to_video.json": "https://comfyanonymous.github.io/ComfyUI_examples/wan/image_to_video_wan_example.json",
}


def download(url: str, destination: Path) -> None:
    request = Request(url, headers={"User-Agent": "OfflineMedia/Portable"})
    with urlopen(request, timeout=60) as response:
        data = response.read()
    if not data:
        raise RuntimeError(f"Empty workflow response: {url}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    print(f"Downloaded {destination} ({len(data):,} bytes)")


def sync(output_dir: Path) -> None:
    for filename, url in WORKFLOW_URLS.items():
        download(url, output_dir / filename)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download official Wan 2.1 ComfyUI workflows")
    parser.add_argument("--output-dir", type=Path, default=Path("workflows/official"))
    args = parser.parse_args()
    sync(args.output_dir)
