"""Run a real OfflineMedia generation smoke test against ComfyUI."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.generation import GenerationRequest, GenerationType
from app.engines.comfyui_client import ComfyUIClient
from app.engines.comfyui_engine import ComfyUIEngine


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
    for output in result.output_files:
        print("Output:", output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
