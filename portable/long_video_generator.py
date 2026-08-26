"""Orchestrate multi-clip generation for long-form video (up to 15+ minutes).

How it works:
1. User provides a list of scene prompts (one prompt per scene/clip).
2. Each scene is sent to Wan2GP via its HTTP API for generation.
3. The last frame of each clip seeds the next one (image-to-video continuity).
4. All clips are stitched with FFmpeg into a single output file.
5. Progress is saved to a state file so a crashed session can resume.

A 15-minute video at 8 fps, 10-second clips requires ~90 clips.
On a free T4 (~5 min/clip) that takes ~7.5 hours — within Colab Pro limits.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from portable.clip_stitcher import extract_last_frame, stitch


# ---------------------------------------------------------------------------
# Scene definition
# ---------------------------------------------------------------------------

@dataclass
class Scene:
    """One scene in the long-form video."""
    prompt: str
    duration_seconds: float = 8.0
    negative_prompt: str = "blurry, distorted, watermark, text, low quality"
    width: int = 480
    height: int = 272   # 16:9 at 480p — fits T4 VRAM
    fps: int = 8
    seed: int = -1       # -1 = random

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt": self.prompt,
            "duration_seconds": self.duration_seconds,
            "negative_prompt": self.negative_prompt,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "seed": self.seed,
        }


@dataclass
class GenerationPlan:
    """The full script for a long-form video."""
    title: str
    scenes: list[Scene]
    use_continuity: bool = True   # last frame → next scene start image
    output_dir: Path = Path("/content/Wan2GP-data/outputs")

    @property
    def clips_dir(self) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in self.title)
        return self.output_dir / safe

    @property
    def state_file(self) -> Path:
        return self.clips_dir / "generation_state.json"

    @property
    def final_output(self) -> Path:
        return self.output_dir / f"{self.clips_dir.name}_final.mp4"

    def estimate_total_duration(self) -> float:
        return sum(s.duration_seconds for s in self.scenes)


# ---------------------------------------------------------------------------
# State tracking (resume on crash)
# ---------------------------------------------------------------------------

@dataclass
class GenerationState:
    """Persisted progress so a Colab restart can pick up where it left off."""
    plan_title: str
    total_scenes: int
    completed: dict[int, str] = field(default_factory=dict)  # index → clip path
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def load(cls, path: Path) -> "GenerationState":
        data = json.loads(path.read_text())
        state = cls(plan_title=data["plan_title"], total_scenes=data["total_scenes"])
        state.completed = {int(k): v for k, v in data.get("completed", {}).items()}
        state.started_at = data.get("started_at", state.started_at)
        return state

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "plan_title": self.plan_title,
            "total_scenes": self.total_scenes,
            "completed": self.completed,
            "started_at": self.started_at,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2))

    @property
    def remaining_indices(self) -> list[int]:
        return [i for i in range(self.total_scenes) if i not in self.completed]

    @property
    def is_complete(self) -> bool:
        return len(self.completed) == self.total_scenes


# ---------------------------------------------------------------------------
# Wan2GP API client (gradio_client — works with Gradio 4.x)
# ---------------------------------------------------------------------------

class Wan2GPClient:
    """Call Wan2GP via gradio_client, which works with Gradio 3.x and 4.x.

    Wan2GP's Gradio endpoint names vary by version, so this client discovers
    the available APIs on first use and picks the best match automatically.
    Call view_api() to print what Wan2GP exposes in this installation.
    """

    # Candidate API names Wan2GP uses for its main generation function.
    # Tried in order; first one that exists wins.
    _CANDIDATE_API_NAMES = [
        "/generate",
        "/run",
        "/predict",
        "/generate_video",
        "/text_to_video",
    ]

    def __init__(self, host: str = "127.0.0.1", port: int = 7860):
        self.base_url = f"http://{host}:{port}"
        self._client = None
        self._api_name: str | None = None

    def _get_client(self):
        if self._client is None:
            try:
                from gradio_client import Client  # type: ignore[import-untyped]
            except ImportError:
                import subprocess, sys
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-q", "gradio_client"],
                    check=True,
                )
                from gradio_client import Client  # type: ignore[import-untyped]
            self._client = Client(self.base_url, verbose=False)
        return self._client

    def view_api(self) -> None:
        """Print all API endpoints Wan2GP exposes in this installation."""
        self._get_client().view_api()

    def _discover_api_name(self) -> str:
        """Find which generation API name this Wan2GP version uses."""
        if self._api_name is not None:
            return self._api_name
        client = self._get_client()
        # gradio_client stores endpoint info in client.endpoints
        try:
            available = {ep.api_name for ep in client.endpoints if hasattr(ep, "api_name")}
        except Exception:
            available = set()

        for name in self._CANDIDATE_API_NAMES:
            if name in available:
                self._api_name = name
                print(f"Wan2GP API: using endpoint '{name}'")
                return name

        # Fallback: use fn_index 0 (works with older Gradio 3.x builds)
        print("Warning: could not discover API name; falling back to fn_index=0")
        self._api_name = 0  # type: ignore[assignment]
        return self._api_name  # type: ignore[return-value]

    def is_available(self, timeout: float = 5.0) -> bool:
        import urllib.request
        try:
            urllib.request.urlopen(f"{self.base_url}/", timeout=timeout)
            return True
        except Exception:
            return False

    def _call(self, *args) -> Path:
        """Invoke the generation endpoint and return the output video path."""
        import shutil as _shutil
        client = self._get_client()
        api_name = self._discover_api_name()
        if isinstance(api_name, int):
            result = client.predict(*args, fn_index=api_name)
        else:
            result = client.predict(*args, api_name=api_name)
        # gradio_client returns a file path string or a dict with "name"
        if isinstance(result, dict):
            clip_path = Path(result["name"])
        elif isinstance(result, (list, tuple)):
            first = result[0]
            clip_path = Path(first["name"] if isinstance(first, dict) else first)
        else:
            clip_path = Path(str(result))
        return clip_path

    def generate_text_to_video(self, scene: Scene, output_path: Path) -> Path:
        """Generate a clip from a text prompt and save it to output_path."""
        import shutil
        frames = max(1, int(scene.duration_seconds * scene.fps))
        clip_path = self._call(
            scene.prompt,
            scene.negative_prompt,
            scene.width,
            scene.height,
            frames,
            scene.fps,
            scene.seed,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(clip_path), str(output_path))
        return output_path

    def generate_image_to_video(
        self,
        scene: Scene,
        start_image: Path,
        output_path: Path,
    ) -> Path:
        """Generate a clip from a start image for visual continuity."""
        import shutil
        frames = max(1, int(scene.duration_seconds * scene.fps))
        clip_path = self._call(
            scene.prompt,
            scene.negative_prompt,
            scene.width,
            scene.height,
            frames,
            scene.fps,
            scene.seed,
            str(start_image),
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(clip_path), str(output_path))
        return output_path


# ---------------------------------------------------------------------------
# Long-form video generator
# ---------------------------------------------------------------------------

class LongVideoGenerator:
    """Generate a long-form video from a GenerationPlan."""

    def __init__(
        self,
        plan: GenerationPlan,
        client: Wan2GPClient | None = None,
    ):
        self.plan = plan
        self.client = client or Wan2GPClient()

    def generate(self, resume: bool = True) -> Path:
        """Run all scenes and stitch into one file. Returns the final video path.

        Args:
            resume: If True and a state file exists, skip already-completed clips.
        """
        if not self.client.is_available():
            raise RuntimeError(
                "Wan2GP server is not reachable. Run wan2gp_bootstrap.bootstrap() first."
            )

        plan = self.plan
        plan.clips_dir.mkdir(parents=True, exist_ok=True)

        # Load or create state
        if resume and plan.state_file.exists():
            state = GenerationState.load(plan.state_file)
            print(f"Resuming '{plan.title}': {len(state.completed)}/{state.total_scenes} clips done.")
        else:
            state = GenerationState(plan_title=plan.title, total_scenes=len(plan.scenes))
            state.save(plan.state_file)

        total = len(plan.scenes)
        est_min = plan.estimate_total_duration() / 60
        print(f"\n{'='*60}")
        print(f"  {plan.title}")
        print(f"  {total} scenes · ~{est_min:.1f} min of video")
        print(f"  Continuity: {'on' if plan.use_continuity else 'off'}")
        print(f"{'='*60}\n")

        seed_image: Path | None = None

        for idx in range(total):
            if idx in state.completed:
                # Already generated; extract last frame for continuity
                clip = Path(state.completed[idx])
                if plan.use_continuity and clip.exists():
                    seed_image = self._extract_seed(clip, idx)
                print(f"  [{idx+1}/{total}] skipped (already done): {clip.name}")
                continue

            scene = plan.scenes[idx]
            clip_path = plan.clips_dir / f"clip_{idx:04d}.mp4"

            print(f"  [{idx+1}/{total}] Generating: {scene.prompt[:60]}...")
            t0 = time.monotonic()

            try:
                if plan.use_continuity and seed_image is not None and seed_image.exists():
                    clip_path = self.client.generate_image_to_video(scene, seed_image, clip_path)
                else:
                    clip_path = self.client.generate_text_to_video(scene, clip_path)
            except Exception as exc:
                print(f"  ❌ Scene {idx} failed: {exc}")
                raise

            elapsed = time.monotonic() - t0
            print(f"  ✅ [{idx+1}/{total}] Done in {elapsed:.0f}s → {clip_path.name}")

            state.completed[idx] = str(clip_path)
            state.save(plan.state_file)

            if plan.use_continuity:
                seed_image = self._extract_seed(clip_path, idx)

        # All scenes done — stitch
        print(f"\nStitching {total} clips...")
        completed_clips = [Path(state.completed[i]) for i in range(total)]
        final = stitch(completed_clips, plan.final_output)

        total_dur = sum(
            c.stat().st_size for c in completed_clips if c.exists()
        )
        print(f"\n🎬 Final video: {final}")
        print(f"   Ready to play or download from Colab.")
        return final

    def _extract_seed(self, clip: Path, idx: int) -> Path:
        seed_path = self.plan.clips_dir / f"seed_{idx:04d}.png"
        try:
            extract_last_frame(clip, seed_path)
        except Exception as exc:
            print(f"  Warning: could not extract seed frame from clip {idx}: {exc}")
        return seed_path


# ---------------------------------------------------------------------------
# Convenience: build a plan from a simple list of prompts
# ---------------------------------------------------------------------------

def plan_from_prompts(
    title: str,
    prompts: list[str],
    *,
    scene_duration: float = 8.0,
    fps: int = 8,
    width: int = 480,
    height: int = 272,
    negative_prompt: str = "blurry, distorted, watermark, text, low quality",
    use_continuity: bool = True,
    output_dir: Path = Path("/content/Wan2GP-data/outputs"),
) -> GenerationPlan:
    """Build a GenerationPlan from a plain list of text prompts.

    Example::

        plan = plan_from_prompts(
            "My Short Film",
            [
                "A sunrise over misty mountains, golden light",
                "A hawk soaring through a valley, aerial view",
                "A river rushing through a forest, slow motion",
            ],
            scene_duration=8.0,
            fps=8,
        )
        generator = LongVideoGenerator(plan)
        final = generator.generate()
    """
    scenes = [
        Scene(
            prompt=prompt,
            duration_seconds=scene_duration,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            fps=fps,
        )
        for prompt in prompts
    ]
    return GenerationPlan(
        title=title,
        scenes=scenes,
        use_continuity=use_continuity,
        output_dir=output_dir,
    )
