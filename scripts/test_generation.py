"""Run and validate a real OfflineMedia generation smoke test against ComfyUI."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.generation import GenerationRequest, GenerationType
from app.engines.comfyui_client import ComfyUIClient
from app.engines.comfyui_engine import ComfyUIEngine


def validate_output(path: Path) -> dict:
    """Validate that a generated output exists and is a readable media file."""
    if not path.is_file():
        raise RuntimeError(f"Output file does not exist: {path}")
    if path.stat().st_size == 0:
        raise RuntimeError(f"Output file is empty: {path}")

    info = {"path": str(path), "size_bytes": path.stat().st_size}
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        info["ffprobe"] = "not installed"
        return info

    command = [
        ffprobe,
        "-v", "error",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(path),
    ]
    completed = subprocess.run(command, text=True, capture_output=True)
    if completed.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}: {completed.stderr.strip()}")

    try:
        probe = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ffprobe returned invalid JSON for {path}") from exc

    streams = probe.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    if video is None:
        raise RuntimeError(f"No video stream found in output: {path}")

    duration = (probe.get("format") or {}).get("duration")
    info.update({
        "codec": video.get("codec_name"),
        "width": video.get("width"),
        "height": video.get("height"),
        "frames": video.get("nb_frames"),
        "fps": video.get("r_frame_rate"),
        "duration": duration,
    })

    # ffprobe reports a still image as a video stream with a single frame, so
    # "has a video stream" alone would let a lone PNG pass as a generated
    # video. Reject only when the file is provably single-frame: an animation
    # whose frame count ffprobe cannot determine must not be failed here.
    if _is_single_frame(video, duration):
        raise RuntimeError(
            f"Output is a single still frame, not a video: {path} "
            f"(codec={video.get('codec_name')}, frames={video.get('nb_frames')})"
        )
    return info


def _as_number(value: object) -> float | None:
    """Parse an ffprobe field, which may be absent, 'N/A' or a numeric string."""
    if value in (None, "", "N/A"):
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _is_single_frame(video: dict, duration: object) -> bool:
    """Return True only when ffprobe positively reports one frame and no runtime."""
    frames = _as_number(video.get("nb_frames"))
    if frames is None or frames > 1:
        return False
    seconds = _as_number(duration)
    return seconds is None or seconds <= 0


def main() -> int:
    parser = argparse.ArgumentParser(description="OfflineMedia ComfyUI smoke test")
    parser.add_argument("--type", choices=[x.value for x in GenerationType], default="text_to_video")
    parser.add_argument("--prompt", default="A small red ball rolling across a wooden table, natural lighting")
    parser.add_argument("--negative-prompt", default="blurry, distorted, low quality")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8188)
    parser.add_argument("--width", type=int, default=320)
    parser.add_argument("--height", type=int, default=240)
    parser.add_argument("--frames", type=int, default=17)
    parser.add_argument("--fps", type=int, default=8)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--workflow-dir", type=Path, default=ROOT / "workflows")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "projects" / "smoke_tests")
    args = parser.parse_args()

    client = ComfyUIClient(host=args.host, port=args.port)
    if not client.is_available():
        print(f"ERROR: ComfyUI is not reachable at {args.host}:{args.port}")
        return 2

    request = GenerationRequest(
        generation_type=GenerationType(args.type),
        prompt=args.prompt,
        negative_prompt=args.negative_prompt,
        width=args.width,
        height=args.height,
        frames=args.frames,
        fps=args.fps,
        seed=args.seed,
        output_dir=args.output_dir,
    )
    engine = ComfyUIEngine(client, args.workflow_dir, args.output_dir)
    result = engine.generate(request)

    if not result.success:
        print("GENERATION FAILED:")
        print(result.error or "unknown error")
        return 1

    print("GENERATION PASSED")
    print("Job:", result.job_id)
    if not result.output_files:
        print("GENERATION FAILED: ComfyUI returned no output files")
        return 1

    for output in result.output_files:
        try:
            info = validate_output(output)
        except Exception as exc:
            print(f"OUTPUT VALIDATION FAILED: {exc}")
            return 1
        print("Output:", output)
        print("Output validation:", json.dumps(info, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
